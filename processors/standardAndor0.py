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

import traits.api as traits
import chaco.api as chaco

defaultDarkImagePath = os.path.join("calibration", "darkPictures", "Andor0", "2016-10-20-darkAverage.npy")
if not os.path.exists(defaultDarkImagePath):
    defaultDarkImagePath = os.path.join("\\\\ursa", "AQOGroupFolder", "Experiment Humphry", "Experiment Control and Software", "darkImages", "darkAverageData", "2016-10-20","2016-10-20-darkAverage.gz" )

class StandardAndor0(processors.Processor):
    """ default processor to use when running ANDOR0 camera"""

    optionsDict = collections.OrderedDict((("process?",True),("darkSubtraction?",True),("rawImageWithDarkSubtraction?", False),
                                          ("rescale?",False),("rescaleInitialX",450),("rescaleInitialY",300),("rescaleWidth",50), ("rescaleHeight",100),("drawRescaleRegion?",True),
                                          ("rotationAngle",-47.8),
                                          ("Dark picture",defaultDarkImagePath),
                                          ("correct OD with alpha function?",False)))

    def process(self,rawImagePath):
        logger.info("using standard Andor 0 process function")
        rawArray = self.read(rawImagePath)
        if not self.optionsDict["process?"]:
            return rawArray
        if self.optionsDict["darkSubtraction?"]:
            loadDarkPic = True
            if hasattr(self,'darkArray'):
                if self.darkPictureFilename == self.optionsDict["Dark picture"]:
                    loadDarkPic = False # already loaded dark picture with same path
            if loadDarkPic:
                _, ext = os.path.splitext( self.optionsDict["Dark picture"] )
                if ext == '.npy':
                    self.darkArray = np.load(self.optionsDict["Dark picture"])
                    self.darkPictureFilename = self.optionsDict["Dark picture"]
                elif ext == '.gz':
                    logger.warning('loading ".gz" picture .. is .. very .. slow .., better use numpy file ".npy"')
                    self.darkArray = self.loadDarkImage(self.optionsDict["Dark picture"])
                    self.darkPictureFilename = self.optionsDict["Dark picture"]
                else:
                    raise TypeError("Invalid file extension: '" + ext + "'")
            try:
                rawArray -= self.darkArray
            except ValueError:
                logger.error("rawArray {} and darkArray {} have different shape".format( rawArray.shape, self.darkArray.shape ))
            rawArray=rawArray.clip(1)
        if self.optionsDict["rawImageWithDarkSubtraction?"]:
            return rawArray
        [self.atomsArray, self.lightArray] = self.fastKineticsCrop(rawArray, 2)
        if self.optionsDict["rescale?"]:
            self.atomsArray = self.rescale(self.optionsDict["rescaleInitialX"],self.optionsDict["rescaleInitialY"],
                         self.optionsDict["rescaleWidth"],self.optionsDict["rescaleHeight"],
                         self.atomsArray, self.lightArray)
        
        # logger.info("atomsArray = %s" % self.atomsArray)
        # logger.info("lightArray = %s" % self.lightArray)
        # logger.info("atomsArray/lightArray = %s" % (self.atomsArray / self.lightArray))
        opticalDensity = self.opticalDensity(self.atomsArray,self.lightArray)
        if self.optionsDict["correct OD with alpha function?"]:
            opticalDensity = self.alphaFunction(opticalDensity)
        # logger.info("optical density = %s" % opticalDensity)
        self.opticalDensityArray = self.rotate(opticalDensity, self.optionsDict["rotationAngle"])
        return self.opticalDensityArray

    def drawRescaleRegion(self, framePlot):
        if self.optionsDict["rescale?"]:
            if True:
                # create line polygon plot to display fit region
                points = np.asarray([
                    [   self.optionsDict["rescaleInitialX"], self.optionsDict["rescaleInitialX"]+self.optionsDict["rescaleWidth"],
                        self.optionsDict["rescaleInitialX"]+self.optionsDict["rescaleWidth"], self.optionsDict["rescaleInitialX"]    ],
                    [   self.optionsDict["rescaleInitialY"], self.optionsDict["rescaleInitialY"],
                        self.optionsDict["rescaleInitialY"]+self.optionsDict["rescaleHeight"],
                        self.optionsDict["rescaleInitialY"]+self.optionsDict["rescaleHeight"]   ]
                ])
                phi = self.optionsDict["rotationAngle"] * np.pi / 180.
                rotMatrix = np.asarray([
                    [np.cos(phi), np.sin(phi)],
                    [-np.sin(phi), np.cos(phi)]
                ])
                print points
                # get old and new dimensions for scale and center of image
                widthOld = self.atomsArray.shape[0]
                heightOld = self.atomsArray.shape[1]
                width = self.opticalDensityArray.shape[0]
                height = self.opticalDensityArray.shape[1]
                # rotate around center
                points[0] = points[0] - widthOld/2.
                points[1] = points[1] - heightOld/2.
                points = rotMatrix.dot(points)
                points[0] = points[0] + width/2.
                points[1] = points[1] + height/2.
                rescaleRegionFrameXs = chaco.ArrayDataSource( points[0] )
                rescaleRegionFrameYs = chaco.ArrayDataSource( points[1] )
                framePlot.index = rescaleRegionFrameXs
                framePlot.value = rescaleRegionFrameYs
                framePlot.visible = self.optionsDict["drawRescaleRegion?"]
                self.framePlot = framePlot
        
    def alphaFunction(self,opticalDensity):
        highODPolynomial = scipy.poly1d([0.4894, -2.059,  2.825,0.9525,0])
        return highODPolynomial(opticalDensity)
        
    def fittedAlphaFunctionAlternate(self,opticalDensity):
        """using polyfit function with a cubic we get a reasonable approximation to
        alpha as a function of optical density. I force alpha to 1 at optical density < 0.5. 
        Function uses poly1d object so is good for arrays"""
        lowODLimit = 0.5
        highODPolynomial = scipy.poly1d([0.2496, -0.5873, 0.3939,1.572])
        lowODPolynomial = scipy.poly1d([2*(highODPolynomial(lowODLimit)-1),1.0])
        return scipy.piecewise(opticalDensity, [opticalDensity<lowODLimit,opticalDensity>=lowODLimit],[lowODPolynomial,highODPolynomial])
        
if __name__=="__main__":
    import matplotlib.pyplot as plt
    p=StandardAndor0()
    ods = scipy.linspace(0, 5)
    alphas1=p.fittedAlphaFunctionAlternate(ods)
    alphas2=p.alphaFunction(ods)
    plt.plot(ods,ods*alphas1, label="alpha alt")
    plt.plot(ods,alphas2, label="alpha std")
    plt.legend()