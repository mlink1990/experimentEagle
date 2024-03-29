# -*- coding: utf-8 -*-
"""
Created on Sun Jan 17 14:00:12 2016

@author: tharrison
"""
from fits import Fit, Parameter, CalculatedParameter
import scipy
import logging
from lmfit import  Model
from lmfit.models import ConstantModel, GaussianModel
import numpy as np

logger=logging.getLogger("ExperimentEagle.fits")
        
class GaussianAndParabola1DFit(Fit):
    """Sub class of Fit which implements a bimodal fit in 2D to get initial values, then in 1D  """
    def __init__(self, **traitsDict):
        super(GaussianAndParabola1DFit, self).__init__(**traitsDict)
        self.function = "AGauss*exp(-(x-x0)**2/(2.*sigmax**2)-(y-y0)**2/(2.*sigmay**2))+AParab*(1-((x-x0)/wParabX)**2-((y-y0)/wParabY)**2)**(1.5)+B"
        self.name = "2D Gaussian + Parabola 1D"
        
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

        self.condensateFraction1D = CalculatedParameter(name="Condensate Fraction 1D", desc="derived from average along one axis")

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

        self.roiStartX=CalculatedParameter(name="roiStartX", desc="Region of interest start x")
        self.roiStartY=CalculatedParameter(name="roiStartY", desc="Region of interest start z")
        self.roiEndX=CalculatedParameter(name="roiEndX", desc="Region of interest end x")
        self.roiEndY=CalculatedParameter(name="roiEndY", desc="Region of interest end y")
        self.roiBool=CalculatedParameter(name="roiBool", desc="Fit over region of interest (1) or not (0)")
        
        self.calculatedParametersList = [self.NThermal,self.NCondensate,self.N,self.condensateFraction, self.condensateFraction1D , self.summedOD,self.summedODAtomNumber, self.Tx, self.Ty, self.T,
            self.ThomasFermiRadiusX, self.ThomasFermiRadiusY,self.effectiveThomasFermiRadius, self.aspectRatioThermal, self.aspectRationCondensate,self.chemicalPotentialX, self.chemicalPotentialY,
            self.roiStartX, self.roiStartY, self.roiEndX, self.roiEndY, self.roiBool
        ]
        
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

        # 1D Condensate Fraction
        # roi = [self.startY,self.startX,self.endY,self.endX]
        ## Fit models
        def paraboloid1D(x, A, x0, wx):
            arg = np.clip( (x-x0)/wx, -1, 1 )
            return A*( -1 + ( arg )**2 )**2
        condensateModel = Model(paraboloid1D)
        thermalModel = GaussianModel()+ConstantModel()

        od = zs #[roi[0]:roi[2],roi[1]:roi[3]]
        od1d = np.mean(od,axis=0)

        ## cuts
        # cutXNoiseLeft = 250
        # cutXNoiseRight = 550
        cutXCondensateLeft = self.x0.calculatedValue - self.wParabX.calculatedValue * 1.2
        cutXCondensateRight = self.x0.calculatedValue + self.wParabX.calculatedValue * 1.2#
        ## apply cuts
        indices = xs
        indicesWings = np.logical_or( indices<cutXCondensateLeft, indices>cutXCondensateRight )
        indicesCenter = np.logical_and(indices>=cutXCondensateLeft,indices<=cutXCondensateRight)
        od1dWings = od1d[indicesWings]
        od1dCenter = od1d[indicesCenter]
        indicesWings = indices[indicesWings]
        indicesCenter = indices[indicesCenter]

        ## Fits
        ### Fit wings
        # guessThermal = thermalModel.eval(x=indices, amplitude=self.AGauss.calculatedValue*self.sigmax.calculatedValue, center=self.x0.calculatedValue, sigma=self.sigmax.calculatedValue, c=self.B.calculatedValue)
        resWings = thermalModel.fit(od1dWings, x=indicesWings, amplitude=self.AGauss.calculatedValue*self.sigmax.calculatedValue, center=self.x0.calculatedValue, sigma=self.sigmax.calculatedValue, c=self.B.calculatedValue)
        # print( resWings.fit_report() )
        ### Fit center
        thermalAndBackgroundFit = resWings.eval(x=indicesCenter)
        condensate = od1dCenter - thermalAndBackgroundFit

        resCenter = condensateModel.fit(condensate, x=indicesCenter, A=self.AParab.calculatedValue, x0=self.x0.calculatedValue, wx=self.wParabX.calculatedValue)
        # print( resCenter.fit_report() )
        condensateFit = resCenter.best_fit

        thermalAndBackgroundFull = resWings.eval(x=indices)
        backgroundFull = np.array( [resWings.best_values["c"]]*len(thermalAndBackgroundFull) )
        thermalFull = thermalAndBackgroundFull - backgroundFull

        # import matplotlib.pyplot as plt
        # plt.plot(indices, od1d, label="Data")
        # plt.plot(indices, thermalAndBackgroundFull, label="Thermal")
        # plt.plot(indices, backgroundFull, 'k-', label="Background")
        # plt.plot(indicesCenter, thermalAndBackgroundFit+condensateFit, label="Condensate")
        # # plt.plot(indices, guessThermal, label="Guess Thermal")
        # plt.fill_between(indicesCenter,thermalAndBackgroundFit,thermalAndBackgroundFit+condensateFit,thermalAndBackgroundFit+condensateFit>thermalAndBackgroundFit, alpha=.2)
        # plt.fill_between(indices,backgroundFull,thermalAndBackgroundFull,thermalAndBackgroundFull>backgroundFull, alpha=.2)
        # # plt.axvline(cutXNoiseRight, color='r', ls='--')
        # # plt.axvline(cutXNoiseLeft, color='r', ls='--')
        # plt.axvline(cutXCondensateLeft, color='b', ls='--')
        # plt.axvline(cutXCondensateRight, color='b', ls='--')
        
        # # plt.xlim(cutXNoiseLeft-50, cutXNoiseRight+50)
        # plt.tight_layout()
        # plt.savefig("debug")
        # plt.clf()

        condensateCount = np.sum(condensateFit)
        thermalCount = np.sum(thermalFull)
        self.condensateFraction1D.value = condensateCount / (condensateCount+thermalCount)

        # save ROI info
        self.roiStartX.value = self.startX
        self.roiStartY.value = self.startY
        self.roiEndX.value = self.endX
        self.roiEndY.value = self.endY
        self.roiBool.value = self.fitSubSpace