# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 12:48:16 2016

@author: User

log Analyser experiment monitor. 

pulls the values from this cycle of experiment monitor

"""

import csv
import os

def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    """a simple default that showshow things could be done """
    NAME = "DMMField "
    latestFile = os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry", "Data", "field stability measurements","dailyLogs", "latestValues.csv")
    with open(latestFile, "rb") as csvFile:
        reader = csv.reader(csvFile)
        names = reader.next()
        names = [NAME+name for name in names]
        values = map(float,reader.next())
    return names,values
    
    
if __name__=="__main__":
    print run(None,None, None,None)
    