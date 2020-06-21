import os
import sys

if sys.platform == "win32":
    ursaGroupFolder = os.path.join("G:",os.sep)
    humphryNASFolder = os.path.join("N:",os.sep)
    humphryNASTemporaryData = os.path.join("T:",os.sep)
elif sys.platform == "linux2":
    ursaGroupFolder = os.path.join(os.sep,"media","ursa","AQOGroupFolder")
    humphryNASFolder = os.path.join(os.sep,"media","humphry-nas","Humphry")
    humphryNASTemporaryData = os.path.join(os.sep,"media","humphry-nas","TemporaryData")
else:
    raise NotImplementedError()

def isHumphryNASConnected():
    return os.path.exists(os.path.join(humphryNASFolder,"Data"))
def isURSAConnected():
    return os.path.exists(os.path.join(ursaGroupFolder,"Experiment Humphry"))

if __name__ == "__main__":
    print( isHumphryNASConnected() )
    print( isURSAConnected() )