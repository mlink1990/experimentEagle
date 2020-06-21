# -*- coding: utf-8 -*-
"""
Created on Wed Jul 20 09:00:22 2016

@author: User
"""

import logAnalyserExperimentInterlockTemperatures
import logAnalyserExperimentMonitor

def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    """a simple default that showshow things could be done """
    names1,values1 = logAnalyserExperimentMonitor.run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues)
    names2,values2 = logAnalyserExperimentInterlockTemperatures.run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues)
    return names1+names2,values1+values2
    

if __name__=="__main__":
    print run(None,None, None,None)
    