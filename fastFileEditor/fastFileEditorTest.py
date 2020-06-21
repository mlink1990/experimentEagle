# -*- coding: utf-8 -*-
"""
Created on Sat Jun 04 18:03:07 2016

@author: tharrison
"""
import traits.api
import traitsui.api
import fastFileEditor
import pyface.constant
from pyface.api import FileDialog


class FileExample(traits.api.HasTraits):
    defaultFile=traits.api.File(exists = True)
    filteredFile=traits.api.File(filter=["Images (*.png *.xpm *.jpg)","Text files (*.txt)","Python files (*.py)"])
    nonexistingFile=traits.api.File(exists=False)
    directory=traits.api.Directory()
    button = traits.api.Button("button")
    
    traits_view =traitsui.api.View("defaultFile","filteredFile","nonexistingFile","directory","button")
    
    def _button_fired(self):
        
        fileDialog = FileDialog(action="open") 
        fileDialog.open()
        if fileDialog.return_code == pyface.constant.OK:
            defaultFile = fileDialog.path
            
        fileDialog = FileDialog(action="save as", default_directory = r"\\ursa", wildcard ="Python files (*.py)" ) 
        fileDialog.open()
        if fileDialog.return_code == pyface.constant.OK:
            nonexistingFile = fileDialog.path
            
        fileDialog = FileDialog(action="open files") 
        fileDialog.open()
        if fileDialog.return_code == pyface.constant.OK:
            print fileDialog.paths
            print fileDialog.path
            print fileDialog.directory
            
        

if __name__=="__main__":
    fastFileEditor.overideDefinitions()
    fileExample = FileExample()
    fileExample.configure_traits()