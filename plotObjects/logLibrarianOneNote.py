# -*- coding: utf-8 -*-
"""
Created on Sat Mar 05 17:15:06 2016

@author: tharrison
"""

import traits.api as traits
import traitsui.api as traitsui
import os
import datetime
import logging
import csv
import oneNotePython
import oneNotePython.eagleLogsOneNote


logger=logging.getLogger("ExperimentEagle.logFilePlot")


class EntryBlock(traits.HasTraits):
    
    fieldName = traits.String("fieldName",desc = "describes what the information to be entered in the text block is referring to")
    textBlock = traits.String()
    
    traits_view = traitsui.View(traitsui.VGroup(
                    traitsui.Item("fieldName",show_label=False, style="readonly"),
                    traitsui.Item("textBlock",show_label=False, style="custom"),
                    show_border=True, label="information"
                        ))
    
    def __init__(self, **traitsDict):
        """user supplies arguments in init to supply class attributes defined above """
        super(EntryBlock,self).__init__(**traitsDict)
    
    def clearTextBlock(self):
        self.textBlock = ""

class AxisSelector(traits.HasTraits):
    """here we select what axes the user should use when plotting this data """
    masterList = traits.List
    masterListWithNone =  traits.List
    xAxis = traits.Enum(values="masterList")
    yAxis = traits.Enum(values="masterList")
    series = traits.Enum(values="masterListWithNone")
    
    traits_view=traitsui.View(traitsui.VGroup(traitsui.Item("xAxis",label="x axis"),traitsui.Item("yAxis",label="y axis"),
                                  traitsui.Item("series",label="series"),show_border=True, label="axes selection"))
    
    def __init__(self, **traitsDict):
        """allows user to select which axes are useful for plotting in this log"""
        super(AxisSelector, self).__init__(**traitsDict)
    
    
    def _masterList_default(self):
        """gets the header row of log file which are interpreted as the column
        names that can be plotted."""
        logger.info("updating master list of axis choices")
        logger.debug("comment file = %s" % self.logFile)
        print "comment file = %s" % self.logFile
        if not os.path.exists(self.logFile):
            return []
        try:
            with open(self.logFile) as csvfile:
                headerReader = csv.reader(csvfile)
                headerRow=headerReader.next()
            return headerRow
        except IOError:
            return []
            
    def _masterListWithNone_default(self):
        return ["None"]+self._masterList_default()
        

class Librarian(traits.HasTraits):
    """Librarian provides a way of writing useful information into the 
    log folder for eagle logs. It is designed to make the information inside
    an eagle log easier to come back to. It mainly writes default strings into
    the comments file in the log folder"""
    
    logType = traits.Enum("important","debug","calibration")
    writeToOneNoteButton = traits.Button("save")
    refreshInformation = traits.Button("refresh")
    saveImage = traits.Button("save plot")
    axisList = AxisSelector()
    purposeBlock = EntryBlock(fieldName="What is the purpose of this log?")
    resultsBlock = EntryBlock(fieldName = "Explain what the data shows (important parameters that change, does it make sense etc.)?")
    commentsBlock = EntryBlock(fieldName = "Anything Else?")
    saveButton = traits.Button("Save")
#    notebooks = traits.Enum(values = "notebookNames") # we could let user select from a range of notebooks
#    notebookNames = traits.List
    notebookName = traits.String("Humphry's Notebook")
    sectionName = traits.String("Eagle Logs")
    logName = traits.String("")
    xAxis = traits.String("")
    yAxis = traits.String("")

    traits_view = traitsui.View(
        traitsui.VGroup(
            traitsui.Item("logName",show_label=False, style="readonly"),            
            traitsui.Item("axisList",show_label=False, editor=traitsui.InstanceEditor(),style='custom'),
            traitsui.Item("purposeBlock",show_label=False, editor=traitsui.InstanceEditor(),style='custom'),
            traitsui.Item("resultsBlock",show_label=False, editor=traitsui.InstanceEditor(),style='custom'),
            traitsui.Item("commentsBlock",show_label=False, editor=traitsui.InstanceEditor(),style='custom'),
            traitsui.HGroup(traitsui.Item("writeToOneNoteButton",show_label=False),traitsui.Item("refreshInformation",show_label=False)),
        )  , resizable=True  , kind ="live", title="Eagle OneNote"
    )    
    
    def __init__(self, **traitsDict):
        """Librarian object requires the log folder it is referring to. If a .csv
        file is given as logFolder argument it will use parent folder as the 
        logFolder"""
        super(Librarian, self).__init__(**traitsDict)
        if os.path.isfile(self.logFolder):
            self.logFolder = os.path.split(self.logFolder)[0]
        else:
            logger.debug("found these in %s: %s" %(self.logFolder, os.listdir(self.logFolder) ))

        self.logName = os.path.split(self.logFolder)[1]
        self.logFile = os.path.join(self.logFolder, os.path.split(self.logFolder)[1]+".csv")
        self.axisList.logFile = self.logFile#needs a copy so it can calculate valid values
        self.axisList.masterList = self.axisList._masterList_default()
        self.axisList.masterListWithNone = self.axisList._masterListWithNone_default() 
        if self.xAxis != "":
            self.axisList.xAxis = self.xAxis
        if self.yAxis != "":
            self.axisList.yAxis = self.yAxis
        
        self.eagleOneNote = oneNotePython.eagleLogsOneNote.EagleLogOneNote(notebookName = self.notebookName, sectionName = self.sectionName)
        logPage = self.eagleOneNote.setPage(self.logName)
#        
#        except Exception as e:
#            logger.error("failed to created an EagleOneNote Instance. This could happen for many reasons. E.g. OneNote not installed or most likely, the registry is not correct. See known bug and fix in source code of onenotepython module:%s" % e.message)
        if logPage is not None:#page exists
            self.purposeBlock.textBlock = self.eagleOneNote.getOutlineText("purpose")
            self.resultsBlock.textBlock = self.eagleOneNote.getOutlineText("results")
            self.commentsBlock.textBlock = self.eagleOneNote.getOutlineText("comments")
            xAxis,yAxis,series = self.eagleOneNote.getParametersOutlineValues()
            try:
                self.axisList.xAxis,self.axisList.yAxis,self.axisList.series = xAxis,yAxis,series
            except Exception as e:
                logger.error("error when trying to read analysis parameters: %s" % e.message)
            self.pageExists = True
        else:
            self.pageExists = False
            self.purposeBlock.textBlock = ""
            self.resultsBlock.textBlock = ""
            self.commentsBlock.textBlock = ""
            #could also reset axis list but it isn't really necessary
            
    def _writeToOneNoteButton_fired(self):
        """writes content of librarian to one note page """
        if not self.pageExists:
            self.eagleOneNote.createNewEagleLogPage(self.logName, refresh=True, setCurrent=True)
            self.pageExists = True
        self.eagleOneNote.setOutline("purpose", self.purposeBlock.textBlock,rewrite=False)
        self.eagleOneNote.setOutline("results", self.resultsBlock.textBlock,rewrite=False)
        self.eagleOneNote.setOutline("comments", self.commentsBlock.textBlock,rewrite=False)
        self.eagleOneNote.setDataOutline(self.logName, rewrite=False)
        self.eagleOneNote.setParametersOutline(self.axisList.xAxis, self.axisList.yAxis, self.axisList.series, rewrite=False)
        self.eagleOneNote.currentPage.rewritePage()
        #now to get resizing done well we want to completely repull the XML and data
        #brute force method:
        self.eagleOneNote = oneNotePython.eagleLogsOneNote.EagleLogOneNote(notebookName = self.notebookName, sectionName = self.sectionName)
        logPage = self.eagleOneNote.setPage(self.logName)#this sets current page of eagleOneNote
        self.eagleOneNote.organiseOutlineSizes()
        
        
        
if __name__=="__main__":
    eb = Librarian(logFolder=r"G:\Experiment Humphry\Experiment Control And Software\experimentEagle\plotObjects\testDebugLog")
    eb.configure_traits()
    