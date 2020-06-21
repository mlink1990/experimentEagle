# -*- coding: utf-8 -*-
"""
Created on 20/10/2016 10:16 AM
Part of: experimentEagle
Filename: __init__.py
@author: tharrison


"""
import processors
import standardAndor0
import standardAndor1
import standardAndor2
import standardAlta1
import andor1ThreePulses
import debugProcessors
import rawImageBinning
import baslerOD

#For a processor to appear in experiment eagle it must be added to the dictionary at the bottom of this file


validProcessors = {"raw image":processors.Processor(), "standard ANDOR 0":standardAndor0.StandardAndor0(), "standard Alta 1":standardAlta1.StandardAlta1(), "standard ANDOR 1":standardAndor1.StandardAndor1(), "ANDOR 1 three pulses":andor1ThreePulses.Andor1ThreePulses(), "standard ANDOR 2":standardAndor2.StandardAndor2(),"debug atoms/light":debugProcessors.DEBUGAtomsOverLight(),
                   "raw image binning":rawImageBinning.rawImageBinning(), "baslerOD": baslerOD.BaslerOD()}
validNames = validProcessors.keys()


if __name__=="__main__":
    import os
    imagePath = os.path.join("\\\\ursa", "AQOGroupFolder", "Experiment Humphry", "Experiment Control and Software",
                             "exampleBECImages", "evaporation Optimisation 7_ANDOR0FT_2010 125140.png")
    validProcessors["raw image"].process(imagePath)