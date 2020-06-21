# -*- coding: utf-8 -*-
"""
Created on Sun Jan 17 14:01:18 2016

@author: tharrison
"""
from fits import Fit, Parameter, CalculatedParameter
import scipy
import logging
import polylog

logger=logging.getLogger("ExperimentEagle.fits")
class FermiGasFit(Fit):
    """Sub class of Fit which implements a Parabola fit  """
    def __init__(self, **traitsDict):
        super(FermiGasFit, self).__init__(**traitsDict)
        self.function = "A*Li_2(-exp(betaMu)*exp(-(x-x0)^2/2sigmax^2)*exp(-(y-y0)^2/2sigmay^2))/Li_2(-exp(betaMu))+B"
        self.name = "Fermi Gas"
        
        
        self.x0 = Parameter(name="x0")
        self.y0 = Parameter(name="y0")
        self.A = Parameter(name="A")
        self.sigmaX = Parameter(name="sigmaX")
        self.sigmaY = Parameter(name="sigmaY")
        self.betaMu = Parameter(name="betaMu")
        self.B = Parameter(name="B")
        self.variablesList = [self.x0,self.y0,self.A,self.sigmaX,self.sigmaY,self.betaMu,self.B]
        
        self.fugacity = CalculatedParameter(name="fugacity", desc="fugacity: exp(betaMu)")

        self.calculatedParametersList = [self.fugacity]
        
    
    @staticmethod    
    def fitFunc(positions,x0,y0,A,sigmaX,sigmaY,betaMu,B ):
        """ Parabola
        data is a 2 row array of positions
        e.g.
        0 1 2 3 4 5 0 1 2 3 4 5...
        0 0 0 0 0 0 1 1 1 1 1 1...    
        so data[0] is x
        data[1] is y
        Note that we use an implementation of the poly log file optimised to perform the polylog calls:
        fermi_poly2(x), equal to -Li_2(-e^x)
        """
        return A*(polylog.fermi_poly2(betaMu-((positions[0]-x0)/(2*sigmaX))**2.-((positions[1]-y0)/(2*sigmaY))**2.))/(polylog.fermi_poly2(betaMu))+B

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
        betaMu0 = 1.0
        logger.debug("x0,y0 %s, %s " % (x0, y0))
        p0 = [x0,y0,A0,sigmaX0,sigmaY0,betaMu0,B0]
        return p0
        
        
    def _deriveCalculatedParameters(self):
        """"Updates all the calculated parameters """

        #useful constants
        imagePixelArea = (self.physics.pixelSize/self.physics.magnification*self.physics.binningSize*1.0E-6)**2.0 # area of a pixel in m^2 accounts for magnification           
        logger.info("imagePixelArea integral in m^2 = %G" % imagePixelArea )
        m = self.physics.selectedElement.massATU*self.physics.u
        imagePixelLength = 1.0E-6*self.physics.pixelSize/self.physics.magnification*self.physics.binningSize
        
        sigmaX = abs(self.sigmaX.calculatedValue)
        sigmaY = abs(self.sigmaY.calculatedValue)
        betaMu = self.betaMu.calculatedValue        
        
        #fugacity
        fugacity = scipy.exp(betaMu)
        self.fugacity.value = fugacity
