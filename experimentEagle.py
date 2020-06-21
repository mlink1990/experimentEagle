"""

The main chunk of the eagle class is an adaption of a chaco example that
renders a colormapped image of a scalar value field, and a cross section
chosen by a line interactor.

In addition this class ties everything else together, including fitting 
the colormapped images and drawing contours etc.

We also can plug in a range of physics parameters to allow calculations to 
be made from the fits

"""

# Standard library imports
import sys
import shutil
import time
#import analyser
from pyface.timer.api import Timer
from pyface.api import FileDialog, OK

import distutils.version
import chaco
IS_CHACO_VERSION_OLD =  ( distutils.version.StrictVersion( chaco.__version__ ) < distutils.version.StrictVersion( "4.7.2" ) )
# contourPlots changed compared to old chaco versions..
# search for "def getContourX(self):" for explanation

import chaco.api as chaco
import traits.api as traits
import traitsui.api as traitsui
import traitsui.menu as traitsmenu
import chaco.tools.api as tools
import chaco.default_colormaps as colormaps
import enable.api as enable

import scipy
import scipy.misc
import os
import glob
import json
import shutil
import datetime
import pyface
import logging
import re
import physicsProperties.physicsProperties

from enable.component_editor import ComponentEditor
from enable.api import Window

#import fits
import fits.fits
import fits.fitGaussian
import fits.fitGaussianRotated
import fits.fitParabola
import fits.fitGaussianAndParabola
import fits.fitGaussianAndParabola1D
import fits.fitFermiGas
import fits.fitClippedExponentialIntegral
import fits.fitGaussianAndDoubleParabola

import plotObjects.boxSelection2D
import plotObjects.clickableLineInspector
import plotObjects.keyBindingsTool

#logFilePlot
import plotObjects.logFilePlot
import processors
import processors.newDarkPicture

from getExperimentPaths import isHumphryNASConnected

logger=logging.getLogger("ExperimentEagle.experimentEagle")

class CameraImage(traits.HasTraits):

    #Traits view definitions:
    traits_view = traitsui.View(
        traitsui.Group(
              traitsui.HGroup(traitsui.Item('pixelsX', label="Pixels X"),
                     traitsui.Item('pixelsY', label="Pixels Y"))),
                     buttons=["OK", "Cancel"])

    pixelsX = traits.CInt(768, desc="number of pixels in the X direction of image")
    pixelsY = traits.CInt(512, desc="number of pixels in the Y direction of image")

    xs = traits.Array
    ys = traits.Array
    zs = traits.Array

    minZ = traits.Float
    maxZ = traits.Float

    scale = traits.Float(10089.33, desc="if in optical density image mode, image = scale*rawImage+offset")
    offset = traits.Float(5000., desc="if in optical density image mode, image = scale*rawImage+offset")

    ODCorrectionBool = traits.Bool(False, desc = "if true will correct the image to account for the maximum OD parameter")
    ODSaturationValue = traits.Float(3.0, desc = "the value of the saturated optical density")
    
    forceRefreshButton = traits.Button("Force Refresh", "re reads the image file and processes as required")

    imageMode = traits.Enum("optical density image", "process raw image",
                            desc="user can choose different types of images i.e. optical density or raw atoms and light. If user selects a raw image he can choose how to process the image with an eagle processor")
    chosenProcessor = traits.Enum(processors.validNames, desc="strings which are keys to the validProcessors dictionary defined in the processors package. This defines the processor the user selects for processing images")
    processor = None # will be a reference to the processor object
    editProcessorOptionsButton = traits.Button("processor options",desc="edit specific options about how the processor works")

    model_changed = traits.Event
    pixels_changed = traits.Event#pixels changed event. when new picture has different dimensions this event is called
    processor_changed = traits.Event

    fitList = traits.List(fits.fits.Fit)#list of possible fits

    
    def __init__(self, *args, **kwargs):
        super(CameraImage, self).__init__(*args, **kwargs)
        
        self.fitList = [fits.fitGaussian.GaussianFit(),
                        fits.fitGaussianRotated.RotatedGaussianFit(),
                        fits.fitParabola.ParabolaFit(),
                        fits.fitGaussianAndParabola.GaussianAndParabolaFit(),
                        fits.fitGaussianAndParabola1D.GaussianAndParabola1DFit(),
                        fits.fitFermiGas.FermiGasFit(),
                        fits.fitClippedExponentialIntegral.ClippedExponentialIntegral(),
                        fits.fitGaussianAndDoubleParabola.GaussianAndDoubleParabolaFit()]

    def _xs_default(self):
        return scipy.linspace(0.0, self.pixelsX-1, self.pixelsX)

    def _ys_default(self):
        return scipy.linspace(0.0, self.pixelsY-1, self.pixelsY)

    def _zs_default(self):
        return scipy.zeros((self.pixelsY, self.pixelsX))

    def getImageData(self, imageFile):
        logger.debug( "pulling image data")
        # The xs and ys used for the image plot range need to be the
        # edges of the cells.
        self.imageFile = imageFile
        if not os.path.exists(imageFile):
            #if no file is define the image is flat 0s of camera size
            logger.error("image file not found. filling with zeros")
            self.zs = self.rawImage = scipy.zeros((self.pixelsX, self.pixelsY))
            self.minZ = 0.0
            self.maxZ = 1.0
            self.xs = scipy.linspace(0.0, self.pixelsX-1, self.pixelsX)
            self.ys = scipy.linspace(0.0, self.pixelsY-1, self.pixelsY)
            self.model_changed = True
        else:
            if self.imageMode == "optical density image":#old standard use case image is an array of optical densities
                self.rawImage = scipy.misc.imread(imageFile).astype(scipy.float_)# still load raw image so that analyser can be passed the raw image always
                logger.debug("self.imageFile = %s" % (imageFile) )
                logger.debug("self.rawImage = %s and type = %s" % (self.rawImage,type(self.rawImage)) )
                logger.debug("scipy.misc.imread = %s" % scipy.misc.imread)
                logger.debug("offset = %s" % self.offset)
                self.zs = (self.rawImage - self.offset) / self.scale# we don't rescale images if they are processed. this should be done by the processor
                if self.ODCorrectionBool:
                    logger.info("Correcting for OD saturation")
                    self.zs = scipy.log((1.0 - scipy.exp(-1.*self.ODSaturationValue)) / (
                    scipy.exp(-self.zs) - scipy.exp(-1.*self.ODSaturationValue)))
                    # we should account for the fact if ODSaturation value is wrong or there is noise we can get complex numbers!
                    self.zs[scipy.imag(self.zs) > 0] = scipy.nan
                    self.zs = self.zs.astype(float)
            else:#USING A PROCESSOR #TODO may need to change to elif when we start having atoms and light pics                
                self.processor = processors.validProcessors[self.chosenProcessor]                 
                logger.info("processor = %s" % self.processor)
                self.zs = self.processor.process(self.imageFile)
                #self.rawImage is still the raw image
                logger.debug("processed raw image = %s" % self.zs)
            logger.info("shape of raw Image = (%s,%s)" % self.zs.shape)
            if (self.pixelsX != self.zs.shape[1] or  self.pixelsY != self.zs.shape[0]):
                #pixels have changed. Need to destroy contour plot on fit if it exists                    
                logger.warning("number of pixels in image have changed. This causes problems for contour fit plot. Will destroy contour fit plot first")
                self.pixels_changed=True
                logger.info("continuing after pixels changed = True event")
            self.pixelsX = self.zs.shape[1]# update number of pixels when we load a new picture! (user shouldn't have to define pixels manually)
            self.pixelsY = self.zs.shape[0]# update number of pixels when we load a new picture! (user shouldn't have to define pixels manually)
            self.xs = scipy.linspace(0.0, self.pixelsX-1, self.pixelsX)
            self.ys = scipy.linspace(0.0, self.pixelsY-1, self.pixelsY)
            #once we have zs we can now move the file
            self.minZ = scipy.nanmin(self.zs)
            self.maxZ = scipy.nanmax(self.zs)                
            for fit in self.fitList:
                fit.xs = self.xs
                fit.ys = self.ys
                fit.zs = self.zs

            self.model_changed = True


    def _scale_changed(self):
        """update zs data when scale or offset changed """
        logger.info( "model scale changed")
        self.getImageData(self.imageFile)

    def _offset_changed(self):
        """update zs data when scale or offset changed """
        self.getImageData(self.imageFile)

    def _forceRefreshButton_fired(self):
        """update zs data when scale or offset changed """
        logger.info( "force refresh button fired")
        self.getImageData(self.imageFile)

    def _editProcessorOptionsButton_fired(self):
        processors.validProcessors[self.chosenProcessor].editOptions()
        # self.physics.binningSize = processors.validProcessors[self.chosenProcessor].getBinningFactor()
        self.processor_changed = True
    
    def _chosenProcessor_changed(self):
        self.processor_changed = True
        # self.physics.binningSize = processors.validProcessors[self.chosenProcessor].getBinningFactor()

    


class EagleHandler(traitsui.Handler):
    """Handler for the Eagle class. The picture can be considered as the model
    this is the controller and the ImagePlotInspector class is the View + a lot of
    tieing together"""
    #---------------------------------------------------------------------------
    # State traits
    #---------------------------------------------------------------------------
    model = traits.Instance(CameraImage)
    view = traits.Any
    watchFolderTimer = traits.Instance(Timer)

    #---------------------------------------------------------------------------
    # Handler interface
    #---------------------------------------------------------------------------
    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        try:
            #stop any previous timer, should only have 1 timer at a time
            self.watchFolderTimer.stop()
            logger.info("attempting to stop timers")
        except Exception as e:
            logger.error("couldn't stop current timer %s " % e.message)
        return

    def init(self, info):
        self.view = info.object
        self.model = info.object.model
        self.model.on_trait_change(self._model_changed, "model_changed")#make sure plot is redrawn when image changes
        self.model.on_trait_change(self._pixels_changed, "pixels_changed")#make sure contours work when pixels change
        self.model.on_trait_change(self._processor_changed, "processor_changed") # update binning size
        self.view.boxSelection2D.on_trait_change(self._box_selection_complete, "selection_complete")#when user finishes dragging a box with r
        self.view.lineInspectorX.on_trait_change(self._setCentreGuess, "mouseClickEvent")#when user clicks somewhere on image
        self.view.on_trait_change(self._watchFolderModeChanged, "watchFolderBool")
        self.model.on_trait_change(self._imageMode_changed, "imageMode")
        self.model.on_trait_change(self._forceRefreshAction, "forceRefreshButton")

    def _model_changed(self):
        """redraw plots when image changes """
        if self.view is not None:
            self.view.update(self.model)
            
    def _pixels_changed(self):
        """redraw plots when image changes """
        if self.view.drawFitBool:
            logger.warning("number of pixels in image changed with a contour plot being drawn. To prevent a crash I need to remove contour plot")
            self.view.centralContainer.remove(self.view.lineplot)
            self.view.drawFitBool=False
        # force fixed aspectRatio, if requested
        # self.view._fixAspectRatioBool_changed()
        self.view.fixAspectRatioBool = not self.view.fixAspectRatioBool
        self.view.fixAspectRatioBool = not self.view.fixAspectRatioBool
        # self.view.zoomTool.reset()
        if self.model.imageMode == "process raw image":
            if hasattr(self.model.processor,'drawRescaleRegion'):
                self.model.processor.drawRescaleRegion(self.view.rescaleRegionFrame)
            else:
                self.view.rescaleRegionFrame.visible=False
        else:
            self.view.rescaleRegionFrame.visible=False
    
    def _processor_changed(self):
        """ update binning size """
        if self.view is not None:
            self.view.physics.binningSize = processors.validProcessors[self.model.chosenProcessor].getBinningFactor()

    def _box_selection_complete(self):
        """box selection allows user to select a sub region of image to fit """
        logger.critical("Box selection complete")
        [self.view.selectedFit.startX,self.view.selectedFit.startY,self.view.selectedFit.endX,self.view.selectedFit.endY] = map(int,self.view.boxSelection2D._get_coordinate_box())
        logger.debug("box selection results %s " % [self.view.selectedFit.startX,self.view.selectedFit.startY,self.view.selectedFit.endX,self.view.selectedFit.endY])

    def _setCentreGuess(self):
        x_ndx, y_ndx = self.view._image_index.metadata["selections"]
        logger.debug("selected fit %s " % self.view.selectedFit)
        self.view.selectedFit.x0.initialValue = self.model.xs[x_ndx]
        self.view.selectedFit.y0.initialValue = self.model.ys[y_ndx]

    def _watchFolderModeChanged(self):
        eagle = self.view
        eagle.oldFiles = set()
        if eagle.watchFolderBool:
            if eagle.watchFolder=='' and os.path.isfile(eagle.selectedFile):
                eagle.watchFolder=os.path.dirname(eagle.selectedFile)
            # commented this, because eagle should directly load an image, if already available
            # eagle.oldFiles = self.getImageFiles()
            self.watchFolderTimer=Timer(2000., self.checkForNewFiles)
        else:
            if self.watchFolderTimer is not None:
                self.watchFolderTimer.stop()
                self.watchFolderTimer = None

    def getImageFiles(self):
        """return set of all image files in watched folder """
        eagle = self.view
        return set([f for f in os.listdir(eagle.watchFolder)  if (os.path.splitext(f)[1] in [".png",".jpg",".pgm",".bmp",".tif"])])

    def parseFiles_old(self, filesSet):
        """given a set of files, this file will check how many match the search string
        and return the LIST of all those that do"""
        searchString = self.view.searchString
        return [fileName for fileName in filesSet if searchString in fileName ]
        
    def parseFiles(self, filesSet):
        """given a set of files, this file will check how many match the search string
        and return the LIST of all those that do
        additional functionality through regular expressions"""
        searchString = self.view.searchString
        return [fileName for fileName in filesSet if bool(re.search(searchString, fileName)) ]
        
    def organiseImageFile(self, filename):
        """once an image has been found in the watched directory, often the user
        may want this file to be organised away in folders by date. This is not how we are doing this (now):
        We delete all files, unless they are important and therefore saved within an eagleLog.
        """
        eagle = self.view
        if not eagle.watchFolderBool:
            logger.info("we do not organise a folder that isn't being watched")
            return
        try:    
            creationTime = os.path.getctime(filename)
        except WindowsError as e:
            logger.error("received a Windows Error while reading creation time of file. Will simply pass the organisation this iteration: error message: %s" % e.message)            
            return
        try:
            os.remove(filename)
            logger.info("file deleted during organisation process successfully")
        except WindowsError as e:
            logger.error("received a Windows Error while deleting file. Will simply pass the organisation this iteration: error message: %s" % e.message)
            return

    def checkForNewFiles(self):
        """function called by timer thread. Checks directory for new files
        and then checks if they match searchString (calls parseFiles)"""
        logger.debug("Check for new files")
        eagle = self.view
        if not os.path.isdir(eagle.watchFolder):
            logger.warning("watchFolder is not a valid directory. Will not check for new files")
            return
        currentFiles = self.getImageFiles()
        newFiles = currentFiles - eagle.oldFiles
        if len(newFiles)==0:
            logger.debug("No new files detected in watch Directory")
            return
        else:
            logger.debug("new files = %s" % list(newFiles))
            newFiles = self.parseFiles(newFiles)
            logger.debug("new files after checking for sub-string = %s" % list(newFiles))
            if len(newFiles)==0:
                logger.debug("new files were found but none matched search string %s" % eagle.searchString)
                return
            if len(newFiles)>1:
                logger.warning("more than one new file found %s only analysing first one" % newFiles)
            newFile = newFiles[0]
            logger.debug("new file is %s" % newFile)
            logger.debug("new full path file is %s" % os.path.join(eagle.watchFolder,newFile))
            eagle.selectedFile = os.path.join(eagle.watchFolder,newFile)
            eagle.physics.selectedFileModifiedTime = os.path.getmtime(eagle.selectedFile)
            eagle.oldFiles = currentFiles
            #only organise previous files once you have found a new one
            if eagle.organisedFolderBool:#organise matching files that aren't the current file
                if eagle.watchFolder.startswith('T:'):
                    matchingFiles = self.parseFiles(currentFiles)
                    logger.debug("attempting to organise files")
                    logger.debug("matching files = %s" % matchingFiles)
                    for matchingFile in matchingFiles:
                        if matchingFile != newFile:#don't move the file currently being analysed!
                            logger.debug("about to organise matching file: %s" % matchingFile)
                            self.organiseImageFile( os.path.join(eagle.watchFolder,matchingFile) )

                        
    def _eagleReferenceAction(self, info):
        """This action (triggered by menu) is used to save info about the current image and
        sequence to the references folder. It creates an eagleReferenceImage dialog and saves
        the current pixmap of the screen. It can also send the information to OneNote"""
        from PyQt4.QtGui import QPixmap
        from plotObjects.imageReferenceDialog import ImageReferenceDialog
        import xml.etree.ElementTree as ET
        import time
        widget = info.ui.control
        pixmap = QPixmap.grabWindow(widget.winId())
        latestSequenceFile = self.view.physics.latestSequenceFile            
        if os.path.exists(latestSequenceFile):
            sequenceXML = ET.parse(latestSequenceFile)
            modifiedTime = os.path.getmtime(latestSequenceFile)
            now = time.time()
            timeDiff = now-modifiedTime
            logger.debug("Time difference between now ('eagle loads sequence file') and modification time of sequence ('Snake saved sequence file after receiving it from runner at beginning of sequence')")
            if timeDiff>60.0: #>5min
                logger.error("Found a time difference of >1min between modification time of XML and current time.This means the sequence is not from the associated image and I will not save the XML")
                sequenceXML=None
        else:
            logger.warning("cannot find latest Sequence File")
            sequenceXML = None
        extraDetails = {"cameraModel":str(self.view.cameraModel), "TOFVariableName":str(self.view.physics.TOFVariableName),
                        "timeOfFlightTimems":str(self.view.physics.timeOfFlightTimems), "magnification":str(self.view.physics.magnification), 
                        "species":str(self.view.physics.species), "imagingDetuningLinewidths":str(self.view.physics.imagingDetuningLinewidths),
                        "fitReport":self.view.selectedFit.mostRecentModelFitReport(),"calculatedValues":self.view.selectedFit.getCalculatedParameters()}#dictionary of extra details that will be written to comments file and oneNote
        
        imageReferenceDialog = ImageReferenceDialog(self.model.zs, pixmap, sequenceXML, extraDetails=extraDetails)
        imageReferenceDialog.edit_traits()

    def _forceRefreshAction(self,info):
        """triggered by the menu. Allows the user to call the models force refresh command"""
        if self.view.watchFolderBool:
            self.checkForNewFiles()
        self.model._forceRefreshButton_fired()
        
    def _reloadProcessors(self,info):
        """reload processors so that you don't have to restart eagle when you change them """
        reload(processors)

    def _imageMode_changed(self):
        """when image mode changes we change this bool in the view so that options can be displayed or hidden.
        Can't get the visible_when to work with object.model.imageMode == 'optical density image'"""
        if self.model.imageMode == "optical density image":
            self.view.processorModeEnabled = False
        else:
            self.view.processorModeEnabled = True

class ImagePlotInspector(traits.HasTraits):
    #Traits view definitions:

    settingsGroup = traitsui.VGroup(
        traitsui.VGroup(
            traitsui.HGroup(
                traitsui.Item("cameraModel", label= "Update Camera Settings to:", editor=traitsui.EnumEditor(name='object.availableCameraModels')),
                traitsui.Item("configureWatchFolder"),
                traitsui.Item("object.model.forceRefreshButton")
            ),
            label="Quick Camera Settings", show_border=True
        ),
        traitsui.VGroup(
            traitsui.HGroup(traitsui.Item("watchFolderBool", label="Watch Folder?"),traitsui.Item("object.model.imageMode", label="image file type:"),
                            traitsui.Item("object.model.chosenProcessor", label="image processor:", visible_when='processorModeEnabled'), traitsui.Item("object.model.editProcessorOptionsButton", show_label=False,visible_when='processorModeEnabled')),
            traitsui.HGroup(traitsui.Item("selectedFile", label="Select a File"), visible_when="not watchFolderBool"),
            traitsui.HGroup(traitsui.Item("watchFolder", label="Select a Directory"), visible_when="watchFolderBool"),
            traitsui.HGroup(traitsui.Item("searchString", label="Filename sub-string"), visible_when="watchFolderBool"),
            traitsui.HGroup(
                traitsui.Item("organisedFolderBool", label="Organise Watched Folder? (must be on drive T:)", visible_when="watchFolderBool", enabled_when="watchFolder.startswith('T:')")
                ),
            label="File Settings", show_border=True
        ),
        traitsui.VGroup(
            traitsui.HGroup('autoRangeColor','colorMapRangeLow','colorMapRangeHigh'),
            traitsui.HGroup('horizontalAutoRange','horizontalLowerLimit','horizontalUpperLimit'),
            traitsui.HGroup('verticalAutoRange','verticalLowerLimit','verticalUpperLimit'),
            label="axis limits", show_border=True
        ),
        traitsui.VGroup(
            traitsui.HGroup('object.model.scale','object.model.offset'),
            traitsui.HGroup(traitsui.Item('object.model.pixelsX', label="Pixels X", style="readonly"),
                            traitsui.Item('object.model.pixelsY', label="Pixels Y", style="readonly")),
            traitsui.HGroup(traitsui.Item('object.model.ODCorrectionBool', label="Correct OD?"),
                            traitsui.Item('object.model.ODSaturationValue', label="OD saturation value")),
            traitsui.HGroup( traitsui.Item('contourLevels', label = "Contour Levels"),
                            traitsui.Item('colormap', label="Colour Map")),
            traitsui.HGroup( traitsui.Item('object.selectedFit.fitTimeLimitBool', label = "Fit Time Limit?"),
                            traitsui.Item('object.selectedFit.fitTimeLimit', label="Time limit (sec)")),
            traitsui.HGroup( traitsui.Item('fixAspectRatioBool', label = "Fix Plot Aspect Ratio?")),
            traitsui.HGroup( traitsui.Item('updatePhysicsBool', label = "Update Physics with XML?")),
            label="advanced", show_border=True
        ),
        label="Settings"
    )


    plotGroup = traitsui.Group(traitsui.Item('container',editor=ComponentEditor(size=(800,600)),show_label=False))
    fitsGroup = traitsui.Group(traitsui.Item('fitList',style="custom",editor=traitsui.ListEditor(use_notebook=True,selected="selectedFit", deletable=False,export = 'DockWindowShell', page_name=".name"),label="Fits", show_label=False), springy=True)

    mainPlotGroup = traitsui.HSplit(plotGroup, fitsGroup, label = "Image")

    fftGroup = traitsui.Group(label="Fourier Transform")#not implemented

    physicsGroup = traitsui.Group(traitsui.Item("physics", editor = traitsui.InstanceEditor(), style="custom", show_label=False), label="Physics")

    #DISABLED logFilePlot Group as this will soon be depracated. Users should plot logFiles with separate program, logfileplots
    #logFilePlotGroup = traitsui.Group(traitsui.Item("logFilePlotObject", editor = traitsui.InstanceEditor(), style="custom", show_label=False),label="Log File Plotter")#deprecated
    settingsAndPhysicsGroup = traitsui.VGroup(settingsGroup, physicsGroup, label="Settings")

    eagleMenubar = traitsmenu.MenuBar(
                        traitsmenu.Menu(
                                        traitsui.Action(name='Save Image Copy As...', action='_save_image_as'),
                                        traitsui.Action(name='Save Image Copy', action='_save_image_default'),
                                        traitsui.Action(name='Save Image as Reference', action='_eagleReferenceAction'),
                                        traitsui.Action(name='Force Resfresh (F5)', action='_forceRefreshAction'),
                                        traitsui.Action(name='Reload Processors', action='_reloadProcessors'),
                                        name="Menu",
                                        ),
                        traitsmenu.Menu(
                                        traitsui.Action(name='New dark picture', action='_new_dark_picture'),
                                        name="Calibration",
                                        )
                                    )
    #Removed logFilePlot Group as this will soon be depracated. Users should plot logFiles with separate program, logfileplots
    traits_view = traitsui.View(settingsAndPhysicsGroup, mainPlotGroup,#physicsGroup,#logFilePlotGroup,
                                buttons=traitsmenu.NoButtons,
                                menubar=eagleMenubar,
                               handler = EagleHandler,
                               title = "Experiment Eagle",
                               statusbar = "statusBarString",
                               icon=pyface.image_resource.ImageResource( os.path.join( 'icons', 'eagles.ico' )),
                       resizable=True)

    model = CameraImage()
    physics = physicsProperties.physicsProperties.PhysicsProperties()#create a physics properties object
    #logFilePlotObject = plotObjects.logFilePlot.LogFilePlot()
    fitList = model.fitList
    selectedFit = traits.Instance(fits.fits.Fit)
    drawFitRequest = traits.Event
    drawFitBool = traits.Bool(False)# true when drawing a fit as well
    selectedFile = traits.File()
    statusBarString = traits.String("no image file selected")
    watchFolderBool = traits.Bool(False)
    watchFolder = traits.Directory()
    processorModeEnabled = traits.Bool(False)

    organisedFolderBool = traits.Bool(False)
    
    searchString = traits.String(desc="sub string that must be contained in file name for it to be shown in Eagle. Can be used to allow different instances of Eagle to detect different saved images.")
    oldFiles = set()
    contourLevels = traits.Int(15)
    colormap = traits.Enum(colormaps.color_map_name_dict.keys())

    autoRangeColor = traits.Bool(True)
    colorMapRangeLow = traits.Float
    colorMapRangeHigh = traits.Float

    horizontalAutoRange = traits.Bool(True)
    horizontalLowerLimit = traits.Float
    horizontalUpperLimit = traits.Float

    verticalAutoRange = traits.Bool(True)
    verticalLowerLimit = traits.Float
    verticalUpperLimit = traits.Float

    fixAspectRatioBool = traits.Bool(True, desc="If True pixels will look like squares, otherwise they may be rectangular distoring aspect ratio")
    updatePhysicsBool = traits.Bool(True, desc="If True, eagle will read latestSequence.xml file to get parameters from sequence to calculate TOF time etc")

    keyBindingsDictionary = {} #defined in __init___


    # cameraModel = traits.Enum("Custom", "ALTA0", "ANDOR0", "ALTA1","ANDOR1","basler","point-grey")
    cameraModel = traits.String()
    availableCameraModels = traits.List([])
    configureWatchFolder = traits.Button("Configure watch folder")

    #---------------------------------------------------------------------------
    # Private Traits
    #---------------------------------------------------------------------------
    _image_index = traits.Instance(chaco.GridDataSource)
    _image_value = traits.Instance(chaco.ImageData)
    _cmap = traits.Trait(colormaps.jet, traits.Callable)

    #---------------------------------------------------------------------------
    # Public View interface
    #---------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        super(ImagePlotInspector, self).__init__(*args, **kwargs)
        self.keyBindingsDictionary={enable.KeySpec("F5"):self.model._forceRefreshButton_fired,
                                    enable.KeySpec("F11"):self._force_fix_aspect_ratio,
                                    enable.KeySpec("F12"):self._zoom_to_fit_region }
        
        self.create_plot()
        
        for fit in self.fitList:
            fit.imageInspectorReference=self
            fit.physics = self.physics
        self.selectedFit = self.fitList[0]

        try:
            self.configPath = kwargs['configPath']
        except KeyError:
            logger.critical("No config path given, can't load settings!")

        self.loadSettings()

        logger.info("initialisation of experiment Eagle complete")

    def loadSettings(self):
        logger.info("Load settings")
        
        # load camera settings
        cameras = glob.glob( os.path.join(self.configPath,'cameraSettings','*.json') )
        cameras = [ os.path.splitext( os.path.basename(c) )[0] for c in cameras ]
        self.availableCameraModels = sorted(cameras)


    def create_plot(self):

        # Create the mapper, etc
        self._image_index = chaco.GridDataSource(scipy.array([]),
                                          scipy.array([]),
                                          sort_order=("ascending","ascending"))
        image_index_range = chaco.DataRange2D(self._image_index)
        self._image_index.on_trait_change(self._metadata_changed,
                                          "metadata_changed")

        self._image_value = chaco.ImageData(data=scipy.array([]), value_depth=1)

        image_value_range = chaco.DataRange1D(self._image_value)

        # Create the contour plots
        #self.polyplot = ContourPolyPlot(index=self._image_index,
        self.polyplot = chaco.CMapImagePlot(index=self._image_index,
                                        value=self._image_value,
                                        index_mapper=chaco.GridMapper(range=
                                            image_index_range),
                                        color_mapper=self._cmap(image_value_range))


        # Add a left axis to the plot
        left = chaco.PlotAxis(orientation='left',
                        title= "y",
                        mapper=self.polyplot.index_mapper._ymapper,
                        component=self.polyplot)
        self.polyplot.overlays.append(left)

        # Add a bottom axis to the plot
        bottom = chaco.PlotAxis(orientation='bottom',
                          title= "x",
                          mapper=self.polyplot.index_mapper._xmapper,
                          component=self.polyplot)
        self.polyplot.overlays.append(bottom)


        # Add some tools to the plot
        self.polyplot.tools.append(tools.PanTool(self.polyplot,
                                           constrain_key="shift", drag_button="middle"))

        #lets you define arbitrary key bindings for function calls
        
        self.polyplot.tools.append(plotObjects.keyBindingsTool.KeyBindings(component=self.polyplot,keyBindingsDictionary=self.keyBindingsDictionary))
        
        self.zoomTool = tools.ZoomTool(component=self.polyplot,
                                            tool_mode="box", always_on=False)
        self.polyplot.overlays.append( self.zoomTool )


        self.lineInspectorX = plotObjects.clickableLineInspector.ClickableLineInspector(component=self.polyplot,
                                               axis='index_x',
                                               inspect_mode="indexed",
                                               write_metadata=True,
                                               is_listener=False,
                                               color="white")

        self.lineInspectorY = plotObjects.clickableLineInspector.ClickableLineInspector(component=self.polyplot,
                                               axis='index_y',
                                               inspect_mode="indexed",
                                               write_metadata=True,
                                               color="white",
                                               is_listener=False)
                                               
           

        self.polyplot.overlays.append(self.lineInspectorX)
        self.polyplot.overlays.append(self.lineInspectorY)

        self.boxSelection2D = plotObjects.boxSelection2D.BoxSelection2D(component=self.polyplot)
        self.polyplot.overlays.append(self.boxSelection2D)

        # Add these two plots to one container
        self.centralContainer = chaco.OverlayPlotContainer(padding=0,
                                                 use_backbuffer=True,
                                                 unified_draw=True)
        self.centralContainer.add(self.polyplot)


         # create line segment plot to display fit region
        self.ROIPolyPlotXs = chaco.ArrayDataSource([100,200,200,100])
        self.ROIPolyPlotYs = chaco.ArrayDataSource([100,100,200,200])
        self.ROIPolyPlot = chaco.PolygonPlot(index = self.ROIPolyPlotXs, value = self.ROIPolyPlotYs, edge_color=(1,0,0),
                                        index_mapper=chaco.GridMapper(range=self.polyplot.index_mapper.range)._xmapper,
                                        value_mapper=chaco.GridMapper(range=self.polyplot.index_mapper.range)._ymapper)
        # self.polyplot.overlays.append( self.ROIPolyPlot )
        self.centralContainer.add(self.ROIPolyPlot)
        self.ROIPolyPlot.visible=False

        # create line segment plot to display processor rescale region
        self.rescaleRegionFrameXs = chaco.ArrayDataSource([100,200,200,100])
        self.rescaleRegionFrameYs = chaco.ArrayDataSource([100,100,200,200])
        self.rescaleRegionFrame = chaco.PolygonPlot(index = self.rescaleRegionFrameXs, value = self.rescaleRegionFrameYs, edge_color=(1,1,1),
                                            index_mapper=chaco.GridMapper(range=self.polyplot.index_mapper.range)._xmapper,
                                            value_mapper=chaco.GridMapper(range=self.polyplot.index_mapper.range)._ymapper)
        self.centralContainer.add(self.rescaleRegionFrame)
        self.rescaleRegionFrame.visible=False



        # Create a colorbar
        cbar_index_mapper = chaco.LinearMapper(range=image_value_range)
        self.colorbar = chaco.ColorBar(index_mapper=cbar_index_mapper,
                                 plot=self.polyplot,
                                 padding_top=self.polyplot.padding_top,
                                 padding_bottom=self.polyplot.padding_bottom,
                                 padding_right=40,
                                 resizable='v',
                                 width=30)

        self.plotData = chaco.ArrayPlotData(line_indexHorizontal = scipy.array([]),
                                line_valueHorizontal = scipy.array([]),
                                scatter_indexHorizontal = scipy.array([]),
                                scatter_valueHorizontal = scipy.array([]),
                                scatter_colorHorizontal = scipy.array([]),
                                fitLine_indexHorizontal = scipy.array([]),
                                fitLine_valueHorizontal = scipy.array([]))

        self.crossPlotHorizontal = chaco.Plot(self.plotData, resizable="h")
        self.crossPlotHorizontal.height = 100
        self.crossPlotHorizontal.padding = 20
        self.crossPlotHorizontal.plot(("line_indexHorizontal", "line_valueHorizontal"),
                             line_style="dot")
        self.crossPlotHorizontal.plot(("scatter_indexHorizontal","scatter_valueHorizontal","scatter_colorHorizontal"),
                             type="cmap_scatter",
                             name="dot",
                             color_mapper=self._cmap(image_value_range),
                             marker="circle",
                             marker_size=4)

        self.crossPlotHorizontal.index_range = self.polyplot.index_range.x_range

        self.plotData.set_data("line_indexVertical", scipy.array([]))
        self.plotData.set_data("line_valueVertical", scipy.array([]))
        self.plotData.set_data("scatter_indexVertical", scipy.array([]))
        self.plotData.set_data("scatter_valueVertical", scipy.array([]))
        self.plotData.set_data("scatter_colorVertical", scipy.array([]))
        self.plotData.set_data("fitLine_indexVertical", scipy.array([]))
        self.plotData.set_data("fitLine_valueVertical", scipy.array([]))

        self.crossPlotVertical = chaco.Plot(self.plotData, width = 140, orientation="v", resizable="v", padding=20, padding_bottom=160)
        self.crossPlotVertical.plot(("line_indexVertical", "line_valueVertical"),
                             line_style="dot")

        self.crossPlotVertical.plot(("scatter_indexVertical","scatter_valueVertical","scatter_colorVertical"),
                             type="cmap_scatter",
                             name="dot",
                             color_mapper=self._cmap(image_value_range),
                             marker="circle",
                             marker_size=4)

        self.crossPlotVertical.index_range = self.polyplot.index_range.y_range

        # Create a container and add components
        self.container = chaco.HPlotContainer(padding=40, fill_padding=True,
                                        bgcolor = "white", use_backbuffer=False)

        inner_cont = chaco.VPlotContainer(padding=40, use_backbuffer=True)
        inner_cont.add(self.crossPlotHorizontal)
        inner_cont.add(self.centralContainer)
        self.container.add(self.colorbar)
        self.container.add(inner_cont)
        self.container.add(self.crossPlotVertical)

        # force default aspect ratio
        self._fixAspectRatioBool_changed()
        # self.view.fixAspectRatioBool = not self.view.fixAspectRatioBool
        # self.view.fixAspectRatioBool = not self.view.fixAspectRatioBool

    def getContourX(self):
        if IS_CHACO_VERSION_OLD:
            # for chaco 4.5.0 the number of xgrid and ygrid values must be one more:
            #   ( len(xgrid) - 1, len(ygrid) - 1 ) == zvalues.shape
            # for chaco 4.7.2 it must be the same
            #   ( len(xgrid), len(ygrid) ) == zvalues.shape
            xstep = 1.0
            return scipy.linspace(xstep/2., self.model.pixelsX-xstep/2., self.model.pixelsX-1)
        else:
            return scipy.arange(self.model.pixelsX)
    
    def getContourY(self):
        if IS_CHACO_VERSION_OLD:
            ystep = 1.0
            return scipy.linspace(ystep/2., self.model.pixelsY-ystep/2., self.model.pixelsY-1)
        else:
            return scipy.arange(self.model.pixelsY)

    def initialiseFitPlot(self):
        """called if this is the first Fit Plot to be drawn """
        self.contourXS = self.getContourX()
        self.contourYS = self.getContourY()
        logger.debug("contour initialise fit debug. xs shape %s" % self.contourXS.shape)
        logger.debug("contour initialise xs= %s" % self.contourXS)
        self._fit_value = chaco.ImageData(data=scipy.array([]), value_depth=1)

        self.lineplot = chaco.ContourLinePlot(index=self._image_index,
                                        value=self._fit_value,
                                        index_mapper=chaco.GridMapper(range=
                                            self.polyplot.index_mapper.range),
                                        levels=self.contourLevels)

        self.centralContainer.add(self.lineplot)
        self.plotData.set_data("fitLine_indexHorizontal", self.model.xs)
        self.plotData.set_data("fitLine_indexVertical", self.model.ys)
        self.crossPlotVertical.plot(("fitLine_indexVertical", "fitLine_valueVertical"), type="line", name="fitVertical")
        self.crossPlotHorizontal.plot(("fitLine_indexHorizontal", "fitLine_valueHorizontal"), type="line", name="fitHorizontal")
        logger.debug("initialise fit plot %s " % self.crossPlotVertical.plots)

       

    def addFitPlot(self, fit):
        """add a contour plot on top using fitted data and add additional plots to sidebars (TODO) """
        logger.debug("adding fit plot with fit %s " % fit)
        if not fit.fitted:
            logger.error("cannot add a fitted plot for unfitted data. Run fit first")
            return
        if not self.drawFitBool:
            logger.info("first fit plot so initialising contour plot")
            self.initialiseFitPlot()
        logger.info("attempting to set fit data")
        self.contourPositions = [scipy.tile(self.contourXS, len(self.contourYS)), scipy.repeat(self.contourYS, len(self.contourXS))]#for creating data necessary for gauss2D function
        zsravelled = fit.fitFunc(self.contourPositions, *fit._getCalculatedValues())
#        logger.debug("zs ravelled shape %s " % zsravelled.shape)
        self.contourZS = zsravelled.reshape((len(self.contourYS), len(self.contourXS)))
#        logger.debug("zs contour shape %s " % self.contourZS.shape)
#        logger.info("shape contour = %s " % self.contourZS)
        self._fit_value.data = self.contourZS
        self.container.invalidate_draw()
        self.container.request_redraw()
        self.drawFitBool = True

    def update(self, model):
        logger.info("updating plot")
#        if self.selectedFile=="":
#            logger.warning("selected file was empty. Will not attempt to update plot.")
#            return
        if self.autoRangeColor:
            self.colorbar.index_mapper.range.low = model.minZ
            self.colorbar.index_mapper.range.high = model.maxZ
        self._image_index.set_data(model.xs, model.ys)
        self._image_value.data = model.zs
        self.plotData.set_data("line_indexHorizontal", model.xs)
        self.plotData.set_data("line_indexVertical", model.ys)
        if self.drawFitBool:
            self.plotData.set_data("fitLine_indexHorizontal", self.contourXS)
            self.plotData.set_data("fitLine_indexVertical", self.contourYS)
        self.updatePlotLimits()
        self._image_index.metadata_changed=True
        self.container.invalidate_draw()
        self.container.request_redraw()

    #---------------------------------------------------------------------------
    # Event handlers
    #---------------------------------------------------------------------------

    def _metadata_changed(self, old, new):
        """ This function takes out a cross section from the image data, based
        on the line inspector selections, and updates the line and scatter
        plots."""
        if self.horizontalAutoRange:
            self.crossPlotHorizontal.value_range.low = self.model.minZ
            self.crossPlotHorizontal.value_range.high = self.model.maxZ
        if self.verticalAutoRange:
            self.crossPlotVertical.value_range.low = self.model.minZ
            self.crossPlotVertical.value_range.high = self.model.maxZ
        if self._image_index.metadata.has_key("selections"):
            selections = self._image_index.metadata["selections"]
            if not selections:#selections is empty list
                return#don't need to do update lines as no mouse over screen. This happens at beginning of script
            x_ndx, y_ndx = selections
            if y_ndx and x_ndx:
                self.plotData.set_data("line_valueHorizontal",
                                 self._image_value.data[y_ndx,:])
                self.plotData.set_data("line_valueVertical",
                                 self._image_value.data[:,x_ndx])
                xdata, ydata = self._image_index.get_data()
                xdata, ydata = xdata.get_data(), ydata.get_data()
                self.plotData.set_data("scatter_indexHorizontal", scipy.array([xdata[x_ndx]]))
                self.plotData.set_data("scatter_indexVertical", scipy.array([ydata[y_ndx]]))
                self.plotData.set_data("scatter_valueHorizontal",
                    scipy.array([self._image_value.data[y_ndx, x_ndx]]))
                self.plotData.set_data("scatter_valueVertical",
                    scipy.array([self._image_value.data[y_ndx, x_ndx]]))
                self.plotData.set_data("scatter_colorHorizontal",
                    scipy.array([self._image_value.data[y_ndx, x_ndx]]))
                self.plotData.set_data("scatter_colorVertical",
                    scipy.array([self._image_value.data[y_ndx, x_ndx]]))
                if self.drawFitBool:
                    self.plotData.set_data("fitLine_valueHorizontal", self._fit_value.data[y_ndx,:])
                    self.plotData.set_data("fitLine_valueVertical", self._fit_value.data[:,x_ndx])
        else:
            self.plotData.set_data("scatter_valueHorizontal", scipy.array([]))
            self.plotData.set_data("scatter_valueVertical", scipy.array([]))
            self.plotData.set_data("line_valueHorizontal", scipy.array([]))
            self.plotData.set_data("line_valueVertical", scipy.array([]))
            self.plotData.set_data("fitLine_valueHorizontal", scipy.array([]))
            self.plotData.set_data("fitLine_valueVertical", scipy.array([]))

    def _colormap_changed(self):
        self._cmap = colormaps.color_map_name_dict[self.colormap]
        if hasattr(self, "polyplot"):
            value_range = self.polyplot.color_mapper.range
            self.polyplot.color_mapper = self._cmap(value_range)
            value_range = self.crossPlotHorizontal.color_mapper.range
            self.crossPlotHorizontal.color_mapper = self._cmap(value_range)
            # FIXME: change when we decide how best to update plots using
            # the shared colormap in plot object
            self.crossPlotHorizontal.plots["dot"][0].color_mapper = self._cmap(value_range)
            self.crossPlotVertical.plots["dot"][0].color_mapper = self._cmap(value_range)
            self.container.request_redraw()

    def _colorMapRangeLow_changed(self):
        self.colorbar.index_mapper.range.low = self.colorMapRangeLow

    def _colorMapRangeHigh_changed(self):
        self.colorbar.index_mapper.range.high = self.colorMapRangeHigh

    def _horizontalLowerLimit_changed(self):
        self.crossPlotHorizontal.value_range.low = self.horizontalLowerLimit

    def _horizontalUpperLimit_changed(self):
        self.crossPlotHorizontal.value_range.high = self.horizontalUpperLimit

    def _verticalLowerLimit_changed(self):
        self.crossPlotVertical.value_range.low = self.verticalLowerLimit

    def _verticalUpperLimit_changed(self):
        self.crossPlotVertical.value_range.high = self.verticalUpperLimit

    def _autoRange_changed(self):
        if self.autoRange:
            self.colorbar.index_mapper.range.low = self.minz
            self.colorbar.index_mapper.range.high = self.maxz

    def _num_levels_changed(self):
        if self.num_levels > 3:
            self.polyplot.levels = self.num_levels
            self.lineplot.levels = self.num_levels

    def _colorMapRangeLow_default(self):
        logger.debug("setting color map rangle low default")
        return self.model.minZ

    def _colorMapRangeHigh_default(self):
        return self.model.maxZ

    def _horizontalLowerLimit_default(self):
        return self.model.minZ

    def _horizontalUpperLimit_default(self):
        return self.model.maxZ

    def _verticalLowerLimit_default(self):
        return self.model.minZ

    def _verticalUpperLimit_default(self):
        return self.model.maxZ

    def _selectedFit_changed(self, selected):
        logger.debug("selected fit was changed")

    def _fixAspectRatioBool_changed(self):
        logger.info("self.fixAspectRatioBool changed to "+str(self.fixAspectRatioBool))
        if self.fixAspectRatioBool:
            #using zoom range works but then when you reset zoom this function isn't called...
#            rangeObject = self.polyplot.index_mapper.range
#            xrangeValue = rangeObject.high[0]-rangeObject.low[0]
#            yrangeValue = rangeObject.high[1]-rangeObject.low[1]
#            logger.info("xrange = %s, yrange = %s " % (xrangeValue, yrangeValue))
#            aspectRatioSquare = (xrangeValue)/(yrangeValue)
#            self.polyplot.aspect_ratio=aspectRatioSquare
            self.centralContainer.aspect_ratio = float(self.model.pixelsX)/float(self.model.pixelsY)
            #self.polyplot.aspect_ratio = self.model.pixelsX/self.model.pixelsY

        else:
            self.centralContainer.aspect_ratio = None
            #self.polyplot.aspect_ratio = None
        self.container.request_redraw()
        self.centralContainer.request_redraw()


    def updatePlotLimits(self):
        """just updates the values in the GUI  """
        if self.autoRangeColor:
            self.colorMapRangeLow = self.model.minZ
            self.colorMapRangeHigh = self.model.maxZ
        if self.horizontalAutoRange:
            self.horizontalLowerLimit = self.model.minZ
            self.horizontalUpperLimit = self.model.maxZ
        if self.verticalAutoRange:
            self.verticalLowerLimit = self.model.minZ
            self.verticalUpperLimit = self.model.maxZ

    def _selectedFile_changed(self):
        logger.info("######################## Selected File changed ########################")
        if self.updatePhysicsBool:
            logger.info("Update physics")
            self.physics.updatePhysics()
        maxAttempts = 5
        # logger.warning("NON REFRESH WARNING - THIS WAS SELECTED FILE %s " % self.selectedFile)
        for i in range(0,maxAttempts):
            try:
                time.sleep(0.1)#DEBUG seeing if adding these sleeps fixes the issue of images not updating!
                self.model.getImageData(self.selectedFile)
            except AttributeError as e:
                logger.error("Error. received Attribute Error when trying to getImageData. This occurs sometimes and causes duplicate points...")
                logger.error("Error message :%s" % e.message)
                logger.error("Will sleep and then retry")
                time.sleep(0.5)
                continue
            logger.info("succesfully completed getImageData. Will now break from repetition loop")
            break
        for fit in self.fitList:
            fit.fitted=False
            fit.fittingStatus = fit.notFittedForCurrentStatus
            if fit.autoFitBool:#we should automatically start fitting for this Fit
                fit._fit_routine()#starts a thread to perform the fit. auto guess and auto draw will be handled automatically
        self.update_view()
        #redefine the statusString whenever selected file changes
        self.statusBarString = self.selectedFile+" - "+self.physics.species+" - "+self.cameraModel

    def _cameraModel_changed(self):
        """camera model enum can be used as a helper. It just sets all the relevant
        editable parameters to the correct values. e.g. pixels size, etc.

        cameras:  "Andor Ixon 3838", "Apogee ALTA"
        """
        logger.info("Camera model changed to " + self.cameraModel)
        filename = os.path.join(self.configPath,'cameraSettings',self.cameraModel+'.json')
        with open(filename, 'r') as f:
            settings = json.load( f )
            if 'pixelSize' in settings:     self.physics.pixelSize = settings['pixelSize']
            if 'magnification' in settings: self.physics.magnification = settings['magnification']
            if 'searchString' in settings:  self.searchString = settings['searchString']
            if 'colorRange' in settings:
                if 'auto' in settings['colorRange']:   self.autoRangeColor = settings['colorRange']['auto']
                if 'min' in settings['colorRange']:    self.colorMapRangeLow = settings['colorRange']['min']
                if 'max' in settings['colorRange']:    self.colorMapRangeHigh = settings['colorRange']['max']
            if 'horizontalRange' in settings:
                if 'auto' in settings['horizontalRange']:   self.horizontalAutoRange = settings['horizontalRange']['auto']
                if 'min' in settings['horizontalRange']:    self.horizontalLowerLimit = settings['horizontalRange']['min']
                if 'max' in settings['horizontalRange']:    self.horizontalUpperLimit = settings['horizontalRange']['max']
            if 'verticalRange' in settings:
                logger.info(str(settings['verticalRange']))
                if 'auto' in settings['verticalRange']:   self.verticalAutoRange = settings['verticalRange']['auto']
                if 'min' in settings['verticalRange']:    self.verticalLowerLimit = settings['verticalRange']['min']
                if 'max' in settings['verticalRange']:    self.verticalUpperLimit = settings['verticalRange']['max']
            if "scale" in settings:         self.model.scale = settings['scale']
            if "offset" in settings:        self.model.offset = settings['offset']
            if "tofVariable" in settings:   self.physics.TOFVariableName = settings['tofVariable']
            if "imageMode" in settings:     self.model.imageMode = settings["imageMode"]
            if "processor" in settings:
                if settings["processor"] in processors.validNames:     self.model.chosenProcessor = settings["processor"]
                if "processorOptions" in settings:
                    if "Binning?" in settings["processorOptions"]:    processors.validProcessors[self.model.chosenProcessor].optionsDict["Binning?"] = settings["processorOptions"]["Binning?"]
                    if "Bin size" in settings["processorOptions"]:    processors.validProcessors[self.model.chosenProcessor].optionsDict["Bin size"] = settings["processorOptions"]["Bin size"]
                    if "Dark picture" in settings["processorOptions"]:    processors.validProcessors[self.model.chosenProcessor].optionsDict["Dark picture"] = settings["processorOptions"]["Dark picture"]
                    if "rescale?" in settings["processorOptions"]:    processors.validProcessors[self.model.chosenProcessor].optionsDict["rescale?"] = settings["processorOptions"]["rescale?"]
                    if "rescaleInitialX" in settings["processorOptions"]:    processors.validProcessors[self.model.chosenProcessor].optionsDict["rescaleInitialX"] = settings["processorOptions"]["rescaleInitialX"]
                    if "rescaleInitialY" in settings["processorOptions"]:    processors.validProcessors[self.model.chosenProcessor].optionsDict["rescaleInitialY"] = settings["processorOptions"]["rescaleInitialY"]
                    if "rescaleWidth" in settings["processorOptions"]:    processors.validProcessors[self.model.chosenProcessor].optionsDict["rescaleWidth"] = settings["processorOptions"]["rescaleWidth"]
                    if "rescaleHeight" in settings["processorOptions"]:    processors.validProcessors[self.model.chosenProcessor].optionsDict["rescaleHeight"] = settings["processorOptions"]["rescaleHeight"]
                    if "rotationAngle" in settings["processorOptions"]:    processors.validProcessors[self.model.chosenProcessor].optionsDict["rotationAngle"] = settings["processorOptions"]["rotationAngle"]
                    

        self.refreshFitReferences()
        self.model.getImageData(self.selectedFile)
    
    def _configureWatchFolder_fired(self):
        """ Set usual watch folder for selected camera, according to its setting file
        """
        logger.info("Configure watch folder for " + self.cameraModel)
        filename = os.path.join(self.configPath,'cameraSettings',self.cameraModel+'.json')
        with open(filename, 'r') as f:
            settings = json.load( f )
            try:
                if isHumphryNASConnected():
                    newWatchFolder = settings['watchFolder']
                else:
                    newWatchFolder = settings.get('watchFolderURSA',"")
                if os.path.exists( newWatchFolder ):
                    self.watchFolder = newWatchFolder
                else:
                    logger.error("Invalid watchFolder: " + newWatchFolder)
                if not self.watchFolderBool:
                    # use above if statement, otherwise there might be two watchFolder timers (?)
                    self.watchFolderBool = True
            except KeyError:
                logger.error("Camera setting does not specify watch folder!")



    def refreshFitReferences(self):
        """When aspects of the image change so that the fits need to have
        properties updated, it should be done by this function"""
        # for fit in self.fitList:
        #     fit.endX = self.model.pixelsX
        #     fit.endY = self.model.pixelsY
        pass

    def _pixelsX_changed(self):
        """If pixelsX or pixelsY change, we must send the new arrays to the fit functions """
        logger.info("pixels X Change detected")
        self.refreshFitReferences()
        self.update(self.model)
        self.model.getImageData(self.selectedFile)

    def _pixelsY_changed(self):
        """If pixelsX or pixelsY change, we must send the new arrays to the fit functions """
        logger.info("pixels Y Change detected")
        self.refreshFitReferences()
        self.update(self.model)
        self.model.getImageData(self.selectedFile)

    @traits.on_trait_change('model')
    def update_view(self):
        if self.model is not None:
            self.update(self.model)

    def _save_image(self,originalFilePath, newFilePath):
        """given the original file path this saves a new copy to new File path """
        shutil.copy2(originalFilePath,newFilePath)

    def _save_image_as(self):
        """ opens a save as dialog and allows user to save a copy of current image to
        a custom location with a custom name"""
        originalFilePath = str(self.selectedFile)#so that this can't be affected by auto update after the dialog is open
        file_wildcard = str("PNG (*.png)|All files|*")
        default_directory=os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry","Data","savedEagleImages")
        dialog = FileDialog(action="save as",default_directory=default_directory, wildcard=file_wildcard)
        dialog.open()
        if dialog.return_code == OK:
            self._save_image(originalFilePath,dialog.path)
        logger.debug("custom image copy made")

    def _save_image_default(self):
        head, tail = os.path.split(self.selectedFile)
        default_file=os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry","Data","savedEagleImages",tail)
        self._save_image(self.selectedFile,default_file)
        logger.debug("default image copy made")

    
    def _force_fix_aspect_ratio(self):
        """turn aspect ratio bool true and then call changed function to force aspect ratio to be fixed
        """
        self.fixAspectRatioBool = True
        self._fixAspectRatioBool_changed()
        
    def _zoom_to_fit_region(self):
        """ zooms to region that is your fit region and then forces aspect ratio to be 1 """
        rangeObject = self.polyplot.index_mapper.range
        logger.info("type of range Object = %s" % type(rangeObject))
        rangeObject.set_bounds((self.selectedFit.startX,self.selectedFit.startY),(self.selectedFit.endX,self.selectedFit.endY))        
        self._force_fix_aspect_ratio()
    
    def _new_dark_picture(self):
        processors.newDarkPicture.newDarkPictureDialog().configure_traits()


        
        




