# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 12:48:16 2016

This follows the mathematica sheet Rabi Oscillations and Pi Pulses/Higgs mode rabi calibration master - 2016 08 16.nb 

We use the fact  we measure the on resonance (81.31 MHz 2 to 3 rabi frequency at 910G at 
a known input MXG power and hence measured the omega_0 for this power. This lets us then 
calculate alpha and effective rabi frequency for any detuning or power)
"""
import scipy
#12 FB resoance properties
aBackground_12 = -1405#Bohr radii
deltaB_12 = -300#Gauss
B0_12 = 834.15 #Gauss

#13 FB resonance properties
aBackground_13 = -1727#Bohr radii
deltaB_13 = -122.3#Gauss
B0_13 = 690.43 #Gauss

#23 FB resonance properties
aBackground_23 = -1490#Bohr radii
deltaB_23 = -222.3#Gauss
B0_23 = 811.22 #Gauss

aBohr = 5.29176E-11

kHz = 1.0E3
MHz = 1.0E6
uK = 1.0E-6
h = 6.626E-34
kB = 1.38065E-23

####IMPORTANT PARAMETERS#####
calibrationDict = {#dictionary mapping field compressions to calibrations and resonance frequencies
#(fieldValue, compressionFactor):(rabiFreq kHz, RF power, f0 (MHz))
#850G is usually 20dB attenuator
(870,0.1):(9.09*kHz, 5.0, 81.5925),
(870,0.2):(9.09*kHz, 5.0, 81.5925),
(870,0.3):(9.09*kHz, 5.0, 81.5925),
(870,0.4):(9.09*kHz, 5.0, 81.5925),
(870,0.5):(9.09*kHz, 5.0, 81.5925),
(870,0.6):(9.09*kHz, 5.0, 81.5925),
#910G is usually 20dB attenuator
(928.25,0.1):(6.176*kHz, 10.0,81.30942 ),
(928.25,0.2):(6.176*kHz, 10.0,81.31040 ),
(928.25,0.3):(6.176*kHz, 10.0,81.31121 ),
(928.25,0.4):(6.176*kHz, 10.0,81.31143 ),
(928.25,0.5):(6.176*kHz, 10.0,81.31152 ),
(928.25,0.6):(6.176*kHz, 10.0,81.31191 ),
#950G is usually 10dB attenuator
(968.75,0.1):(8.261*kHz,5.0, 81.1345 ),
(968.75,0.2):(8.261*kHz,5.0, 81.1345 ),
(968.75,0.3):(8.261*kHz,5.0, 81.1345 ),
(968.75,0.4):(8.261*kHz,5.0, 81.1345 ),
(968.75,0.5):(8.261*kHz,5.0, 81.1345 ),
(968.75,0.6):(8.261*kHz,5.0, 81.1345 )
}

#dipole trap frequencies calibrations
dipoleTrapMeasuredQuantities = {}
dipoleTrapMeasuredQuantities["setPointHorizontalForMeasured"] = 0.1
dipoleTrapMeasuredQuantities["setPointVerticalForMeasured"] = 0.1
dipoleTrapMeasuredQuantities["DMMVoltageForMeasurement"] = 1.4254
dipoleTrapMeasuredQuantities["frequenciesHorizontalAlone"] = scipy.array([16.26, 69.37, 166.0])
dipoleTrapMeasuredQuantities["frequenciesBoth"] = scipy.array([91.76, 134.14, 166.0])
dipoleTrapMeasuredQuantities["frequenciesVerticalAlone"] = scipy.sqrt(scipy.array(dipoleTrapMeasuredQuantities["frequenciesBoth"] )**2-scipy.array(dipoleTrapMeasuredQuantities["frequenciesHorizontalAlone"])**2)

def dipoleTrapFrequencies(setVoltageHorizontal, setVoltageVertical, DMMSetVoltage = 1.4254 ):
    """returns the trap frequencies in Hz given the input set voltage points and DMM value
    DMM value is required as the Feshbach coils affect the trapping potential. Values are derived
    from T Harrison measurement on 2016 10 13 see Eagle Log and above values"""
    BFactor = (DMMSetVoltage/dipoleTrapMeasuredQuantities["DMMVoltageForMeasurement"])**0.5
    HFactor = (setVoltageHorizontal/dipoleTrapMeasuredQuantities["setPointHorizontalForMeasured"])**0.5
    VFactor = (setVoltageVertical/dipoleTrapMeasuredQuantities["setPointVerticalForMeasured"])**0.5
    hFreqs = dipoleTrapMeasuredQuantities["frequenciesHorizontalAlone"]
    vFreqs = dipoleTrapMeasuredQuantities["frequenciesVerticalAlone"]
    return scipy.sqrt(scipy.array([(BFactor*hFreqs[0])**2+(VFactor*vFreqs[0])**2,(HFactor*hFreqs[1])**2+(VFactor*vFreqs[1])**2,(HFactor*hFreqs[2])**2]))

#backup made in ThesisLargeData
def feshbachResonance(aBackground,deltaB, B0, B):
    return aBackground*(1-deltaB/(B-B0))

def feshbachResonance_12(B):
    """returns scattering length of 12 feshbach resonance at field B in G. returns
    in units of bohr radii"""
    return feshbachResonance(aBackground_12,deltaB_12,B0_12,B)
    
def feshbachResonance_13(B):
    """returns scattering length of 12 feshbach resonance at field B in G. returns
    in units of bohr radii"""
    return feshbachResonance(aBackground_13,deltaB_13,B0_13,B)
    
def feshbachResonance_23(B):
    """returns scattering length of 12 feshbach resonance at field B in G. returns
    in units of bohr radii"""
    return feshbachResonance(aBackground_23,deltaB_23,B0_23,B)

def BCSGap(B, EFermikHz, kFa):
    """ B Field Gauss, EFermi in kHz, and kFa in dimensionless
    returns BCS gap energy in kHz"""
    return 1.08268 * EFermikHz * scipy.exp( scipy.pi / (2 *kFa ))

def omega0(PdBm,omegaMeasured,PdBForMeasured):
    """calculates the on resonance rabi frequency for a given input power
    on the MXG. copied from mathematica sheet"""
    return omegaMeasured*10.0**(0.5*0.1*(PdBm-PdBForMeasured))
    
def alpha(delta,omega0):
    """returns the rabi fraction"""
    return (1.0+(delta/omega0)**2.)**(-1.0)
    
def deltaForFixedAlpha(PdBm, alpha,omegaMeasured,PdBForMeasured):##
    """returns the detuning for a given RF power that should be used """
    return omega0(PdBm,omegaMeasured,PdBForMeasured) *( (1.-alpha)/alpha )**0.5
    
def omegaEffective(omega0, delta):
    """returns effective rabi frequency """
    return (omega0**2+delta**2)**0.5

def find(variableName, parameterList):
    """helper function for finding the value of a fitted parameter or 
    derived parameter. Goes through parameter List and returns when it finds
    the correct value"""
    for variable in parameterList:
        if variable.name==variableName:
            return variable.value
    return None

def BCSGapFromCondensateFraction(temperature, condensateFraction):
    """converts a condensate fraction and temperature into a BCS gap.
    assumes 0 temperature formula. That T_c = 1.78/pi delta0 and
    condensate fraction = 1-(T/Tc)**3. returns value in Hz"""
    return 3.678E10 * temperature * (1 - condensateFraction )**(-0.3333)


def calculateEFermi(N,fx,fy,fz):
    """Fermi energy given atom number N and frequencies in Hz """
    return (6*N)**(1./3)*(fx*fy*fz)**(1./3)
    
def run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues):
    """called by log analyser """
    
    piPulseBFieldGauss = xmlVariablesDict["PiPulseBFieldGauss"]#used in calibration dictionary
    finalHorizontalSetPointVoltage = xmlVariablesDict["BeamPowerSetVoltageDipoleHorizontalRecompressed"]#used in dipole trap frequency calculation
    finalVerticalSetPointVoltage = xmlVariablesDict["BeamPowerSetVoltageDipoleVerticalRecompressed"]
    
    omegaMeasured,PdBForMeasured, f0 = calibrationDict[(piPulseBFieldGauss,finalHorizontalSetPointVoltage)]
    
    
    dmmValue = xmlVariablesDict["PIDFeshbachSetVoltage"]
    fieldValueGauss = (dmmValue/1.531) * 853.819
    freqX,freqY,freqZ = dipoleTrapFrequencies(finalHorizontalSetPointVoltage,finalVerticalSetPointVoltage,dmmValue)# calculate trap frequencies from calibrated values
    
    a12 = feshbachResonance_12(fieldValueGauss)
    a13 = feshbachResonance_13(fieldValueGauss)
    a23 = feshbachResonance_23(fieldValueGauss)
    
    #these value were calculated with horizontal set voltage 0.1 and vertical set voltage 0
    #now we recompress for BCS side
    EFermi = calculateEFermi(1E6, freqX,freqY,freqZ)/1000.0  # kHz
    kFermi = 34499.6*(EFermi*1000.0)**0.5 # SI units (1/m)

    #kFa    
    kFa_12 = kFermi*a12*aBohr
    kFa_13 = kFermi*a13*aBohr
    kFa_23 = kFermi*a23*aBohr
    #1/kFa
    kFa_12_inv = 1/kFa_12
    kFa_13_inv = 1/kFa_13
    kFa_23_inv = 1/kFa_23
    
    #BCS Gap
    BCSGap_12 = BCSGap(fieldValueGauss,EFermi,kFa_12  )
    BCSGap_13 = BCSGap(fieldValueGauss,EFermi,kFa_13  )
    BCSGap_23 = BCSGap(fieldValueGauss,EFermi,kFa_23  )
    
    try:
        temperature = find("Temperature",derivedValues )
        if temperature==None:
            temperature = 0.0
        condensateFraction = find("Condensate Fraction",derivedValues )
    except Exception as e:
        temperature = 0.0
        condensateFraction =0.0
        print "can't find temperature. error = %s " % e.message
    
    bcsGapFromCondensateFractionkHz = BCSGapFromCondensateFraction(temperature*uK,condensateFraction )/kHz
        
    powerdBm = xmlVariablesDict["PiPulseRFPowerdBm"]
    freq = xmlVariablesDict["PiPulseRFFreqMHz"]
    omega0kHz = omega0(powerdBm,omegaMeasured,PdBForMeasured)/kHz
    detuningkHz = (freq-f0)*1000.0#kHz
    detuningSign = scipy.sign(detuningkHz)
    calculatedAlpha = alpha(detuningkHz*kHz,omega0kHz*kHz ) 

    rabiFreqEffectivekHz = omegaEffective(omega0kHz, detuningkHz)
    rabiFreqEffectiveGapUnits = rabiFreqEffectivekHz/BCSGap_12
    
    rabiFreqEffectivekHzSigned = detuningSign*rabiFreqEffectivekHz
    rabiFreqEffectiveGapUnitsSigned = detuningSign*rabiFreqEffectiveGapUnits
    names = ["fieldValueGaussPiPulse","EFermi","kFermi","a12","a13","a23","kFa_12","kFa_13","kFa_23","BCSGap_12","BCSGap_13","BCSGap_23","rabiFreqEffectivekHz","rabiFreqEffectiveGapUnits","rabiFreqEffectivekHzSigned","rabiFreqEffectiveGapUnitsSigned","detuningkHz","detuningSign","omega0kHz","calculatedAlpha","bcsGapFromCondensateFractionkHz"]
    values = [fieldValueGauss,EFermi,kFermi,a12,a13,a23,kFa_12,kFa_13,kFa_23,BCSGap_12,BCSGap_13,BCSGap_23,rabiFreqEffectivekHz,rabiFreqEffectiveGapUnits,rabiFreqEffectivekHzSigned,rabiFreqEffectiveGapUnitsSigned,detuningkHz,detuningSign,omega0kHz,calculatedAlpha,bcsGapFromCondensateFractionkHz]
    roundingDigits = 4
    values = map(round, values,[roundingDigits]*len(values))
    return names,values
    
if __name__=="__main__":
    varsDict = {"PiPulseBFieldGauss":928.25,"PIDFeshbachSetVoltage":1.6336, "BeamPowerSetVoltageDipoleHorizontalRecompressed":0.2,"BeamPowerSetVoltageDipoleVerticalRecompressed":0.1,"PiPulseRFPowerdBm":11.5,"PiPulseRFFreqMHz":81.6221 }
    names=run(None,varsDict,None,None)
    for name,val in zip(names[0],names[1]):
        print name,val
    
