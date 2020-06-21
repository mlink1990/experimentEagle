# -*- coding: utf-8 -*-
"""
Reads flag written by RPI Oscilloscope to extract Li MOT photodiode max signal
"""
import os.path

import json

from getExperimentPaths import ursaGroupFolder, humphryNASFolder, isURSAConnected, isHumphryNASConnected

flagPath = os.path.join(humphryNASFolder,"Lab Monitoring","Flags","rpiADCOscilloscope","statusMOT.txt")

def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    if isHumphryNASConnected():
        fn = os.path.join(humphryNASFolder, "Humphry", "Lab Monitoring", "Flags", "rpiADCOscilloscope", "statusMOT.txt")
    else:
        fn = os.path.join(ursaGroupFolder, "Experiment Humphry", "Lab Monitoring", "Flags", "rpiADCOscilloscope", "statusMOT.txt")
    try:
        with open(fn,"r") as f:
            flag = json.load(f)
        return ["photodiodeLiMOTVoltage","photodiodeNaMOTVoltage"], [flag["LiFluorescenceVoltage"],flag["NaFluorescenceVoltage"]]
    except (ValueError, IOError):
        return [["photodiodeLiMOTVoltage","photodiodeNaMOTVoltage"], [float("nan"),float("nan")]]
    
if __name__=="__main__":
    print "Running.."
    print run(None, None, None, None)