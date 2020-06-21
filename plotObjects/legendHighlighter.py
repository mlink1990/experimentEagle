# -*- coding: utf-8 -*-
"""
Created on Mon Jan 18 18:13:09 2016

@author: User
"""

#general traits,traitsui and chaco
import traits.api as traits

import chaco.api as chaco
import chaco.tools.api as tools

import operator
import logging
logger=logging.getLogger("ExperimentEagle.plotObjects.LegendHighlighter")

class LegendHighlighter(tools.LegendTool):
    """ A tool for legends that allows clicking on the legend to show
    or hide certain plots.
    """

    #: Which mousebutton to use to move the legend
    drag_button = "left"

    #: What to divide the alpha value by when plot is not selected
    dim_factor = traits.Float(2.0)

    #: How much to scale the line when it is selected or deselected
    line_scale = traits.Float(2.0)
    
    hoverPlot = None # the plot currently being hovered over
    hoverPlotWasVisibleBool = False
    hover_scale = traits.Float(5.0)

    doubleClickToggle = False
    # The currently selected renderers
    _selected_renderers = traits.List()


    humanNamesOverride = {} # probably not needed?

    def get_hit_plots(self, event):
        legend = self.component
        if legend is None or not legend.is_in(event.x, event.y):
            return []
    
        try:
            # FIXME: The size of the legend is not being computed correctly, so
            # always look at the front of the label where we know we'll get a hit.
            label = legend.get_label_at(legend.x + 20, event.y)
#            print type(label)
#            print label
        except:
            raise
            label = None
    
        if label is None:
            return []
        try:
            ndx = legend._cached_labels.index(label)
            label_name = legend._cached_label_names[ndx]
            renderers = legend.plots[label_name]
            return renderers
        except (ValueError, KeyError):
            return []
    
        
    def normal_left_dclick(self,event):
        logger.critical("Double click detected")
        if not self.component.is_in(event.x, event.y):
            return
        logger.critical("INSIDE LEGEND Double click detected")
        plots = self.get_hit_plots(event)
        logger.critical("plots clicked on  %s ", plots)
        if plots == []:
            logger.error("User did not click on a plot on the legend. ending event")
        if not self.doubleClickToggle:
            self._selected_renderers = [plots]
            logger.critical("left click on legend item detected, will change plot. Renderer = %s", self._selected_renderers)
            if self._selected_renderers:
                self._set_states(self.component.plots)
            else:
                self._reset_selects(self.component.plots)
            self.doubleClickToggle = True                
        else:
            logger.critical("double click toggle true so trying to set all plots to visible")
            self._selected_renderers=self.__selected_renderers_default()
            self._set_states(self.component.plots)
            self.doubleClickToggle = False 
        logger.critical("plots =%s ",self.component.plots.values())
        for plot in self.component.plots.values():
            logger.critical("plot =%s ",plot)
            plot.request_redraw()
        event.handled = True
    
    def normal_left_down(self, event):
        if not self.component.is_in(event.x, event.y):
            return
        
        logger.critical("left click on legend detected. Selected renderers %s ",  self._selected_renderers)
        plots = self.get_hit_plots(event)
        if plots == []:
            logger.error("User did not click on a plot on the legend. ending event")
        logger.critical("plots clicked on  %s ", plots)
        plot = plots#in CSV master plots is a list and plots[0] is used
        if plot in self._selected_renderers:
            self._selected_renderers.remove(plot)
        else:
            self._selected_renderers.append(plot)
        logger.critical("left click on legend item detected, will change plot. Renderer = %s", self._selected_renderers)
        if self._selected_renderers:
            self._set_states(self.component.plots)
        else:
            self._reset_selects(self.component.plots)
        plot.request_redraw()
        
        event.handled = True
 
#Almost working but issues when you hover and then click       
#    def normal_mouse_move(self,event):
#        #logger.debug("Mouse movement detected Event %s, event.x %s, event.y %s", event, event.x,event.y)
#        if not self.component.is_in(event.x, event.y):#outside of legend
#            if self.hoverPlot is None:
#                return
#            #outside of legend but something still hoverPlot so remove 
#            self.hoverPlot.line_width = self.hoverPlot._orig_line_width
#            self.hoverPlot.visible = self.hoverPlotWasVisibleBool
#            return    
#        #logger.debug("Mouse movement detected inside legend: Event %s, event.x %s, event.y %s.", event, event.x,event.y)
#        plots = self.get_hit_plots(event)
#        if len(plots)>0:#hovered over a line in legend
#            if not self.hoverPlot!=plots[0]:#if something else already hovered over
#                self.hoverPlot.line_width = self.hoverPlot._orig_line_width
#                self.hoverPlot.visible=self.hoverPlotWasVisibleBool
#            self.hoverPlot = plots[0]
#            if not hasattr(self.hoverPlot, '_orig_line_width'):
#                self.hoverPlot._orig_line_width = self.hoverPlot.line_width
#                self.hoverPlotWasVisibleBool = self.hoverPlot.visible                
#            self.hoverPlot.line_width = self.hoverPlot._orig_line_width*self.hover_scale
#            self.hoverPlot.visible = True
#        else:
#            if self.hoverPlot!=None:
#                self.hoverPlot.line_width = self.hoverPlot._orig_line_width
#                self.hoverPlot.visible=self.hoverPlotWasVisibleBool
#                self.hoverPlot = None
#        

    def _reset_selects(self, plots):
        """ Set all renderers to their default values. """
        for plot in plots.values():
            if not hasattr(plot, '_orig_alpha'):
                plot._orig_alpha = plot.alpha
                plot._orig_line_width = plot.line_width
                plot.visible = True
            plot.alpha = plot._orig_alpha
            plot.line_width = plot._orig_line_width
        return

    def _set_states(self, plots):
        """ Decorates a plot to indicate it is selected """
        for plot in  plots.values():
            if not hasattr(plot, '_orig_alpha'):
                # FIXME: These attributes should be put into the class def.
                plot._orig_alpha = plot.alpha
                plot._orig_line_width = plot.line_width
            if plot in self._selected_renderers:
                plot.line_width = plot._orig_line_width
                plot.alpha = plot._orig_alpha
                plot.visible=True
            else:
                plot.alpha = plot._orig_alpha / self.dim_factor
                plot.line_width = plot._orig_line_width / self.line_scale
                plot.visible=False
        # Move the selected renderers to the front
        if len(self._selected_renderers) > 0:
            container = self._selected_renderers[0].container
            components = container.components[:]
            for renderer in self._selected_renderers:
                components.remove(renderer)
            components += self._selected_renderers
            container._components = components 
    
    def __selected_renderers_default(self):
        """start with all plots selected as default... """
        logger.debug("setting default selected renderers")
        return self.component.plots.values()
