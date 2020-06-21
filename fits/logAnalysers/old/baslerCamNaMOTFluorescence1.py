# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 12:48:16 2016

@author: User

For this log analyser to work you need to be autofitting the basler camera Na
which will create a file called basler-lastfit.csv.

This file is then read and N extracted

"""
import os.path

def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    """gets Na MOT fluorescence from fitted basler camera image"""
    latestFitFile = os.path.join("basler-latestfit.csv")
    parameterName="N"
    value = None
    with open(latestFitFile, "r") as latestFit:
            for line in latestFit.readlines():
                name,value = line.split(",")
                if name == parameterName:
                    value = float(value)
                    break
    return ["NaMOTFluorescenceBaslerCamera"], [value]