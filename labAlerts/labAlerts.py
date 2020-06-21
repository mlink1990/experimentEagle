# -*- coding: utf-8 -*-
"""
Created on Wed May 21 22:03:05 2014

@author: tharrison

LogAlert.py

This file contains the function that logs an alert from any piece of equipment
to the alert file. This file is monitored by the email Daemon which sends a 
formatted response from projecthumphry@gmail.com to a list of alertees. It then
copies the log to a separate historic log file.

"""

import csv
import datetime
import os

#different ways to group folder... 
alertLogFileName = r'//ursa/AQOGroupFolder/Experiment Humphry/Lab Monitoring/EmailDaemon/alertLog.txt'
historicLogFileName = r'//ursa/AQOGroupFolder/Experiment Humphry/Lab Monitoring/EmailDaemon/alertLogHistoric.txt'
if not os.path.exists(alertLogFileName):
    alertLogFileName = r'/media/ursa/AQOGroupFolder/Experiment Humphry/Lab Monitoring/EmailDaemon/alertLog.txt'
    historicLogFileName = r'/media/ursa/AQOGroupFolder/Experiment Humphry/Lab Monitoring/EmailDaemon/alertLogHistoric.txt'
    if not os.path.exists(alertLogFileName):
        alertLogFileName = r'./EmailDaemon/alertLog.txt'
        historicLogFileName =  r'./EmailDaemon/alertLogHistoric.txt'
#print "DEBUG alertLogFileName ", alertLogFileName
minutes = 60.0
hours = minutes*60.0
days =24*hours



def writeAlert(Priority, Device, Type, Message, Attachment=None, sendPhoto=False,waitTime=0.0):
    """This will write to the Alert Log file given the 4 necessary parameters.
    Priority should be Low Medium or High.
    Device should be the name of the device that detected the issue.
    Type is the type of alert e.g. temperature, power failure etc.
    Message is text body that will be included in email. (avoid commas!)
    Attachment will be attached to the email
    if sendPhoto True, email will send a picture of the lab as well
    wait time defines how long it will wait before sending an alert of the same priority, device and type in seconds
    
    Columns in alert Log.
    datetime, priority, device, type, message, Attachment, sendPhoto
    """
    
    with open(alertLogFileName, 'a+') as logFile:
        logWriter = csv.writer(logFile)
        logWriter.writerow([datetime.datetime.now(), Priority, Device,os.getenv('COMPUTERNAME'), Type, Message, str(Attachment), sendPhoto,waitTime])
            
def writeNewAlertFile(alertLogFileName = alertLogFileName):
    """After Email Daemon reads all alerts, it moves them to the historic log and then clears the old log file """
    with open(alertLogFileName, 'w') as logFile:
        logWriter = csv.writer(logFile)
        logWriter.writerow(['datetime', 'priority','device', 'computername','type', 'message', 'Attachment', 'sendPhoto', 'waitTime'])
        
def clearAlertLog(expectedLines,alertLogFileName = alertLogFileName):
    """Clears alert Log. If expected number of alerts is smaller than actual number, it writes a new alert afterwards. """
    actualLines = sum(1 for line in open(alertLogFileName))#counts number of lines in file #DOES NOT WORK!!!!
    writeNewAlertFile(alertLogFileName)
    print "debug, actualLines = ", actualLines
    if actualLines-1 != expectedLines:
        message = "I have found more alerts in the file than I expected. But, I have been instructed to remove alerts file. This can happen if lots of alerts arrive simultaneously..."
        print "TODO NEED TO CORRECT THIS SOMETHING DOESN@T WORK WITH THIS CHECK..."
        #writeAlert("HIGH", "ALERTSYSTEM", "LOST ALERTS",message)
        
def writeHistoricAlert(alertLine):
    """This will write to the Alert Log Historic file given the 4 necessary parameters.
    Priority should be Low Medium or High.
    Device should be the name of the device that detected the issue.
    Type is the type of alert e.g. temperature, power failure etc.
    Message is text body that will be included in email. (avoid commas!)
    Attachment will be attached to the email
    if sendPhoto True, email will send a picture of the lab as well
    
    Columns in alert Log.
    datetime, priority, device, type, message, Attachment, sendPhoto
    IDENTICAL TO writeAlert() except with different file name
    """

    with open(historicLogFileName, 'a+') as logFile:
        logWriter = csv.writer(logFile)
        logWriter.writerow(alertLine)
        
def writeTestAlert(waitTime=0.0):
    writeAlert("low", "ALERTSYSTEM", "TEST", "This is a test of the alertsystem",waitTime=waitTime)
    
    
    