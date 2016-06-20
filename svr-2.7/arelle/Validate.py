u'''
Created on Oct 17, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
import os, sys, traceback
from collections import defaultdict
from arelle import (ModelXbrl, ModelVersReport, XbrlConst, 
               ValidateXbrl, ValidateFiling, ValidateHmrc, ValidateVersReport, ValidateFormula,
               ValidateInfoset, RenderingEvaluator, ViewFileRenderedGrid)
from arelle.ModelDocument import Type, ModelDocumentReference, load as modelDocumentLoad
from arelle.ModelValue import (qname, QName)
from arelle.PluginManager import pluginClassMethods

def validate(modelXbrl):
    validate = Validate(modelXbrl)
    validate.validate()

class ValidationException(Exception):
    def __init__(self, message, severity, code):
        self.message = message
        self.severity = severity
        self.code = code
    def __repr__(self):
        return u"{0}({1})={2}".format(self.code,self.severity,self.message)
    
class Validate(object):
    u"""Validation operations are separated from the objects that are validated, because the operations are 
    complex, interwoven, and factored quite differently than the objects being validated. 
    There are these validation modules at present: validation infrastructure, test suite and submission control, 
    versioning report validation, XBRL base spec, dimensions, and formula linkbase validation, 
    Edgar and Global Filer Manual validation. 
    """
    def __init__(self, modelXbrl):
        self.modelXbrl = modelXbrl
        if modelXbrl.modelManager.validateDisclosureSystem:
            if modelXbrl.modelManager.disclosureSystem.HMRC:
                self.instValidator = ValidateHmrc.ValidateHmrc(modelXbrl)
            elif modelXbrl.modelManager.disclosureSystem.EFMorGFM or modelXbrl.modelManager.disclosureSystem.SBRNL:
                self.instValidator = ValidateFiling.ValidateFiling(modelXbrl)
            else: # custom validator, probably a plug-in
                self.instValidator = ValidateXbrl.ValidateXbrl(modelXbrl)
            self.formulaValidator = ValidateXbrl.ValidateXbrl(modelXbrl)
        else:
            self.instValidator = ValidateXbrl.ValidateXbrl(modelXbrl)
            self.formulaValidator = self.instValidator
        if hasattr(modelXbrl,u"fileSource"):
            self.useFileSource = modelXbrl.fileSource
        else:
            self.useFileSource = None
            
    def close(self):
        self.instValidator.close(reusable=False)
        self.formulaValidator.close(reusable=False)
        self.__dict__.clear()   # dereference variables
        
    def validate(self):
        if self.modelXbrl.modelDocument is None:
            self.modelXbrl.info(u"arelle:notValdated",
                _(u"Validation skipped, document not successfully loaded: %(file)s"),
                modelXbrl=self.modelXbrl, file=self.modelXbrl.modelDocument.basename)
        elif self.modelXbrl.modelDocument.type in (Type.TESTCASESINDEX, Type.REGISTRY):
            for doc in sorted(self.modelXbrl.modelDocument.referencesDocument.keys(), key=lambda doc: doc.uri):
                self.validateTestcase(doc)  # testcases doc's are sorted by their uri (file names), e.g., for formula
        elif self.modelXbrl.modelDocument.type in (Type.TESTCASE, Type.REGISTRYTESTCASE):
            try:
                self.validateTestcase(self.modelXbrl.modelDocument)
            except Exception, err:
                self.modelXbrl.error(u"exception",
                    _(u"Testcase validation exception: %(error)s, testcase: %(testcase)s"),
                    modelXbrl=self.modelXbrl,
                    testcase=self.modelXbrl.modelDocument.basename, error=err,
                    #traceback=traceback.format_tb(sys.exc_info()[2]),
                    exc_info=True)
        elif self.modelXbrl.modelDocument.type == Type.VERSIONINGREPORT:
            try:
                ValidateVersReport.ValidateVersReport(self.modelXbrl).validate(self.modelXbrl)
            except Exception, err:
                self.modelXbrl.error(u"exception",
                    _(u"Versioning report exception: %(error)s, testcase: %(reportFile)s"),
                    modelXbrl=self.modelXbrl,
                    reportFile=self.modelXbrl.modelDocument.basename, error=err,
                    #traceback=traceback.format_tb(sys.exc_info()[2]),
                    exc_info=True)
        elif self.modelXbrl.modelDocument.type == Type.RSSFEED:
            self.validateRssFeed()
        else:
            try:
                self.instValidator.validate(self.modelXbrl, self.modelXbrl.modelManager.formulaOptions.typedParameters())
                self.instValidator.close()
            except Exception, err:
                self.modelXbrl.error(u"exception",
                    _(u"Instance validation exception: %(error)s, instance: %(instance)s"),
                    modelXbrl=self.modelXbrl,
                    instance=self.modelXbrl.modelDocument.basename, error=err,
                    # traceback=traceback.format_tb(sys.exc_info()[2]),
                    exc_info=True)
        self.close()
        
    def validateRssFeed(self):
        self.modelXbrl.info(u"info", u"RSS Feed", modelDocument=self.modelXbrl)
        from arelle.FileSource import openFileSource
        for rssItem in self.modelXbrl.modelDocument.rssItems:
            if getattr(rssItem, u"skipRssItem", False):
                self.modelXbrl.info(u"info", _(u"skipping RSS Item %(accessionNumber)s %(formType)s %(companyName)s %(period)s"),
                    modelObject=rssItem, accessionNumber=rssItem.accessionNumber, formType=rssItem.formType, companyName=rssItem.companyName, period=rssItem.period)
                continue
            self.modelXbrl.info(u"info", _(u"RSS Item %(accessionNumber)s %(formType)s %(companyName)s %(period)s"),
                modelObject=rssItem, accessionNumber=rssItem.accessionNumber, formType=rssItem.formType, companyName=rssItem.companyName, period=rssItem.period)
            modelXbrl = None
            try:
                modelXbrl = ModelXbrl.load(self.modelXbrl.modelManager, 
                                           openFileSource(rssItem.zippedUrl, self.modelXbrl.modelManager.cntlr),
                                           _(u"validating"), rssItem=rssItem)
                for pluginXbrlMethod in pluginClassMethods(u"RssItem.Xbrl.Loaded"):  
                    pluginXbrlMethod(modelXbrl, {}, rssItem)      
                if getattr(rssItem, u"doNotProcessRSSitem", False) or modelXbrl.modelDocument is None:
                    modelXbrl.close()
                    continue # skip entry based on processing criteria
                self.instValidator.validate(modelXbrl, self.modelXbrl.modelManager.formulaOptions.typedParameters())
                self.instValidator.close()
                rssItem.setResults(modelXbrl)
                self.modelXbrl.modelManager.viewModelObject(self.modelXbrl, rssItem.objectId())
                for pluginXbrlMethod in pluginClassMethods(u"Validate.RssItem"):
                    pluginXbrlMethod(self, modelXbrl, rssItem)
                modelXbrl.close()
            except Exception, err:
                self.modelXbrl.error(u"exception",
                    _(u"RSS item validation exception: %(error)s, instance: %(instance)s"),
                    modelXbrl=(self.modelXbrl, modelXbrl),
                    instance=rssItem.zippedUrl, error=err,
                    exc_info=True)
                try:
                    self.instValidator.close()
                    if modelXbrl is not None:
                        modelXbrl.close()
                except Exception, err:
                    pass
            del modelXbrl  # completely dereference
   
    def validateTestcase(self, testcase):
        self.modelXbrl.info(u"info", u"Testcase", modelDocument=testcase)
        self.modelXbrl.viewModelObject(testcase.objectId())
        if hasattr(testcase, u"testcaseVariations"):
            for modelTestcaseVariation in testcase.testcaseVariations:
                # update ui thread via modelManager (running in background here)
                self.modelXbrl.modelManager.viewModelObject(self.modelXbrl, modelTestcaseVariation.objectId())
                # is this a versioning report?
                resultIsVersioningReport = modelTestcaseVariation.resultIsVersioningReport
                resultIsXbrlInstance = modelTestcaseVariation.resultIsXbrlInstance
                formulaOutputInstance = None
                inputDTSes = defaultdict(list)
                baseForElement = testcase.baseForElement(modelTestcaseVariation)
                # try to load instance document
                self.modelXbrl.info(u"info", _(u"Variation %(id)s %(name)s: %(expected)s - %(description)s"),
                                    modelObject=modelTestcaseVariation, 
                                    id=modelTestcaseVariation.id, 
                                    name=modelTestcaseVariation.name, 
                                    expected=modelTestcaseVariation.expected, 
                                    description=modelTestcaseVariation.description)
                errorCaptureLevel = modelTestcaseVariation.severityLevel # default is INCONSISTENCY
                for readMeFirstUri in modelTestcaseVariation.readMeFirstUris:
                    if isinstance(readMeFirstUri,tuple):
                        # dtsName is for formula instances, but is from/to dts if versioning
                        dtsName, readMeFirstUri = readMeFirstUri
                    elif resultIsVersioningReport:
                        if inputDTSes: dtsName = u"to"
                        else: dtsName = u"from"
                    else:
                        dtsName = None
                    if resultIsVersioningReport and dtsName: # build multi-schemaRef containing document
                        if dtsName in inputDTSes:
                            dtsName = inputDTSes[dtsName]
                        else:
                            modelXbrl = ModelXbrl.create(self.modelXbrl.modelManager, 
                                         Type.DTSENTRIES,
                                         self.modelXbrl.modelManager.cntlr.webCache.normalizeUrl(readMeFirstUri[:-4] + u".dts", baseForElement),
                                         isEntry=True,
                                         errorCaptureLevel=errorCaptureLevel)
                        DTSdoc = modelXbrl.modelDocument
                        DTSdoc.inDTS = True
                        doc = modelDocumentLoad(modelXbrl, readMeFirstUri, base=baseForElement)
                        if doc is not None:
                            DTSdoc.referencesDocument[doc] = ModelDocumentReference(u"import", DTSdoc.xmlRootElement)  #fake import
                            doc.inDTS = True
                    else: # not a multi-schemaRef versioning report
                        modelXbrl = ModelXbrl.load(self.modelXbrl.modelManager, 
                                                   readMeFirstUri,
                                                   _(u"validating"), 
                                                   base=baseForElement,
                                                   useFileSource=self.useFileSource,
                                                   errorCaptureLevel=errorCaptureLevel)
                    if modelXbrl.modelDocument is None:
                        self.modelXbrl.error(u"arelle:notLoaded",
                             _(u"Testcase %(id)s %(name)s document not loaded: %(file)s"),
                             modelXbrl=testcase, id=modelTestcaseVariation.id, name=modelTestcaseVariation.name, file=os.path.basename(readMeFirstUri))
                        modelXbrl.close()
                        self.determineNotLoadedTestStatus(modelTestcaseVariation)
                    elif resultIsVersioningReport:
                        inputDTSes[dtsName] = modelXbrl
                    elif modelXbrl.modelDocument.type == Type.VERSIONINGREPORT:
                        ValidateVersReport.ValidateVersReport(self.modelXbrl).validate(modelXbrl)
                        self.determineTestStatus(modelTestcaseVariation, modelXbrl)
                        modelXbrl.close()
                    elif testcase.type == Type.REGISTRYTESTCASE:
                        self.instValidator.validate(modelXbrl)  # required to set up dimensions, etc
                        self.instValidator.executeCallTest(modelXbrl, modelTestcaseVariation.id, 
                                   modelTestcaseVariation.cfcnCall, modelTestcaseVariation.cfcnTest)
                        self.determineTestStatus(modelTestcaseVariation, modelXbrl)
                        self.instValidator.close()
                        modelXbrl.close()
                    else:
                        inputDTSes[dtsName].append(modelXbrl)
                if resultIsVersioningReport and modelXbrl.modelDocument:
                    versReportFile = modelXbrl.modelManager.cntlr.webCache.normalizeUrl(
                        modelTestcaseVariation.versioningReportUri, baseForElement)
                    if os.path.exists(versReportFile): #validate existing
                        modelVersReport = ModelXbrl.load(self.modelXbrl.modelManager, versReportFile, _(u"validating existing version report"))
                        if modelVersReport and modelVersReport.modelDocument and modelVersReport.modelDocument.type == Type.VERSIONINGREPORT:
                            ValidateVersReport.ValidateVersReport(self.modelXbrl).validate(modelVersReport)
                            self.determineTestStatus(modelTestcaseVariation, modelVersReport)
                            modelVersReport.close()
                    elif len(inputDTSes) == 2:
                        ModelVersReport.ModelVersReport(self.modelXbrl).diffDTSes(
                              versReportFile, inputDTSes[u"from"], inputDTSes[u"to"])
                        modelTestcaseVariation.status = u"generated"
                    else:
                        self.modelXbrl.error(u"arelle:notLoaded",
                             _(u"Testcase %(id)s %(name)s DTSes not loaded, unable to generate versioning report: %(file)s"),
                             modelXbrl=testcase, id=modelTestcaseVariation.id, name=modelTestcaseVariation.name, file=os.path.basename(readMeFirstUri))
                        modelTestcaseVariation.status = u"failed"
                    for inputDTS in inputDTSes.values():
                        inputDTS.close()
                    del inputDTSes # dereference
                elif inputDTSes:
                    # validate schema, linkbase, or instance
                    modelXbrl = inputDTSes[None][0]
                    for pluginXbrlMethod in pluginClassMethods(u"TestcaseVariation.Xbrl.Loaded"):
                        pluginXbrlMethod(self.modelXbrl, modelXbrl)
                    parameters = modelTestcaseVariation.parameters.copy()
                    for dtsName, inputDTS in inputDTSes.items():  # input instances are also parameters
                        if dtsName: # named instance
                            parameters[dtsName] = (None, inputDTS) #inputDTS is a list of modelXbrl's (instance DTSes)
                        elif len(inputDTS) > 1: # standard-input-instance with multiple instance documents
                            parameters[XbrlConst.qnStandardInputInstance] = (None, inputDTS) # allow error detection in validateFormula
                    if modelXbrl.hasTableRendering or modelTestcaseVariation.resultIsTable:
                        RenderingEvaluator.init(modelXbrl)
                    try:
                        self.instValidator.validate(modelXbrl, parameters)
                    except Exception, err:
                        self.modelXbrl.error(u"exception",
                            _(u"Testcase variation validation exception: %(error)s, instance: %(instance)s"),
                            modelXbrl=modelXbrl, instance=modelXbrl.modelDocument.basename, error=err, exc_info=True)
                    if modelTestcaseVariation.resultIsInfoset and self.modelXbrl.modelManager.validateInfoset:
                        for pluginXbrlMethod in pluginClassMethods(u"Validate.Infoset"):
                            pluginXbrlMethod(modelXbrl, modelTestcaseVariation.resultInfosetUri)
                        infoset = ModelXbrl.load(self.modelXbrl.modelManager, 
                                                 modelTestcaseVariation.resultInfosetUri,
                                                   _(u"loading result infoset"), 
                                                   base=baseForElement,
                                                   useFileSource=self.useFileSource,
                                                   errorCaptureLevel=errorCaptureLevel)
                        if infoset.modelDocument is None:
                            self.modelXbrl.error(u"arelle:notLoaded",
                                _(u"Testcase %(id)s %(name)s result infoset not loaded: %(file)s"),
                                modelXbrl=testcase, id=modelTestcaseVariation.id, name=modelTestcaseVariation.name, 
                                file=os.path.basename(modelTestcaseVariation.resultXbrlInstance))
                            modelTestcaseVariation.status = u"result infoset not loadable"
                        else:   # check infoset
                            ValidateInfoset.validate(self.instValidator, modelXbrl, infoset)
                        infoset.close()
                    if modelTestcaseVariation.resultIsTable: # and self.modelXbrl.modelManager.validateInfoset:
                        # diff (or generate) table infoset
                        resultTableUri = modelXbrl.modelManager.cntlr.webCache.normalizeUrl(modelTestcaseVariation.resultTableUri, baseForElement)
                        if not any(alternativeValidation(modelXbrl, resultTableUri)
                                   for alternativeValidation in pluginClassMethods(u"Validate.TableInfoset")):
                            ViewFileRenderedGrid.viewRenderedGrid(modelXbrl, resultTableUri, diffToFile=True)  # false to save infoset files
                    self.determineTestStatus(modelTestcaseVariation, modelXbrl) # include infoset errors in status
                    self.instValidator.close()
                    if modelXbrl.formulaOutputInstance and self.noErrorCodes(modelTestcaseVariation.actual): 
                        # if an output instance is created, and no string error codes, ignoring dict of assertion results, validate it
                        modelXbrl.formulaOutputInstance.hasFormulae = False #  block formulae on output instance (so assertion of input is not lost)
                        self.instValidator.validate(modelXbrl.formulaOutputInstance, modelTestcaseVariation.parameters)
                        self.determineTestStatus(modelTestcaseVariation, modelXbrl.formulaOutputInstance)
                        if self.noErrorCodes(modelTestcaseVariation.actual): # if still 'clean' pass it forward for comparison to expected result instance
                            formulaOutputInstance = modelXbrl.formulaOutputInstance
                            modelXbrl.formulaOutputInstance = None # prevent it from being closed now
                        self.instValidator.close()
                    for inputDTSlist in inputDTSes.values():
                        for inputDTS in inputDTSlist:
                            inputDTS.close()
                    del inputDTSes # dereference
                    if resultIsXbrlInstance and formulaOutputInstance and formulaOutputInstance.modelDocument:
                        expectedInstance = ModelXbrl.load(self.modelXbrl.modelManager, 
                                                   modelTestcaseVariation.resultXbrlInstanceUri,
                                                   _(u"loading expected result XBRL instance"), 
                                                   base=baseForElement,
                                                   useFileSource=self.useFileSource,
                                                   errorCaptureLevel=errorCaptureLevel)
                        if expectedInstance.modelDocument is None:
                            self.modelXbrl.error(u"arelle:notLoaded",
                                _(u"Testcase %(id)s %(name)s expected result instance not loaded: %(file)s"),
                                modelXbrl=testcase, id=modelTestcaseVariation.id, name=modelTestcaseVariation.name, 
                                file=os.path.basename(modelTestcaseVariation.resultXbrlInstance))
                            modelTestcaseVariation.status = u"result not loadable"
                        else:   # compare facts
                            if len(expectedInstance.facts) != len(formulaOutputInstance.facts):
                                formulaOutputInstance.error(u"formula:resultFactCounts",
                                    _(u"Formula output %(countFacts)s facts, expected %(expectedFacts)s facts"),
                                    modelXbrl=modelXbrl, countFacts=len(formulaOutputInstance.facts),
                                         expectedFacts=len(expectedInstance.facts))
                            else:
                                for fact in expectedInstance.facts:
                                    unmatchedFactsStack = []
                                    if formulaOutputInstance.matchFact(fact, unmatchedFactsStack, deemP0inf=True) is None:
                                        if unmatchedFactsStack: # get missing nested tuple fact, if possible
                                            missingFact = unmatchedFactsStack[-1]
                                        else:
                                            missingFact = fact
                                        formulaOutputInstance.error(u"formula:expectedFactMissing",
                                            _(u"Formula output missing expected fact %(fact)s"),
                                            modelXbrl=missingFact, fact=missingFact.qname)
                            # for debugging uncomment next line to save generated instance document
                            # formulaOutputInstance.saveInstance(r"c:\temp\test-out-inst.xml")
                        expectedInstance.close()
                        del expectedInstance # dereference
                        self.determineTestStatus(modelTestcaseVariation, formulaOutputInstance)
                        formulaOutputInstance.close()
                        del formulaOutputInstance
                # update ui thread via modelManager (running in background here)
                self.modelXbrl.modelManager.viewModelObject(self.modelXbrl, modelTestcaseVariation.objectId())
                    
            self.modelXbrl.modelManager.showStatus(_(u"ready"), 2000)
            
    def noErrorCodes(self, modelTestcaseVariation):
        return not any(not isinstance(actual,dict) for actual in modelTestcaseVariation)
                
    def determineTestStatus(self, modelTestcaseVariation, modelUnderTest):
        numErrors = len(modelUnderTest.errors)
        expected = modelTestcaseVariation.expected
        if expected == u"valid":
            if numErrors == 0:
                status = u"pass"
            else:
                status = u"fail"
        elif expected == u"invalid":
            if numErrors == 0:
                status = u"fail"
            else:
                status = u"pass"
        elif expected is None and numErrors == 0:
            status = u"pass"
        elif isinstance(expected,(QName,_STR_BASE,dict)): # string or assertion id counts dict
            status = u"fail"
            for testErr in modelUnderTest.errors:
                if isinstance(expected,QName) and isinstance(testErr,_STR_BASE):
                    errPrefix, sep, errLocalName = testErr.partition(u":")
                    if ((not sep and errPrefix == expected.localName) or
                        (expected == qname(XbrlConst.errMsgPrefixNS.get(errPrefix), errLocalName)) or
                        # XDT xml schema tests expected results 
                        (expected.namespaceURI == XbrlConst.xdtSchemaErrorNS and errPrefix == u"xmlSchema")):
                        status = u"pass"
                        break
                elif type(testErr) == type(expected):
                    if (testErr == expected or
                        (isinstance(expected, _STR_BASE) and (
                         (expected == u"EFM.6.03.04" and testErr.startswith(u"xmlSchema:")) or
                         (expected == u"EFM.6.03.05" and (testErr.startswith(u"xmlSchema:") or testErr == u"EFM.5.02.01.01")) or
                         (expected == u"EFM.6.04.03" and (testErr.startswith(u"xmlSchema:") or testErr.startswith(u"utr:") or testErr.startswith(u"xbrl.") or testErr.startswith(u"xlink:"))) or
                         (expected == u"EFM.6.05.35" and testErr.startswith(u"utre:")) or
                         (expected.startswith(u"EFM.") and testErr.startswith(expected)) or
                         (expected == u"vere:invalidDTSIdentifier" and testErr.startswith(u"xbrl"))))):
                        status = u"pass"
                        break
            if expected == u"EFM.6.03.02" or expected == u"EFM.6.03.08": # 6.03.02 is not testable
                status = u"pass"
            if not modelUnderTest.errors and status == u"fail":
                if modelTestcaseVariation.assertions:
                    if modelTestcaseVariation.assertions == expected:
                        status = u"pass" # passing was previously successful and no further errors
                elif (isinstance(expected,dict) and # no assertions fired, are all the expected zero counts?
                      all(countSatisfied == 0 and countNotSatisfied == 0 for countSatisfied, countNotSatisfied in expected.values())):
                    status = u"pass" # passes due to no counts expected
                         
        else:
            status = u"fail"
        modelTestcaseVariation.status = status
        modelTestcaseVariation.actual = []
        if numErrors > 0: # either coded errors or assertions (in errors list)
            # put error codes first, sorted, then assertion result (dict's)
            for error in modelUnderTest.errors:
                if isinstance(error,dict):  # asserion results
                    modelTestcaseVariation.assertions = error
                else:   # error code results
                    modelTestcaseVariation.actual.append(error)
            modelTestcaseVariation.actual.sort(key=lambda d: unicode(d))
            for error in modelUnderTest.errors:
                if isinstance(error,dict):
                    modelTestcaseVariation.actual.append(error)
                
    def determineNotLoadedTestStatus(self, modelTestcaseVariation):
        expected = modelTestcaseVariation.expected
        status = u"not loadable"
        if expected in (u"EFM.6.03.04", u"EFM.6.03.05"):
            status = u"pass"
        modelTestcaseVariation.status = status
                
import logging
class ValidationLogListener(logging.Handler):
    def __init__(self, logView):
        self.logView = logView
        self.level = logging.DEBUG
    def flush(self):
        u''' Nothing to flush '''
    def emit(self, logRecord):
        # add to logView        
        msg = self.format(logRecord)        
        try:            
            self.logView.append(msg)
        except:
            pass
