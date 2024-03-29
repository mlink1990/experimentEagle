# -*- coding: utf-8 -*-
"""
Created on Sun Jan 17 13:57:49 2016

@author: tharrison
"""
import logging

import scipy
import numpy as np

from fits import Fit, Parameter, CalculatedParameter

logger=logging.getLogger("ExperimentEagle.fits")

class GaussianFit(Fit):
    """Sub class of Fit which implements a Guassian fit  """
    def __init__(self, **traitsDict):
        super(GaussianFit, self).__init__(**traitsDict)
        self.function = "(A*exp(-(x-x0)**2/(2.*sigmax**2)-(y-y0)**2/(2.*sigmay**2))+B)"
        self.name = "2D Gaussian"
        
        self.A = Parameter(name="A")
        self.x0 = Parameter(name="x0")
        self.sigmax = Parameter(name="sigmax")
        self.y0 = Parameter(name="y0")
        self.sigmay = Parameter(name="sigmay")
        self.B = Parameter(name="B")
        
        self.variablesList = [self.A,self.x0,self.sigmax,self.y0,self.sigmay,self.B ]
        
        self.N = CalculatedParameter(name="N", desc="Atom number calculated from gaussian fit")
        self.stdevX = CalculatedParameter(name="stdev X (um)", desc="stdev X of TOF cloud from gaussian fit")
        self.stdevY = CalculatedParameter(name="stdev Y (um)", desc="stdev Y of TOF cloud from gaussian fit")
        self.Tx = CalculatedParameter(name="Tx (uK)", desc="Temperature from time of flight in x direction. Uses in trap size defined in physics")
        self.Ty = CalculatedParameter(name="Ty (uK)", desc="Temperature from time of flight in x direction. Uses in trap size defined in physics")
        self.T = CalculatedParameter(name="T (uK)", desc="Average of Tx and Ty")
        self.TxHarmonic = CalculatedParameter(name="Tx harmonic (uK)", desc="Temperature from time of flight in x direction. Uses trap frequency defined in physics")
        self.TyHarmonic = CalculatedParameter(name="Ty harmonic (uK)", desc="Temperature from time of flight in y direction.  Uses trap frequency defined in physics")
        self.THarmonic = CalculatedParameter(name="T harmonic (uK)", desc="average of Tx harmonic and Ty Harmonic")
        self.aspectRatio = CalculatedParameter(name="Aspect Ratio", desc="ratio of sigma x to sigma y")
        self.inverseAspectRatio = CalculatedParameter(name="Aspect Ratio Inverse", desc="ratio of sigma y to sigma x")
        self.summedOD = CalculatedParameter(name="Summed OD", desc="Optical density summed in the calculated region. Clipped at 0. (i.e. does not count negatives)")
        self.summedODAtomNumber = CalculatedParameter(name="Summed OD Atom Number", desc="Using optical density summed in the calculated region we calculate an estimate of atom number. Clipped at 0. (i.e. does not count negatives)")
        self.criticalTemperature = CalculatedParameter(name="Critical Temperature (nK)", desc="Critical temperature from trapping frequency and atom number")  
        self.thermalDensity = CalculatedParameter(name="Thermal Cloud Density Linear Trap (cm^-3)", desc = "N/( 32 Pi (kb T / mu B')^3)")
        self.thermalDensityHarmonic = CalculatedParameter(name="Peak Thermal Density Harmonic Trap (cm^-3)", desc = "N omegax, omegay, omegaz (m/2 pi kb T)^(3/2)")
        self.phaseSpaceDensity = CalculatedParameter(name="Phase Space Density (thermal)", desc="phase space density using thermal cloud density" )
        self.phaseSpaceDensityHarmonic = CalculatedParameter(name="Phase Space Density Harmonic (thermal)", desc="phase space density using thermal cloud density for a harmonic trap" )
        self.vbarLinear = CalculatedParameter(name="average thermal velocity Linear Trap (m/s)", desc = "sqrt(8 kB T / pi m)")        
        self.collisionTimeLinear = CalculatedParameter(name="Collision Time Linear Trap (ms)", desc = "sqrt(20 n sigma vbar")
        self.signalToNoise = CalculatedParameter(name="Signal to Noise ratio", desc = "gaussian amplitude to background std.dev.")
        
        
        self.calculatedParametersList = [self.N,self.stdevX,self.stdevY, self.Tx,self.Ty , self.T,self.TxHarmonic,self.TyHarmonic,self.THarmonic, 
                                         self.aspectRatio,self.inverseAspectRatio, self.summedOD,self.summedODAtomNumber, self.criticalTemperature,self.thermalDensity,
                                         self.thermalDensityHarmonic,self.phaseSpaceDensity,self.phaseSpaceDensityHarmonic,self.vbarLinear,self.collisionTimeLinear,self.signalToNoise]
    
    @staticmethod
    def fitFunc(positions, A,x0,sigmax,y0,sigmay,B):
        """2D GAUSSIAN: data is a 2 row array of positions
        e.g.
        0 1 2 3 4 5 0 1 2 3 4 5...
        0 0 0 0 0 0 1 1 1 1 1 1...    
        so data[0] is x
        data[1] is y
        """
        return (A*scipy.exp(-(positions[0]-x0)**2/(2.*sigmax**2)-(positions[1]-y0)**2/(2.*sigmay**2))+B)
                  
    def _deriveCalculatedParameters(self):
        """"Updates all the calculated parameters """
        #atom number N
        #first we calculate the integral of the gaussian
        gaussianIntegral = 2.0*scipy.pi*abs(self.A.calculatedValue)*abs(self.sigmax.calculatedValue*self.sigmay.calculatedValue)#ignores background B
        logger.debug("gaussian integral in pixels = %G" % gaussianIntegral )
        imagePixelArea = (self.physics.pixelSize/self.physics.magnification*self.physics.binningSize*1.0E-6)**2.0 # area of a pixel in m^2 accounts for magnification
        logger.debug("imagePixelArea integral in m^2 = %G" % imagePixelArea )
        N=(gaussianIntegral*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.selectedElement.crossSectionSigmaPlus
        self.N.value = N
        #temperature
        imagePixelLength = 1.0E-6*self.physics.pixelSize/self.physics.magnification*self.physics.binningSize
        logger.debug("imagePixelLength integral  = %G" % imagePixelLength )
        #stdev x and y
        stdevX = abs(imagePixelLength*self.sigmax.calculatedValue)*1.0E6
        stdevY = abs(imagePixelLength*self.sigmay.calculatedValue)*1.0E6
        self.stdevX.value = stdevX
        self.stdevY.value = stdevY
        m = self.physics.selectedElement.massATU*self.physics.u
        logger.debug("m  = %G" % m )
        logger.debug("stdevx in m = %G " % (imagePixelLength*self.sigmax.calculatedValue))
        vx = imagePixelLength*(abs(self.sigmax.calculatedValue)-self.physics.inTrapSizeX)/(self.physics.timeOfFlightTimems*1.0E-3)
        logger.debug("vx = %G" % vx )
        Tx = (m*vx*vx)/(self.physics.kb)*1.0E6 # page 27 Pethick and Smith
        logger.debug("Tx = %G" % Tx )
        logger.debug("stdevy in m = %G " % (imagePixelLength*self.sigmay.calculatedValue))
        vy = imagePixelLength*(abs(self.sigmay.calculatedValue)-self.physics.inTrapSizeY)/(self.physics.timeOfFlightTimems*1.0E-3)
        logger.debug("vy = %G" % vy )
        Ty = (m*vy*vy)/(self.physics.kb)*1.0E6  # page 27 Pethick and Smith
        logger.debug("Ty = %G" % Ty )
        self.Tx.value = Tx
        self.Ty.value = Ty
        T =(Tx+Ty)/2.0
        self.T.value = T
        
        #making probing and understanding Fermi gases pg 70  http://arxiv.org/pdf/0801.2500v1.pdf
        TxHarmonic = (1.0E6*m/self.physics.kb)*(2*scipy.pi*self.physics.trapFrequencyXHz)**2*(stdevX*1.0E-6)**2/((1.0+ (2*scipy.pi*self.physics.trapFrequencyXHz* self.physics.timeOfFlightTimems*1.0E-3)**2))
        logger.debug("TxHarmonic = %G" % TxHarmonic )
        TyHarmonic = 1.0E6*m*(2*scipy.pi*self.physics.trapFrequencyYHz)**2*(stdevY*1.0E-6)**2/(self.physics.kb*(1.0+ (2*scipy.pi*self.physics.trapFrequencyYHz* self.physics.timeOfFlightTimems*1.0E-3 )**2))
        logger.debug("TyHarmonic = %G" % TyHarmonic )        
        THarmonic =(TxHarmonic+TyHarmonic)/2.0
        self.TxHarmonic.value = TxHarmonic
        self.TyHarmonic.value = TyHarmonic
        self.THarmonic.value = THarmonic
        #critical Temperature
        trapGradientXTelsaPerMetre = self.physics.trapGradientX*0.01 # convert G/cm to T/m
        fbar=(self.physics.trapFrequencyXHz*self.physics.trapFrequencyYHz*self.physics.trapFrequencyZHz)**(0.33)
        Tc = 4.5*(fbar/100.)*N**(1.0/3.0)#page 23 pethick and smith1776.5
        
        self.criticalTemperature.value=Tc
        logger.debug("criticalTemperature = %G" % Tc )   
        nThermal = N/( 32.*scipy.pi*((self.physics.kb*T*1.0E-6)/(self.physics.bohrMagneton*trapGradientXTelsaPerMetre*2.0))**3.0) # PRA 83 013622 2011 pg 3 in cm^-3
        self.thermalDensity.value =1.0E-6*nThermal
        
        #derived from integrating gaussian wavefunction (exp(-V(r)/kb T ) or see http://www.physi.uni-heidelberg.de/Forschung/QD/datafiles/publications/theses/2011_Aline_Faber.pdf pg 6
        nThermalHarmonic = N * (2 * scipy.pi * fbar  )**3 * (m / (2*scipy.pi*self.physics.kb*THarmonic*1.0E-6 ))**1.5 
        self.thermalDensityHarmonic.value = nThermalHarmonic*1.0E-6# in cm^-3  
        
        psd = nThermal*( (2*scipy.pi*self.physics.hbar**2.0)/(m*self.physics.kb*T*1.0E-6) ) **(1.5) # PRA 83 013622 2011 pg 3 and Pethick and Smith pg 23 
        self.phaseSpaceDensity.value =psd
        
        psdHarmonic = nThermalHarmonic*( (2*scipy.pi*self.physics.hbar**2.0)/(m*self.physics.kb*T*1.0E-6) ) **(1.5) # PRA 83 013622 2011 pg 3 and Pethick and Smith pg 23 
        #and http://www.physi.uni-heidelberg.de/Forschung/QD/datafiles/publications/theses/2011_Aline_Faber.pdf
        self.phaseSpaceDensityHarmonic.value =psdHarmonic
        
        #vbar and collision time linear trap following arXiv:1011.1078v1 Fast production of large 23 Na Bose-Einstein condensates in an optically plugged magnetic quadrupole trap
        sigmaElastic = 8.0 * scipy.pi * (self.physics.selectedElement.scatteringLength*self.physics.a0)**2
        logger.debug("sigma elastic =%s " % sigmaElastic )
        vbarLinear =scipy.sqrt((8 * self.physics.kb * (T *1E-6))/(scipy.pi*m) ) # m/s
        logger.debug("vbarLinear =%s " % vbarLinear )
        collisionTimeLinear =  1.0E3/(scipy.sqrt(2) * (nThermal)*sigmaElastic*vbarLinear)#milliseconds nThermal is in m^-3
        logger.debug("collisionTimeLinear =%s " % collisionTimeLinear )
        self.vbarLinear.value = vbarLinear
        self.collisionTimeLinear.value = collisionTimeLinear
        
        #aspect ratio
        self.aspectRatio.value = self.sigmax.calculatedValue/self.sigmay.calculatedValue
        self.inverseAspectRatio.value = 1.0/self.aspectRatio.value

        #summed OD
        xs,ys,zs = self._get_subSpaceArrays()        
        summedOD = scipy.sum(zs.clip(0))
        self.summedOD.value = summedOD
        
        #atom number from sum
        summedODAtomNumber = (summedOD*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.selectedElement.crossSectionSigmaPlus
        self.summedODAtomNumber.value = summedODAtomNumber
        logger.info("Derived values from fit" )

        # signal-to-noise
        background = np.ravel(zs) - self.mostRecentModelResult.best_fit
        self.signalToNoise.value = self.A.calculatedValue / np.std(background)


    def _getIntelligentInitialValues(self):
        
        xs,ys,zs = self._get_subSpaceArrays()#returns the full arrays if subspace not used
        logger.debug("attempting to set initial values intellgently")
        if xs is None or ys is None or zs is None:
            logger.debug("couldn't find all necessary data")
            return False
        A0 = scipy.amax(zs)
        B0 = scipy.average(zs[0:len(ys)//10,0:len(xs)//10])
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
