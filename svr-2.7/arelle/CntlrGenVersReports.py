u'''
Created on Dec 14, 2010

Use this module to start Arelle in command line non-interactive mode

(This module can be a pattern for custom use of Arelle in an application.)

In this example a versioning report production file is read and used to generate
versioning reports, per Roland Hommes 2010-12-10

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.

'''
from __future__ import with_statement
from arelle import PythonUtil # define 2.x or 3.x string types
import time, datetime, os, gettext, io, sys, traceback
from lxml import etree
from optparse import OptionParser
from arelle import (Cntlr, ModelXbrl, ModelDocument, ModelVersReport, FileSource, 
                    XmlUtil, XbrlConst, Version)
from arelle import xlrd
import logging
from io import open

conformanceNS = u"http://xbrl.org/2008/conformance"

def main():
    gettext.install(u"arelle") # needed for options messages
    usage = u"usage: %prog [options]"
    parser = OptionParser(usage, version=u"Arelle(r) {0}".format(Version.version))
    parser.add_option(u"--excelfile", dest=u"excelfilename",
                      help=_(u"FILENAME is an excel 95-2003 index file containing columns: \n"
                             u"Dir is a test directory, \n"
                             u"fromURI is the fromDTS URI relative to test director, \n"
                             u"toURI is the toDTS URI relative to test director, \n"
                             u"Description is the goal of the test for testcase description, \n"
                             u"Assignment is the business, technical, or errata classification, \n"
                             u"Expected event is an event localName that is expected \n\n"
                             u"Output files and testcases are located in filename's directory, \n"
                             u"report files are generated in '/report' under fromURI's directory."))
    parser.add_option(u"--testfiledate", dest=u"testfiledate",
                      help=_(u"Date if desired to use (instead of today) in generated testcase elements."))
    (options, args) = parser.parse_args()
    try:
        CntlrGenVersReports().runFromExcel(options)
    except Exception, ex:
        print ex, traceback.format_tb(sys.exc_info()[2])
        
class CntlrGenVersReports(Cntlr.Cntlr):

    def __init__(self):
        super(CntlrGenVersReports, self).__init__()
        
    def runFromExcel(self, options):
        #testGenFileName = options.excelfilename
        testGenFileName = ur"C:\Users\Herm Fischer\Documents\mvsl\projects\XBRL.org\conformance-versioning\trunk\versioningReport\conf\creation-index.xls"
        testGenDir = os.path.dirname(testGenFileName)
        schemaDir = os.path.dirname(testGenDir) + os.sep + u"schema"
        timeNow = XmlUtil.dateunionValue(datetime.datetime.now())
        if options.testfiledate:
            today = options.testfiledate
        else:
            today = XmlUtil.dateunionValue(datetime.date.today())
        startedAt = time.time()
        
        LogHandler(self) # start logger

        self.logMessages = []
        logMessagesFile = testGenDir + os.sep + u'log-generation-messages.txt'

        modelTestcases = ModelXbrl.create(self.modelManager, url=testGenFileName, isEntry=True)
        testcaseIndexBook = xlrd.open_workbook(testGenFileName)
        testcaseIndexSheet = testcaseIndexBook.sheet_by_index(0)
        self.addToLog(_(u"[info] xls loaded in {0:.2} secs at {1}").format(time.time() - startedAt, timeNow))
        
        # start index file
        indexFiles = [testGenDir + os.sep + u'creation-testcases-index.xml',
                      testGenDir + os.sep + u'consumption-testcases-index.xml']
        indexDocs = []
        testcasesElements = []
        for purpose in (u"Creation",u"Consumption"):
            file = io.StringIO(
                #'<?xml version="1.0" encoding="UTF-8"?>'
                u'<!-- XBRL Versioning 1.0 {0} Tests -->'
                u'<!-- Copyright 2011 XBRL International.  All Rights Reserved. -->'
                u'<?xml-stylesheet type="text/xsl" href="infrastructure/testcases-index.xsl"?>'
                u'<testcases name="XBRL Versioning 1.0 {0} Tests" '
                u' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                u' xsi:noNamespaceSchemaLocation="infrastructure/testcases-index.xsd">'
                u'</testcases>'.format(purpose, today)
                )
            doc = etree.parse(file)
            file.close()
            indexDocs.append(doc)
            testcasesElements.append(doc.getroot())
        priorTestcasesDir = None
        testcaseFiles = None
        testcaseDocs = None
        for iRow in xrange(1, testcaseIndexSheet.nrows):
            try:
                row = testcaseIndexSheet.row(iRow)
                if (row[0].ctype == xlrd.XL_CELL_EMPTY or # must have directory
                    row[1].ctype == xlrd.XL_CELL_EMPTY or # from
                    row[2].ctype == xlrd.XL_CELL_EMPTY):  # to
                    continue
                testDir = row[0].value
                uriFrom = row[1].value
                uriTo = row[2].value
                overrideReport = row[3].value
                description = row[4].value
                if description is None or len(description) == 0:
                    continue # test not ready to run
                assignment = row[5].value
                expectedEvents = row[6].value # comma space separated if multiple
                note = row[7].value
                useCase = row[8].value
                base = os.path.join(os.path.dirname(testGenFileName),testDir) + os.sep
                self.addToLog(_(u"[info] testcase uriFrom {0}").format(uriFrom))
                if uriFrom and uriTo and assignment.lower() not in (u"n.a.", u"error") and expectedEvents != u"N.A.":
                    modelDTSfrom = modelDTSto = None
                    for URIs, msg, isFrom in ((uriFrom, _(u"loading from DTS"), True), (uriTo, _(u"loading to DTS"), False)):
                        if u',' not in URIs:
                            modelDTS = ModelXbrl.load(self.modelManager, URIs, msg, base=base)
                        else:
                            modelDTS = ModelXbrl.create(self.modelManager, 
                                         ModelDocument.Type.DTSENTRIES,
                                         self.webCache.normalizeUrl(URIs.replace(u", ",u"_") + u".dts", 
                                                                    base),
                                         isEntry=True)
                            DTSdoc = modelDTS.modelDocument
                            DTSdoc.inDTS = True
                            for uri in URIs.split(u','):
                                doc = ModelDocument.load(modelDTS, uri.strip(), base=base)
                                if doc is not None:
                                    DTSdoc.referencesDocument[doc] = u"import"  #fake import
                                    doc.inDTS = True
                        if isFrom: modelDTSfrom = modelDTS
                        else: modelDTSto = modelDTS
                    if modelDTSfrom is not None and modelDTSto is not None:
                        # generate differences report
                        reportUri = uriFrom.partition(u',')[0]  # first file
                        reportDir = os.path.dirname(reportUri)
                        if reportDir: reportDir += os.sep
                        reportName = os.path.basename(reportUri).replace(u"from.xsd",u"report.xml")
                        reportFile = reportDir + u"out" + os.sep + reportName
                        #reportFile = reportDir + "report" + os.sep + reportName
                        reportFullPath = self.webCache.normalizeUrl(
                                            reportFile, 
                                            base)
                        testcasesDir = os.path.dirname(os.path.dirname(reportFullPath))
                        if testcasesDir != priorTestcasesDir:
                            # close prior report
                            if priorTestcasesDir:
                                for i,testcaseFile in enumerate(testcaseFiles):
                                    with open(testcaseFile, u"w", encoding=u"utf-8") as fh:
                                        XmlUtil.writexml(fh, testcaseDocs[i], encoding=u"utf-8")
                            testcaseName = os.path.basename(testcasesDir)
                            testcaseFiles = [testcasesDir + os.sep + testcaseName + u"-creation-testcase.xml",
                                             testcasesDir + os.sep + testcaseName + u"-consumption-testcase.xml"]
                            for i,testcaseFile in enumerate(testcaseFiles):
                                etree.SubElement(testcasesElements[i], u"testcase", 
                                                 attrib={u"uri": 
                                                         testcaseFile[len(testGenDir)+1:].replace(u"\\",u"/")} )
                            
                            # start testcase file
                            testcaseDocs = []
                            testcaseElements = []
                            testcaseNumber = testcaseName[0:4]
                            if testcaseNumber.isnumeric():
                                testcaseNumberElement = u"<number>{0}</number>".format(testcaseNumber)
                                testcaseName = testcaseName[5:]
                            else:
                                testcaseNumberElement = u""
                            testDirSegments = testDir.split(u'/')
                            if len(testDirSegments) >= 2 and u'-' in testDirSegments[1]:
                                testedModule = testDirSegments[1][testDirSegments[1].index(u'-') + 1:]
                            else:
                                testedModule = u''
                            for purpose in (u"Creation",u"Consumption"):
                                file = io.StringIO(
                                    #'<?xml version="1.0" encoding="UTF-8"?>'
                                    u'<!-- Copyright 2011 XBRL International.  All Rights Reserved. -->'
                                    u'<?xml-stylesheet type="text/xsl" href="../../../infrastructure/test.xsl"?>'
                                    u'<testcase '
                                    u' xmlns="http://xbrl.org/2008/conformance"'
                                    u' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                                    u' xsi:schemaLocation="http://xbrl.org/2008/conformance ../../../infrastructure/test.xsd">'
                                    u'<creator>'
                                    u'<name>Roland Hommes</name>'
                                    u'<email>roland@rhocon.nl</email>'
                                    u'</creator>'
                                    u'{0}'
                                    u'<name>{1}</name>'
                                    # '<description>{0}</description>'
                                    u'<reference>'
                                    u'{2}'
                                    u'{3}'
                                    u'</reference>'
                                    u'</testcase>'.format(testcaseNumberElement,
                                                         testcaseName,
                                                         u'<name>{0}</name>'.format(testedModule) if testedModule else u'',
                                                         u'<id>{0}</id>'.format(useCase) if useCase else u'')
                                    
                                    )
                                doc = etree.parse(file)
                                file.close()
                                testcaseDocs.append(doc)
                                testcaseElements.append(doc.getroot())
                            priorTestcasesDir = testcasesDir
                            variationSeq = 1
                        try:
                            os.makedirs(os.path.dirname(reportFullPath))
                        except WindowsError:
                            pass # dir already exists
                        modelVersReport = ModelVersReport.ModelVersReport(modelTestcases)
                        modelVersReport.diffDTSes(reportFullPath,modelDTSfrom, modelDTSto, 
                                                  assignment=assignment,
                                                  schemaDir=schemaDir)
                        
                        # check for expected elements
                        if expectedEvents:
                            for expectedEvent in expectedEvents.split(u","):
                                if expectedEvent not in (u"No change", u"N.A."):
                                    prefix, sep, localName = expectedEvent.partition(u':')
                                    if sep and len(modelVersReport.xmlDocument.findall(
                                                        u'//{{{0}}}{1}'.format(
                                                            XbrlConst.verPrefixNS.get(prefix),
                                                            localName))) == 0:
                                        modelTestcases.warning(u"warning",
                                            u"Generated test case %(reportName)s missing expected event %(event)s",
                                            reportName=reportName, 
                                            event=expectedEvent)
                        
                        modelVersReport.close()
                        uriFromParts = uriFrom.split(u'_')
                        if len(uriFromParts) >= 2:
                            variationId = uriFromParts[1]
                        else:
                            variationId = u"_{0:02n}".format(variationSeq)
                        for i,testcaseElt in enumerate(testcaseElements):
                            variationElement = etree.SubElement(testcaseElt, u"{http://xbrl.org/2008/conformance}variation", 
                                                                attrib={u"id": variationId})
                            nameElement = etree.SubElement(variationElement, u"{http://xbrl.org/2008/conformance}description")
                            nameElement.text = description
                            u''' (removed per RH 2011/10/04
                            if note:
                                paramElement = etree.SubElement(variationElement, "{http://xbrl.org/2008/conformance}description")
                                paramElement.text = "Note: " + note
                            if useCase:
                                paramElement = etree.SubElement(variationElement, "{http://xbrl.org/2008/conformance}reference")
                                paramElement.set("specification", "versioning-requirements")
                                paramElement.set("useCase", useCase)
                            '''
                            dataElement = etree.SubElement(variationElement, u"{http://xbrl.org/2008/conformance}data")
                            if i == 0:  # result is report
                                if expectedEvents:
                                    paramElement = etree.SubElement(dataElement, u"{http://xbrl.org/2008/conformance}parameter",
                                                                    attrib={u"name":u"expectedEvent",
                                                                            u"value":expectedEvents.replace(u',',u' ')},
                                                                    nsmap={u"conf":u"http://xbrl.org/2008/conformance",
                                                                           None:u""})
                                if assignment:
                                    paramElement = etree.SubElement(dataElement, u"{http://xbrl.org/2008/conformance}parameter",
                                                                    attrib={u"name":u"assignment",
                                                                            u"value":assignment},
                                                                    nsmap={u"conf":u"http://xbrl.org/2008/conformance",
                                                                           None:u""})
                            for schemaURIs, dtsAttr in ((uriFrom,u"from"), (uriTo,u"to")):
                                for schemaURI in schemaURIs.split(u","): 
                                    schemaElement = etree.SubElement(dataElement, u"{http://xbrl.org/2008/conformance}schema")
                                    schemaElement.set(u"dts",dtsAttr)
                                    if i == 0:
                                        schemaElement.set(u"readMeFirst",u"true")
                                    schemaElement.text=os.path.basename(schemaURI.strip())
                            resultElement = etree.SubElement(variationElement, u"{http://xbrl.org/2008/conformance}result")
                            reportElement = etree.SubElement(resultElement if i == 0 else dataElement, 
                                             u"{http://xbrl.org/2008/conformance}versioningReport")
                            if i == 1:
                                reportElement.set(u"readMeFirst",u"true")
                            reportElement.text = u"report/" + reportName
                        variationSeq += 1
            except Exception, err:
                modelTestcases.error(u"exception",
                    _(u"Exception: %(error)s, Excel row: %(excelRow)s"),
                    error=err,
                    excelRow=iRow, 
                    exc_info=True)
        
        # add tests-error-code index files to consumption
        for testcaseFile in self.testcaseFiles(testGenDir + os.sep + u"tests-error-code"):
            etree.SubElement(testcasesElements[1], u"testcase", 
                             attrib={u"uri": 
                             testcaseFile[len(testGenDir)+1:].replace(u"\\",u"/")} )

        with open(logMessagesFile, u"w") as fh:
            fh.writelines(self.logMessages)

        if priorTestcasesDir:
            for i,testcaseFile in enumerate(testcaseFiles):
                with open(testcaseFile, u"w", encoding=u"utf-8") as fh:
                    XmlUtil.writexml(fh, testcaseDocs[i], encoding=u"utf-8")
        for i,indexFile in enumerate(indexFiles):
            with open(indexFile, u"w", encoding=u"utf-8") as fh:
                XmlUtil.writexml(fh, indexDocs[i], encoding=u"utf-8")
                
    def testcaseFiles(self, dir, files=None):
        if files is None: files = []
        for file in os.listdir(dir):
            path = dir + os.sep + file
            if path.endswith(u".svn"):
                continue
            if path.endswith(u"-testcase.xml"):
                files.append(path)
            elif os.path.isdir(path): 
                self.testcaseFiles(path, files)
        return files
    
    def runFromXml(self):
        testGenFileName = ur"C:\Users\Herm Fischer\Documents\mvsl\projects\Arelle\roland test cases\1000-Concepts\index.xml"
        filesource = FileSource.FileSource(testGenFileName)
        startedAt = time.time()
        LogHandler(self) # start logger
        modelTestcases = self.modelManager.load(filesource, _(u"views loading"))
        self.addToLog(_(u"[info] loaded in {0:.2} secs").format(time.time() - startedAt))
        if modelTestcases.modelDocument.type == ModelDocument.Type.TESTCASESINDEX:
            for testcasesElement in modelTestcases.modelDocument.iter(tag=u"testcases"):
                rootAttr = testcasesElement.get(u"root")
                title = testcasesElement.get(u"title")
                self.addToLog(_(u"[info] testcases {0}").format(title))
                if rootAttr is not None:
                    base = os.path.join(os.path.dirname(modelTestcases.modelDocument.filepath),rootAttr) + os.sep
                else:
                    base = self.filepath
                for testcaseElement in testcasesElement.iterchildren(tag=u"testcase"):
                    uriFrom = testcaseElement.get(u"uriFrom")
                    uriTo = testcaseElement.get(u"uriTo")
                    modelDTSfrom = modelDTSto = None
                    self.addToLog(_(u"[info] testcase uriFrom {0}").format(uriFrom))
                    if uriFrom is not None and uriTo is not None:
                        modelDTSfrom = ModelXbrl.load(modelTestcases.modelManager, 
                                                   uriFrom,
                                                   _(u"loading from DTS"), 
                                                   base=base)
                        modelDTSto = ModelXbrl.load(modelTestcases.modelManager, 
                                                   uriTo,
                                                   _(u"loading to DTS"), 
                                                   base=base)
                        if modelDTSfrom is not None and modelDTSto is not None:
                            # generate differences report
                            reportName = os.path.basename(uriFrom).replace(u"from.xsd",u"report.xml")
                            reportFile = os.path.dirname(uriFrom) + u"\\report\\" + reportName
                            reportFullPath = self.webCache.normalizeUrl(
                                                reportFile, 
                                                base)
                            try:
                                os.makedirs(os.path.dirname(reportFullPath))
                            except WindowsError:
                                pass # dir already exists
                            ModelVersReport.ModelVersReport(modelTestcases).diffDTSes(
                                          reportFullPath,
                                          modelDTSfrom, modelDTSto)

    def addToLog(self, message):
        self.logMessages.append(message + u'\n')
        print message
    
    def showStatus(self, message, clearAfter=None):
        pass

class LogHandler(logging.Handler):
    def __init__(self, cntlr):
        super(LogHandler, self).__init__()
        self.cntlr = cntlr
        self.level = logging.DEBUG
        formatter = logging.Formatter(u"[%(messageCode)s] %(message)s - %(file)s %(sourceLine)s")
        self.setFormatter(formatter)
        logging.getLogger(u"arelle").addHandler(self)
    def flush(self):
        u''' Nothing to flush '''
    def emit(self, logRecord):
        self.cntlr.addToLog(self.format(logRecord))      

if __name__ == u"__main__":
    main()
