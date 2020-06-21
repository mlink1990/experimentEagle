import logging
logger=logging.getLogger("ExperimentEagle.Processor")
import numpy
import os
import glob
import time
import scipy
from scipy.misc import imread, imsave
import matplotlib.pyplot as plt

import numpy as np

import traits.api as traits
import traitsui.api as traitsui

eagleLogsFolder = os.path.join("N:",os.sep,"Data","eagleLogs")
if not os.path.exists( eagleLogsFolder ):
    eagleLogsFolder = ""

defaultDarkPictureFilename = os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry","Experiment Control And Software","experimentEagle","calibration","darkPictures")

def readImage(fn):
    if fn.endswith("_X2.tif"): # Andor Solis series saved as single pictures
        im2 = imread(fn).astype(scipy.float_)
        im1 = imread(fn.replace("_X2.tif","_X1.tif")).astype(scipy.float_)
        return np.vstack( (im1,im2) )
    else:
        return imread(fn).astype(scipy.float_)

class newDarkPictureDialogHandler(traitsui.Handler):
    def _ok(self, info):
        """calculate new dark picture"""
        logger.info("Calculate new dark picture..")
        filenames = glob.glob( os.path.join(info.object.pathSourceImages, "*.png") ) + glob.glob( os.path.join(info.object.pathSourceImages, "*_X2.tif") )
        if len(filenames) == 0:
            logger.error("New dark picture: No pictures found!")
            return
        darkPicture = readImage(filenames[0])

        for fn in filenames[1:]:
            logger.debug(fn)
            currentPicture = readImage(fn)
            darkPicture += currentPicture
        darkPicture /= len(filenames)
        # scipy.savetxt( str(info.object.pathNewDarkPicture), darkPicture)
        numpy.save(str(info.object.pathNewDarkPicture), darkPicture)
        plt.imshow(darkPicture)
        plt.colorbar()
        plotFilename, _ = os.path.splitext(info.object.pathNewDarkPicture)
        plt.savefig(plotFilename)
        plt.clf()
        info.ui.dispose()
    def _cancel(self, info):
        info.ui.dispose()

class newDarkPictureDialog(traits.HasTraits):
    # pathSourceImages = traits.Directory( os.path.join("\\\\192.168.16.71","Humphry","Data","eagleLogs") )
    pathSourceImages = traits.Directory( eagleLogsFolder )
    pathNewDarkPicture = traits.File( defaultDarkPictureFilename, editor = traitsui.FileEditor(dialog_style='save') )
    cancelButton = traitsui.Action(name = 'Cancel', action = '_cancel')
    okButton = traitsui.Action(name = 'Calculate dark picture', action = '_ok')

    date = traits.String( time.strftime('%Y %m %d'), desc='Date' )
    camera = traits.String( "Andor1" )
    interval = traits.Float(0.003)
    filterCountLi = traits.Int(1)
    temperature = traits.Float(-40.0)
    autoFilename = traits.Button('Auto Filename')

    traits_view = traitsui.View(
        traitsui.Group(
            traitsui.Item('pathSourceImages'),
            traitsui.Group(
                traitsui.Item('date'),
                traitsui.Item('camera'),
                traitsui.Item('interval'),
                traitsui.Item('temperature'),
                traitsui.Item('autoFilename'),
                label='Auto Filename', show_border=True
            ),
            traitsui.Item('pathNewDarkPicture')
        ),
        buttons = [cancelButton, okButton],
        handler = newDarkPictureDialogHandler()
    )

    def _autoFilename_fired(self):
        filename = self.date + ' - dark ' + self.camera + ' - '
        filename += 'interval {} '.format(self.interval)
        filename += 'temperature {} '.format(self.temperature)
        filename = filename.replace('.','_')
        # filename += '.gz'
        filename += '.npy'
        path = os.path.join( defaultDarkPictureFilename, self.camera)
        if not os.path.exists( path ):
            os.mkdir( path )
        self.pathNewDarkPicture = os.path.join( path, filename )

        

if __name__ == '__main__':
    logging.basicConfig()
    logger=logging.getLogger("ExperimentEagle.Processor")
    logger.setLevel(logging.DEBUG)
    newDarkPictureDialog().configure_traits()
    