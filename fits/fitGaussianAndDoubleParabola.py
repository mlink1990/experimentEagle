# -*- coding: utf-8 -*-
"""
Created on Mon Sep 12 12:47:17 2016

@author: User
"""

"""
Fit function for 2-parabola profile4
"""

from fits import Fit, Parameter, CalculatedParameter
import scipy
import logging

logger = logging.getLogger("ExperimentEagle.fits")


class GaussianAndDoubleParabolaFit(Fit):
    def __init__(self, **traitsDict):
        super(GaussianAndDoubleParabolaFit, self).__init__(**traitsDict)
        self.function = """AGauss*scipy.exp(-(positions[0]-x0)**2/(2.*sigmax**2)-(positions[1]-y0)**2/(2.*sigmay**2))+
               AParab_1*(1-((positions[0]-(x0+distX/2.0))/wParabX_1)**2-((positions[1]-(y0+distY/2.0))/wParabY_1)**2).clip(0)**(1.5)+
               AParab_2*(1-((positions[0]-(x0-distX/2.0))/wParabX_2)**2-((positions[1]-(y0-distY/2.0))/wParabY_2)**2).clip(0)**(1.5) + B"""
        self.name = "2D Gaussian + double Parabola"

        self.x0 = Parameter(name="x0")
        self.y0 = Parameter(name="y0")
        self.distX = Parameter(name="distX")
        self.distY = Parameter(name="distY")
        self.AGauss = Parameter(name="AGauss")
        self.sigmax = Parameter(name="sigmax")
        self.sigmay = Parameter(name="sigmay")
        self.AParab_1 = Parameter(name="AParab_1")
        self.wParabX_1 = Parameter(name="wParabX_1")
        self.wParabY_1 = Parameter(name="wParabY_1")
        self.AParab_2 = Parameter(name="AParab_2")
        self.wParabX_2 = Parameter(name="wParabX_2")
        self.wParabY_2 = Parameter(name="wParabY_2")
        self.B = Parameter(name="B")

        self.variablesList = [self.x0, self.y0, self.distX, self.distY, self.AGauss, self.sigmax, self.sigmay,
                              self.AParab_1, self.wParabX_1, self.wParabY_1, self.AParab_2, self.wParabX_2,
                              self.wParabY_2, self.B]

        #        self.summedOD_1 = CalculatedParameter(name="Summed OD", desc="Optical density summed in the calculated region. Clipped at 0. (i.e. does not count negatives)")
        #        self.summedODAtomNumber_1 = CalculatedParameter(name="Summed OD Atom Number", desc="Using optical density summed in the calculated region we calculate an estimate of atom number. Clipped at 0. (i.e. does not count negatives)")
        #
        #        self.summedOD_2 = CalculatedParameter(name="Summed OD", desc="Optical density summed in the calculated region. Clipped at 0. (i.e. does not count negatives)")
        #        self.summedODAtomNumber_2 = CalculatedParameter(name="Summed OD Atom Number", desc="Using optical density summed in the calculated region we calculate an estimate of atom number. Clipped at 0. (i.e. does not count negatives)")

        self.summedOD_total = CalculatedParameter(name="Summed OD",
                                                  desc="Optical density summed in the calculated region. Clipped at 0. (i.e. does not count negatives)")
        self.summedODAtomNumber_total = CalculatedParameter(name="Summed OD Atom Number",
                                                            desc="Using optical density summed in the calculated region we calculate an estimate of atom number. Clipped at 0. (i.e. does not count negatives)")

        self.condensateFraction = CalculatedParameter(name="Condensate Fraction",
                                                      desc="Condensate fraction, where condensate is calculated from both parabolas")
        self.parabolaRatio = CalculatedParameter(name="Parabola ratio", desc="Ratio of atom number in parabolas.")

        self.NThermal = CalculatedParameter(name="NThermal", desc="Generic")
        self.NCondensate_1 = CalculatedParameter(name="NCondensate_1", desc="Generic")
        self.NCondensate_2 = CalculatedParameter(name="NCondensate_2", desc="Generic")
        self.NCondensate = CalculatedParameter(name="NCondensate", desc="Generic")
        self.N = CalculatedParameter(name="N", desc="Generic")
        self.k = CalculatedParameter(name="k", desc="momentum in SI units for k (wave number)")

        self.calculatedParametersList = [self.NThermal, self.NCondensate_1, self.NCondensate_2, self.NCondensate,
                                         self.N, self.condensateFraction, self.parabolaRatio, self.k]

    @staticmethod
    def fitFunc(positions, x0, y0, distX, distY, AGauss, sigmax, sigmay, AParab_1, wParabX_1, wParabY_1, AParab_2,
                wParabX_2, wParabY_2, B):
        """ Gaussian + Parabola
        data is a 2 row array of positions
        e.g.
        0 1 2 3 4 5 0 1 2 3 4 5...
        0 0 0 0 0 0 1 1 1 1 1 1...    
        so data[0] is x
        data[1] is y
        Note that we must clip the parabola to 0 otherwise we would take the square root of negative number
        """
        #        return AGauss*scipy.exp(-(positions[0]-x0)**2/(2.*sigmax**2)-(positions[1]-y0)**2/(2.*sigmay**2))+AParab*((1-((positions[0]-x0)/wParabX)**2-((positions[1]-y0)/wParabY)**2).clip(0)**(1.5))+B
        return AGauss * scipy.exp(
            -(positions[0] - x0) ** 2 / (2. * sigmax ** 2) - (positions[1] - y0) ** 2 / (2. * sigmay ** 2)) + \
               AParab_1 * (1 - ((positions[0] - (x0 + distX / 2.0)) / wParabX_1) ** 2 - (
               (positions[1] - (y0 + distY / 2.0)) / wParabY_1) ** 2).clip(0) ** (1.5) + \
               AParab_2 * (1 - ((positions[0] - (x0 - distX / 2.0)) / wParabX_2) ** 2 - (
               (positions[1] - (y0 - distY / 2.0)) / wParabY_2) ** 2).clip(0) ** (1.5) + B

    def _deriveCalculatedParameters(self):
        """"Updates all the calculated parameters """

        # useful constants
        imagePixelArea = (
                         self.physics.pixelSize / self.physics.magnification * self.physics.binningSize * 1.0E-6) ** 2.0  # area of a pixel in m^2 accounts for magnification
        logger.info("imagePixelArea integral in m^2 = %G" % imagePixelArea)
        m = self.physics.selectedElement.massATU * self.physics.u
        sigmax = abs(self.sigmax.calculatedValue)
        sigmay = abs(self.sigmay.calculatedValue)
        wParabX_1 = abs(self.wParabX_1.calculatedValue)
        wParabY_1 = abs(self.wParabY_1.calculatedValue)
        wParabX_2 = abs(self.wParabX_2.calculatedValue)
        wParabY_2 = abs(self.wParabY_2.calculatedValue)

        # atom number N
        # NThermal
        # integral under gaussian function. Then multiply by factors to get atoms contained in thermal part
        gaussianIntegral = 2.0 * scipy.pi * self.AGauss.calculatedValue * sigmax * sigmay  # ignores background B
        logger.info("gaussian integral in pixels = %G" % gaussianIntegral)
        NThermal = (gaussianIntegral * imagePixelArea) * (
        1.0 + 4.0 * self.physics.imagingDetuningLinewidths ** 2) / self.physics.selectedElement.crossSectionSigmaPlus
        self.NThermal.value = NThermal

        # NCondensate
        # integral under clipped parabola ^3/2
        parabolaIntegral_1 = 0.4 * scipy.pi * self.AParab_1.calculatedValue * wParabX_1 * wParabY_1  # ignores background B
        logger.info("parabolaIntegral 1 in pixels = %G" % parabolaIntegral_1)
        NCondensate_1 = (parabolaIntegral_1 * imagePixelArea) * (
        1.0 + 4.0 * self.physics.imagingDetuningLinewidths ** 2) / self.physics.selectedElement.crossSectionSigmaPlus
        self.NCondensate_1.value = NCondensate_1

        parabolaIntegral_2 = 0.4 * scipy.pi * self.AParab_2.calculatedValue * wParabX_2 * wParabY_2  # ignores background B
        logger.info("parabolaIntegral 2 in pixels = %G" % parabolaIntegral_2)
        NCondensate_2 = (parabolaIntegral_2 * imagePixelArea) * (
        1.0 + 4.0 * self.physics.imagingDetuningLinewidths ** 2) / self.physics.selectedElement.crossSectionSigmaPlus
        self.NCondensate_2.value = NCondensate_2

        # total atom number N
        N = NThermal + NCondensate_1 + NCondensate_2
        self.N.value = N

        # CondensateFraction

        self.NCondensate.value = NCondensate_1 + NCondensate_2
        self.condensateFraction.value = self.NCondensate.value / N

        # ParabolaRatio
        self.parabolaRatio.value = NCondensate_1 / NCondensate_2

        # calculate momentum of peaks
        imagePixelLength = 1E-6 * self.physics.pixelSize / self.physics.magnification * self.physics.binningSize
        separationPixels = (self.distX.calculatedValue ** 2 + self.distY.calculatedValue ** 2) ** 0.5
        separationDistance = separationPixels * imagePixelLength
        logger.info("separationDistance = %s" % separationDistance)
        TOFTime = self.physics.timeOfFlightTimems * 0.001
        logger.info("TOFTime = %s" % TOFTime)
        m = self.physics.selectedElement.massATU * self.physics.u
        kMeasured = (m * separationDistance) / (2. * TOFTime * self.physics.hbar)  # in  SI units
        self.k.value = kMeasured


        # summedOD_total
        # summedOD_total = (summedOD_total*imagePixelArea)*(1.0+4.0*self.physics.imagingDetuningLinewidths**2)/self.physics.selectedElement.crossSectionSigmaPlus
        # self.summedOD_total.value = summedOD_total

    def _getIntelligentInitialValues(self):
        xs, ys, zs = self._get_subSpaceArrays()  # returns the full arrays if subspace not used
        logger.debug("attempting to set initial values intellgently")
        if xs is None or ys is None or zs is None:
            logger.debug("couldn't find all necessary data")
            return False

        left_half = xs[0:len(xs) / 2]
        right_half = xs[len(xs / 2):len(xs)]

        # left and right half of the picture
        zs_left = [z_slice[0:len(xs) / 2] for z_slice in zs]
        zs_right = [z_slice[len(xs) / 2:len(xs)] for z_slice in zs]  # That's right!

        AParab_1 = scipy.amax(zs_left)
        AParab_2 = scipy.amax(zs_right)
        index_flattened = scipy.argmax(zs_left)

        maxIndex_1 = (index_flattened / len(left_half), index_flattened % len(left_half))  # indicex (y, x)

        index_flattened = scipy.argmax(zs_right)
        maxIndex_2 = (index_flattened / len(right_half), index_flattened % len(right_half))  # indicex (y, x)

        A = zs_left[maxIndex_1[0]][len(left_half) - 1]

        B = scipy.average(zs[0:len(ys) / 10.0, 0:len(xs) / 10.0])

        y0Index, x0Index = maxIndex_1[0], len(left_half - 1)

        logger.debug("index of max z is %s, %s " % (y0Index, x0Index))
        x0 = xs[x0Index]
        y0 = ys[y0Index]

        distX = maxIndex_2[1] - maxIndex_1[1]
        distY = 0.01  # usually not very far away from y0
        # WHEN WE IMPLEMENT ONLY FITTING A SUBSET THIS WILL HAVE TO CHANGE A BIT
        x0HalfIndex = (scipy.absolute(zs[y0Index] - A / 2.0)).argmin()
        y0HalfIndex = (scipy.absolute(zs[:, x0Index] - A / 2.0)).argmin()
        logger.debug("index of half max z is %s, %s " % (y0HalfIndex, x0HalfIndex))
        x0Half = xs[x0HalfIndex]
        y0Half = ys[y0HalfIndex]
        FWHMX0 = 2.0 * abs(x0 - x0Half)
        FWHMY0 = 2.0 * abs(y0 - y0Half)

        # make gaussian wings larger for thermal part (*4)
        sigmax = 4 * FWHMX0 / 2.355
        sigmay = 4 * FWHMY0 / 2.355
        wParabX_1 = FWHMX0 / 2.0
        wParabY_1 = FWHMY0 / 2.0
        wParabX_2 = FWHMX0 / 2.0
        wParabY_2 = FWHMY0 / 2.0
        AGauss = 0.1 * A
        AParab_1 = 0.9 * A
        AParab_2 = 0.9 * A

        p0 = [x0, y0, distX, distY, AGauss, sigmax, sigmay, AParab_1, wParabX_1, wParabY_1, AParab_2, wParabX_2,
              wParabY_2, B]
        logger.debug("initial values guess = %s" % p0)
        return p0
