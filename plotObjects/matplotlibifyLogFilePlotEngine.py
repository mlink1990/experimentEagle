# -*- coding: utf-8 -*-
"""
Created on Sat May 23 11:35:11 2015

@author: tharrison

"""

import logging
import scipy
import pandas
import itertools

logger=logging.getLogger("ExperimentEagle.logFilePlotEngine")

class LogFilePlotEngine():
    """just analyses and aggregates data in eagle log files. subset of the code
    in LogFilePlot"""
    mode="X Variable - Measured Y"
    
    logFile = ""
    xAxis = ""
    yAxis = ""
    aggregateAxis = ""
    masterList = ""
    series = ""

    filterYs = False
    filterMinYs = -scipy.inf
    filterMaxYs = scipy.inf
    
    filterXs = False
    filterMinXs = -scipy.inf
    filterMaxXs = scipy.inf
    
    filterNaN = True    
    
    filterSpecific = False
    filterSpecificString = ""
            
    def parseSeries(self):
        """series is a column seperated string of all columns in log file 
        to be treated as a seperate series. If there are multiple values
        each unique combination is a new series"""
        if self.series=="":
            return []
        else:
            return self.series.split(",")
    
    def getData(self):
        """using pandas, this function aggregates the data and groups by
        each series combination. Returns the aggregated data at which point 
        we can now see what we need to plot etc.

        All filters are performed after getting the dataframe but before returning
        the aggregate frame.
        """
        try:
            self.dataframe = pandas.read_csv(self.logFile, index_col="datetime", parse_dates = True)
        except ValueError as e:
            logger.error("No datetime column. Is this a valid Eagle log file? I will try without index")
            self.dataframe = pandas.read_csv(self.logFile, parse_dates = True)  
        self.filterData()
        seriesList = self.parseSeries()
        self.validateColumns()
        if self.mode == "X Variable - Measured Y":
            #The last column we aggregate over is the x axis. y axis gets mean and stdev per aggregation
            return self.dataframe.groupby(seriesList+[self.xAxis], as_index=False).aggregate({self.yAxis:["mean","std"]})
        elif self.mode == "X Measured - Y Measured":
            #here the x axis needs to be aggregated to mean and stdev as well as the y axis. aggregate axis defines the last axis we aggregate over
            #classic example here is a N vs T plot where aggregate axis is evaporation time. series would be for evaporation at different MT gradients
            return self.dataframe.groupby(seriesList+[self.aggregateAxis], as_index=False).aggregate({self.xAxis:["mean","std"],self.yAxis:["mean","std"]})
        elif self.mode == "XY Scatter":
            #here we don't care if x is a variable or measured. We just plot every x y point as a scatter point. no error bars.
            #here the raw data frame contains everything we need in the correct format!            
            return self.dataframe[seriesList+[self.xAxis,self.yAxis]]
        
    def humanSeriesName(self, seriesTuple):
        """returns the name for a given series Tuple"""
        name=""
        c=0
        for seriesName in self.seriesList:
            name+=seriesName+"="+str(seriesTuple[c])+" "
            c+=1
        name = name.strip(" ")
        return name
        
    def filterData(self):
        """filtering before aggregating the data for plots """
        if self.filterYs:
            self.performFilterYS()
        if self.filterXs:
            self.performFilterXS()
        if self.filterNaN:
            self.performFilterNaN()
        if self.filterSpecific:
            self.performFilterSpecific()
        
    def performFilterYS(self):
        """ remove y values above or below set bounds"""
        logger.debug("filtering y data before aggregating and plotting")
        logger.debug("dataframe was %s rows" % (len(self.dataframe)))
        self.dataframe = self.dataframe[(self.dataframe[self.yAxis]>self.filterMinYs) &(self.dataframe[self.yAxis]<self.filterMaxYs)]
        logger.debug("dataframe now %s rows" % (len(self.dataframe)))
        
    def performFilterXS(self):
        """remove x data above or below set bounds """
        logger.debug("filtering x data before aggregating and plotting")
        logger.debug("dataframe was %s rows" % (len(self.dataframe)))
        self.dataframe = self.dataframe[(self.dataframe[self.xAxis]>self.filterMinXs) &(self.dataframe[self.xAxis]<self.filterMaxXs)]
        logger.debug("dataframe now %s rows" % (len(self.dataframe)))
        
    def performFilterNaN(self):
        """removes NaN and replaces with zero """
        logger.debug("filtering NaN--> 0 in place")
        self.dataframe.fillna(value=0.0, inplace=True)

    def performFilterSpecific(self):
        """specific filter string is a comma separated list of filters. Supported filters are:
        ==, >, <"""
        filterStrings = self.filterSpecificString.split(",")
        for query in filterStrings:
            query = query.strip()
            if "==" in query:
                columnName, value = query.split("==")
                columnName=columnName.strip()
                value=float(value.strip())
                self.dataframe = self.dataframe[self.dataframe[columnName]==value]
            elif ">" in query:
                columnName, value = query.split(">")
                columnName=columnName.strip()
                value=float(value.strip())
                self.dataframe = self.dataframe[self.dataframe[columnName]>value]
            elif "<" in query:
                columnName, value = query.split("<")
                columnName=columnName.strip()
                value=float(value.strip())
                self.dataframe = self.dataframe[self.dataframe[columnName]<value]
            else:
                logger.error("unrecognised operator for query")
                
    def getUniqueSeries(self, aggregatedDataFrame):
        """ given a aggregated data frame, this returns the list of all series
        names that are contained in the logFile."""
        self.seriesList = self.parseSeries()
        uniqueValues = [aggregatedDataFrame[seriesName].unique() for seriesName in self.seriesList] # [array(uniquevaluesseries1), array(uniquevaluesseries2),...]
        uniqueSeriesValues = list(itertools.product(*uniqueValues))#TODO at this point we should filter to only unique series combinations that actually have data
        #uniqueSeriesValuesWithData = []
        return uniqueSeriesValues
        
    def getRelevantData(self,aggregatedDataFrame,uniqueSeriesValueTuple):
        """given a uniqueSeriesValueTuple (e.g. (35, 0.002, 1) for (gradient, TOFtime, dummyVar)
        we return the aggregated data frame filtered to the relevant series.
        Returns None if there is no data in the relevant data frame this allows user to catch a non existing legend series        
        """
        relevantDataFrame = aggregatedDataFrame
        for columnName, value in zip(self.seriesList,uniqueSeriesValueTuple):
            logger.debug( "columnName, value = %s, %s" % (columnName, value) )
            logger.debug( "relevantDataFrame[relevantDataFrame[%s]==%s]" % (columnName, value) )
            relevantDataFrame = relevantDataFrame[relevantDataFrame[columnName]==value]
        logger.debug("relevantDataFrame = \n %s" % relevantDataFrame)
        if len(relevantDataFrame)==0:
            return None
        return relevantDataFrame        

    def setFittingData(self):
        """gets a list of all valid series aggregated
        then iterates through and sends them to fitting module"""
        logger.info("beginning set Fitting Data func")
        aggregatedDataFrame = self.getData()
        uniqueSeriesValueTuples = self.getUniqueSeries(aggregatedDataFrame)
        logger.warning("uniqueSeriesValuesTuples=%s", uniqueSeriesValueTuples)
        validNames = []#can change when user presses refresh
        for uniqueSeriesValueTuple in uniqueSeriesValueTuples:#TODO ADD SORTED STATEMENT  
            relevantDataFrame=self.getRelevantData(aggregatedDataFrame,uniqueSeriesValueTuple)
            if relevantDataFrame is None:#skip non existing legend series
                continue
            xs = relevantDataFrame[self.xAxis].values
            if self.mode == "XY Scatter":
                ys = relevantDataFrame[self.yAxis].values
            else:
                ys = relevantDataFrame[self.yAxis,"mean"].values
            humanName = self.humanSeriesName(uniqueSeriesValueTuple)
            if humanName == "":
                humanName="data"
            self.logFilePlotFitterReference.setFitData(humanName,xs,ys)
            validNames.append(humanName) 
        self.logFilePlotFitterReference.cleanValidNames(validNames)#removes unecessary elements from datasets dict
        self.logFilePlotFitterReference.setValidNames()#resets name choices to only be remaining valid keys of datasets dict
