# -*- coding: utf-8 -*-
"""
Created on 18/9/2016 2:27 PM
Part of: experimentEagle
Filename: doubleStructureAnalyser
@author: tharrison

This is an example where we need the values from one log analyser for the next so
we import higgsModeMaster get the values and then use them.

When log analysers are more independent you can just select multiple log analysers


This log analyser follows the Maths in:
http://iopscience.iop.org/article/10.1209/0295-5075/85/20004/meta
Cooper pair turbulence in atomic Fermi gases
"""

import scipy
import higgsModeMaster
import scipy.constants

aBohr = 5.29176E-11
kHz = 1.0E3
MHz = 1.0E6
uK = 1.0E-6
h = scipy.constants.physical_constants["Planck constant"][0]
mass = scipy.constants.physical_constants["atomic mass constant"][0] * 6.0151214  # mass of Li 6 (kg SI)


def find(variableName, parameterList):
    """helper function for finding the value of a fitted parameter or
    derived parameter. Goes through parameter List and returns when it finds
    the correct value"""
    for variable in parameterList:
        if variable.name == variableName:
            return variable.value
    return None


def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    """called by log analyser """
    higgsModeMasterNames, higgsModeMasterValues = higgsModeMaster.run(imageDataArray, xmlVariablesDict,
                                                                      fittedParameters, derivedValues)
    higgsModeMasterDict = {name: value for (name, value) in zip(higgsModeMasterNames, higgsModeMasterValues)}

    EFermi = h * 1000.0 * higgsModeMasterDict["EFermi"]  # kHz --> J
    kFermi = higgsModeMasterDict["kFermi"]
    BCSGap = 1000.0 * higgsModeMasterDict["BCSGap_12"]  # kHz --> Hz
    vFermi = scipy.sqrt(2 * EFermi / mass)
    qValue = higgsModeMasterDict["calculatedAlpha"]

    kEpsilon = BCSGap / vFermi  # SI
    calculatedKWidth = scipy.sqrt(qValue) * kEpsilon
    measuredK = find("k", derivedValues)
    k_kF_units = measuredK / kFermi  # relative units
    k_kEpsilon_units = measuredK / kEpsilon  # relative units

    names = ["qValue", "kEpsilon", "calculatedKWidth", "k/kF", "k/kEpsilon"]
    values = [qValue, kEpsilon, calculatedKWidth, k_kF_units, k_kEpsilon_units]

    finalNames = higgsModeMasterNames + names
    finalValues = higgsModeMasterValues + values
    return finalNames, finalValues
