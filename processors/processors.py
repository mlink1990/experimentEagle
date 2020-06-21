# -*- coding: utf-8 -*-
"""
Created on 20/10/2016 9:15 AM
Part of: experimentEagle
Filename: processors.py
@author: tharrison


"""
import logging
import collections

import numpy as np
import scipy
import scipy.misc
import scipy.ndimage

import traits.api as traits
import traitsui.api as traitsui

import optionsDictEditor

logger=logging.getLogger("ExperimentEagle.Processor")

class Processor(traits.HasTraits):
    """parent class for image processing. Raw image is received and then the process
     function returns the image experiment eagle should be given / display
     many helper functions such as average, subtract rotate are implemented in the
     process parent class. Children just need to implement their own specific version
     of process and can add their own helper functions as required.

     the options dictionary defines options that can be changed but should all have
     a default value. The options dictionary can be edited from the main GUI
     """

    optionsDict = collections.OrderedDict()
    traits_view = traitsui.View(traitsui.Item("optionsDict", style="custom"))

    def read(self, rawImagePath):
        """ returns array from image file"""
        logger.info("processor reading file!")
        im = scipy.misc.imread(rawImagePath).astype(scipy.float_)
        if len(im.shape) == 3:
            logger.warning("loaded picture is not monochromatic, take mean of color values..")
            im = np.mean(im,axis=2)
        return im

    def scale(self, array, scale, offset):
        """ due to how files are saved we often need to rescale and add offset. This function
        inverts the action of the scaling done by experiment Control"""
        return (array-offset)/scale

    def loadDarkImage(self, darkFilePath):
        """ dark images should be saved using scipy.savetxt(.gz, array)"""
        return scipy.loadtxt( str(darkFilePath) )

    def opticalDensity(self, atomArray, lightArray):
        if atomArray.shape != lightArray.shape:
            logger.error("shape of atom and light images is not the same. Cannot proceed. Stopping processing")
            return None
        if (not scipy.all(atomArray>=0.0)) or (not scipy.all(lightArray>0.0)):
            logger.warning("negative values found in atom / light array which won't work when log is taken. clipping to 1")
            atomArray = atomArray.clip(1)
            lightArray = lightArray.clip(1)
        logger.warning("Calculate OD picture..")
        # print(atomArray)
        # print(lightArray)
        # print(atomArray/lightArray)
        # print(scipy.log(atomArray/lightArray))
        return -scipy.log(atomArray/lightArray)

    def rotate(self,array, angle):
        """bilinear interpolation used and standard scipy rotation """
        return scipy.ndimage.interpolation.rotate(array, angle, order=1)

    def fastKineticsCrop(self,rawArray,n):
        """in fast kinetic picture we have one large array and then need to crop it into n equal arrays vertically.
        Uses scipy split function which returns a python list of the arrays
        returned list has the order of first picture taken --> last picture taken. i.e. [atomsImage,lightImage]"""
        try:
            return scipy.split(rawArray, n, axis=0)
        except ValueError as e:
            logger.error("fastKinetics crop couldn't equally divide the image into n=%s. This will fail. You must crop the image to a divisble size first."%n)
            raise e


    def rescale(self,initialX, initialY, width, height, array1, array2):
        """selects region defined by initialX, initialY, width and height
         and then rescales array 1 by the average(array2/array1)"""
        subArray1 = array1[initialY:initialY + height, initialX: initialX + width]
        subArray2 = array2[initialY:initialY + height, initialX: initialX + width]
        rescaleFactor = (subArray2/subArray1).mean()
        logger.info("processor: rescale factor = %s using region of shape: %s, %s" % (rescaleFactor, subArray1.shape[0],subArray1.shape[1]))
        import matplotlib.pyplot as plt
        plt.imshow( self.opticalDensity(subArray2,rescaleFactor*subArray1) )
        plt.savefig("debug")
        plt.clf()
        return rescaleFactor*array1
    
    def getBinningFactor(self):
        """ The factor by which a pixel is larger due to binning, should be implemented by subclass, if binning is available """
        return 1


    def process(self, rawImagePath):
        """ function must be implemented in all subclasses. Only argument is the path to the raw file
        must return an array for Eagle to display and use. If you set perform process in optionsDict to false,
        then this function will not be called and eagle will just show the raw image"""
        return self.read(rawImagePath)

    def editOptions(self):
        """This method is used to create a dialog to edit the processor options and once the user is finish
        update the optionsDict so that the changes are reflected"""
        updatedOptionsDict = optionsDictEditor.editOptionsDialog(self.optionsDict)
        if updatedOptionsDict is not None:
            logger.info("updating options dictionary with values %s" % updatedOptionsDict)
            self.optionsDict = updatedOptionsDict
            # for standardAndor1 and 0
            if hasattr(self,"framePlot"):
                self.drawRescaleRegion(self.framePlot)

if __name__=="__main__":
    p = Processor()