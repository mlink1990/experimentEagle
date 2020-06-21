# -*- coding: utf-8 -*-
"""
Created on Sun Apr 05 17:46:54 2015

@author: tharrison
"""

import chaco.tools.api as tools
import traits.api as traits


class ClickableLineInspector(tools.LineInspector):
    
    mouseClickEvent = traits.Event    
    
    def __init__(self, component=None, **traitsDict):
        super(ClickableLineInspector,self).__init__(component=component, **traitsDict)
        
    def normal_left_down(self, event):
        """ Handles the mouse clicking. This event can be picked up by the 
        view to change x0, y0 of current fit
        """
        self.mouseClickEvent=True