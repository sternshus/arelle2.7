u'''
Created on May 14,2012

Use this module to start Arelle in py.test modes

@author: Mark V Systems Limited
(c) Copyright 2012 Mark V Systems Limited, All rights reserved.

This module runs the conformance tests to validate that Arelle is
working properly.  It needs to be run through the package pytest which
can be installed via pip.

$ pip install pytest
  -or-
c:\python32\scripts> easy_install -U pytest

$ py.test test_conformance.py

It can take an optional parameter --tests to specify a .ini file for
loading additional test suites.

$ py.test --tests=~/Desktop/custom_tests.ini

c:arelleSrcTopDirectory> \python32\scripts\py.test 

The default test suites are specified in test_conformance.ini .

In order to use SVN tests, you will need an XII user name and password (in [DEFAULT] section of ini file)

To get a standard xml file out of the test run, add --junittests=foo.xml, e.g.:

c:arelleSrcTopDirectory> \python32\scripts\py.test --tests=myIniWithPassword.ini -junittests=foo.xml
 
'''

try:
    import pytest
except ImportError:
    print u'Please install pytest\neasy_install -U pytest'
    exit()
    
import os, ConfigParser, logging
from collections import namedtuple
from arelle.CntlrCmdLine import parseAndRun
from arelle import ModelDocument
            
# clean out non-ansi characters in log
class TestLogHandler(logging.Handler):        
    def __init__(self):
        super(TestLogHandler, self).__init__()
        self.setFormatter(TestLogFormatter())
        
    def emit(self, logRecord):
        print self.format(logRecord)
                
class TestLogFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        super(TestLogFormatter, self).__init__(fmt, datefmt)
        
    def format(self, record):
        formattedMessage = super(TestLogFormatter, self).format(record)
        return u''.join(c if ord(c) < 128 else u'*' for c in formattedMessage)

logging.basicConfig(level=logging.DEBUG)
testLogHandler = TestLogHandler()

def test(section, testcase, variation, name, status, expected, actual):
    assert status == u"pass"

# assert status == "pass", ("[%s] %s:%s %s (%s != %s)" % (section, testcase, variation, name, expected, actual))

# Pytest test parameter generator
def pytest_generate_tests(metafunc):
    print u"gen tests" # ?? print does not come out to console or log, want to show progress
    config = ConfigParser.ConfigParser(allow_no_value=True) # allow no value
    if not os.path.exists(metafunc.config.option.tests):
        raise IOError(u'--test file does not exist: %s' %
                      metafunc.config.option.tests)
    config.read(metafunc.config.option.tests)
    for i, section in enumerate(config.sections()):
        # don't close, so we can inspect results below; log to std err
        arelleRunArgs = [u'--keepOpen', u'--logFile', u'logToStdErr']  
        for optionName, optionValue in config.items(section):
            if not optionName.startswith(u'_'):
                arelleRunArgs.append(u'--' + optionName)
                if optionValue:
                    arelleRunArgs.append(optionValue)
        print u"section {0} run arguments {1}".format(section, u" ".join(arelleRunArgs))
        cntlr_run = runTest(section, arelleRunArgs)
        for variation in cntlr_run:
            metafunc.addcall(funcargs=variation,
                             id=u"[{0}] {1}: {2}".format(variation[u"section"],
                                                       variation[u"testcase"].rpartition(u".")[0],
                                                       variation[u"variation"]))
        # if i == 1: break # stop on first test  -- uncomment to do just counted number of tests
    
def runTest(section, args):
    print u"run tests" # ?? print does not come out to console or log, want to show progress
    
    cntlr = parseAndRun(args) # log to print (only failed assertions are captured)
        
    outcomes = []
    if u'--validate' in args:
        modelDocument = cntlr.modelManager.modelXbrl.modelDocument

        if modelDocument is not None:
            if modelDocument.type in (ModelDocument.Type.TESTCASESINDEX,
                                      ModelDocument.Type.REGISTRY):
                index = os.path.basename(modelDocument.uri)
                for tc in sorted(modelDocument.referencesDocument.keys(), key=lambda doc: doc.uri):
                    test_case = os.path.basename(tc.uri)
                    if hasattr(tc, u"testcaseVariations"):
                        for mv in tc.testcaseVariations:
                            outcomes.append({u'section': section,
                                             u'testcase': test_case,
                                             u'variation': unicode(mv.id or mv.name), # copy string to dereference mv
                                             u'name': unicode(mv.description or mv.name), 
                                             u'status': unicode(mv.status), 
                                             u'expected': unicode(mv.expected), 
                                             u'actual': unicode(mv.actual)})
            elif modelDocument.type in (ModelDocument.Type.TESTCASE,
                                        ModelDocument.Type.REGISTRYTESTCASE):
                tc = modelDocument
                test_case = os.path.basename(tc.uri)
                if hasattr(tc, u"testcaseVariations"):
                    for mv in tc.testcaseVariations:
                        outcomes.append({u'section': section,
                                         u'testcase': test_case,
                                         u'variation': unicode(mv.id or mv.name), 
                                         u'name': unicode(mv.description or mv.name), 
                                         u'status': unicode(mv.status), 
                                         u'expected': unicode(mv.expected), 
                                         u'actual': unicode(mv.actual)})
            elif modelDocument.type == ModelDocument.Type.RSSFEED:
                tc = modelDocument
                if hasattr(tc, u"rssItems"):
                    for rssItem in tc.rssItems:
                        outcomes.append({u'section': section,
                                         u'testcase': os.path.basename(rssItem.url),
                                         u'variation': unicode(rssItem.accessionNumber), 
                                         u'name': unicode(rssItem.formType + u" " +
                                                     rssItem.cikNumber + u" " +
                                                     rssItem.companyName + u" " +
                                                     unicode(rssItem.period) + u" " + 
                                                     unicode(rssItem.filingDate)), 
                                         u'status': unicode(rssItem.status), 
                                         u'expected': rssItem.url, 
                                         u'actual': u" ".join(unicode(result) for result in (rssItem.results or [])) +
                                                   ((u" " + unicode(rssItem.assertions)) if rssItem.assertions else u"")})
        del modelDocument # dereference
    cntlr.modelManager.close()
    del cntlr # dereference

    return outcomes        
            
