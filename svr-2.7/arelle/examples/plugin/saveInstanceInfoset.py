u'''
Save Instance Infoset is an example of a plug-in to both GUI menu and command line/web service
that will save facts decorated with ptv:periodType, ptv:balance, ptv:decimals and ptv:precision (inferred).

(c) Copyright 2012 Mark V Systems Limited, All rights reserved.
'''
from io import open

def generateInstanceInfoset(dts, instanceInfosetFile):
    if dts.fileSource.isArchive:
        return
    import os, io
    from arelle import XmlUtil, XbrlConst
    from arelle.ValidateXbrlCalcs import inferredPrecision, inferredDecimals            
    
    XmlUtil.setXmlns(dts.modelDocument, u"ptv", u"http://www.xbrl.org/2003/ptv")
    
    numFacts = 0
    
    for fact in dts.facts:
        try:
            if fact.concept.periodType:
                fact.set(u"{http://www.xbrl.org/2003/ptv}periodType", fact.concept.periodType)
            if fact.concept.balance:
                fact.set(u"{http://www.xbrl.org/2003/ptv}balance", fact.concept.balance)
            if fact.isNumeric and not fact.isNil:
                fact.set(u"{http://www.xbrl.org/2003/ptv}decimals", unicode(inferredDecimals(fact)))
                fact.set(u"{http://www.xbrl.org/2003/ptv}precision", unicode(inferredPrecision(fact)))
            numFacts += 1
        except Exception, err:
            dts.error(u"saveInfoset.exception",
                     _(u"Facts exception %(fact)s %(value)s %(error)s."),
                     modelObject=fact, fact=fact.qname, value=fact.effectiveValue, error = err)

    fh = open(instanceInfosetFile, u"w", encoding=u"utf-8")
    XmlUtil.writexml(fh, dts.modelDocument.xmlDocument, encoding=u"utf-8")
    fh.close()
    
    dts.info(u"info:saveInstanceInfoset",
             _(u"Instance infoset of %(entryFile)s has %(numberOfFacts)s facts in infoset file %(infosetOutputFile)s."),
             modelObject=dts,
             entryFile=dts.uri, numberOfFacts=numFacts, infosetOutputFile=instanceInfosetFile)

def saveInstanceInfosetMenuEntender(cntlr, menu):
    # Extend menu with an item for the save infoset plugin
    menu.add_command(label=u"Save infoset", 
                     underline=0, 
                     command=lambda: saveInstanceInfosetMenuCommand(cntlr) )

def saveInstanceInfosetMenuCommand(cntlr):
    # save Infoset menu item has been invoked
    from arelle.ModelDocument import Type
    if cntlr.modelManager is None or cntlr.modelManager.modelXbrl is None or cntlr.modelManager.modelXbrl.modelDocument.type != Type.INSTANCE:
        cntlr.addToLog(u"No instance loaded.")
        return

        # get file name into which to save log file while in foreground thread
    instanceInfosetFile = cntlr.uiFileDialog(u"save",
            title=_(u"arelle - Save instance infoset file"),
            initialdir=cntlr.config.setdefault(u"infosetFileDir",u"."),
            filetypes=[(_(u"Infoset file .xml"), u"*.xml")],
            defaultextension=u".xml")
    if not instanceInfosetFile:
        return False
    import os
    cntlr.config[u"infosetFileDir"] = os.path.dirname(instanceInfosetFile)
    cntlr.saveConfig()

    try: 
        generateInstanceInfoset(cntlr.modelManager.modelXbrl, instanceInfosetFile)
    except Exception, ex:
        dts = cntlr.modelManager.modelXbrl
        dts.error(u"exception",
            _(u"Instance infoset generation exception: %(error)s"), error=ex,
            modelXbrl=dts,
            exc_info=True)

def saveInstanceInfosetCommandLineOptionExtender(parser):
    # extend command line options with a save DTS option
    parser.add_option(u"--save-instance-infoset", 
                      action=u"store", 
                      dest=u"instanceInfosetFile", 
                      help=_(u"Save instance infoset in specified file, or to send testcase infoset out files to out directory specify 'generateOutFiles'."))

def saveInstanceInfosetCommandLineXbrlLoaded(cntlr, options, modelXbrl):
    # extend XBRL-loaded run processing for this option
    from arelle.ModelDocument import Type
    if getattr(options, u"instanceInfosetFile", None) and options.infosetFile == u"generateOutFiles" and modelXbrl.modelDocument.type in (Type.TESTCASESINDEX, Type.TESTCASE):
        cntlr.modelManager.generateInfosetOutFiles = True

def saveInstanceInfosetCommandLineXbrlRun(cntlr, options, modelXbrl):
    # extend XBRL-loaded run processing for this option
    if getattr(options, u"instanceInfosetFile", None) and options.instanceInfosetFile != u"generateOutFiles":
        if cntlr.modelManager is None or cntlr.modelManager.modelXbrl is None:
            cntlr.addToLog(u"No taxonomy loaded.")
            return
        generateInstanceInfoset(cntlr.modelManager.modelXbrl, options.instanceInfosetFile)
        
def validateInstanceInfoset(dts, instanceInfosetFile):
    if getattr(dts.modelManager, u'generateInfosetOutFiles', False):
        generateInstanceInfoset(dts, 
                        # normalize file to instance
                        dts.modelManager.cntlr.webCache.normalizeUrl(instanceInfosetFile, dts.uri))


__pluginInfo__ = {
    u'name': u'Save Instance Infoset (PTV)',
    u'version': u'0.9',
    u'description': u"This plug-in adds a feature to output an instance \"ptv\" infoset.  "
                    u"(Does not offset infoset hrefs and schemaLocations for directory offset from DTS.) "
                    u"The ptv infoset is the source instance with facts having ptv:periodType, ptv:balance (where applicable), ptv:decimals and ptv:precision (inferred).  ",
    u'license': u'Apache-2',
    u'author': u'Mark V Systems Limited',
    u'copyright': u'(c) Copyright 2012 Mark V Systems Limited, All rights reserved.',
    # classes of mount points (required)
    u'CntlrWinMain.Menu.Tools': saveInstanceInfosetMenuEntender,
    u'CntlrCmdLine.Options': saveInstanceInfosetCommandLineOptionExtender,
    u'CntlrCmdLine.Xbrl.Loaded': saveInstanceInfosetCommandLineXbrlLoaded,
    u'CntlrCmdLine.Xbrl.Run': saveInstanceInfosetCommandLineXbrlRun,
    u'Validate.Infoset': validateInstanceInfoset,
}
