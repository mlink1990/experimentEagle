# -*- coding: utf-8 -*-
"""
Created on Tue Aug 16 09:43:51 2016

@author: tharrison

used in logFilePlots GUI, user can request the selected log file plot to auto update
and use this dialog to choose basic settings. Initially it was very basic and was a subclass
defined in auto_refresh fired function. Now with alerts and sounds it is  a separate class dialog
window
"""

import traits.api as traits
import traitsui.api as traitsui
from traitsui.menu import OKButton, CancelButton

DEFAULT_ALERT_CODE = """def alertAnalyser(dataFrameTail):
    '''dataFrameTail is a dataframe with only
    the last linesOfDataFrame at the end.
    If function returns True it will send requested alerts.
    False will result in no action'''
    boolFrame = dataFrameTail["N"]>1E10
    return boolFrame.any()
    """

class AutoRefreshDialog(traits.HasTraits):

    minutes = traits.Float(1.0)
    autoRefreshBool = traits.Bool()

    emailAlertBool = traits.Bool(False)
    soundAlertBool = traits.Bool(False)
    linesOfDataFrame = traits.Range(1, 10)
    alertCode = traits.Code(DEFAULT_ALERT_CODE, desc="python code for finding alert worthy elements")

    basicGroup = traitsui.Group("minutes","autoRefreshBool")
    alertGroup = traitsui.VGroup(
        traitsui.HGroup(traitsui.Item("emailAlertBool"),traitsui.Item("soundAlertBool")),
        traitsui.Item("linesOfDataFrame",visible_when="emailAlertBool or soundAlertBool"),
        traitsui.Item("alertCode", visible_when="emailAlertBool or soundAlertBool")
    )

    traits_view = traitsui.View(
        traitsui.VGroup(basicGroup, alertGroup),
        title="auto refresh", buttons=[OKButton],
                                kind='livemodal', resizable = True)

if __name__=="__main__":
    ard = AutoRefreshDialog()
    ard.configure_traits()