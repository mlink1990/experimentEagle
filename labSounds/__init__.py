# -*- coding: utf-8 -*-
"""
Created on Sat Sep 17 10:23:37 2016

@author: tharrison

for small projects users can just use the script in lab monitoring 
for bigger projects this packaged version is identical but easier to embed
in a larger project as it is a package
"""

__version__="1.0"
__author__="Timothy Harrison"

from labSounds import *

if __name__=="__main__":
    ss = getSoundSystem()
    ss.againstMyWishes(1)

