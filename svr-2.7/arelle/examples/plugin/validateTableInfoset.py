u'''
This is an example of a plug-in to both GUI menu and command line/web service
that will provide an option to replace behavior of table linkbase validation to 
generate vs diff table linkbase infoset files.

(c) Copyright 2012 Mark V Systems Limited, All rights reserved.
'''

def validateTableInfosetMenuEntender(cntlr, validateMenu):
    # Extend menu with an item for the save infoset plugin
    cntlr.modelManager.generateTableInfoset = cntlr.config.setdefault(u"generateTableInfoset",False)
    from tkinter import BooleanVar
    generateTableInfoset = BooleanVar(value=cntlr.modelManager.generateTableInfoset)
    def setTableInfosetOption(*args):
        cntlr.config[u"generateTableInfoset"] = cntlr.modelManager.generateTableInfoset = generateTableInfoset.get()
    generateTableInfoset.trace(u"w", setTableInfosetOption)
    validateMenu.add_checkbutton(label=_(u"Generate table infosets (instead of diffing them)"), 
                                 underline=0, 
                                 variable=generateTableInfoset, onvalue=True, offvalue=False)

def validateTableInfosetCommandLineOptionExtender(parser):
    # extend command line options with a save DTS option
    parser.add_option(u"--generate-table-infoset", 
                      action=u"store_true", 
                      dest=u"generateTableInfoset", 
                      help=_(u"Generate table instance infosets (instead of diffing them)."))

def validateTableInfosetCommandLineXbrlLoaded(cntlr, options, modelXbrl):
    cntlr.modelManager.generateTableInfoset = getattr(options, u"generateTableInfoset", False)

def validateTableInfoset(modelXbrl, resultTableUri):
    diffToFile = not getattr(modelXbrl.modelManager, u'generateTableInfoset', False)
    from arelle import ViewFileRenderedGrid
    ViewFileRenderedGrid.viewRenderedGrid(modelXbrl, 
                                          resultTableUri, 
                                          diffToFile=diffToFile)  # false to save infoset files
    return True # blocks standard behavior in validate.py

__pluginInfo__ = {
    u'name': u'Validate Table Infoset (Optional behavior)',
    u'version': u'0.9',
    u'description': u"This plug-in adds a feature modify batch validation of table linkbase to save, versus diff, infoset files.  ",
    u'license': u'Apache-2',
    u'author': u'Mark V Systems Limited',
    u'copyright': u'(c) Copyright 2012 Mark V Systems Limited, All rights reserved.',
    # classes of mount points (required)
    u'CntlrWinMain.Menu.Validation': validateTableInfosetMenuEntender,
    u'CntlrCmdLine.Options': validateTableInfosetCommandLineOptionExtender,
    u'CntlrCmdLine.Xbrl.Loaded': validateTableInfosetCommandLineXbrlLoaded,
    u'Validate.TableInfoset': validateTableInfoset,
}
