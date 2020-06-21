# -*- coding: utf-8 -*-
"""
Reads the flag from rpiADC, which contains the last plug voltage
"""
import os.path

import json

from getExperimentPaths import ursaGroupFolder, humphryNASFolder, isURSAConnected, isHumphryNASConnected

def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    """gets plug power from flag"""
    if isHumphryNASConnected():
        fn = os.path.join(humphryNASFolder, "Humphry", "Lab Monitoring", "Flags", "rpiADCOscilloscope", "statusPlug.txt")
    else:
        fn = os.path.join(ursaGroupFolder, "Experiment Humphry", "Lab Monitoring", "Flags", "rpiADCOscilloscope", "statusPlug.txt")
    try:
        with open(fn,"r") as f:
            flag = json.load(f)
        return ["plugPDVoltage"], [flag["PlugVoltage"]]
    except (ValueError, IOError):
        print "ValueError!"
        return ["plugPDVoltage"], [float("nan")]
    
if __name__=="__main__":
    print "Running.."
    print run(None, None, None, None)