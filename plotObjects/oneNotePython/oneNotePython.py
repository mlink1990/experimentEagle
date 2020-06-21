# -*- coding: utf-8 -*-
"""
Created on Wed Mar 09 17:06:01 2016

@author: tharrison

See: https://github.com/varunsrin/one-py

Note you need to delete 1.0 folder from regedit to get it working see above link

https://msdn.microsoft.com/de-de/library/office/gg649853(v=office.14).aspx


Possible Error:

To work around this, run regedit.exe, and navigate to
HKEY_CLASSES_ROOT\TypeLib\{0EA692EE-BB50-4E3C-AEF0-356D91732725}
There should only be one subfolder in this class called 1.1. If you see 1.0 or any other folders, you'll need to delete them. The final hierarchy should look like this:

|- {0EA692EE-BB50-4E3C-AEF0-356D91732725}
|     |- 1.1
|         |-0
|         | |- win32
|         |- FLAGDS
|         |- HELPDIR
Source: Stack Overflow
"""

import onepy
import os
import xml.etree.ElementTree as ET
import pytz
import datetime
import base64
import logging

logger=logging.getLogger("ExperimentEagle.plotObjects.oneNotePython")
ET.register_namespace("one","http://schemas.microsoft.com/office/onenote/2013/onenote")


class NotebookWrapper(object):
    
    def __init__(self, notebookName):
        self.notebookName = notebookName
        self.oneNote = onepy.OneNote()
        try:
            [self.notebook] = [notebook for notebook in self.oneNote.hierarchy if str(notebook)==self.notebookName]
        except ValueError as e:
            logger.error("couldn't unpack notebooks list. Maybe you have multiple notebooks with the selected notebook name? This will cause failure")
            logger.error("Error message: %s"%e.message) 
            logger.error("values of list comprehension = %s " % [notebook for notebook in self.oneNote.hierarchy if str(notebook)==self.notebookName])
            self.notebook = [notebook for notebook in self.oneNote.hierarchy if str(notebook)==self.notebookName][0]#try to just take the first
        self.process = self.oneNote.process
        
        
    def refresh(self):
        """the notebook is static so we need to re pull data if we want to see 
        our updates"""
        self.__init__(self.notebookName)
        
    def getAllNotebookNames(self):
        """returns list of names of all notebooks """
        [str(notebook) for notebook in self.oneNote.hierarchy]

    #sections
    def getSectionIDs(self):
        return [section.id for section in self.notebook]
        
    def getSectionNames(self):
        return [section.name for section in self.notebook]
        
    def getSectionID(self, sectionName):
        return [section.id for section in self.notebook if section.name==sectionName][0]
        
    def getSectionFromName(self, sectionName):
        return [section for section in self.notebook if section.name==sectionName][0]
    
    def getSectionFromID(self,sectionID):
        """given section ID returns section object """
        section = [section for section in self.notebook if section.id==sectionID][0]
        
    def createSection(self, sectionName):
        """creates a section in notebook """
        newSection = os.path.join(self.notebook.path, sectionName+".one")
        self.process.open_hierarchy(newSection,"" ,"", 3)#2 would create section group
        
    #pages
    def getPages(self,section):
        return [page for page in section]
        
    def getPagesfromSectionID(self,sectionID):
        section = self.getSectionFromID(sectionID)
        return self.getPages(section)
    
    def getPagesfromSectionName(self,sectionName):
        section = self.getSectionFromName(sectionName)
        return self.getPages(section)
        
    def getPageFromName(self,section, pageName):
        """returns page in section with given Name """
        if isinstance(section, str):
            section=self.getSectionFromName(section)
        return [page for page in section if page.name==pageName][0]
        
    def createBlankPage(self,sectionID):
        """creates a page in section identifier """
        return(self.process.create_new_page(sectionID, 0))
    
    def createBlankPageFromName(self,sectionName):
        return self.process.create_new_page(self.getSectionID(sectionName))

    def getPageContent(self,page):
        """default is to use page id but if clause also allows you to use page instance """
        if isinstance(page, (str,unicode)):
            return self.process.get_page_content(page,0)
        else:
            return self.process.get_page_content(page.id,0)
            
    def getBinaryPageContent(self,page):
        """gets content of page with binary """
        if isinstance(page, (str,unicode)):
            return self.process.get_page_content(page,1)
        else:
            return self.process.get_page_content(page.id,1)
                
    def updatePageContent(self,pageChangesXMLIn,dateModifiedExpected= pytz.utc.localize(datetime.datetime(year=1899, month=12, day=30))):
        """updates page content
        NOTE THE ORIGINAL ONEPY MODULE HAS A BROKEN DEFAULT DATEMODIFIED.
        to ignore date must use :       pytz.utc.localize(datetime.datetime(year=1899, month=12, day=30))
        see:  https://stackoverflow.com/questions/34904094/how-to-debug-win32com-call-in-python
        """
        self.process.update_page_content(pageChangesXMLIn, dateModifiedExpected)


class PageContent:
    """useful for construction of pages. Specifically for eagle logs but can easily be adapted """
    def __init__(self, rawXMLString, notebookReference):
        self.raw = rawXMLString.encode("utf-8") #required!
        self.root =  ET.fromstring(self.raw)
        
        self.schema = onepy.onmanager.ON15_SCHEMA
        self.title = self.root.find(self.schema+"Title")
        self.outlines = self.root.findall(self.schema+"Outline")
        self.notebook = notebookReference

    def getXMLAsString(self):
        """returns the updated XML as string """
        return ET.tostring(self.root,encoding="utf8", method="xml")
        
    def rewritePage(self):
        self.notebook.updatePageContent(self.getXMLAsString())

    def getTitleText(self):
        """given either a title or outline this will extract the text part """
        return self.root.attrib["name"]#N.B. this can be different to title text it would seem....
        
    def setTitle(self, text, rewrite=False):
        """set the title of page to text.updates attribute and text.if rewrite it 
        writes these cahnges to onenote"""
        self.root.attrib["name"] = text
        titleText = self.title.iter(self.schema+"T").next()#iter searhes through subchildren
#        oe = self.title.find(self.schema+"OE")
#        titleText = oe.find(self.schema+"T")
        titleText.text = text
        if rewrite:
            self.rewritePage()
            
    def getImagesIterator(self, outline):
        return outline.iter(self.schema+"Image")
        
    def addImage(self,outline, fullImagePath,shape, rewrite=True):
        """adds image at fullImagPath to the specified outline """
        with open(fullImagePath, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
        oechildren = outline.find(self.schema+"OEChildren")
        OE = ET.SubElement(oechildren, self.schema+"OE", {"alignment":"left"})
        image = ET.SubElement(OE,self.schema+"Image")
        size = ET.SubElement(image, self.schema+"Size", {"width":str(shape[0]), "height":str(shape[1])})
        data= ET.SubElement(image, self.schema+"Data")
        data.text = encoded_string
        if rewrite:
            self.rewritePage()
            
    def addPageTags(self,tagNames):
        """page tags kit is used by experiment Humphry for sorting and tagging pages. This function writes a tag
        called tagName to a given OneNote page. If it is the first page tag to be created it creates the necessary Tag for the
        symbol image.
        
        page tags have the form (at the top of a oneNote page)
        
        <one:TagDef xmlns:one="http://schemas.microsoft.com/office/onenote/2013/onenote" fontColor="#808083" highlightColor="none" index="0" name="Check" symbol="0" type="3" />
        <one:TagDef xmlns:one="http://schemas.microsoft.com/office/onenote/2013/onenote" fontColor="#808083" highlightColor="none" index="1" name="Calibration" symbol="0" type="2" />
        <one:TagDef xmlns:one="http://schemas.microsoft.com/office/onenote/2013/onenote" fontColor="#808083" highlightColor="none" index="2" name="BEC" symbol="0" type="1" />
        <one:TagDef xmlns:one="http://schemas.microsoft.com/office/onenote/2013/onenote" fontColor="automatic" highlightColor="none" index="3" name="Page Tags" symbol="26" type="23" />
        
        They are children of the page content. On the same level as QuickStyleDef, PageSettings,Outlines
        
        This function takes a list of strings of page tags  and adds them to the page as PageTags. It assumes no page tags already exist which may complicate the code for now.TODO can add some checks and fix this.
        
        """
        
        logger.info("adding page tags")
        print "adding page tags"
        print "initial children"
        print self.root.getchildren()
        numberOfTags = len(tagNames)
        
        pageTagGeneric = ET.fromstring('<one:TagDef xmlns:one="http://schemas.microsoft.com/office/onenote/2013/onenote" fontColor="automatic" highlightColor="none" index="1" name="Page Tags" symbol="26" type="23" />')
        pageTagGeneric.set("type",str(23))
        pageTagGeneric.set("index",str(numberOfTags))
        pageTags = []
        for counter in range(0, numberOfTags):
            newPageTag = ET.fromstring('<one:TagDef xmlns:one="http://schemas.microsoft.com/office/onenote/2013/onenote" fontColor="#808083" highlightColor="none" index="0" name="Check" symbol="0" type="3" />')
            newPageTag.set("index", str(counter))
            newPageTag.set("type",str(numberOfTags-counter))
            newPageTag.set("name",tagNames[counter])
            pageTags.append(newPageTag)
            
        pageTags.append(pageTagGeneric)
        meta = ET.fromstring('<one:Meta xmlns:one="http://schemas.microsoft.com/office/onenote/2013/onenote" content="BEC, DebugPageTag" name="TaggingKit.PageTags" />')
        meta.set("content", ", ".join(tagNames))
        pageTags.append(meta)
        print pageTags
        pageTags.reverse()
        for tag in pageTags:
            self.root.insert(0,tag)
        print "final children"
        print self.root.getchildren()
        
            
            
        
            
    def getOutlineText(self, outline):
        """an outline contains OEChildren. This function returns a list of each OEChild as text """
        oechildren = outline.find(self.schema+"OEChildren").getchildren()#returns list of OE element
        textBlocks = [oe.find(self.schema+"T") for oe in oechildren ]
        return [textBlock.text for textBlock in textBlocks if textBlock is not None ]
        
    def getOutlinePosition(self, outline):
        """returns x,y,z position of outline as floats """
        position = outline.find(self.schema+"Position")
        return float(position.attrib["x"]), float(position.attrib["y"]), float(position.attrib["z"])
        
    def getOutlineSize(self, outline):
        """returns width, height floats of outline """
        size =  outline.find(self.schema+"Size")
        return float(size.attrib["width"]), float(size.attrib["height"])
        
    def setOutlinePosition(self,outline, x,y, z=None, rewrite=True):
        """sets position of outline x and y and optional z """
        position =  outline.find(self.schema+"Position")
        position.attrib["x"] = str(x)
        position.attrib["y"] = str(y)
        if z is not None:
            position.attrib["z"] = str(z)
        if rewrite:
            self.rewritePage()
            
    def setOutlineSize(self,outline, width,height, rewrite=True):
        """sets width and height of outline """
        position =  outline.find(self.schema+"Size")
        position.attrib["width"] = str(width)
        position.attrib["height"] = str(height)
        if rewrite:
            self.rewritePage()
            
        
        
    def getOutlineTextElements(self,outline, cdata=True):
        """returns T elements in outline that contain text """
        oechildren = outline.find(self.schema+"OEChildren").getchildren()#returns list of OE element
        textBlocks = [oe.find(self.schema+"T") for oe in oechildren ]
        return [textBlock for textBlock in textBlocks if (textBlock is not None)]
    
    def setOneNoteText(self, element):
        """given either a title or outline this will extract the text part """
        oe=element.find(self.schema+"OE")
        textBlock = oe.find(self.schema+"T")
        return textBlock.text

    def recursivePrint(self, node, level=0):
        """recursive print through an xml node """
        try:
            print level*"\t"+str([node.tag,node.attrib])+str(node.text)
        except UnicodeEncodeError:
            print level*"\t"+str([node.tag.encode("utf-8"),node.attrib])+str(node.text.encode("utf-8"))
        children = node.getchildren()
        if len(children) == 0:
            return            
        else:
            map(self.recursivePrint, children,[level+1]*len(children))
            
if __name__=="__main__":    
    nbw=NotebookWrapper(u"Humphry's Notebook")
    page=nbw.getPageFromName("Eagle Logs", "2016 09 14 - higgs mode - 910G - 20dB att - repeat line red detuned")
    
    page=nbw.getPageFromName("Eagle Logs","2016 10 07 - page tags test 2")
    content = nbw.getPageContent(page)
    pc = PageContent(content, nbw)
    
    
    
    
