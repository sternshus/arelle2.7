u'''
Created on Feb 19, 2011

Use this module to start Arelle in command line modes

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
import sys, os
from arelle import CntlrCmdLine, CntlrComServer

if u'--COMserver' in sys.argv:
    CntlrComServer.main()
elif __name__.startswith(u'_mod_wsgi_') or os.getenv(u'wsgi.version'):
    application = CntlrCmdLine.wsgiApplication()
elif __name__ == u'__main__':
    CntlrCmdLine.main()