# -*- coding: utf-8 -*-
"""
Created on 21/10/2016 10:24 AM
Part of: experimentEagle
Filename: optionsDictEditor.py
@author: tharrison

These classes allow for the creation of a nice GUI dialog for editing the options of processors
In general options are either Bools, floats or ints.
To make the GUI look nice and have the appropriate editors, I use the add_trait to dynamically create the appropriate trait type

"""
import traits.api as traits
import traitsui.api as traitsui
import logging
import collections

logger=logging.getLogger("ExperimentEagle.OptionsDictionaryEditor")



class Option(traits.HasTraits):

    name = traits.String(desc="key from options dictionary. describes the option")
    value = traits.Any()
    traits_view = traitsui.View(traitsui.HGroup( traitsui.Item("name", style="readonly", springy=True, show_label=False),traitsui.Item("value", show_label=False, springy=True) ) )


def createOption(name, initialValue):
    """creates an option with a boolean attribute as the value, type should be the result of type(value)"""
    option = Option(name=name)
    if type(initialValue) is bool:
        option.add_trait("value", traits.Bool(initialValue))
    elif type(initialValue) is int:
        option.add_trait("value", traits.Int(initialValue))
    elif type(initialValue) is float:
        option.add_trait("value", traits.Float(initialValue))
    elif type(initialValue) is str:
        option.add_trait("value", traits.File(initialValue))
        # # need to modify the view, not sure how to make this more elegantly
        option.traits_view = traitsui.View(traitsui.HGroup( traitsui.Item("name", style="readonly", springy=True, show_label=False),traitsui.Item("value", show_label=False, springy=True, editor = traitsui.FileEditor(dialog_style='save')) ) )
    else:
        logger.warning("unrecognised option type ({}) in processor. Using traits.Any Editor and value".format(type(initialValue)))
        option.add_trait("value", traits.Any(initialValue))
    return option

class OptionsDictionaryDialog(traits.HasTraits):
    """options dictionary dialog for editing the options of an image processor"""

    optionsList = traits.List(Option)
    traits_view = traitsui.View( traitsui.VGroup(
        traitsui.Item("optionsList", editor=traitsui.ListEditor(style="custom"), show_label=False,resizable=True)
    ),buttons = [traitsui.OKButton, traitsui.CancelButton], kind="livemodal",
    width=0.15, height=0.5)

    def populateOptionsFromDictionary(self, optionsDict):
        """creates the options for GUI from an options dictionary"""
        for key, value in optionsDict.iteritems():
            self.optionsList.append(createOption(key,value))

    def getOptionsDictionaryFromList(self):
        """returns an options dictionary from the current state of the options list"""
        return collections.OrderedDict([(option.name,option.value) for option in self.optionsList])

def editOptionsDialog(optionsDict):
    """give current optionsDict and this will create a GUI to edit the options. If user presses OK, then
    the optionsDict will be returned otherwise None is returned. This function is called by the processor
    parent class"""
    dialog = OptionsDictionaryDialog()
    dialog.populateOptionsFromDictionary(optionsDict)
    returnCode = dialog.configure_traits()
    if not returnCode:#user clicked cancel
        logger.info("detected a cancel return code. Will not update optionsDict")
        return None
    else:#user clicked OK or X (close) (note the X click is not desireable!)
        logger.info("returning optionsDict")
        return dialog.getOptionsDictionaryFromList()



if __name__=="__main__":
    optionsDict = collections.OrderedDict((("process?", True), ("darkSubtraction?", True),
                             ("rescale?", True), ("rescaleInitialX", 350), ("rescaleInitialY", 100),
                             ("rescaleWidth", 100), ("rescaleHeight", 100),
                             ("rotationAngle", -47.8)))

    print editOptionsDialog(optionsDict)