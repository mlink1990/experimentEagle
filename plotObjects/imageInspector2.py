"""
Renders a colormapped image of a scalar value field, and a cross section
chosen by a line interactor.
"""
# Standard library imports
import sys
import shutil
#import analyser
from pyface.timer.api import Timer
from pyface.api import FileDialog, OK

import chaco.api as chaco
import traits.api as traits
import traitsui.api as traitsui
import traitsui.menu as traitsmenu
import chaco.tools.api as tools
import chaco.default_colormaps as colormaps

import scipy
import scipy.misc
import os
import pyface
import logging
import physicsProperties.physicsProperties

from enable.component_editor import ComponentEditor
from enable.api import Window

#import fits
import lmfitFits as fits
import boxSelection2D
import clickableLineInspector

#logFilePlot
import logFilePlot

logger=logging.getLogger("ExperimentEagle.experimentEagle")


class CameraImage(traits.HasTraits):

    #Traits view definitions:
    traits_view = traitsui.View(
        traitsui.Group(
              traitsui.HGroup(traitsui.Item('pixelsX', label="Pixels X"),
                     traitsui.Item('pixelsY', label="Pixels Y"))),
                     buttons=["OK", "Cancel"])

    pixelsX = traits.CInt(768)
    pixelsY = traits.CInt(512)

    xs = traits.Array
    ys = traits.Array
    zs = traits.Array

    minZ = traits.Float
    maxZ = traits.Float

    scale = traits.Float(10089.33)
    offset = traits.Float(5000.)

    ODCorrectionBool = traits.Bool(False, desc = "if true will correct the image to account for the maximum OD parameter")
    ODSaturationValue = traits.Float(3.0, desc = "the value of the saturated optical density")


    model_changed = traits.Event

    fitList = traits.List(fits.Fit)#list of possible fits

    def __init__(self, *args, **kwargs):
        super(CameraImage, self).__init__(*args, **kwargs)
        self.fitList = [fits.GaussianFit(endX=self.pixelsX, endY=self.pixelsY),
                        fits.RotatedGaussianFit(endX=self.pixelsX, endY=self.pixelsY),
                        fits.ParabolaFit(endX=self.pixelsX, endY=self.pixelsY),
                        fits.GaussianAndParabolaFit(endX=self.pixelsX, endY=self.pixelsY),
                        fits.FermiGasFit(endX=self.pixelsX, endY=self.pixelsY),
                        fits.ClippedExponentialIntegral(endX=self.pixelsX, endY=self.pixelsY)]

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
        self.xs = scipy.linspace(0.0, self.pixelsX-1, self.pixelsX)
        self.ys = scipy.linspace(0.0, self.pixelsY-1, self.pixelsY)
        if not os.path.exists(imageFile):
            #if no file is define the image is flat 0s of camera size
            logger.error("image file not found. filling with zeros")
            self.zs = scipy.zeros((self.pixelsX, self.pixelsY))
            print self.zs
            self.minZ = 0.0
            self.maxZ = 1.0
            self.model_changed = True
        else:
            try:
                self.rawImage = scipy.misc.imread(imageFile)
                self.zs = (self.rawImage-self.offset)/self.scale
                if self.ODCorrectionBool:
                    logger.info("Correcting for OD saturation")
                    self.zs = scipy.log( (1.0 - scipy.exp(-self.ODSaturationValue)) / (scipy.exp(-self.zs)-scipy.exp(-self.ODSaturationValue)) )
                    #we should account for the fact if ODSaturation value is wrong or there is noise we can get complex numbers!
                    self.zs[scipy.imag(self.zs)>0]=scipy.nan
                    self.zs=self.zs.astype(float)
                self.minZ = scipy.nanmin(self.zs)
                self.maxZ = scipy.nanmax(self.zs)
                self.model_changed = True
                for fit in self.fitList:
                    fit.xs = self.xs
                    fit.ys = self.ys
                    fit.zs = self.zs

            except Exception as e:
                logger.error( "error in setting data %s" % e.message)
                logger.debug("Sometimes we get an error  unsupported operand type(s) for -: 'instance' and 'float'. ")
                logger.debug("checking for what could cause this . Tell Tim if you see this error message!!!!")
                logger.debug("type(self.rawImage) ->  %s" % type(self.rawImage))
                logger.debug("type(self.offset) ->  %s" % type(self.offset))


    def _scale_changed(self):
        """update zs data when scale or offset changed """
        logger.info( "model scale changed")
        self.getImageData(self.imageFile)

    def _offset_changed(self):
        """update zs data when scale or offset changed """
        self.getImageData(self.imageFile)

class EagleHandler(traitsui.Handler):

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
            logger.info("closing image plot inspector")
        except Exception as e:
            logger.error("couldn't close: error: %s " % e.message)
        return

    def init(self, info):
        self.view = info.object
        self.model = info.object.model
        self.model.on_trait_change(self._model_changed, "model_changed")
        self.view.boxSelection2D.on_trait_change(self._box_selection_complete, "selection_complete")
        self.view.lineInspectorX.on_trait_change(self._setCentreGuess, "mouseClickEvent")
        self.view.on_trait_change(self._watchFolderModeChanged, "watchFolderBool")

        #self.start_timer()

    def _model_changed(self):
        if self.view is not None:
            self.view.update(self.model)

    def _box_selection_complete(self):
        logger.critical("Box selection complete")
        [self.view.selectedFit.startX,self.view.selectedFit.startY,self.view.selectedFit.endX,self.view.selectedFit.endY] = map(int,self.view.boxSelection2D._get_coordinate_box())
        logger.debug("box selection results %s " % [self.view.selectedFit.startX,self.view.selectedFit.startY,self.view.selectedFit.endX,self.view.selectedFit.endY])

    def _setCentreGuess(self):
        x_ndx, y_ndx = self.view._image_index.metadata["selections"]
        logger.debug("selected fit %s " % self.view.selectedFit)
        #x0=self.model.xs[x_ndx]
        #y0=self.model.ys[y_ndx]
        #print x0,y0
        #for variable in self.view.selectedFit
        self.view.selectedFit.x0.initialValue = self.model.xs[x_ndx]
        self.view.selectedFit.y0.initialValue = self.model.ys[y_ndx]

    def _watchFolderModeChanged(self):
        eagle = self.view
        eagle.oldFiles = []
        if eagle.watchFolderBool:
            if eagle.watchFolder=='' and os.path.isfile(eagle.selectedFile):
                eagle.watchFolder=os.path.dirname(eagle.selectedFile)
            eagle.oldFiles = self.getPNGFiles()
            self.watchFolderTimer=Timer(2000., self.checkForNewFiles)
        else:
            if self.watchFolderTimer is not None:
                self.watchFolderTimer.stop()
                self.watchFolderTimer = None

    def getPNGFiles(self):
        """return set of all pngs in watched folder """
        eagle = self.view
        return set([f for f in os.listdir(eagle.watchFolder)  if os.path.splitext(f)[1] == ".png"])

    def parseFiles(self, filesSet):
        """given a set of files, this file will check how many match the search string
        and return the LIST of all those that do"""
        searchString = self.view.searchString
        return [fileName for fileName in filesSet if searchString in fileName ]

    def checkForNewFiles(self):
        """function called by timer thread. Checks directory for new files
        and then checks if they match searchString (calls parseFiles)"""
        eagle = self.view
        if not os.path.isdir(eagle.watchFolder):
            logger.warning("watchFolder is not a valid directory. Will not check for new files")
            return
        currentFiles = self.getPNGFiles()
        newFiles = currentFiles - eagle.oldFiles
        if len(newFiles)==0:
            #logger.debug("No new files detected in watch Directory")
            return
        else:
            logger.debug("new files = %s" % list(newFiles))
            newFiles = self.parseFiles(newFiles)
            logger.debug("new files after checking for sub-string = %s" % list(newFiles))
            if len(newFiles)==0:
                logger.info("new files were found but none matched search string %s" % eagle.searchString)
                return
            if len(newFiles)>1:
                logger.warning("more than one new file found %s only analysing first one" % newFiles)
            newFile = newFiles[0]
            logger.debug("new file is %s" % newFile)
            logger.debug("new full path file is %s" % os.path.join(eagle.watchFolder,newFile))
            eagle.selectedFile = os.path.join(eagle.watchFolder,newFile)
            eagle.oldFiles = currentFiles

class ImagePlotInspector(traits.HasTraits):
    #Traits view definitions:

    settingsGroup = traitsui.VGroup(
                        traitsui.VGroup( traitsui.Item("watchFolderBool", label="Watch Folder?"),
                            traitsui.HGroup(traitsui.Item("selectedFile", label="Select a File"), visible_when="not watchFolderBool"),
                            traitsui.HGroup(traitsui.Item("watchFolder", label="Select a Directory"), visible_when="watchFolderBool"),
                            traitsui.HGroup(traitsui.Item("searchString", label="Filename sub-string"), visible_when="watchFolderBool"), label="File Settings", show_border=True
                            ),
                        traitsui.VGroup(
                            traitsui.HGroup('autoRangeColor','colorMapRangeLow','colorMapRangeHigh'),
                            traitsui.HGroup('horizontalAutoRange','horizontalLowerLimit','horizontalUpperLimit'),
                            traitsui.HGroup('verticalAutoRange','verticalLowerLimit','verticalUpperLimit'),
                            label="axis limits", show_border=True),
                        traitsui.VGroup(
                            traitsui.HGroup('object.model.scale','object.model.offset'),
                            traitsui.HGroup(traitsui.Item('object.model.pixelsX', label="Pixels X"),
                                            traitsui.Item('object.model.pixelsY', label="Pixels Y")),
                            traitsui.HGroup(traitsui.Item('object.model.ODCorrectionBool', label="Correct OD?"),
                                            traitsui.Item('object.model.ODSaturationValue', label="OD saturation value")),
                            traitsui.HGroup( traitsui.Item('contourLevels', label = "Contour Levels"),
                                            traitsui.Item('colormap', label="Colour Map")),
                            traitsui.HGroup( traitsui.Item('fixAspectRatioBool', label = "Fix Plot Aspect Ratio?")),
                            traitsui.HGroup( traitsui.Item('updatePhysicsBool', label = "Update Physics with XML?")),
                            traitsui.HGroup( traitsui.Item("cameraModel", label= "Update Camera Settings to:")),
                            label="advanced", show_border=True),
                        label="settings"
                        )


    plotGroup = traitsui.Group(traitsui.Item('container',editor=ComponentEditor(size=(800,600)),show_label=False))
    fitsGroup = traitsui.Group(traitsui.Item('fitList',style="custom",editor=traitsui.ListEditor(use_notebook=True,selected="selectedFit", deletable=False,export = 'DockWindowShell', page_name=".name"),label="Fits", show_label=False), springy=True)

    mainPlotGroup = traitsui.HSplit(plotGroup, fitsGroup, label = "Image")

    fftGroup = traitsui.Group(label="Fourier Transform")

    physicsGroup = traitsui.Group(traitsui.Item("physics", editor = traitsui.InstanceEditor(), style="custom", show_label=False), label="Physics")

    logFilePlotGroup = traitsui.Group(traitsui.Item("logFilePlotObject", editor = traitsui.InstanceEditor(), style="custom", show_label=False),label="Log File Plotter")

    eagleMenubar = traitsmenu.MenuBar(
                        traitsmenu.Menu(
                                        traitsui.Action(name='Save Image Copy As...', action='_save_image_as'),
                                        traitsui.Action(name='Save Image Copy', action='_save_image_default'),
                                        name="File",
                                        )
                                    )

    traits_view = traitsui.View(settingsGroup, mainPlotGroup,physicsGroup,logFilePlotGroup,buttons=traitsmenu.NoButtons,
                                menubar=eagleMenubar,
                               handler = EagleHandler,
                               title = "Experiment Eagle",
                               statusbar = "selectedFile",
                               icon=pyface.image_resource.ImageResource( os.path.join( 'icons', 'eagles.ico' )),
                       resizable=True)

    model = CameraImage()
    physics = physicsProperties.physicsProperties.PhysicsProperties()#create a physics properties object
    logFilePlotObject = logFilePlot.LogFilePlot()
    fitList = model.fitList
    selectedFit = traits.Instance(fits.Fit)
    drawFitRequest = traits.Event
    drawFitBool = traits.Bool(False)# true when drawing a fit as well
    selectedFile = traits.File()
    watchFolderBool = traits.Bool(False)
    watchFolder = traits.Directory()
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

    fixAspectRatioBool = traits.Bool(False)
    updatePhysicsBool = traits.Bool(True)


    cameraModel = traits.Enum("Custom", "ALTA0", "ANDOR0", "ALTA1","ANDOR1")

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
        #self.update(self.model)
        self.create_plot()
        for fit in self.fitList:
            fit.imageInspectorReference=self
            fit.physics = self.physics
        self.selectedFit = self.fitList[0]
        self.logFilePlotObject.physicsReference = self.physics
        #self._selectedFile_changed()
        logger.info("initialisation of experiment Eagle complete")

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

        self.polyplot.overlays.append(tools.ZoomTool(component=self.polyplot,
                                            tool_mode="box", always_on=False))


        self.lineInspectorX = clickableLineInspector.ClickableLineInspector(component=self.polyplot,
                                               axis='index_x',
                                               inspect_mode="indexed",
                                               write_metadata=True,
                                               is_listener=False,
                                               color="white")

        self.lineInspectorY = clickableLineInspector.ClickableLineInspector(component=self.polyplot,
                                               axis='index_y',
                                               inspect_mode="indexed",
                                               write_metadata=True,
                                               color="white",
                                               is_listener=False)

        self.polyplot.overlays.append(self.lineInspectorX)
        self.polyplot.overlays.append(self.lineInspectorY)

        self.boxSelection2D = boxSelection2D.BoxSelection2D(component=self.polyplot)
        self.polyplot.overlays.append(self.boxSelection2D)

        # Add these two plots to one container
        self.centralContainer = chaco.OverlayPlotContainer(padding=0,
                                                 use_backbuffer=True,
                                                 unified_draw=True)
        self.centralContainer.add(self.polyplot)



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



    def initialiseFitPlot(self):
        """called if this is the first Fit Plot to be drawn """
        xstep = 1.0
        ystep = 1.0
        self.contourXS = scipy.linspace(xstep/2., self.model.pixelsX-xstep/2., self.model.pixelsX-1)
        self.contourYS = scipy.linspace(ystep/2., self.model.pixelsY-ystep/2., self.model.pixelsY-1)
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
        self.model.getImageData(self.selectedFile)
        if self.updatePhysicsBool:
            self.physics.updatePhysics()
        for fit in self.fitList:
            fit.fitted=False
            fit.fittingStatus = fit.notFittedForCurrentStatus
            if fit.autoFitBool:#we should automatically start fitting for this Fit
                fit._fit_routine()#starts a thread to perform the fit. auto guess and auto draw will be handled automatically
        self.update_view()
        #update log file plot if autorefresh is selected
        if self.logFilePlotObject.autoRefresh:
            try:
                self.logFilePlotObject.refreshPlot()
            except Exception as e:
                logger.error( "failed to update log plot -  %s...." % e.message)

    def _cameraModel_changed(self):
        """camera model enum can be used as a helper. It just sets all the relevant
        editable parameters to the correct values. e.g. pixels size, etc.

        cameras:  "Andor Ixon 3838", "Apogee ALTA"
        """
        logger.info("camera model changed")
        if self.cameraModel == "ANDOR0":
            self.model.pixelsX = 512
            self.model.pixelsY = 512
            self.physics.pixelSize = 16.0
            self.physics.magnification = 2.0
            self.searchString = "ANDOR0"
        elif self.cameraModel == "ALTA0":
            self.model.pixelsX = 768
            self.model.pixelsY = 512
            self.physics.pixelSize = 9.0
            self.physics.magnification = 0.5
            self.searchString = "ALTA0"
        elif self.cameraModel == "ALTA1":
            self.model.pixelsX = 768
            self.model.pixelsY = 512
            self.physics.pixelSize = 9.0
            self.physics.magnification = 4.25
            self.searchString = "ALTA1"
        elif self.cameraModel == "ANDOR1":
            self.model.pixelsX = 512
            self.model.pixelsY = 512
            self.physics.pixelSize = 16.0
            self.physics.magnification = 2.0
            self.searchString = "ANDOR1"
        else:
            logger.error("unrecognised camera model")
        self.refreshFitReferences()
        self.model.getImageData(self.selectedFile)



    def refreshFitReferences(self):
        """When aspects of the image change so that the fits need to have
        properties updated, it should be done by this function"""
        for fit in self.fitList:
            fit.endX = self.model.pixelsX
            fit.endY = self.model.pixelsY

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




