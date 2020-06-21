from __future__ import with_statement

import numpy
import logging
import traits.api as traits
import chaco.api as chaco
import chaco.tools.api as ctools

from chaco.abstract_overlay import AbstractOverlay
from enable.api import ColorTrait, KeySpec
from traits.api import Bool, Enum, Trait, Int, Float, Tuple, Instance, Property, Str, Event
from traits.util.deprecated import deprecated

logger=logging.getLogger("ExperimentEagle.boxSelection2D")

class BoxSelection2D(ctools.BetterSelectingZoom):
    """ Zooming tool which allows the user to draw a box which defines the
        desired region to zoom in to
    """
    # The selection mode:
    #
    # range:
    #   Select a range across a single index or value axis.
    # box:
    #   Perform a "box" selection on two axes.
    selection_complete = Event    
    
    tool_mode = Enum("box")
    metadata_name = Str("selections")
    
    # The key press to enter zoom mode, if **always_on** is False.  Has no effect
    # if **always_on** is True.
    enter_zoom_key = Instance(KeySpec, args=("r",))

    # The key press to leave zoom mode, if **always_on** is False.  Has no effect
    # if **always_on** is True.
    exit_zoom_key = Instance(KeySpec, args=("r",))


    #-------------------------------------------------------------------------
    # Appearance properties (for Box mode)
    #-------------------------------------------------------------------------

    # The pointer to use when drawing a zoom box.
    pointer = "magnifier"

    # The color of the selection box.
    color = ColorTrait("lightskyblue")

    # The alpha value to apply to **color** when filling in the selection
    # region.  Because it is almost certainly useless to have an opaque zoom
    # rectangle, but it's also extremely useful to be able to use the normal
    # named colors from Enable, this attribute allows the specification of a
    # separate alpha value that replaces the alpha value of **color** at draw
    # time.
    alpha = Trait(0.4, None, Float)

    # The color of the outside selection rectangle.
    border_color = ColorTrait("dodgerblue")

    # The thickness of selection rectangle border.
    border_size = Int(1)

    # The (x,y) screen point where the mouse went down.
    _screen_start = Trait(None, None, Tuple)

    # The (x,,y) screen point of the last seen mouse move event.
    _screen_end = Trait(None, None, Tuple)

    # If **always_on** is False, this attribute indicates whether the tool
    # is currently enabled.
    _enabled = Bool(False)

    #-------------------------------------------------------------------------
    # Private traits
    #-------------------------------------------------------------------------

    # the original numerical screen ranges
    _orig_low_setting = Tuple
    _orig_high_setting = Tuple

    #--------------------------------------------------------------------------
    #  BetterZoom interface
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    #  AbstractOverlay interface
    #--------------------------------------------------------------------------

    def overlay(self, component, gc, view_bounds=None, mode="normal"):
        """ Draws this component overlaid on another component.

        Overrides AbstractOverlay.
        """
        if self.event_state == "selecting":
            if self.tool_mode == "range":
                self._overlay_range(component, gc)
            else:
                self._overlay_box(component, gc)
        return


    def _end_select(self, event):
        """ Ends selection of the zoom region, adds the new zoom range to
        the zoom stack, and does the zoom.
        """
        self._screen_end = (event.x, event.y)

        start = numpy.array(self._screen_start)
        end = numpy.array(self._screen_end)
        #logger.debug( "COORDINATES (%s to %s)" % (start, end))
        #logger.debug(print "data space coordinates (%s to %s) " % self._map_coordinate_box(start, end))
        self._end_selecting(event)
        event.handled = True
        self.selection_complete=True
        return
        
    def _end_selecting(self, event=None):
        """ Ends selection of zoom region, without zooming.
        """
        #self.reset()#removed and exchanged for resetting to normal so that it remembers last selection
        self.event_state="normal"
        self._enabled = False
        if self.component.active_tool == self:
            self.component.active_tool = None
        if event and event.window:
            event.window.set_pointer("arrow")

        self.component.request_redraw()
        if event and event.window.mouse_owner == self:
            event.window.set_mouse_owner(None)
        return

    def _overlay_box(self, component, gc):
        """ Draws the overlay as a box.
        """
        if self._screen_start and self._screen_end:
            with gc:
                gc.set_antialias(0)
                gc.set_line_width(self.border_size)
                gc.set_stroke_color(self.border_color_)
                gc.clip_to_rect(component.x, component.y, component.width, component.height)
                x, y = self._screen_start
                x2, y2 = self._screen_end
                rect = (x, y, x2-x+1, y2-y+1)
                if self.color != "transparent":
                    if self.alpha:
                        color = list(self.color_)
                        if len(color) == 4:
                            color[3] = self.alpha
                        else:
                            color += [self.alpha]
                    else:
                        color = self.color_
                    gc.set_fill_color(color)
                    gc.draw_rect(rect)
                else:
                    gc.rect(*rect)
                    gc.stroke_path()
        return

    def _map_coordinate_box(self, start, end):
        """ Given start and end points in screen space, returns corresponding
        low and high points in data space.
        """
        low = [0,0]
        high = [0,0]
        for axis_index, mapper in [(0, self.component.x_mapper), \
                                   (1, self.component.y_mapper)]:
            # Ignore missing axis mappers (ColorBar instances only have one).
            if not mapper:
                continue
            low_val = mapper.map_data(start[axis_index])
            high_val = mapper.map_data(end[axis_index])

            if low_val > high_val:
                low_val, high_val = high_val, low_val
            low[axis_index] = low_val
            high[axis_index] = high_val
        return low, high

    def _get_coordinate_box(self):
        """returns last selected box """
        start = numpy.array(self._screen_start)
        end = numpy.array(self._screen_end)
        ([startX,startY],[endX,endY])=self._map_coordinate_box(start,end)
        return [startX,startY,endX,endY]
