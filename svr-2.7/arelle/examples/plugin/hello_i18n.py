u'''
Hello dolly is a simple "Hello world" to demonstrate how plug-ins
are written for Arelle

(c) Copyright 2012 Mark V Systems Limited, All rights reserved.
'''
        
def menuEntender(cntlr, menu):
    menu.add_command(label=u"Hello i18n", underline=0, command=lambda: menuCommand(cntlr) )

def menuCommand(cntlr):
    i10L_world = _(u"Hello World");
    cntlr.addToLog(i10L_world)
    import tkinter
    tkMessageBox.showinfo(_(u"Prints 'Hello World'"), i10L_world, parent=cntlr.parent)            

u'''
   Do not use _( ) in pluginInfo itself (it is applied later, after loading
'''
__pluginInfo__ = {
    u'name': u'Hello i18n',
    u'version': u'0.9',
    u'description': u'''Minimal plug-in that demonstrates i18n internationalization by localized gettext.''',
    u'localeURL': u"locale",
    u'localeDomain': u'hello_i18n',
    u'license': u'Apache-2',
    u'author': u'R\u00e9gis D\u00e9camps',
    u'copyright': u'(c) Copyright 2012 Mark V Systems Limited, All rights reserved.',
    # classes of mount points (required)
    u'CntlrWinMain.Menu.Tools': menuEntender
}
