# -*- coding: utf-8 -*-
"""
Created on 20/10/2016 9:56 AM
Part of: experimentEagle
Filename: standardAndor0.py
@author: tharrison


"""

import processors
import logging
import scipy
logger=logging.getLogger("ExperimentEagle.Processor")
import os
import collections
import numpy as np
import time

import traits.api as traits
import chaco.api as chaco

class BaslerOD(processors.Processor):
    """ default processor to use when running ANDOR0 camera"""

    optionsDict = collections.OrderedDict((("process?",True),
                                          ("rotationAngle",0.0),))
    #darkImagePath = os.path.join("\\\\ursa", "AQOGroupFolder", "Experiment Humphry", "Experiment Control and Software", "darkImages", "darkAverageData", "2016-10-20","2016-10-20-darkAverage.gz" )

    def process(self,rawImagePath):
        if rawImagePath.split("_")[-1] == "atoms.png":        
            try_var = 0
            while True:            
                try:
                    self.atomsArray = self.read(rawImagePath)
                    time.sleep(1.0)
                    self.lightArray = self.read(rawImagePath.split("atoms.png")[0]+"light.png")
                    #os.remove(rawImagePath.split("atoms.png")[0]+"light.png") # remove light picture
                    break
                except IOError:
                    try_var += 1                    
                    logger.warning( "Light picture not yet taken. Try again in 1s. Tried %i times" %try_var )
                    if try_var > 2:                    
                        return self.read(rawImagePath)
        else:
            logger.info( "Found light picture first.. showing only light picture." )
            self.lightArray = self.read(rawImagePath)
            return self.lightArray
            
        if not self.optionsDict["process?"]:
            return self.atomsArray            
        #[self.atomsArray, self.lightArray] = self.fastKineticsCrop(rawArray, 2)        
        # logger.info("atomsArray = %s" % self.atomsArray)
        # logger.info("lightArray = %s" % self.lightArray)
        # logger.info("atomsArray/lightArray = %s" % (self.atomsArray / self.lightArray))
        opticalDensity = self.opticalDensity(self.atomsArray,self.lightArray)
        # logger.info("optical density = %s" % opticalDensity)
        self.opticalDensityArray = self.rotate(opticalDensity, self.optionsDict["rotationAngle"])
        return self.opticalDensityArray

#    def drawRescaleRegion(self, framePlot):
#        if self.optionsDict["rescale?"]:
#            if True:
#                # create line polygon plot to display fit region
#                points = np.asarray([
#                    [   self.optionsDict["rescaleInitialX"], self.optionsDict["rescaleInitialX"]+self.optionsDict["rescaleWidth"],
#                        self.optionsDict["rescaleInitialX"]+self.optionsDict["rescaleWidth"], self.optionsDict["rescaleInitialX"]    ],
#                    [   self.optionsDict["rescaleInitialY"], self.optionsDict["rescaleInitialY"],
#                        self.optionsDict["rescaleInitialY"]+self.optionsDict["rescaleHeight"],
#                        self.optionsDict["rescaleInitialY"]+self.optionsDict["rescaleHeight"]   ]
#                ])
#                phi = self.optionsDict["rotationAngle"] * np.pi / 180.
#                rotMatrix = np.asarray([
#                    [np.cos(phi), np.sin(phi)],
#                    [-np.sin(phi), np.cos(phi)]
#                ])
#                print points
#                # get old and new dimensions for scale and center of image
#                widthOld = self.atomsArray.shape[0]
#                heightOld = self.atomsArray.shape[1]
#                width = self.opticalDensityArray.shape[0]
#                height = self.opticalDensityArray.shape[1]
#                # rotate around center
#                points[0] = points[0] - widthOld/2.
#                points[1] = points[1] - heightOld/2.
#                points = rotMatrix.dot(points)
#                points[0] = points[0] + width/2.
#                points[1] = points[1] + height/2.
#                rescaleRegionFrameXs = chaco.ArrayDataSource( points[0] )
#                rescaleRegionFrameYs = chaco.ArrayDataSource( points[1] )
#                framePlot.index = rescaleRegionFrameXs
#                framePlot.value = rescaleRegionFrameYs
#                framePlot.visible = self.optionsDict["drawRescaleRegion?"]
#                self.framePlot = framePlot
        
#    def alphaFunction(self,opticalDensity):
#        highODPolynomial = scipy.poly1d([0.4894, -2.059,  2.825,0.9525,0])
#        return highODPolynomial(opticalDensity)
        
#    def fittedAlphaFunctionAlternate(self,opticalDensity):
#        """using polyfit function with a cubic we get a reasonable approximation to
#        alpha as a function of optical density. I force alpha to 1 at optical density < 0.5. 
#        Function uses poly1d object so is good for arrays"""
#        lowODLimit = 0.5
#        highODPolynomial = scipy.poly1d([0.2496, -0.5873, 0.3939,1.572])
#        lowODPolynomial = scipy.poly1d([2*(highODPolynomial(lowODLimit)-1),1.0])
#        return scipy.piecewise(opticalDensity, [opticalDensity<lowODLimit,opticalDensity>=lowODLimit],[lowODPolynomial,highODPolynomial])
        
if __name__=="__main__":
    import matplotlib.pyplot as plt
    p=StandardAndor0()
    ods = scipy.linspace(0, 5)
    alphas1=p.fittedAlphaFunctionAlternate(ods)
    alphas2=p.alphaFunction(ods)
    plt.plot(ods,ods*alphas1, label="alpha alt")
    plt.plot(ods,alphas2, label="alpha std")
    plt.legend()