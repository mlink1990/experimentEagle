# -*- coding: utf-8 -*-
"""
Created on Mon Feb 16 15:26:52 2015

@author: tharrison
"""
import threading
import time
import platform
import os
import subprocess
if platform.system()=="Windows":
    import winsound

lastSoundTime = time.time()
fileTimes = {}#dictionary mapping filepath and the time it was last played
    

def getGroupFolder():
    """returns the location of the group folder. supports both
     linux and windows. assumes it is mounted to /media/ursa/AQOGroupFolder
     for linux"""
    if platform.system()=="Windows":
        groupFolder = os.path.join("\\\\ursa","AQOGroupFolder")
    if platform.system()=="Linux":
        groupFolder = os.path.join("/media","ursa","AQOGroupFolder")
    return groupFolder
    
def getSoundSystem():
    if platform.system()=="Windows":
        return SoundSystem()
    if platform.system()=="Linux":
        return SoundSystemLinux()
    

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, target,duration,*args):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()
        self._target = target
        self._args = args
        self.duration = duration
        self._isPlaying = False
        self.start()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
        
    def run(self):
        startTime = time.time()
        self._isPlaying=True
        while not self.stopped():
            self._target(*self._args)
            if self.duration>0.0:
                elapsedTime = time.time()-startTime
                print "ELAPSED TIME %s " % (elapsedTime)
                if elapsedTime>self.duration:
                    self.stop()
        self._isPlaying=False
        
        
class StoppableThreadCount(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition. Runs a specified number of loops before
    stopping"""

    def __init__(self, target,count,*args):
        super(StoppableThreadCount, self).__init__()
        self._stop = threading.Event()
        self._target = target
        self._args = args
        self.count = count
        self._isPlaying = False
        self.start()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
        
    def run(self):
        self._isPlaying=True
        i=0
        while not self.stopped():
            if self.count>0 and i>=self.count-1:
                self.stop()
            self._target(*self._args)
            i+=1
            print i
                    
        self._isPlaying=False

class SoundSystemLinux():
    """A small similar class that can play basic sounds on linux """
    
    def __init__(self):
        self.absolutePath = os.path.join(getGroupFolder(),"Experiment Humphry","Lab Monitoring", "sounds")
    
    def playFile(self, filePath, count, repeatTimeLimit=0.0):
        """plays sound file once. Set count to 0 or negative to have it play 
        repeatedly until manually stopped.
        repeatTimeLimit sets the minimum time between playing files with identical paths        
        """
        now = time.time()
        if filePath in fileTimes:
            timeSinceLastPlay = now-fileTimes[filePath]
            if timeSinceLastPlay< repeatTimeLimit:
                print "it has only been %s since last play. Will not play again" % timeSinceLastPlay
                return
        fileTimes[filePath]=now# update fileTimes
        try:
            for x in range(0,count):
                subprocess.check_call(["aplay", filePath])
        except Exception as e:
            print "failed to play sound... error message below"
            print e.message

    def againstMyWishes(self,count):
        try:
            self.playFile(os.path.join("sounds","againstMyWishes.wav"), count)
        except Exception as e:
            print "failed to play sound... error message below"
            print e.message
            
class SoundSystem():
    
    def __init__(self):
        self.playingSounds = []#list of sound threads
        self.isPlaying=False
        self.timeIncrement = 0.5#seconds
        self.absolutePath = os.path.join(getGroupFolder(),"Experiment Humphry","Lab Monitoring", "sounds")
        
    def beep(self, frequency, duration):
        """starts a thread beeping using winsound for length duration. Each beep lasts time increment
        set duration to -ve or 0.0 for an infinite lasting beep until stopped manually"""
        try:
            beepThread = StoppableThread(winsound.Beep,duration, int(frequency), int(self.timeIncrement*1000))
            self.playingSounds.append(beepThread)
            self.isPlaying=True
        except Exception as e:
            print "failed to play sound... error message below"
            print e.message
            
    def killAllSounds(self):
        try:
            for thread in self.playingSounds:
                thread.stop()
            self.isPlaying=False
        except Exception as e:
            print "failed to kill sounds... error message below"
            print e.message
        
    def playFile(self, filePath, count):
        """plays sound file count number of times. Set count to 0 or negative to have it play 
        repeatedly until manually stopped."""
        try:
            fileThread = StoppableThreadCount(winsound.PlaySound,count, filePath, winsound.SND_FILENAME )
            self.playingSounds.append(fileThread)
            self.isPlaying=True
        except Exception as e:
            print "failed to play sound... error message below"
            print e.message
            
    def highPriorityAlertAlarm(self,duration):
        self.beep(555,duration)
        self.beep(555*2.,duration)
    
    def againstMyWishes(self,count):
        try:
            self.playFile(os.path.join("sounds","againstMyWishes.wav"), count)
        except Exception as e:
            print "failed to play sound... error message below"
            print e.message

if __name__=="__main__":
    if platform.system()=="Windows":    
        ss=SoundSystem()
        print "windows system found"
    elif platform.system() =="Linux":
        ss=SoundSystemLinux()
        print "linux system found"
    ss.againstMyWishes(1)