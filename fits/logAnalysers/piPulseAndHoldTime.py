# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 12:48:16 2016

@author: User
"""

def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    """a simple default that showshow things could be done """
    piPulseDurationTime = float(xmlVariablesDict["PiPulseDurationTime"])
    dipoleTrapHoldTime = float(xmlVariablesDict["DipoleTrapHoldTime"])
    return ["PiPulseDurationTime+DipoleTrapHoldTime"], [piPulseDurationTime+dipoleTrapHoldTime]