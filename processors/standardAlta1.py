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

defaultDarkImagePath = os.path.join("calibration", "darkPictures", "Andor0", "2016-10-20-darkAverage.npy")
if not os.path.exists(defaultDarkImagePath):
    defaultDarkImagePath = os.path.join("\\\\ursa", "AQOGroupFolder", "Experiment Humphry", "Experiment Control and Software", "darkImages", "darkAverageData", "2016-10-20","2016-10-20-darkAverage.gz" )

def binArray(data, axis, binstep, binsize, func=np.nanmean):
    """
    from https://stackoverflow.com/questions/21921178/binning-a-numpy-array/42024730#42024730
    data    ---  is your array
    axis    ---  is the axis you want to been
    binstep ---  is the number of points between each bin (allow overlapping bins)
    binsize ---  is the size of each bin

    func    ---  is the function you want to apply to the bin (np.max for maxpooling, np.mean for an average ...)"""
    
    data = np.array(data)
    dims = np.array(data.shape)
    argdims = np.arange(data.ndim)
    argdims[0], argdims[axis]= argdims[axis], argdims[0]
    data = data.transpose(argdims)
    data = [func(np.take(data,np.arange(int(i*binstep),int(i*binstep+binsize)),0),0) for i in np.arange(dims[axis]//binstep)]
    data = np.array(data).transpose(argdims)
    return data

class StandardAlta1(processors.Processor):
    """ default processor to use when running ANDOR0 camera"""

    optionsDict = collections.OrderedDict((
        ("process?",True),("darkSubtraction?",True),("rawImageWithDarkSubtraction?", False),
        ("rescale?",False),("rescaleInitialX",450),("rescaleInitialY",300),("rescaleWidth",50), ("rescaleHeight",100),("drawRescaleRegion?",True),
        ("rotationAngle",0.0),
        ("Binning?",False),("Bin size",2),
    ))

    def process(self,rawImagePath):
        logger.info("using standard Alta 1 process function")
        rawImageAtomPath = rawImagePath
        rawImageDarkPath = rawImagePath.replace("atoms","dark")
        rawImageLightPath = rawImagePath.replace("atoms","light")
        
        logger.error(rawImageAtomPath)
        logger.error(rawImageDarkPath)
        logger.error(rawImageLightPath)

        if not (os.path.exists(rawImageDarkPath) and os.path.exists(rawImageLightPath)):
            logger.error("Dark or Light picture does not exist!")
            return self.read(rawImageAtomPath)

        self.atomsArray = self.read(rawImageAtomPath)
        self.lightArray = self.read(rawImageLightPath)
        logger.error("atoms array mean:{}".format(np.mean(self.atomsArray)))
        logger.error("light array mean:{}".format(np.mean(self.lightArray)))
        if not self.optionsDict["process?"]:
            return self.atomsArray
        if self.optionsDict["darkSubtraction?"]:
            self.darkArray = self.read(rawImageDarkPath)
            logger.error("dark array mean:{}".format(np.mean(self.darkArray)))
            self.atomsArray -= self.darkArray
            self.atomsArray = self.atomsArray.clip(1)
            self.lightArray -= self.darkArray
            self.lightArray = self.lightArray.clip(1)
        if self.optionsDict["rawImageWithDarkSubtraction?"]:
            return self.atomsArray
        if self.optionsDict["rescale?"]:
            self.lightArray = self.rescale(self.optionsDict["rescaleInitialX"],self.optionsDict["rescaleInitialY"],
                                self.optionsDict["rescaleWidth"],self.optionsDict["rescaleHeight"],
                                self.lightArray, self.atomsArray)
            self.atomsArray = self.rescale(self.optionsDict["rescaleInitialX"],self.optionsDict["rescaleInitialY"],
                         self.optionsDict["rescaleWidth"],self.optionsDict["rescaleHeight"],
                         self.atomsArray, self.lightArray)
        if self.optionsDict["Binning?"]:
            self.atomsArray = self.binning(self.atomsArray,self.optionsDict["Bin size"])
            self.lightArray = self.binning(self.lightArray,self.optionsDict["Bin size"])
        
        # logger.info("atomsArray = %s" % self.atomsArray)
        # logger.info("lightArray = %s" % self.lightArray)
        # logger.info("atomsArray/lightArray = %s" % (self.atomsArray / self.lightArray))
        opticalDensity = self.opticalDensity(self.atomsArray,self.lightArray)
        logger.error("OD mean:{}".format(np.mean(opticalDensity)))
        self.opticalDensityArray = self.rotate(opticalDensity, self.optionsDict["rotationAngle"])

        return self.opticalDensityArray

    def drawRescaleRegion(self, framePlot):
        if self.optionsDict["rescale?"]:
            logger.warning("drawRescaleRegion")
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
    
    @staticmethod
    def binning(array, binsize=2):
        data_binned = binArray(array, 0, binsize, binsize, np.mean)
        data_binned = binArray(data_binned, 1, binsize, binsize, np.mean)
        return data_binned
        
# if __name__=="__main__":
#     import matplotlib.pyplot as plt
#     p=StandardAndor0()
#     ods = scipy.linspace(0, 5)
#     alphas1=p.fittedAlphaFunctionAlternate(ods)
#     alphas2=p.alphaFunction(ods)
#     plt.plot(ods,ods*alphas1, label="alpha alt")
#     plt.plot(ods,alphas2, label="alpha std")
#     plt.legend()