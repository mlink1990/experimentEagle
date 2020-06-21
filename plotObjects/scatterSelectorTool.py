# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 13:54:27 2016

@author: tharrison
"""
import chaco.tools.api as tools
import logging

logger=logging.getLogger("ExperimentEagle.scatterSelectorTool")

class ScatterSelector(tools.ScatterInspector):
    """small adaptation to the standard chaco inspector tool. Here the right mouse button activates the
    selection"""
    
    def normal_left_down(self,event):
        logger.debug("left down for Scatter selector detected")
        pass
    
    def normal_right_down(self,event):
        """calls the normal left down when right button clicked """
        super(ScatterSelector,self).normal_left_down(event)
        