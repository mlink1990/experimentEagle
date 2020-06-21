# -*- coding: utf-8 -*-
"""
Created on Sun Jan 17 14:01:06 2016

@author: tharrison
"""
from fits import Fit, Parameter, CalculatedParameter
import scipy
import logging

logger=logging.getLogger("ExperimentEagle.fits")
                
class ParabolaFit(Fit):
    """Sub class of Fit which implements a Parabola fit  """
    def __init__(self, **traitsDict):
        super(ParabolaFit, self).__init__(**traitsDict)
        self.function = "AParab*(1-((x-x0)/wParabX)**2-((y-y0)/wParabY)**2)**(1.5)+B"
        self.name = "2D Parabola"
        
        self.x0 = Parameter(name="x0")
        self.y0 = Parameter(name="y0")
        self.AParab = Parameter(name="AParab")
        self.wParabX = Parameter(name="wParabX")
        self.wParabY = Parameter(name="wParabY")
        self.B = Parameter(name="B")
        self.variablesList = [self.x0,self.y0,self.AParab,self.wParabX,self.wParabY,self.B]
        
        self.NCondensate = CalculatedParameter(name="N Condensate", desc="Atom number calculated from parabola part of fit")
    
        self.ThomasFermiRadiusX = CalculatedParameter(name="Thomas Fermi Radius X", desc="edge of parabola in X direction")    
        self.ThomasFermiRadiusY = CalculatedParameter(name="Thomas Fermi Radius Y", desc="edge of parabola in Y direction")
        
        self.effectiveThomasFermiRadius = CalculatedParameter(name="Thomas Fermi Radius Bar", desc="SQRT(TFRadiusX * TFRadiusY)")
        
        self.aspectRationCondensate = CalculatedParameter(name="Aspect Ratio Condensate", desc="ratio of wx to wy")
        
        self.chemicalPotentialX=CalculatedParameter(name="Chem Pot. X", desc="chemical potential from trapping Freq X direction and TF Radius X")         
        self.chemicalPotentialY=CalculatedParameter(name="Chem Pot. Y", desc="chemical potential from trapping Freq Y direction and TF Radius Y")  
        
        self.calculatedParametersList = [self.NCondensate,self.ThomasFermiRadiusX, self.ThomasFermiRadiusY,self.effectiveThomasFermiRadius, self.aspectRationCondensate,self.chemicalPotentialX, self.chemicalPotentialY]
        
    
    @staticmethod    
    def fitFunc(positions,x0,y0,AParab,wParabX,wParabY,B ):
        """ Parabola
        data is a 2 row array of positions
        e.g.
        0 1 2 3 4 5 0 1 2 3 4 5...
        0 0 0 0 0 0 1 1 1 1 1 1...    
        so data[0] is x
        data[1] is y
        Note that we must clip the parabola to 0 otherwise we would take the square root of negative number
        """
        return AParab*((1-((positions[0]-x0)/wParabX)**2-((positions[1]-y0)/wParabY)**2).clip(0)**(1.5))+B

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
        m = self.physics.selectedElement.massATU*self.physics.u
        imagePixelLength = 1.0E-6*self.physics.pixelSize/self.physics.magnification*self.physics.binningSize
        wParabX = abs(self.wParabX.calculatedValue)
        wParabY = abs(self.wParabY.calculatedValue)
        
        #atom number N

        #NCondensate
        #integral under clipped parabola ^3/2
        parabolaIntegral = 0.4*scipy.pi*self.AParab.calculatedValue*wParabX*wParabY#ignores background B
        logger.info("parabolaIntegral in pixels = %G" % parabolaIntegral )        
        NCondensate=(parabolaIntegral*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.selectedElement.crossSectionSigmaPlus
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
