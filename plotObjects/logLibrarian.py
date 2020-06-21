# -*- coding: utf-8 -*-
"""
Created on Sat Mar 05 17:15:06 2016

@author: tharrison
"""

import traits.api as traits
import traitsui.api as traitsui
import os
import datetime
import logging
import csv


logger=logging.getLogger("ExperimentEagle.logFilePlot")


class EntryBlock(traits.HasTraits):
    
    fieldName = traits.String("fieldName",desc = "describes what the information to be entered in the text block is referring to")
    textBlock = traits.String()
    commitButton = traits.Button("save",desc="commit information in text block to logFile")

    
    traits_view = traitsui.View(traitsui.VGroup(
                    traitsui.Item("fieldName",show_label=False, style="readonly"),
                    traitsui.Item("textBlock",show_label=False, style="custom"),
                    traitsui.Item("commitButton",show_label=False), show_border=True, label="information"
                        ))
    
    def __init__(self, **traitsDict):
        """user supplies arguments in init to supply class attributes defined above """
        super(EntryBlock,self).__init__(**traitsDict)
        
    def _commitButton_fired(self):
        logger.info("saving %s info starting" % self.fieldName)
        timeStamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        blockDelimiterStart = "__"+self.fieldName+"__<start>"
        blockDelimiterEnd = "__"+self.fieldName+"__<end>"
        fullString = "\n"+blockDelimiterStart+"\n"+timeStamp+"\n"+self.textBlock+"\n"+blockDelimiterEnd+"\n"
        with open(self.commentFile, "a+") as writeFile:
            writeFile.write(fullString)
        logger.info("saving %s info finished" % self.fieldName)
    
    def clearTextBlock(self):
        self.textBlock = ""

class AxisSelector(traits.HasTraits):
    """here we select what axes the user should use when plotting this data """
    masterList = traits.List
    masterListWithNone =  traits.List
    xAxis = traits.Enum(values="masterList")
    yAxis = traits.Enum(values="masterList")
    series = traits.Enum(values="masterListWithNone")
    commitButton = traits.Button("save",desc="commit information in text block to logFile")
    
    traits_view=traitsui.View(traitsui.VGroup(traitsui.Item("xAxis",label="x axis"),traitsui.Item("yAxis",label="y axis"),
                                  traitsui.Item("series",label="series"),traitsui.Item("commitButton",show_label=False),show_border=True, label="axes selection"))
    
    def __init__(self, **traitsDict):
        """allows user to select which axes are useful for plotting in this log"""
        super(AxisSelector, self).__init__(**traitsDict)
    
    
    def _masterList_default(self):
        """gets the header row of log file which are interpreted as the column
        names that can be plotted."""
        logger.info("updating master list of axis choices")
        logger.debug("comment file = %s" % self.logFile)
        print "comment file = %s" % self.logFile
        if not os.path.exists(self.logFile):
            return []
        try:
            with open(self.logFile) as csvfile:
                headerReader = csv.reader(csvfile)
                headerRow=headerReader.next()
            return headerRow
        except IOError:
            return []
            
    def _masterListWithNone_default(self):
        return ["None"]+self._masterList_default()
        
    def _commitButton_fired(self):
        logger.info("saving axes info starting")
        timeStamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        blockDelimiterStart = "__Axes Selection__<start>"
        blockDelimiterEnd = "__Axes Selection__<end>"
        textBlock = "xAxis = %s\nyAxis = %s\n series = %s" % (self.xAxis,self.yAxis,self.series)
        fullString = "\n"+blockDelimiterStart+"\n"+timeStamp+"\n"+textBlock+"\n"+blockDelimiterEnd+"\n"
        with open(self.commentFile, "a+") as writeFile:
            writeFile.write(fullString)
        logger.info("saving axes info finished")

class Librarian(traits.HasTraits):
    """Librarian provides a way of writing useful information into the 
    log folder for eagle logs. It is designed to make the information inside
    an eagle log easier to come back to. It mainly writes default strings into
    the comments file in the log folder"""
    
    logType = traits.Enum("important","debug","calibration")
    typeCommitButton = traits.Button("save")
    axisList = AxisSelector()
    purposeBlock = EntryBlock(fieldName="What is the purpose of this log?")
    explanationBlock = EntryBlock(fieldName = "Explain what the data shows (important parameters that change, does it make sense etc.)?")
    additionalComments = EntryBlock(fieldName = "Anything Else?")

    traits_view = traitsui.View(
        traitsui.VGroup(
            traitsui.Item("logFolder",show_label=False, style="readonly"),
            traitsui.HGroup(traitsui.Item("logType",show_label=False),traitsui.Item("typeCommitButton",show_label=False)),
            traitsui.Item("axisList",show_label=False, editor=traitsui.InstanceEditor(),style='custom'),
            traitsui.Item("purposeBlock",show_label=False, editor=traitsui.InstanceEditor(),style='custom'),
            traitsui.Item("explanationBlock",show_label=False, editor=traitsui.InstanceEditor(),style='custom'),
            traitsui.Item("additionalComments",show_label=False, editor=traitsui.InstanceEditor(),style='custom')
        )  , resizable=True  , kind ="live"
    )    
    
    def __init__(self, **traitsDict):
        """Librarian object requires the log folder it is referring to. If a .csv
        file is given as logFolder argument it will use parent folder as the 
        logFolder"""
        super(Librarian, self).__init__(**traitsDict)
        if os.path.isfile(self.logFolder):
            self.logFolder = os.path.split(self.logFolder)[0]
        else:
            logger.debug("found these in %s: %s" %(self.logFolder, os.listdir(self.logFolder) ))
        
        self.logFile = os.path.join(self.logFolder, os.path.split(self.logFolder)[1]+".csv")
        self.commentFile = os.path.join(self.logFolder, "comments.txt")
        self.axisList.commentFile = self.commentFile
        self.axisList.logFile = self.logFile
        self.purposeBlock.commentFile = self.commentFile
        self.explanationBlock.commentFile = self.commentFile
        self.additionalComments.commentFile  = self.commentFile
        
    def _typeCommitButton_fired(self):
        logger.info("saving axes info starting")
        timeStamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        blockDelimiterStart = "__Log Type__<start>"
        blockDelimiterEnd = "__Log Type__<end>"
        fullString = "\n"+blockDelimiterStart+"\n"+timeStamp+"\n"+self.logType+"\n"+blockDelimiterEnd+"\n"
        with open(self.commentFile, "a+") as writeFile:
            writeFile.write(fullString)
        logger.info("saving axes info finished")
        
if __name__=="__main__":
    eb = Librarian(logFolder=r"G:\Experiment Humphry\Experiment Control And Software\experimentEagle\plotObjects\testDebugLog")
    eb.configure_traits()
    