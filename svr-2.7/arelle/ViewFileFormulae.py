u'''
Created on Nov 27, 2011

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
from arelle import ModelObject, XbrlConst, ViewFile
from arelle.ModelDtsObject import ModelRelationship
from arelle.ModelFormulaObject import ModelParameter, ModelVariable, ModelVariableSetAssertion, ModelConsistencyAssertion
from arelle.ViewUtilFormulae import rootFormulaObjects, formulaObjSortKey
import os

def viewFormulae(modelXbrl, outfile, header, lang=None):
    modelXbrl.modelManager.showStatus(_(u"viewing formulae"))
    view = ViewFormulae(modelXbrl, outfile, header, lang)
    view.view()
    view.close()
    
class ViewFormulae(ViewFile.View):
    def __init__(self, modelXbrl, outfile, header, lang):
        super(ViewFormulae, self).__init__(modelXbrl, outfile, header, lang)
        
    def view(self):
        # determine relationships indent depth
        rootObjects = rootFormulaObjects(self)
        self.treeCols = 0
        for rootObject in rootObjects:
            self.treeDepth(rootObject, 1, set())
        self.addRow([u"Formula object", u"Label", u"Cover", u"Com\u00ADple\u00ADment", u"Bind as se\u00ADquence", u"Expression"], asHeader=True)
        for rootObject in sorted(rootObjects, key=formulaObjSortKey):
            self.viewFormulaObjects(rootObject, None, 0, set())
        for cfQnameArity in sorted(qnameArity
                                   for qnameArity in self.modelXbrl.modelCustomFunctionSignatures.keys()
                                   if isinstance(qnameArity, (tuple,list))):
            cfObject = self.modelXbrl.modelCustomFunctionSignatures[cfQnameArity]
            self.viewFormulaObjects(cfObject, None, 0, set())

    def treeDepth(self, fromObject, indent, visited):
        if fromObject is None:
            return
        if indent > self.treeCols: self.treeCols = indent
        if fromObject not in visited:
            visited.add(fromObject)
            relationshipArcsShown = set()
            for relationshipSet in (self.varSetFilterRelationshipSet,
                                    self.allFormulaRelationshipsSet):
                for modelRel in relationshipSet.fromModelObject(fromObject):
                    if modelRel.arcElement not in relationshipArcsShown:
                        relationshipArcsShown.add(modelRel.arcElement)
                        toObject = modelRel.toModelObject
                        self.treeDepth(toObject, indent + 1, visited)
            visited.remove(fromObject)
            
    def viewFormulaObjects(self, fromObject, fromRel, indent, visited):
        if fromObject is None:
            return
        if isinstance(fromObject, (ModelVariable, ModelParameter)) and fromRel is not None:
            text = u"{0} ${1}".format(fromObject.localName, fromRel.variableQname)
            xmlRowEltAttr = {u"type": unicode(fromObject.localName), u"name": unicode(fromRel.variableQname)}
        elif isinstance(fromObject, (ModelVariableSetAssertion, ModelConsistencyAssertion)):
            text = u"{0} {1}".format(fromObject.localName, fromObject.id)
            xmlRowEltAttr = {u"type": unicode(fromObject.localName), u"id": unicode(fromObject.id)}
        else:
            text = fromObject.localName
            xmlRowEltAttr = {u"type": unicode(fromObject.localName)}
        cols = [text, fromObject.xlinkLabel] # label
        if fromRel is not None and fromRel.elementQname == XbrlConst.qnVariableFilterArc:
            cols.append(u"true" if fromRel.isCovered else u"false") # cover
            cols.append(u"true" if fromRel.isComplemented else u"false") #complement
        else:
            cols.append(None) # cover
            cols.append(None) # compelement
        if isinstance(fromObject, ModelVariable):
            cols.append(fromObject.bindAsSequence) # bind as sequence
        else:
            cols.append(None) # bind as sequence
        if hasattr(fromObject, u"viewExpression"):
            cols.append(fromObject.viewExpression) # expression
        else:            
            cols.append(None) # expression
        self.addRow(cols, treeIndent=indent, xmlRowElementName = u"formulaObject", xmlRowEltAttr=xmlRowEltAttr, xmlCol0skipElt=True)
        if fromObject not in visited:
            visited.add(fromObject)
            relationshipArcsShown = set()
            for relationshipSet in (self.varSetFilterRelationshipSet,
                                    self.allFormulaRelationshipsSet):
                for modelRel in relationshipSet.fromModelObject(fromObject):
                    if modelRel.arcElement not in relationshipArcsShown:
                        relationshipArcsShown.add(modelRel.arcElement)
                        toObject = modelRel.toModelObject
                        self.viewFormulaObjects(toObject, modelRel, indent + 1, visited)
            visited.remove(fromObject)