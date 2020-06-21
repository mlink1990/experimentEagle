# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 12:48:16 2016

@author: User

For this log analyser to work you need to be autofitting the basler camera Na
which will create a file called basler-lastfit.csv.

This file is then read and N extracted

"""
#
#import plugPowerMonitor
#import baslerCamLiMOTFluorescence
#import baslerCamNaMOTFluorescence
#import importlib
import imp
import os
import platform
import logging

logger=logging.getLogger("ExperimentEagle.fits.analyser")

def flatten(listOfLists):
    return [val for sublist in listOfLists for val in sublist]
    
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
    importStrings = ["plugPowerMonitor", "baslerCamLiMOTFluorescence", "baslerCamNaMOTFluorescence", "photodiodeMonitors"]

    
    #importStrings = ["plugPowerMonitor"]

#    importedLibs = [importlib.import_module(i) for i in importStrings]
    logger.info( "Load analyser.." )

    prePath = os.path.join(getGroupFolder(), "Experiment Humphry", "Experiment Control And Software", "experimentEagle", "fits", "logAnalysers")
    importedLibs = [imp.load_source(_, os.path.join(prePath,_)+".py") for _ in importStrings]
    
    collectiveReturn = []
    for i in range(len(importStrings)):
        # Note: sorry for destroying a list comprehension.. ;-P
        logger.info( "Run analyser {} ..".format(importStrings[i]) )
        output = getattr(importedLibs[i], "run")(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues)
        collectiveReturn.append(output)

    names, values = flatten([_[0] for _ in collectiveReturn]),flatten([_[1] for _ in collectiveReturn])
    
    #The return statement takes care of joining the arguments from all run-methods. this also works for different amount
    #   of returned parameters.   
    #   Note: I like list comprehensions.
    #return tuple(np.concatenate([[x[i][j] for j in range(0, len(x[i]))] for x in collectiveReturn]) for i in [0, 1])
    return (names,values)

    
if __name__=="__main__":
    print "Running.."
    print run(None, None, None, None)
    a = run(None, None, None, None)