# -*- coding: utf-8 -*-
"""
Created on Mon Apr 06 19:05:03 2015

@author: tharrison

simple script for using a fit without a gui. 

can easily wrap to do bulk processing
"""

import experimentEagle
import lmfits
import os
import physicsProperties
import scipy
import scipy.misc

cameraImage = experimentEagle.CameraImage()

imageFile = os.path.join("testData", "clipped.png")

#or...

physics = physicsProperties.PhysicsProperties()
cameraImage.getImageData(imageFile)
fit = lmfits.RotatedGaussianFit(physics = physics)

#[self.A,self.x0,self.sigmax,self.y0,self.sigmay,self.B ]#
#A,x0,sigmax,y0,sigmay,B,clipValue
fit._setInitialValues([6,500,22.0,202,27.1,-0.05])
fit.xs = cameraImage.xs
fit.ys = cameraImage.ys
fit.zs = cameraImage.zs
print fit._perform_fit()
params, cov = fit._perform_fit()
print params
fit._setCalculatedValues(params)
print fit._deriveCalculatedParameters()