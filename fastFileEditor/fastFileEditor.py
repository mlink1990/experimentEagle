# -*- coding: utf-8 -*-
"""
Created on Sat Jun 04 17:49:27 2016

@author: tharrison

If this file is imported it will overwrite the traitsui Qt simple editor
to use native dialogs even on windows.

"""

from traitsui.qt4.file_editor import SimpleEditor as SimpleEditorFile
from traitsui.qt4.directory_editor import SimpleEditor as SimpleEditorDirectory
from os.path import splitext, isfile, exists, split
from pyface.qt import QtCore, QtGui

from pyface.api import FileDialog
import pyface.constant

#use this function to override traitsui.qt4.file_editor.SimpleEditor.show_file_dialog
def show_file_dialog_File(self):
    """ Displays the pop-up file dialog.
    """
    if len(self.factory.filter) > 0:
        #Qt filter example format : "Images (*.png *.xpm *.jpg);;Text files (*.txt);;XML files (*.xml)"
        filters = ";;".join(self.factory.filter)#from File filter list of trait to Qt QFileDialog filter syntax. 
    else:
        filters = ""
    #FIXME! at the moment i don't know how to access the exists attribute of the File trait from within the editor
    #until then I use the getSaveFileName static function as it allows you to name files that don't exist. TextEditor box will still turn red if a bad file
    #is chosen when exists is True
    if self.factory.dialog_style == 'open':
            file_name = QtGui.QFileDialog.getOpenFileName(self.control, 'Select file', 
            self._file_name.text(),filters, options = QtGui.QFileDialog.DontConfirmOverwrite)
    elif self.factory.dialog_style == 'save':
        file_name = QtGui.QFileDialog.getSaveFileName(self.control, 'Select file', 
            self._file_name.text(),filters, options = QtGui.QFileDialog.DontConfirmOverwrite)

    if file_name !="":#only true if user selected a file and didn't click close or cancel
        if self.factory.truncate_ext:
            file_name = splitext(file_name)[0]

        self.value = file_name
        self.update_editor()
        
#use this function to override traitsui.qt4.directory_editor.SimpleEditor.show_file_dialog      
def show_file_dialog_Directory(self):
    """ Displays the pop-up file dialog.
    """
    #here we use the static getExistingDirectoryDialog
    file_name = QtGui.QFileDialog.getExistingDirectory(self.control, 'Select file', 
            self._file_name.text())
    if file_name !="":#only true if user selected a file and didn't click close or cancel
        if self.factory.truncate_ext:
            file_name = splitext(file_name)[0]
        self.value = file_name
        self.update_editor()




def _open_pyfaceFileDialog(self):
    """open the dialog using static QFileDialog functions
    This will invoke the Windows native dialogs that are much faster
    when there are many files/directories"""
    if len(self.default_path) != 0 and len(self.default_directory) == 0 \
        and len(self.default_filename) == 0:
        default_directory, default_filename = split(self.default_path)
    else:
        default_directory = self.default_directory
        default_filename = self.default_filename
    
    
    # Convert the filter.
    filters = []
    for filter_list in self.wildcard.split('|')[::2]:
        # Qt uses spaces instead of semicolons for extension separators
        #filter_list = filter_list.replace(';', ' ')
        filters.append(filter_list)
        
    filters = ";;".join(filters)
    
    #open dialogs with static QFileDialog functions and update Dialog attributes
    #as per normal pyface fileDialog. This must set the attributes directory, filename and path
    if self.action == 'open':
        file_name = QtGui.QFileDialog.getOpenFileName(self.control, 'Open File', 
            default_directory,filters)
    elif self.action == 'open files':
        file_name = QtGui.QFileDialog.getOpenFileNames(self.control, 'Open Files', 
            default_directory,filters)
    else:#self.action == 'save as'
        file_name = QtGui.QFileDialog.getSaveFileName(self.control, 'Save As', 
            default_directory,filters)
    
    if file_name != "" and file_name != [] :
        self.return_code = pyface.constant.OK
        if self.action == 'open files':
            self.paths = file_name
        else:
            self.directory, self.filename = split(file_name)
            self.path = file_name
    else:
        self.return_code = pyface.constant.CANCEL
        
    return self.return_code





def overideDefinitions():
    """calling this funciton overrides the definitions and uses native dialogs """
    SimpleEditorFile.show_file_dialog = show_file_dialog_File
    SimpleEditorDirectory.show_file_dialog = show_file_dialog_Directory
    FileDialog.open = _open_pyfaceFileDialog

