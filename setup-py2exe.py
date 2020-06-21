# -*- coding: utf-8 -*-
"""
Created on Sat Oct 29 20:01:30 2016

@author: tharrison
"""

from distutils.core import setup
import py2exe
import os
import sys
sys.setrecursionlimit(5000)

includes = []
includes.append('numpy')
includes.append('numpy.core')
includes.append('configobj')
#includes.append('reportlab')
#includes.append('reportlab.pdfbase')
#includes.append('reportlab.pdfbase.*')
includes.append('scipy')
includes.append('xml')
includes.append('xml.etree')
includes.append('xml.etree.*')

#includes.append('wx')
#includes.append('wx.*')

includes.append('traits')
includes.append('traitsui')
includes.append('traitsui.editors')
includes.append('traitsui.editors.*')
includes.append('traitsui.extras')
includes.append('traitsui.extras.*')
includes.append('traitsui.image')
includes.append('traitsui.image.*')
includes.append('traitsui.ui_traits')

includes.append('traits.api')
includes.append('traits.*')

includes.append('traitsui.qt4')
includes.append('traitsui.qt4.*')
includes.append('traitsui.editors')
includes.append('chaco.*')

includes.append('kiva')

includes.append('pyface')
includes.append('pyface.*')
includes.append('pyface.qt')
includes.append('pyface.toolkit')
includes.append('pyface.image_resource')
includes.append('pyface.image_resource.*')
includes.append('sip')

#

#includes.append('pyface.ui.wx')
#includes.append('pyface.ui.wx.init')
#includes.append('pyface.ui.wx.*')
#includes.append('pyface.ui.wx.grid.*')
#includes.append('pyface.ui.wx.action.*')
#includes.append('pyface.ui.wx.timer.*')
#includes.append('pyface.ui.wx.wizard.*')
#includes.append('pyface.ui.wx.workbench.*')
#
#includes.append('enable')
#includes.append('enable.drawing')
#includes.append('enable.tools')
#includes.append('enable.wx')
#includes.append('enable.wx.*')
#
#includes.append('enable.savage')
#includes.append('enable.savage.*')
#includes.append('enable.savage.svg')
#includes.append('enable.savage.svg.*')
#includes.append('enable.savage.svg.backends')
#includes.append('enable.savage.svg.backends.wx')
#includes.append('enable.savage.svg.backends.wx.*')
#includes.append('enable.savage.svg.css')
#includes.append('enable.savage.compliance')
#includes.append('enable.savage.trait_defs')
#includes.append('enable.savage.trait_defs.*')
#includes.append('enable.savage.trait_defs.ui')
#includes.append('enable.savage.trait_defs.ui.*')
#includes.append('enable.savage.trait_defs.ui.wx')
#includes.append('enable.savage.trait_defs.ui.wx.*')

packages = []

data_folders = []
data_files = []
# Traited apps:
ETS_folder = r'C:\Python27\Lib\site-packages'

#data_folders.append((os.path.join(ETS_folder, r'enable\images'), r'enable/images'))
#data_folders.append((os.path.join(ETS_folder, r'pyface\images'), r'pyface\images'))
#data_folders.append((os.path.join(ETS_folder, r'pyface\ui\wx\images'), r'pyface\ui\wx\images'))
#data_folders.append((os.path.join(ETS_folder, r'pyface\ui\wx\grid\images'), r'pyface\ui\wx\grid\images'))
#
#data_folders.append((os.path.join(ETS_folder, r'traitsui\wx\images'), r'traitsui\wx\images'))
#
#data_folders.append((os.path.join(ETS_folder, r'traitsui\image\library'), r'traitsui\image\library'))
#
#data_folders.append((os.path.join(ETS_folder, r'enable\savage\trait_defs\ui\wx\data'), r'enable\savage\trait_defs\ui\wx\data'))
#

# Matplotlib
#import matplotlib as mpl
#data_files = mpl.get_py2exe_datafiles()

#Parsing folders and building the data_files table
for folder, relative_path in data_folders:
    for file in os.listdir(folder):
        f1 = os.path.join(folder, file)
        if os.path.isfile(f1):  # skip directories
            f2 = relative_path, [f1]
            data_files.append(f2)

#data_files.append((r'enable', [os.path.join(ETS_folder, r'enable\images.zip')]))

setup(windows=['__init__.py'],
    author="TH",
    version="0.1",
    description="Experiment Eagle",
    name="Experiment Eagle",
    options={"py2exe": {"optimize": 0,
                        "packages": packages,
                        "includes": includes,
                        "dist_dir": 'dist',
                        "bundle_files": 2,
                        "xref": False,
                        "skip_archive": True,
                        "ascii": False,
                        "custom_boot_script": '',
                        "compressed": False,
                        "dll_excludes": []
                       }, },
    data_files=data_files)