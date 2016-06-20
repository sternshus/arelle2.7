u'''
Created on Oct 3, 2010

This module is Arelle's controller in command line non-interactive mode

(This module can be a pattern for custom integration of Arelle into an application.)

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from arelle import PythonUtil # define 2.x or 3.x string types
import gettext, time, datetime, os, shlex, sys, traceback, fnmatch
from optparse import OptionParser, SUPPRESS_HELP
import re
from arelle import (Cntlr, FileSource, ModelDocument, XmlUtil, Version, 
                    ViewFileDTS, ViewFileFactList, ViewFileFactTable, ViewFileConcepts, 
                    ViewFileFormulae, ViewFileRelationshipSet, ViewFileTests, ViewFileRssFeed,
                    ViewFileRoleTypes,
                    ModelManager)
from arelle.ModelValue import qname
from arelle.Locale import format_string
from arelle.ModelFormulaObject import FormulaOptions
from arelle import PluginManager
from arelle.PluginManager import pluginClassMethods
from arelle.WebCache import proxyTuple
import logging
from lxml import etree
win32file = None

def main():
    u"""Main program to initiate application from command line or as a separate process (e.g, java Runtime.getRuntime().exec).  May perform
    a command line request, or initiate a web server on specified local port.
       
       :param argv: Command line arguments.  (Currently supported arguments can be displayed by the parameter *--help*.)
       :type message: [str]
       """
    envArgs = os.getenv(u"ARELLE_ARGS")
    if envArgs:
        args = shlex.split(envArgs)
    else:
        args = sys.argv[1:]
        
    gettext.install(u"arelle") # needed for options messages
    parseAndRun(args)
    
def wsgiApplication():
    return parseAndRun( [u"--webserver=::wsgi"] )
       
def parseAndRun(args):
    u"""interface used by Main program and py.test (arelle_test.py)
    """
    try:
        from arelle import webserver
        hasWebServer = True
    except ImportError:
        hasWebServer = False
    cntlr = CntlrCmdLine()  # need controller for plug ins to be loaded
    usage = u"usage: %prog [options]"
    
    parser = OptionParser(usage, 
                          version=u"Arelle(r) {0}bit {1}".format(cntlr.systemWordSize, Version.version),
                          conflict_handler=u"resolve") # allow reloading plug-in options without errors
    parser.add_option(u"-f", u"--file", dest=u"entrypointFile",
                      help=_(u"FILENAME is an entry point, which may be "
                             u"an XBRL instance, schema, linkbase file, "
                             u"inline XBRL instance, testcase file, "
                             u"testcase index file.  FILENAME may be "
                             u"a local file or a URI to a web located file."))
    parser.add_option(u"--username", dest=u"username",
                      help=_(u"user name if needed (with password) for web file retrieval"))
    parser.add_option(u"--password", dest=u"password",
                      help=_(u"password if needed (with user name) for web retrieval"))
    # special option for web interfaces to suppress closing an opened modelXbrl
    parser.add_option(u"--keepOpen", dest=u"keepOpen", action=u"store_true", help=SUPPRESS_HELP)
    parser.add_option(u"-i", u"--import", dest=u"importFiles",
                      help=_(u"FILENAME is a list of files to import to the DTS, such as "
                             u"additional formula or label linkbases.  "
                             u"Multiple file names are separated by a '|' character. "))
    parser.add_option(u"-d", u"--diff", dest=u"diffFile",
                      help=_(u"FILENAME is a second entry point when "
                             u"comparing (diffing) two DTSes producing a versioning report."))
    parser.add_option(u"-r", u"--report", dest=u"versReportFile",
                      help=_(u"FILENAME is the filename to save as the versioning report."))
    parser.add_option(u"-v", u"--validate",
                      action=u"store_true", dest=u"validate",
                      help=_(u"Validate the file according to the entry "
                             u"file type.  If an XBRL file, it is validated "
                             u"according to XBRL validation 2.1, calculation linkbase validation "
                             u"if either --calcDecimals or --calcPrecision are specified, and "
                             u"SEC EDGAR Filing Manual (if --efm selected) or Global Filer Manual "
                             u"disclosure system validation (if --gfm=XXX selected). "
                             u"If a test suite or testcase, the test case variations "
                             u"are individually so validated. "
                             u"If formulae are present they will be validated and run unless --formula=none is specified. "
                             ))
    parser.add_option(u"--calcDecimals", action=u"store_true", dest=u"calcDecimals",
                      help=_(u"Specify calculation linkbase validation inferring decimals."))
    parser.add_option(u"--calcdecimals", action=u"store_true", dest=u"calcDecimals", help=SUPPRESS_HELP)
    parser.add_option(u"--calcPrecision", action=u"store_true", dest=u"calcPrecision",
                      help=_(u"Specify calculation linkbase validation inferring precision."))
    parser.add_option(u"--calcprecision", action=u"store_true", dest=u"calcPrecision", help=SUPPRESS_HELP)
    parser.add_option(u"--efm", action=u"store_true", dest=u"validateEFM",
                      help=_(u"Select Edgar Filer Manual (U.S. SEC) disclosure system validation (strict)."))
    parser.add_option(u"--gfm", action=u"store", dest=u"disclosureSystemName", help=SUPPRESS_HELP)
    parser.add_option(u"--disclosureSystem", action=u"store", dest=u"disclosureSystemName",
                      help=_(u"Specify a disclosure system name and"
                             u" select disclosure system validation.  "
                             u"Enter --disclosureSystem=help for list of names or help-verbose for list of names and descriptions. "))
    parser.add_option(u"--disclosuresystem", action=u"store", dest=u"disclosureSystemName", help=SUPPRESS_HELP)
    parser.add_option(u"--hmrc", action=u"store_true", dest=u"validateHMRC",
                      help=_(u"Select U.K. HMRC disclosure system validation."))
    parser.add_option(u"--utr", action=u"store_true", dest=u"utrValidate",
                      help=_(u"Select validation with respect to Unit Type Registry."))
    parser.add_option(u"--utrUrl", action=u"store", dest=u"utrUrl",
                      help=_(u"Override disclosure systems Unit Type Registry location (URL or file path)."))
    parser.add_option(u"--utrurl", action=u"store", dest=u"utrUrl", help=SUPPRESS_HELP)
    parser.add_option(u"--infoset", action=u"store_true", dest=u"infosetValidate",
                      help=_(u"Select validation with respect testcase infosets."))
    parser.add_option(u"--labelLang", action=u"store", dest=u"labelLang",
                      help=_(u"Language for labels in following file options (override system settings)"))
    parser.add_option(u"--labellang", action=u"store", dest=u"labelLang", help=SUPPRESS_HELP)
    parser.add_option(u"--labelRole", action=u"store", dest=u"labelRole",
                      help=_(u"Label role for labels in following file options (instead of standard label)"))
    parser.add_option(u"--labelrole", action=u"store", dest=u"labelRole", help=SUPPRESS_HELP)
    parser.add_option(u"--DTS", u"--csvDTS", action=u"store", dest=u"DTSFile",
                      help=_(u"Write DTS tree into FILE (may be .csv or .html)"))
    parser.add_option(u"--facts", u"--csvFacts", action=u"store", dest=u"factsFile",
                      help=_(u"Write fact list into FILE"))
    parser.add_option(u"--factListCols", action=u"store", dest=u"factListCols",
                      help=_(u"Columns for fact list file"))
    parser.add_option(u"--factTable", u"--csvFactTable", action=u"store", dest=u"factTableFile",
                      help=_(u"Write fact table into FILE"))
    parser.add_option(u"--concepts", u"--csvConcepts", action=u"store", dest=u"conceptsFile",
                      help=_(u"Write concepts into FILE"))
    parser.add_option(u"--pre", u"--csvPre", action=u"store", dest=u"preFile",
                      help=_(u"Write presentation linkbase into FILE"))
    parser.add_option(u"--cal", u"--csvCal", action=u"store", dest=u"calFile",
                      help=_(u"Write calculation linkbase into FILE"))
    parser.add_option(u"--dim", u"--csvDim", action=u"store", dest=u"dimFile",
                      help=_(u"Write dimensions (of definition) linkbase into FILE"))
    parser.add_option(u"--formulae", u"--htmlFormulae", action=u"store", dest=u"formulaeFile",
                      help=_(u"Write formulae linkbase into FILE"))
    parser.add_option(u"--viewArcrole", action=u"store", dest=u"viewArcrole",
                      help=_(u"Write linkbase relationships for viewArcrole into viewFile"))
    parser.add_option(u"--viewarcrole", action=u"store", dest=u"viewArcrole", help=SUPPRESS_HELP)
    parser.add_option(u"--viewFile", action=u"store", dest=u"viewFile",
                      help=_(u"Write linkbase relationships for viewArcrole into viewFile"))
    parser.add_option(u"--viewfile", action=u"store", dest=u"viewFile", help=SUPPRESS_HELP)
    parser.add_option(u"--roleTypes", action=u"store", dest=u"roleTypesFile",
                      help=_(u"Write defined role types into FILE"))
    parser.add_option(u"--roletypes", action=u"store", dest=u"roleTypesFile", help=SUPPRESS_HELP)
    parser.add_option(u"--arcroleTypes", action=u"store", dest=u"arcroleTypesFile",
                      help=_(u"Write defined arcrole types into FILE"))
    parser.add_option(u"--arcroletypes", action=u"store", dest=u"arcroleTypesFile", help=SUPPRESS_HELP)
    parser.add_option(u"--testReport", u"--csvTestReport", action=u"store", dest=u"testReport",
                      help=_(u"Write test report of validation (of test cases) into FILE"))
    parser.add_option(u"--testreport", u"--csvtestreport", action=u"store", dest=u"testReport", help=SUPPRESS_HELP)
    parser.add_option(u"--testReportCols", action=u"store", dest=u"testReportCols",
                      help=_(u"Columns for test report file"))
    parser.add_option(u"--testreportcols", action=u"store", dest=u"testReportCols", help=SUPPRESS_HELP)
    parser.add_option(u"--rssReport", action=u"store", dest=u"rssReport",
                      help=_(u"Write RSS report into FILE"))
    parser.add_option(u"--rssreport", action=u"store", dest=u"rssReport", help=SUPPRESS_HELP)
    parser.add_option(u"--rssReportCols", action=u"store", dest=u"rssReportCols",
                      help=_(u"Columns for RSS report file"))
    parser.add_option(u"--rssreportcols", action=u"store", dest=u"rssReportCols", help=SUPPRESS_HELP)
    parser.add_option(u"--skipDTS", action=u"store_true", dest=u"skipDTS",
                      help=_(u"Skip DTS activities (loading, discovery, validation), useful when an instance needs only to be parsed."))
    parser.add_option(u"--skipdts", action=u"store_true", dest=u"skipDTS", help=SUPPRESS_HELP)
    parser.add_option(u"--skipLoading", action=u"store", dest=u"skipLoading",
                      help=_(u"Skip loading discovered or schemaLocated files matching pattern (unix-style file name patterns separated by '|'), useful when not all linkbases are needed."))
    parser.add_option(u"--skiploading", action=u"store", dest=u"skipLoading", help=SUPPRESS_HELP)
    parser.add_option(u"--logFile", action=u"store", dest=u"logFile",
                      help=_(u"Write log messages into file, otherwise they go to standard output.  " 
                             u"If file ends in .xml it is xml-formatted, otherwise it is text. "))
    parser.add_option(u"--logfile", action=u"store", dest=u"logFile", help=SUPPRESS_HELP)
    parser.add_option(u"--logFormat", action=u"store", dest=u"logFormat",
                      help=_(u"Logging format for messages capture, otherwise default is \"[%(messageCode)s] %(message)s - %(file)s\"."))
    parser.add_option(u"--logformat", action=u"store", dest=u"logFormat", help=SUPPRESS_HELP)
    parser.add_option(u"--logLevel", action=u"store", dest=u"logLevel",
                      help=_(u"Minimum level for messages capture, otherwise the message is ignored.  " 
                             u"Current order of levels are debug, info, info-semantic, warning, warning-semantic, warning, assertion-satisfied, inconsistency, error-semantic, assertion-not-satisfied, and error. "))
    parser.add_option(u"--loglevel", action=u"store", dest=u"logLevel", help=SUPPRESS_HELP)
    parser.add_option(u"--logLevelFilter", action=u"store", dest=u"logLevelFilter",
                      help=_(u"Regular expression filter for logLevel.  " 
                             u"(E.g., to not match *-semantic levels, logLevelFilter=(?!^.*-semantic$)(.+). "))
    parser.add_option(u"--loglevelfilter", action=u"store", dest=u"logLevelFilter", help=SUPPRESS_HELP)
    parser.add_option(u"--logCodeFilter", action=u"store", dest=u"logCodeFilter",
                      help=_(u"Regular expression filter for log message code."))
    parser.add_option(u"--logcodefilter", action=u"store", dest=u"logCodeFilter", help=SUPPRESS_HELP)
    parser.add_option(u"--statusPipe", action=u"store", dest=u"statusPipe", help=SUPPRESS_HELP)
    parser.add_option(u"--outputAttribution", action=u"store", dest=u"outputAttribution", help=SUPPRESS_HELP)
    parser.add_option(u"--outputattribution", action=u"store", dest=u"outputAttribution", help=SUPPRESS_HELP)
    parser.add_option(u"--showOptions", action=u"store_true", dest=u"showOptions", help=SUPPRESS_HELP)
    parser.add_option(u"--parameters", action=u"store", dest=u"parameters", help=_(u"Specify parameters for formula and validation (name=value[,name=value])."))
    parser.add_option(u"--parameterSeparator", action=u"store", dest=u"parameterSeparator", help=_(u"Specify parameters separator string (if other than comma)."))
    parser.add_option(u"--parameterseparator", action=u"store", dest=u"parameterSeparator", help=SUPPRESS_HELP)
    parser.add_option(u"--formula", choices=(u"validate", u"run", u"none"), dest=u"formulaAction", 
                      help=_(u"Specify formula action: "
                             u"validate - validate only, without running, "
                             u"run - validate and run, or "
                             u"none - prevent formula validation or running when also specifying -v or --validate.  "
                             u"if this option is not specified, -v or --validate will validate and run formulas if present"))
    parser.add_option(u"--formulaParamExprResult", action=u"store_true", dest=u"formulaParamExprResult", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulaparamexprresult", action=u"store_true", dest=u"formulaParamExprResult", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaParamInputValue", action=u"store_true", dest=u"formulaParamInputValue", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulaparaminputvalue", action=u"store_true", dest=u"formulaParamInputValue", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaCallExprSource", action=u"store_true", dest=u"formulaCallExprSource", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulacallexprsource", action=u"store_true", dest=u"formulaCallExprSource", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaCallExprCode", action=u"store_true", dest=u"formulaCallExprCode", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulacallexprcode", action=u"store_true", dest=u"formulaCallExprCode", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaCallExprEval", action=u"store_true", dest=u"formulaCallExprEval", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulacallexpreval", action=u"store_true", dest=u"formulaCallExprEval", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaCallExprResult", action=u"store_true", dest=u"formulaCallExprResult", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulacallexprtesult", action=u"store_true", dest=u"formulaCallExprResult", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaVarSetExprEval", action=u"store_true", dest=u"formulaVarSetExprEval", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulavarsetexpreval", action=u"store_true", dest=u"formulaVarSetExprEval", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaVarSetExprResult", action=u"store_true", dest=u"formulaVarSetExprResult", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulavarsetexprresult", action=u"store_true", dest=u"formulaVarSetExprResult", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaVarSetTiming", action=u"store_true", dest=u"timeVariableSetEvaluation", help=_(u"Specify showing times of variable set evaluation."))
    parser.add_option(u"--formulavarsettiming", action=u"store_true", dest=u"timeVariableSetEvaluation", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaAsserResultCounts", action=u"store_true", dest=u"formulaAsserResultCounts", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulaasserresultcounts", action=u"store_true", dest=u"formulaAsserResultCounts", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaSatisfiedAsser", action=u"store_true", dest=u"formulaSatisfiedAsser", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulasatisfiedasser", action=u"store_true", dest=u"formulaSatisfiedAsser", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaUnsatisfiedAsser", action=u"store_true", dest=u"formulaUnsatisfiedAsser", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulaunsatisfiedasser", action=u"store_true", dest=u"formulaUnsatisfiedAsser", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaUnsatisfiedAsserError", action=u"store_true", dest=u"formulaUnsatisfiedAsserError", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulaunsatisfiedassererror", action=u"store_true", dest=u"formulaUnsatisfiedAsserError", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaFormulaRules", action=u"store_true", dest=u"formulaFormulaRules", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulaformularules", action=u"store_true", dest=u"formulaFormulaRules", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaVarsOrder", action=u"store_true", dest=u"formulaVarsOrder", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulavarsorder", action=u"store_true", dest=u"formulaVarsOrder", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaVarExpressionSource", action=u"store_true", dest=u"formulaVarExpressionSource", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulavarexpressionsource", action=u"store_true", dest=u"formulaVarExpressionSource", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaVarExpressionCode", action=u"store_true", dest=u"formulaVarExpressionCode", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulavarexpressioncode", action=u"store_true", dest=u"formulaVarExpressionCode", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaVarExpressionEvaluation", action=u"store_true", dest=u"formulaVarExpressionEvaluation", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulavarexpressionevaluation", action=u"store_true", dest=u"formulaVarExpressionEvaluation", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaVarExpressionResult", action=u"store_true", dest=u"formulaVarExpressionResult", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulavarexpressionresult", action=u"store_true", dest=u"formulaVarExpressionResult", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaVarFilterWinnowing", action=u"store_true", dest=u"formulaVarFilterWinnowing", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulavarfilterwinnowing", action=u"store_true", dest=u"formulaVarFilterWinnowing", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaVarFiltersResult", action=u"store_true", dest=u"formulaVarFiltersResult", help=_(u"Specify formula tracing."))
    parser.add_option(u"--formulavarfiltersresult", action=u"store_true", dest=u"formulaVarFiltersResult", help=SUPPRESS_HELP)
    parser.add_option(u"--formulaRunIDs", action=u"store", dest=u"formulaRunIDs", help=_(u"Specify formula/assertion IDs to run, separated by a '|' character."))
    parser.add_option(u"--formularunids", action=u"store", dest=u"formulaRunIDs", help=SUPPRESS_HELP)
    parser.add_option(u"--uiLang", action=u"store", dest=u"uiLang",
                      help=_(u"Language for user interface (override system settings, such as program messages).  Does not save setting."))
    parser.add_option(u"--uilang", action=u"store", dest=u"uiLang", help=SUPPRESS_HELP)
    parser.add_option(u"--proxy", action=u"store", dest=u"proxy",
                      help=_(u"Modify and re-save proxy settings configuration.  " 
                             u"Enter 'system' to use system proxy setting, 'none' to use no proxy, "
                             u"'http://[user[:password]@]host[:port]' "
                             u" (e.g., http://192.168.1.253, http://example.com:8080, http://joe:secret@example.com:8080), "
                             u" or 'show' to show current setting, ." ))
    parser.add_option(u"--internetConnectivity", choices=(u"online", u"offline"), dest=u"internetConnectivity", 
                      help=_(u"Specify internet connectivity: online or offline"))
    parser.add_option(u"--internetconnectivity", action=u"store", dest=u"internetConnectivity", help=SUPPRESS_HELP)
    parser.add_option(u"--internetTimeout", type=u"int", dest=u"internetTimeout", 
                      help=_(u"Specify internet connection timeout in seconds (0 means unlimited)."))
    parser.add_option(u"--internettimeout", type=u"int", action=u"store", dest=u"internetTimeout", help=SUPPRESS_HELP)
    parser.add_option(u"--internetRecheck", choices=(u"weekly", u"daily", u"never"), dest=u"internetRecheck", 
                      help=_(u"Specify rechecking cache files (weekly is default)"))
    parser.add_option(u"--internetrecheck", choices=(u"weekly", u"daily", u"never"), action=u"store", dest=u"internetRecheck", help=SUPPRESS_HELP)
    parser.add_option(u"--internetLogDownloads", action=u"store_true", dest=u"internetLogDownloads", 
                      help=_(u"Log info message for downloads to web cache."))
    parser.add_option(u"--internetlogdownloads", action=u"store_true", dest=u"internetLogDownloads", help=SUPPRESS_HELP)
    parser.add_option(u"--xdgConfigHome", action=u"store", dest=u"xdgConfigHome", 
                      help=_(u"Specify non-standard location for configuration and cache files (overrides environment parameter XDG_CONFIG_HOME)."))
    parser.add_option(u"--plugins", action=u"store", dest=u"plugins",
                      help=_(u"Modify plug-in configuration.  "
                             u"Re-save unless 'temp' is in the module list.  " 
                             u"Enter 'show' to show current plug-in configuration.  "
                             u"Commands show, and module urls are '|' separated: "
                             u"+url to add plug-in by its url or filename, ~name to reload a plug-in by its name, -name to remove a plug-in by its name, "
                             u"relative URLs are relative to installation plug-in directory, "
                             u" (e.g., '+http://arelle.org/files/hello_web.py', '+C:\Program Files\Arelle\examples\plugin\hello_dolly.py' to load, "
                             u"or +../examples/plugin/hello_dolly.py for relative use of examples directory, "
                             u"~Hello Dolly to reload, -Hello Dolly to remove).  "
                             u"If + is omitted from .py file nothing is saved (same as temp).  "
                             u"Packaged plug-in urls are their directory's url.  " ))
    parser.add_option(u"--packages", action=u"store", dest=u"packages",
                      help=_(u"Modify taxonomy packages configuration.  "
                             u"Re-save unless 'temp' is in the module list.  " 
                             u"Enter 'show' to show current packages configuration.  "
                             u"Commands show, and module urls are '|' separated: "
                             u"+url to add package by its url or filename, ~name to reload package by its name, -name to remove a package by its name, "
                             u"URLs are full absolute paths.  "
                             u"If + is omitted from package file nothing is saved (same as temp).  " ))
    parser.add_option(u"--packageManifestName", action=u"store", dest=u"packageManifestName",
                      help=_(u"Provide non-standard archive manifest file name pattern (e.g., *taxonomyPackage.xml).  "
                             u"Uses unix file name pattern matching.  "
                             u"Multiple manifest files are supported in archive (such as oasis catalogs).  "
                             u"(Replaces search for either .taxonomyPackage.xml or catalog.xml).  " ))
    parser.add_option(u"--abortOnMajorError", action=u"store_true", dest=u"abortOnMajorError", help=_(u"Abort process on major error, such as when load is unable to find an entry or discovered file."))
    parser.add_option(u"--showEnvironment", action=u"store_true", dest=u"showEnvironment", help=_(u"Show Arelle's config and cache directory and host OS environment parameters."))
    parser.add_option(u"--showenvironment", action=u"store_true", dest=u"showEnvironment", help=SUPPRESS_HELP)
    parser.add_option(u"--collectProfileStats", action=u"store_true", dest=u"collectProfileStats", help=_(u"Collect profile statistics, such as timing of validation activities and formulae."))
    if hasWebServer:
        parser.add_option(u"--webserver", action=u"store", dest=u"webserver",
                          help=_(u"start web server on host:port[:server] for REST and web access, e.g., --webserver locahost:8080, "
                                 u"or specify nondefault a server name, such as cherrypy, --webserver locahost:8080:cherrypy. "
                                 u"(It is possible to specify options to be defaults for the web server, such as disclosureSystem and validations, but not including file names.) "))
    pluginOptionsIndex = len(parser.option_list)

    # install any dynamic plugins so their command line options can be parsed if present
    for i, arg in enumerate(args):
        if arg.startswith(u'--plugins'):
            if len(arg) > 9 and arg[9] == u'=':
                preloadPlugins = arg[10:]
            elif i < len(args) - 1:
                preloadPlugins = args[i+1]
            else:
                preloadPlugins = u""
            for pluginCmd in preloadPlugins.split(u'|'):
                cmd = pluginCmd.strip()
                if cmd not in (u"show", u"temp") and len(cmd) > 0 and cmd[0] not in (u'-', u'~', u'+'):
                    moduleInfo = PluginManager.addPluginModule(cmd)
                    if moduleInfo:
                        cntlr.preloadedPlugins[cmd] = moduleInfo
                        PluginManager.reset()
            break
    # add plug-in options
    for optionsExtender in pluginClassMethods(u"CntlrCmdLine.Options"):
        optionsExtender(parser)
    pluginLastOptionIndex = len(parser.option_list)
    parser.add_option(u"-a", u"--about",
                      action=u"store_true", dest=u"about",
                      help=_(u"Show product version, copyright, and license."))
    
    if not args and cntlr.isGAE:
        args = [u"--webserver=::gae"]
    elif cntlr.isCGI:
        args = [u"--webserver=::cgi"]
    elif cntlr.isMSW:
        # if called from java on Windows any empty-string arguments are lost, see:
        # http://bugs.sun.com/view_bug.do?bug_id=6518827
        # insert needed arguments
        sourceArgs = args
        args = []
        namedOptions = set()
        optionsWithArg = set()
        for option in parser.option_list:
            names = unicode(option).split(u'/')
            namedOptions.update(names)
            if option.action == u"store":
                optionsWithArg.update(names)
        priorArg = None
        for arg in sourceArgs:
            if priorArg in optionsWithArg and arg in namedOptions:
                # probable java/MSFT interface bug 6518827
                args.append(u'')  # add empty string argument
            args.append(arg)
            priorArg = arg
        
    (options, leftoverArgs) = parser.parse_args(args)
    if options.about:
        print _(u"\narelle(r) {0}bit {1}\n\n"
                u"An open source XBRL platform\n"
                u"(c) 2010-2014 Mark V Systems Limited\n"
                u"All rights reserved\nhttp://www.arelle.org\nsupport@arelle.org\n\n"
                u"Licensed under the Apache License, Version 2.0 (the \"License\"); "
                u"you may not \nuse this file except in compliance with the License.  "
                u"You may obtain a copy \nof the License at "
                u"'http://www.apache.org/licenses/LICENSE-2.0'\n\n"
                u"Unless required by applicable law or agreed to in writing, software \n"
                u"distributed under the License is distributed on an \"AS IS\" BASIS, \n"
                u"WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  \n"
                u"See the License for the specific language governing permissions and \n"
                u"limitations under the License."
                u"\n\nIncludes:"
                u"\n   Python(r) {3[0]}.{3[1]}.{3[2]} (c) 2001-2013 Python Software Foundation"
                u"\n   PyParsing (c) 2003-2013 Paul T. McGuire"
                u"\n   lxml {4[0]}.{4[1]}.{4[2]} (c) 2004 Infrae, ElementTree (c) 1999-2004 by Fredrik Lundh"
                u"\n   xlrd (c) 2005-2013 Stephen J. Machin, Lingfo Pty Ltd, (c) 2001 D. Giffin, (c) 2000 A. Khan"
                u"\n   xlwt (c) 2007 Stephen J. Machin, Lingfo Pty Ltd, (c) 2005 R. V. Kiseliov"
                u"{2}"
                ).format(cntlr.systemWordSize, Version.version,
                         _(u"\n   Bottle (c) 2011-2013 Marcel Hellkamp") if hasWebServer else u"",
                         sys.version_info, etree.LXML_VERSION)
    elif options.disclosureSystemName in (u"help", u"help-verbose"):
        text = _(u"Disclosure system choices: \n{0}").format(u' \n'.join(cntlr.modelManager.disclosureSystem.dirlist(options.disclosureSystemName)))
        try:
            print text
        except UnicodeEncodeError:
            print text.encode(u"ascii", u"replace").decode(u"ascii")
    elif len(leftoverArgs) != 0 and (not hasWebServer or options.webserver is None):
        parser.error(_(u"unrecognized arguments: {}".format(u', '.join(leftoverArgs))))
    elif (options.entrypointFile is None and 
          ((not options.proxy) and (not options.plugins) and
           (not any(pluginOption for pluginOption in parser.option_list[pluginOptionsIndex:pluginLastOptionIndex])) and
           (not hasWebServer or options.webserver is None))):
        parser.error(_(u"incorrect arguments, please try\n  python CntlrCmdLine.py --help"))
    elif hasWebServer and options.webserver:
        # webserver incompatible with file operations
        if any((options.entrypointFile, options.importFiles, options.diffFile, options.versReportFile,
                options.factsFile, options.factListCols, options.factTableFile,
                options.conceptsFile, options.preFile, options.calFile, options.dimFile, options.formulaeFile, options.viewArcrole, options.viewFile,
                options.roleTypesFile, options.arcroleTypesFile
                )):
            parser.error(_(u"incorrect arguments with --webserver, please try\n  python CntlrCmdLine.py --help"))
        else:
            cntlr.startLogging(logFileName=u'logToBuffer')
            from arelle import CntlrWebMain
            app = CntlrWebMain.startWebserver(cntlr, options)
            if options.webserver == u'::wsgi':
                return app
    else:
        # parse and run the FILENAME
        cntlr.startLogging(logFileName=(options.logFile or u"logToPrint"),
                           logFormat=(options.logFormat or u"[%(messageCode)s] %(message)s - %(file)s"),
                           logLevel=(options.logLevel or u"DEBUG"))
        cntlr.run(options)
        
        return cntlr
        
class CntlrCmdLine(Cntlr.Cntlr):
    u"""
    .. class:: CntlrCmdLin()
    
    Initialization sets up for platform via Cntlr.Cntlr.
    """

    def __init__(self, logFileName=None):
        super(CntlrCmdLine, self).__init__(hasGui=False)
        self.preloadedPlugins =  {}
        
    def run(self, options, sourceZipStream=None):
        u"""Process command line arguments or web service request, such as to load and validate an XBRL document, or start web server.
        
        When a web server has been requested, this method may be called multiple times, once for each web service (REST) request that requires processing.
        Otherwise (when called for a command line request) this method is called only once for the command line arguments request.
           
        :param options: OptionParser options from parse_args of main argv arguments (when called from command line) or corresponding arguments from web service (REST) request.
        :type options: optparse.Values
        """
                
        if options.statusPipe:
            try:
                global win32file
                import win32file, pywintypes
                self.statusPipe = win32file.CreateFile(u"\\\\.\\pipe\\{}".format(options.statusPipe), 
                                                       win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None, win32file.OPEN_EXISTING, win32file.FILE_FLAG_NO_BUFFERING, None)
                self.showStatus = self.showStatusOnPipe
                self.lastStatusTime = 0.0
            except ImportError: # win32 not installed
                self.addToLog(u"--statusPipe {} cannot be installed, packages for win32 missing".format(options.statusPipe))
            except pywintypes.error: # named pipe doesn't exist
                self.addToLog(u"--statusPipe {} has not been created by calling program".format(options.statusPipe))
        if options.showOptions: # debug options
            for optName, optValue in sorted(options.__dict__.items(), key=lambda optItem: optItem[0]):
                self.addToLog(u"Option {0}={1}".format(optName, optValue), messageCode=u"info")
            self.addToLog(u"sys.argv {0}".format(sys.argv), messageCode=u"info")
        if options.uiLang: # set current UI Lang (but not config setting)
            self.setUiLanguage(options.uiLang)
        if options.proxy:
            if options.proxy != u"show":
                proxySettings = proxyTuple(options.proxy)
                self.webCache.resetProxies(proxySettings)
                self.config[u"proxySettings"] = proxySettings
                self.saveConfig()
                self.addToLog(_(u"Proxy configuration has been set."), messageCode=u"info")
            useOsProxy, urlAddr, urlPort, user, password = self.config.get(u"proxySettings", proxyTuple(u"none"))
            if useOsProxy:
                self.addToLog(_(u"Proxy configured to use {0}.").format(
                    _(u'Microsoft Windows Internet Settings') if sys.platform.startswith(u"win")
                    else (_(u'Mac OS X System Configuration') if sys.platform in (u"darwin", u"macos")
                          else _(u'environment variables'))), messageCode=u"info")
            elif urlAddr:
                self.addToLog(_(u"Proxy setting: http://{0}{1}{2}{3}{4}").format(
                    user if user else u"",
                    u":****" if password else u"",
                    u"@" if (user or password) else u"",
                    urlAddr,
                    u":{0}".format(urlPort) if urlPort else u""), messageCode=u"info")
            else:
                self.addToLog(_(u"Proxy is disabled."), messageCode=u"info")
        if options.plugins:
            resetPlugins = False
            savePluginChanges = True
            showPluginModules = False
            for pluginCmd in options.plugins.split(u'|'):
                cmd = pluginCmd.strip()
                if cmd == u"show":
                    showPluginModules = True
                elif cmd == u"temp":
                    savePluginChanges = False
                elif cmd.startswith(u"+"):
                    moduleInfo = PluginManager.addPluginModule(cmd[1:])
                    if moduleInfo:
                        self.addToLog(_(u"Addition of plug-in {0} successful.").format(moduleInfo.get(u"name")), 
                                      messageCode=u"info", file=moduleInfo.get(u"moduleURL"))
                        resetPlugins = True
                        if u"CntlrCmdLine.Options" in moduleInfo[u"classMethods"]:
                            addedPluginWithCntlrCmdLineOptions = True
                    else:
                        self.addToLog(_(u"Unable to load plug-in."), messageCode=u"info", file=cmd[1:])
                elif cmd.startswith(u"~"):
                    if PluginManager.reloadPluginModule(cmd[1:]):
                        self.addToLog(_(u"Reload of plug-in successful."), messageCode=u"info", file=cmd[1:])
                        resetPlugins = True
                    else:
                        self.addToLog(_(u"Unable to reload plug-in."), messageCode=u"info", file=cmd[1:])
                elif cmd.startswith(u"-"):
                    if PluginManager.removePluginModule(cmd[1:]):
                        self.addToLog(_(u"Deletion of plug-in successful."), messageCode=u"info", file=cmd[1:])
                        resetPlugins = True
                    else:
                        self.addToLog(_(u"Unable to delete plug-in."), messageCode=u"info", file=cmd[1:])
                else: # assume it is a module or package (may also have been loaded before for option parsing)
                    savePluginChanges = False
                    if cmd in self.preloadedPlugins:
                        moduleInfo =  self.preloadedPlugins[cmd] # already loaded, add activation message to log below
                    else:
                        moduleInfo = PluginManager.addPluginModule(cmd)
                        if moduleInfo:
                            resetPlugins = True
                    if moduleInfo: 
                        self.addToLog(_(u"Activation of plug-in {0} successful.").format(moduleInfo.get(u"name")), 
                                      messageCode=u"info", file=moduleInfo.get(u"moduleURL"))
                    else:
                        self.addToLog(_(u"Unable to load {0} as a plug-in or {0} is not recognized as a command. ").format(cmd), messageCode=u"info", file=cmd)
                if resetPlugins:
                    PluginManager.reset()
                    if savePluginChanges:
                        PluginManager.save(self)
            if showPluginModules:
                self.addToLog(_(u"Plug-in modules:"), messageCode=u"info")
                for i, moduleItem in enumerate(sorted(PluginManager.pluginConfig.get(u"modules", {}).items())):
                    moduleInfo = moduleItem[1]
                    self.addToLog(_(u"Plug-in: {0}; author: {1}; version: {2}; status: {3}; date: {4}; description: {5}; license {6}.").format(
                                  moduleItem[0], moduleInfo.get(u"author"), moduleInfo.get(u"version"), moduleInfo.get(u"status"),
                                  moduleInfo.get(u"fileDate"), moduleInfo.get(u"description"), moduleInfo.get(u"license")),
                                  messageCode=u"info", file=moduleInfo.get(u"moduleURL"))
        if options.packages:
            from arelle import PackageManager
            savePackagesChanges = True
            showPackages = False
            for packageCmd in options.packages.split(u'|'):
                cmd = packageCmd.strip()
                if cmd == u"show":
                    showPackages = True
                elif cmd == u"temp":
                    savePackagesChanges = False
                elif cmd.startswith(u"+"):
                    packageInfo = PackageManager.addPackage(cmd[1:], options.packageManifestName)
                    if packageInfo:
                        self.addToLog(_(u"Addition of package {0} successful.").format(packageInfo.get(u"name")), 
                                      messageCode=u"info", file=packageInfo.get(u"URL"))
                    else:
                        self.addToLog(_(u"Unable to load plug-in."), messageCode=u"info", file=cmd[1:])
                elif cmd.startswith(u"~"):
                    if PackageManager.reloadPackageModule(cmd[1:]):
                        self.addToLog(_(u"Reload of package successful."), messageCode=u"info", file=cmd[1:])
                    else:
                        self.addToLog(_(u"Unable to reload package."), messageCode=u"info", file=cmd[1:])
                elif cmd.startswith(u"-"):
                    if PackageManager.removePackageModule(cmd[1:]):
                        self.addToLog(_(u"Deletion of package successful."), messageCode=u"info", file=cmd[1:])
                    else:
                        self.addToLog(_(u"Unable to delete package."), messageCode=u"info", file=cmd[1:])
                else: # assume it is a module or package
                    savePackagesChanges = False
                    packageInfo = PackageManager.addPackage(cmd, options.packageManifestName)
                    if packageInfo:
                        self.addToLog(_(u"Activation of package {0} successful.").format(packageInfo.get(u"name")), 
                                      messageCode=u"info", file=packageInfo.get(u"URL"))
                        resetPlugins = True
                    else:
                        self.addToLog(_(u"Unable to load {0} as a package or {0} is not recognized as a command. ").format(cmd), messageCode=u"info", file=cmd)
            if savePackagesChanges:
                PackageManager.save(self)
            if showPackages:
                self.addToLog(_(u"Taxonomy packages:"), messageCode=u"info")
                for packageInfo in PackageManager.orderedPackagesConfig()[u"packages"]:
                    self.addToLog(_(u"Package: {0}; version: {1}; status: {2}; date: {3}; description: {4}.").format(
                                  packageInfo.get(u"name"), packageInfo.get(u"version"), packageInfo.get(u"status"),
                                  packageInfo.get(u"fileDate"), packageInfo.get(u"description")),
                                  messageCode=u"info", file=packageInfo.get(u"URL"))
                
        if options.showEnvironment:
            self.addToLog(_(u"Config directory: {0}").format(self.configDir))
            self.addToLog(_(u"Cache directory: {0}").format(self.userAppDir))
            for envVar in (u"XDG_CONFIG_HOME",):
                if envVar in os.environ:
                    self.addToLog(_(u"XDG_CONFIG_HOME={0}").format(os.environ[envVar]))
            return True
        # run utility command line options that don't depend on entrypoint Files
        hasUtilityPlugin = False
        for pluginXbrlMethod in pluginClassMethods(u"CntlrCmdLine.Utility.Run"):
            hasUtilityPlugin = True
            try:
                pluginXbrlMethod(self, options, sourceZipStream=sourceZipStream)
            except SystemExit: # terminate operation, plug in has terminated all processing
                return True # success
            
        # if no entrypointFile is applicable, quit now
        if options.proxy or options.plugins or hasUtilityPlugin:
            if not options.entrypointFile:
                return True # success
        self.username = options.username
        self.password = options.password
        self.entrypointFile = options.entrypointFile
        if self.entrypointFile:
            filesource = FileSource.openFileSource(self.entrypointFile, self, sourceZipStream)
        else:
            filesource = None
        if options.validateEFM:
            if options.disclosureSystemName:
                self.addToLog(_(u"both --efm and --disclosureSystem validation are requested, proceeding with --efm only"),
                              messageCode=u"info", file=self.entrypointFile)
            self.modelManager.validateDisclosureSystem = True
            self.modelManager.disclosureSystem.select(u"efm")
        elif options.disclosureSystemName:
            self.modelManager.validateDisclosureSystem = True
            self.modelManager.disclosureSystem.select(options.disclosureSystemName)
        elif options.validateHMRC:
            self.modelManager.validateDisclosureSystem = True
            self.modelManager.disclosureSystem.select(u"hmrc")
        else:
            self.modelManager.disclosureSystem.select(None) # just load ordinary mappings
            self.modelManager.validateDisclosureSystem = False
        if options.utrUrl:  # override disclosureSystem utrUrl
            self.modelManager.disclosureSystem.utrUrl = options.utrUrl
            # can be set now because the utr is first loaded at validation time 
        if options.skipDTS: # skip DTS loading, discovery, etc
            self.modelManager.skipDTS = True
        if options.skipLoading: # skip loading matching files (list of unix patterns)
            self.modelManager.skipLoading = re.compile(
                u'|'.join(fnmatch.translate(f) for f in options.skipLoading.split(u'|')))
            
        # disclosure system sets logging filters, override disclosure filters, if specified by command line
        if options.logLevelFilter:
            self.setLogLevelFilter(options.logLevelFilter)
        if options.logCodeFilter:
            self.setLogCodeFilter(options.logCodeFilter)
        if options.calcDecimals:
            if options.calcPrecision:
                self.addToLog(_(u"both --calcDecimals and --calcPrecision validation are requested, proceeding with --calcDecimals only"),
                              messageCode=u"info", file=self.entrypointFile)
            self.modelManager.validateInferDecimals = True
            self.modelManager.validateCalcLB = True
        elif options.calcPrecision:
            self.modelManager.validateInferDecimals = False
            self.modelManager.validateCalcLB = True
        if options.utrValidate:
            self.modelManager.validateUtr = True
        if options.infosetValidate:
            self.modelManager.validateInfoset = True
        if options.abortOnMajorError:
            self.modelManager.abortOnMajorError = True
        if options.collectProfileStats:
            self.modelManager.collectProfileStats = True
        if options.outputAttribution:
            self.modelManager.outputAttribution = options.outputAttribution
        if options.internetConnectivity == u"offline":
            self.webCache.workOffline = True
        elif options.internetConnectivity == u"online":
            self.webCache.workOffline = False
        if options.internetTimeout is not None:
            self.webCache.timeout = (options.internetTimeout or None)  # use None if zero specified to disable timeout
        if options.internetLogDownloads:
            self.webCache.logDownloads = True
        fo = FormulaOptions()
        if options.parameters:
            parameterSeparator = (options.parameterSeparator or u',')
            fo.parameterValues = dict(((qname(key, noPrefixIsNoNamespace=True),(None,value)) 
                                       for param in options.parameters.split(parameterSeparator) 
                                       for key,sep,value in (param.partition(u'='),) ) )
        if options.formulaParamExprResult:
            fo.traceParameterExpressionResult = True
        if options.formulaParamInputValue:
            fo.traceParameterInputValue = True
        if options.formulaCallExprSource:
            fo.traceCallExpressionSource = True
        if options.formulaCallExprCode:
            fo.traceCallExpressionCode = True
        if options.formulaCallExprEval:
            fo.traceCallExpressionEvaluation = True
        if options.formulaCallExprResult:
            fo.traceCallExpressionResult = True
        if options.formulaVarSetExprEval:
            fo.traceVariableSetExpressionEvaluation = True
        if options.formulaVarSetExprResult:
            fo.traceVariableSetExpressionResult = True
        if options.formulaAsserResultCounts:
            fo.traceAssertionResultCounts = True
        if options.formulaSatisfiedAsser:
            fo.traceSatisfiedAssertions = True
        if options.formulaUnsatisfiedAsser:
            fo.traceUnsatisfiedAssertions = True
        if options.formulaUnsatisfiedAsserError:
            fo.errorUnsatisfiedAssertions = True
        if options.formulaFormulaRules:
            fo.traceFormulaRules = True
        if options.formulaVarsOrder:
            fo.traceVariablesOrder = True
        if options.formulaVarExpressionSource:
            fo.traceVariableExpressionSource = True
        if options.formulaVarExpressionCode:
            fo.traceVariableExpressionCode = True
        if options.formulaVarExpressionEvaluation:
            fo.traceVariableExpressionEvaluation = True
        if options.formulaVarExpressionResult:
            fo.traceVariableExpressionResult = True
        if options.timeVariableSetEvaluation:
            fo.timeVariableSetEvaluation = True
        if options.formulaVarFilterWinnowing:
            fo.traceVariableFilterWinnowing = True
        if options.formulaVarFiltersResult:
            fo.traceVariableFiltersResult = True
        if options.formulaVarFiltersResult:
            fo.traceVariableFiltersResult = True
        if options.formulaRunIDs:
            fo.runIDs = options.formulaRunIDs   
        self.modelManager.formulaOptions = fo
        timeNow = XmlUtil.dateunionValue(datetime.datetime.now())
        firstStartedAt = startedAt = time.time()
        modelDiffReport = None
        success = True
        modelXbrl = None
        try:
            if filesource:
                modelXbrl = self.modelManager.load(filesource, _(u"views loading"))
        except ModelDocument.LoadingException:
            pass
        except Exception, err:
            self.addToLog(_(u"[Exception] Failed to complete request: \n{0} \n{1}").format(
                        err,
                        traceback.format_tb(sys.exc_info()[2])))
            success = False    # loading errors, don't attempt to utilize loaded DTS
        if modelXbrl and modelXbrl.modelDocument:
            loadTime = time.time() - startedAt
            modelXbrl.profileStat(_(u"load"), loadTime)
            self.addToLog(format_string(self.modelManager.locale, 
                                        _(u"loaded in %.2f secs at %s"), 
                                        (loadTime, timeNow)), 
                                        messageCode=u"info", file=self.entrypointFile)
            if options.importFiles:
                for importFile in options.importFiles.split(u"|"):
                    fileName = importFile.strip()
                    if sourceZipStream is not None and not (fileName.startswith(u'http://') or os.path.isabs(fileName)):
                        fileName = os.path.dirname(modelXbrl.uri) + os.sep + fileName # make relative to sourceZipStream
                    ModelDocument.load(modelXbrl, fileName)
                    loadTime = time.time() - startedAt
                    self.addToLog(format_string(self.modelManager.locale, 
                                                _(u"import in %.2f secs at %s"), 
                                                (loadTime, timeNow)), 
                                                messageCode=u"info", file=importFile)
                    modelXbrl.profileStat(_(u"import"), loadTime)
                if modelXbrl.errors:
                    success = False    # loading errors, don't attempt to utilize loaded DTS
            if modelXbrl.modelDocument.type in ModelDocument.Type.TESTCASETYPES:
                for pluginXbrlMethod in pluginClassMethods(u"Testcases.Start"):
                    pluginXbrlMethod(self, options, modelXbrl)
            else: # not a test case, probably instance or DTS
                for pluginXbrlMethod in pluginClassMethods(u"CntlrCmdLine.Xbrl.Loaded"):
                    pluginXbrlMethod(self, options, modelXbrl)
        else:
            success = False
        if success and options.diffFile and options.versReportFile:
            try:
                diffFilesource = FileSource.FileSource(options.diffFile,self)
                startedAt = time.time()
                modelXbrl2 = self.modelManager.load(diffFilesource, _(u"views loading"))
                if modelXbrl2.errors:
                    if not options.keepOpen:
                        modelXbrl2.close()
                    success = False
                else:
                    loadTime = time.time() - startedAt
                    modelXbrl.profileStat(_(u"load"), loadTime)
                    self.addToLog(format_string(self.modelManager.locale, 
                                                _(u"diff comparison DTS loaded in %.2f secs"), 
                                                loadTime), 
                                                messageCode=u"info", file=self.entrypointFile)
                    startedAt = time.time()
                    modelDiffReport = self.modelManager.compareDTSes(options.versReportFile)
                    diffTime = time.time() - startedAt
                    modelXbrl.profileStat(_(u"diff"), diffTime)
                    self.addToLog(format_string(self.modelManager.locale, 
                                                _(u"compared in %.2f secs"), 
                                                diffTime), 
                                                messageCode=u"info", file=self.entrypointFile)
            except ModelDocument.LoadingException:
                success = False
            except Exception, err:
                success = False
                self.addToLog(_(u"[Exception] Failed to doad diff file: \n{0} \n{1}").format(
                            err,
                            traceback.format_tb(sys.exc_info()[2])))
        if success:
            try:
                modelXbrl = self.modelManager.modelXbrl
                hasFormulae = modelXbrl.hasFormulae
                isAlreadyValidated = False
                for pluginXbrlMethod in pluginClassMethods(u"ModelDocument.IsValidated"):
                    if pluginXbrlMethod(modelXbrl): # e.g., streaming extensions already has validated
                        isAlreadyValidated = True
                if options.validate and not isAlreadyValidated:
                    startedAt = time.time()
                    if options.formulaAction: # don't automatically run formulas
                        modelXbrl.hasFormulae = False
                    self.modelManager.validate()
                    if options.formulaAction: # restore setting
                        modelXbrl.hasFormulae = hasFormulae
                    self.addToLog(format_string(self.modelManager.locale, 
                                                _(u"validated in %.2f secs"), 
                                                time.time() - startedAt),
                                                messageCode=u"info", file=self.entrypointFile)
                if (options.formulaAction in (u"validate", u"run") and  # do nothing here if "none"
                    not isAlreadyValidated):  # formulas can't run if streaming has validated the instance 
                    from arelle import ValidateXbrlDimensions, ValidateFormula
                    startedAt = time.time()
                    if not options.validate:
                        ValidateXbrlDimensions.loadDimensionDefaults(modelXbrl)
                    # setup fresh parameters from formula optoins
                    modelXbrl.parameters = fo.typedParameters()
                    ValidateFormula.validate(modelXbrl, compileOnly=(options.formulaAction != u"run"))
                    self.addToLog(format_string(self.modelManager.locale, 
                                                _(u"formula validation and execution in %.2f secs")
                                                if options.formulaAction == u"run"
                                                else _(u"formula validation only in %.2f secs"), 
                                                time.time() - startedAt),
                                                messageCode=u"info", file=self.entrypointFile)
                    

                if options.testReport:
                    ViewFileTests.viewTests(self.modelManager.modelXbrl, options.testReport, options.testReportCols)
                    
                if options.rssReport:
                    ViewFileRssFeed.viewRssFeed(self.modelManager.modelXbrl, options.rssReport, options.rssReportCols)
                    
                if options.DTSFile:
                    ViewFileDTS.viewDTS(modelXbrl, options.DTSFile)
                if options.factsFile:
                    ViewFileFactList.viewFacts(modelXbrl, options.factsFile, labelrole=options.labelRole, lang=options.labelLang, cols=options.factListCols)
                if options.factTableFile:
                    ViewFileFactTable.viewFacts(modelXbrl, options.factTableFile, labelrole=options.labelRole, lang=options.labelLang)
                if options.conceptsFile:
                    ViewFileConcepts.viewConcepts(modelXbrl, options.conceptsFile, labelrole=options.labelRole, lang=options.labelLang)
                if options.preFile:
                    ViewFileRelationshipSet.viewRelationshipSet(modelXbrl, options.preFile, u"Presentation Linkbase", u"http://www.xbrl.org/2003/arcrole/parent-child", labelrole=options.labelRole, lang=options.labelLang)
                if options.calFile:
                    ViewFileRelationshipSet.viewRelationshipSet(modelXbrl, options.calFile, u"Calculation Linkbase", u"http://www.xbrl.org/2003/arcrole/summation-item", labelrole=options.labelRole, lang=options.labelLang)
                if options.dimFile:
                    ViewFileRelationshipSet.viewRelationshipSet(modelXbrl, options.dimFile, u"Dimensions", u"XBRL-dimensions", labelrole=options.labelRole, lang=options.labelLang)
                if options.formulaeFile:
                    ViewFileFormulae.viewFormulae(modelXbrl, options.formulaeFile, u"Formulae", lang=options.labelLang)
                if options.viewArcrole and options.viewFile:
                    ViewFileRelationshipSet.viewRelationshipSet(modelXbrl, options.viewFile, os.path.basename(options.viewArcrole), options.viewArcrole, labelrole=options.labelRole, lang=options.labelLang)
                if options.roleTypesFile:
                    ViewFileRoleTypes.viewRoleTypes(modelXbrl, options.roleTypesFile, u"Role Types", isArcrole=False, lang=options.labelLang)
                if options.arcroleTypesFile:
                    ViewFileRoleTypes.viewRoleTypes(modelXbrl, options.arcroleTypesFile, u"Arcrole Types", isArcrole=True, lang=options.labelLang)
                for pluginXbrlMethod in pluginClassMethods(u"CntlrCmdLine.Xbrl.Run"):
                    pluginXbrlMethod(self, options, modelXbrl)
                                        
            except (IOError, EnvironmentError), err:
                self.addToLog(_(u"[IOError] Failed to save output:\n {0}").format(err),
                              messageCode=u"IOError", 
                              file=options.entrypointFile, 
                              level=logging.CRITICAL)
                success = False
            except Exception, err:
                self.addToLog(_(u"[Exception] Failed to complete request: \n{0} \n{1}").format(
                                err,
                                traceback.format_tb(sys.exc_info()[2])),
                              messageCode=err.__class__.__name__, 
                              file=options.entrypointFile, 
                              level=logging.CRITICAL)
                success = False
        if modelXbrl:
            modelXbrl.profileStat(_(u"total"), time.time() - firstStartedAt)
            if options.collectProfileStats and modelXbrl:
                modelXbrl.logProfileStats()
            if not options.keepOpen:
                if modelDiffReport:
                    self.modelManager.close(modelDiffReport)
                elif modelXbrl:
                    self.modelManager.close(modelXbrl)
        self.username = self.password = None #dereference password

        if options.statusPipe and getattr(self, u"statusPipe", None) is not None:
            win32file.WriteFile(self.statusPipe, " ")  # clear status
            win32file.FlushFileBuffers(self.statusPipe)
            win32file.SetFilePointer(self.statusPipe, 0, win32file.FILE_BEGIN) # hangs on close without this
            win32file.CloseHandle(self.statusPipe)
            self.statusPipe = None # dereference

        return success

    # default web authentication password
    def internet_user_password(self, host, realm):
        return (self.username, self.password)
    
    # special show status for named pipes
    def showStatusOnPipe(self, message, clearAfter=None):
        # now = time.time() # seems ok without time-limiting writes to the pipe
        if self.statusPipe is not None:  # max status updates 3 per second now - 0.3 > self.lastStatusTime and 
            # self.lastStatusTime = now
            win32file.WriteFile(self.statusPipe, (message or u"").encode(u"utf8"))
            win32file.FlushFileBuffers(self.statusPipe)
            win32file.SetFilePointer(self.statusPipe, 0, win32file.FILE_BEGIN)  # hangs on close without this

if __name__ == u"__main__":
    u'''
    if '--COMserver' in sys.argv:
        from arelle import CntlrComServer
        CntlrComServer.main()
    else:
        main()
    '''
    main()

