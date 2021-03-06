u'''
Created on Dec 30, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from __future__ import division  # expect 3.2 integer division even in 2.7
from arelle.XPathParser import (VariableRef, QNameDef, OperationDef, RangeDecl, Expr, ProgHeader,
                          exceptionErrorIndication)
from arelle import (ModelXbrl, XbrlConst, XmlUtil)
from arelle.ModelObject import ModelObject, ModelAttribute
from arelle.ModelInstanceObject import ModelFact, ModelInlineFact
from arelle.ModelValue import (qname,QName,dateTime, DateTime, DATEUNION, DATE, DATETIME, anyURI, AnyURI)
from arelle.XmlValidate import UNKNOWN, VALID, VALID_NO_CONTENT, validate
from arelle.PluginManager import pluginClassMethods
from decimal import Decimal, InvalidOperation
from lxml import etree
from types import LambdaType

class XPathException(Exception):
    def __init__(self, progStep, code, message):
        self.column = None
        if isinstance(progStep, OperationDef):
            self.line = progStep.sourceStr
            self.column = progStep.loc
        elif isinstance(progStep, ProgHeader):
            self.line = progStep.sourceStr
        elif isinstance(progStep, XPathContext) and progStep.progHeader:
            self.line = progStep.sourceStr
        else:
            self.line = u"(not available)"
        self.code = unicode(code)  # called with qname or string, qname -> prefixed name string
        self.message = message
        self.args = ( self.__repr__(), )
    def __repr__(self):
        if self.column:
            return _(u'[{0}] exception at {1} in {2}').format(self.code, self.column, self.message)
        else:
            return _(u'[{0}] exception {1}').format(self.code, self.message)
    @property
    def sourceErrorIndication(self):
        return exceptionErrorIndication(self)
            
    
class FunctionNumArgs(Exception):
    def __init__(self, errCode=u'err:XPST0017', errText=None):
        self.errCode = errCode
        self.errText = errText or _(u'Number of arguments do not match signature arity')
        self.args = ( self.__repr__(), )
    def __repr__(self):
        return _(u"Exception: Number of arguments mismatch")
    
class FunctionArgType(Exception):
    def __init__(self, argIndex, expectedType, foundObject=u'', errCode=u'err:XPTY0004'):
        self.errCode = errCode
        self.argNum = (argIndex + 1) if isinstance(argIndex, _NUM_TYPES) else argIndex # may be string
        self.expectedType = expectedType
        self.foundObject = foundObject
        self.args = ( self.__repr__(), )
    def __repr__(self):
        return _(u"[{0}]: Arg {1} expected type {2}").format(self.errCode, self.argNum, self.expectedType)
    
class FunctionNotAvailable(Exception):
    def __init__(self, name=None):
        self.name = name
        self.args = ( self.__repr__(), )
    def __repr__(self):
        return _(u"Exception, function implementation not available: {0}").format(self.name)
    
class RunTimeExceededException(Exception):
    def __init__(self):
        self.args = ( self.__repr__(), )
    def __repr__(self):
        return _(u"Formula run time exceeded")

   
def create(modelXbrl, inputXbrlInstance=None, sourceElement=None):
    return XPathContext(modelXbrl, 
                        inputXbrlInstance if inputXbrlInstance else modelXbrl.modelDocument,
                        sourceElement)

# note: 2.2% execution time savings by having these sets/lists as constant instead of in expression where used
VALUE_OPS = set([u'+', u'-', u'*', u'div', u'idiv', u'mod', u'to', u'gt', u'ge', u'eq', u'ne', u'lt', u'le'])
GENERALCOMPARISON_OPS = set([u'>', u'>=', u'=', u'!=', u'<', u'<='])
NODECOMPARISON_OPS = set([u'is', u'>>', u'<<'])
COMBINING_OPS = set([u'intersect',u'except',u'union',u'|'])
LOGICAL_OPS = set([u'and', u'or'])
UNARY_OPS = set([u'u+', u'u-'])
FORSOMEEVERY_OPS = set([u'for',u'some',u'every'])
PATH_OPS = set([u'/', u'//', u'rootChild', u'rootDescendant'])
SEQUENCE_TYPES = (tuple,list,set)

class XPathContext(object):
    def __init__(self, modelXbrl, inputXbrlInstance, sourceElement, inScopeVars=None):
        self.modelXbrl = modelXbrl
        self.isRunTimeExceeded = False
        self.inputXbrlInstance = inputXbrlInstance
        self.outputLastContext = {}   # last context element output per output instance
        self.outputLastUnit = {}
        self.outputLastFact = {}
        self.outputFirstFact = {}
        self.sourceElement = sourceElement
        self.contextItem = self.inputXbrlInstance.xmlRootElement
        self.progHeader = None
        self.traceType = None
        self.variableSet = None
        self.inScopeVars = {} if inScopeVars is None else inScopeVars
        self.cachedFilterResults = {}
        if inputXbrlInstance: 
            self.inScopeVars[XbrlConst.qnStandardInputInstance] = inputXbrlInstance.modelXbrl
        self.customFunctions = {}
        for pluginXbrlMethod in pluginClassMethods(u"Formula.CustomFunctions"):
            self.customFunctions.update(pluginXbrlMethod())
        
    def copy(self):  # shallow copy (for such as for Table LB table processiong
        xpCtxCpy = XPathContext(self.modelXbrl, self.inputXbrlInstance, self.sourceElement, 
                                self.inScopeVars.copy())
        # note: not currently duplicating cachedFilterResults
        return xpCtxCpy
            
    def close(self):
        self.outputLastContext.clear() # dereference
        self.outputLastUnit.clear()
        self.outputLastFact.clear()
        self.outputFirstFact.clear()
        self.inScopeVars.clear()
        self.cachedFilterResults.clear()
        self.__dict__.clear() # dereference everything
        
    def runTimeExceededCallback(self):
        self.isRunTimeExceeded = True
        
    @property
    def formulaOptions(self):
        return self.modelXbrl.modelManager.formulaOptions
        
    def evaluate(self, exprStack, contextItem=None, resultStack=None, parentOp=None):
        if resultStack is None: resultStack =  []
        if contextItem is None: contextItem = self.contextItem
        setProgHeader = False
        for p in exprStack:
            result = None
            if isinstance(p,QNameDef) or (p == u'*' and parentOp in (u'/', u'//')): # path step QName or wildcard
                # step axis operation
                if len(resultStack) == 0 or not self.isNodeSequence(resultStack[-1]):
                    resultStack.append( [ contextItem, ] )
                result = self.stepAxis(parentOp, p, resultStack.pop() )
            elif isinstance(p,_STR_NUM_TYPES):
                result = p
            elif isinstance(p,VariableRef):
                if p.name in self.inScopeVars:
                    result = self.inScopeVars[p.name]
                    # uncomment to allow lambdas as variable values (for deferred processing if needed)
                    #if isinstance(result, LambdaType):
                    #    result = result()  # dereference lambda-valued variables
                    if result is None: # None atomic result is XPath empty sequence
                        result = []  # subsequent processing discards None results
            elif isinstance(p,OperationDef):
                op = p.name
                if isinstance(op, QNameDef): # function call
                    args = self.evaluate(p.args, contextItem=contextItem)
                    ns = op.namespaceURI; localname = op.localName
                    try:
                        from arelle import (FunctionXs, FunctionFn, FunctionXfi, FunctionIxt, FunctionCustom)
                        if op in self.modelXbrl.modelCustomFunctionSignatures:
                            result = FunctionCustom.call(self, p, op, contextItem, args)
                        elif op.unprefixed and localname in set([u'attribute', u'comment', u'document-node', u'element', 
                           u'item', u'node', u'processing-instruction', u'schema-attribute', u'schema-element', u'text']):
                            # step axis operation
                            if len(resultStack) == 0 or not self.isNodeSequence(resultStack[-1]):
                                if isinstance(contextItem, (tuple,list)):
                                    resultStack.append( contextItem )
                                else:
                                    resultStack.append( [ contextItem, ] )
                            result = self.stepAxis(parentOp, p, resultStack.pop() )
                        elif op.unprefixed or ns == XbrlConst.fn:
                            result = FunctionFn.call(self, p, localname, contextItem, args)
                        elif ns == XbrlConst.xfi or ns == XbrlConst.xff:
                            result = FunctionXfi.call(self, p, localname, args)
                        elif ns == XbrlConst.xsd:
                            result = FunctionXs.call(self, p, localname, args)
                        elif ns in FunctionIxt.ixtNamespaceURIs:
                            result = FunctionIxt.call(self, p, localname, args)
                        else:
                            raise XPathException(p, u'err:XPST0017', _(u'Function call not identified: {0}.').format(op))
                    except FunctionNumArgs, err:
                        raise XPathException(p, err.errCode, u"{}: {}".format(err.errText, op))
                    except FunctionArgType, err:
                        raise XPathException(p, err.errCode, _(u'Argument {0} does not match expected type {1} for {2} {3}.')
                                             .format(err.argNum, err.expectedType, op, err.foundObject))
                    except FunctionNotAvailable:
                        raise XPathException(p, u'err:XPST0017', _(u'Function named {0} does not have a custom or built-in implementation.').format(op))
                elif op in VALUE_OPS:
                    # binary arithmetic operations and value comparisons
                    s1 = self.atomize( p, resultStack.pop() ) if len(resultStack) > 0 else []
                    s2 = self.atomize( p, self.evaluate(p.args, contextItem=contextItem) )
                    # value comparisons
                    if len(s1) > 1 or len(s2) > 1:
                        raise XPathException(p, u'err:XPTY0004', _(u"Value operation '{0}' sequence length error").format(op))
                    if len(s1) == 0 or len(s2) == 0:
                        result = []
                    else:
                        op1 = s1[0]
                        op2 = s2[0]
                        from arelle.FunctionUtil import (testTypeCompatiblity)
                        testTypeCompatiblity( self, p, op, op1, op2 )
                        if type(op1) != type(op2) and op in (u'+', u'-', u'*', u'div', u'idiv', u'mod'):
                            # check if type promotion needed (Decimal-float, not needed for integer-Decimal)
                            if isinstance(op1,Decimal) and isinstance(op2,float):
                                op1 = float(op1) # per http://http://www.w3.org/TR/xpath20/#dt-type-promotion 1b
                            elif isinstance(op2,Decimal) and isinstance(op1,float):
                                op2 = float(op2)
                        if op == u'+':
                            result = op1 + op2 
                        elif op == u'-':
                            result = op1 - op2
                        elif op == u'*':
                            result = op1 * op2
                        elif op in (u'div', u'idiv', u"mod"):
                            try:
                                if op == u'div':
                                    result = op1 / op2
                                elif op == u'idiv':
                                    result = op1 // op2
                                elif op == u'mod':
                                    result = op1 % op2
                            except ZeroDivisionError:
                                raise XPathException(p, u'err:FOAR0001', _(u'Attempt to divide by zero: {0} {1} {2}.')
                                                     .format(op1, op, op2))
                        elif op == u'ge':
                            result = op1 >= op2
                        elif op == u'gt':
                            result = op1 > op2
                        elif op == u'le':
                            result = op1 <= op2
                        elif op == u'lt':
                            result = op1 < op2
                        elif op == u'eq':
                            result = op1 == op2
                        elif op == u'ne':
                            result = op1 != op2
                        elif op == u'to':
                            result = _RANGE( _INT(op1), _INT(op2) + 1 )
                elif op in GENERALCOMPARISON_OPS:
                    # general comparisons
                    s1 = self.atomize( p, resultStack.pop() ) if len(resultStack) > 0 else []
                    s2 = self.atomize( p, self.evaluate(p.args, contextItem=contextItem) )
                    result = [];
                    for op1 in s1:
                        for op2 in s2:
                            if op == u'>=':
                                result = op1 >= op2
                            elif op == u'>':
                                result = op1 > op2
                            elif op == u'<=':
                                result = op1 <= op2
                            elif op == u'<':
                                result = op1 < op2
                            elif op == u'=':
                                result = op1 == op2
                            elif op == u'!=':
                                result = op1 != op2
                            if result:
                                break
                        if result:
                            break
                elif op in NODECOMPARISON_OPS:
                    # node comparisons
                    s1 = resultStack.pop() if len(resultStack) > 0 else []
                    s2 = self.evaluate(p.args, contextItem=contextItem)
                    if len(s1) > 1 or len(s2) > 1 or not self.isNodeSequence(s1) or not self.isNodeSequence(s2[0]):
                        raise XPathException(p, u'err:XPTY0004', _(u'Node comparison sequence error'))
                    if len(s1) == 0 or len(s2[0]) == 0:
                        result = []
                    else:
                        n1 = s1[0]
                        n2 = s2[0][0]
                        result = False;
                        for op1 in s1:
                            for op2 in s2:
                                if op == u'is':
                                    result = n1 == n2
                                elif op == u'>>':
                                    result = op1 > op2
                                elif op == u'<<':
                                    result = op1 <= op2
                            if result:
                                break
                elif op in COMBINING_OPS:
                    # node comparisons
                    s1 = resultStack.pop() if len(resultStack) > 0 else []
                    s2 = self.flattenSequence(self.evaluate(p.args, contextItem=contextItem))
                    if not self.isNodeSequence(s1) or not self.isNodeSequence(s2):
                        raise XPathException(p, u'err:XPTY0004', _(u'Node operation sequence error'))
                    set1 = set(s1)
                    set2 = set(s2)
                    if op == u'intersect':
                        resultset = set1 & set2
                    elif op == u'except':
                        resultset = set1 - set2
                    elif op == u'union' or op == u'|':
                        resultset = set1 | set2
                    # convert to a list in document order
                    result = self.documentOrderedNodes(resultset)
                elif op in LOGICAL_OPS:
                    # general comparisons
                    if len(resultStack) == 0:
                        result = []
                    else:
                        op1 = self.effectiveBooleanValue( p, resultStack.pop() ) if len(resultStack) > 0 else False
                        op2 = self.effectiveBooleanValue( p, self.evaluate(p.args, contextItem=contextItem) )
                        result = False;
                        if op == u'and':
                            result = op1 and op2
                        elif op == u'or':
                            result = op1 or op2
                elif op in UNARY_OPS:
                    s1 = self.atomize( p, self.evaluate(p.args, contextItem=contextItem) )
                    if len(s1) > 1:
                        raise XPathException(p, u'err:XPTY0004', _(u'Unary expression sequence length error'))
                    if len(s1) == 0:
                        result = []
                    else:
                        op1 = s1[0]
                        if op == u'u+':
                            result = op1 
                        elif op == u'u-':
                            result = -op1
                elif op == u'instance':
                    result = False
                    s1 = self.flattenSequence( resultStack.pop() ) if len(resultStack) > 0 else []
                    arity = len(s1)
                    if len(p.args) > 1:
                        occurenceIndicator = p.args[1]
                        if (occurenceIndicator == u'?' and arity in (0,1) ) or \
                           (occurenceIndicator == u'+' and arity >= 1) or \
                           (occurenceIndicator == u'*'):
                            result = True
                    elif arity == 1:
                        result = True
                    if result and len(p.args) > 0:
                        t = p.args[0]
                        for x in s1:
                            if isinstance(t, QNameDef):
                                if t.namespaceURI == XbrlConst.xsd:
                                    tType = {
                                           u"integer": _INT_TYPES,
                                           u"string": _STR_BASE,
                                           u"decimal": Decimal,
                                           u"double": float,
                                           u"float": float,
                                           u"boolean": bool,
                                           u"QName": QName,
                                           u"anyURI": AnyURI,
                                           u"date": DateTime,
                                           u"dateTime": DateTime,
                                            }.get(t.localName)
                                    if tType:
                                        result = isinstance(x, tType)
                                        if result and tType == DateTime:
                                            result = x.dateOnly == (t.localName == u"date")
                            elif isinstance(t, OperationDef):
                                if t.name == u"element":
                                    if isinstance(x,ModelObject):
                                        if len(t.args) >= 1:
                                            qn = t.args[0]
                                            if qn== u'*' or (isinstance(qn,QNameDef) and qn == x):
                                                result = True
                                                if len(t.args) >= 2 and isinstance(t.args[1],QNameDef):
                                                    modelXbrl = x.modelDocument.modelXbrl
                                                    modelConcept = modelXbrl.qnameConcepts.get(qname(x))
                                                    if not modelConcept.instanceOfType(t.args[1]):
                                                        result = False
                                    else:
                                        result = False
                                # elif t.name == "item" comes here and result stays True
                            if not result: 
                                break
                elif op == u'sequence':
                    result = self.evaluate(p.args, contextItem=contextItem)
                elif op == u'predicate':
                    result = self.predicate(p, resultStack.pop()) if len(resultStack) > 0 else []
                elif op in FORSOMEEVERY_OPS: # for, some, every
                    result = []
                    self.evaluateRangeVars(op, p.args[0], p.args[1:], contextItem, result)
                elif op == u'if':
                    test = self.effectiveBooleanValue( p, self.evaluate(p.args[0].expr[0], contextItem=contextItem) )
                    result = self.evaluate(p.args[1 if test else 2].args, contextItem=contextItem)
                elif op == u'.':
                    result = contextItem
                elif op == u'..':
                    result = XmlUtil.parent(contextItem)
                elif op in PATH_OPS:
                    if op in (u'rootChild', u'rootDescendant'):
                        # fix up for multi-instance
                        resultStack.append( [self.inputXbrlInstance.xmlDocument,] )
                        op = u'/' if op == u'rootChild' else u'//'
                    # contains QNameDefs and predicates
                    if len(resultStack) > 0:
                        innerFocusNodes = resultStack.pop()
                    else:
                        innerFocusNodes = contextItem
                    navSequence = []
                    for innerFocusNode in self.flattenSequence(innerFocusNodes):
                        navSequence += self.evaluate(p.args, contextItem=innerFocusNode, parentOp=op)
                    result = self.documentOrderedNodes(self.flattenSequence(navSequence))
            elif isinstance(p,ProgHeader):
                self.progHeader = p
                from arelle.ModelFormulaObject import Trace
                if p.traceType not in (Trace.MESSAGE, Trace.CUSTOM_FUNCTION): 
                    self.traceType = p.traceType
                setProgHeader = True
            if result is not None:   # note: result can be False which gets appended to resultStack
                resultStack.append( self.flattenSequence( result ) )  
        if setProgHeader:
            self.progHeader = None                  
        return resultStack
    
    def evaluateBooleanValue(self, exprStack, contextItem=None):
        if len(exprStack) > 0 and isinstance(exprStack[0], ProgHeader):
            progHeader = exprStack[0]
            return self.effectiveBooleanValue(progHeader, self.evaluate(exprStack,contextItem))
        return False
                    
    def evaluateAtomicValue(self, exprStack, type, contextItem=None):
        if exprStack and len(exprStack) > 0 and isinstance(exprStack[0], ProgHeader):
            progHeader = exprStack[0]
            result = self.atomize( progHeader, self.evaluate( exprStack, contextItem=contextItem ) )
            if isinstance(type, QName) and type.namespaceURI == XbrlConst.xsd:
                type = u"xs:" + type.localName
            if isinstance(type,unicode):
                prefix,sep,localName = type.rpartition(u':')
                if prefix == u'xs':
                    if localName.endswith(u'*'): localName = localName[:-1]
                    if isinstance(result, (tuple,list,set)):
                        from arelle import (FunctionXs)
                        if type.endswith(u'*'):
                            return[FunctionXs.call(self,progHeader,localName,(r,)) for r in result]
                        elif len(result) > 0:
                            return FunctionXs.call(self,progHeader,localName,(result[0],))
                elif localName.startswith(u"item()"):
                    return result # can be any type
            else: # no conversion
                if len(result) == 0: return None
                elif len(result) == 1: return result[0]
                else: return result
        return None
                    
    def evaluateRangeVars(self, op, p, args, contextItem, result):
        if isinstance(p, RangeDecl):
            r = self.evaluate(p.bindingSeq, contextItem=contextItem)
            if len(r) == 1: # should be an expr single
                r = r[0]
                if isinstance(r, (tuple,list,set)):
                    if len(r) == 1 and isinstance(r[0],_RANGE):
                        r = r[0]
                    rvQname = p.rangeVar.name
                    hasPrevValue = rvQname in self.inScopeVars
                    if hasPrevValue: 
                        prevValue = self.inScopeVars[rvQname]
                    for rv in r:
                        self.inScopeVars[rvQname] = rv 
                        self.evaluateRangeVars(op, args[0], args[1:], contextItem, result)
                        if op != u'for' and len(result) > 0:
                            break	# short circuit evaluation
                    if op == u'every' and len(result) == 0:
                        result.append( True )   # true if no false result returned during iteration
                    if hasPrevValue: 
                        self.inScopeVars[rvQname] = prevValue
        elif isinstance(p, Expr):
            if p.name == u'return':
                result.append( self.evaluate(p.expr, contextItem=contextItem) )
            elif p.name == u'satisfies':
                boolresult = self.effectiveBooleanValue(p, self.evaluate(p.expr, contextItem=contextItem))
                if (op == u'every') != boolresult:
                    # stop short circuit eval
                    result.append( boolresult )
            
    def isNodeSequence(self, x):
        for el in x:
            if not isinstance(el,ModelObject):
                return False
        return True

    def stepAxis(self, op, p, sourceSequence):
        targetSequence = []
        for node in sourceSequence:
            if not isinstance(node,(ModelObject, etree._ElementTree, ModelAttribute)):
                raise XPathException(self.progHeader, u'err:XPTY0020', _(u'Axis step {0} context item is not a node: {1}').format(op, node))
            targetNodes = []
            if isinstance(p,QNameDef):
                ns = p.namespaceURI; localname = p.localName; axis = p.axis
                if p.isAttribute:
                    if isinstance(node,ModelObject):
                        attrTag = p.localName if p.unprefixed else p.clarkNotation
                        modelAttribute = None
                        try:
                            modelAttribute = node.xAttributes[attrTag]
                        except (AttributeError, TypeError, IndexError, KeyError):
                            # may be lax or deferred validated
                            try:
                                validate(node.modelXbrl, node, p)
                                modelAttribute = node.xAttributes[attrTag]
                            except (AttributeError, TypeError, IndexError, KeyError):
                                pass
                        if modelAttribute is None:
                            value = node.get(attrTag)
                            if value is not None:
                                targetNodes.append(ModelAttribute(node,p.clarkNotation,UNKNOWN,value,value,value))
                        elif modelAttribute.xValid >= VALID:
                                targetNodes.append(modelAttribute)
                elif op == u'/' or op is None:
                    if axis is None or axis == u"child":
                        if isinstance(node,(ModelObject, etree._ElementTree)):
                            targetNodes = XmlUtil.children(node, ns, localname)
                    elif axis == u"parent":
                        if isinstance(node,ModelAttribute):
                            parentNode = [ node.modelElement ]
                        else:
                            parentNode = [ XmlUtil.parent(node) ]
                        if (isinstance(node,ModelObject) and
                                (not ns or ns == parentNode.namespaceURI or ns == u"*") and
                            (localname == parentNode.localName or localname == u"*")):
                            targetNodes = [ parentNode ]
                    elif axis == u"self":
                        if (isinstance(node,ModelObject) and
                                (not ns or ns == node.namespaceURI or ns == u"*") and
                            (localname == node.localName or localname == u"*")):
                            targetNodes = [ node ]
                    elif axis.startswith(u"descendant"):
                        if isinstance(node,(ModelObject, etree._ElementTree)):
                            targetNodes = XmlUtil.descendants(node, ns, localname)
                            if (axis.endswith(u"-or-self") and
                                isinstance(node,ModelObject) and
                                (not ns or ns == node.namespaceURI or ns == u"*") and
                                (localname == node.localName or localname == u"*")):
                                targetNodes.append(node) 
                    elif axis.startswith(u"ancestor"):
                        if isinstance(node,ModelObject):
                            targetNodes = [ancestor
                                           for ancestor in XmlUtil.ancestors(node)
                                           if ((not ns or ns == ancestor.namespaceURI or ns == u"*") and
                                               (localname == ancestor.localName or localname == u"*"))]
                            if (axis.endswith(u"-or-self") and
                                isinstance(node,ModelObject) and
                                (not ns or ns == node.namespaceURI or ns == u"*") and
                                (localname == node.localName or localname == u"*")):
                                targetNodes.insert(0, node) 
                    elif axis.endswith(u"-sibling"):
                        if isinstance(node,ModelObject):
                            targetNodes = [sibling
                                           for sibling in node.itersiblings(preceding=axis.startswith(u"preceding"))
                                           if ((not ns or ns == sibling.namespaceURI or ns == u"*") and
                                               (localname == sibling.localName or localname == u"*"))]
                    elif axis == u"preceding":
                        if isinstance(node,ModelObject):
                            for preceding in node.getroottree().iter():
                                if preceding == node:
                                    break
                                elif ((not ns or ns == preceding.namespaceURI or ns == u"*") and
                                      (localname == preceding.localName or localname == u"*")):
                                    targetNodes.append(preceding)
                    elif axis == u"following":
                        if isinstance(node,ModelObject):
                            foundNode = False
                            for following in node.getroottree().iter():
                                if following == node:
                                    foundNode = True
                                elif (foundNode and
                                      (not ns or ns == following.namespaceURI or ns == u"*") and
                                      (localname == following.localName or localname == u"*")):
                                    targetNodes.append(following)
                elif op == u'//':
                    if isinstance(node,(ModelObject, etree. _ElementTree)):
                        targetNodes = XmlUtil.descendants(node, ns, localname)
                elif op == u'..':
                    if isinstance(node,ModelAttribute):
                        targetNodes = [ node.modelElement ]
                    else:
                        targetNodes = [ XmlUtil.parent(node) ]
            elif isinstance(p, OperationDef) and isinstance(p.name,QNameDef):
                if isinstance(node,ModelObject):
                    if p.name.localName == u"text": # note this is not string value, just child text
                        targetNodes = [node.textValue]
                    # todo: add element, attribute, node, etc...
            elif p == u'*':  # wildcard
                if op == u'/' or op is None:
                    if isinstance(node,(ModelObject, etree._ElementTree)):
                        targetNodes = XmlUtil.children(node, u'*', u'*')
                elif op == u'//':
                    if isinstance(node,(ModelObject, etree._ElementTree)):
                        targetNodes = XmlUtil.descendants(node, u'*', u'*')
            targetSequence.extend(targetNodes)
        return targetSequence
        
    def predicate(self, p, sourceSequence):
        targetSequence = []
        sourcePosition = 0
        for item in sourceSequence:
            sourcePosition += 1
            predicateResult = self.evaluate(p.args, contextItem=item)
            if len(predicateResult) == 1: predicateResult = predicateResult[0] # first result
            if len(predicateResult) == 1 and isinstance(predicateResult[0],_NUM_TYPES):
                result = predicateResult[0]
                if isinstance(result, bool):  # note that bool is subclass of int
                    if result:
                        targetSequence.append(item)
                elif sourcePosition == result:
                    targetSequence.append(item)
            elif self.effectiveBooleanValue(p, predicateResult):
                    targetSequence.append(item)
        return targetSequence
            
    def atomize(self, p, x):
        # sequence
        if isinstance(x, SEQUENCE_TYPES):
            sequence = []
            for item in self.flattenSequence(x):
                atomizedItem = self.atomize(p, item)
                if atomizedItem != []:
                    sequence.append(atomizedItem)
            return sequence
        # individual items
        if isinstance(x, _RANGE): 
            return x
        baseXsdType = None
        e = None
        if isinstance(x, ModelFact):
            if x.isTuple:
                raise XPathException(p, u'err:FOTY0012', _(u'Atomizing tuple {0} that does not have a typed value').format(x))
            if x.isNil:
                return []
            baseXsdType = x.concept.baseXsdType
            v = x.value # resolves default value
            e = x
        elif isinstance(x, ModelAttribute): # ModelAttribute is a tuple (below), check this first!
            return x.xValue
        else:
            if isinstance(x, ModelObject):
                e = x
            if e is not None:
                if getattr(e, u"xValid", 0) == VALID_NO_CONTENT:
                    raise XPathException(p, u'err:FOTY0012', _(u'Atomizing element {0} that does not have a typed value').format(x))
                if e.get(u"{http://www.w3.org/2001/XMLSchema-instance}nil") == u"true":
                    return []
                try:
                    if e.xValid >= VALID:
                        return e.xValue
                except AttributeError:
                    pass
                modelXbrl = x.modelXbrl
                modelConcept = modelXbrl.qnameConcepts.get(qname(x))
                if modelConcept is not None:
                    baseXsdType = modelConcept.baseXsdType
                v = x.stringValue
        if baseXsdType in (u"float", u"double"):
            try:
                x = float(v)
            except ValueError:
                raise XPathException(p, u'err:FORG0001', _(u'Atomizing {0} to a {1} does not have a proper value').format(x,baseXsdType))
        elif baseXsdType == u"decimal":
            try:
                x = Decimal(v)
            except InvalidOperation:
                raise XPathException(p, u'err:FORG0001', _(u'Atomizing {0} to decimal does not have a proper value'))
        elif baseXsdType in (u"integer",
                             u"nonPositiveInteger",u"negativeInteger",u"nonNegativeInteger",u"positiveInteger",
                             u"long",u"unsignedLong",
                             u"int",u"unsignedInt",
                             u"short",u"unsignedShort",
                             u"byte",u"unsignedByte"):
            try:
                x = _INT(v)
            except ValueError:
                raise XPathException(p, u'err:FORG0001', _(u'Atomizing {0} to an integer does not have a proper value').format(x))
        elif baseXsdType == u"boolean":
            x = (v == u"true" or v == u"1")
        elif baseXsdType == u"QName" and e is not None:
            x = qname(e, v)
        elif baseXsdType == u"anyURI":
            x = anyURI(v.strip())
        elif baseXsdType in (u"normalizedString",u"token",u"language",u"NMTOKEN",u"Name",u"NCName",u"ID",u"IDREF",u"ENTITY"):
            x = v.strip()
        elif baseXsdType == u"XBRLI_DATEUNION":
            x = dateTime(v, type=DATEUNION)
        elif baseXsdType == u"date":
            x = dateTime(v, type=DATE)
        elif baseXsdType == u"dateTime":
            x = dateTime(v, type=DATETIME)
        elif baseXsdType == u"noContent":
            x = None # can't be atomized
        elif baseXsdType:
            x = unicode(v)
        return x
    
    def effectiveBooleanValue(self, p, x):
        from arelle.FunctionFn import boolean
        return boolean( self, p, None, (self.flattenSequence(x),) )
    
    def traceEffectiveVariableValue(self, elt, varname):
        # used for tracing variable value
        if varname.startswith(u'$'):
            varQname = qname(elt,varname[1:])
            if varQname in self.inScopeVars:
                varValue = self.inScopeVars[varQname]
                if isinstance(varValue, ModelFact):
                    return varValue.effectiveValue
                else:
                    return unicode(varValue)
            else:
                return varname
        else: # not a variable name
            return varname

    # flatten into a sequence
    def flattenSequence(self, x, sequence=None):
        if sequence is None: 
            if not isinstance(x, SEQUENCE_TYPES):
                if x is None:
                    return [] # none as atomic value is an empty sequence in xPath semantics
                return [x]
            sequence = []
        for el in x:
            if isinstance(el, SEQUENCE_TYPES):
                self.flattenSequence(el, sequence)
            else:
                sequence.append(el)
        return sequence
    u'''  (note: slice operation makes the below slower than the above by about 15%)
    def flattenSequence(self, x):
        sequenceTypes=SEQUENCE_TYPES
        if not isinstance(x, sequenceTypes):
            return [x]
        needsFlattening = False  # no need to do anything
        for i, e in enumerate(x):
            if isinstance(e, sequenceTypes):
                needsFlattening = True # needs action at i
                break            
        if needsFlattening:
            x = list(x) # start with fresh copy of list
            while i < len(x):
                if isinstance(x[i], sequenceTypes):
                    x[i:i+1] = list(x[i])
                else:
                    i += 1
        return x            
    '''
    
    # order nodes
    def documentOrderedNodes(self, x):
        l = set()  # must have unique nodes only
        for e in x:
            if isinstance(e,ModelObject):
                h = e.sourceline
            elif isinstance(e,ModelAttribute):
                h = e.modelElement.sourceline
            else:
                h = 0
            l.add((h,e))
        return [e for h,e in sorted(l, key=lambda h: h[0] or 0)]  # or 0 in case sourceline is None
    
    def modelItem(self, x):
        if isinstance(x, (ModelFact, ModelInlineFact)) and x.isItem:
            return x
        return None

    def modelInstance(self, x):
        if isinstance(x, ModelXbrl.ModelXbrl):
            return x
        if isinstance(x, ModelObject):
            return x.modelXbrl
        return None
        
        