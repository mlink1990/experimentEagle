# -*- coding: utf-8 -*-
"""
Created on 20/10/2016 9:15 AM
Part of: experimentEagle
Filename: processors.py
@author: tharrison


"""

import traits.api as traits
import traitsui.api as traitsui
import scipy
import scipy.misc
import logging
import scipy.ndimage
import collections
import optionsDictEditor
import os
import numpy as np

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

defaultDarkImagePath = os.path.join("\\\\ursa", "AQOGroupFolder", "Experiment Humphry", "Experiment Control and Software", "darkImages", "darkAverageData", "2016-10-20","2016-10-20-darkAverage.gz" )

class rawImageBinning(traits.HasTraits):
    """parent class for image processing. Raw image is received and then the process
     function returns the image experiment eagle should be given / display
     many helper functions such as average, subtract rotate are implemented in the
     process parent class. Children just need to implement their own specific version
     of process and can add their own helper functions as required.

     the options dictionary defines options that can be changed but should all have
     a default value. The options dictionary can be edited from the main GUI
     """

    optionsDict = collections.OrderedDict((("Binning?",True),
                                          ("process?",True),
                                          ("rotationAngle",-47.8),
                                          ("Bin size",2),
                                          ("Dark picture",defaultDarkImagePath),
                                          ("rotate?", True),
                                          ("cut light picture?", True)))
                                          
                                          
    traits_view = traitsui.View(traitsui.Item("optionsDict", style="custom"))

    def read(self, rawImagePath):
        """ returns array from image file"""
        logger.info("processor reading file!")
        return scipy.misc.imread(rawImagePath).astype(scipy.float_)

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
        subArray1 = array1[initialY:initialY + width, initialX: initialX + width]
        subArray2 = array2[initialY:initialY + width, initialX: initialX + width]
        rescaleFactor = (subArray2/subArray1).mean()
        logger.info("processor: rescale factor = %s using region of shape: %s, %s" % (rescaleFactor, subArray1.shape[0],subArray1.shape[1]))
        return rescaleFactor*array1


    def process(self, rawImagePath):
        """ function must be implemented in all subclasses. Only argument is the path to the raw file
        must return an array for Eagle to display and use. If you set perform process in optionsDict to false,
        then this function will not be called and eagle will just show the raw image"""
        
        rawArray = self.read(rawImagePath)
        if self.optionsDict["process?"] is True:
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
        if self.optionsDict["cut light picture?"] is True:
            [atomsArray, lightArray] = self.fastKineticsCrop(rawArray, 2)
            rawArray = atomsArray
        if self.optionsDict["Binning?"] is True:
            rawArray = self.binning(rawArray,self.optionsDict["Bin size"])
        if self.optionsDict["rotate?"] is True:
            rawArray = self.rotate(rawArray, self.optionsDict["rotationAngle"])
        
        return np.array(rawArray)
        
    @staticmethod
    def binning(array, binsize=2):
        data_binned = binArray(array, 0, binsize, binsize, np.mean)
        data_binned = binArray(data_binned, 1, binsize, binsize, np.mean)
        return data_binned

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