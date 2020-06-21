# -*- coding: utf-8 -*-
"""
Created on Sun Jan 17 13:58:07 2016

@author: tharrison
"""

from fits import Fit, Parameter, CalculatedParameter
import scipy
import logging

logger=logging.getLogger("ExperimentEagle.fits")

class RotatedGaussianFit(Fit):
    """Sub class of Fit which implements a Rotated Guassian fit  """
    def __init__(self, **traitsDict):
        super(RotatedGaussianFit, self).__init__(**traitsDict)
        self.function = "(A*exp( -(( (y-y0)*cos(theta)+(x-x0)*Sin(theta))**2/(2*sigmay**2)) - ( + (x-x0)*cos(theta) - (y-y0)*sin(theta))**2/(2*sigmax**2))+B)"
        self.name = "Rotated 2D Gaussian"
        
        self.A = Parameter(name="A")
        self.x0 = Parameter(name="x0")
        self.sigmax = Parameter(name="sigmax")
        self.y0 = Parameter(name="y0")
        self.sigmay = Parameter(name="sigmay")        
        self.theta = Parameter(name="theta")        
        self.B = Parameter(name="B")
        
        self.variablesList = [self.A,self.x0,self.sigmax,self.y0,self.sigmay,self.theta,self.B ]
        
        self.N = CalculatedParameter(name="N", desc="Atom number calculated from gaussian fit")
        self.stdevX = CalculatedParameter(name="stdev X (um)", desc="stdev X of TOF cloud from gaussian fit")
        self.stdevY = CalculatedParameter(name="stdev Y (um)", desc="stdev Y of TOF cloud from gaussian fit")
        self.xPrime = CalculatedParameter(name="xPrime (um)", desc="uses angle theta to rotate frame so that you get position along principal axes")
        self.yPrime = CalculatedParameter(name="yPrime (um)", desc="uses angle theta to rotate frame so that you get position along principal axes")
        self.Tx = CalculatedParameter(name="Tx (uK)", desc="Temperature from time of flight in x direction. Uses in trap size defined in physics")
        self.Ty = CalculatedParameter(name="Ty (uK)", desc="Temperature from time of flight in y direction. Uses in trap size defined in physics")
        self.T = CalculatedParameter(name="T (uK)", desc="Average of Tx and Ty")
        self.aspectRatio = CalculatedParameter(name="Aspect Ratio", desc="ratio of sigma x to sigma y")
        self.summedOD = CalculatedParameter(name="Summed OD", desc="Optical density summed in the calculated region. Clipped at 0. (i.e. does not count negatives)")
        self.summedODAtomNumber = CalculatedParameter(name="Summed OD Atom Number", desc="Using optical density summed in the calculated region we calculate an estimate of atom number. Clipped at 0. (i.e. does not count negatives)")
        self.criticalTemperature = CalculatedParameter(name="Critical Temperature (nK)", desc="Critical temperature from trapping frequency and atom number")  
        self.thermalDensity = CalculatedParameter(name="Thermal Cloud Density (cm^-3)", desc = "N/( 32 Pi (kb T / mu B')^3)")
        self.phaseSpaceDensity = CalculatedParameter(name="Phase Space Density (thermal)", desc="phase space density using thermal cloud density" )
        
        self.calculatedParametersList = [self.N,self.stdevX,self.stdevY,self.xPrime,self.yPrime, self.Tx,self.Ty , self.T, self.aspectRatio,self.summedOD,self.summedODAtomNumber, self.criticalTemperature,self.thermalDensity,self.phaseSpaceDensity]
    
    @staticmethod
    def fitFunc(positions, A,x0,sigmax,y0,sigmay,theta,B):
        """2D GAUSSIAN: data is a 2 row array of positions
        e.g.
        0 1 2 3 4 5 0 1 2 3 4 5...
        0 0 0 0 0 0 1 1 1 1 1 1...    
        so data[0] is x
        data[1] is y
        """
        theta = scipy.pi*theta/180.0
        return (A*scipy.exp(-(((positions[1]-y0)*scipy.cos(theta)+(positions[0]-x0)*scipy.sin(theta))**2/(2*sigmay**2)) - ((positions[0]-x0)*scipy.cos(theta) - (positions[1]-y0)*scipy.sin(theta))**2/(2*sigmax**2))+B)

    def _deriveCalculatedParameters(self):
        """"Updates all the calculated parameters """
        #atom number N
        #first we calculate the integral of the gaussian
        gaussianIntegral = 2.0*scipy.pi*abs(self.A.calculatedValue)*abs(self.sigmax.calculatedValue*self.sigmay.calculatedValue)#ignores background B
        logger.info("gaussian integral in pixels = %G" % gaussianIntegral )
        imagePixelArea = (self.physics.pixelSize/self.physics.magnification*self.physics.binningSize*1.0E-6)**2.0 # area of a pixel in m^2 accounts for magnification
        logger.info("imagePixelArea integral in m^2 = %G" % imagePixelArea )
        N=(gaussianIntegral*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.selectedElement.crossSectionSigmaPlus
        self.N.value = N
        #temperature
        imagePixelLength = 1.0E-6*self.physics.pixelSize/self.physics.magnification*self.physics.binningSize
        logger.info("imagePixelLength integral  = %G" % imagePixelLength )
        #stdev x and y
        stdevX = abs(imagePixelLength*self.sigmax.calculatedValue)*1.0E6
        stdevY = abs(imagePixelLength*self.sigmay.calculatedValue)*1.0E6
        self.stdevX.value = stdevX
        self.stdevY.value = stdevY
        #xprime and yprime
        x0 = self.x0.calculatedValue
        y0 = self.y0.calculatedValue
        theta = scipy.pi*self.theta.calculatedValue/180.0
        xPrime  = 1.0E6*imagePixelLength*(x0*scipy.cos(theta)+y0*scipy.sin(theta)) #in microns and then rotation around theta
        yPrime  = 1.0E6*imagePixelLength*(x0*scipy.sin(theta)-y0*scipy.cos(theta)) #in microns and then rotation around theta
        self.xPrime.value = xPrime
        self.yPrime.value = yPrime
        #mass and velocity
        m = self.physics.selectedElement.massATU*self.physics.u
        logger.info("m  = %G" % m )
        logger.info("stdevx in m = %G " % (imagePixelLength*self.sigmax.calculatedValue))
        vx = imagePixelLength*(abs(self.sigmax.calculatedValue)-self.physics.inTrapSizeX)/(self.physics.timeOfFlightTimems*1.0E-3)
        logger.info("vx = %G" % vx )
        Tx = (m*vx*vx)/(self.physics.kb)*1.0E6 # page 27 Pethick and Smith
        logger.info("Tx = %G" % Tx )
        logger.info("stdevy in m = %G " % (imagePixelLength*self.sigmay.calculatedValue))
        vy = imagePixelLength*(abs(self.sigmay.calculatedValue)-self.physics.inTrapSizeY)/(self.physics.timeOfFlightTimems*1.0E-3)
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
        Tc = 4.5*(fbar/100.)*N**(1.0/3.0)#page 23 pethick and smith1776.5
        
        self.criticalTemperature.value=Tc
        
        nThermal = N/( 32.*scipy.pi*((self.physics.kb*T*1.0E-6)/(self.physics.bohrMagneton*trapGradientXTelsaPerMetre*2.0))**3.0) # PRA 83 013622 2011 pg 3 in cm^-3
        self.thermalDensity.value =1.0E-6*nThermal
        
        psd = nThermal*( (2*scipy.pi*self.physics.hbar**2.0)/(m*self.physics.kb*T*1.0E-6) ) **(1.5) # PRA 83 013622 2011 pg 3 and Pethick and Smith pg 23 
        self.phaseSpaceDensity.value =psd
        
        
        #aspect ratio
        self.aspectRatio.value = abs(self.sigmax.calculatedValue)/abs(self.sigmay.calculatedValue)

        #summed OD
        xs,ys,zs = self._get_subSpaceArrays()        
        summedOD = scipy.sum(zs.clip(0))
        self.summedOD.value = summedOD
        
        #atom number from sum
        summedODAtomNumber = (summedOD*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.selectedElement.crossSectionSigmaPlus
        self.summedODAtomNumber.value = summedODAtomNumber
        
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
        theta0 = 0.0
        logger.debug("x0,y0 %s, %s " % (x0, y0))
        return[A0,x0,sigmaX0, y0,sigmaY0,theta0,B0]        
