# -*- coding: utf-8 -*-
"""
Created on 20/10/2016 12:58 PM
Part of: experimentEagle
Filename: deubgProcessors.py
@author: tharrison


"""

import processors
import logging
import scipy
import collections
import os
logger=logging.getLogger("ExperimentEagle.Processor")


class DEBUGAtomsOverLight(processors.Processor):
    """debug processor, shows atoms/light with dark subtractions"""
    optionsDict = collections.OrderedDict((("process?", True), ("darkSubtraction?", True),("correct OD with alpha function?",True) ))
    darkImagePath = os.path.join("\\\\ursa", "AQOGroupFolder", "Experiment Humphry", "Experiment Control and Software",
                                 "darkImages", "darkAverageData", "2016-10-20", "2016-10-20-darkAverage.gz")
    def processDebug1(self,rawImagePath):
        logger.info("using standard Andor 0 process function")
        rawArray = self.read(rawImagePath)
        if not self.optionsDict["process?"]:
            return rawArray
        [atomsArray,lightArray] = self.fastKineticsCrop(rawArray, 2)
        if self.optionsDict["darkSubtraction"]:
            darkArray = self.loadDarkImage(self.darkImagePath)
            rawArray -= darkArray
            rawArray.clip(1)
        logger.info("atomsArray = %s" % atomsArray)
        logger.info("lightArray = %s" % lightArray)
        logger.info("atomsArray/lightArray = %s" % (atomsArray/lightArray))
        logger.info("min , max atoms = %s, %s" % (scipy.nanmin(atomsArray),scipy.nanmax(atomsArray)))
        logger.info("min , max light = %s, %s" % (scipy.nanmin(lightArray), scipy.nanmax(lightArray)))
        logger.info("min , max atoms/light = %s, %s" % (scipy.nanmin(atomsArray/lightArray), scipy.nanmax(atomsArray/lightArray)))
        corrected = atomsArray/lightArray
        if self.optionsDict["rotate?"]:
            rotated = self.rotate(corrected, self.optionsDict["rotationAngle"])
        return rotated

    def process(self,rawImagePath):
        opticalDensity = self.read(rawImagePath)
        opticalDensity = self.scale(opticalDensity,10089.33, 5000)
        if self.optionsDict["correct OD with alpha function?"]:
            opticalDensity = self.alphaFunction(opticalDensity)
        return opticalDensity
            
    def alphaFunction(self,opticalDensity):
        lowODLimit = 0.5
        highODPolynomial = scipy.poly1d([0.4894, -2.059,  2.825,0.9525,0])
        #return scipy.piecewise(opticalDensity, [opticalDensity<lowODLimit,opticalDensity>=lowODLimit],[lambda opticalDensity:opticalDensity,highODPolynomial])
        return highODPolynomial(opticalDensity)

    def fittedAlphaFunction1(self,opticalDensity):
        """using polyfit function with a cubic we get a reasonable approximation to
        alpha as a function of optical density. I force alpha to 1 at optical density < 0.5. 
        Function uses poly1d object so is good for arrays"""
        lowODLimit = 0.5
        highODPolynomial = scipy.poly1d([0.2496, -0.5873, 0.3939,1.572])
        lowODPolynomial = scipy.poly1d([2*(highODPolynomial(lowODLimit)-1),1.0])
        return scipy.piecewise(opticalDensity, [opticalDensity<lowODLimit,opticalDensity>=lowODLimit],[lowODPolynomial,highODPolynomial])
     
     
if __name__=="__main__":
    import pylab
    p=DEBUGAtomsOverLight()
    xs = pylab.linspace(0,4,100)
    ys = p.alphaFunction(xs)
    pylab.plot(xs,ys,"r-")
     