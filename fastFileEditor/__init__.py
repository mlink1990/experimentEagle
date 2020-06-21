# -*- coding: utf-8 -*-
"""
Created on Sat Jun 04 18:14:46 2016

@author: tharrison

This package implements fast native file/directory selection in traitsui
it does this by overriding the Qt dialog calls in the traits File/Directory
Editors.

It also overides the pyface File Dialogs so that they use native windows but otherwise
have the same behaviour

the call to override is in the __init__.py so user just needs to import the package and nothing else

"""


import fastFileEditor
__version__="2.0"
fastFileEditor.overideDefinitions()
