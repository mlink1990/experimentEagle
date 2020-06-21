
from enable.api import BaseTool, KeySpec
import traits.api as traits
import logging

logger=logging.getLogger("ExperimentEagle.KeyBindingTool")

class KeyBindings(BaseTool):
    """Tool that can be attached to chaco objects to allow arbitrary functions
    to be called  from key press events.

    attach tool and functions with code like this:
    
    keyBindingsDictionary={enable.KeySpec("F5"):self.model.functionToBeCalled}
    self.chacoObject.tools.append(plotObjects.keyBindingsTool.KeyBindings(component=self.chacoObject,keyBindingsDictionary=keyBindingsDictionary))
    """

    #keys to perform actions
    keyBindingsDictionary = traits.Dict(key_trait=traits.Instance(KeySpec))
    #dictionary matching {Instance(KeySpec)-->pyFunction}
#    refreshKey = traits.Instance(KeySpec, args=("F5",))
#    refreshKeyAlternative = traits.Instance(KeySpec, args=("p",))
#    
    #zoom_out_key = Instance(KeySpec, args=("-",))
    # Keys to zoom in/out in x direction only
    #zoom_in_x_key = Instance(KeySpec, args=("Right", "shift"))
    # Keys to zoom in/out in y direction only
    # Key to go to the previous state in the history.
    #prev_state_key = Instance(KeySpec, args=("z", "control"))
    # Key to go to the next state in the history.

    #--------------------------------------------------------------------------
    #  BaseTool interface
    #--------------------------------------------------------------------------

    def normal_key_pressed(self, event):
        """ Handles a key being pressed when the tool is in the 'normal'
        state.
        """
        logger.info("normal key pressed")
        logger.info("%s keys registered for detection" % len(self.keyBindingsDictionary))
        for key in self.keyBindingsDictionary.iterkeys():
            logger.info("normal key press detected: %s" % event)
            if key.match(event):
                logger.info("key press action found for : %s" % key)
                self.keyBindingsDictionary[key]()
                event.handled = True

    def normal_mouse_enter(self, event):
        """ Try to set the focus to the window when the mouse enters, otherwise
            the keypress events will not be triggered.
        """
        if self.component._window is not None:
            self.component._window._set_focus()
            