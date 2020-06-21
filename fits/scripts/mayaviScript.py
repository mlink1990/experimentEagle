# -*- coding: utf-8 -*-
"""
Created on Mon Apr 06 19:05:03 2015

@author: tharrison

simple script for using a fit without a gui. 

can easily wrap to do bulk processing
"""

import experimentEagle
import fits
import os
import physicsProperties.physicsProperties
from mayavi.mlab import *

cameraImage = experimentEagle.CameraImage()
imageFile = r"G:/Experiment Humphry/Data/TOF Atom Number/20150505/evaporation Optimisation 7_scaledOpticalDensity_0505 202423.png"

physics = physicsProperties.PhysicsProperties()
cameraImage.getImageData(imageFile)

cameraImage.xs
cameraImage.ys
cameraImage.zs

s = surf(cameraImage.xs,cameraImage.ys,cameraImage.zs,vmin=0.0,vmax=0.3,extent = [320,650,150,450,0,0.3],warp_scale=5.0)

