# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 12:48:16 2016

@author: User

For this log analyser to work you need to be autofitting the basler camera Na
which will create a file called basler-lastfit.csv.

This file is then read and N extracted

"""
import os.path
import platform

def getGroupFolder():
        """returns the location of the group folder. supports both
         linux and windows. assumes it is mounted to /media/ursa/AQOGroupFolder
         for linux"""
        if platform.system()=="Windows":
            groupFolder = os.path.join("\\\\ursa","AQOGroupFolder")
        if platform.system()=="Linux":
            groupFolder = os.path.join("/media","ursa","AQOGroupFolder")
        return groupFolder

def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    """gets Na MOT fluorescence from fitted basler camera image"""
    latestFitFile = os.path.join(getGroupFolder(), "Experiment Humphry", "Experiment Control And Software", "experimentEagle", "baslerLi-Li6-lastFit.csv")
    parameterName="N"
    value = None
    with open(latestFitFile, "r") as latestFit:
            for line in latestFit.readlines():
                name,value = line.split(",")
                if name == parameterName:
                    value = float(value)
                    break
    return ["LiMOTFluorescenceBaslerCamera"], [value]

if __name__=="__main__":
    print "Running.."
    print run(None, None, None, None)