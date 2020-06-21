# -*- coding: utf-8 -*-
"""
Created on 20/10/2016 9:56 AM
Part of: experimentEagle
Filename: standardAndor1.py
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

defaultDarkImagePath = os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry","Experiment Control and Software","experimentEagle","calibration","darkPictures","Andor1","2018 07 12 - dark ANDOR1.gz")

class Andor1ThreePulses(processors.Processor):
    """ default processor to use when running ANDOR1 camera"""

    optionsDict = collections.OrderedDict((("process?",True),("darkSubtraction?",True),("rawImageWithDarkSubtraction?", False),
                                          ("rescale?",True),("rescaleInitialX",350),("rescaleInitialY",100),("rescaleWidth",100), ("rescaleHeight",100),
                                          ("rotationAngle",-45.0),
                                          ("Skip initial rows",1),
                                          ("Skip final rows",3),
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
                                          ("Dark picture",defaultDarkImagePath)
                                          ))
    

    def process(self,rawImagePath):
        logger.info("using standard Andor 0 process function")
        rawArray = self.read(rawImagePath)
        if not self.optionsDict["process?"]:
            return rawArray
        if self.optionsDict["Use boosted light image?"]:
            darkArray = self.loadDarkImage(self.optionsDict["Dark picture"]) if self.optionsDict["darkSubtraction?"] else np.zeros( rawArray.shape )
            opticalDensity = self.opticalDensityStrongerLightPicture(rawArray, darkArray, self.optionsDict["Light boost factor"])
        else:
            if self.optionsDict["darkSubtraction?"]:
                darkArray = self.loadDarkImage(self.optionsDict["Dark picture"])
                try:
                    rawArray -= darkArray
                except ValueError:
                    logger.error("rawArray {} and darkArray {} have different shape".format( rawArray.shape, darkArray.shape ))
                    # in this case, the reason is that the total number of rows is int(1024/3)*3 = 1023
                    # => neglect last row of dark picture (TODO: double check, that it's not the first instead)
                    rawArray -= darkArray[:-1]
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
                self.rescale(self.optionsDict["rescaleInitialX"],self.optionsDict["rescaleInitialY"],
                            self.optionsDict["rescaleWidth"],self.optionsDict["rescaleHeight"],
                            atomsArray, lightArray)
            if self.optionsDict["Binning?"]:
                atomsArray = self.binning(atomsArray,self.optionsDict["Bin size"])
                lightArray = self.binning(lightArray,self.optionsDict["Bin size"])
            
            logger.debug("atomsArray = %s" % atomsArray)
            logger.debug("lightArray = %s" % lightArray)
            logger.debug("atomsArray/lightArray = %s" % (atomsArray / lightArray))
            opticalDensity = self.opticalDensity(atomsArray,lightArray)
        if self.optionsDict["correct OD with alpha function?"]:
            opticalDensity = self.alphaFunction(opticalDensity)
        logger.debug("optical density = %s" % opticalDensity)
        opticalDensity = self.rotate(opticalDensity, self.optionsDict["rotationAngle"])
        return opticalDensity
    
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
        atomStartPx = 340
        atomEndPx = 511
        lightStartPx = 682
        lightEndPx = 853
        pic1 = rawArray[atomStartPx+self.optionsDict["Skip initial rows"]:atomEndPx-self.optionsDict["Skip final rows"]] # e.g. [0:512] -> 0-511
        pic2 = rawArray[lightStartPx+self.optionsDict["Skip initial rows"]:lightEndPx-self.optionsDict["Skip final rows"]] # e.g. [512:1024] -> 512-1023
        return pic1, pic2
    
    @staticmethod
    def binning(array, binsize=2):
        data_binned = binArray(array, 0, binsize, binsize, np.mean)
        data_binned = binArray(data_binned, 1, binsize, binsize, np.mean)
        return data_binned


        
if __name__=="__main__":
    import matplotlib.pyplot as plt
    p=Andor1ThreePulses()
    ods = scipy.linspace(0, 5)
    alphas1=p.fittedAlphaFunctionAlternate(ods)
    alphas2=p.alphaFunction(ods)
    plt.plot(ods,ods*alphas1, label="alpha alt")
    plt.plot(ods,alphas2, label="alpha std")
    plt.legend()