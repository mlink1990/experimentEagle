# -*- coding: utf-8 -*-
"""
Created on Thu Mar 31 17:56:18 2016

@author: user
"""

import chaco.api as chaco
import chaco.tools.api as tools
import traits.api as traits
import traitsui.api as traitsui
import lmfit
import scipy
import inspect
import logging
import time
import os.path
import csv
import fittingFunctions
import collections

logger=logging.getLogger("ExperimentEagle.logFilePlotFitter")

class Parameter(traits.HasTraits):
    """represents a lmfit variable in a fit. E.g. the standard deviation in a gaussian
    fit"""    
    parameter = traits.Instance(lmfit.Parameter)
    name = traits.Str
    
    initialValue = traits.Float
    calculatedValue = traits.Float
    vary = traits.Bool(True)

    minimumEnable = traits.Bool(False)
    minimum = traits.Float
    
    maximumEnable  = traits.Bool(False)
    maximum = traits.Float
    
    stdevError = traits.Float
    
    def __init__(self, **traitsDict):
        super(Parameter, self).__init__(**traitsDict)
        self.parameter = lmfit.Parameter(name=self.name)
        self.parameter.set(value=self.initialValue)
    
    def _initialValue_changed(self):
        self.parameter.set(value=self.initialValue)
    
    def _vary_changed(self):
        self.parameter.set(vary=self.vary)   
    
    def _minimum_changed(self):
        if self.minimumEnable:
            self.parameter.set(min=self.minimum)

    def _maximum_changed(self):
        if self.maximumEnabled:
            self.parameter.set(max=self.maximum)
        
    traits_view = traitsui.View(
                    traitsui.VGroup(
                        traitsui.HGroup(
                            traitsui.Item("vary", label="vary?", resizable= True),
                            traitsui.Item("name", show_label=False, style="readonly",width=0.2, resizable=True),
                            traitsui.Item("initialValue",label="initial", show_label=True, resizable=True),
                            traitsui.Item("calculatedValue",label="calculated",show_label=True,format_str="%G", style="readonly",width=0.2, resizable=True),
                            traitsui.Item("stdevError",show_label=False,format_str=u"\u00B1%G", style="readonly", resizable=True)
                                ),
                        traitsui.HGroup(
                            traitsui.Item("minimumEnable", label="min?", resizable= True),
                            traitsui.Item("minimum", label="min", resizable=True, visible_when="minimumEnable"),
                            traitsui.Item("maximumEnable",label="max?", resizable=True),
                            traitsui.Item("maximum",label="max", resizable=True, visible_when="maximumEnable")
                            )
                        ), resizable =True
                        )


#guess functions follow the syntax _funcname_guess(xs,ys)
#and they return a dictionary of variable names for the fits --> initial values
def custom(x):
    pass


class Model(traits.HasTraits):
    
    model = traits.Instance(lmfit.Model)
    function = None #python function for fitting
    guessFunction = None
    definitionString = traits.String()
    modelName = traits.String("")
    
    def __init__(self,function,**traitsDict):
        super(Model, self).__init__(**traitsDict)
        self.function = function
        self.model = lmfit.Model(function)
        self.parameters = self.model.make_params()
        try:
            self.definitionString = inspect.getsource(function)
        except IOError as e:
            self.definitionString = e.message
        if hasattr(fittingFunctions, function.__name__+"_guess"):
            self.guessFunction = getattr(fittingFunctions, function.__name__+"_guess")

class LogFilePlotFitter(traits.HasTraits):
    """This class allows the user to fit the data in log file plots with standard 
    functions or a custom function"""

    model = traits.Trait("Gaussian", {"Linear":Model(fittingFunctions.linear), "Quadratic":Model(fittingFunctions.quadratic), "Gaussian":Model(fittingFunctions.gaussian), "lorentzian":Model(fittingFunctions.lorentzian),"parabola":Model(fittingFunctions.parabola),
                                      "exponential":Model(fittingFunctions.exponentialDecay),"sineWave":Model(fittingFunctions.sineWave), "sineWaveDecay1":Model(fittingFunctions.sineWaveDecay1),  "sineWaveDecay2":Model(fittingFunctions.sineWaveDecay2),
                                        "sincSquared":Model(fittingFunctions.sincSquared),"sineSquared":Model(fittingFunctions.sineSquared), "sineSquaredDecay":Model(fittingFunctions.sineSquaredDecay), "custom":Model(custom)
                                      },desc="model selected for fitting the data") # mapped trait. so model --> string and model_ goes to Model object. see http://docs.enthought.com/traits/traits_user_manual/custom.html#mapped-traits
    parametersList = traits.List(Parameter, desc="list of parameters for fitting in chosen model")
    
    customCode = traits.Code("def custom(x, param1, param2):\n\treturn param1*param2*x", desc="python code for a custom fitting function")
    customCodeCompileButton = traits.Button("compile", desc="defines the above function and assigns it to the custom model for fitting")    
    fitButton = traits.Button("fit", desc = "runs fit on selected data set using selected parameters and model")
    usePreviousFitButton = traits.Button("use previous fit", desc="use the fitted values as the initial guess for the next fit")
    guessButton = traits.Button("guess", desc = "guess initial values from data using _guess function in library. If not defined button is disabled" )
    saveFitButton = traits.Button("save fit", desc="writes fit parameters values and tolerances to a file")
    cycleAndFitButton = traits.Button("cycle fit", desc="fits using current initial parameters, saves fit, copies calculated values to initial guess and moves to next dataset in ordered dict")
    dataSets = collections.OrderedDict() #dict mapping dataset name (for when we have multiple data sets) --> (xdata,ydata ) tuple (scipy arrays) e.g. {"myData": (array([1,2,3]), array([1,2,3]))}
    dataSetNames = traits.List(traits.String)
    selectedDataSet = traits.Enum(values="dataSetNames")
    modelFitResult = None
    logFilePlotReference = None
    modelFitMessage = traits.String("not yet fitted")
    isFitted = traits.Bool(False)
    maxFitTime = traits.Float(10.0, desc="maximum time fitting can last before abort")
    statisticsButton = traits.Button("stats")
    statisticsString = traits.String("statistics not calculated")    
    
    predefinedModelGroup = traitsui.VGroup( traitsui.Item("model",show_label=False), traitsui.Item("object.model_.definitionString", style="readonly", show_label=False, visible_when="model!='custom'"))
    customFunctionGroup = traitsui.VGroup(traitsui.Item("customCode",show_label=False), traitsui.Item("customCodeCompileButton", show_label=False), visible_when="model=='custom'")
    modelGroup = traitsui.VGroup(predefinedModelGroup,customFunctionGroup, show_border= True)
    dataAndFittingGroup =  traitsui.VGroup( traitsui.HGroup(traitsui.Item("selectedDataSet", label="dataset"), traitsui.Item("fitButton", show_label=False), traitsui.Item("usePreviousFitButton", show_label=False),
                                                            traitsui.Item("guessButton", show_label=False, enabled_when="model_.guessFunction is not None")),
                                            traitsui.HGroup( traitsui.Item("cycleAndFitButton", show_label=False),traitsui.Item("saveFitButton", show_label=False),traitsui.Item("statisticsButton", show_label=False)),
                                                            traitsui.Item("statisticsString", style="readonly"),traitsui.Item("modelFitMessage", style="readonly"), show_border=True)
    variablesGroup = traitsui.VGroup(traitsui.Item("parametersList", editor=traitsui.ListEditor(style="custom"), show_label=False,resizable=True), show_border=True, label="parameters")
        
    traits_view = traitsui.View(traitsui.Group(modelGroup,dataAndFittingGroup,variablesGroup, layout="split"), resizable=True)
    
    def __init__(self, **traitsDict):
        super(LogFilePlotFitter, self).__init__(**traitsDict)
        self._set_parametersList()
            
            
    def _set_parametersList(self):
        """sets the parameter list to the correct values given the current model """
        self.parametersList = [Parameter(name=parameterName, parameter = parameterObject ) for (parameterName,parameterObject) in self.model_.parameters.iteritems() ]

       
    def _model_changed(self):
        """updates model and hences changes parameters appropriately"""
        self._set_parametersList()
        self._guessButton_fired()# will only guess if there is a valid guessing function
        
    def _customCodeCompileButton_fired(self):
        """defines function as defined by user """
        exec(self.customCode)
        self.model_.__init__(custom)
        self._set_parametersList()
        
    def setFitData(self, name,xData, yData ):
        """updates the dataSets dictionary """
        self.dataSets[name]=(xData,yData)
        
    def cleanValidNames(self,uniqueValidNames):
        """removes any elements from datasets dictionary that do not 
        have a key in uniqueValidNames"""
        for dataSetName in self.dataSets.keys():
            if dataSetName not in uniqueValidNames:
                del self.dataSets[dataSetName]
    
    def setValidNames(self):
        """sets list of valid choices for datasets """
        self.dataSetNames = self.dataSets.keys()
    
    def getParameters(self):
        """ returns the lmfit parameters object for the fit function"""
        return lmfit.Parameters({_.name:_.parameter for _ in self.parametersList })
    
    
    def _setCalculatedValues(self, modelFitResult):
        """updates calculated values with calculated argument """
        parametersResult = modelFitResult.params
        for variable in self.parametersList:
            variable.calculatedValue = parametersResult[variable.name].value

            
    def _setCalculatedValuesErrors(self, modelFitResult):
        """given the covariance matrix returned by scipy optimize fit
        convert this into stdeviation errors for parameters list and updated
        the stdevError attribute of variables"""
        parametersResult = modelFitResult.params
        for variable in self.parametersList:
            variable.stdevError = parametersResult[variable.name].stderr    
    
    def fit(self):
        params = self.getParameters()
        x,y = self.dataSets[self.selectedDataSet]
        self.modelFitResult = self.model_.model.fit(y, x=x, params=params)
        #self.modelFitResult = self.model_.model.fit(y, x=x, params=params,iter_cb=self.getFitCallback(time.time()))#can also pass fit_kws= {"maxfev":1000}
        self._setCalculatedValues(self.modelFitResult)#update fitting paramters final values
        self._setCalculatedValuesErrors(self.modelFitResult)
        self.modelFitMessage = self.modelFitResult.message
        if not self.modelFitResult.success:
            logger.error("failed to fit in LogFilePlotFitter")
        self.isFitted=True
        if self.logFilePlotReference is not None:
            self.logFilePlotReference.plotFit()

    def getFitCallback(self, startTime):
        """returns the callback function that is called at every iteration of fit to check if it 
        has been running too long"""
        def fitCallback(params, iter, resid, *args, **kws):
            """check the time and compare to start time """
            if time.time()-startTime>self.maxFitTime:
                return True
        return fitCallback
    
    def _fitButton_fired(self):
        self.fit()
        
    def _usePreviousFitButton_fired(self):
        """update the initial guess value with the fitted values of the parameter """
        for parameter in self.parametersList:
            parameter.initialValue = parameter.calculatedValue
            
    def _guessButton_fired(self):
        """calls _guess function and updates initial fit values accordingly """
        print "guess button clicked"
        if self.model_.guessFunction is None:
            print "attempted to guess initial values but no guess function is defined. returning without changing initial values"
            logger.error("attempted to guess initial values but no guess function is defined. returning without changing initial values")
            return
        logger.info("attempting to guess initial values using %s" % self.model_.guessFunction.__name__)
        xs,ys = self.dataSets[self.selectedDataSet]
        guessDictionary = self.model_.guessFunction(xs,ys)
        logger.debug("guess results = %s" % guessDictionary)
        print "guess results = %s" % guessDictionary
        for parameterName, guessValue in guessDictionary.iteritems():
            for parameter in self.parametersList:
                if parameter.name == parameterName:
                    parameter.initialValue = guessValue
            
        
    def _saveFitButton_fired(self):
        saveFolder, filename = os.path.split(self.logFilePlotReference.logFile)
        parametersResult = self.modelFitResult.params
        logFileName = os.path.split(saveFolder)[1]
        functionName = self.model_.function.__name__
        saveFileName = os.path.join(saveFolder, logFileName+"-"+functionName+"-fitSave.csv")

        #parse selected data set name to get column names
        #selectedDataSet is like "aaaa=1.31 bbbb=1.21"
        seriesColumnNames = [seriesString.split("=")[0] for seriesString in self.selectedDataSet.split(" ")]

        if not os.path.exists(saveFileName):#create column names
            with open(saveFileName, "ab+") as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(seriesColumnNames+[variable.name for variable in self.parametersList]+[variable.name+"-tolerance" for variable in self.parametersList])
        with open(saveFileName, "ab+") as csvFile:#write save to file
            writer = csv.writer(csvFile)      
            seriesValues = [seriesString.split("=")[1] for seriesString in self.selectedDataSet.split(" ")]#values of the legend keys so you know what fit was associated with
            writer.writerow(seriesValues+[parametersResult[variable.name].value for variable in self.parametersList]+[parametersResult[variable.name].stderr for variable in self.parametersList])



    def _cycleAndFitButton_fired(self):
        logger.info("cycle and fit button pressed")
        self._fitButton_fired()
        self._saveFitButton_fired()
        self._usePreviousFitButton_fired()
        currentDataSetIndex = self.dataSets.keys().index(self.selectedDataSet)
        self.selectedDataSet = self.dataSets.keys()[currentDataSetIndex+1]
        
    def _statisticsButton_fired(self):
        from scipy.stats import pearsonr
        xs,ys = self.dataSets[self.selectedDataSet]
        mean = scipy.mean(ys)
        median = scipy.median(ys)
        std = scipy.std(ys)
        minimum = scipy.nanmin(ys)
        maximum = scipy.nanmax(ys)
        peakToPeak = maximum - minimum
        pearsonCorrelation = pearsonr(xs,ys)
        resultString = "mean=%G , median=%G stdev =%G\nmin=%G,max=%G, pk-pk=%G\nPearson Correlation=(%G,%G)\n(stdev/mean)=%G"%(mean,median,std,minimum,maximum,peakToPeak,pearsonCorrelation[0],pearsonCorrelation[1],std/mean)
        self.statisticsString = resultString
        
        

if __name__=="__main__":
    lfpf= LogFilePlotFitter()
    x = scipy.linspace(-10,10)
    y = fittingFunctions.gaussian(x, 10.,5.,0.1,0.1) + scipy.random.normal(0, 0.2, len(x))
    lfpf.setFitData("noisyGauss",x,y)
    lfpf.startFitTime = time.time()
    modelFitResult = lfpf.model_.model.fit(y, x=x, params=lfpf.getParameters(),iter_cb=lfpf.getFitCallback(time.time()))
    lfpf.configure_traits()