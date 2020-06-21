# -*- coding: utf-8 -*-
"""
Created on Wed Apr 20 12:41:33 2016

@author: tharrison


defines the pop up dialog that is used when user wants to save a reference image
includes features to write to one note etc.
"""
import traits.api as traits
import traitsui.api as traitsui
import os.path
import logging
import time
import scipy.misc

logger=logging.getLogger("ExperimentEagle.plotObjects.imageReferenceDialog")


class ImageReferenceDialogHandler(traitsui.Handler):
    view=traits.Any
    ui = traits.Any    
    
    def init(self, info):
        self.view = info.object
        self.ui = info.ui
        
    def object_saveButton_changed(self,info):
        if not info.initialized:
            logger.warning("image reference dialog not yet initialised")
            return
        logger.info("attempting to save reference")
        self.view.saveReference()
        info.ui.dispose()
        


class ImageReferenceDialog(traits.HasTraits):
    
    referenceName = traits.String(desc="name of reference, should be short as it is used in filenames etc. date will be added automatically")
    referenceDescription = traits.String(desc="text block to describe reference image in detail")
    saveToOneNote = traits.Bool(True, desc= "if True, then when user clicks save it will attempt to write details to a page in OneNote")
    logReferenceDirectory = traits.Directory(os.path.join("\\\ursa", "AQOGroupFolder","Experiment Humphry","Data","eagleReferences"), desc="directory into which references are saved")
    referenceFolder = None
    currentImageArray = None
    currentPixmap = None
    saveButton = traits.Button("Save")
    notebookName = traits.String("Humphry's Notebook")
    sectionName = traits.String("Eagle References")    
    
    mainGroup = traitsui.Group(traitsui.Item("referenceName", label = "Reference Name"),
                   traitsui.Item("referenceDescription",label="referenceDescription", style="custom"),
                    traitsui.Item("saveToOneNote", label="Save to OneNote?"),
                    traitsui.Item("saveButton"))
    traits_view = traitsui.View(mainGroup, title="Save Image Reference", resizable = True, handler =ImageReferenceDialogHandler() )
    
    def __init__(self,currentImageArray,currentPixmap,sequenceXML, extraDetails={}, **traitsDict):
        """construct an ImageReferenceDialog object """
        super(ImageReferenceDialog, self).__init__(**traitsDict)
        self.referenceName = ""
        self.referenceFolder = None
        self.currentImageArray = currentImageArray
        self.currentPixmap = currentPixmap
        self.sequenceXML = sequenceXML
        self.extraDetails=extraDetails
        self.referenceDescription = self.generateExtraDetailsText(self.extraDetails)

            
    def createReferenceDirectory(self):
        """creates a new reference folder. does nothing if reference name is not defined
        or if name already exists"""
        if self.referenceName=="":
            logger.warning("no log file defined. Will not log")
            return
        #generate folders if they don't exist
        todayString = time.strftime("%Y-%m-%d ",time.gmtime(time.time()))
        self.referenceFolder = os.path.join(self.logReferenceDirectory,todayString+self.referenceName)
        if not os.path.isdir(self.referenceFolder):
            logger.info("creating a new reference folder %s" % self.referenceFolder)
            os.mkdir(self.referenceFolder)

    def generateExtraDetailsText(self,extraDetails):
        """produced a formatted block of text from dictionary """
        preamble = "\nAutomated Extra Details:\n\n"
        stringList = [str(key)+" --> "+str(value) for key,value in extraDetails.iteritems() ]
        return preamble+"\n".join(stringList)
        
 
    def saveReferenceTextToFile(self):
        if self.referenceFolder is None or self.referenceName == "":
            logger.warning("cannot save reference to textfile as no reference Folder is defined")
            return      
        textFile = os.path.join(self.referenceFolder,"comments.txt")
        with open(textFile, "a+") as commentsFile:
            commentsFile.write(self.referenceDescription)
        return textFile
        
    def createOneNotePage(self,paths):
        """use OneNote module to make a pretty one Note page """
        import oneNotePython
        import oneNotePython.eagleReferencesOneNote
        #get name of onenote page to be created
        todayString = time.strftime("%Y-%m-%d ",time.gmtime(time.time()))
        referenceName = todayString+self.referenceName
        #create page
        eagleRefOneNote = oneNotePython.eagleReferencesOneNote.EagleReferenceOneNote(notebookName = self.notebookName, sectionName = self.sectionName)
        eagleRefOneNote.createNewEagleReferencePage(referenceName)
        #add description text
        eagleRefOneNote.setOutline("description", self.referenceDescription, rewrite=False)
        #add images and links
        eagleRefOneNote.addRawImage(paths["rawImage"], self.currentImageArray.shape, rewrite = False)# TODO or is shape in array in the wrong order?????!
        eagleRefOneNote.addScreenshot(paths["screenshot"], (self.currentPixmap.width(), self.currentPixmap.height()), rewrite=False)
        eagleRefOneNote.setDataOutline(referenceName,self.referenceFolder, 
                                       paths["rawImage"],paths["screenshot"],paths["sequenceName"],paths["comments"], rewrite=False)
       #write data to onenote
        eagleRefOneNote.currentPage.rewritePage()
        #now to get resizing done well we want to completely repull the XML and data
        #brute force method:
        eagleRefOneNote = oneNotePython.eagleReferencesOneNote.EagleReferenceOneNote(notebookName = self.notebookName, sectionName = self.sectionName)
        page = eagleRefOneNote.setPage(referenceName)#this sets current page of eagleOneNote
        eagleRefOneNote.organiseOutlineSizes()
    
    def saveImageAndScreenshot(self):
        """pixmap of eagle screen and name of image file are passed to ImageReferenceFDialog on creation. This function 
        saves them
        returns imageName and screenshotName        
        """
        imageName = os.path.join(self.referenceFolder, self.referenceName+" raw image.png")
        scipy.misc.imsave(imageName, self.currentImageArray)
        screenshotName = os.path.join(self.referenceFolder, self.referenceName+" screenshot.png")
        self.currentPixmap.save(screenshotName,"png")
        return imageName, screenshotName
        
    def saveXML(self):
        """save a copy of the XML to the reference folder"""
        if self.sequenceXML is None:
            logger.warning("sequence XML was none. Not saving sequence")
            return ""
        todayString = time.strftime("%Y-%m-%d ",time.gmtime(time.time()))
        referenceName = todayString+self.referenceName
        sequenceName = os.path.join(self.referenceFolder, referenceName+".ctr")
        sequenceNameBackup = os.path.join(self.referenceFolder, referenceName+"-BACKUP of Original.xml")
        self.sequenceXML.write(sequenceName)
        self.sequenceXML.write(sequenceNameBackup)
        return sequenceName
        
    def saveReference(self):
        """main function called by the imageReferenceDialog that performs the save"""
        self.createReferenceDirectory()
        commentsName = self.saveReferenceTextToFile()
        imageName, screenshotName = self.saveImageAndScreenshot()
        sequenceName = self.saveXML()
        if self.saveToOneNote:
            paths = {"rawImage":imageName, "screenshot":screenshotName, "comments":commentsName,"sequenceName":sequenceName}
            self.createOneNotePage(paths)
    
if __name__=="__main__":
    ird = ImageReferenceDialog()
    ird.configure_traits()