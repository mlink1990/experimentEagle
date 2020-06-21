# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 12:45:06 2016

@author: User


log analysers can be used to perform analytical or data pulling actions after a fit is performed.
This could be for example, to calculate some compicated derived property not calculated in a fit
 or to grab some relevant data like the plug power or MOT fluorescence and write it to the log file
 
each file in the logAnalyser package should contain a run() function that has the following signature:

run(imageDataArray, xmlVariablesDict, fittedParameters, derivedValues)
and returns [list of column names], [list of values]


-the image data as a numpy array
        -the xml variables dictionary
        -the fitted paramaters
        -the derived values
"""

