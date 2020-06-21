# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 12:48:16 2016

@author: User

log Analyser experiment monitor. 

pulls the values from this cycle of experiment monitor

"""
import pyInterlock
#BOX SPECIFIC#
IP_ADDRESS = "192.168.16.12"
selectedChannels = range(0,5)
import csv
import os

def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    """a simple default that showshow things could be done """
    NAME = "experimentTemperature "
    connection =  pyInterlock.ARD_Interlock( HOST=IP_ADDRESS, PORT = 8888, DEBUG=False)
    names = [NAME+connection.GetChName(counter) for counter in selectedChannels]
    values = [connection.GetTemp(counter) for counter in selectedChannels]
    return names,values
    
    
if __name__=="__main__":
    print run(None,None, None,None)
    