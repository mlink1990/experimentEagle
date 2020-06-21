# -*- coding: utf-8 -*-
"""
Created on Sun Apr 05 14:11:18 2015

@author: tharrison
"""

import traits.api as traits
import traitsui.api as traitsui


import scipy
import scipy.misc
import scipy.constants
import logging
import os
import time
import xml.etree.ElementTree as ET # for xml comprehension of experiment runner files
import element

logger=logging.getLogger("ExperimentEagle.physicsProperties")

class PhysicsProperties(traits.HasTraits):
    
    selectedElement = traits.Instance(element.Element)#default of Li6 set in init
    species = traits.Enum(*element.names)

    massATU = traits.Float(22.9897692807,label="mass (u)", desc="mass in atomic mass units")
    decayRateMHz = traits.Float(9.7946,label = u"Decay Rate \u0393 (MHz)", desc= "decay rate/ natural line width of 2S1/2 -> 2P3/2")
    crossSectionSigmaPlus = traits.Float(1.6573163925E-13, label=u"cross section \u03C3 + (m^2)",
                                         desc = "resonant cross section 2S1/2 -> 2P3/2. Warning not accurate for 6Li yet")
    scatteringLength = traits.Float(62.0, label="scattering length (a0)")
    IsatSigmaPlus = traits.Float(6.260021, width=10, label=u"Isat (mW/cm^2)",desc = "I sat sigma + 2S1/2 -> 2P3/2")
    
    TOFFromVariableBool = traits.Bool(True, label = "Use TOF variable?", desc = "Attempt to read TOF variable from latestSequence.xml. If found update the TOF variable automatically")
    TOFVariableName = traits.String("ImagingTimeTOFLi",label="variable name:", desc = "The name of the TOF variable in Experiment Control")
    timeOfFlightTimems = traits.Float(4.0, label = "TOF Time (ms)", desc = "Time of Flight time in ms. Should match experiment control")

    
    trapGradientXFromVariableBool = traits.Bool(True, label = "Use MTGradientX variable?", desc = "Attempt to read MTGradientX variable from latestSequence.xml. If found update the TOF variable automatically")
    trapGradientXVariableName = traits.String("MagneticTrapEvaporation2GradientX",label="variable name:", desc = "The name of the trapGradientX variable in Experiment Control")
    trapGradientX = traits.Float(20.0, label="Trap Gradient (small) (G/cm)", desc = "gradient of trap before time of flight. Smaller of the anti helmholtz gradients" )
    trapFrequencyXHz = traits.Float(100.0, label="Trap frequency X (Hz)", desc = "trap frequency in X direction in Hz")
    trapFrequencyYHz = traits.Float(100.0, label="Trap frequency Y (Hz)", desc = "trap frequency in Y direction in Hz") 
    trapFrequencyZHz = traits.Float(100.0, label="Trap frequency Z (Hz)", desc = "trap frequency in Z direction in Hz")
    imagingDetuningLinewidths = traits.Float(0.0, label= u"imaging detuning (\u0393)", desc = "imaging light detuning from resonance in units of linewidths")    
    
    inTrapSizeX = traits.Float(0.0, label="In trap Size X (pixels)", desc = "size of cloud in trap in x direciton in pixels. Use very short TOF to estimate" )    
    inTrapSizeY = traits.Float(0.0, label="In trap Size Y (pixels)", desc = "size of cloud in trap in y direciton in pixels. Use very short TOF to estimate" )    
    autoInTrapSizeBool = traits.Bool(False, label="Change TOFTime InTrap Calibration?", desc= "Allows user to change the TOF time for which the fit will automatically update the in trap size if the autoSetSize box is checked for Gaussian fit")
    inTrapSizeTOFTimems = traits.Float(0.2, label="In Trap Size TOFTime", desc= "If the TOF time is this value and the autoSetSize box is checked, then we will automatically update the size whenever the TOFTime equals this value" )
    
    pixelSize = traits.Float(9.0, label=u"Pixel Size (\u03BCm)", desc = "Actual pixel size of the camera (excluding magnification)")    
    magnification = traits.Float(0.5, label="Magnification", desc = "Magnification of the imaging system")
    binningSize = traits.Int(1, label=u"Binning Size (px)", desc = "Binning size; influences effective pixel size")
    
    latestSequenceFile = os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry","Experiment Control And Software","currentSequence", "latestSequence.xml")    
    secondLatestSequenceFile = os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry","Experiment Control And Software","currentSequence", "secondLatestSequence.xml")    
    
    traits_view = traitsui.View(
                    traitsui.HGroup(

                        traitsui.VGroup(
                            traitsui.Item("species"),
                            traitsui.Item("selectedElement",editor = traitsui.InstanceEditor(), style="custom", show_label=False),                
                            show_border=True, label = "Element Properties"
                        ),
                        traitsui.VGroup(
                            traitsui.HGroup(traitsui.Item("TOFFromVariableBool"),traitsui.Item("TOFVariableName", visible_when="TOFFromVariableBool"),traitsui.Item("timeOfFlightTimems",style="readonly",visible_when="(TOFFromVariableBool)"),traitsui.Item("timeOfFlightTimems",visible_when="(not TOFFromVariableBool)")),
                            traitsui.HGroup(traitsui.Item("trapGradientXFromVariableBool"),traitsui.Item("trapGradientXVariableName", visible_when="trapGradientXFromVariableBool"),traitsui.Item("trapGradientX",style="readonly",visible_when="(trapGradientXFromVariableBool)"),traitsui.Item("trapGradientX",visible_when="(not trapGradientXFromVariableBool)")),
                            traitsui.Item("trapFrequencyXHz"),
                            traitsui.Item("trapFrequencyYHz"),
                            traitsui.Item("trapFrequencyZHz"),
                            traitsui.Item("inTrapSizeX"),
                            traitsui.Item("inTrapSizeY"),
                            traitsui.HGroup(traitsui.Item("autoInTrapSizeBool"),traitsui.Item("inTrapSizeTOFTimems", visible_when="(autoInTrapSizeBool)")),
                             label="Experiment Parameters", show_border=True
                        ),
                        traitsui.VGroup(
                            traitsui.Item("imagingDetuningLinewidths"), 
                            traitsui.Item("pixelSize"),
                            traitsui.Item("binningSize"),
                            traitsui.Item("magnification"), label="Camera and Imaging", show_border=True
                        )
                    )                    
                    )
    
    
    def __init__(self, **traitsDict):
        super(PhysicsProperties, self).__init__(**traitsDict)
        # self.selectedElement = element.Li6#set default element
        self.species = element.Li6.nameID
        #pull some uselful variables from the physics constants dictionary for reference
        
        self.constants = scipy.constants.physical_constants
        self.u = self.constants["atomic mass constant"][0]
        self.bohrMagneton = self.constants["Bohr magneton"][0]
        self.bohrRadius = self.constants["Bohr radius"][0]
        self.kb = self.constants["Boltzmann constant"][0]
        self.joulesToKelvin = self.constants["joule-kelvin relationship"][0]
        self.hbar = self.constants["Planck constant over 2 pi"][0]
        self.h = self.constants["Planck constant"][0]
        self.joulesToHertz = self.constants["joule-hertz relationship"][0]
        self.hertzToKelvin =self.constants["hertz-kelvin relationship"][0]
        self.a0 = self.constants["Bohr radius"][0]
        
    def _species_changed(self):
        """update constants according to the changed species """
        logger.debug("species changed to %s" % self.species)
        self.selectedElement = element.elements[self.species]
    
    def updatePhysics(self):
        try:
            logger.debug("attempting to update physics from xml")
            if os.path.exists(self.latestSequenceFile):
                modifiedTime = os.path.getmtime(self.latestSequenceFile)
                imageTime = self.selectedFileModifiedTime
                now = time.time()
                timeDiff = imageTime-modifiedTime
                timeDiff += 31 # ToDo: debug this strange time offset!!
                if timeDiff>300.0: #>5min
                    logger.warning("Found a time difference of >5min between modification time of XML and of image. Are you sure the latest XML file is being updated? Check snake is running?")
                if timeDiff<0:
                    logger.error("Found very fresh sequence file. Probably read already variables of next sequence?")
                    logger.warning("Use second last sequence file instead..")
                    self.tree = ET.parse(self.secondLatestSequenceFile)
                else:
                    self.tree = ET.parse(self.latestSequenceFile)
                logger.warning("Age of sequence file: {}".format(timeDiff)) # for debugging, remove or reduce log level later ;P
                # logger.warning("Age of image file: {}".format(imageTime))
                # logger.warning("Now = {}".format(now)) # for debugging, remove or reduce log level later ;P
                # logger.warning("ModifiedTime of xml = {}".format(modifiedTime)) # for debugging, remove or reduce log level later ;P
                self.root = self.tree.getroot()
                variables = self.root.find("variables")
                self.variables = {child[0].text:float(child[1].text) for child in variables}
                logger.debug("Read a TOF time of %s from variables in XML " % self.variables[self.TOFVariableName])
            else:
                logger.error("Could not find latest xml File. cannot update physics.")
                return
        except Exception as e:
            logger.error("Error when trying to load XML %s" % e.message)
            return
            
        #update TOF Time
        if self.TOFFromVariableBool:
            logger.debug("attempting to update TOF time from xml")
            try:
                self.timeOfFlightTimems = self.variables[self.TOFVariableName]*1.0E3
            except KeyError as e:
                logger.error("incorrect variable name. No variable %s found. Using default 1ms" % self.TOFVariableName )
                self.timeOfFlightTimems = 1.0
            
        if self.trapGradientXFromVariableBool:
            logger.debug("attempting to update trapGradientX from xml")
            try:
                self.trapGradientX = self.variables[self.trapGradientXVariableName]
            except KeyError:
                logger.error("incorrect variable name. No variable %s found. Using default 50G/cm" % self.trapGradientXVariableName )
                self.trapGradientX = 50.0
            
if __name__=="__main__":
    physics = PhysicsProperties()
    physics.configure_traits()