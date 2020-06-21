# -*- coding: utf-8 -*-
"""
Created on Mon Mar 14 16:33:27 2016

@author: user
"""


import chaco.api as chaco
import traits.api as traits
import traitsui.api as traitsui
import traitsui.menu as traitsmenu
import chaco.tools.api as tools
import chaco.default_colormaps as colormaps

from enable.component_editor import ComponentEditor
from enable.api import Window

import scipy
import clickableLineInspector


class ImagePlotInspector(traits.HasTraits):
    #Traits view definitions:
    plotGroup = traitsui.Group(traitsui.Item('container',editor=ComponentEditor(size=(800,600)),show_label=False))
    #---------------------------------------------------------------------------
    # Private Traits
    #---------------------------------------------------------------------------
    _image_index = traits.Instance(chaco.GridDataSource)
    _image_value = traits.Instance(chaco.ImageData)
    _cmap = traits.Trait(colormaps.jet, traits.Callable)
    
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

#        self.boxSelection2D = plotObjects.boxSelection2D.BoxSelection2D(component=self.polyplot)
#        self.polyplot.overlays.append(self.boxSelection2D)

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
        
    def update(self, indexData,imageData):
        logger.info("updating plot")
        if self.autoRangeColor:
            self.colorbar.index_mapper.range.low = model.minZ
            self.colorbar.index_mapper.range.high = model.maxZ
        self._image_index.set_data(model.xs, model.ys)
        self._image_value.data = model.zs
        self.plotData.set_data("line_indexHorizontal", model.xs)
        self.plotData.set_data("line_indexVertical", model.ys)
        self.updatePlotLimits()
        self._image_index.metadata_changed=True
        self.container.invalidate_draw()
        self.container.request_redraw()
        
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
