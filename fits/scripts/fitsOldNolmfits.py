# -*- coding: utf-8 -*-
"""
Created on Sat Apr 04 14:33:56 2015

@author: tharrison
"""

import enthought.chaco.api as chaco
import enthought.traits.api as traits
import enthought.traits.ui.api as traitsui
import logging
import os
import csv
import scipy
import scipy.optimize
import threading
import physicsProperties
import time

logger=logging.getLogger("ExperimentEagle.fits")

class FitVariable(traits.HasTraits):
    """represents a variable in a fit. E.g. the standard deviation in a gaussian
    fit"""
    name = traits.Str
    initialValue = traits.Float
    calculatedValue = traits.Float
    stdevError = traits.Float
    
    
    traits_view = traitsui.View(
                        traitsui.HGroup(
                            traitsui.Item("name", show_label=False, style="readonly",width=0.2, resizable=True),
                            traitsui.Item("initialValue",label="initial", show_label=True, resizable=True),
                            traitsui.Item("calculatedValue",label="calculated",show_label=True,format_str="%G", style="readonly",width=0.2, resizable=True),
                            traitsui.Item("stdevError",show_label=False,format_str=u"\u00B1%G", style="readonly", resizable=True)
                                )
                            )

class CalculatedParameter(traits.HasTraits):
    """represents a number calculated from a fit. e.g. atom number """
    name = traits.Str
    value = traits.Float

    
    traits_view = traitsui.View(
                        traitsui.HGroup(
                            traitsui.Item("name", show_label=False, style="readonly"),
                            traitsui.Item("value",show_label=False,format_str="%G", style="readonly")
                            
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
     

class FitThread(threading.Thread):
    """wrapper for performing the scipy.optimise curve fit in a seperate
    thread. Useful as sometimes fits can take several seconds and we want the
    gui to keep responding. FitThread has a property called fitReference which
    is a reference to the fit object so that it can call the necesary functions"""
    def run(self):
        logger.info( "starting fitting thread")
        try:
            params, cov = self.fitReference._perform_fit()
            
            self.fitReference._setCalculatedValues(params)#update fitting paramters final values
            self.fitReference._setCalculatedValuesErrors(cov)#update fitting parameters errors
            self.fitReference.fitting=False
            self.fitReference.fitted=True 
            self.fitReference.fittingStatus = self.fitReference.fittedForCurrentImageStatus
            self.fitReference.deriveCalculatedParameters()
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
        except Exception as e:
            logger.error( "failed to finish fit -  %s...." % e.message)
            self.fitReference.fittingStatus = self.fitReference.failedFitStatus
            return 
                           
class Fit(traits.HasTraits):
    
    name = traits.Str(desc="name of fit")
    function = traits.Str(desc="function we are fitting with all parameters")
    variablesList = traits.List(FitVariable)
    calculatedParametersList = traits.List(CalculatedParameter)
    xs = None # will be a scipy array
    ys = None # will be a scipy array
    zs = None # will be a scipy array
    performFitButton = traits.Button("Perform Fit")
    getInitialParametersButton = traits.Button("Guess Initial Values")
    drawRequestButton = traits.Button("Draw Fit")
    autoFitBool = traits.Bool(False, desc = "Automatically perform this Fit with current settings whenever a new image is loaded")    
    autoGuessBool = traits.Bool(False, desc = "Whenever a fit is completed replace the guess values with the calculated values (useful for increasing speed of the next fit)")    
    autoDrawBool = traits.Bool(False, desc = "Once a fit is complete update the drawing of the fit or draw the fit for the first time")
    logBool = traits.Bool(False,desc = "Log the calculated and fitted values with a timestamp" )
    logFile = traits.File(desc = "file path of logFile")    
    
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
    physics = traits.Instance(physicsProperties.PhysicsProperties)
    #status strings
    notFittedForCurrentStatus = "Not Fitted for Current Image"
    fittedForCurrentImageStatus = "Fit Complete for Current Image"
    currentlyFittingStatus = "Currently Fitting..."
    failedFitStatus = "Failed to finish fit. See logger"
    
    fitSubSpaceGroup = traitsui.VGroup(
                            traitsui.Item("fitSubSpace", label="Fit Sub Space"),
                            traitsui.VGroup(
                                traitsui.HGroup(traitsui.Item("startX"),traitsui.Item("startY")),
                                traitsui.HGroup(traitsui.Item("endX"),traitsui.Item("endY")),
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
        traitsui.HGroup(traitsui.Item("autoFitBool"),traitsui.Item("performFitButton")),
        traitsui.HGroup(traitsui.Item("autoGuessBool"),traitsui.Item("getInitialParametersButton")),
        traitsui.HGroup(traitsui.Item("autoDrawBool"),traitsui.Item("drawRequestButton"))
        )
        
    logGroup = traitsui.HGroup(traitsui.Item("logBool"),traitsui.Item("logFile", visible_when="logBool"), label= "Logging", show_border=True)
    
    actionsGroup = traitsui.VGroup(traitsui.Item("fittingStatus", style="readonly"),logGroup, buttons, label="Fit Actions", show_border=True)
    traits_view = traitsui.View(
                        traitsui.VGroup(generalGroup, variablesGroup,derivedGroup,actionsGroup)
                    )

    def __init__(self, **traitsDict):
        super(Fit, self).__init__(**traitsDict)
        self.startX = 0
        self.startY = 0
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

    def _getCalculatedValues(self):
        """returns ordered list of initial values from variables List """
        return [_.calculatedValue for _ in self.variablesList]


    def _log_fit(self):
        if self.logFile=="":
            logger.warning("no log file defined. Will not log")
            return
        if not os.path.exists(self.logFile):
            variables = [_.name for _ in self.variablesList]
            calculated = [_.name for _ in self.calculatedParametersList]
            times = ["datetime", "epoch seconds"]
            info = ["img file name"]
            columnNames = times+info+variables+calculated
            with open(self.logFile, 'a+') as logFile:
                    writer = csv.writer(logFile)
                    writer.writerow(columnNames)
        #column names already exist so...
        variables = [_.calculatedValue for _ in self.variablesList]
        calculated = [_.value for _ in self.calculatedParametersList]
        now = time.time()#epoch seconds
        timeTuple = time.localtime(now)
        date=time.strftime("%Y-%m-%dT%H:%M:%S", timeTuple)
        times = [date,now]
        info = [self.imageInspectorReference.selectedFile]
        data = times+info+variables+calculated
        with open(self.logFile, 'a+') as logFile:
                writer = csv.writer(logFile)
                writer.writerow(data)

    def _intelligentInitialValues(self):
        """If possible we can auto set the initial parameters to intelligent guesses user can always overwrite them """
        self._setInitialValues(self._getIntelligentInitialValues())
        
    def _get_subSpaceArrays(self):
        """returns the arrays of the selected sub space. If subspace is not
        activated then returns the full arrays"""
        if self.fitSubSpace:
            xs = self.xs[self.startX:self.endX]
            ys = self.ys[self.startY:self.endY]
            logger.debug("xs array sliced length %s " % (xs.shape) )
            logger.debug("ys array sliced length %s  " % (ys.shape) )
            zs = self.zs[self.startY:self.endY,self.startX:self.endX] 
            print zs
            print zs.shape            
            logger.debug("zs sub space array %s,%s " % (zs.shape) )
            
            return xs,ys,zs
        else:
            return self.xs,self.ys,self.zs
            
    
    def _getIntelligentInitialValues(self):
        """If possible we can auto set the initial parameters to intelligent guesses user can always overwrite them """
        logger.debug("Dummy function should not be called directly")
        return
        
    def fitFunc(self,data, *p):
        """Function that we are trying to fit to. """
        logger.error("Dummy function should not be called directly")
        return
        
    def _setCalculatedValues(self, calculated):
        """updates calculated values with calculated argument """
        c = 0
        for variable in self.variablesList:
            variable.calculatedValue = calculated[c]
            c+=1
            
    def _setCalculatedValuesErrors(self, covarianceMatrix):
        """given the covariance matrix returned by scipy optimize fit
        convert this into stdeviation errors for parameters list and updated
        the stdevError attribute of variables"""
        logger.debug("covariance matrix -> %s " % covarianceMatrix)
        parameterErrors = scipy.sqrt(scipy.diag(covarianceMatrix))
        logger.debug("parameterErrors  -> %s " % parameterErrors)
        c = 0
        for variable in self.variablesList:
            variable.stdevError = parameterErrors[c]
            c+=1
            
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
            logger.warning("Fitting is already running cannot kick off a new fit until it has finished!")
            return
        else:
            self.fitThread = FitThread()
            self.fitThread.fitReference = self
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
        p0 = self._getInitialValues()  
        if self.fitSubSpace:#fit only the sub space
            #create xs, ys and zs which are appropriate slices of the arrays
            xs,ys,zs = self._get_subSpaceArrays()
            positions = [scipy.tile(xs, len(ys)), scipy.repeat(ys, len(xs))]#for creating data necessary for gauss2D function
            params2D, cov2D = scipy.optimize.curve_fit(self.fitFunc, positions, scipy.ravel(zs), p0=p0 )
            chi2 = scipy.sum((scipy.ravel(zs) - self.fitFunc(positions, *params2D))**2/self.fitFunc(positions, *params2D))
            logger.debug("TEMPORARY ::: CHI^2 = %s " % chi2)
        else:#fit the whole array of data (slower)
            positions = [scipy.tile(self.xs, len(self.ys)), scipy.repeat(self.ys, len(self.xs))]#for creating data necessary for gauss2D function
            #note that it is necessary to ravel zs as curve_fit expects a flattened array
            params2D, cov2D = scipy.optimize.curve_fit(self.fitFunc, positions, scipy.ravel(self.zs), p0=p0 )
            
        return params2D, cov2D
        
    def _performFitButton_fired(self):
        self._fit_routine()
        
    def _getInitialParametersButton_fired(self):
        self._intelligentInitialValues()
    
    def _drawRequestButton_fired(self):
        """tells the imageInspector to try and draw this fit as an overlay contour plot"""
        self.imageInspectorReference.addFitPlot(self)
        
    def _getFitFuncData(self):
        """if data has been fitted, this returns the zs data for the ideal
        fitted function using the calculated paramters"""
        positions = [scipy.tile(self.xs, len(self.ys)), scipy.repeat(self.ys, len(self.xs))]#for creating data necessary for gauss2D function
        zsravelled = self.fitFunc(positions, *self._getCalculatedValues())
        return zsravelled.reshape(self.zs.shape)
        
class GaussianFit(Fit):
    """Sub class of Fit which implements a Guassian fit  """
    def __init__(self, **traitsDict):
        super(GaussianFit, self).__init__(**traitsDict)
        self.function = "(A*exp(-(x-x0)**2/(2.*sigmax**2)-(y-y0)**2/(2.*sigmay**2))+B)"
        self.name = "2D Gaussian"
        
        self.A = FitVariable(name="A")
        self.x0 = FitVariable(name="x0")
        self.sigmax = FitVariable(name="sigmax")
        self.y0 = FitVariable(name="y0")
        self.sigmay = FitVariable(name="sigmay")
        self.B = FitVariable(name="B")
        
        self.variablesList = [self.A,self.x0,self.sigmax,self.y0,self.sigmay,self.B ]
        
        self.N = CalculatedParameter(name="N", desc="Atom number calculated from gaussian fit")
        self.stdevX = CalculatedParameter(name="stdev X (um)", desc="stdev X of TOF cloud from gaussian fit")
        self.stdevY = CalculatedParameter(name="stdev Y (um)", desc="stdev Y of TOF cloud from gaussian fit")
        self.Tx = CalculatedParameter(name="Tx (uK)", desc="Temperature from time of flight in x direction. Uses in trap size defined in physics")
        self.Ty = CalculatedParameter(name="Ty (uK)", desc="Temperature from time of flight in x direction. Uses in trap size defined in physics")
        self.T = CalculatedParameter(name="T (uK)", desc="Average of Tx and Ty")
        self.aspectRatio = CalculatedParameter(name="Aspect Ratio", desc="ratio of sigma x to sigma y")
        
        
        self.criticalTemperature = CalculatedParameter(name="Critical Temperature (nK)", desc="Critical temperature from trapping frequency and atom number")  
        self.thermalDensity = CalculatedParameter(name="Thermal Cloud Density (cm^-3)", desc = "N/( 32 Pi (kb T / mu B')^3)")
        self.phaseSpaceDensity = CalculatedParameter(name="Phase Space Density (thermal)", desc="phase space density using thermal cloud density" )
        
        self.calculatedParametersList = [self.N,self.stdevX,self.stdevY, self.Tx,self.Ty , self.T, self.aspectRatio, self.criticalTemperature,self.thermalDensity,self.phaseSpaceDensity]
        
    def fitFunc(self,data, *p):
        """2D GAUSSIAN: data is a 2 row array of positions
        e.g.
        0 1 2 3 4 5 0 1 2 3 4 5...
        0 0 0 0 0 0 1 1 1 1 1 1...    
        so data[0] is x
        data[1] is y
        """
        A, x0,sigmax, y0, sigmay,B = p
        return (A*scipy.exp(-(data[0]-x0)**2/(2.*sigmax**2)-(data[1]-y0)**2/(2.*sigmay**2))+B)
        
    def _deriveCalculatedParameters(self):
        """"Updates all the calculated parameters """
        #atom number N
        #first we calculate the integral of the gaussian
        gaussianIntegral = 2.0*scipy.pi*self.A.calculatedValue*abs(self.sigmax.calculatedValue*self.sigmay.calculatedValue)#ignores background B
        logger.info("gaussian integral in pixels = %G" % gaussianIntegral )
        imagePixelArea = (self.physics.pixelSize/self.physics.magnification*self.physics.binningSize*1.0E-6)**2.0 # area of a pixel in m^2 accounts for magnification
        logger.info("imagePixelArea integral in m^2 = %G" % imagePixelArea )
        N=(gaussianIntegral*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.crossSectionSigmaPlus
        self.N.value = N
        #temperature
        imagePixelLength = 1.0E-6*self.physics.pixelSize/self.physics.magnification*self.physics.binningSize
        logger.info("imagePixelLength integral  = %G" % imagePixelLength )
        #stdev x and y
        stdevX = abs(imagePixelLength*self.sigmax.calculatedValue)*1.0E6
        stdevY = abs(imagePixelLength*self.sigmay.calculatedValue)*1.0E6
        self.stdevX.value = stdevX
        self.stdevY.value = stdevY
        m = self.physics.massATU*self.physics.u
        logger.info("m  = %G" % m )
        logger.info("stdevx in m = %G " % (imagePixelLength*self.sigmax.calculatedValue))
        vx = imagePixelLength*(self.sigmax.calculatedValue-self.physics.inTrapSizeX)/(self.physics.timeOfFlightTimems*1.0E-3)
        logger.info("vx = %G" % vx )
        Tx = (m*vx*vx)/(self.physics.kb)*1.0E6 # page 27 Pethick and Smith
        logger.info("Tx = %G" % Tx )
        logger.info("stdevy in m = %G " % (imagePixelLength*self.sigmay.calculatedValue))
        vy = imagePixelLength*(self.sigmay.calculatedValue-self.physics.inTrapSizeY)/(self.physics.timeOfFlightTimems*1.0E-3)
        logger.info("vy = %G" % vy )
        Ty = (m*vy*vy)/(self.physics.kb)*1.0E6  # page 27 Pethick and Smith
        logger.info("Ty = %G" % Ty )
        self.Tx.value = Tx
        self.Ty.value = Ty
        T =(Tx+Ty)/2.0
        self.T.value = T
        

        #critical Temperature
        trapGradientXTelsaPerMetre = self.physics.trapGradientX*0.01 # convert G/cm to T/m
        fbar=(self.physics.trapFrequencyXHz*self.physics.trapFrequencyYHz*self.physics.trapFrequencyZHz)**(0.33)
        Tc = 4.5*(fbar/100.)*N**(1.0/3.0)#page 23 pethick and smith
        
        self.criticalTemperature.value=Tc
        
        nThermal = N/( 32.*scipy.pi*((self.physics.kb*T*1.0E-6)/(self.physics.bohrMagneton*trapGradientXTelsaPerMetre*2.0))**3.0) # PRA 83 013622 2011 pg 3 in cm^-3
        self.thermalDensity.value =1.0E-6*nThermal
        
        psd = nThermal*( (2*scipy.pi*self.physics.hbar**2.0)/(m*self.physics.kb*T*1.0E-6) ) **(1.5) # PRA 83 013622 2011 pg 3 and Pethick and Smith pg 23 
        self.phaseSpaceDensity.value =psd
        
        
        #aspect ratio
        self.aspectRatio.value = self.sigmax.calculatedValue/self.sigmay.calculatedValue
        return [self.N.value, self.Tx.value,self.Ty.value, self.T, self.aspectRatio.value]
    def _getIntelligentInitialValues(self):
        
        xs,ys,zs = self._get_subSpaceArrays()#returns the full arrays if subspace not used
        logger.debug("attempting to set initial values intellgently")
        if xs is None or ys is None or zs is None:
            logger.debug("couldn't find all necessary data")
            return False
        A0 = scipy.amax(zs)
        B0 = scipy.average(zs[0:len(ys)/10.0,0:len(xs)/10.0])
        y0Index, x0Index = scipy.unravel_index(zs.argmax(), zs.shape)
        logger.debug("index of max z is %s, %s " % (y0Index, x0Index))
        x0 = xs[x0Index]
        y0 = ys[y0Index]
        #WHEN WE IMPLEMENT ONLY FITTING A SUBSET THIS WILL HAVE TO CHANGE A BIT  
        x0HalfIndex = (scipy.absolute(zs[y0Index]-A0/2.0)).argmin()
        y0HalfIndex = (scipy.absolute(zs[:,x0Index]-A0/2.0)).argmin()
        logger.debug("index of half max z is %s, %s " % (y0HalfIndex, x0HalfIndex))
        x0Half = xs[x0HalfIndex]
        y0Half = ys[y0HalfIndex]
        FWHMX0 = 2.0*abs(x0-x0Half)
        FWHMY0 = 2.0*abs(y0-y0Half)
        sigmaX0 = FWHMX0/2.355
        sigmaY0 = FWHMY0/2.355
        logger.debug("x0,y0 %s, %s " % (x0, y0))
        return[A0,x0,sigmaX0, y0,sigmaY0,B0]
        
class GaussianAndParabolaFit(Fit):
    """Sub class of Fit which implements a Guassian fit  """
    def __init__(self, **traitsDict):
        super(GaussianAndParabolaFit, self).__init__(**traitsDict)
        self.function = "AGauss*exp(-(x-x0)**2/(2.*sigmax**2)-(y-y0)**2/(2.*sigmay**2))+AParab*(1-((x-x0)/wParabX)**2-((y-y0)/wParabY)**2)**(1.5)+B"
        self.name = "2D Gaussian + Parabola"
        
        self.x0 = FitVariable(name="x0")
        self.y0 = FitVariable(name="y0")
        self.AGauss = FitVariable(name="AGauss")
        self.sigmax = FitVariable(name="sigmax")
        self.sigmay = FitVariable(name="sigmay")
        self.AParab = FitVariable(name="AParab")
        self.wParabX = FitVariable(name="wParabX")
        self.wParabY = FitVariable(name="wParabY")
        self.B = FitVariable(name="B")
        self.variablesList = [self.x0,self.y0,self.AGauss,self.sigmax,self.sigmay,self.AParab,self.wParabX,self.wParabY,self.B]
        

        self.NThermal = CalculatedParameter(name="N Thermal", desc="Atom number calculated from gaussian part of fit")
        self.NCondensate = CalculatedParameter(name="N Condensate", desc="Atom number calculated from parabola part of fit")
        self.N = CalculatedParameter(name="Total N", desc="N Thermal + N Condensate")
        self.condensateFraction = CalculatedParameter(name="Condensate Fraction", desc="NCondensate/NThermal")
        
        self.Tx = CalculatedParameter(name="Temperature X", desc="Temperature from time of flight in x direction. Assumes initial size of zero")
        self.Ty = CalculatedParameter(name="Temperature Y", desc="Temperature from time of flight in y direction. Assumes initial size of zero")
        self.T = CalculatedParameter(name="Temperature", desc="average of temperature X and temperature Y")     
        
        self.ThomasFermiRadiusX = CalculatedParameter(name="Thomas Fermi Radius X", desc="edge of parabola in X direction")    
        self.ThomasFermiRadiusY = CalculatedParameter(name="Thomas Fermi Radius Y", desc="edge of parabola in Y direction")
        self.effectiveThomasFermiRadius = CalculatedParameter(name="Thomas Fermi Radius Bar", desc="SQRT(TFRadiusX * TFRadiusY)")
        
        self.aspectRatioThermal = CalculatedParameter(name="Aspect Ratio Thermal", desc="ratio of sigma x to sigma y")
        self.aspectRationCondensate = CalculatedParameter(name="Aspect Ratio Condensate", desc="ratio of wx to wy")
        
        self.chemicalPotentialX=CalculatedParameter(name="Chem Pot. X", desc="chemical potential from trapping Freq X direction and TF Radius X")         
        self.chemicalPotentialY=CalculatedParameter(name="Chem Pot. Y", desc="chemical potential from trapping Freq Y direction and TF Radius Y")  

        
        self.calculatedParametersList = [self.NThermal,self.NCondensate,self.condensateFraction , self.Tx, self.Ty, self.T, self.ThomasFermiRadiusX, self.ThomasFermiRadiusY,self.effectiveThomasFermiRadius, self.aspectRatioThermal, self.aspectRationCondensate,self.chemicalPotentialX, self.chemicalPotentialY]
        
        
    def fitFunc(self,data, *p):
        """ Gaussian + Parabola
        data is a 2 row array of positions
        e.g.
        0 1 2 3 4 5 0 1 2 3 4 5...
        0 0 0 0 0 0 1 1 1 1 1 1...    
        so data[0] is x
        data[1] is y
        Note that we must clip the parabola to 0 otherwise we would take the square root of negative number
        """
        x0,y0,AGauss,sigmax,sigmay,AParab,wParabX,wParabY,B = p
        return AGauss*scipy.exp(-(data[0]-x0)**2/(2.*sigmax**2)-(data[1]-y0)**2/(2.*sigmay**2))+AParab*((1-((data[0]-x0)/wParabX)**2-((data[1]-y0)/wParabY)**2).clip(0)**(1.5))+B

    def _getIntelligentInitialValues(self):
        xs,ys,zs = self._get_subSpaceArrays()#returns the full arrays if subspace not used
        logger.debug("attempting to set initial values intellgently")
        if xs is None or ys is None or zs is None:
            logger.debug("couldn't find all necessary data")
            return False
        A = scipy.amax(zs)
        B = scipy.average(zs[0:len(ys)/10.0,0:len(xs)/10.0])
        y0Index, x0Index = scipy.unravel_index(zs.argmax(), zs.shape)
        logger.debug("index of max z is %s, %s " % (y0Index, x0Index))
        x0 = xs[x0Index]
        y0 = ys[y0Index]
        #WHEN WE IMPLEMENT ONLY FITTING A SUBSET THIS WILL HAVE TO CHANGE A BIT  
        x0HalfIndex = (scipy.absolute(zs[y0Index]-A/2.0)).argmin()
        y0HalfIndex = (scipy.absolute(zs[:,x0Index]-A/2.0)).argmin()
        logger.debug("index of half max z is %s, %s " % (y0HalfIndex, x0HalfIndex))
        x0Half = xs[x0HalfIndex]
        y0Half = ys[y0HalfIndex]
        FWHMX0 = 2.0*abs(x0-x0Half)
        FWHMY0 = 2.0*abs(y0-y0Half)
        
        #make gaussian wings larger for thermal part (*4)
        sigmax = 4*FWHMX0/2.355
        sigmay = 4*FWHMY0/2.355
        wParabX = FWHMX0/2.0
        wParabY = FWHMY0/2.0
        AGauss = 0.1*A
        AParab = 0.9*A
        
        p0=[x0,y0,AGauss,sigmax,sigmay,AParab,wParabX,wParabY,B]
        logger.debug("initial values guess = %s" % p0)
        return p0
        
        
    def _deriveCalculatedParameters(self):
        """"Updates all the calculated parameters """

        #useful constants
        imagePixelArea = (self.physics.pixelSize/self.physics.magnification*self.physics.binningSize*1.0E-6)**2.0 # area of a pixel in m^2 accounts for magnification           
        logger.info("imagePixelArea integral in m^2 = %G" % imagePixelArea )
        m = self.physics.massATU*self.physics.u
        sigmax = abs(self.sigmax.calculatedValue)
        sigmay = abs(self.sigmay.calculatedValue)
        wParabX = abs(self.wParabX.calculatedValue)
        wParabY = abs(self.wParabY.calculatedValue)
        
        #atom number N
        #NThermal        
        #integral under gaussian function. Then multiply by factors to get atoms contained in thermal part
        gaussianIntegral = 2.0*scipy.pi*self.AGauss.calculatedValue*sigmax*sigmay#ignores background B
        logger.info("gaussian integral in pixels = %G" % gaussianIntegral )        
        NThermal=(gaussianIntegral*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.crossSectionSigmaPlus
        self.NThermal.value = NThermal

        #NCondensate
        #integral under clipped parabola ^3/2
        parabolaIntegral = 0.4*scipy.pi*self.AParab.calculatedValue*wParabX*wParabY#ignores background B
        logger.info("parabolaIntegral in pixels = %G" % parabolaIntegral )        
        NCondensate=(parabolaIntegral*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.crossSectionSigmaPlus
        self.NCondensate.value = NCondensate
        
        #total atom number N
        N = NThermal + NCondensate        
        self.N.value = N
        
        #CondensateFraction 
        self.condensateFraction.value = NCondensate/(N)        
        

        #trap frequency omegas
        omegaX = self.physics.trapFrequencyXHz*2.0*scipy.pi
        omegaY = self.physics.trapFrequencyYHz*2.0*scipy.pi
        omegaZ = self.physics.trapFrequencyZHz*2.0*scipy.pi
        
        
        #Temperatures
        #temperatureX
        imagePixelLength = 1.0E-6*self.physics.pixelSize/self.physics.magnification*self.physics.binningSize
        logger.info("imagePixelLength integral  = %G" % imagePixelLength )
        
        logger.info("m  = %G" % m )
        logger.info("stdevx in m = %G " % imagePixelLength*self.sigmax.calculatedValue)
        vx = imagePixelLength*self.sigmax.calculatedValue/(self.physics.timeOfFlightTimems*1.0E-3)
        logger.info("vx = %G" % vx )
        Tx = (m*vx*vx)/(self.physics.kb)*1.0E6 # page 27 Pethick and Smith
        logger.info("Tx = %G" % Tx )
        
        #temperature Y
        logger.info("stdevy in m = %G " % imagePixelLength*self.sigmax.calculatedValue)
        vy = imagePixelLength*self.sigmay.calculatedValue/(self.physics.timeOfFlightTimems*1.0E-3)
        logger.info("vy = %G" % vy )
        Ty = (m*vy*vy)/(self.physics.kb)*1.0E6  # page 27 Pethick and Smith
        logger.info("Ty = %G" % Ty )
        self.Tx.value = Tx
        self.Ty.value = Ty
        
        #Temperature
        self.T.value = (Tx+Ty)/2.0
    
        #Thomas Fermi Radius
        # Thomas Fermi Radius x
        Rx = wParabX*imagePixelLength 
        Ry = wParabY*imagePixelLength 
        Rbar = (Rx*Ry)**(0.5)
        
        self.ThomasFermiRadiusX.value = Rx
        self.ThomasFermiRadiusY.value = Ry
        self.effectiveThomasFermiRadius.value = Rbar
        #Aspect Ratio Thermal
        self.aspectRatioThermal.value = sigmax /sigmay
        self.aspectRationCondensate.value = wParabX/wParabY
        
        #chemical potentials
        muX = m * omegaX * Rx /2.0
        muY = m * omegaY * Ry /2.0
        self.chemicalPotentialX.value = muX
        self.chemicalPotentialY.value = muY
                
                
                

class ParabolaFit(Fit):
    """Sub class of Fit which implements a Guassian fit  """
    def __init__(self, **traitsDict):
        super(ParabolaFit, self).__init__(**traitsDict)
        self.function = "AParab*(1-((x-x0)/wParabX)**2-((y-y0)/wParabY)**2)**(1.5)+B"
        self.name = "2D Parabola"
        
        self.x0 = FitVariable(name="x0")
        self.y0 = FitVariable(name="y0")
        self.AParab = FitVariable(name="AParab")
        self.wParabX = FitVariable(name="wParabX")
        self.wParabY = FitVariable(name="wParabY")
        self.B = FitVariable(name="B")
        self.variablesList = [self.x0,self.y0,self.AParab,self.wParabX,self.wParabY,self.B]
        
        self.NCondensate = CalculatedParameter(name="N Condensate", desc="Atom number calculated from parabola part of fit")
    
        self.ThomasFermiRadiusX = CalculatedParameter(name="Thomas Fermi Radius X", desc="edge of parabola in X direction")    
        self.ThomasFermiRadiusY = CalculatedParameter(name="Thomas Fermi Radius Y", desc="edge of parabola in Y direction")
        
        self.effectiveThomasFermiRadius = CalculatedParameter(name="Thomas Fermi Radius Bar", desc="SQRT(TFRadiusX * TFRadiusY)")
        
        self.aspectRationCondensate = CalculatedParameter(name="Aspect Ratio Condensate", desc="ratio of wx to wy")
        
        self.chemicalPotentialX=CalculatedParameter(name="Chem Pot. X", desc="chemical potential from trapping Freq X direction and TF Radius X")         
        self.chemicalPotentialY=CalculatedParameter(name="Chem Pot. Y", desc="chemical potential from trapping Freq Y direction and TF Radius Y")  
        
        self.calculatedParametersList = [self.NCondensate,self.ThomasFermiRadiusX, self.ThomasFermiRadiusY,self.effectiveThomasFermiRadius, self.aspectRationCondensate,self.chemicalPotentialX, self.chemicalPotentialY]
        
        
    def fitFunc(self,data, *p):
        """ Parabola
        data is a 2 row array of positions
        e.g.
        0 1 2 3 4 5 0 1 2 3 4 5...
        0 0 0 0 0 0 1 1 1 1 1 1...    
        so data[0] is x
        data[1] is y
        Note that we must clip the parabola to 0 otherwise we would take the square root of negative number
        """
        x0,y0,AParab,wParabX,wParabY,B = p
        return AParab*((1-((data[0]-x0)/wParabX)**2-((data[1]-y0)/wParabY)**2).clip(0)**(1.5))+B

    def _getIntelligentInitialValues(self):
        xs,ys,zs = self._get_subSpaceArrays()#returns the full arrays if subspace not used
        logger.debug("attempting to set initial values intellgently")
        if xs is None or ys is None or zs is None:
            logger.debug("couldn't find all necessary data")
            return False
        AParab = scipy.amax(zs)
        B = scipy.average(zs[0:len(ys)/10.0,0:len(xs)/10.0])
        y0Index, x0Index = scipy.unravel_index(zs.argmax(), zs.shape)
        logger.debug("index of max z is %s, %s " % (y0Index, x0Index))
        x0 = xs[x0Index]
        y0 = ys[y0Index]
        #WHEN WE IMPLEMENT ONLY FITTING A SUBSET THIS WILL HAVE TO CHANGE A BIT  
        x0HalfIndex = (scipy.absolute(zs[y0Index]-AParab/2.0)).argmin()
        y0HalfIndex = (scipy.absolute(zs[:,x0Index]-AParab/2.0)).argmin()
        logger.debug("index of half max z is %s, %s " % (y0HalfIndex, x0HalfIndex))
        x0Half = xs[x0HalfIndex]
        y0Half = ys[y0HalfIndex]
        deltaXHalf = abs(x0-x0Half)
        deltaYHalf = abs(y0-y0Half)
        wParabX = 1.644*deltaXHalf
        wParabY = 1.644*deltaYHalf
        
        p0=[x0,y0,AParab,wParabX,wParabY,B]
        logger.debug("initial values guess = %s" % p0)
        return p0
        
        
    def _deriveCalculatedParameters(self):
        """"Updates all the calculated parameters """

        #useful constants
        imagePixelArea = (self.physics.pixelSize/self.physics.magnification*self.physics.binningSize*1.0E-6)**2.0 # area of a pixel in m^2 accounts for magnification           
        logger.info("imagePixelArea integral in m^2 = %G" % imagePixelArea )
        m = self.physics.massATU*self.physics.u
        imagePixelLength = 1.0E-6*self.physics.pixelSize/self.physics.magnification*self.physics.binningSize
        wParabX = abs(self.wParabX.calculatedValue)
        wParabY = abs(self.wParabY.calculatedValue)
        
        #atom number N

        #NCondensate
        #integral under clipped parabola ^3/2
        parabolaIntegral = 0.4*scipy.pi*self.AParab.calculatedValue*wParabX*wParabY#ignores background B
        logger.info("parabolaIntegral in pixels = %G" % parabolaIntegral )        
        NCondensate=(parabolaIntegral*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.crossSectionSigmaPlus
        self.NCondensate.value = NCondensate
        
        

        #trap frequency omegas
        omegaX = self.physics.trapFrequencyXHz*2.0*scipy.pi
        omegaY = self.physics.trapFrequencyYHz*2.0*scipy.pi
        omegaZ = self.physics.trapFrequencyZHz*2.0*scipy.pi
        
        #Thomas Fermi Radius
        # Thomas Fermi Radius x
        Rx = wParabX*imagePixelLength 
        Ry = wParabY*imagePixelLength 
        Rbar = (Rx*Ry)**(0.5)
        
        self.ThomasFermiRadiusX.value = Rx
        self.ThomasFermiRadiusY.value = Ry
        self.effectiveThomasFermiRadius.value = Rbar
        #Aspect Ratio Thermal
        self.aspectRationCondensate.value = wParabX/wParabY
        
        #chemical potentials
        muX = m * omegaX * Rx /2.0
        muY = m * omegaY * Ry /2.0
        self.chemicalPotentialX.value = muX
        self.chemicalPotentialY.value = muY


if __name__=="__main__":
    wx = FitVariable(name="wx", initialValue=1.0)
    wy = FitVariable(name="wy", initialValue=2.0)
    stdx = FitVariable(name="stdx", initialValue=3.0)
    stdy = FitVariable(name="stdy", initialValue=4.0)
    variablesList=[wx,wy,stdx,stdy]    
    n = CalculatedParameter(name="N", value=1.0E7)
    fit = GaussianFit()
    fit.configure_traits()