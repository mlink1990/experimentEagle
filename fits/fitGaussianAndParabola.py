# -*- coding: utf-8 -*-
"""
Created on Sun Jan 17 14:00:12 2016

@author: tharrison
"""
from fits import Fit, Parameter, CalculatedParameter
import scipy
import logging

logger=logging.getLogger("ExperimentEagle.fits")
        
class GaussianAndParabolaFit(Fit):
    """Sub class of Fit which implements a Guassian fit  """
    def __init__(self, **traitsDict):
        super(GaussianAndParabolaFit, self).__init__(**traitsDict)
        self.function = "AGauss*exp(-(x-x0)**2/(2.*sigmax**2)-(y-y0)**2/(2.*sigmay**2))+AParab*(1-((x-x0)/wParabX)**2-((y-y0)/wParabY)**2)**(1.5)+B"
        self.name = "2D Gaussian + Parabola"
        
        self.x0 = Parameter(name="x0")
        self.y0 = Parameter(name="y0")
        self.AGauss = Parameter(name="AGauss")
        self.sigmax = Parameter(name="sigmax")
        self.sigmay = Parameter(name="sigmay")
        self.AParab = Parameter(name="AParab")
        self.wParabX = Parameter(name="wParabX")
        self.wParabY = Parameter(name="wParabY")
        self.B = Parameter(name="B")
        self.variablesList = [self.x0,self.y0,self.AGauss,self.sigmax,self.sigmay,self.AParab,self.wParabX,self.wParabY,self.B]
        

        self.NThermal = CalculatedParameter(name="N Thermal", desc="Atom number calculated from gaussian part of fit")
        self.NCondensate = CalculatedParameter(name="N Condensate", desc="Atom number calculated from parabola part of fit")
        self.N = CalculatedParameter(name="Total N", desc="N Thermal + N Condensate")
        self.condensateFraction = CalculatedParameter(name="Condensate Fraction", desc="NCondensate/NThermal")

        self.summedOD = CalculatedParameter(name="Summed OD", desc="Optical density summed in the calculated region. Clipped at 0. (i.e. does not count negatives)")
        self.summedODAtomNumber = CalculatedParameter(name="Summed OD Atom Number", desc="Using optical density summed in the calculated region we calculate an estimate of atom number. Clipped at 0. (i.e. does not count negatives)")
        
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

        
        self.calculatedParametersList = [self.NThermal,self.NCondensate,self.N,self.condensateFraction , self.summedOD,self.summedODAtomNumber , self.Tx, self.Ty, self.T, self.ThomasFermiRadiusX, self.ThomasFermiRadiusY,self.effectiveThomasFermiRadius, self.aspectRatioThermal, self.aspectRationCondensate,self.chemicalPotentialX, self.chemicalPotentialY]
        
    @staticmethod    
    def fitFunc(positions,x0,y0,AGauss,sigmax,sigmay,AParab,wParabX,wParabY,B):
        """ Gaussian + Parabola
        data is a 2 row array of positions
        e.g.
        0 1 2 3 4 5 0 1 2 3 4 5...
        0 0 0 0 0 0 1 1 1 1 1 1...    
        so data[0] is x
        data[1] is y
        Note that we must clip the parabola to 0 otherwise we would take the square root of negative number
        """
        return AGauss*scipy.exp(-(positions[0]-x0)**2/(2.*sigmax**2)-(positions[1]-y0)**2/(2.*sigmay**2))+AParab*((1-((positions[0]-x0)/wParabX)**2-((positions[1]-y0)/wParabY)**2).clip(0)**(1.5))+B

    def _getIntelligentInitialValues(self):
        xs,ys,zs = self._get_subSpaceArrays()#returns the full arrays if subspace not used
        logger.debug("attempting to set initial values intellgently")
        if xs is None or ys is None or zs is None:
            logger.debug("couldn't find all necessary data")
            return False
        A = scipy.amax(zs)
        B = scipy.average(zs[0:len(ys)//10,0:len(xs)//10])
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
        m = self.physics.selectedElement.massATU*self.physics.u
        sigmax = abs(self.sigmax.calculatedValue)
        sigmay = abs(self.sigmay.calculatedValue)
        wParabX = abs(self.wParabX.calculatedValue)
        wParabY = abs(self.wParabY.calculatedValue)
        
        #atom number N
        #NThermal        
        #integral under gaussian function. Then multiply by factors to get atoms contained in thermal part
        gaussianIntegral = 2.0*scipy.pi*self.AGauss.calculatedValue*sigmax*sigmay#ignores background B
        logger.info("gaussian integral in pixels = %G" % gaussianIntegral )        
        NThermal=(gaussianIntegral*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.selectedElement.crossSectionSigmaPlus
        self.NThermal.value = NThermal

        #NCondensate
        #integral under clipped parabola ^3/2
        parabolaIntegral = 0.4*scipy.pi*self.AParab.calculatedValue*wParabX*wParabY#ignores background B
        logger.info("parabolaIntegral in pixels = %G" % parabolaIntegral )        
        NCondensate=(parabolaIntegral*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.selectedElement.crossSectionSigmaPlus
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
        #logger.info("stdevx in m = %G " % imagePixelLength*self.sigmax.calculatedValue)
        vx = imagePixelLength*self.sigmax.calculatedValue/(self.physics.timeOfFlightTimems*1.0E-3)
        logger.info("vx = %G" % vx )
        Tx = (m*vx*vx)/(self.physics.kb)*1.0E6 # page 27 Pethick and Smith
        logger.info("Tx = %G" % Tx )
        
        #temperature Y
        #logger.info("stdevy in m = %G " % imagePixelLength*self.sigmax.calculatedValue)
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

        #summed OD
        xs,ys,zs = self._get_subSpaceArrays()        
        summedOD = scipy.sum(zs.clip(0))
        self.summedOD.value = summedOD
        
        #atom number from sum
        summedODAtomNumber = (summedOD*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.selectedElement.crossSectionSigmaPlus
        self.summedODAtomNumber.value = summedODAtomNumber