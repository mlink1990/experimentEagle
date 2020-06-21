"""
Renders a colormapped image of a scalar value field, and a cross section
chosen by a line interactor.
"""
import chaco.api as chaco
import traits.api as traits
import traitsui.api as traitsui
import traitsui.menu as traitsmenu
import chaco.tools.api as tools
import chaco.default_colormaps as colormaps

import scipy
import scipy.misc
import pyface
import logging

from enable.component_editor import ComponentEditor

import boxSelection2D
import clickableLineInspector

logger=logging.getLogger("ImagePlotInspector")
logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] [%(threadName)s] [%(name)s] [func=%(funcName)s:line=%(lineno)d] %(message)s")
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)
logger.debug("TEST")
logger.setLevel(logging.DEBUG)
consoleHandler.flush()                            

class ImagePlotInspectorHandler(traitsui.Handler):

    #---------------------------------------------------------------------------
    # State traits
    #---------------------------------------------------------------------------
    object = traits.Any
    #---------------------------------------------------------------------------
    # Handler interface
    #---------------------------------------------------------------------------
    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        super(ImagePlotInspectorHandler, self).close()
        
    def init(self, info):
        self.object = info.object
        self.on_trait_change(self._model_changed, "model_changed")
        self.object.boxSelection2D.on_trait_change(self._box_selection_complete, "selection_complete")
        self.object.lineInspectorX.on_trait_change(self._setCentreGuess, "mouseClickEvent")
        #self.start_timer()
    def _model_changed(self):
        self.object.update()
            
    def _box_selection_complete(self):
        logger.critical("Box selection complete")
        logger.debug("selection range: %s"  % list(map(int,self.object.boxSelection2D._get_coordinate_box())))

    def _setCentreGuess(self):
        x_ndx, y_ndx = self.object._image_index.metadata["selections"]
        logger.debug("click at x=%s, y=%s" % (self.object.xs[x_ndx],self.object.ys[y_ndx]))

class ImagePlotInspector(traits.HasTraits):
    
    pixelsX = traits.CInt(768)
    pixelsY = traits.CInt(512)
    
    xs = traits.Array
    ys = traits.Array
    zs = traits.Array    
    minZ = traits.Float
    maxZ = traits.Float
    drawContourBool = traits.Bool(False)
    test = traits.Button("test")
    contourXS = None
    contourYS = None
    contourZS = None     
    model_changed = traits.Event
    
    def _xs_default(self):
        return scipy.linspace(0.0, self.pixelsX-1, self.pixelsX)
        
    def _ys_default(self):
        return scipy.linspace(0.0, self.pixelsY-1, self.pixelsY)
        
    def _zs_default(self):
        return scipy.zeros((self.pixelsY, self.pixelsX))

    def _minZ_default(self):
        return 0.0
    
    def _maxZ_default(self):
        return 1.0
        
    def setData(self, zs):
        self.zs = zs
        self.minZ = zs.min()
        self.maxZ = zs.max()
        self.update()
 
    settingsGroup = traitsui.VGroup(
                            traitsui.VGroup(
                            traitsui.HGroup(traitsui.Item('pixelsX', label="Pixels X"),
                                            traitsui.Item('pixelsY', label="Pixels Y")),
                            traitsui.HGroup( traitsui.Item('contourLevels', label = "Contour Levels"),
                                            traitsui.Item('colormap', label="Colour Map"),"test"),
                            traitsui.HGroup( traitsui.Item('fixAspectRatioBool', label = "Fix Plot Aspect Ratio?")),
                            label="settings", show_border=True),
                            traitsui.VGroup(
                            traitsui.HGroup('autoRangeColor','colorMapRangeLow','colorMapRangeHigh'),
                            traitsui.HGroup('horizontalAutoRange','horizontalLowerLimit','horizontalUpperLimit'),
                            traitsui.HGroup('verticalAutoRange','verticalLowerLimit','verticalUpperLimit'),
                            label="axis limits", show_border=True))
                            
    plotGroup = traitsui.Group(traitsui.Item('container',editor=ComponentEditor(size=(800,600)),show_label=False))
    
    traits_view = traitsui.View(settingsGroup,plotGroup,buttons=traitsmenu.NoButtons,
                               handler = ImagePlotInspectorHandler,
                               title = "ImagePlotInspectorHandler",
                       resizable=True)

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
        self.create_plot()
        self.update()
        logger.info("initialisation of Image inspector plot")

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
         
    def initialiseContourPlot(self):
        """called if this is the first Fit Plot to be drawn """
        xstep = 0.5
        ystep = 0.5
        self.contourXS = scipy.linspace(xstep/2, self.pixelsX-xstep/2, self.pixelsX-1)
        self.contourYS = scipy.linspace(ystep/2, self.pixelsY-ystep/2, self.pixelsY-1)
        self.countourZS = chaco.ImageData(data=scipy.array([]), value_depth=1)

        self.lineplot = chaco.ContourLinePlot(index=self._image_index, 
                                        value=self.countourZS, 
                                        index_mapper=chaco.GridMapper(range=
                                            self.polyplot.index_mapper.range),
                                        levels=self.contourLevels)
        self.centralContainer.add(self.lineplot)
        self.plotData.set_data("fitLine_indexHorizontal", self.xs)
        self.plotData.set_data("fitLine_indexVertical", self.ys)
        self.crossPlotVertical.plot(("fitLine_indexVertical", "fitLine_valueVertical"), type="line", name="fitVertical")
        self.crossPlotHorizontal.plot(("fitLine_indexHorizontal", "fitLine_valueHorizontal"), type="line", name="fitHorizontal")
        logger.debug("initialise fit plot %s " % self.crossPlotVertical.plots)

    def addContourPlot(self, contourZS):
        """add a contour plot on top using fitted data and add additional plots to sidebars (TODO) """
        logger.debug("adding fit plot with fit")
        if not self.drawContourBool:
            logger.info("first fit plot so initialising contour plot")
            self.initialiseFitPlot()
        logger.info("attempting to set fit data")
        self.countourZS.data = contourZS
        self.container.invalidate_draw()
        self.container.request_redraw()
        self.drawContourBool = True
 
    def update(self):
        logger.info("updating plot")
        logger.info("zs = %s", self.zs)
        if self.autoRangeColor:
            self.colorbar.index_mapper.range.low = self.minZ
            self.colorbar.index_mapper.range.high = self.maxZ
        self._image_index.set_data(self.xs, self.ys)
        self._image_value.data = self.zs
        self.plotData.set_data("line_indexHorizontal", self.xs)
        self.plotData.set_data("line_indexVertical", self.ys)
        if self.drawContourBool and self.contourZS is not None:
            self.plotData.set_data("fitLine_indexHorizontal", self.contourXS)
            self.plotData.set_data("fitLine_indexVertical", self.contourYS)
        self.updatePlotLimits()
        #self._image_index.metadata_changed=True
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
            self.crossPlotHorizontal.value_range.low = self.minZ 
            self.crossPlotHorizontal.value_range.high = self.maxZ
        if self.verticalAutoRange:
            self.crossPlotVertical.value_range.low = self.minZ
            self.crossPlotVertical.value_range.high = self.maxZ
        if self._image_index.metadata.has_key("selections"):
            x_ndx, y_ndx = self._image_index.metadata["selections"]
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
                if self.drawContourBool:
                    self.plotData.set_data("fitLine_valueHorizontal", self.countourZS.data[y_ndx,:]) 
                    self.plotData.set_data("fitLine_valueVertical", self.countourZS.data[:,x_ndx]) 
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
        return self.minZ
        
    def _colorMapRangeHigh_default(self):
        return self.maxZ
        
    def _horizontalLowerLimit_default(self):
        return self.minZ
        
    def _horizontalUpperLimit_default(self):
        return self.maxZ
    
    def _verticalLowerLimit_default(self):
        return self.minZ
        
    def _verticalUpperLimit_default(self):
        return self.maxZ

    def _selectedFit_changed(self, selected):
        logger.debug("selected fit was changed")
        
    def _fixAspectRatioBool_changed(self):
        if self.fixAspectRatioBool:
            self.centralContainer.aspect_ratio = float(self.pixelsX)/float(self.pixelsY)
        else:
            self.centralContainer.aspect_ratio = None
        self.container.request_redraw()
        self.centralContainer.request_redraw()
        
    def updatePlotLimits(self):
        """just updates the values in the GUI  """
        if self.autoRangeColor:
            self.colorMapRangeLow = self.minZ
            self.colorMapRangeHigh = self.maxZ
        if self.horizontalAutoRange:
            self.horizontalLowerLimit = self.minZ
            self.horizontalUpperLimit = self.maxZ
        if self.verticalAutoRange:
            self.verticalLowerLimit = self.minZ
            self.verticalUpperLimit = self.maxZ
        
    def _zs_changed(self):
        logger.debug("zs changed")
        self.update()
        
    def _random_zs(self, low=0.0, high=1.0):
        """generates random zs. Useful for testing """
        self.setData(scipy.random.uniform(low,high, (self.pixelsY,self.pixelsX)))
        
    def _test_fired(self):
        self._random_zs()


if __name__ == "__main__":
    img = ImagePlotInspector()
    img.configure_traits()
    img._random_zs()
