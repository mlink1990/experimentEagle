# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 12:57:05 2015

@author: tharrison
"""
import traits.api as traits
import traitsui.api as traitsui


class Element(traits.HasTraits):
    """parent class for a defined element. Element can be chosen as
    a physics property in the physics tab and allow fits to calculate
    properties of atomic clouds"""
    nameID = traits.String(desc="name of element for dictionary key (no superscripts etc)")
    massATU = traits.Float(22.9897692807,label="mass (u)", desc="mass in atomic mass units")
    decayRateMHz = traits.Float(9.7946,label = u"Decay Rate \u0393 (MHz)", desc= "decay rate/ natural line width of 2S1/2 -> 2P3/2")
    
    crossSectionSigmaPlus = traits.Float(1.6573163925E-13, label=u"cross section \u03C3 + (m^2)",
                                         desc = "resonant cross section 2S1/2 -> 2P3/2. Warning not accurate for 6Li yet")

    scatteringLength = traits.Float(62.0, label="scattering length (a0)")
    IsatSigmaPlus = traits.Float(6.260021, width=10, label=u"Isat (mW/cm^2)",desc = "I sat sigma + 2S1/2 -> 2P3/2")
    
    traits_view = traitsui.View( 
                    traitsui.VGroup(
                        traitsui.Item("nameID", style="readonly"),
                        traitsui.Item("massATU", style="readonly"),
                        traitsui.Item("decayRateMHz", style="readonly"),
                        traitsui.Item("crossSectionSigmaPlus", style="readonly"),
                        traitsui.Item("scatteringLength"),
                        traitsui.Item("IsatSigmaPlus", style="readonly")
                        )
                    )
                          
Na23 = Element(nameID="Na23", 
               massATU=22.9897692807,decayRateMHz=9.7946,
               crossSectionSigmaPlus=1.6573163925E-13,
               scatteringLength=62.0,IsatSigmaPlus=6.260021 )
               
Li6 = Element(nameID="Li6", 
               massATU=6.0151214,decayRateMHz=5.8724,
               crossSectionSigmaPlus=2.15E-13,
               scatteringLength=0.0,IsatSigmaPlus=2.54 )
               
Li6Molecule = Element(nameID="2Li6 (Molecule)", 
               massATU=2*6.0151214,decayRateMHz=5.8724,
               crossSectionSigmaPlus=2.15E-13,
               scatteringLength=0.0,IsatSigmaPlus=2.54 )

               
elements = {Na23.nameID:Na23,Li6.nameID:Li6,Li6Molecule.nameID:Li6Molecule}
names = [Na23.nameID,Li6.nameID,Li6Molecule.nameID]