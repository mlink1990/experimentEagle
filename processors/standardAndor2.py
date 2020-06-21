# -*- coding: utf-8 -*-
"""
Created on 20/10/2016 9:56 AM
Part of: experimentEagle
Filename: standardAndor1.py
@author: tharrison


"""
import logging
import os
import collections
import time

import scipy
import numpy as np

import traits.api as traits
import chaco.api as chaco

import processors

logger=logging.getLogger("ExperimentEagle.Processor")

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

defaultDarkImagePath = os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry","Experiment Control and Software","experimentEagle","calibration","darkPictures","Andor2","2020 02 24 - dark Andor2 - interval 0_01 temperature -80_0 .npy")

class StandardAndor2(processors.Processor):
    """ default processor to use when running ANDOR1 camera"""

    optionsDict = collections.OrderedDict((("process?",True),("darkSubtraction?",True),("rawImageWithDarkSubtraction?", False),
                                          ("rescale?",False),("rescaleInitialX",400),("rescaleInitialY",700),("rescaleWidth",50), ("rescaleHeight",50),("drawRescaleRegion?",True),
                                          ("rotationAngle",87.8),
                                          ("Skip initial rows",1),
                                          ("Skip final rows",23),
                                          ("Shift Light Picture Vertically by rows",-3),
                                          ("correct OD with alpha function?",False),
                                          ("Rescale with circular mask?",False), # multiply light picture by a factor, to balance imaging light of atom and light picture
                                          ("Atom mask PosX",295), # to determine lightBalanceFactor, the region where atoms could be must be masked
                                          ("Atom mask PosY",295),
                                          ("Atom mask Radius",160),
                                          ("Balance light Radius",200), # Also use a radius to limit the region, which is used to determine lightBalanceFactor
                                          ("Use boosted light image?",False), # if a method is used, which uses a boosted light image, this setting can rescale the light image
                                          ("Light boost factor",1.),
                                          ("Binning?",False),
                                          ("Bin size",2),
                                          ("Dark picture",defaultDarkImagePath),
                                          ("High intensity correction for low OD?",False), # takes the limit of low intensity, assuming constant alpha (thus low OD)
                                          ("alpha",1.25),
                                          ("C0Sat",231), # for 1e-6 s
                                          ("Imaging pulse duration",6e-6)
                                          ))
    
    def getBinningFactor(self):
        """ The factor by which a pixel is larger due to binning """
        return self.optionsDict["Bin size"] if self.optionsDict["Binning?"] else 1

    def process(self,rawImagePath):
        logger.info("using standard Andor 0 process function")
        if rawImagePath.endswith("_X2.tif"):
            for i in range(4):
                try:
                    rawArray2 = self.read(rawImagePath)
                    rawArray1 = self.read(rawImagePath.replace("_X2.tif","_X1.tif"))
                    rawArray = np.vstack( (rawArray1,rawArray2) )
                    break
                except IOError:
                    logger.warning("IOError for loading tif file. Since Andor Solis needs some time to save this picture, wait 1 s and try again. Try {} of 4".format(i+1))
                    time.sleep(1)
                    pass
        else:
            rawArray = self.read(rawImagePath)
        if not self.optionsDict["process?"]:
            return rawArray
        if self.optionsDict["Use boosted light image?"]:
            darkArray = self.loadDarkImage(self.optionsDict["Dark picture"]) if self.optionsDict["darkSubtraction?"] else np.zeros( rawArray.shape )
            opticalDensity = self.opticalDensityStrongerLightPicture(rawArray, darkArray, self.optionsDict["Light boost factor"])
        else:
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
            [atomsArray, lightArray] = self.fastKineticsCrop(rawArray, 2)
            if self.optionsDict["Rescale with circular mask?"]:
                y = np.arange(lightArray.shape[0])
                x = np.arange(lightArray.shape[1])
                x, y = np.meshgrid(x, y)
                distanceSq = (x - self.optionsDict["Atom mask PosX"])*(x - self.optionsDict["Atom mask PosX"]) + (y - self.optionsDict["Atom mask PosY"])*(y - self.optionsDict["Atom mask PosY"])
                indices = np.logical_and( self.optionsDict["Atom mask Radius"]**2 < distanceSq, distanceSq < self.optionsDict["Balance light Radius"]**2 )
                lightBalanceFactor = np.mean( atomsArray[indices] / lightArray[indices] )
                logger.info( "1/lightBalanceFactor = {}".format(1/lightBalanceFactor) ) # change to debug after initial testing phase
                lightArray *= lightBalanceFactor
            elif self.optionsDict["rescale?"]:
                lightArray = self.rescale(self.optionsDict["rescaleInitialX"],self.optionsDict["rescaleInitialY"],
                                self.optionsDict["rescaleWidth"],self.optionsDict["rescaleHeight"],
                                lightArray, atomsArray)
            if self.optionsDict["Binning?"]:
                atomsArray = self.binning(atomsArray,self.optionsDict["Bin size"])
                lightArray = self.binning(lightArray,self.optionsDict["Bin size"])
            
            self.atomsArray = atomsArray.clip(1)
            self.lightArray = lightArray.clip(1)

            logger.debug("atomsArray = %s" % atomsArray)
            logger.debug("lightArray = %s" % lightArray)
            logger.debug("atomsArray/lightArray = %s" % (atomsArray / lightArray))
            opticalDensity = self.opticalDensity(atomsArray,lightArray)
        if self.optionsDict["correct OD with alpha function?"]:
            opticalDensity = self.alphaFunction(opticalDensity)
        elif self.optionsDict["High intensity correction for low OD?"]:
            highIntensityCorrection = (self.lightArray - self.atomsArray) * 1e-6 / self.optionsDict["Imaging pulse duration"] # C0Sat is defined for 1e-6 s
            opticalDensity += highIntensityCorrection / ( self.optionsDict["C0Sat"] * self.optionsDict["alpha"] )
            opticalDensity *= self.optionsDict["alpha"]
        logger.debug("optical density = %s" % opticalDensity)
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
                ]) / self.getBinningFactor()
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
    
    def opticalDensityStrongerLightPicture(self, rawArray, darkArray, lightArrayFactor):
        # idea: Use longer exposure for light picture to reduce noise
        # longer exposure requires different dark subtraction
        # Dark subtraction is done in this funciton, don't do it twice!!
        [atomsArray, lightArray] = self.fastKineticsCrop(rawArray, 2)
        [atomsDarkArray, lightDarkArray] = self.fastKineticsCrop(darkArray, 2)
        lightArray /= lightArrayFactor
        lightArray -= lightDarkArray
        atomsArray -= atomsDarkArray
        return self.opticalDensity( atomsArray, lightArray )
        
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
    
    def fastKineticsCrop(self,rawArray,n):
        """ Atom picture is usually on rows 0-1023, light picture on rows 1024-2047 """
        rowCount = rawArray.shape[0] /2
        atomStart = 0 # inclusive
        atomEnd = rowCount # exclusive
        lightStart = rowCount+self.optionsDict["Shift Light Picture Vertically by rows"] #inclusive
        lightEnd = 2*rowCount+self.optionsDict["Shift Light Picture Vertically by rows"] # exclusive
        skipFinal = max(0,self.optionsDict["Shift Light Picture Vertically by rows"]) + self.optionsDict["Skip final rows"]
        skipInitial = max(0,-self.optionsDict["Shift Light Picture Vertically by rows"]) + self.optionsDict["Skip initial rows"]
        pic1 = rawArray[atomStart+skipInitial:atomEnd-skipFinal]
        pic2 = rawArray[lightStart+skipInitial:lightEnd-skipFinal]
        return pic1, pic2
    
    @staticmethod
    def binning(array, binsize=2):
        data_binned = binArray(array, 0, binsize, binsize, np.mean)
        data_binned = binArray(data_binned, 1, binsize, binsize, np.mean)
        return data_binned


        
if __name__=="__main__":
    import matplotlib.pyplot as plt
    p=StandardAndor2()
    ods = scipy.linspace(0, 5)
    alphas1=p.fittedAlphaFunctionAlternate(ods)
    alphas2=p.alphaFunction(ods)
    plt.plot(ods,ods*alphas1, label="alpha alt")
    plt.plot(ods,alphas2, label="alpha std")
    plt.legend()