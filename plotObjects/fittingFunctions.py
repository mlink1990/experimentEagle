# -*- coding: utf-8 -*-
"""
Created on Tue Apr 05 09:55:44 2016

@author: User
"""
import scipy

#here is the class definition for fitting funtion
class FittingFunction(object):
    """wrapper for a python fitting function. adds the optional guess functions,
    verbal description and allows """
    
    def __init__(self, fittingFunction, guessFunction=None,desc=None,prettyEquationString=None):
        self.fittingFunction = fittingFunction
        self.guessFunction = guessFunction
        self.desc = desc
        self.prettyEquationString = prettyEquationString
        
        
#######
#DEFINE FITTING FUNCTIONS AND GUESS FUNCTIONS
#######

#standard fitting functions

##################################################
def linear(x,m,c):
    return m*x+c
    
def linear_guess(xs,ys):
    return {"m":(ys.max()-ys.min())/(xs.max()-xs.min()), "c":scipy.average(ys)}
##################################################  
def quadratic(x,a,b,c):
    return a*x**2+b*x+c
##################################################       
def gaussian(x,A, sigma, x0, B):
    return A*scipy.exp( -(x-x0)**2. / (2.*sigma**2. ) )+B

def gaussian_guess(xs,ys):
    A=ys.max()-ys.min()
    B=ys.min()
    #x0 = (xs.max()+xs.min())/2.0
    maximumIndex = scipy.argmax(A)
    x0 = xs[maximumIndex]
    sigma = (xs.max()-x0)/2.0
    return {"A":A,"B":B,"x0":x0,"sigma":sigma}
##################################################
def lorentzian(x,x0,gamma,A,B):
    return A*gamma**2 / ((x-x0)**2+gamma**2)+B
    
def lorentzian_guess(xs,ys):
    A=ys.max()-ys.min()
    B=ys.min()
    #x0 = (xs.max()+xs.min())/2.0
    maximumIndex = scipy.argmax(A)
    x0 = xs[maximumIndex]
    sigma = (xs.max()-x0)/2.0
    return {"A":A,"B":B,"x0":x0,"sigma":sigma}
##################################################    
def parabola(x,x0,a,B):
    return a*(x-x0)**2+B
    
def parabola_guess(xs,ys):
    return {"a":1, "B":scipy.average(ys),"x0":(xs.max()+xs.min())/2.0}
##################################################   
def exponentialDecay(x,A,tau,B):
    return A*scipy.exp(-x/tau)+B
    
def exponentialDecay_guess(xs,ys):
    A=ys.max()-ys.min()
    B=ys.min()
    tau = (xs.max()+xs.min())/2.0
    return {"A":A,"B":B,"tau":tau}
##################################################   
def sineWave(x, f, phi, A,B):
    return A*scipy.sin(2*scipy.pi*f*x+phi)+B
    
def sineWave_guess(xs,ys):
    A=ys.max()-ys.min()
    B=ys.min()
    phi = 0.001
    f = 1.0/(xs.max()-xs.min())
    return {"A":A,"B":B,"phi":phi,"f":f}
##################################################
def sineWaveDecay1(x, f, phi, A,B, tau):
    return A*scipy.exp(-x/tau)*scipy.sin(2*scipy.pi*f*x+phi)+B
    
def sineWaveDecay1_guess(xs,ys):
    A=ys.max()-ys.min()
    B=ys.min()
    phi = 0.001
    f = 1.0/(xs.max()-xs.min())
    tau = (xs.max()+xs.min())/2.0
    return {"A":A,"B":B,"phi":phi,"f":f, "tau":tau}
##################################################
def sineWaveDecay2(x, f, phi, A,B, tau):
    return A*scipy.exp(-x/tau)*scipy.sin(2*scipy.pi*((f**2-(1/(2*scipy.pi*tau))**2)**0.5)*x+phi)+B
    
def sineWaveDecay2_guess(xs,ys):
    A=ys.max()-ys.min()
    B=ys.min()
    phi = 0.001
    f = 1.0/(xs.max()-xs.min())
    tau = (xs.max()+xs.min())/2.0
    return {"A":A,"B":B,"phi":phi,"f":f, "tau":tau}
##################################################    
def sincSquared(x,A,B,tau,x0):
    return A*(scipy.sinc(tau * 2*scipy.pi * (x-x0) ))**2 / (2*scipy.pi) + B
##################################################
def sineSquared(x, f, phi, A, B):
    return A*scipy.sin(2*scipy.pi*f*x+phi)**2+B

def sineSquared_guess(xs,ys):
    A=ys.max()-ys.min()
    B=ys.min()
    phi = 0.001
    f = 1.0/(xs.max()-xs.min())
    return {"A":A,"B":B,"phi":phi,"f":f}
##################################################
def sineSquaredDecay(x, f, phi, A, B, tau):
    return A*scipy.exp(-x/tau)*scipy.sin(2*scipy.pi*f*(x+phi)/2.0)**2+B
    
def sineSquaredDecay_guess(xs,ys):
    A=ys.max()-ys.min()
    B=ys.min()
    phi = 0.001
    f = 1.0/(xs.max()-xs.min())
    tau = (xs.max()+xs.min())/2.0
    return {"A":A,"B":B,"phi":phi,"f":f, "tau":tau}
##################################################    
      


        