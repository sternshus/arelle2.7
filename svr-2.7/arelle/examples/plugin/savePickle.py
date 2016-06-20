u'''
Save Instance Infoset is an example of a plug-in to both GUI menu and command line/web service
that will save facts decorated with ptv:periodType, ptv:balance, ptv:decimals and ptv:precision (inferred).

(c) Copyright 2012 Mark V Systems Limited, All rights reserved.
'''

def savePickle(cntlr, modelXbrl, pickleFile):
    if modelXbrl.fileSource.isArchive:
        return
    import io, time, pickle
    from arelle import Locale
    startedAt = time.time()

    fh = io.open(pickleFile, u"wb")
    try:
        pickle.dump(modelXbrl, fh)
    except Exception, ex:
        cntlr.addToLog(u"Exception " + unicode(ex))
    fh.close()
    
    cntlr.addToLog(Locale.format_string(cntlr.modelManager.locale, 
                                        _(u"profiled command processing completed in %.2f secs"), 
                                        time.time() - startedAt))

def savePickleMenuEntender(cntlr, menu):
    # Extend menu with an item for the save infoset plugin
    menu.add_command(label=u"Save pickled modelXbrl", 
                     underline=0, 
                     command=lambda: savePickleMenuCommand(cntlr) )

def savePickleMenuCommand(cntlr):
    # save Infoset menu item has been invoked
    from arelle.ModelDocument import Type
    if cntlr.modelManager is None or cntlr.modelManager.modelXbrl is None or cntlr.modelManager.modelXbrl.modelDocument.type != Type.INSTANCE:
        cntlr.addToLog(u"No instance loaded.")
        return

        # get file name into which to save log file while in foreground thread
    pickleFile = cntlr.uiFileDialog(u"save",
            title=_(u"arelle - Save pickle file"),
            initialdir=cntlr.config.setdefault(u"pickleDir",u"."),
            filetypes=[(_(u"Pickle .prl"), u"*.prl")],
            defaultextension=u".prl")
    if not pickleFile:
        return False
    import os
    cntlr.config[u"pickleDir"] = os.path.dirname(pickleFile)
    cntlr.saveConfig()

    try: 
        savePickle(cntlr, cntlr.modelManager.modelXbrl, pickleFile)
    except Exception, ex:
        modelXbrl = cntlr.modelManager.modelXbrl
        modelXbrl.error(u"exception",
                        _(u"Save pickle exception: %(error)s"), error=ex,
                        modelXbrl=modelXbrl,
                        exc_info=True)

def savePickleCommandLineOptionExtender(parser):
    # extend command line options with a save DTS option
    parser.add_option(u"--save-pickle", 
                      action=u"store", 
                      dest=u"pickleFile", 
                      help=_(u"Save pickle of object model in specified file, or to send testcase infoset out files to out directory specify 'generateOutFiles'."))

def savePickleCommandLineXbrlLoaded(cntlr, options, modelXbrl):
    # extend XBRL-loaded run processing for this option
    from arelle.ModelDocument import Type
    if getattr(options, u"instanceInfosetFile", None) and options.infosetFile == u"generateOutFiles" and modelXbrl.modelDocument.type in (Type.TESTCASESINDEX, Type.TESTCASE):
        cntlr.modelManager.generateInfosetOutFiles = True

def savePickleCommandLineXbrlRun(cntlr, options, modelXbrl):
    # extend XBRL-loaded run processing for this option
    if getattr(options, u"pickleFile", None):
        if cntlr.modelManager is None or cntlr.modelManager.modelXbrl is None:
            cntlr.addToLog(u"No taxonomy loaded.")
            return
        savePickle(cntlr, cntlr.modelManager.modelXbrl, options.pickleFile)
        
__pluginInfo__ = {
    u'name': u'Save (Pickle) Object Model',
    u'version': u'0.9',
    u'description': u"This plug-in pickels the running object model.  ",
    u'license': u'Apache-2',
    u'author': u'Mark V Systems Limited',
    u'copyright': u'(c) Copyright 2012 Mark V Systems Limited, All rights reserved.',
    # classes of mount points (required)
    u'CntlrWinMain.Menu.Tools': savePickleMenuEntender,
    u'CntlrCmdLine.Options': savePickleCommandLineOptionExtender,
    u'CntlrCmdLine.Xbrl.Loaded': savePickleCommandLineXbrlLoaded,
    u'CntlrCmdLine.Xbrl.Run': savePickleCommandLineXbrlRun,
}
