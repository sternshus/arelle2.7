u'''
Created on Mar 7, 2011

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
import inspect, os
from arelle import XmlUtil, XbrlConst, XPathParser, Locale, XPathContext
from arelle.ModelDtsObject import ModelResource
from arelle.ModelInstanceObject import ModelDimensionValue
from arelle.ModelValue import qname, QName
from arelle.ModelObject import ModelObject
from arelle.ModelFormulaObject import (Trace, ModelFormulaResource, ModelFormulaRules, ModelConceptName,
                                       ModelParameter, Aspect, aspectStr, aspectRuleAspects)
from arelle.ModelInstanceObject import ModelFact
from arelle.FormulaEvaluator import (filterFacts as formulaEvaluatorFilterFacts, 
                                     aspectsMatch, factsPartitions, VariableBinding)
from arelle.PrototypeInstanceObject import FactPrototype

ROLLUP_NOT_ANALYZED = 0
CHILD_ROLLUP_FIRST = 1  
CHILD_ROLLUP_LAST = 2
CHILDREN_BUT_NO_ROLLUP = 3

OPEN_ASPECT_ENTRY_SURROGATE = u'\uDBFF'

EMPTY_SET = set()

def definitionNodes(nodes):
    return [(ord.definitionNodeObject if isinstance(node, StructuralNode) else node) for node in nodes]

# table linkbase structural nodes for rendering
class StructuralNode(object):
    def __init__(self, parentStructuralNode, breakdownNode, definitionNode, zInheritance=None, contextItemFact=None, tableNode=None, rendrCntx=None):
        self.parentStructuralNode = parentStructuralNode
        self._rendrCntx = rendrCntx or parentStructuralNode._rendrCntx # copy from parent except at root
        self.definitionNode = definitionNode
        self.variables = {}
        self.aspects = {}
        self.childStructuralNodes = []
        self.rollUpStructuralNode = None
        self.zInheritance = zInheritance
        if contextItemFact is not None:
            self.contextItemBinding = VariableBinding(self._rendrCntx,
                                                      boundFact=contextItemFact)
            if isinstance(self.contextItemBinding.yieldedFact, FactPrototype):
                for aspect in definitionNode.aspectsCovered():
                    if aspect != Aspect.DIMENSIONS:
                        self.aspectEntryObjectId = self.aspects[aspect] = contextItemFact.aspectEntryObjectId
                        break
        else:
            self.contextItemBinding = None
        self.subtreeRollUp = ROLLUP_NOT_ANALYZED
        self.depth = parentStructuralNode.depth + 1 if parentStructuralNode else 0
        if tableNode is not None:
            self.tableNode = tableNode
        self.breakdownNode = breakdownNode # CR definition node
        self.tagSelector = definitionNode.tagSelector
        self.isLabeled = True
        
    @property
    def modelXbrl(self):
        return self.definitionNode.modelXbrl
    
    @property
    def choiceStructuralNodes(self):
        if hasattr(self, u"_choiceStructuralNodes"):
            return self._choiceStructuralNodes
        if self.parentStructuralNode is not None:
            return self.parentStructuralNode.choiceStructuralNodes
        # choiceStrNodes are on the breakdown node (if any)
        return None
    
    @property
    def isAbstract(self):
        if self.subtreeRollUp:
            return self.subtreeRollUp == CHILDREN_BUT_NO_ROLLUP
        try:
            try:
                return self.abstract # ordinate may have an abstract attribute
            except AttributeError: # if none use axis object
                return self.definitionNode.isAbstract
        except AttributeError: # axis may never be abstract
            return False
        
    @property
    def isRollUp(self):
        return self.definitionNode.isRollUp
        
    @property
    def cardinalityAndDepth(self):
        return self.definitionNode.cardinalityAndDepth(self)
    
    @property
    def structuralDepth(self):
        if self.parentStructuralNode is not None:
            return self.parentStructuralNode.structuralDepth + 1
        return 0
    
    u'''
    def breakdownNode(self, tableELR):
        definitionNode = self.definitionNode
        if isinstance(definitionNode, ModelBreakdown):
            return definitionNode
        axisSubtreeRelSet = definitionNode.modelXbrl.relationshipSet((XbrlConst.tableBreakdownTree, XbrlConst.tableBreakdownTreeMMDD, XbrlConst.tableBreakdownTree201305, XbrlConst.tableDefinitionNodeSubtree, XbrlConst.tableDefinitionNodeSubtreeMMDD, XbrlConst.tableDefinitionNodeSubtree201305, XbrlConst.tableDefinitionNodeSubtree201301, XbrlConst.tableAxisSubtree2011), tableELR)
        while (True):
            for parentRel in axisSubtreeRelSet.toModelObject(definitionNode):
                definitionNode = parentRel.fromModelObject
                if isinstance(definitionNode, ModelBreakdown):
                    return definitionNode
                break # recurse to move to this node's parent breakdown node
        return definitionNode # give up here
    '''
   
    def constraintSet(self, tagSelectors=None):
        definitionNode = self.definitionNode
        if tagSelectors:
            for tag in tagSelectors:
                if tag in definitionNode.constraintSets:
                    return definitionNode.constraintSets[tag]
        return definitionNode.constraintSets.get(None) # returns None if no default constraint set
    
    def aspectsCovered(self, inherit=False):
        aspectsCovered = _DICT_SET(self.aspects.keys()) | self.definitionNode.aspectsCovered()
        if inherit and self.parentStructuralNode is not None:
            aspectsCovered.update(self.parentStructuralNode.aspectsCovered(inherit=inherit))
        return aspectsCovered
      
    def hasAspect(self, aspect, inherit=True):
        return (aspect in self.aspects or 
                self.definitionNode.hasAspect(self, aspect) or 
                (inherit and
                 self.parentStructuralNode is not None and 
                 self.parentStructuralNode.hasAspect(aspect, inherit)))
    
    def aspectValue(self, aspect, inherit=True, dims=None, depth=0, tagSelectors=None):
        xc = self._rendrCntx
        if False: # TEST: self.choiceStructuralNodes:  # use aspects from choice structural node
            choiceNodeIndex = getattr(self,u"choiceNodeIndex",0)
            if choiceNodeIndex != -1:
                chosenStructuralNode = self.choiceStructuralNodes[choiceNodeIndex]
                aspects = chosenStructuralNode.aspects
                definitionNode = chosenStructuralNode.definitionNode
                contextItemBinding = chosenStructuralNode.contextItemBinding
            else: # aspect entry mode
                aspects = self.aspects
                definitionNode = self.choiceStructuralNodes[0].definitionNode
                contextItemBinding = None
        else:
            aspects = self.aspects
            definitionNode = self.definitionNode
            contextItemBinding = self.contextItemBinding
        constraintSet = self.constraintSet(tagSelectors)
        if aspect == Aspect.DIMENSIONS:
            if dims is None: dims = set()
            if inherit and self.parentStructuralNode is not None:
                dims |= self.parentStructuralNode.aspectValue(aspect, dims=dims, depth=depth+1)
            if aspect in aspects:
                dims |= aspects[aspect]
            elif constraintSet is not None and constraintSet.hasAspect(self, aspect):
                dims |= set(definitionNode.aspectValue(xc, aspect) or {})
            if constraintSet is not None and constraintSet.hasAspect(self, Aspect.OMIT_DIMENSIONS):
                dims -= set(constraintSet.aspectValue(xc, Aspect.OMIT_DIMENSIONS))
            return dims
        if aspect in aspects:
            return aspects[aspect]
        elif constraintSet is not None and constraintSet.hasAspect(self, aspect):
            if isinstance(definitionNode, ModelSelectionDefinitionNode):
                # result is in the indicated variable of ordCntx
                return self.variables.get(self.definitionNode.variableQname)
            elif isinstance(definitionNode, ModelFilterDefinitionNode):
                if contextItemBinding:
                    return contextItemBinding.aspectValue(aspect)
            elif isinstance(definitionNode, ModelTupleDefinitionNode):
                if aspect == Aspect.LOCATION and contextItemBinding:
                    return contextItemBinding.yieldedFact
                # non-location tuple aspects don't leak into cell bindings
            else:
                return constraintSet.aspectValue(xc, aspect)
        if inherit and self.parentStructuralNode is not None:
            return self.parentStructuralNode.aspectValue(aspect, depth=depth+1)
        return None

    u'''
    @property   
    def primaryItemQname(self):  # for compatibility with viewRelationsihps
        if Aspect.CONCEPT in self.aspects:
            return self.aspects[Aspect.CONCEPT]
        return self.definitionNode.primaryItemQname
        
    @property
    def explicitDims(self):
        return self.definitionNode.explicitDims
    '''
        
    def objectId(self, refId=u""):
        return self.definitionNode.objectId(refId)
        
    def header(self, role=None, lang=None, evaluate=True, returnGenLabel=True, returnMsgFormatString=False, recurseParent=True):
        # if ord is a nested selectionAxis selection, use selection-message or text contents instead of axis headers
        isZSelection = isinstance(self.definitionNode, ModelSelectionDefinitionNode) and hasattr(self, u"zSelection")
        if role is None:
            # check for message before checking for genLabel
            msgsRelationshipSet = self.definitionNode.modelXbrl.relationshipSet(
                    (XbrlConst.tableDefinitionNodeSelectionMessage201301, XbrlConst.tableAxisSelectionMessage2011) 
                    if isZSelection else 
                    (XbrlConst.tableDefinitionNodeMessage201301, XbrlConst.tableAxisMessage2011))
            if msgsRelationshipSet:
                msg = msgsRelationshipSet.label(self.definitionNode, XbrlConst.standardMessage, lang, returnText=False)
                if msg is not None:
                    if evaluate:
                        if returnMsgFormatString:
                            return msg.formatString # not possible to evaluate (during resolution)
                        else:
                            return self.evaluate(msg, msg.evaluate)
                    else:
                        return XmlUtil.text(msg)
        if isZSelection: # no message, return text of selection
            return self.variables.get(self.definitionNode.variableQname, u"selection")
        if returnGenLabel:
            label = self.definitionNode.genLabel(role=role, lang=lang)
            if label:
                return label
        if self.isEntryAspect and role is None:
            # True if open node bound to a prototype, false if boudn to a real fact
            return OPEN_ASPECT_ENTRY_SURROGATE # sort pretty high, work ok for python 2.7/3.2 as well as 3.3
        # if there's a child roll up, check for it
        if self.rollUpStructuralNode is not None:  # check the rolling-up child too
            return self.rollUpStructuralNode.header(role, lang, evaluate, returnGenLabel, returnMsgFormatString, recurseParent)
        # if aspect is a concept of dimension, return its standard label
        concept = None
        if role is None:
            for aspect in self.aspectsCovered():
                aspectValue = self.aspectValue(aspect, inherit=recurseParent)
                if isinstance(aspect, QName) or aspect == Aspect.CONCEPT: # dimension or concept
                    if isinstance(aspectValue, QName):
                        concept = self.modelXbrl.qnameConcepts[aspectValue]
                        break
                    elif isinstance(aspectValue, ModelDimensionValue):
                        if aspectValue.isExplicit:
                            concept = aspectValue.member
                        elif aspectValue.isTyped:
                            return XmlUtil.innerTextList(aspectValue.typedMember)
                elif isinstance(aspectValue, ModelObject):
                    text = XmlUtil.innerTextList(aspectValue)
                    if not text and XmlUtil.hasChild(aspectValue, aspectValue.namespaceURI, u"forever"):
                        text = u"forever" 
                    return text
        if concept is not None:
            label = concept.label(lang=lang)
            if label:
                return label
        # if there is a role, check if it's available on a parent node
        if role and recurseParent and self.parentStructuralNode is not None:
            return self.parentStructuralNode.header(role, lang, evaluate, returnGenLabel, returnMsgFormatString, recurseParent)
        return None
    
    def evaluate(self, evalObject, evalMethod, otherAxisStructuralNode=None, evalArgs=()):
        xc = self._rendrCntx
        if self.contextItemBinding and not isinstance(xc.contextItem, ModelFact):
            previousContextItem = xc.contextItem # xbrli.xbrl
            xc.contextItem = self.contextItemBinding.yieldedFact
        else:
            previousContextItem = None
        if self.choiceStructuralNodes and hasattr(self,u"choiceNodeIndex"):
            variables = self.choiceStructuralNodes[self.choiceNodeIndex].variables
        else:
            variables = self.variables
        removeVarQnames = []
        for variablesItems in variables.items():
            for qn, value in variablesItems:
                if qn not in xc.inScopeVars:
                    removeVarQnames.append(qn)
                    xc.inScopeVars[qn] = value
        if self.parentStructuralNode is not None:
            result = self.parentStructuralNode.evaluate(evalObject, evalMethod, otherAxisStructuralNode, evalArgs)
        elif otherAxisStructuralNode is not None:
            # recurse to other ordinate (which will recurse to z axis)
            result = otherAxisStructuralNode.evaluate(evalObject, evalMethod, None, evalArgs)
        elif self.zInheritance is not None:
            result = self.zInheritance.evaluate(evalObject, evalMethod, None, evalArgs)
        else:
            try:
                result = evalMethod(xc, *evalArgs)
            except XPathContext.XPathException, err:
                xc.modelXbrl.error(err.code,
                         _(u"%(element)s set %(xlinkLabel)s \nException: %(error)s"), 
                         modelObject=evalObject, element=evalObject.localName, 
                         xlinkLabel=evalObject.xlinkLabel, error=err.message)
                result = u''
        for qn in removeVarQnames:
            xc.inScopeVars.pop(qn)
        if previousContextItem is not None:
            xc.contextItem = previousContextItem # xbrli.xbrl
        return result
    
    def hasValueExpression(self, otherAxisStructuralNode=None):
        return (self.definitionNode.hasValueExpression or 
                (otherAxisStructuralNode is not None and otherAxisStructuralNode.definitionNode.hasValueExpression))
    
    def evalValueExpression(self, fact, otherAxisStructuralNode=None):
        for structuralNode in (self, otherAxisStructuralNode):
            if structuralNode is not None and structuralNode.definitionNode.hasValueExpression:
                return self.evaluate(self.definitionNode, structuralNode.definitionNode.evalValueExpression, otherAxisStructuralNode=otherAxisStructuralNode, evalArgs=(fact,))
        return None
    
    @property
    def isEntryAspect(self):
        # true if open node and bound to a fact prototype
        return self.contextItemBinding is not None and isinstance(self.contextItemBinding.yieldedFact, FactPrototype)
    
    def isEntryPrototype(self, default=False):
        # true if all axis open nodes before this one are entry prototypes (or not open axes)
        if self.contextItemBinding is not None:
            # True if open node bound to a prototype, false if bound to a real fact
            return isinstance(self.contextItemBinding.yieldedFact, FactPrototype)
        if self.parentStructuralNode is not None:
            return self.parentStructuralNode.isEntryPrototype(default)
        return default # nothing open to be bound to a fact
            
    @property
    def tableDefinitionNode(self):
        if self.parentStructuralNode is None:
            return self.tableNode
        else:
            return self.parentStructuralNode.tableDefinitionNode
        
    @property
    def tagSelectors(self):
        try:
            return self._tagSelectors
        except AttributeError:
            if self.parentStructuralNode is None:
                self._tagSelectors = set()
            else:
                self._tagSelectors = self.parentStructuralNode.tagSelectors
            if self.tagSelector:
                self._tagSelectors.add(self.tagSelector)
            return self._tagSelectors
    
    @property
    def leafNodeCount(self):
        childLeafCount = 0
        if self.childStructuralNodes:
            for childStructuralNode in self.childStructuralNodes:
                childLeafCount += childStructuralNode.leafNodeCount
        if childLeafCount == 0:
            return 1
        if not self.isAbstract and isinstance(self.definitionNode, (ModelClosedDefinitionNode, ModelEuAxisCoord)):
            childLeafCount += 1 # has a roll up
        return childLeafCount
    
    def setHasOpenNode(self):
        if self.parentStructuralNode is not None:
            self.parentStructuralNode.setHasOpenNode()
        else:
            self.hasOpenNode = True

    def inheritedPrimaryItemQname(self, view):
        return (self.primaryItemQname or self.inheritedPrimaryItemQname(self.parentStructuralNode, view))
            
    def inheritedExplicitDims(self, view, dims=None, nested=False):
        if dims is None: dims = {}
        if self.parentOrdinateContext:
            self.parentStructuralNode.inheritedExplicitDims(view, dims, True)
        for dim, mem in self.explicitDims:
            dims[dim] = mem
        if not nested:
            return set((dim,mem) for dim,mem in dims.items() if mem != u'omit')

    def inheritedAspectValue(self, otherAxisStructuralNode,
                             view, aspect, tagSelectors, 
                             xAspectStructuralNodes, yAspectStructuralNodes, zAspectStructuralNodes):
        aspectStructuralNodes = xAspectStructuralNodes.get(aspect, EMPTY_SET) | yAspectStructuralNodes.get(aspect, EMPTY_SET) | zAspectStructuralNodes.get(aspect, EMPTY_SET)
        structuralNode = None
        if len(aspectStructuralNodes) == 1:
            structuralNode = aspectStructuralNodes.pop()
        elif len(aspectStructuralNodes) > 1:
            if aspect == Aspect.LOCATION:
                hasClash = False
                for _aspectStructuralNode in aspectStructuralNodes:
                    if not _aspectStructuralNode.definitionNode.aspectValueDependsOnVars(aspect):
                        if structuralNode:
                            hasClash = True
                        else:
                            structuralNode = _aspectStructuralNode 
            else:
                # take closest structural node
                hasClash = True
                
            u''' reported in static analysis by RenderingEvaluator.py
            if hasClash:
                from arelle.ModelFormulaObject import aspectStr
                view.modelXbrl.error("xbrlte:aspectClashBetweenBreakdowns",
                    _("Aspect %(aspect)s covered by multiple axes."),
                    modelObject=view.modelTable, aspect=aspectStr(aspect))
            '''
        if structuralNode:
            definitionNodeConstraintSet = structuralNode.constraintSet(tagSelectors)
            if definitionNodeConstraintSet is not None and definitionNodeConstraintSet.aspectValueDependsOnVars(aspect):
                return self.evaluate(definitionNodeConstraintSet, 
                                     definitionNodeConstraintSet.aspectValue, # this passes a method
                                     otherAxisStructuralNode=otherAxisStructuralNode,
                                     evalArgs=(aspect,))
            return structuralNode.aspectValue(aspect, tagSelectors=tagSelectors)
        return None 

                      
    def __repr__(self):
        return (u"structuralNode[{0}]{1})".format(self.objectId(),self.definitionNode))
        
# Root class for rendering is formula, to allow linked and nested compiled expressions
def definitionModelLabelsView(mdlObj):
    return tuple(sorted([(u"{} {} {} {}".format(label.localName,
                                            unicode(rel.order).rstrip(u"0").rstrip(u"."),
                                            os.path.basename(label.role),
                                            label.xmlLang), 
                          label.stringValue)
                         for rel in mdlObj.modelXbrl.relationshipSet((XbrlConst.elementLabel,XbrlConst.elementReference)).fromModelObject(mdlObj)
                         for label in (rel.toModelObject,)] +
                        [(u"xlink:label", mdlObj.xlinkLabel)]))

# 2010 EU Table linkbase
class ModelEuTable(ModelResource):
    def init(self, modelDocument):
        super(ModelEuTable, self).init(modelDocument)
        self.aspectsInTaggedConstraintSets = set()
        
    @property
    def aspectModel(self):
        return u"dimensional"
        
    @property
    def propertyView(self):
        return (((u"id", self.id),) +
                self.definitionLabelsView)
    
    u''' now only accessed from structural node    
    def header(self, role=None, lang=None, strip=False, evaluate=True):
        return self.genLabel(role=role, lang=lang, strip=strip)
    '''
    
    @property
    def parameters(self):
        return {}
  
    @property
    def definitionLabelsView(self):
        return definitionModelLabelsView(self)
        
    def filteredFacts(self, xpCtx, facts):
        return facts
    
    @property
    def xpathContext(self):
        return None
    
    def __repr__(self):
        return (u"table[{0}]{1})".format(self.objectId(),self.propertyView))

class ModelEuAxisCoord(ModelResource):
    def init(self, modelDocument):
        super(ModelEuAxisCoord, self).init(modelDocument)
        
    @property
    def abstract(self):
        return self.get(u"abstract") or u'false'
    
    @property
    def isAbstract(self):
        return self.abstract == u"true"
    
    @property
    def isMerged(self):
        return False
    
    @property
    def parentChildOrder(self):
        return self.get(u"parentChildOrder")
    
    @property
    def isRollUp(self):
        return False
    
    @property
    def parentDefinitionNode(self):
        try:
            return self._parentDefinitionNode
        except AttributeError:
            parentDefinitionNode = None
            for rel in self.modelXbrl.relationshipSet(XbrlConst.euAxisMember).toModelObject(self):
                parentDefinitionNode = rel.fromModelObject
                break
            self._parentDefinitionNode = parentDefinitionNode
            return parentDefinitionNode

    def aspectsCovered(self):
        aspectsCovered = set()
        if XmlUtil.hasChild(self, XbrlConst.euRend, u"primaryItem"):
            aspectsCovered.add(Aspect.CONCEPT)
        if XmlUtil.hasChild(self, XbrlConst.euRend, u"timeReference"):
            aspectsCovered.add(Aspect.INSTANT)
        for e in XmlUtil.children(self, XbrlConst.euRend, u"explicitDimCoord"):
            aspectsCovered.add(self.prefixedNameQname(e.get(u"dimension")))
        return aspectsCovered
    
    @property
    def constraintSets(self):
        return {None: self}
                    
    @property
    def tagSelector(self):  # default constraint set for ruleNode has name None
        return None
        
    def hasAspect(self, structuralNode, aspect):
        if aspect == Aspect.CONCEPT:
            return XmlUtil.hasChild(self, XbrlConst.euRend, u"primaryItem")
        elif aspect == Aspect.DIMENSIONS:
            return XmlUtil.hasChild(self, XbrlConst.euRend, u"explicitDimCoord")
        elif aspect in (Aspect.PERIOD_TYPE, Aspect.INSTANT):
            return XmlUtil.hasChild(self, XbrlConst.euRend, u"timeReference")
        elif isinstance(aspect, QName):
            for e in XmlUtil.children(self, XbrlConst.euRend, u"explicitDimCoord"):
                if self.prefixedNameQname(e.get(u"dimension")) == aspect:
                    return True
        return False
    
    def aspectValueDependsOnVars(self, aspect):
        return False
    
    def aspectValue(self, xpCtx, aspect, inherit=False):
        if aspect == Aspect.DIMENSIONS:
            dims = set(self.prefixedNameQname(e.get(u"dimension"))
                       for e in XmlUtil.children(self, XbrlConst.euRend, u"explicitDimCoord"))
            if inherit and self.parentDefinitionNode is not None:
                dims |= self.parentDefinitionNode.aspectValue(None, aspect, inherit)
            return dims
        if inherit and not self.hasAspect(None, aspect):
            if self.parentDefinitionNode is not None:
                return self.parentDefinitionNode.aspectValue(None, aspect, inherit)
            return None
        if aspect == Aspect.CONCEPT:
            priItem = XmlUtil.childAttr(self, XbrlConst.euRend, u"primaryItem", u"name")
            if priItem is not None:
                return self.prefixedNameQname(priItem)
            return None
        elif aspect == Aspect.PERIOD_TYPE:
            if XmlUtil.hasChild(self, XbrlConst.euRend, u"timeReference"):
                return u"instant"
        elif aspect == Aspect.INSTANT:
            return XmlUtil.datetimeValue(XmlUtil.childAttr(self, XbrlConst.euRend, u"timeReference", u"instant"), 
                                         addOneDay=True)
        elif isinstance(aspect, QName):
            for e in XmlUtil.children(self, XbrlConst.euRend, u"explicitDimCoord"):
                if self.prefixedNameQname(e.get(u"dimension")) == aspect:
                    return self.prefixedNameQname(e.get(u"value"))
        return None

    u'''
    @property
    def primaryItemQname(self):
        priItem = XmlUtil.childAttr(self, XbrlConst.euRend, "primaryItem", "name")
        if priItem is not None:
            return self.prefixedNameQname(priItem)
        return None
    
    @property
    def explicitDims(self):
        return {(self.prefixedNameQname(e.get("dimension")),
                 self.prefixedNameQname(e.get("value")))
                for e in XmlUtil.children(self, XbrlConst.euRend, "explicitDimCoord")}
    
    @property
    def instant(self):
        return XmlUtil.datetimeValue(XmlUtil.childAttr(self, XbrlConst.euRend, "timeReference", "instant"), 
                                     addOneDay=True)
    '''

    def cardinalityAndDepth(self, structuralNode):
        return (1, 1)
        
    u''' now only accessed from structural node    
    def header(self, role=None, lang=None, strip=False, evaluate=True):
        return self.genLabel(role=role, lang=lang, strip=strip)
    '''
    
    @property
    def hasValueExpression(self):
        return False
  
    @property
    def definitionLabelsView(self):
        return definitionModelLabelsView(self)
    
    @property
    def propertyView(self):
        explicitDims = self.aspectValue(None, Aspect.DIMENSIONS, inherit=True)
        return (((u"id", self.id),
                 (u"primary item", self.aspectValue(None, Aspect.CONCEPT, inherit=True)),
                 (u"dimensions", u"({0})".format(len(explicitDims)),
                   tuple((unicode(dim),unicode(self.aspectValue(None, dim, inherit=True))) 
                         for dim in sorted(explicitDims)))
                   if explicitDims else (),
                 (u"abstract", self.abstract)) +
                self.definitionLabelsView)
        
    def __repr__(self):
        return (u"axisCoord[{0}]{1})".format(self.objectId(),self.propertyView))

# 2011 Table linkbase
class ModelTable(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelTable, self).init(modelDocument)
        self.modelXbrl.modelRenderingTables.add(self)
        self.modelXbrl.hasRenderingTables = True
        self.aspectsInTaggedConstraintSets = set()
        
    def clear(self):
        if getattr(self, u"_rendrCntx"):
            self._rendrCntx.close()
        super(ModelTable, self).clear()  # delete children
                   
    @property
    def aspectModel(self):
        return self.get(u"aspectModel", u"dimensional") # attribute removed 2013-06, always dimensional

    @property
    def descendantArcroles(self):        
        return (XbrlConst.tableFilter, XbrlConst.tableFilterMMDD, XbrlConst.tableFilter201305, XbrlConst.tableFilter201301, XbrlConst.tableFilter2011, 
                XbrlConst.tableBreakdown, XbrlConst.tableBreakdownMMDD, XbrlConst.tableBreakdown201305, XbrlConst.tableBreakdown201301, XbrlConst.tableAxis2011,
                XbrlConst.tableParameter, XbrlConst.tableParameterMMDD)
                
    @property
    def filterRelationships(self):
        try:
            return self._filterRelationships
        except AttributeError:
            rels = [] # order so conceptName filter is first (if any) (may want more sorting in future)
            for rel in self.modelXbrl.relationshipSet((XbrlConst.tableFilter, XbrlConst.tableFilterMMDD, XbrlConst.tableFilter201305, XbrlConst.tableFilter201301, XbrlConst.tableFilter2011)).fromModelObject(self):
                if isinstance(rel.toModelObject, ModelConceptName):
                    rels.insert(0, rel)  # put conceptName filters first
                else:
                    rels.append(rel)
            self._filterRelationships = rels
            return rels
        
    u''' now only accessed from structural node    
    def header(self, role=None, lang=None, strip=False, evaluate=True):
        return self.genLabel(role=role, lang=lang, strip=strip)
    '''
  
    @property
    def definitionLabelsView(self):
        return definitionModelLabelsView(self)
    
    def filteredFacts(self, xpCtx, facts):
        return formulaEvaluatorFilterFacts(xpCtx, VariableBinding(xpCtx), 
                                           facts, self.filterRelationships, None)
        
    @property
    def renderingXPathContext(self):
        try:
            return self._rendrCntx
        except AttributeError:
            xpCtx = getattr(self.modelXbrl, u"rendrCntx", None) # none for EU 2010 tables
            if xpCtx is not None:
                self._rendrCntx = xpCtx.copy()
                for tblParamRel in self.modelXbrl.relationshipSet((XbrlConst.tableParameter, XbrlConst.tableParameterMMDD)).fromModelObject(self):
                    varQname = tblParamRel.variableQname
                    parameter = tblParamRel.toModelObject
                    if isinstance(parameter, ModelParameter):
                        self._rendrCntx.inScopeVars[varQname] = xpCtx.inScopeVars.get(parameter.parameterQname)
            else:
                self._rendrCntx = None
            return self._rendrCntx
        
    @property
    def propertyView(self):
        return (((u"id", self.id),) +
                self.definitionLabelsView)
        
    def __repr__(self):
        return (u"modlTable[{0}]{1})".format(self.objectId(),self.propertyView))

class ModelDefinitionNode(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelDefinitionNode, self).init(modelDocument)
    
    @property
    def parentDefinitionNode(self):
        return None
                
    @property
    def descendantArcroles(self):        
        return (XbrlConst.tableDefinitionNodeMessage201301, XbrlConst.tableAxisMessage2011,
                XbrlConst.tableDefinitionNodeSubtree201305,
                XbrlConst.tableDefinitionNodeSubtree, XbrlConst.tableDefinitionNodeSubtreeMMDD)
        
    def hasAspect(self, structuralNode, aspect):
        return False

    def aspectValueDependsOnVars(self, aspect):
        return False
    
    @property
    def variablename(self):
        u"""(str) -- name attribute"""
        return self.getStripped(u"name")

    @property
    def variableQname(self):
        u"""(QName) -- resolved name for an XPath bound result having a QName name attribute"""
        varName = self.variablename
        return qname(self, varName, noPrefixIsNoNamespace=True) if varName else None

    def aspectValue(self, xpCtx, aspect, inherit=True):
        if aspect == Aspect.DIMENSIONS:
            return []
        return None
    
    def aspectsCovered(self):
        return set()

    @property
    def constraintSets(self):
        return {None: self}
                    
    @property
    def tagSelector(self):
        return self.get(u"tagSelector")
            
    @property
    def valueExpression(self):
        return self.get(u"value") 

    @property
    def hasValueExpression(self):
        return bool(self.valueProg)  # non empty program
    
    def compile(self):
        if not hasattr(self, u"valueProg"):
            value = self.valueExpression
            self.valueProg = XPathParser.parse(self, value, self, u"value", Trace.VARIABLE)
        # duplicates formula resource for RuleAxis but not for other subclasses
        super(ModelDefinitionNode, self).compile()
        
    def evalValueExpression(self, xpCtx, fact):
        # compiled by FormulaResource compile()
        return xpCtx.evaluateAtomicValue(self.valueProg, u'xs:string', fact)
    
    u'''
    @property   
    def primaryItemQname(self):  # for compatibility with viewRelationsihps
        return None
        
    @property
    def explicitDims(self):
        return set()
    '''
        
    @property
    def isAbstract(self):
        return False
    
    @property
    def isMerged(self):
        return False
    
    @property
    def isRollUp(self):
        return self.get(u"rollUp") == u'true'
    
    def cardinalityAndDepth(self, structuralNode):
        return (1, 
                1 if (structuralNode.header(evaluate=False) is not None) else 0)
        
    u''' now only accessed from structural node (mulst have table context for evaluate)           
    def header(self, role=None, lang=None, strip=False, evaluate=True):
        if role is None:
            # check for message before checking for genLabel
            msgsRelationshipSet = self.modelXbrl.relationshipSet((XbrlConst.tableDefinitionNodeMessage201301, XbrlConst.tableAxisMessage2011))
            if msgsRelationshipSet:
                msg = msgsRelationshipSet.label(self, XbrlConst.standardMessage, lang, returnText=False)
                if msg is not None:
                    if evaluate:
                        result = msg.evaluate(self.modelXbrl.rendrCntx)
                    else:
                        result = XmlUtil.text(msg)
                    if strip:
                        return result.strip()
                    return result
        return self.genLabel(role=role, lang=lang, strip=strip)
    '''

    @property
    def definitionNodeView(self):        
        return XmlUtil.xmlstring(self, stripXmlns=True, prettyPrint=True)
  

    @property
    def definitionLabelsView(self):
        return definitionModelLabelsView(self)
  
class ModelBreakdown(ModelDefinitionNode):
    def init(self, modelDocument):
        super(ModelBreakdown, self).init(modelDocument)
        
    @property
    def parentChildOrder(self):
        return self.get(u"parentChildOrder")

    @property
    def descendantArcroles(self):        
        return (XbrlConst.tableBreakdownTree, XbrlConst.tableBreakdownTreeMMDD, XbrlConst.tableBreakdownTree201305)
    
    @property
    def propertyView(self):
        return (((u"id", self.id),
                 (u"parent child order", self.parentChildOrder),
                 (u"definition", self.definitionNodeView)) +
                 self.definitionLabelsView)

class ModelClosedDefinitionNode(ModelDefinitionNode):
    def init(self, modelDocument):
        super(ModelClosedDefinitionNode, self).init(modelDocument)
        
    @property
    def abstract(self):
        return self.get(u"abstract")
    
    @property
    def isAbstract(self):
        return self.abstract == u'true'
        
    @property
    def parentChildOrder(self):
        return self.get(u"parentChildOrder")

    @property
    def descendantArcroles(self):        
        return (XbrlConst.tableDefinitionNodeSubtree, XbrlConst.tableDefinitionNodeSubtreeMMDD, XbrlConst.tableDefinitionNodeSubtree201305, XbrlConst.tableDefinitionNodeSubtree201301, XbrlConst.tableAxisSubtree2011, XbrlConst.tableDefinitionNodeMessage201301, XbrlConst.tableAxisMessage2011)
    
    def filteredFacts(self, xpCtx, facts):
        aspects = self.aspectsCovered()
        axisAspectValues = dict((aspect, self.aspectValue(xpCtx, aspect))
                                for aspect in aspects)
        fp = FactPrototype(self, axisAspectValues)
        return set(fact
                   for fact in facts
                   if aspectsMatch(xpCtx, fact, fp, aspects))
        
class ModelConstraintSet(ModelFormulaRules):
    def init(self, modelDocument):
        super(ModelConstraintSet, self).init(modelDocument)
        self._locationSourceVar = self.source(Aspect.LOCATION_RULE, acceptFormulaSource=False)
        self._locationAspectCovered = set()
        self.aspectValues = {} # only needed if error blocks compiling this node, replaced by compile()
        self.aspectProgs = {} # ditto
        if self._locationSourceVar: self._locationAspectCovered.add(Aspect.LOCATION) # location is parent (tuple), not sibling
        
    def hasAspect(self, structuralNode, aspect, inherit=None):
        return self._hasAspect(structuralNode, aspect, inherit)
    
    def _hasAspect(self, structuralNode, aspect, inherit=None): # opaque from ModelRuleDefinitionNode
        if aspect == Aspect.LOCATION and self._locationSourceVar:
            return True
        elif aspect in aspectRuleAspects:
            return any(self.hasRule(a) for a in aspectRuleAspects[aspect])
        return self.hasRule(aspect)
    
    def aspectValue(self, xpCtx, aspect, inherit=None):
        try:
            # if xpCtx is None: xpCtx = self.modelXbrl.rendrCntx (must have xpCtx of callint table)
            if aspect == Aspect.LOCATION and self._locationSourceVar in xpCtx.inScopeVars:
                return xpCtx.inScopeVars[self._locationSourceVar]
            return self.evaluateRule(xpCtx, aspect)
        except AttributeError:
            return u'(unavailable)'  # table defective or not initialized
    
    def aspectValueDependsOnVars(self, aspect):
        return aspect in _DICT_SET(self.aspectProgs.keys()) or aspect in self._locationAspectCovered
    
    def aspectsCovered(self):
        return _DICT_SET(self.aspectValues.keys()) | _DICT_SET(self.aspectProgs.keys()) | self._locationAspectCovered
    
    # provide model table's aspect model to compile() method of ModelFormulaRules
    @property
    def aspectModel(self):
        for frameRecord in inspect.stack():
            obj = frameRecord[0].f_locals[u'self']
            if isinstance(obj,ModelTable):
                return obj.aspectModel
        return None
    
    u'''
    @property   
    def primaryItemQname(self):
        return self.evaluateRule(self.modelXbrl.rendrCntx, Aspect.CONCEPT)

    @property
    def explicitDims(self):
        dimMemSet = set()
        dims = self.evaluateRule(self.modelXbrl.rendrCntx, Aspect.DIMENSIONS)
        if dims: # may be none if no dim aspects on this ruleAxis
            for dim in dims:
                mem = self.evaluateRule(self.modelXbrl.rendrCntx, dim)
                if mem: # may be none if dimension was omitted
                    dimMemSet.add( (dim, mem) )
        return dimMemSet
    
    @property
    def instant(self):
        periodType = self.evaluateRule(self.modelXbrl.rendrCntx, Aspect.PERIOD_TYPE)
        if periodType == "forever":
            return None
        return self.evaluateRule(self.modelXbrl.rendrCntx, 
                                 {"instant": Aspect.INSTANT,
                                  "duration": Aspect.END}[periodType])
    '''
    
    def cardinalityAndDepth(self, structuralNode):
        if self.aspectValues or self.aspectProgs or structuralNode.header(evaluate=False) is not None:
            return (1, 1)
        else:
            return (0, 0)

class ModelRuleSet(ModelConstraintSet, ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelRuleSet, self).init(modelDocument)
        
    @property
    def tagName(self):  # can't call it tag because that would hide ElementBase.tag
        return self.get(u"tag")

class ModelRuleDefinitionNode(ModelConstraintSet, ModelClosedDefinitionNode):
    def init(self, modelDocument):
        super(ModelRuleDefinitionNode, self).init(modelDocument)
        
    @property
    def merge(self):
        return self.get(u"merge")
    
    @property
    def isMerged(self):
        return self.merge == u"true"
    
    @property
    def constraintSets(self):
        try:
            return self._constraintSets
        except AttributeError:
            self._constraintSets = dict((ruleSet.tagName, ruleSet)
                                        for ruleSet in XmlUtil.children(self, self.namespaceURI, u"ruleSet"))
            if self.aspectsCovered(): # any local rule?
                self._constraintSets[None] = self                
            return self._constraintSets
            
    def hasAspect(self, structuralNode, aspect):
        return any(constraintSet._hasAspect(structuralNode, aspect)
                   for constraintSet in self.constraintSets.values())
        
    @property
    def aspectsInTaggedConstraintSet(self):
        try:
            return self._aspectsInTaggedConstraintSet
        except AttributeError:
            self._aspectsInTaggedConstraintSet = set()
            for tag, constraintSet in self.constraitSets().items():
                if tag is not None:
                    for aspect in constraintSet.aspectsCovered():
                        if aspect != Aspect.DIMENSIONS:
                            self._aspectsInTaggedConstraintSet.add(aspect)
            return self._aspectsInTaggedConstraintSet
                    
    def compile(self):
        super(ModelRuleDefinitionNode, self).compile()
        for constraintSet in self.constraintSets.values():
            if constraintSet != self: # compile nested constraint sets
                constraintSet.compile()
   
    @property
    def propertyView(self):
        return (((u"id", self.id),
                 (u"abstract", self.abstract),
                 (u"merge", self.merge),
                 (u"definition", self.definitionNodeView)) +
                 self.definitionLabelsView)
        
    def __repr__(self):
        return (u"modelRuleDefinitionNode[{0}]{1})".format(self.objectId(),self.propertyView))

# deprecated 2013-05-17
class ModelTupleDefinitionNode(ModelRuleDefinitionNode):
    def init(self, modelDocument):
        super(ModelTupleDefinitionNode, self).init(modelDocument)
        
    @property
    def descendantArcroles(self):        
        return (XbrlConst.tableTupleContent201301, XbrlConst.tableTupleContent2011, XbrlConst.tableDefinitionNodeMessage201301, XbrlConst.tableAxisMessage2011)
        
    @property
    def contentRelationships(self):
        return self.modelXbrl.relationshipSet((XbrlConst.tableTupleContent201301, XbrlConst.tableTupleContent2011)).fromModelObject(self)
        
    def hasAspect(self, structuralNode, aspect, inherit=None):
        return aspect == Aspect.LOCATION # non-location aspects aren't leaked to ordinate for Tuple or self.hasRule(aspect)
    
    def aspectValue(self, xpCtx, aspect, inherit=None):
        return self.evaluateRule(xpCtx, aspect)
    
    def aspectsCovered(self):
        return set([Aspect.LOCATION])  # tuple's aspects don't leak to ordinates
    
    def tupleAspectsCovered(self):
        return _DICT_SET(self.aspectValues.keys()) | _DICT_SET(self.aspectProgs.keys()) | set([Aspect.LOCATION])
    
    def filteredFacts(self, xpCtx, facts):
        aspects = self.aspectsCovered()
        axisAspectValues = dict((aspect, self.tupleAspectsCovered(aspect))
                                for aspect in aspects
                                if aspect != Aspect.LOCATION)  # location determined by ordCntx, not axis
        fp = FactPrototype(self, axisAspectValues)
        return set(fact
                   for fact in facts
                   if fact.isTuple and aspectsMatch(xpCtx, fact, fp, aspects))

class ModelCompositionDefinitionNode(ModelClosedDefinitionNode):
    def init(self, modelDocument):
        super(ModelCompositionDefinitionNode, self).init(modelDocument)
        
    @property
    def abstract(self):  # always abstract, no filters, no data
        return u'true'

class ModelRelationshipDefinitionNode(ModelClosedDefinitionNode):
    def init(self, modelDocument):
        super(ModelRelationshipDefinitionNode, self).init(modelDocument)
        
    def aspectsCovered(self):
        return set([Aspect.CONCEPT])

    @property
    def conceptQname(self):
        name = self.getStripped(u"conceptname")
        return qname(self, name, noPrefixIsNoNamespace=True) if name else None
        
    @property
    def relationshipSourceQname(self):
        sourceQname = XmlUtil.child(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"relationshipSource")
        if sourceQname is not None:
            return qname( sourceQname, XmlUtil.text(sourceQname) )
        return None
    
    @property
    def linkrole(self):
        return XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"linkrole")

    @property
    def axis(self):
        a = XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), (u"axis", u"formulaAxis"))
        if not a: a = u'descendant'  # would be an XML error
        return a
    
    @property
    def isOrSelfAxis(self):
        return self.axis.endswith(u'-or-self')

    @property
    def generations(self):
        try:
            return _INT( XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"generations") )
        except (TypeError, ValueError):
            if self.axis in (u'sibling', u'child', u'parent'): 
                return 1
            return 0

    @property
    def relationshipSourceQnameExpression(self):
        return XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"relationshipSourceExpression")

    @property
    def linkroleExpression(self):
        return XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"linkroleExpression")

    @property
    def axisExpression(self):
        return XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), (u"axisExpression", u"formulAxisExpression"))

    @property
    def generationsExpression(self):
        return XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"generationsExpression")

    def compile(self):
        if not hasattr(self, u"relationshipSourceQnameExpressionProg"):
            self.relationshipSourceQnameExpressionProg = XPathParser.parse(self, self.relationshipSourceQnameExpression, self, u"relationshipSourceQnameExpressionProg", Trace.VARIABLE)
            self.linkroleExpressionProg = XPathParser.parse(self, self.linkroleExpression, self, u"linkroleQnameExpressionProg", Trace.VARIABLE)
            self.axisExpressionProg = XPathParser.parse(self, self.axisExpression, self, u"axisExpressionProg", Trace.VARIABLE)
            self.generationsExpressionProg = XPathParser.parse(self, self.generationsExpression, self, u"generationsExpressionProg", Trace.VARIABLE)
            super(ModelRelationshipDefinitionNode, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        if self.relationshipSourceQname and self.relationshipSourceQname != XbrlConst.qnXfiRoot:
            if varRefSet is None: varRefSet = set()
            varRefSet.add(self.relationshipSourceQname)
        return super(ModelRelationshipDefinitionNode, self).variableRefs(
                                                [p for p in (self.relationshipSourceQnameExpressionProg,
                                                             self.linkroleExpressionProg, self.axisExpressionProg,
                                                             self.generationsExpressionProg)
                                        if p], varRefSet)

    def evalRrelationshipSourceQname(self, xpCtx, fact=None):
        if self.relationshipSourceQname:
            return self.relationshipSourceQname
        return xpCtx.evaluateAtomicValue(self.relationshipSourceQnameExpressionProg, u'xs:QName', fact)
    
    def evalLinkrole(self, xpCtx, fact=None):
        if self.linkrole:
            return self.linkrole
        return xpCtx.evaluateAtomicValue(self.linkroleExpressionProg, u'xs:anyURI', fact)
    
    def evalAxis(self, xpCtx, fact=None):
        if self.axis:
            return self.axis
        return xpCtx.evaluateAtomicValue(self.axisExpressionProg, u'xs:token', fact)
    
    def evalGenerations(self, xpCtx, fact=None):
        if self.generations:
            return self.generations
        return xpCtx.evaluateAtomicValue(self.generationsExpressionProg, u'xs:integer', fact)

    def cardinalityAndDepth(self, structuralNode):
        return self.lenDepth(self.relationships(structuralNode), 
                             self.axis.endswith(u'-or-self'))
    
    def lenDepth(self, nestedRelationships, includeSelf):
        l = 0
        d = 1
        for rel in nestedRelationships:
            if isinstance(rel, list):
                nl, nd = self.lenDepth(rel, False)
                l += nl
                nd += 1 # returns 0 if sublist is not nested
                if nd > d:
                    d = nd
            else:
                l += 1
                if includeSelf:
                    l += 1 # root relationships include root in addition
        if includeSelf:
            d += 1
        return (l, d)
    
    @property
    def propertyView(self):
        return (((u"id", self.id),
                 (u"abstract", self.abstract),
                 (u"definition", self.definitionNodeView)) +
                self.definitionLabelsView)
        
    def __repr__(self):
        return (u"modelRelationshipDefinitionNode[{0}]{1})".format(self.objectId(),self.propertyView))
    
class ModelConceptRelationshipDefinitionNode(ModelRelationshipDefinitionNode):
    def init(self, modelDocument):
        super(ModelConceptRelationshipDefinitionNode, self).init(modelDocument)
    
    def hasAspect(self, structuralNode, aspect):
        return aspect == Aspect.CONCEPT

    @property
    def arcrole(self):
        return XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"arcrole")

    @property
    def arcQname(self):
        arcnameElt = XmlUtil.child(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"arcname")
        if arcnameElt is not None:
            return qname( arcnameElt, XmlUtil.text(arcnameElt) )
        return None

    @property
    def linkQname(self):
        linknameElt = XmlUtil.child(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"linkname")
        if linknameElt is not None:
            return qname( linknameElt, XmlUtil.text(linknameElt) )
        return None
    

    def compile(self):
        if not hasattr(self, u"arcroleExpressionProg"):
            self.arcroleExpressionProg = XPathParser.parse(self, self.arcroleExpression, self, u"arcroleExpressionProg", Trace.VARIABLE)
            self.linkQnameExpressionProg = XPathParser.parse(self, self.linkQnameExpression, self, u"linkQnameExpressionProg", Trace.VARIABLE)
            self.arcQnameExpressionProg = XPathParser.parse(self, self.arcQnameExpression, self, u"arcQnameExpressionProg", Trace.VARIABLE)
            super(ModelConceptRelationshipDefinitionNode, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelConceptRelationshipDefinitionNode, self).variableRefs(
                                                [p for p in (self.arcroleExpressionProg,
                                                             self.linkQnameExpressionProg, self.arcQnameExpressionProg)
                                                 if p], varRefSet)

    def evalArcrole(self, xpCtx, fact=None):
        if self.arcrole:
            return self.arcrole
        return xpCtx.evaluateAtomicValue(self.arcroleExpressionProg, u'xs:anyURI', fact)
    
    def evalLinkQname(self, xpCtx, fact=None):
        if self.linkQname:
            return self.linkQname
        return xpCtx.evaluateAtomicValue(self.linkQnameExpressionProg, u'xs:QName', fact)
    
    def evalArcQname(self, xpCtx, fact=None):
        if self.arcQname:
            return self.arcQname
        return xpCtx.evaluateAtomicValue(self.arcQnameExpressionProg, u'xs:QName', fact)

    @property
    def arcroleExpression(self):
        return XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"arcroleExpression")

    @property
    def linkQnameExpression(self):
        return XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"linknameExpression")

    @property
    def arcQnameExpression(self):
        return XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"arcnameExpression")
    
    def coveredAspect(self, ordCntx=None):
        return Aspect.CONCEPT

    def relationships(self, structuralNode):
        self._sourceQname = structuralNode.evaluate(self, self.evalRrelationshipSourceQname) or XbrlConst.qnXfiRoot
        linkrole = structuralNode.evaluate(self, self.evalLinkrole)
        if not linkrole:
            linkrole = u"XBRL-all-linkroles"
        linkQname = (structuralNode.evaluate(self, self.evalLinkQname) or () )
        arcrole = (structuralNode.evaluate(self, self.evalArcrole) or () )
        arcQname = (structuralNode.evaluate(self, self.evalArcQname) or () )
        self._axis = (structuralNode.evaluate(self, self.evalAxis) or () )
        self._generations = (structuralNode.evaluate(self, self.evalGenerations) or () )
        return concept_relationships(self.modelXbrl.rendrCntx, 
                                     None, 
                                     (self._sourceQname,
                                      linkrole,
                                      arcrole,
                                      self._axis.replace(u'-or-self',u''),
                                      self._generations,
                                      linkQname,
                                      arcQname),
                                     True) # return nested lists representing concept tree nesting
    
class ModelDimensionRelationshipDefinitionNode(ModelRelationshipDefinitionNode):
    def init(self, modelDocument):
        super(ModelDimensionRelationshipDefinitionNode, self).init(modelDocument)
    
    def hasAspect(self, structuralNode, aspect):
        return aspect == self.coveredAspect(structuralNode) or aspect == Aspect.DIMENSIONS
    
    def aspectValue(self, xpCtx, aspect, inherit=None):
        if aspect == Aspect.DIMENSIONS:
            return (self.coveredAspect(xpCtx), )
        return None
    
    def aspectsCovered(self):
        return set([self.dimensionQname])

    @property
    def dimensionQname(self):
        dimensionElt = XmlUtil.child(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"dimension")
        if dimensionElt is not None:
            return qname( dimensionElt, XmlUtil.text(dimensionElt) )
        return None

    @property
    def dimensionQnameExpression(self):
        return XmlUtil.childText(self, (XbrlConst.table, XbrlConst.tableMMDD, XbrlConst.table201305, XbrlConst.table201301, XbrlConst.table2011), u"dimensionExpression")

    def compile(self):
        if not hasattr(self, u"dimensionQnameExpressionProg"):
            self.dimensionQnameExpressionProg = XPathParser.parse(self, self.dimensionQnameExpression, self, u"dimensionQnameExpressionProg", Trace.VARIABLE)
            super(ModelDimensionRelationshipDefinitionNode, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelDimensionRelationshipDefinitionNode, self).variableRefs(self.dimensionQnameExpressionProg, varRefSet)

    def evalDimensionQname(self, xpCtx, fact=None):
        if self.dimensionQname:
            return self.dimensionQname
        return xpCtx.evaluateAtomicValue(self.dimensionQnameExpressionProg, u'xs:QName', fact)
    
    def coveredAspect(self, structuralNode=None):
        try:
            return self._coveredAspect
        except AttributeError:
            self._coveredAspect = self.dimRelationships(structuralNode, getDimQname=True)
            return self._coveredAspect
        
    def relationships(self, structuralNode):
        return self.dimRelationships(structuralNode, getMembers=True)
    
    def dimRelationships(self, structuralNode, getMembers=False, getDimQname=False):
        self._dimensionQname = structuralNode.evaluate(self, self.evalDimensionQname)
        self._sourceQname = structuralNode.evaluate(self, self.evalRrelationshipSourceQname) or XbrlConst.qnXfiRoot
        linkrole = structuralNode.evaluate(self, self.evalLinkrole)
        if not linkrole and getMembers:
            linkrole = u"XBRL-all-linkroles"
        dimConcept = self.modelXbrl.qnameConcepts.get(self._dimensionQname)
        sourceConcept = self.modelXbrl.qnameConcepts.get(self._sourceQname)
        self._axis = (structuralNode.evaluate(self, self.evalAxis) or () )
        self._generations = (structuralNode.evaluate(self, self.evalGenerations) or () )
        if ((self._dimensionQname and (dimConcept is None or not dimConcept.isDimensionItem)) or
            (self._sourceQname and self._sourceQname != XbrlConst.qnXfiRoot and (
                    sourceConcept is None or not sourceConcept.isItem))):
            return ()
        if dimConcept is not None:
            if getDimQname:
                return self._dimensionQname
            if sourceConcept is None:
                sourceConcept = dimConcept
        if getMembers:
            return concept_relationships(self.modelXbrl.rendrCntx, 
                                         None, 
                                         (self._sourceQname,
                                          linkrole,
                                          u"XBRL-dimensions",  # all dimensions arcroles
                                          self._axis.replace(u'-or-self',u''),
                                          self._generations),
                                         True) # return nested lists representing concept tree nesting
        if getDimQname:
            if sourceConcept is not None:
                # look back from member to a dimension
                return self.stepDimRel(sourceConcept, linkrole)
            return None
        
    def stepDimRel(self, stepConcept, linkrole):
        if stepConcept.isDimensionItem:
            return stepConcept.qname
        for rel in self.modelXbrl.relationshipSet(u"XBRL-dimensions").toModelObject(stepConcept):
            if not linkrole or linkrole == rel.consecutiveLinkrole:
                dim = self.stepDimRel(rel.fromModelObject, rel.linkrole)
                if dim:
                    return dim
        return None
        
coveredAspectToken = {u"concept": Aspect.CONCEPT, 
                      u"entity-identifier": Aspect.VALUE, 
                      u"period-start": Aspect.START, u"period-end": Aspect.END, 
                      u"period-instant": Aspect.INSTANT, u"period-instant-end": Aspect.INSTANT_END, 
                      u"unit": Aspect.UNIT}

class ModelOpenDefinitionNode(ModelDefinitionNode):
    def init(self, modelDocument):
        super(ModelOpenDefinitionNode, self).init(modelDocument)

# deprecated 2013-05-17
class ModelSelectionDefinitionNode(ModelOpenDefinitionNode):
    def init(self, modelDocument):
        super(ModelSelectionDefinitionNode, self).init(modelDocument)
        
    @property
    def descendantArcroles(self):        
        return (XbrlConst.tableDefinitionNodeMessage201301, XbrlConst.tableAxisMessage2011, XbrlConst.tableDefinitionNodeSelectionMessage201301, XbrlConst.tableAxisSelectionMessage2011)
        
    def clear(self):
        XPathParser.clearNamedProg(self, u"selectProg")
        super(ModelSelectionDefinitionNode, self).clear()
    
    def coveredAspect(self, structuralNode=None):
        try:
            return self._coveredAspect
        except AttributeError:
            coveredAspect = self.get(u"coveredAspect")
            if coveredAspect in coveredAspectToken:
                self._coveredAspect = coveredAspectToken[coveredAspect]
            else:  # must be a qname
                self._coveredAspect = qname(self, coveredAspect)
            return self._coveredAspect
        
    def aspectsCovered(self):
        return set([self.coveredAspect])

    def hasAspect(self, structuralNode, aspect):
        return aspect == self.coveredAspect() or (isinstance(self._coveredAspect,QName) and aspect == Aspect.DIMENSIONS)
    
    @property
    def select(self):
        return self.get(u"select")
    
    def compile(self):
        if not hasattr(self, u"selectProg"):
            self.selectProg = XPathParser.parse(self, self.select, self, u"select", Trace.PARAMETER)
            super(ModelSelectionDefinitionNode, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelSelectionDefinitionNode, self).variableRefs(self.selectProg, varRefSet)
        
    def evaluate(self, xpCtx, typeQname=None):
        if typeQname:
            return xpCtx.evaluateAtomicValue(self.selectProg, typeQname)
        else:
            return xpCtx.flattenSequence(xpCtx.evaluate(self.selectProg, None))
            
aspectNodeAspectCovered = {u"conceptAspect": Aspect.CONCEPT,
                           u"unitAspect": Aspect.UNIT,
                           u"entityIdentifierAspect": Aspect.ENTITY_IDENTIFIER,
                           u"periodAspect": Aspect.PERIOD}

class ModelFilterDefinitionNode(ModelOpenDefinitionNode):
    def init(self, modelDocument):
        super(ModelFilterDefinitionNode, self).init(modelDocument)
    
    @property
    def descendantArcroles(self):        
        return (XbrlConst.tableAspectNodeFilter, XbrlConst.tableAspectNodeFilterMMDD, XbrlConst.tableAspectNodeFilter201305, XbrlConst.tableFilterNodeFilter2011, XbrlConst.tableAxisFilter2011,XbrlConst.tableAxisFilter201205, XbrlConst.tableDefinitionNodeMessage201301, XbrlConst.tableAxisMessage2011,
                XbrlConst.tableDefinitionNodeSubtree, XbrlConst.tableDefinitionNodeSubtreeMMDD, XbrlConst.tableDefinitionNodeSubtree201305, XbrlConst.tableDefinitionNodeSubtree201301, XbrlConst.tableAxisSubtree2011, XbrlConst.tableDefinitionNodeMessage201301, XbrlConst.tableAxisMessage2011)
    
        
    @property
    def filterRelationships(self):
        try:
            return self._filterRelationships
        except AttributeError:
            rels = [] # order so conceptName filter is first (if any) (may want more sorting in future)
            for rel in self.modelXbrl.relationshipSet((XbrlConst.tableAspectNodeFilter, XbrlConst.tableAspectNodeFilterMMDD, XbrlConst.tableAspectNodeFilter201305, XbrlConst.tableFilterNodeFilter2011, XbrlConst.tableAxisFilter2011,XbrlConst.tableAxisFilter201205)).fromModelObject(self):
                if isinstance(rel.toModelObject, ModelConceptName):
                    rels.insert(0, rel)  # put conceptName filters first
                else:
                    rels.append(rel)
            self._filterRelationships = rels
            return rels
    
    def hasAspect(self, structuralNode, aspect):
        return aspect in self.aspectsCovered()
    
    def aspectsCovered(self, varBinding=None):
        try:
            return self._aspectsCovered
        except AttributeError:
            self._aspectsCovered = set()
            self._dimensionsCovered = set()
            self.includeUnreportedValue = False
            if self.localName == u"aspectNode": # after 2-13-05-17
                aspectElt = XmlUtil.child(self, self.namespaceURI, (u"conceptAspect", u"unitAspect", u"entityIdentifierAspect", u"periodAspect", u"dimensionAspect"))
                if aspectElt is not None:
                    if aspectElt.localName == u"dimensionAspect":
                        dimQname = qname(aspectElt, aspectElt.textValue)
                        self._aspectsCovered.add(dimQname)
                        self._aspectsCovered.add(Aspect.DIMENSIONS)
                        self._dimensionsCovered.add(dimQname)
                        self.includeUnreportedValue = aspectElt.get(u"includeUnreportedValue") in (u"true", u"1")
                    else:
                        self._aspectsCovered.add(aspectNodeAspectCovered[aspectElt.localName])                                                  
            else:
                # filter node (prior to 2013-05-17)
                for rel in self.filterRelationships:
                    if rel.isCovered:
                        _filter = rel.toModelObject
                        self._aspectsCovered |= _filter.aspectsCovered(varBinding)
                self._dimensionsCovered = set(aspect for aspect in self._aspectsCovered if isinstance(aspect,QName))
                if self._dimensionsCovered:
                    self._aspectsCovered.add(Aspect.DIMENSIONS)
            return self._aspectsCovered

    def aspectValue(self, xpCtx, aspect, inherit=None):
        if aspect == Aspect.DIMENSIONS:
            return self._dimensionsCovered
        # does not apply to filter, value can only come from a bound fact
        return None
    
    def filteredFactsPartitions(self, xpCtx, facts):
        filteredFacts = formulaEvaluatorFilterFacts(xpCtx, VariableBinding(xpCtx), 
                                                    facts, self.filterRelationships, None)
        if not self.includeUnreportedValue:
            # remove unreported falue
            reportedAspectFacts = set()
            for fact in filteredFacts:
                if all(fact.context is not None and
                       isinstance(fact.context.dimValue(dimAspect), ModelDimensionValue)
                       for dimAspect in self._dimensionsCovered):
                    reportedAspectFacts.add(fact)
        else:
            reportedAspectFacts = filteredFacts
        return factsPartitions(xpCtx, reportedAspectFacts, self.aspectsCovered())
        
    @property
    def propertyView(self):
        return (((u"id", self.id),
                 (u"aspect", u", ".join(aspectStr(aspect)
                                      for aspect in self.aspectsCovered()
                                      if aspect != Aspect.DIMENSIONS)),
                 (u"definition", self.definitionNodeView)) +
                self.definitionLabelsView)
        
        

from arelle.ModelObjectFactory import elementSubstitutionModelClass
elementSubstitutionModelClass.update((
    # IWD
    (XbrlConst.qnTableTableMMDD, ModelTable),
    (XbrlConst.qnTableBreakdownMMDD, ModelBreakdown),
    (XbrlConst.qnTableRuleSetMMDD, ModelRuleSet),
    (XbrlConst.qnTableRuleNodeMMDD, ModelRuleDefinitionNode),
    (XbrlConst.qnTableConceptRelationshipNodeMMDD, ModelConceptRelationshipDefinitionNode),
    (XbrlConst.qnTableDimensionRelationshipNodeMMDD, ModelDimensionRelationshipDefinitionNode),
    (XbrlConst.qnTableAspectNodeMMDD, ModelFilterDefinitionNode),
    # PWD 2013-08-28
    (XbrlConst.qnTableTable, ModelTable),
    (XbrlConst.qnTableBreakdown, ModelBreakdown),
    (XbrlConst.qnTableRuleSet, ModelRuleSet),
    (XbrlConst.qnTableRuleNode, ModelRuleDefinitionNode),
    (XbrlConst.qnTableConceptRelationshipNode, ModelConceptRelationshipDefinitionNode),
    (XbrlConst.qnTableDimensionRelationshipNode, ModelDimensionRelationshipDefinitionNode),
    (XbrlConst.qnTableAspectNode, ModelFilterDefinitionNode),
    # PWD 2013-05-17
    (XbrlConst.qnTableTable201305, ModelTable),
    (XbrlConst.qnTableBreakdown201305, ModelBreakdown),
    (XbrlConst.qnTableRuleNode201305, ModelRuleDefinitionNode),
    (XbrlConst.qnTableConceptRelationshipNode201305, ModelConceptRelationshipDefinitionNode),
    (XbrlConst.qnTableDimensionRelationshipNode201305, ModelDimensionRelationshipDefinitionNode),
    (XbrlConst.qnTableAspectNode201305, ModelFilterDefinitionNode),
    # PWD 2013-01-17
    (XbrlConst.qnTableTable201301, ModelTable),
    (XbrlConst.qnTableRuleNode201301, ModelRuleDefinitionNode),
    (XbrlConst.qnTableCompositionNode201301, ModelCompositionDefinitionNode),
    (XbrlConst.qnTableConceptRelationshipNode201301, ModelConceptRelationshipDefinitionNode),
    (XbrlConst.qnTableDimensionRelationshipNode201301, ModelDimensionRelationshipDefinitionNode),
    (XbrlConst.qnTableSelectionNode201301, ModelSelectionDefinitionNode),
    (XbrlConst.qnTableFilterNode201301, ModelFilterDefinitionNode),
    (XbrlConst.qnTableTupleNode201301, ModelTupleDefinitionNode),
    # PWD 2011 Montreal
    (XbrlConst.qnTableTable2011, ModelTable),
    (XbrlConst.qnTableRuleAxis2011, ModelRuleDefinitionNode),
    (XbrlConst.qnTableCompositionAxis2011, ModelCompositionDefinitionNode),
    (XbrlConst.qnTableConceptRelationshipAxis2011, ModelConceptRelationshipDefinitionNode),
    (XbrlConst.qnTableSelectionAxis2011, ModelSelectionDefinitionNode),
    (XbrlConst.qnTableFilterAxis2011, ModelFilterDefinitionNode),
    (XbrlConst.qnTableTupleAxis2011, ModelTupleDefinitionNode),
    (XbrlConst.qnTableDimensionRelationshipAxis2011, ModelDimensionRelationshipDefinitionNode),
    # Eurofiling
    (XbrlConst.qnEuTable, ModelEuTable),
    (XbrlConst.qnEuAxisCoord, ModelEuAxisCoord),
     ))

# import after other modules resolved to prevent circular references
from arelle.FunctionXfi import concept_relationships
