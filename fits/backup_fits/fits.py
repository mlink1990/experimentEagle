# -*- coding: utf-8 -*-
"""
Created on Sat Apr 04 14:33:56 2015

@author: tharrison
"""

import enthought.traits.api as traits
import enthought.traits.ui.api as traitsui
import logging
import os
import csv
import scipy
import scipy.optimize
import scipy.integrate
import threading
import physicsProperties
import processors#used to extract processor options that were used during the fit
import plotObjects.logLibrarian
import time
import lmfit


import shutil
import importlib
from pyface.api import FileDialog
import pyface.constant


logger=logging.getLogger("ExperimentEagle.fits")

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
                        ), kind="subpanel"
                        )
                        
class CalculatedParameter(traits.HasTraits):
    """represents a number calculated from a fit. e.g. atom number """
    name = traits.Str
    value = traits.Float

    
    traits_view = traitsui.View(
                        traitsui.HGroup(
                            traitsui.Item("name", show_label=False, style="readonly", resizable=True),
                            traitsui.Item("value",show_label=False,format_str="%G", style="readonly", resizable=True)
                            
                                )
                            )


#class FitVariablesList(traits.HasTraits):
#    """A list of variables"""
#    variablesList = traits.List(FitVariable)
#    traits_view = traitsui.View(
#                    traitsui.VGroup(
#                        traitsui.Item("variablesList", editor=traitsui.ListEditor(style="custom"), show_label=False)        
#                                    )
#                                )
     
class ColumnEditor ( traits.HasTraits ):
    """ Define the main column Editor class. Complex part is handled 
    by get columns function below that defines the view and editor."""
    columns = traits.List(  )
    numberOfColumns = traits.Int()
    selectAllButton = traits.Button('Select/Deselect All')
    selectDeselectBool = traits.Bool(True)
    
    def _selectAllButton_fired(self):
        if self.selectDeselectBool:
            self.columns=[]
            self.selectDeselectBool= not self.selectDeselectBool
        else:
            self.columns=range(0, self.numberOfColumns)
            self.selectDeselectBool= not self.selectDeselectBool
    

class FitException(Exception):
    
    def __init__(self, *args, **kwargs):
        super(FitException,self).__init__( *args, **kwargs)


class FitThread(threading.Thread):
    """wrapper for performing the scipy.optimise curve fit in a seperate
    thread. Useful as sometimes fits can take several seconds and we want the
    gui to keep responding. FitThread has a property called fitReference which
    is a reference to the fit object so that it can call the necesary functions"""
    def run(self):
        logger.info( "starting fitting thread")
        try:
            modelFitResult = self.fitReference._perform_fit()#this call can take a long time depending on fit parameters etc.
            self.fitReference.mostRecentModelResult = modelFitResult
            self.fitReference._setCalculatedValues(modelFitResult)#update fitting paramters final values
            self.fitReference._setCalculatedValuesErrors(modelFitResult)#update fitting parameters errors
            self.fitReference.fitting=False
            self.fitReference.fitted=True 
            self.fitReference.fittingStatus = modelFitResult.message
            self.fitReference.deriveCalculatedParameters()
            #when the fit finishes there are several options to check and actions to perform
            if self.fitReference.autoGuessBool:
                logger.info("auto guess bool is true so replacing guess values with calculated values to increase speed of next fit")
                self.fitReference._setInitialValues(self.fitReference._getCalculatedValues())
            #could improve so that this is handled by an event in the EAGLE #TODO!!!
            if self.fitReference.autoDrawBool:
                logger.info("auto draw bool is true so using the rerefernce to imageInspector bool to call the function to draw the fit as contours")
                self.fitReference.imageInspectorReference.addFitPlot(self.fitReference)
            if self.fitReference.logBool:
                logger.info("logging the fit")
                self.fitReference._log_fit()
            logger.info("saving last fit results to a separate text file")
            self.fitReference.saveLastFit()
            if self.fitReference.autoSizeBool:
                #physics is already updated before fitting so we can now check if TOF time was the value for setting the size
                #default is 0.11ms
                if self.fitReference.physics.timeOfFlightTimems == self.fitReference.physics.inTrapSizeTOFTimems:
                    logger.info("DETECTED AUTOMATICALLY THAT THIS MEASUREMENT WAS A SIZE CALIBRATION")
                    logger.info("updating intrapSizeX, Y in physics accordingly")
                    self.fitReference._setSizeButton_fired()#simulate user pressing the setSize button
#            logFilePlotObject = self.fitReference.imageInspectorReference.logFilePlotObject
#            if logFilePlotObject.autoRefresh and logFilePlotObject.logFilePlotBool:
#                try:
#                    logFilePlotObject.refreshPlot()
#                except Exception as e:
#                    logger.error( "failed to update log plot -  %s...." % e.message)
        except KeyboardInterrupt as e:
            raise e
        except FitException as e:
            logger.warning( "A fit ran out of time and was cancelled by iter_cb callback")
            self.fitReference.fittingStatus = self.fitReference.timeExceededStatus
        except Exception as e:
            logger.error( "failed to finish fit - %s - %s - %s...." % (type(e),e.args,e.message))
            self.fitReference.fittingStatus = self.fitReference.failedFitStatus
            return
                           
class Fit(traits.HasTraits):
    
    name = traits.Str(desc="name of fit")
    function = traits.Str(desc="function we are fitting with all parameters")
    variablesList = traits.List(Parameter)
    calculatedParametersList = traits.List(CalculatedParameter)
    xs = None # will be a scipy array
    ys = None # will be a scipy array
    zs = None # will be a scipy array
    performFitButton = traits.Button("Perform Fit")
    getInitialParametersButton = traits.Button("Guess Initial Values")
    usePreviousFitValuesButton = traits.Button("Use Previous Fit")
    drawRequestButton = traits.Button("Draw Fit")
    setSizeButton = traits.Button("Set Initial Size")
    chooseVariablesButtons= traits.Button("choose logged variables")
    logLibrarianButton = traits.Button("librarian")
    logLastFitButton=traits.Button("log current fit")
    removeLastFitButton=traits.Button("remove last fit")
    autoFitBool = traits.Bool(False, desc = "Automatically perform this Fit with current settings whenever a new image is loaded")    
    autoGuessBool = traits.Bool(False, desc = "Whenever a fit is completed replace the guess values with the calculated values (useful for increasing speed of the next fit)")    
    autoDrawBool = traits.Bool(False, desc = "Once a fit is complete update the drawing of the fit or draw the fit for the first time")
    autoSizeBool = traits.Bool(False, desc = "If TOF variable is read from latest XML and is equal to 0.11ms (or time set in Physics) then it will automatically update the physics sizex and sizey with the Sigma x and sigma y from the gaussian fit")
    logBool = traits.Bool(False,desc = "Log the calculated and fitted values with a timestamp" )
    logName = traits.String(desc="name of the scan - will be used in the folder name")
    logDirectory = os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry","Data","eagleLogs")
    latestSequence = os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry","Experiment Control And Software","currentSequence","latestSequence.xml")
    
    logFile = traits.File(desc = "file path of logFile")
    
    logAnalyserBool = traits.Bool(False, desc = "only use log analyser script when True")
    logAnalysers = []#list containing full paths to each logAnalyser file to run
    logAnalyserDisplayString = traits.String(desc = "comma separated read only string that is a list of all logAnalyser python scripts to run. Use button to choose files")    
    logAnalyserSelectButton = traits.Button("sel. analyser", image = '@icons:function_node', style="toolbar" )
    xmlLogVariables = []
    imageInspectorReference = None#will be a reference to the image inspector
    fitting = traits.Bool(False)#true when performing fit
    fitted = traits.Bool(False)#true when current data displayed has been fitted
    fitSubSpace = traits.Bool(False)#true when current data displayed has been fitted
    startX = traits.Int
    startY = traits.Int
    endX = traits.Int
    endY = traits.Int
    fittingStatus = traits.Str()
    fitThread = None
    fitTimeLimit = traits.Float(10.0, desc="Time limit in seconds for fitting function. Only has an effect when fitTimeLimitBool is True")
    fitTimeLimitBool = traits.Bool(True, desc="If True then fitting functions will be limited to time limit defined by fitTimeLimit ")
    physics = traits.Instance(physicsProperties.physicsProperties.PhysicsProperties)
    #status strings
    notFittedForCurrentStatus = "Not Fitted for Current Image"
    fittedForCurrentImageStatus = "Fit Complete for Current Image"
    currentlyFittingStatus = "Currently Fitting..."
    failedFitStatus = "Failed to finish fit. See logger"
    timeExceededStatus = "Fit exceeded user time limit"
    
    lmfitModel = traits.Instance(lmfit.Model)#reference to the lmfit model  must be initialised in subclass
    mostRecentModelResult = None # updated to the most recent ModelResult object from lmfit when a fit thread is performed
    
    fitSubSpaceGroup = traitsui.VGroup(
                            traitsui.Item("fitSubSpace", label="Fit Sub Space", resizable=True),
                            traitsui.VGroup(
                                traitsui.HGroup(traitsui.Item("startX", resizable=True),traitsui.Item("startY", resizable=True)),
                                traitsui.HGroup(traitsui.Item("endX", resizable=True),traitsui.Item("endY", resizable=True)),
                                visible_when="fitSubSpace"
                            ), label="Fit Sub Space", show_border=True
                        )    
    
    generalGroup = traitsui.VGroup(
                        traitsui.Item("name",label="Fit Name", style="readonly",resizable=True),
                        traitsui.Item("function",label="Fit Function", style="readonly",resizable=True),
                        fitSubSpaceGroup, label="Fit",                   
                        show_border=True)
                        
    
    variablesGroup = traitsui.VGroup( traitsui.Item("variablesList", editor=traitsui.ListEditor(style="custom"), show_label=False,resizable=True), show_border=True, label="parameters")         

    derivedGroup = traitsui.VGroup(traitsui.Item("calculatedParametersList", editor=traitsui.ListEditor(style="custom"), show_label=False,resizable=True), show_border=True, label="derived values")    
    
    
    
    buttons = traitsui.VGroup(
        traitsui.HGroup(traitsui.Item("autoFitBool", label="Auto fit?", resizable=True),traitsui.Item("performFitButton", show_label=False, resizable=True)),
        traitsui.HGroup(traitsui.Item("autoGuessBool", label="Auto guess?", resizable=True),traitsui.Item("getInitialParametersButton", show_label=False, resizable=True)),
        traitsui.HGroup(traitsui.Item("autoDrawBool",label="Auto draw?", resizable=True),traitsui.Item("drawRequestButton", show_label=False, resizable=True)),
        traitsui.HGroup(traitsui.Item("autoSizeBool",label="Auto size?", resizable=True),traitsui.Item("setSizeButton", show_label=False, resizable=True)),
        traitsui.HGroup(traitsui.Item("usePreviousFitValuesButton", show_label=False, resizable=True))
        )
        
    logGroup = traitsui.VGroup(
                traitsui.HGroup(traitsui.Item("logBool", resizable=True),traitsui.Item("chooseVariablesButtons", show_label=False, resizable=True)),
                traitsui.HGroup(traitsui.Item("logName", resizable=True)),
                traitsui.HGroup(traitsui.Item("removeLastFitButton", show_label=False, resizable=True),traitsui.Item("logLastFitButton", show_label=False, resizable=True)),
                traitsui.HGroup(traitsui.Item("logAnalyserBool", label = "analyser?", resizable=True),traitsui.Item("logAnalyserDisplayString", show_label=False, style="readonly",resizable=True),traitsui.Item("logAnalyserSelectButton",show_label=False, resizable=True)),
                     label= "Logging", show_border=True)
    
    actionsGroup = traitsui.VGroup(traitsui.Item("fittingStatus", style="readonly", resizable=True),logGroup, buttons, label="Fit Actions", show_border=True)
    traits_view = traitsui.View(
                        traitsui.VGroup(generalGroup, variablesGroup,derivedGroup,actionsGroup), kind="subpanel"
                    )

    def __init__(self, **traitsDict):
        super(Fit, self).__init__(**traitsDict)
        self.startX = 0
        self.startY = 0
        self.lmfitModel = lmfit.Model(self.fitFunc)
        
    def _set_xs(self,xs):
        self.xs = xs
        
    def _set_ys(self,ys):
        self.ys = ys
            
    def _set_zs(self,zs):
        self.zs = zs
        
    def _fittingStatus_default(self):
        return self.notFittedForCurrentStatus

    def _getInitialValues(self):
        """returns ordered list of initial values from variables List """
        return [_.initialValue for _ in self.variablesList]

    def _getParameters(self):
        """creates an lmfit parameters object based on the user input in variablesList """
        return lmfit.Parameters({_.name:_.parameter for _ in self.variablesList })

    def _getCalculatedValues(self):
        """returns ordered list of fitted values from variables List """
        return [_.calculatedValue for _ in self.variablesList]

    def _intelligentInitialValues(self):
        """If possible we can auto set the initial parameters to intelligent guesses user can always overwrite them """
        self._setInitialValues(self._getIntelligentInitialValues())
        
    def _get_subSpaceArrays(self):
        """returns the arrays of the selected sub space. If subspace is not
        activated then returns the full arrays"""
        if self.fitSubSpace:
            xs = self.xs[self.startX:self.endX]
            ys = self.ys[self.startY:self.endY]
            logger.info("xs array sliced length %s " % (xs.shape) )
            logger.info("ys array sliced length %s  " % (ys.shape) )
            zs = self.zs[self.startY:self.endY,self.startX:self.endX]            
            logger.info("zs sub space array %s,%s " % (zs.shape) )
            
            return xs,ys,zs
        else:
            return self.xs,self.ys,self.zs
            
    def _getIntelligentInitialValues(self):
        """If possible we can auto set the initial parameters to intelligent guesses user can always overwrite them """
        logger.debug("Dummy function should not be called directly")
        return
        #in python this should be a pass statement. I.e. user has to overwrite this
        
    def fitFunc(self,data, *p):
        """Function that we are trying to fit to. """
        logger.error("Dummy function should not be called directly")
        return
        #in python this should be a pass statement. I.e. user has to overwrite this
        
    def _setCalculatedValues(self, modelFitResult):
        """updates calculated values with calculated argument """
        parametersResult = modelFitResult.params
        for variable in self.variablesList:
            variable.calculatedValue = parametersResult[variable.name].value

            
    def _setCalculatedValuesErrors(self, modelFitResult):
        """given the covariance matrix returned by scipy optimize fit
        convert this into stdeviation errors for parameters list and updated
        the stdevError attribute of variables"""
        parametersResult = modelFitResult.params
        for variable in self.variablesList:
            variable.stdevError = parametersResult[variable.name].stderr

            
    def _setInitialValues(self, guesses):
        """updates calculated values with calculated argument """
        c = 0
        for variable in self.variablesList:
            variable.initialValue = guesses[c]
            c+=1

    def deriveCalculatedParameters(self):
        """Wrapper for subclass definition of deriving calculated parameters
        can put more general calls in here"""
        if self.fitted:
            self._deriveCalculatedParameters()
        
    def _deriveCalculatedParameters(self):
        """Should be implemented by subclass. should update all variables in calculate parameters list"""
        logger.error("Should only be called by subclass")
        return 
        
    def _fit_routine(self):
        """This function performs the fit in an appropriate thread and 
        updates necessary values when the fit has been performed"""
        self.fitting=True
        if self.fitThread and self.fitThread.isAlive():
            logger.warning("Fitting is already running. You should wait till this fit has timed out before a new thread is started....")
            #logger.warning("I will start a new fitting thread but your previous thread may finish at some undetermined time. you probably had bad starting conditions :( !")
            return
        self.fitThread = FitThread()#new fitting thread
        self.fitThread.fitReference = self
        self.fitThread.isCurrentFitThread = True # user can create multiple fit threads on a particular fit but only the latest one will have an effect in the GUI
        self.fitThread.start() 
        self.fittingStatus = self.currentlyFittingStatus
            
    def _perform_fit(self):
        """Perform the fit using scipy optimise curve fit.
        We must supply x and y as one argument and zs as anothger. in the form
        xs: 0 1 2 0 1 2 0 
        ys: 0 0 0 1 1 1 2
        zs: 1 5 6 1 9 8 2
        Hence the use of repeat and tile in  positions and unravel for zs
        initially xs,ys is a linspace array and zs is a 2d image array
        """
        if self.xs is None or self.ys is None or self.zs is None:
            logger.warning("attempted to fit data but had no data inside the Fit object. set xs,ys,zs first")
            return ([],[])
        params = self._getParameters()  
        if self.fitSubSpace:#fit only the sub space
            #create xs, ys and zs which are appropriate slices of the arrays
            xs,ys,zs = self._get_subSpaceArrays()
        else:#fit the whole array of data (slower)
            xs,ys,zs = self.xs,self.ys, self.zs
        positions = scipy.array([scipy.tile(xs, len(ys)), scipy.repeat(ys, len(xs))])#for creating data necessary for gauss2D function
        if self.fitTimeLimitBool:
            modelFitResult = self.lmfitModel.fit(scipy.ravel(zs), positions=positions, params=params, iter_cb = self.getFitCallback(time.time()))        
        else:#no iter callback
            modelFitResult = self.lmfitModel.fit(scipy.ravel(zs), positions=positions, params=params)
        return modelFitResult
        
    def getFitCallback(self, startTime):
        """returns the callback function that is called at every iteration of fit to check if it 
        has been running too long"""
        def fitCallback(params, iter, resid, *args, **kws):
            """check the time and compare to start time """
            if time.time()-startTime>self.fitTimeLimit:
                raise FitException("Fit time exceeded user limit")
        return fitCallback
        
        
    def _performFitButton_fired(self):
        self._fit_routine()
        
    def _getInitialParametersButton_fired(self):
        self._intelligentInitialValues()
    
    def _drawRequestButton_fired(self):
        """tells the imageInspector to try and draw this fit as an overlay contour plot"""
        self.imageInspectorReference.addFitPlot(self)
        
    def _setSizeButton_fired(self):
        """use the sigmaX and sigmaY from the current fit to overwrite the 
        inTrapSizeX and inTrapSizeY parameters in the Physics Instance"""
        self.physics.inTrapSizeX = abs(self.sigmax.calculatedValue)
        self.physics.inTrapSizeY = abs(self.sigmay.calculatedValue)
        
        
    def _getFitFuncData(self):
        """if data has been fitted, this returns the zs data for the ideal
        fitted function using the calculated paramters"""
        positions = [scipy.tile(self.xs, len(self.ys)), scipy.repeat(self.ys, len(self.xs))]#for creating data necessary for gauss2D function
        zsravelled = self.fitFunc(positions, *self._getCalculatedValues())
        return zsravelled.reshape(self.zs.shape)
        

    def _logAnalyserSelectButton_fired(self):
        """open a fast file editor for selecting many files """
        fileDialog = FileDialog(action="open files") 
        fileDialog.open()
        if fileDialog.return_code == pyface.constant.OK:
            self.logAnalysers = fileDialog.paths
            logger.info("selected log analysers: %s " % self.logAnalysers)
        self.logAnalyserDisplayString = str([os.path.split(path)[1] for path in self.logAnalysers])

    def runSingleAnalyser(self, module):
        """runs the logAnalyser module calling the run function and returns the 
        columnNames and values as a list"""
        exec("import logAnalysers.%s as currentAnalyser" % module )
        reload(currentAnalyser)#in case it has changed..#could make this only when user requests
        #now the array also contains the raw image as this may be different to zs if you are using a processor
        if hasattr(self.imageInspectorReference,"rawImage"):
            rawImage = self.imageInspectorReference.rawImage
        else:
            rawImage = None
        return currentAnalyser.run([self.xs,self.ys,self.zs,rawImage], self.physics.variables, self.variablesList, self.calculatedParametersList)
        
        
    def runAnalyser(self):
        """ if logAnalyserBool is true we perform runAnalyser at the end of _log_fit
        runAnalyser checks that logAnalyser exists and is a python script with a valid run()function
        it then performs the run method and passes to the run function:
        -the image data as a numpy array
        -the xml variables dictionary
        -the fitted paramaters
        -the derived values"""
        for logAnalyser in self.logAnalysers:
            if not os.path.isfile(logAnalyser):
                logger.error("attempted to runAnalyser but could not find the logAnalyser File: %s" % logAnalyser)
                return
        #these will contain the final column names and values
        finalColumns = []
        finalValues = []
        #iterate over each selected logAnalyser get the column names and values and add them to the master lists
        for logAnalyser in self.logAnalysers:
            directory, module = os.path.split(logAnalyser)
            module,ext = os.path.splitext(module)
            if ext!= ".py":
                logger.error("file was not a python module. %s" % logAnalyser)
            else:
                columns, values = self.runSingleAnalyser(module)
                finalColumns.extend(columns)
                finalValues.extend(values)
        return finalColumns, finalValues                

    def mostRecentModelFitReport(self):
        """returns the lmfit fit report of the most recent 
        lmfit model results object"""
        if self.mostRecentModelResult is not None:
            return lmfit.fit_report(self.mostRecentModelResult)+"\n\n"
        else:
            return "No fit performed"
        
    def getCalculatedParameters(self):
        """useful for print returns tuple list of calculated parameter name and value """
        return [(_.name,_.value) for _ in self.calculatedParametersList]
                
            
    def _log_fit(self):
        
        if self.logName=="":
            logger.warning("no log file defined. Will not log")
            return
        #generate folders if they don't exist
        logFolder = os.path.join(self.logDirectory,self.logName)
        if not os.path.isdir(logFolder):
            logger.info("creating a new log folder %s" % logFolder)
            os.mkdir(logFolder)

        imagesFolder = os.path.join(logFolder,"images" )
        if not os.path.isdir(imagesFolder):
            logger.info("creating a new images Folder %s" % imagesFolder)
            os.mkdir(imagesFolder)
            
        commentsFile = os.path.join(logFolder,"comments.txt" )
        if not os.path.exists(commentsFile):
            logger.info("creating a comments file %s" % commentsFile)
            open(commentsFile,"a+").close()#create a comments file in every folder!
        
        firstSequenceCopy = os.path.join(logFolder,"copyOfInitialSequence.ctr" )
        if not os.path.exists(firstSequenceCopy):
            logger.info("creating a copy of the first sequence %s -> %s" % (self.latestSequence, firstSequenceCopy))
            shutil.copy(self.latestSequence, firstSequenceCopy)
        
        if self.imageInspectorReference.model.imageMode == "process raw image":#if we are using a processor, save the details of the processor used to the log folder
            processorParamtersFile = os.path.join(logFolder, "processorOptions.txt")
            processorPythonScript = os.path.join(logFolder, "usedProcessor.py")#TODO!
            if not os.path.exists(processorParamtersFile):
                with open(processorParamtersFile,"a+") as processorParamsFile:
                    string = str(self.imageInspectorReference.model.chosenProcessor)+"\n"
                    string += str(self.imageInspectorReference.model.processor.optionsDict)
                    processorParamsFile.write(string)
            
            
        logger.debug("finished all checks on log folder")
        #copy current image
        try:
            shutil.copy(self.imageInspectorReference.selectedFile, imagesFolder)
        except IOError as e:
            logger.error("Could not copy image. Got IOError: %s " % e.message)
        except Exception as e:
            logger.error("Could not copy image. Got %s: %s " % (type(e),e.message))
            raise e
        logger.info("copying current image")
        self.logFile = os.path.join(logFolder, self.logName+".csv")
        
        #analyser logic
        if self.logAnalyserBool:#run the analyser script as requested
            logger.info("log analyser bool enabled... will attempt to run analyser script")
            analyserResult = self.runAnalyser()
            logger.info("analyser result = %s " %  list(analyserResult))
            if analyserResult is None:
                analyserColumnNames = []
                analyserValues = []
                #analyser failed. continue as if nothing happened
            else:
                analyserColumnNames, analyserValues = analyserResult
        else:#no analyser enabled
            analyserColumnNames = []
            analyserValues = []
                        
        if not os.path.exists(self.logFile):
            variables = [_.name for _ in self.variablesList]
            calculated = [_.name for _ in self.calculatedParametersList]
            times = ["datetime", "epoch seconds"]
            info = ["img file name"]
            xmlVariables = self.xmlLogVariables
            columnNames = times+info+variables+calculated+xmlVariables+analyserColumnNames
            with open(self.logFile, 'ab+') as logFile: # note use of binary file so that windows doesn't write too many /r
                    writer = csv.writer(logFile)
                    writer.writerow(columnNames)
        #column names already exist so...
        logger.debug("copying current image")
        variables = [_.calculatedValue for _ in self.variablesList]
        calculated = [_.value for _ in self.calculatedParametersList]
        now = time.time()#epoch seconds
        timeTuple = time.localtime(now)
        date=time.strftime("%Y-%m-%dT%H:%M:%S", timeTuple)
        times = [date,now]
        info = [self.imageInspectorReference.selectedFile]
        xmlVariables = [self.physics.variables[varName] for varName in self.xmlLogVariables]
        data = times+info+variables+calculated+xmlVariables+analyserValues
        
            
        with open(self.logFile, 'ab+') as logFile:
                writer = csv.writer(logFile)
                writer.writerow(data)
                
    def _logLastFitButton_fired(self):
        """logs the fit. User can use this for non automated logging. i.e. log
        particular fits"""
        self._log_fit()
        
    def _removeLastFitButton_fired(self):
        """removes the last line in the log file """
        logFolder = os.path.join(self.logDirectory,self.logName )
        self.logFile = os.path.join(logFolder, self.logName+".csv")
        if self.logFile=="":
            logger.warning("no log file defined. Will not log")
            return
        if not os.path.exists(self.logFile):
            logger.error("cant remove a line from a log file that doesn't exist")
        with open(self.logFile, 'r') as logFile:
            lines = logFile.readlines()
        with open(self.logFile, 'wb') as logFile:
            logFile.writelines(lines[:-1])
            
    def saveLastFit(self):
        """saves result of last fit to a txt/csv file. This can be useful for live analysis
        or for generating sequences based on result of last fit"""
        try:
            with open(self.imageInspectorReference.cameraModel+"-"+self.physics.species+"-"+"lastFit.csv", "wb") as lastFitFile:
                writer = csv.writer(lastFitFile)
                writer.writerow(["time",time.time()])
                for variable in self.variablesList:
                    writer.writerow([variable.name,variable.calculatedValue])
                for variable in self.calculatedParametersList:
                    writer.writerow([variable.name,variable.value])
        except Exception as e:
            logger.error("failed to save last fit to text file. message %s " % e.message)
        
    def _chooseVariablesButtons_fired(self):
        self.xmlLogVariables = self.chooseVariables()
        
    def _usePreviousFitValuesButton_fired(self):
        """update the guess initial values with the value from the last fit """
        logger.info("use previous fit values button fired. loading previous initial values")
        self._setInitialValues(self._getCalculatedValues())
        
    def chooseVariables(self):
        """Opens a dialog asking user to select columns from a data File that has
        been selected. THese are then returned as a string suitable for Y cols input"""
        columns = self.physics.variables.keys()
        columns.sort()
        values = zip(range(0, len(columns)), columns)
        
        checklist_group = traitsui.Group('10', # insert vertical space
                                        traitsui.Label('Select the additional variables you wish to log'),
                                        traitsui.UItem( 'columns', style = 'custom',editor = traitsui.CheckListEditor(
                                                           values = values,
                                                           cols   = 6 )),
                                        traitsui.UItem('selectAllButton')
                                       )
        
        traits_view = traitsui.View(
                                    checklist_group,
                                    
                                    title     = 'CheckListEditor',
                                    buttons   = [ 'OK' ],
                                    resizable = True,
                                    kind='livemodal'
                                    )
    
        col = ColumnEditor( numberOfColumns = len(columns) )
        try:
            col.columns = [columns.index(varName) for varName in self.xmlLogVariables]
        except Exception as e:
            logger.error("couldn't selected correct variable names. Returning empty selection")
            logger.error("%s " % e.message)
            col.columns = []
        col.edit_traits(view=traits_view)
        logger.debug("value of columns selected = %s ", col.columns)
        logger.debug("value of columns selected = %s ", [columns[i] for i in col.columns])        
        return [columns[i] for i in col.columns]
        

    def _logLibrarianButton_fired(self):       
        """opens log librarian for current folder in logName box. """
        logFolder = os.path.join(self.logDirectory,self.logName)
        if not os.path.isdir(logFolder):
            logger.error("cant open librarian on a log that doesn't exist.... Could not find %s" % logFolder)
            return
        librarian = plotObjects.logLibrarian.Librarian(logFolder = logFolder)
        librarian.edit_traits()

if __name__=="__main__":
    import fitGaussian
    wx = Parameter(name="wx", initialValue=1.0)
    wy = Parameter(name="wy", initialValue=2.0)
    stdx = Parameter(name="stdx", initialValue=3.0)
    stdy = Parameter(name="stdy", initialValue=4.0)
    variablesList=[wx,wy,stdx,stdy]    
    n = CalculatedParameter(name="N", value=1.0E7)
    fit = fitGaussian.GaussianFit()
    fit.configure_traits()