u'''
Crash test is a plug in to cause an uncaught exception to test its recover

(c) Copyright 2012 Mark V Systems Limited, All rights reserved.
'''
def crashMenuEntender(cntlr, menu):
    menu.add_command(label=u"Crash now!!!", underline=0, command=lambda: crashMenuCommand(cntlr) )

def crashMenuCommand(cntlr):
    foo = 25
    foo /= 0

def crashCommandLineOptionExtender(parser):
    parser.add_option(u"--crash-test", 
                      action=u"store_true", 
                      dest=u"crashTest", 
                      help=_(u'Test what happens with an exception'))

def crashCommandLineXbrlRun(cntlr, options, modelXbrl):
    if getattr(options, u"crashTest", False):
        foo = 25
        foo /= 0


__pluginInfo__ = {
    u'name': u'Crash Test',
    u'version': u'0.9',
    u'description': u"Used to test that uncaught exceptions report their cause to the Arelle user.",
    u'license': u'Apache-2',
    u'author': u'Mark V Systems Limited',
    u'copyright': u'(c) Copyright 2012 Mark V Systems Limited, All rights reserved.',
    # classes of mount points (required)
    u'CntlrWinMain.Menu.Tools': crashMenuEntender,
    u'CntlrCmdLine.Options': crashCommandLineOptionExtender,
    u'CntlrCmdLine.Xbrl.Run': crashCommandLineXbrlRun,
}
