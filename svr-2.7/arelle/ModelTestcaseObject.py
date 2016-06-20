u'''
Created on Oct 5, 2010
Refactored from ModelObject on Jun 11, 2011

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from __future__ import with_statement
import os, io, logging
from arelle import XmlUtil, XbrlConst, ModelValue
from arelle.ModelObject import ModelObject
from arelle.PluginManager import pluginClassMethods

class ModelTestcaseVariation(ModelObject):
    def init(self, modelDocument):
        super(ModelTestcaseVariation, self).init(modelDocument)
        self.status = u""
        self.actual = []
        self.assertions = None
        
    @property
    def id(self):
        # if there is a real ID, use it
        id = super(ModelTestcaseVariation, self).id
        if id is not None:
            return id
        # no ID, use the object ID so it isn't None
        return self.objectId()

    @property
    def name(self):
        try:
            return self._name
        except AttributeError:
            if self.get(u"name"):
                self._name = self.get(u"name")
            else:
                nameElement = XmlUtil.descendant(self, None, u"name" if self.localName != u"testcase" else u"number")
                if nameElement is not None:
                    self._name = XmlUtil.innerText(nameElement)
                else:
                    self._name = None
            return self._name

    @property
    def description(self):
        nameElement = XmlUtil.descendant(self, None, (u"description", u"documentation"))
        if nameElement is not None:
            return XmlUtil.innerText(nameElement)
        return None

    @property
    def reference(self):
        efmNameElts = XmlUtil.children(self.getparent(), None, u"name")
        for efmNameElt in efmNameElts:
            if efmNameElt is not None and efmNameElt.text.startswith(u"EDGAR"):
                return efmNameElt.text
        referenceElement = XmlUtil.descendant(self, None, u"reference")
        if referenceElement is not None: # formula test suite
            return u"{0}#{1}".format(referenceElement.get(u"specification"), referenceElement.get(u"id"))
        referenceElement = XmlUtil.descendant(self, None, u"documentationReference")
        if referenceElement is not None: # w3c test suite
            return referenceElement.get(u"{http://www.w3.org/1999/xlink}href")
        descriptionElement = XmlUtil.descendant(self, None, u"description")
        if descriptionElement is not None and descriptionElement.get(u"reference"):
            return descriptionElement.get(u"reference")  # xdt test suite
        if self.getparent().get(u"description"):
            return self.getparent().get(u"description")  # base spec 2.1 test suite
        functRegistryRefElt = XmlUtil.descendant(self.getparent(), None, u"reference")
        if functRegistryRefElt is not None: # function registry
            return functRegistryRefElt.get(u"{http://www.w3.org/1999/xlink}href")
        return None
    
    @property
    def readMeFirstUris(self):
        try:
            return self._readMeFirstUris
        except AttributeError:
            self._readMeFirstUris = []
            # first look if any plugin method to get readme first URIs
            if not any(pluginXbrlMethod(self)
                       for pluginXbrlMethod in pluginClassMethods(u"ModelTestcaseVariation.ReadMeFirstUris")):
                if self.localName == u"testGroup":  #w3c testcase
                    instanceTestElement = XmlUtil.descendant(self, None, u"instanceTest")
                    if instanceTestElement is not None: # take instance first
                        self._readMeFirstUris.append(XmlUtil.descendantAttr(instanceTestElement, None, 
                                                                            u"instanceDocument", 
                                                                            u"{http://www.w3.org/1999/xlink}href"))
                    else:
                        schemaTestElement = XmlUtil.descendant(self, None, u"schemaTest")
                        if schemaTestElement is not None:
                            self._readMeFirstUris.append(XmlUtil.descendantAttr(schemaTestElement, None, 
                                                                                u"schemaDocument", 
                                                                                u"{http://www.w3.org/1999/xlink}href"))
                elif self.localName == u"test-case":  #xpath testcase
                    inputFileElement = XmlUtil.descendant(self, None, u"input-file")
                    if inputFileElement is not None: # take instance first
                        self._readMeFirstUris.append(u"TestSources/" + inputFileElement.text + u".xml")
                else:
                    # default built-in method for readme first uris
                    for anElement in self.iterdescendants():
                        if isinstance(anElement,ModelObject) and anElement.get(u"readMeFirst") == u"true":
                            if anElement.get(u"{http://www.w3.org/1999/xlink}href"):
                                uri = anElement.get(u"{http://www.w3.org/1999/xlink}href")
                            else:
                                uri = XmlUtil.innerText(anElement)
                            if anElement.get(u"name"):
                                self._readMeFirstUris.append( (ModelValue.qname(anElement, anElement.get(u"name")), uri) )
                            elif anElement.get(u"dts"):
                                self._readMeFirstUris.append( (anElement.get(u"dts"), uri) )
                            else:
                                self._readMeFirstUris.append(uri)
            if not self._readMeFirstUris:  # provide a dummy empty instance document
                self._readMeFirstUris.append(os.path.join(self.modelXbrl.modelManager.cntlr.configDir, u"empty-instance.xml"))
            return self._readMeFirstUris
    
    @property
    def parameters(self):
        try:
            return self._parameters
        except AttributeError:
            self._parameters = dict([
                (ModelValue.qname(paramElt, paramElt.get(u"name")), # prefix-less parameter names take default namespace of element 
                 (ModelValue.qname(paramElt, paramElt.get(u"datatype")),paramElt.get(u"value"))) 
                for paramElt in XmlUtil.descendants(self, self.namespaceURI, u"parameter")])
            return self._parameters
    
    @property
    def resultIsVersioningReport(self):
        return XmlUtil.descendant(XmlUtil.descendant(self, None, u"result"), None, u"versioningReport") is not None
        
    @property
    def versioningReportUri(self):
        return XmlUtil.text(XmlUtil.descendant(self, None, u"versioningReport"))

    @property
    def resultIsXbrlInstance(self):
        return XmlUtil.descendant(XmlUtil.descendant(self, None, u"result"), None, u"instance") is not None
        
    @property
    def resultXbrlInstanceUri(self):
        resultInstance = XmlUtil.descendant(XmlUtil.descendant(self, None, u"result"), None, u"instance")
        if resultInstance is not None:
            return XmlUtil.text(resultInstance)
        return None
    
    @property
    def resultIsInfoset(self):
        if self.modelDocument.outpath:
            result = XmlUtil.descendant(self, None, u"result")
            if result is not None:
                return XmlUtil.child(result, None, u"file") is not None or XmlUtil.text(result).endswith(u".xml")
        return False
        
    @property
    def resultInfosetUri(self):
        result = XmlUtil.descendant(self, None, u"result")
        if result is not None:
            child = XmlUtil.child(result, None, u"file")
            return os.path.join(self.modelDocument.outpath, XmlUtil.text(child if child is not None else result))
        return None    
    
    @property
    def resultIsTable(self):
        result = XmlUtil.descendant(self, None, u"result")
        if result is not None :
            child = XmlUtil.child(result, None, u"table")
            return child is not None and XmlUtil.text(child).endswith(u".xml")
        return False
        
    @property
    def resultTableUri(self):
        result = XmlUtil.descendant(self, None, u"result")
        if result is not None:
            child = XmlUtil.child(result, None, u"table")
            return os.path.join(self.modelDocument.outpath, XmlUtil.text(child if child is not None else result))
        return None    
    
    @property
    def cfcnCall(self):
        # tuple of (expression, element holding the expression)
        try:
            return self._cfcnCall
        except AttributeError:
            self._cfcnCall = None
            if self.localName == u"test-case":  #xpath testcase
                queryElement = XmlUtil.descendant(self, None, u"query")
                if queryElement is not None: 
                    filepath = (self.modelDocument.filepathdir + u"/" + u"Queries/XQuery/" +
                                self.get(u"FilePath") + queryElement.get(u"name") + u'.xq')
                    if os.sep != u"/": filepath = filepath.replace(u"/", os.sep)
                    with io.open(filepath, u'rt', encoding=u'utf-8') as f:
                        self._cfcnCall = (f.read(), self)
            else:
                for callElement in XmlUtil.descendants(self, XbrlConst.cfcn, u"call"):
                    self._cfcnCall = (XmlUtil.innerText(callElement), callElement)
                    break
            if self._cfcnCall is None and self.namespaceURI == u"http://xbrl.org/2011/conformance-rendering/transforms":
                name = self.getparent().get(u"name")
                input = self.get(u"input")
                if name and input:
                    self._cfcnCall =  (u"{0}('{1}')".format(name, input.replace(u"'",u"''")), self)
            return self._cfcnCall
    
    @property
    def cfcnTest(self):
        # tuple of (expression, element holding the expression)
        try:
            return self._cfcnTest
        except AttributeError:
            self._cfcnTest = None
            if self.localName == u"test-case":  #xpath testcase
                outputFileElement = XmlUtil.descendant(self, None, u"output-file")
                if outputFileElement is not None and outputFileElement.get(u"compare") == u"Text": 
                    filepath = (self.modelDocument.filepathdir + u"/" + u"ExpectedTestResults/" +
                                self.get(u"FilePath") + outputFileElement.text)
                    if os.sep != u"/": filepath = filepath.replace(u"/", os.sep)
                    with io.open(filepath, u'rt', encoding=u'utf-8') as f:
                        self._cfcnTest = (u"xs:string($result) eq '{0}'".format(f.read()), self)
            else:
                testElement = XmlUtil.descendant(self, XbrlConst.cfcn, u"test")
                if testElement is not None:
                    self._cfcnTest = (XmlUtil.innerText(testElement), testElement)
                elif self.namespaceURI == u"http://xbrl.org/2011/conformance-rendering/transforms":
                    output = self.get(u"output")
                    if output:
                        self._cfcnTest =  (u"$result eq '{0}'".format(output.replace(u"'",u"''")), self)
            return self._cfcnTest
    
    @property
    def expected(self):
        for pluginXbrlMethod in pluginClassMethods(u"ModelTestcaseVariation.ExpectedResult"):
            expected = pluginXbrlMethod(self)
            if expected:
                return expected
        # default behavior without plugins
        if self.localName == u"testcase":
            return self.document.basename[:4]   #starts with PASS or FAIL
        elif self.localName == u"testGroup":  #w3c testcase
            instanceTestElement = XmlUtil.descendant(self, None, u"instanceTest")
            if instanceTestElement is not None: # take instance first
                return XmlUtil.descendantAttr(instanceTestElement, None, u"expected", u"validity")
            else:
                schemaTestElement = XmlUtil.descendant(self, None, u"schemaTest")
                if schemaTestElement is not None:
                    return XmlUtil.descendantAttr(schemaTestElement, None, u"expected", u"validity")
        errorElement = XmlUtil.descendant(self, None, u"error")
        if errorElement is not None:
            return ModelValue.qname(errorElement, XmlUtil.text(errorElement))
        resultElement = XmlUtil.descendant(self, None, u"result")
        if resultElement is not None:
            expected = resultElement.get(u"expected")
            if expected:
                return expected
            for assertElement in XmlUtil.children(resultElement, None, u"assert"):
                num = assertElement.get(u"num")
                if len(num) == 5:
                    return u"EFM.{0}.{1}.{2}".format(num[0],num[1:3],num[3:6])
            asserTests = {}
            for atElt in XmlUtil.children(resultElement, None, u"assertionTests"):
                try:
                    asserTests[atElt.get(u"assertionID")] = (_INT(atElt.get(u"countSatisfied")),_INT(atElt.get(u"countNotSatisfied")))
                except ValueError:
                    pass
            if asserTests:
                return asserTests
        elif self.get(u"result"):
            return self.get(u"result")
                
        return None
    
    @property
    def severityLevel(self):
        for pluginXbrlMethod in pluginClassMethods(u"ModelTestcaseVariation.ExpectedSeverity"):
            severityLevelName = pluginXbrlMethod(self)
            if severityLevelName: # ignore plug in if not a plug-in-recognized test case
                return logging._checkLevel(severityLevelName)
        # default behavior without plugins
        # SEC error cases have <assert severity={err|wrn}>...
        if XmlUtil.descendant(self, None, u"assert", attrName=u"severity", attrValue=u"wrn") is not None:
            return logging._checkLevel(u"WARNING")
        return logging._checkLevel(u"INCONSISTENCY")

    @property
    def expectedVersioningReport(self):
        XmlUtil.text(XmlUtil.text(XmlUtil.descendant(XmlUtil.descendant(self, None, u"result"), None, u"versioningReport")))

    @property
    def propertyView(self):
        assertions = []
        for assertionElement in XmlUtil.descendants(self, None, u"assertionTests"):
            assertions.append((u"assertion",assertionElement.get(u"assertionID")))
            assertions.append((u"   satisfied", assertionElement.get(u"countSatisfied")))
            assertions.append((u"   not sat.", assertionElement.get(u"countNotSatisfied")))
        u'''
        for assertionElement in XmlUtil.descendants(self, None, "assert"):
            efmNum = assertionElement.get("num")
            assertions.append(("assertion",
                               "EFM.{0}.{1}.{2}".format(efmNum[0], efmNum[1:2], efmNum[3:4])))
            assertions.append(("   not sat.", "1"))
        '''
        readMeFirsts = [(u"readFirst", readMeFirstUri) for readMeFirstUri in self.readMeFirstUris]
        parameters = []
        if len(self.parameters) > 0: parameters.append((u"parameters", None))
        for pName, pTypeValue in self.parameters.items():
            parameters.append((pName,pTypeValue[1]))
        return [(u"id", self.id),
                (u"name", self.name),
                (u"description", self.description)] + \
                readMeFirsts + \
                parameters + \
               [(u"status", self.status),
                (u"call", self.cfcnCall[0]) if self.cfcnCall else (),
                (u"test", self.cfcnTest[0]) if self.cfcnTest else (),
                (u"infoset", self.resultInfosetUri) if self.resultIsInfoset else (),
                (u"expected", self.expected) if self.expected else (),
                (u"actual", u" ".join(unicode(i) for i in self.actual) if len(self.actual) > 0 else ())] + \
                assertions
        
    def __repr__(self):
        return (u"modelTestcaseVariation[{0}]{1})".format(self.objectId(),self.propertyView))
