# -*- coding: utf-8 -*-
"""
Created on Tue Nov 01 20:13:34 2016

@author: tharrison

matplotlibify converts eagle log file plots into a python script that
generates a matplotlib plot ready for Tim's thesis!

"""

import os
import traits.api as traits
import traitsui.api as traitsui
import logFilePlot
import logFilePlots
import logging

logger=logging.getLogger("ExperimentEagle.Matplotlibify")

class Matplotlibify(traits.HasTraits):
    
    logFilePlotReference = traits.Instance(logFilePlot.LogFilePlot)#gives access to most of the required attributes
    logFilePlotsReference = traits.Instance(logFilePlots.LogFilePlots)#refernce to logFilePlots object
    xAxisLabel = traits.String("")
    yAxisLabel = traits.String("")
    xAxisLabel2 = traits.String("")#used if in dual plot mode
    yAxisLabel2 = traits.String("")
    legendReplacements = traits.Dict(key_trait=traits.String, value_trait=traits.String)
    #xLim = traits.Tuple()
    replacementStrings = {}
    setXLimitsBool = traits.Bool(False)
    setYLimitsBool = traits.Bool(False)
    
    xMin = traits.Float
    xMax = traits.Float
    yMin = traits.Float
    yMax = traits.Float
    
    matplotlibifyMode = traits.Enum("default","dual plot")
    logFilePlot1 = traits.Any()#will be mapped traits of name of log file plot to lfp reference
    logFilePlot2 = traits.Any()#will be mapped traits of name of log file plot to lfp reference
    
    generatePlotScriptButton = traits.Button("generate plot")
    showPlotButton = traits.Button("show")
    templatesFolder = os.path.join("C:","Users","tharrison","Google Drive","Thesis","python scripts","matplotlibify")
    templateFile = traits.File(os.path.join(templatesFolder,"matplotlibifyDefaultTemplate.py"))    
    generatedScriptLocation = traits.File(os.path.join("C:","Users","tharrison","Google Drive","Thesis","python scripts","matplotlibify", "debug.py"))
    
    secondPlotGroup = traitsui.VGroup(traitsui.Item("matplotlibifyMode", label="add second plot"),
                                      traitsui.HGroup(traitsui.Item("logFilePlot1", visible_when="matplotlibifyMode=='dual plot'"), 
                                      traitsui.Item("logFilePlot2", visible_when="matplotlibifyMode=='dual plot'") ))
                                      
    labelsGroup = traitsui.VGroup(traitsui.HGroup(traitsui.Item("xAxisLabel"),
                                                  traitsui.Item("yAxisLabel")),
                                  traitsui.HGroup(traitsui.Item("xAxisLabel2", label="X axis label (2nd)", visible_when="matplotlibifyMode=='dual plot'"),
                                                  traitsui.Item("yAxisLabel2", label="Y axis label (2nd)", visible_when="matplotlibifyMode=='dual plot'")))
    
    limitsGroup = traitsui.VGroup(traitsui.Item("setXLimitsBool", label="set x limits?"),traitsui.Item("setYLimitsBool", label="set x limits?"),
                                  traitsui.HGroup(traitsui.Item("xMin", label="x min", visible_when="setXLimitsBool" ),traitsui.Item("xMax", label="x max", visible_when="setXLimitsBool"),
                                                  traitsui.Item("yMin", label="y min", visible_when="setYLimitsBool"),traitsui.Item("yMax", label="y max", visible_when="setYLimitsBool")))
    
    traits_view = traitsui.View( secondPlotGroup,
                                 labelsGroup,
                                 limitsGroup,
                                 traitsui.Item("legendReplacements"), 
                                 traitsui.Item("templateFile"),
                                 traitsui.Item("generatedScriptLocation"),
                                 traitsui.Item('generatePlotScriptButton'),traitsui.Item('showPlotButton'), resizable=True)
                                
    def __init__(self, **traitsDict):
        super(Matplotlibify, self).__init__(**traitsDict)
        self.generateReplacementStrings()
        self.add_trait("logFilePlot1",traits.Trait(self.logFilePlotReference.logFilePlotsTabName,{lfp.logFilePlotsTabName:lfp for lfp in self.logFilePlotsReference.lfps}))
        self.add_trait("logFilePlot2",traits.Trait(self.logFilePlotReference.logFilePlotsTabName,{lfp.logFilePlotsTabName:lfp for lfp in self.logFilePlotsReference.lfps}))
        
    def generateReplacementStrings(self):
        self.replacementStrings = {}
        
        if self.matplotlibifyMode == 'default':
            specific = self.getReplacementStringsFor(self.logFilePlotReference)
            generic = self.getGlobalReplacementStrings()
            self.replacementStrings.update(specific)
            self.replacementStrings.update(generic)

        elif self.matplotlibifyMode == 'dual plot':
            specific1 = self.getReplacementStringsFor(self.logFilePlot1_, identifier = "lfp1.")
            specific2 = self.getReplacementStringsFor(self.logFilePlot2_, identifier = "lfp2.")
            generic = self.getGlobalReplacementStrings()
            self.replacementStrings.update(specific1)
            self.replacementStrings.update(specific2)
            self.replacementStrings.update(generic)
        
        for key in self.replacementStrings.keys():#wrap strings in double quotes
            logger.info("%s = %s" % (self.replacementStrings[key],type(self.replacementStrings[key])))
            if isinstance(self.replacementStrings[key],(str,unicode)):
                self.replacementStrings[key] = unicode(self.wrapInQuotes(self.replacementStrings[key]))

    def getReplacementStringsFor(self,logFilePlot, identifier = ""):
        """generates the replacement strings that are specific to a log file plot.
        indentifier is used inside key to make it unique to that lfp and should have the format
        {{lfp.mode}}. Identifier must include the . character"""
        return {'{{%smode}}'%identifier:logFilePlot.mode,
        '{{%slogFile}}'%identifier:logFilePlot.logFile,'{{%sxAxis}}'%identifier:logFilePlot.xAxis,'{{%syAxis}}'%identifier:logFilePlot.yAxis,
        '{{%saggregateAxis}}'%identifier:logFilePlot.aggregateAxis,'{{%sseries}}'%identifier:logFilePlot.series,'{{%sfiterYs}}'%identifier:logFilePlot.filterYs,
        '{{%sfilterMinYs}}'%identifier:logFilePlot.filterMinYs,'{{%sfilterMaxYs}}'%identifier:logFilePlot.filterMaxYs,'{{%sfilterXs}}'%identifier:logFilePlot.filterXs,
        '{{%sfilterMinXs}}'%identifier:logFilePlot.filterMinXs,'{{%sfilterMaxXs}}'%identifier:logFilePlot.filterMaxXs,'{{%sfilterNaN}}'%identifier:logFilePlot.filterNaN,
        '{{%sfilterSpecific}}'%identifier:logFilePlot.filterSpecific,'{{%sfilterSpecificString}}'%identifier:logFilePlot.filterSpecificString,
        '{{%sxLogScale}}'%identifier:logFilePlot.xLogScale,'{{%syLogScale}}'%identifier:logFilePlot.yLogScale,'{{%sinterpretAsTimeAxis}}'%identifier:logFilePlot.interpretAsTimeAxis} 

    def getGlobalReplacementStrings(self, identifier=""):
        """generates the replacement strings that are specific to a log file plot """
        return {'{{%sxAxisLabel}}'%identifier:self.xAxisLabel , '{{%syAxisLabel}}'%identifier:self.yAxisLabel,
                '{{%sxAxisLabel2}}'%identifier:self.xAxisLabel2 , '{{%syAxisLabel2}}'%identifier:self.yAxisLabel2,
        '{{%slegendReplacements}}'%identifier:self.legendReplacements,
        '{{%ssetXLimitsBool}}'%identifier:self.setXLimitsBool,'{{%ssetYLimitsBool}}'%identifier:self.setYLimitsBool,
        '{{%sxlimits}}'%identifier:(self.xMin,self.xMax),'{{%sylimits}}'%identifier:(self.yMin,self.yMax), 
        '{{%smatplotlibifyMode}}'%identifier:self.matplotlibifyMode}
        
    def wrapInQuotes(self, string):
        return '"%s"' % string
    
    def _xAxisLabel_default(self):
        return self.logFilePlotReference.xAxis
    
    def _yAxisLabel_default(self):
        return self.logFilePlotReference.yAxis
        
    def _legendReplacements_default(self):
        return {_:_ for _ in self.logFilePlotReference.parseSeries()}
        
    def _xMin_default(self):
        return self.logFilePlotReference.firstPlot.x_axis.mapper.range.low
    def _xMax_default(self):
        return self.logFilePlotReference.firstPlot.x_axis.mapper.range.high
    def _yMin_default(self):
        return self.logFilePlotReference.firstPlot.y_axis.mapper.range.low    
    def _yMax_default(self):
        return self.logFilePlotReference.firstPlot.y_axis.mapper.range.high    
        
    def _generatedScriptLocation_default(self):
        root = os.path.join("C:","Users","tharrison","Google Drive","Thesis","python scripts","matplotlibify")
        head,tail = os.path.split(self.logFilePlotReference.logFile)
        matplotlibifyName = os.path.splitext(tail)[0]+"-%s-vs-%s" % (self._yAxisLabel_default() ,self._xAxisLabel_default() )
        baseName = os.path.join(root, matplotlibifyName )
        filename = baseName+".py"
        c=0
        while os.path.exists(baseName+".py"):
            filename=baseName+"-%s.py" % c
        return filename
    
    def replace_all(self,text, replacementDictionary):
        for placeholder, new in replacementDictionary.iteritems():
            text = text.replace(placeholder, str(new))
        return text
        
    def _generatePlotScriptButton_fired(self):
        logger.info("attempting to generate matplotlib script...")
        self.generateReplacementStrings()
        with open(self.templateFile, "rb") as template:
            text = self.replace_all(template.read(), self.replacementStrings)
        with open(self.generatedScriptLocation,"wb") as output:
            output.write(text)
        logger.info("succesfully generated matplotlib script at location %s "% self.generatedScriptLocation)
            
    def _showPlotButton_fired(self):
        logger.info("attempting to show matplotlib plot...")
        self.generateReplacementStrings()
        with open(self.templateFile, "rb") as template:
            text = self.replace_all(template.read(), self.replacementStrings)
        ns = {}
        exec text in ns
        logger.info("exec completed succesfully...")
        
    def _matplotlibifyMode_changed(self):
        """change default template depending on whether or not this is a double axis plot """
        if self.matplotlibifyMode == "default":
            self.templateFile = os.path.join(self.templatesFolder,"matplotlibifyDefaultTemplate.py")
        elif self.matplotlibifyMode == "dual plot":
            self.templateFile = os.path.join(self.templatesFolder,"matplotlibifyDualPlotTemplate.py")
            self.xAxisLabel2 = self.logFilePlot2.xAxis
            self.yAxisLabel2 = self.logFilePlot2.yAxis
            
            