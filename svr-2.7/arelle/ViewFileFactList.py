u'''
Created on Jan 10, 2011

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
from arelle import ViewFile, XbrlConst, XmlUtil
from collections import defaultdict

def viewFacts(modelXbrl, outfile, lang=None, labelrole=None, cols=None):
    modelXbrl.modelManager.showStatus(_(u"viewing facts"))
    view = ViewFacts(modelXbrl, outfile, labelrole, lang, cols)
    view.view(modelXbrl.modelDocument)
    view.close()
    
class ViewFacts(ViewFile.View):
    def __init__(self, modelXbrl, outfile, labelrole, lang, cols):
        super(ViewFacts, self).__init__(modelXbrl, outfile, u"Fact List", lang)
        self.labelrole = labelrole
        self.cols = cols

    def view(self, modelDocument):
        if self.cols:
            if isinstance(self.cols,unicode): self.cols = self.cols.replace(u',',u' ').split()
            unrecognizedCols = []
            for col in self.cols:
                if col not in (u"Label",u"Name",u"contextRef",u"unitRef",u"Dec",u"Prec",u"Lang",u"Value",u"EntityScheme",u"EntityIdentifier",u"Period",u"Dimensions"):
                    unrecognizedCols.append(col)
            if unrecognizedCols:
                self.modelXbrl.error(u"arelle:unrecognizedFactListColumn",
                                     _(u"Unrecognized columns: %(cols)s"),
                                     modelXbrl=self.modelXbrl, cols=u','.join(unrecognizedCols))
            if u"Period" in self.cols:
                i = self.cols.index(u"Period")
                self.cols[i:i+1] = [u"Start", u"End/Instant"]
        else:
            self.cols = [u"Label",u"contextRef",u"unitRef",u"Dec",u"Prec",u"Lang",u"Value"]
        col0 = self.cols[0]
        if col0 not in (u"Label", u"Name"):
            self.modelXbrl.error(u"arelle:firstFactListColumn",
                                 _(u"First column must be Label or Name: %(col1)s"),
                                 modelXbrl=self.modelXbrl, col1=col0)
        self.isCol0Label = col0 == u"Label"
        self.maxNumDims = 1
        self.tupleDepth(self.modelXbrl.facts, 0)
        if u"Dimensions" == self.cols[-1]:
            lastColSpan = self.maxNumDims
        else:
            lastColSpan = None
        self.addRow(self.cols, asHeader=True, lastColSpan=lastColSpan)
        self.viewFacts(self.modelXbrl.facts, 0)
        
    def tupleDepth(self, modelFacts, indentedCol):
        if indentedCol > self.treeCols: self.treeCols = indentedCol
        for modelFact in modelFacts:
            if modelFact.context is not None:
                numDims = len(modelFact.context.qnameDims) * 2
                if numDims > self.maxNumDims: self.maxNumDims = numDims
            self.tupleDepth(modelFact.modelTupleFacts, indentedCol + 1)
        
    def viewFacts(self, modelFacts, indent):
        for modelFact in modelFacts:
            concept = modelFact.concept
            xmlRowElementName = u'item'
            attr = {u"name": unicode(modelFact.qname)}
            if concept is not None and self.isCol0Label:
                lbl = concept.label(preferredLabel=self.labelrole, lang=self.lang, linkroleHint=XbrlConst.defaultLinkRole)
                xmlCol0skipElt = False # provide label as a row element
            else:
                lbl = modelFact.qname
                xmlCol0skipElt = True # name is an attribute, don't do it also as an element
            cols = [lbl]
            if concept is not None:
                if modelFact.isItem:
                    for col in self.cols[1:]:
                        if col == u"Label": # label or name may be 2nd to nth col if name or label is 1st col
                            cols.append( concept.label(preferredLabel=self.labelrole, lang=self.lang) )
                        elif col == u"Name":
                            cols.append( modelFact.qname )
                        elif col == u"contextRef":
                            cols.append( modelFact.contextID )
                        elif col == u"unitRef":
                            cols.append( modelFact.unitID )
                        elif col == u"Dec":
                            cols.append( modelFact.decimals )
                        elif col == u"Prec":
                            cols.append( modelFact.precision )
                        elif col == u"Lang":
                            cols.append( modelFact.xmlLang )
                        elif col == u"Value":
                            cols.append( u"(nil)" if modelFact.xsiNil == u"true" else modelFact.effectiveValue.strip() )
                        elif col == u"EntityScheme":
                            cols.append( modelFact.context.entityIdentifier[0] )
                        elif col == u"EntityIdentifier":
                            cols.append( modelFact.context.entityIdentifier[1] )
                        elif col == u"Start":
                            cols.append( XmlUtil.text(XmlUtil.child(modelFact.context.period, XbrlConst.xbrli, u"startDate")) )
                        elif col == u"End/Instant":
                            cols.append( XmlUtil.text(XmlUtil.child(modelFact.context.period, XbrlConst.xbrli, (u"endDate",u"instant"))) )
                        elif col == u"Dimensions":
                            for dimQname in sorted(modelFact.context.qnameDims.keys()):
                                cols.append( unicode(dimQname) )
                                cols.append( unicode(modelFact.context.dimMemberQname(dimQname)) )
                elif modelFact.isTuple:
                    xmlRowElementName = u'tuple'
            self.addRow(cols, treeIndent=indent, xmlRowElementName=xmlRowElementName, xmlRowEltAttr=attr, xmlCol0skipElt=xmlCol0skipElt)
            self.viewFacts(modelFact.modelTupleFacts, indent + 1)
