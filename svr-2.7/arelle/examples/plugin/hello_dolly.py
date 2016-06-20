u'''
Hello dolly is a simple "Hello world" to demonstrate how plug-ins
are written for Arelle

(c) Copyright 2012 Mark V Systems Limited, All rights reserved.
'''
from __future__ import print_function
from random import randint


LYRICS =  [u"I said hello, dolly,......well, hello, dolly", \
            u"It's so nice to have you back where you belong ", \
            u"You're lookin' swell, dolly.......i can tell, dolly ", \
            u"You're still glowin'...you're still crowin'...you're still goin' strong ", \
            u"I feel that room swayin'......while the band's playin' ", \
            u"One of your old favourite songs from way back when ", \
            u"So..... take her wrap, fellas.......find her an empty lap, fellas ", \
            u"Dolly'll never go away again" 
            ]

def randomLyric():
    u''' A random lyrics.'''
    return LYRICS[randint(0, len(LYRICS) - 1)]
        
def helloMenuEntender(cntlr, menu):
    menu.add_command(label=u"Hello Dolly", underline=0, command=lambda: helloMenuCommand(cntlr, u"Hello Dolly") )

def helloMenuCommand(cntlr, label):
    hello_dolly = randomLyric();
    cntlr.addToLog(hello_dolly)
    import tkinter
    tkMessageBox.showinfo(label, hello_dolly, parent=cntlr.parent)            

def helloCommandLineOptionExtender(parser):
    parser.add_option(u"--hello_dolly", 
                      action=u"store_true", 
                      dest=u"hello_dolly", 
                      help=_(u'Print a random lyric from "Hello, Dolly"'))

def helloCommandLineUtilityRun(cntlr, options, **kwargs):
    if getattr(options, u"hello_dolly", False):
        hello_dolly = randomLyric();
        try:
            cntlr.addToLog(u"[info] " + hello_dolly)
        except:
            print hello_dolly


__pluginInfo__ = {
    u'name': u'Hello Dolly',
    u'version': u'0.9',
    u'description': u"This is not just a plug-in, it symbolizes the hope and enthusiasm "
					u"of an entire generation summed up in two words sung most famously "
					u"by Louis Armstrong: Hello, Dolly. When activated you will randomly "
					u"see a lyric from Hello, Dolly.",
    u'license': u'Apache-2',
    u'author': u'R\xe9gis D\xce9camps',
    u'copyright': u'(c) Copyright 2012 Mark V Systems Limited, All rights reserved.',
    # classes of mount points (required)
    u'CntlrWinMain.Menu.Tools': helloMenuEntender,
    u'CntlrCmdLine.Options': helloCommandLineOptionExtender,
    u'CntlrCmdLine.Utility.Run': helloCommandLineUtilityRun,
}
