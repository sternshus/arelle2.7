u'''
Created on Nov 28, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from arelle import ModelDocument, ViewFile
import os

def viewTests(modelXbrl, outfile, cols=None):
    modelXbrl.modelManager.showStatus(_(u"viewing Tests"))
    view = ViewTests(modelXbrl, outfile, cols)
    view.viewTestcaseIndexElement(modelXbrl.modelDocument)
    view.close()
    
class ViewTests(ViewFile.View):
    def __init__(self, modelXbrl, outfile, cols):
        super(ViewTests, self).__init__(modelXbrl, outfile, u"Tests")
        self.cols = cols
        
    def viewTestcaseIndexElement(self, modelDocument):
        if self.cols:
            if isinstance(self.cols,unicode): self.cols = self.cols.replace(u',',u' ').split()
            unrecognizedCols = []
            for col in self.cols:
                if col not in (u"Index", u"Testcase", u"ID", u"Name", u"Reference", u"ReadMeFirst", u"Status", u"Expected",u"Actual"):
                    unrecognizedCols.append(col)
            if unrecognizedCols:
                self.modelXbrl.error(u"arelle:unrecognizedTestReportColumn",
                                     _(u"Unrecognized columns: %(cols)s"),
                                     modelXbrl=self.modelXbrl, cols=u','.join(unrecognizedCols))
            if u"Period" in self.cols:
                i = self.cols.index(u"Period")
                self.cols[i:i+1] = [u"Start", u"End/Instant"]
        else:
            self.cols = [u"Index", u"Testcase", u"ID", u"Name", u"ReadMeFirst", u"Status", u"Expected", u"Actual"]
        
        self.addRow(self.cols, asHeader=True)

        if modelDocument.type in (ModelDocument.Type.TESTCASESINDEX, ModelDocument.Type.REGISTRY):
            cols = []
            for col in self.cols:
                if col == u"Index":
                    cols.append(os.path.basename(modelDocument.uri))
                    break
                else:
                    cols.append(u"")
            self.addRow(cols)
            # sort test cases by uri
            testcases = []
            for referencedDocument in modelDocument.referencesDocument.keys():
                testcases.append((referencedDocument.uri, referencedDocument.objectId()))
            testcases.sort()
            for testcaseTuple in testcases:
                self.viewTestcase(self.modelXbrl.modelObject(testcaseTuple[1]))
        elif modelDocument.type in (ModelDocument.Type.TESTCASE, ModelDocument.Type.REGISTRYTESTCASE):
            self.viewTestcase(modelDocument)
        else:
            pass
                
    def viewTestcase(self, modelDocument):
        cols = []
        for col in self.cols:
            if col == u"Testcase":
                cols.append(os.path.basename(modelDocument.uri))
                break
            else:
                cols.append(u"")
        self.addRow(cols, xmlRowElementName=u"testcase")
        if hasattr(modelDocument, u"testcaseVariations"):
            for modelTestcaseVariation in modelDocument.testcaseVariations:
                self.viewTestcaseVariation(modelTestcaseVariation)
                
    def viewTestcaseVariation(self, modelTestcaseVariation):
        id = modelTestcaseVariation.id
        if id is None:
            id = u""
        cols = []
        for col in self.cols:
            if col == u"ID":
                cols.append(id or modelTestcaseVariation.name)
            elif col == u"Name":
                cols.append(modelTestcaseVariation.description or modelTestcaseVariation.name)
            elif col == u"Reference":
                cols.append(modelTestcaseVariation.reference)
            elif col == u"ReadMeFirst":
                cols.append(u" ".join(unicode(uri) for uri in modelTestcaseVariation.readMeFirstUris))
            elif col == u"Status":
                cols.append(modelTestcaseVariation.status)
            elif col == u"Expected":
                cols.append(modelTestcaseVariation.expected)
            elif col == u"Actual":
                cols.append(u" ".join(unicode(code) for code in modelTestcaseVariation.actual))
            else:
                cols.append(u"")
        self.addRow(cols, xmlRowElementName=u"variation")
