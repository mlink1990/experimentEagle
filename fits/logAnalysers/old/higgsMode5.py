# -*- coding: utf-8 -*-
"""
Created on Wed Jul 20 09:00:22 2016

@author: User
"""

import higgsMode20dB
import baslerCamNaMOTFluorescence3

def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    names1,values1 = higgsMode20dB.run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues)
    names2,values2 = baslerCamNaMOTFluorescence3.run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues)
    return names1+names2,values1+values2
    

if __name__=="__main__":
    print run(None,None, None,None)
    