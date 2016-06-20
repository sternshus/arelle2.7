u'''
Created on Dec 9, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
import os, sys, time, logging
from collections import defaultdict
from threading import Timer

from arelle.ModelFormulaObject import (ModelParameter, ModelInstance, ModelVariableSet,
                                       ModelFormula, ModelTuple, ModelVariable, ModelFactVariable, 
                                       ModelVariableSetAssertion, ModelConsistencyAssertion,
                                       ModelExistenceAssertion, ModelValueAssertion, ModelAssertionSeverity,
                                       ModelPrecondition, ModelConceptName, Trace,
                                       Aspect, aspectModels, ModelAspectCover,
                                       ModelMessage)
from arelle.ModelRenderingObject import (ModelRuleDefinitionNode, ModelRelationshipDefinitionNode, ModelFilterDefinitionNode)
from arelle.ModelObject import (ModelObject)
from arelle.ModelValue import (qname,QName)
from arelle import (XbrlConst, XmlUtil, ModelXbrl, ModelDocument, XPathParser, XPathContext, FunctionXs,
                    ValidateXbrlDimensions) 

arcroleChecks = {
    XbrlConst.equalityDefinition:   (None, 
                                     XbrlConst.qnEqualityDefinition, 
                                     u"xbrlve:info"),
    XbrlConst.assertionSet:          (XbrlConst.qnAssertionSet,
                                      (XbrlConst.qnAssertion, XbrlConst.qnVariableSetAssertion),
                                      u"xbrlvalide:info"),
    XbrlConst.variableSet:           (XbrlConst.qnVariableSet,
                                      (XbrlConst.qnVariableVariable, XbrlConst.qnParameter),
                                      u"xbrlve:info"),
    XbrlConst.variableSetFilter:    (XbrlConst.qnVariableSet, 
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlve:info"),
    XbrlConst.variableFilter:       (XbrlConst.qnFactVariable, 
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlve:info"),
    XbrlConst.booleanFilter:        (XbrlConst.qnVariableFilter, 
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlbfe:info"),
    XbrlConst.consistencyAssertionFormula:       (XbrlConst.qnConsistencyAssertion, 
                                                 None, 
                                     u"xbrlca:info"),
    XbrlConst.functionImplementation: (XbrlConst.qnCustomFunctionSignature,
                                      XbrlConst.qnCustomFunctionImplementation,
                                      u"xbrlcfie:info"),
    XbrlConst.tableBreakdown:       (XbrlConst.qnTableTable,
                                     XbrlConst.qnTableBreakdown,
                                     u"xbrlte:tableBreakdownSourceError",
                                     u"xbrlte:tableBreakdownTargetError"),
    XbrlConst.tableBreakdownTree:   (XbrlConst.qnTableBreakdown,
                                     (XbrlConst.qnTableClosedDefinitionNode,
                                      XbrlConst.qnTableAspectNode),
                                     u"xbrlte:breakdownTreeSourceError",
                                     u"xbrlte:breakdownTreeTargetError"),
    XbrlConst.tableDefinitionNodeSubtree: (XbrlConst.qnTableDefinitionNode, 
                                     XbrlConst.qnTableDefinitionNode,
                                     u"xbrlte:definitionNodeSubtreeSourceError",
                                     u"xbrlte:definitionNodeSubtreeTargetError",
                                     (XbrlConst.qnTableConceptRelationshipNode,
                                      XbrlConst.qnTableDimensionRelationshipNode),
                                     None,
                                     u"xbrlte:prohibitedDefinitionNodeSubtreeSourceError",
                                     None),
    XbrlConst.tableFilter:          (XbrlConst.qnTableTable, 
                                     XbrlConst.qnVariableFilter,
                                     u"xbrlte:tableFilterSourceError",
                                     u"xbrlte:tableFilterTargetError"),
    XbrlConst.tableParameter:       (XbrlConst.qnTableTable, 
                                     XbrlConst.qnParameter,
                                     u"xbrlte:tableParameterSourceError",
                                     u"xbrlte:tableParameterTargetError"),
    XbrlConst.tableAspectNodeFilter:(XbrlConst.qnTableAspectNode,
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlte:aspectNodeFilterSourceError",
                                     u"xbrlte:aspectNodeFilterTargetError"),
    XbrlConst.tableBreakdownMMDD:   (XbrlConst.qnTableTableMMDD,
                                     XbrlConst.qnTableBreakdownMMDD,
                                     u"xbrlte:tableBreakdownSourceError",
                                     u"xbrlte:tableBreakdownTargetError"),
    XbrlConst.tableBreakdownTreeMMDD:(XbrlConst.qnTableBreakdownMMDD,
                                     (XbrlConst.qnTableClosedDefinitionNodeMMDD,
                                      XbrlConst.qnTableAspectNodeMMDD),
                                     u"xbrlte:breakdownTreeSourceError",
                                     u"xbrlte:breakdownTreeTargetError"),
    XbrlConst.tableDefinitionNodeSubtreeMMDD: (XbrlConst.qnTableDefinitionNodeMMDD, 
                                     XbrlConst.qnTableDefinitionNodeMMDD,
                                     u"xbrlte:definitionNodeSubtreeSourceError",
                                     u"xbrlte:definitionNodeSubtreeTargetError",
                                     (XbrlConst.qnTableConceptRelationshipNodeMMDD,
                                      XbrlConst.qnTableDimensionRelationshipNodeMMDD),
                                     None,
                                     u"xbrlte:prohibitedDefinitionNodeSubtreeSourceError",
                                     None),
    XbrlConst.tableFilterMMDD:      (XbrlConst.qnTableTableMMDD, 
                                     XbrlConst.qnVariableFilter,
                                     u"xbrlte:tableFilterSourceError",
                                     u"xbrlte:tableFilterTargetError"),
    XbrlConst.tableParameterMMDD:   (XbrlConst.qnTableTableMMDD, 
                                     XbrlConst.qnParameter,
                                     u"xbrlte:tableParameterSourceError",
                                     u"xbrlte:tableParameterTargetError"),
    XbrlConst.tableAspectNodeFilterMMDD:(XbrlConst.qnTableAspectNodeMMDD,
                                     XbrlConst.qnVariableFilter,  
                                     u"xbrlte:aspectNodeFilterSourceError",
                                     u"xbrlte:aspectNodeFilterTargetError"),
    XbrlConst.tableBreakdown201305:   (XbrlConst.qnTableTable201305,
                                     XbrlConst.qnTableBreakdown201305, 
                                     u"xbrlte:info"),
    XbrlConst.tableBreakdownTree201305:(XbrlConst.qnTableBreakdown201305,
                                     (XbrlConst.qnTableClosedDefinitionNode201305,
                                      XbrlConst.qnTableAspectNode201305),
                                     u"xbrlte:info"),
    XbrlConst.tableDefinitionNodeSubtree201305: (XbrlConst.qnTableClosedDefinitionNode201305, 
                                     XbrlConst.qnTableClosedDefinitionNode201305, 
                                     u"xbrlte:info"),
    XbrlConst.tableFilter201305:      (XbrlConst.qnTableTable201305, 
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlte:info"),
    XbrlConst.tableAspectNodeFilter201305:(XbrlConst.qnTableAspectNode201305,
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlte:info"),
    XbrlConst.tableBreakdown201301: (XbrlConst.qnTableTable201301,
                                     (XbrlConst.qnTableClosedDefinitionNode201301, 
                                      XbrlConst.qnTableFilterNode201301, 
                                      XbrlConst.qnTableSelectionNode201301, 
                                      XbrlConst.qnTableTupleNode201301),
                                     u"xbrlte:info"),
    XbrlConst.tableAxis2011:        (XbrlConst.qnTableTable2011,
                                     (XbrlConst.qnTablePredefinedAxis2011, 
                                      XbrlConst.qnTableFilterAxis2011,
                                      XbrlConst.qnTableSelectionAxis2011, 
                                      XbrlConst.qnTableTupleAxis2011),
                                     u"xbrlte:info"),
    XbrlConst.tableFilter201301:    (XbrlConst.qnTableTable201301, 
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlte:info"),
    XbrlConst.tableFilter2011:      (XbrlConst.qnTableTable2011, 
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlte:info"),
    XbrlConst.tableDefinitionNodeSubtree201301:     (XbrlConst.qnTableClosedDefinitionNode201301, 
                                     XbrlConst.qnTableClosedDefinitionNode201301, 
                                     u"xbrlte:info"),
    XbrlConst.tableAxisSubtree2011:     (XbrlConst.qnTablePredefinedAxis2011, 
                                     XbrlConst.qnTablePredefinedAxis2011, 
                                     u"xbrlte:info"),
    XbrlConst.tableFilterNodeFilter2011:(XbrlConst.qnTableFilterNode201301,
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlte:info"),
    XbrlConst.tableAxisFilter2011:  (XbrlConst.qnTableFilterAxis2011,
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlte:info"),
    XbrlConst.tableAxisFilter201205:(XbrlConst.qnTableFilterAxis2011,
                                     XbrlConst.qnVariableFilter, 
                                     u"xbrlte:info"),
    XbrlConst.tableTupleContent201301:    ((XbrlConst.qnTableTupleNode201301,
                                      XbrlConst.qnTableTupleAxis2011), 
                                     (XbrlConst.qnTableRuleNode201301,
                                      XbrlConst.qnTableRuleAxis2011), 
                                     u"xbrlte:info"),
    }
def checkBaseSet(val, arcrole, ELR, relsSet):
    # check hypercube-dimension relationships
     
    if arcrole in arcroleChecks:
        arcroleCheck = arcroleChecks[arcrole]
        notFromQname = notToQname = notFromErrCode = notToErrCode = None
        if len(arcroleCheck) == 3:
            fromQname, toQname, fromErrCode = arcroleCheck
            toErrCode = fromErrCode
        elif len(arcroleCheck) == 4: 
            fromQname, toQname, fromErrCode, toErrCode = arcroleCheck
        elif len(arcroleCheck) == 8:
            fromQname, toQname, fromErrCode, toErrCode, notFromQname, notToQname, notFromErrCode, notToErrCode = arcroleCheck
        else:
            raise Exception(u"Invalid arcroleCheck " + unicode(arcroleCheck))
        level = u"INFO" if fromErrCode.endswith(u":info") else u"ERROR"
        for modelRel in relsSet.modelRelationships:
            fromMdlObj = modelRel.fromModelObject
            toMdlObj = modelRel.toModelObject
            if fromQname:
                if (fromMdlObj is None or 
                    # if not in subs group, only warn if the namespace has a loaded schema, otherwise no complaint
                    (not val.modelXbrl.isInSubstitutionGroup(fromMdlObj.elementQname, fromQname) and
                     fromMdlObj.elementQname.namespaceURI in val.modelXbrl.namespaceDocs)):
                    val.modelXbrl.log(level, fromErrCode,
                        _(u"Relationship from %(xlinkFrom)s to %(xlinkTo)s should have an %(element)s source"),
                        modelObject=modelRel, xlinkFrom=modelRel.fromLabel, xlinkTo=modelRel.toLabel, element=fromQname)
                elif notFromQname and val.modelXbrl.isInSubstitutionGroup(fromMdlObj.elementQname, notFromQname):
                    val.modelXbrl.log(level, notFromErrCode,
                        _(u"Relationship from %(xlinkFrom)s to %(xlinkTo)s should not have an %(element)s source"),
                        modelObject=modelRel, xlinkFrom=modelRel.fromLabel, xlinkTo=modelRel.toLabel, element=fromQname)
            if toQname:
                if (toMdlObj is None or 
                    (not val.modelXbrl.isInSubstitutionGroup(toMdlObj.elementQname, toQname) and
                     toMdlObj.elementQname.namespaceURI in val.modelXbrl.namespaceDocs)):
                    val.modelXbrl.log(level, toErrCode,
                        _(u"Relationship from %(xlinkFrom)s to %(xlinkTo)s should have an %(element)s target"),
                        modelObject=modelRel, xlinkFrom=modelRel.fromLabel, xlinkTo=modelRel.toLabel, element=toQname)
                elif notToQname and val.modelXbrl.isInSubstitutionGroup(fromMdlObj.elementQname, notToQname):
                    val.modelXbrl.log(level, notFromErrCode,
                        _(u"Relationship from %(xlinkFrom)s to %(xlinkTo)s should not have an %(element)s target"),
                        modelObject=modelRel, xlinkFrom=modelRel.fromLabel, xlinkTo=modelRel.toLabel, element=fromQname)
    if arcrole == XbrlConst.functionImplementation:
        for relFrom, rels in relsSet.fromModelObjects().items():
            if len(rels) > 1:
                val.modelXbrl.error(u"xbrlcfie:tooManyCFIRelationships",
                    _(u"Function-implementation relationship from signature %(name)s has more than one implementation target"),
                     modelObject=modelRel, name=relFrom.name)
        for relTo, rels in relsSet.toModelObjects().items():
            if len(rels) > 1:
                val.modelXbrl.error(u"xbrlcfie:tooManyCFIRelationships",
                    _(u"Function implementation %(xlinkLabel)s must be the target of only one function-implementation relationship"),
                    modelObject=modelRel, xlinkLabel=relTo.xlinkLabel)
                
def executeCallTest(val, name, callTuple, testTuple):
    if callTuple:
        XPathParser.initializeParser(val.modelXbrl.modelManager)
        
        try:                            
            val.modelXbrl.modelManager.showStatus(_(u"Executing call"))
            callExprStack = XPathParser.parse(val, callTuple[0], callTuple[1], name + u" call", Trace.CALL)
            xpathContext = XPathContext.create(val.modelXbrl, sourceElement=callTuple[1])
            result = xpathContext.evaluate(callExprStack)
            xpathContext.inScopeVars[qname(u'result',noPrefixIsNoNamespace=True)] = result 
            val.modelXbrl.info(u"formula:trace", 
                               _(u"%(name)s result %(result)s"), 
                               modelObject=callTuple[1], name=name, result=unicode(result))
            
            if testTuple:
                val.modelXbrl.modelManager.showStatus(_(u"Executing test"))
                testExprStack = XPathParser.parse(val, testTuple[0], testTuple[1], name + u" test", Trace.CALL)
                testResult = xpathContext.effectiveBooleanValue( None, xpathContext.evaluate(testExprStack) )
                
                if testResult:
                    val.modelXbrl.info(u"cfcn:testPass",
                                       _(u"Test %(name)s result %(result)s"), 
                                       modelObject=testTuple[1], name=name, result=unicode(testResult))
                else:
                    val.modelXbrl.error(u"cfcn:testFail",
                                        _(u"Test %(name)s result %(result)s"), 
                                        modelObject=testTuple[1], name=name, result=unicode(testResult))
                    
            xpathContext.close()  # dereference

        except XPathContext.XPathException, err:
            val.modelXbrl.error(err.code,
                _(u"%(name)s evaluation error: %(error)s \n%(errorSource)s"),
                modelObject=callTuple[1], name=name, error=err.message, errorSource=err.sourceErrorIndication)

        val.modelXbrl.modelManager.showStatus(_(u"ready"), 2000)
                
def validate(val, xpathContext=None, parametersOnly=False, statusMsg=u'', compileOnly=False):
    for e in (u"xbrl.5.1.4.3:cycles", u"xbrlgene:violatedCyclesConstraint"):
        if e in val.modelXbrl.errors:
            val.modelXbrl.info(u"info", _(u"Formula validation skipped due to %(error)s error"),
                                modelObject=val.modelXbrl, error=e)
            return
    
    val.modelXbrl.profileStat()
    formulaOptions = val.modelXbrl.modelManager.formulaOptions
    if XPathParser.initializeParser(val.modelXbrl.modelManager):
        val.modelXbrl.profileStat(_(u"initializeXPath2Grammar")) # only provide stat when not yet initialized
    val.modelXbrl.modelManager.showStatus(statusMsg)
    val.modelXbrl.profileActivity()
    initialErrorCount = val.modelXbrl.logCount.get(logging._checkLevel(u'ERROR'), 0)
    
    # global parameter names
    parameterQnames = set()
    instanceQnames = set()
    parameterDependencies = {}
    instanceDependencies = defaultdict(set)  # None-key entries are non-formula dependencies
    dependencyResolvedParameters = set()
    orderedParameters = []
    orderedInstances = []
    for paramQname, modelParameter in val.modelXbrl.qnameParameters.items():
        if isinstance(modelParameter, ModelParameter):
            modelParameter.compile()
            parameterDependencies[paramQname] = modelParameter.variableRefs()
            parameterQnames.add(paramQname)
            if isinstance(modelParameter, ModelInstance):
                instanceQnames.add(paramQname)
            # duplicates checked on loading modelDocument
            
    #resolve dependencies
    resolvedAParameter = True
    while (resolvedAParameter):
        resolvedAParameter = False
        for paramQname in parameterQnames:
            if paramQname not in dependencyResolvedParameters and \
               len(parameterDependencies[paramQname] - dependencyResolvedParameters) == 0:
                dependencyResolvedParameters.add(paramQname)
                orderedParameters.append(paramQname)
                resolvedAParameter = True
    # anything unresolved?
    for paramQname in parameterQnames:
        if paramQname not in dependencyResolvedParameters:
            circularOrUndefDependencies = parameterDependencies[paramQname] - dependencyResolvedParameters
            undefinedVars = circularOrUndefDependencies - parameterQnames 
            paramsCircularDep = circularOrUndefDependencies - undefinedVars
            if len(undefinedVars) > 0:
                val.modelXbrl.error(u"xbrlve:unresolvedDependency",
                    _(u"Undefined dependencies in parameter %(name)s, to names %(dependencies)s"),
                    modelObject=val.modelXbrl.qnameParameters[paramQname],
                    name=paramQname, dependencies=u", ".join((unicode(v) for v in undefinedVars)))
            if len(paramsCircularDep) > 0:
                val.modelXbrl.error(u"xbrlve:parameterCyclicDependencies",
                    _(u"Cyclic dependencies in parameter %(name)s, to names %(dependencies)s"),
                    modelObject=val.modelXbrl.qnameParameters[paramQname],
                    name=paramQname, dependencies=u", ".join((unicode(d) for d in paramsCircularDep)) )
    val.modelXbrl.profileActivity(u"... formula parameter checks", minTimeToShow=1.0)
            
    for custFnSig in val.modelXbrl.modelCustomFunctionSignatures.values():
        # entries indexed by qname, arity are signature, by qname are just for parser (value=None)
        if custFnSig is not None:
            custFnQname = custFnSig.functionQname
            if custFnQname.namespaceURI == XbrlConst.xfi:
                val.modelXbrl.error(u"xbrlve:noProhibitedNamespaceForCustomFunction",
                    _(u"Custom function %(name)s has namespace reserved for functions in the function registry %(namespace)s"),
                    modelObject=custFnSig, name=custFnQname, namespace=custFnQname.namespaceURI )
            # any custom function implementations?
            for modelRel in val.modelXbrl.relationshipSet(XbrlConst.functionImplementation).fromModelObject(custFnSig):
                custFnImpl = modelRel.toModelObject
                custFnSig.customFunctionImplementation = custFnImpl
                if len(custFnImpl.inputNames) != len(custFnSig.inputTypes):
                    val.modelXbrl.error(u"xbrlcfie:inputMismatch",
                        _(u"Custom function %(name)s signature has %(parameterCountSignature)s parameters but implementation has %(parameterCountImplementation)s, must be matching"),
                        modelObject=custFnSig, name=custFnQname, 
                        parameterCountSignature=len(custFnSig.inputTypes), parameterCountImplementation=len(custFnImpl.inputNames) )
        
    for custFnImpl in val.modelXbrl.modelCustomFunctionImplementations:
        if not val.modelXbrl.relationshipSet(XbrlConst.functionImplementation).toModelObject(custFnImpl):
            val.modelXbrl.error(u"xbrlcfie:missingCFIRelationship",
                _(u"Custom function implementation %(xlinkLabel)s has no relationship from any custom function signature"),
                modelObject=custFnSig, xlinkLabel=custFnImpl.xlinkLabel)
        custFnImpl.compile()
    val.modelXbrl.profileActivity(u"... custom function checks and compilation", minTimeToShow=1.0)
            
    # xpathContext is needed for filter setup for expressions such as aspect cover filter
    # determine parameter values
    
    if xpathContext is None:
        xpathContext = XPathContext.create(val.modelXbrl) 
    xpathContext.parameterQnames = parameterQnames  # needed for formula filters to determine variable dependencies
    for paramQname in orderedParameters:
        modelParameter = val.modelXbrl.qnameParameters[paramQname]
        if not isinstance(modelParameter, ModelInstance):
            asType = modelParameter.asType
            asLocalName = asType.localName if asType else u"string"
            try:
                if val.parameters and paramQname in val.parameters:
                    paramDataType, paramValue = val.parameters[paramQname]
                    typeLocalName = paramDataType.localName if paramDataType else u"string"
                    value = FunctionXs.call(xpathContext, None, typeLocalName, [paramValue])
                    result = FunctionXs.call(xpathContext, None, asLocalName, [value])
                    if formulaOptions.traceParameterInputValue:
                        val.modelXbrl.info(u"formula:trace",
                            _(u"Parameter %(name)s input value %(input)s"), 
                            modelObject=modelParameter, name=paramQname, input=result)
                else:
                    result = modelParameter.evaluate(xpathContext, asType)
                    if formulaOptions.traceParameterExpressionResult:
                        val.modelXbrl.info(u"formula:trace",
                            _(u"Parameter %(name)s select result %(result)s"), 
                            modelObject=modelParameter, name=paramQname, result=result)
                xpathContext.inScopeVars[paramQname] = result    # make visible to subsequent parameter expression 
            except XPathContext.XPathException, err:
                val.modelXbrl.error(u"xbrlve:parameterTypeMismatch" if err.code == u"err:FORG0001" else err.code,
                    _(u"Parameter \n%(name)s \nException: \n%(error)s"), 
                    modelObject=modelParameter, name=paramQname, error=err.message,
                    messageCodes=(u"xbrlve:parameterTypeMismatch", u"err:FORG0001"))
        u''' Removed as per WG discussion 2012-12-20. This duplication checking unfairly presupposes URI based
           implementation and exceeds the scope of linkbase validation
        elif not parametersOnly: # is a modelInstance
            if val.parameters and paramQname in val.parameters:
                instanceModelXbrls = val.parameters[paramQname][1]
                instanceUris = set()
                for instanceModelXbrl in instanceModelXbrls:
                    if instanceModelXbrl.uri in instanceUris:
                        val.modelXbrl.error("xbrlvarinste:inputInstanceDuplication",
                            _("Input instance resource %(instName)s has multiple XBRL instances %(uri)s"), 
                            modelObject=modelParameter, instName=paramQname, uri=instanceModelXbrl.uri)
                    instanceUris.add(instanceModelXbrl.uri)
        if val.parameters and XbrlConst.qnStandardInputInstance in val.parameters: # standard input instance has
            if len(val.parameters[XbrlConst.qnStandardInputInstance][1]) != 1:
                val.modelXbrl.error("xbrlvarinste:standardInputInstanceNotUnique",
                    _("Standard input instance resource parameter has multiple XBRL instances"), 
                    modelObject=modelParameter)
        '''
    val.modelXbrl.profileActivity(u"... parameter checks and select evaluation", minTimeToShow=1.0)
    
    val.modelXbrl.profileStat(_(u"parametersProcessing"))

    # check typed dimension equality test
    val.modelXbrl.modelFormulaEqualityDefinitions = {}
    for modelRel in val.modelXbrl.relationshipSet(XbrlConst.equalityDefinition).modelRelationships:
        typedDomainElt = modelRel.fromModelObject
        modelEqualityDefinition = modelRel.toModelObject
        if typedDomainElt in val.modelXbrl.modelFormulaEqualityDefinitions:
            val.modelXbrl.error(u"xbrlve:multipleTypedDimensionEqualityDefinitions",
                _(u"Multiple typed domain definitions from %(typedDomain)s to %(equalityDefinition1)s and %(equalityDefinition2)s"),
                 modelObject=modelRel.arcElement, typedDomain=typedDomainElt.qname,
                 equalityDefinition1=modelEqualityDefinition.xlinkLabel,
                 equalityDefinition2=val.modelXbrl.modelFormulaEqualityDefinitions[typedDomainElt].xlinkLabel)
        else:
            modelEqualityDefinition.compile()
            val.modelXbrl.modelFormulaEqualityDefinitions[typedDomainElt] = modelEqualityDefinition
            
    if parametersOnly:
        return

    for modelVariableSet in val.modelXbrl.modelVariableSets:
        modelVariableSet.compile()
    val.modelXbrl.profileStat(_(u"formulaCompilation"))

    produceOutputXbrlInstance = False
    instanceProducingVariableSets = defaultdict(list)
        
    for modelVariableSet in val.modelXbrl.modelVariableSets:
        varSetInstanceDependencies = set()
        if isinstance(modelVariableSet, ModelFormula):
            instanceQname = None
            for modelRel in val.modelXbrl.relationshipSet(XbrlConst.formulaInstance).fromModelObject(modelVariableSet):
                instance = modelRel.toModelObject
                if isinstance(instance, ModelInstance):
                    if instanceQname is None:
                        instanceQname = instance.instanceQname
                        modelVariableSet.fromInstanceQnames = set([instanceQname]) # required if referred to by variables scope chaining
                    else:
                        val.modelXbrl.info(u"arelle:multipleOutputInstances",
                            _(u"Multiple output instances for formula %(xlinkLabel)s, to names %(instanceTo)s, %(instanceTo2)s"),
                            modelObject=modelVariableSet, xlinkLabel=modelVariableSet.xlinkLabel, 
                            instanceTo=instanceQname, instanceTo2=instance.instanceQname)
            if instanceQname is None: 
                instanceQname = XbrlConst.qnStandardOutputInstance
                instanceQnames.add(instanceQname)
                modelVariableSet.fromInstanceQnames = None # required if referred to by variables scope chaining
            modelVariableSet.outputInstanceQname = instanceQname
            if getattr(val, u"validateSBRNL", False): # may not exist on some val objects
                val.modelXbrl.error(u"SBR.NL.2.3.9.03",
                    _(u"Formula:formula %(xlinkLabel)s is not allowed"),
                    modelObject=modelVariableSet, xlinkLabel=modelVariableSet.xlinkLabel)
        else:
            instanceQname = None
            modelVariableSet.countSatisfied = 0
            modelVariableSet.countNotSatisfied = 0
            checkValidationMessages(val, modelVariableSet)
        instanceProducingVariableSets[instanceQname].append(modelVariableSet)
        modelVariableSet.outputInstanceQname = instanceQname
        if modelVariableSet.aspectModel not in (u"non-dimensional", u"dimensional"):
            val.modelXbrl.error(u"xbrlve:unknownAspectModel",
                _(u"Variable set %(xlinkLabel)s, aspect model %(aspectModel)s not recognized"),
                modelObject=modelVariableSet, xlinkLabel=modelVariableSet.xlinkLabel, aspectModel=modelVariableSet.aspectModel)
        modelVariableSet.hasConsistencyAssertion = False
            
        #determine dependencies within variable sets
        nameVariables = {}
        qnameRels = {}
        definedNamesSet = set()
        for modelRel in val.modelXbrl.relationshipSet(XbrlConst.variableSet).fromModelObject(modelVariableSet):
            varqname = modelRel.variableQname
            if varqname:
                qnameRels[varqname] = modelRel
                toVariable = modelRel.toModelObject
                if varqname not in definedNamesSet:
                    definedNamesSet.add(varqname)
                if varqname not in nameVariables:
                    nameVariables[varqname] = toVariable
                elif nameVariables[varqname] != toVariable:
                    val.modelXbrl.error(u"xbrlve:duplicateVariableNames",
                        _(u"Multiple variables named %(xlinkLabel)s in variable set %(name)s"),
                        modelObject=toVariable, xlinkLabel=modelVariableSet.xlinkLabel, name=varqname )
                fromInstanceQnames = None
                for instRel in val.modelXbrl.relationshipSet(XbrlConst.instanceVariable).toModelObject(toVariable):
                    fromInstance = instRel.fromModelObject
                    if isinstance(fromInstance, ModelInstance):
                        fromInstanceQname = fromInstance.instanceQname
                        varSetInstanceDependencies.add(fromInstanceQname)
                        instanceDependencies[instanceQname].add(fromInstanceQname)
                        if fromInstanceQnames is None: fromInstanceQnames = set()
                        fromInstanceQnames.add(fromInstanceQname)
                if fromInstanceQnames is None:
                    varSetInstanceDependencies.add(XbrlConst.qnStandardInputInstance)
                    if instanceQname: instanceDependencies[instanceQname].add(XbrlConst.qnStandardInputInstance)
                toVariable.fromInstanceQnames = fromInstanceQnames
            else:
                val.modelXbrl.error(u"xbrlve:variableNameResolutionFailure",
                    _(u"Variables name %(name)s cannot be determined on arc from %(xlinkLabel)s"),
                    modelObject=modelRel, xlinkLabel=modelVariableSet.xlinkLabel, name=modelRel.variablename )
        checkVariablesScopeVisibleQnames(val, nameVariables, definedNamesSet, modelVariableSet)
        definedNamesSet |= parameterQnames
                
        variableDependencies = {}
        for modelRel in val.modelXbrl.relationshipSet(XbrlConst.variableSet).fromModelObject(modelVariableSet):
            variable = modelRel.toModelObject
            if isinstance(variable, (ModelParameter,ModelVariable)):    # ignore anything not parameter or variable
                varqname = modelRel.variableQname
                depVars = variable.variableRefs()
                variableDependencies[varqname] = depVars
                if len(depVars) > 0 and formulaOptions.traceVariablesDependencies:
                    val.modelXbrl.info(u"formula:trace",
                        _(u"Variable set %(xlinkLabel)s, variable %(name)s, dependences %(dependencies)s"),
                        modelObject=modelVariableSet, xlinkLabel=modelVariableSet.xlinkLabel, 
                        name=varqname, dependencies=depVars)
                definedNamesSet.add(varqname)
                # check for fallback value variable references
                if isinstance(variable, ModelFactVariable):
                    variable.hasNoVariableDependencies = len(depVars - parameterQnames) == 0
                    for depVar in XPathParser.variableReferencesSet(variable.fallbackValueProg, variable):
                        if depVar in qnameRels and isinstance(qnameRels[depVar].toModelObject,ModelVariable):
                            val.modelXbrl.error(u"xbrlve:fallbackValueVariableReferenceNotAllowed",
                                _(u"Variable set %(xlinkLabel)s fallbackValue '%(fallbackValue)s' cannot refer to variable %(dependency)s"),
                                modelObject=variable, xlinkLabel=modelVariableSet.xlinkLabel, 
                                fallbackValue=variable.fallbackValue, dependency=depVar)
                    # check for covering aspect not in variable set aspect model
                    checkFilterAspectModel(val, modelVariableSet, variable.filterRelationships, xpathContext)

        orderedNameSet = set()
        orderedNameList = []
        orderedAVariable = True
        while (orderedAVariable):
            orderedAVariable = False
            for varqname, depVars in variableDependencies.items():
                if varqname not in orderedNameSet and len(depVars - parameterQnames - orderedNameSet) == 0:
                    orderedNameList.append(varqname)
                    orderedNameSet.add(varqname)
                    orderedAVariable = True
                if varqname in instanceQnames:
                    varSetInstanceDependencies.add(varqname)
                    instanceDependencies[instanceQname].add(varqname)
                elif isinstance(nameVariables.get(varqname), ModelInstance):
                    instqname = nameVariables[varqname].instanceQname
                    varSetInstanceDependencies.add(instqname)
                    instanceDependencies[instanceQname].add(instqname)
                    
        # anything unresolved?
        for varqname, depVars in variableDependencies.items():
            if varqname not in orderedNameSet:
                circularOrUndefVars = depVars - parameterQnames - orderedNameSet
                undefinedVars = circularOrUndefVars - definedNamesSet 
                varsCircularDep = circularOrUndefVars - undefinedVars
                if len(undefinedVars) > 0:
                    val.modelXbrl.error(u"xbrlve:unresolvedDependency",
                        _(u"Undefined variable dependencies in variable set %(xlinkLabel)s, from variable %(nameFrom)s to %(nameTo)s"),
                        modelObject=modelVariableSet, xlinkLabel=modelVariableSet.xlinkLabel, 
                        nameFrom=varqname, nameTo=undefinedVars)
                if len(varsCircularDep) > 0:
                    val.modelXbrl.error(u"xbrlve:cyclicDependencies",
                        _(u"Cyclic dependencies in variable set %(xlinkLabel)s, from variable %(nameFrom)s to %(nameTo)s"),
                        modelObject=modelVariableSet, xlinkLabel=modelVariableSet.xlinkLabel, 
                        nameFrom=varqname, nameTo=varsCircularDep )
                    
        # check unresolved variable set dependencies
        for varSetDepVarQname in modelVariableSet.variableRefs():
            if varSetDepVarQname not in definedNamesSet and varSetDepVarQname not in parameterQnames:
                val.modelXbrl.error(u"xbrlve:unresolvedDependency",
                    _(u"Undefined variable dependency in variable set %(xlinkLabel)s, %(name)s"),
                    modelObject=modelVariableSet, xlinkLabel=modelVariableSet.xlinkLabel,
                    name=varSetDepVarQname)
            if varSetDepVarQname in instanceQnames:
                varSetInstanceDependencies.add(varSetDepVarQname)
                instanceDependencies[instanceQname].add(varSetDepVarQname)
            elif isinstance(nameVariables.get(varSetDepVarQname), ModelInstance):
                instqname = nameVariables[varSetDepVarQname].instanceQname
                varSetInstanceDependencies.add(instqname)
                instanceDependencies[instanceQname].add(instqname)
        
        if formulaOptions.traceVariablesOrder:
            val.modelXbrl.info(u"formula:trace",
                   _(u"Variable set %(xlinkLabel)s, variables order: %(dependencies)s"),
                   modelObject=modelVariableSet, xlinkLabel=modelVariableSet.xlinkLabel, dependencies=orderedNameList)
        
        if (formulaOptions.traceVariablesDependencies and len(varSetInstanceDependencies) > 0 and
            varSetInstanceDependencies != set([XbrlConst.qnStandardInputInstance])):
            val.modelXbrl.info(u"formula:trace",
                   _(u"Variable set %(xlinkLabel)s, instance dependences %(dependencies)s"),
                   modelObject=modelVariableSet, xlinkLabel=modelVariableSet.xlinkLabel, dependencies=varSetInstanceDependencies)
            
        modelVariableSet.orderedVariableRelationships = []
        for varqname in orderedNameList:
            if varqname in qnameRels:
                modelVariableSet.orderedVariableRelationships.append(qnameRels[varqname])
        
        orderedNameSet.clear()       
        del orderedNameList[:]  # dereference            
                
        # check existence assertion @test variable dependencies (not including precondition references)
        if isinstance(modelVariableSet, ModelExistenceAssertion):
            for depVar in XPathParser.variableReferencesSet(modelVariableSet.testProg, modelVariableSet):
                if depVar in qnameRels and isinstance(qnameRels[depVar].toModelObject,ModelVariable):
                    val.modelXbrl.error(u"xbrleae:variableReferenceNotAllowed",
                        _(u"Existence Assertion %(xlinkLabel)s, cannot refer to variable %(name)s"),
                        modelObject=modelVariableSet, xlinkLabel=modelVariableSet.xlinkLabel, name=depVar)
                    
        # check messages variable dependencies
        checkValidationMessageVariables(val, modelVariableSet, qnameRels, xpathContext.parameterQnames)

        if isinstance(modelVariableSet, ModelFormula): # check consistency assertion message variables and its messages variables
            for consisAsserRel in val.modelXbrl.relationshipSet(XbrlConst.consistencyAssertionFormula).toModelObject(modelVariableSet):
                consisAsser = consisAsserRel.fromModelObject
                if isinstance(consisAsser, ModelConsistencyAssertion):
                    checkValidationMessages(val, consisAsser)
                    checkValidationMessageVariables(val, consisAsser, qnameRels, xpathContext.parameterQnames)
                        
        # check preconditions
        modelVariableSet.preconditions = []
        for modelRel in val.modelXbrl.relationshipSet(XbrlConst.variableSetPrecondition).fromModelObject(modelVariableSet):
            precondition = modelRel.toModelObject
            if isinstance(precondition, ModelPrecondition):
                modelVariableSet.preconditions.append(precondition)
                
        # check for variable sets referencing fact or general variables
        for modelRel in val.modelXbrl.relationshipSet(XbrlConst.variableSetFilter).fromModelObject(modelVariableSet):
            varSetFilter = modelRel.toModelObject
            if modelRel.isCovered:
                val.modelXbrl.warning(u"arelle:variableSetFilterCovered",
                    _(u"Variable set %(xlinkLabel)s, filter %(filterLabel)s, cannot be covered"),
                     modelObject=varSetFilter, xlinkLabel=modelVariableSet.xlinkLabel, filterLabel=varSetFilter.xlinkLabel)
                modelRel._isCovered = False # block group filter from being able to covered
                
            for depVar in varSetFilter.variableRefs():
                if depVar in qnameRels and isinstance(qnameRels[depVar].toModelObject,ModelVariable):
                    val.modelXbrl.error(u"xbrlve:factVariableReferenceNotAllowed",
                        _(u"Variable set %(xlinkLabel)s, filter %(filterLabel)s, cannot refer to variable %(name)s"),
                        modelObject=varSetFilter, xlinkLabel=modelVariableSet.xlinkLabel, filterLabel=varSetFilter.xlinkLabel, name=depVar)
                    
        # check aspects of formula
        if isinstance(modelVariableSet, ModelFormula):
            checkFormulaRules(val, modelVariableSet, nameVariables)

        nameVariables.clear() # dereference
        qnameRels.clear()
        definedNamesSet.clear()
        variableDependencies.clear()
        varSetInstanceDependencies.clear()

    val.modelXbrl.profileActivity(u"... assertion and formula checks and compilation", minTimeToShow=1.0)
            
    for modelTable in val.modelXbrl.modelRenderingTables:
        modelTable.fromInstanceQnames = None # required if referred to by variables scope chaining
        if modelTable.aspectModel not in (u"non-dimensional", u"dimensional"):
            val.modelXbrl.error(u"xbrlte:unknownAspectModel",
                _(u"Table %(xlinkLabel)s, aspect model %(aspectModel)s not recognized"),
                modelObject=modelTable, xlinkLabel=modelTable.xlinkLabel, aspectModel=modelTable.aspectModel)
        modelTable.compile()
        checkTableRules(val, xpathContext, modelTable)

    val.modelXbrl.profileActivity(u"... rendering tables and axes checks and compilation", minTimeToShow=1.0)
            
    # determine instance dependency order
    orderedInstancesSet = set()
    stdInpInst = set([XbrlConst.qnStandardInputInstance])
    orderedInstancesList = []
    orderedAnInstance = True
    while (orderedAnInstance):
        orderedAnInstance = False
        for instqname, depInsts in instanceDependencies.items():
            if instqname and instqname not in orderedInstancesSet and len(depInsts - stdInpInst - orderedInstancesSet) == 0:
                orderedInstancesList.append(instqname)
                orderedInstancesSet.add(instqname)
                orderedAnInstance = True
    # add instances with variable sets with no variables or other dependencies
    for independentInstance in _DICT_SET(instanceProducingVariableSets.keys()) - _DICT_SET(orderedInstancesList): # must be set for 2.7 compatibility
        orderedInstancesList.append(independentInstance)
        orderedInstancesSet.add(independentInstance)
    if None not in orderedInstancesList:
        orderedInstancesList.append(None)  # assertions come after all formulas that produce outputs

    # anything unresolved?
    for instqname, depInsts in instanceDependencies.items():
        if instqname not in orderedInstancesSet:
            # can also be satisfied from an input DTS
            missingDependentInstances = depInsts - stdInpInst
            if val.parameters: missingDependentInstances -= _DICT_SET(val.parameters.keys()) 
            if instqname:
                if missingDependentInstances:
                    val.modelXbrl.error(u"xbrlvarinste:instanceVariableRecursionCycle",
                        _(u"Cyclic dependencies of instance %(name)s produced by a formula, with variables consuming instances %(dependencies)s"),
                        modelObject=val.modelXbrl,
                        name=instqname, dependencies=missingDependentInstances )
                elif instqname == XbrlConst.qnStandardOutputInstance:
                    orderedInstancesSet.add(instqname)
                    orderedInstancesList.append(instqname) # standard output formula, all input dependencies in parameters
            u''' future check?  if instance has no external input or producing formula
            else:
                val.modelXbrl.error("xbrlvarinste:instanceVariableRecursionCycle",
                    _("Unresolved dependencies of an assertion's variables on instances %(dependencies)s"),
                    dependencies=str(_DICT_SET(depInsts) - stdInpInst) )
            '''
        elif instqname in depInsts: # check for direct cycle
            val.modelXbrl.error(u"xbrlvarinste:instanceVariableRecursionCycle",
                _(u"Cyclic dependencies of instance %(name)s produced by its own variables"),
                modelObject=val.modelXbrl, name=instqname )

    if formulaOptions.traceVariablesOrder and len(orderedInstancesList) > 1:
        val.modelXbrl.info(u"formula:trace",
               _(u"Variable instances processing order: %(dependencies)s"),
                modelObject=val.modelXbrl, dependencies=orderedInstancesList)

    # linked consistency assertions
    for modelRel in val.modelXbrl.relationshipSet(XbrlConst.consistencyAssertionFormula).modelRelationships:
        if (modelRel.fromModelObject is not None and modelRel.toModelObject is not None and 
            isinstance(modelRel.toModelObject,ModelFormula)):
            consisAsser = modelRel.fromModelObject
            consisAsser.countSatisfied = 0
            consisAsser.countNotSatisfied = 0
            if consisAsser.hasProportionalAcceptanceRadius and consisAsser.hasAbsoluteAcceptanceRadius:
                val.modelXbrl.error(u"xbrlcae:acceptanceRadiusConflict",
                    _(u"Consistency assertion %(xlinkLabel)s has both absolute and proportional acceptance radii"), 
                    modelObject=consisAsser, xlinkLabel=consisAsser.xlinkLabel)
            consisAsser.orderedVariableRelationships = []
            for consisParamRel in val.modelXbrl.relationshipSet(XbrlConst.consistencyAssertionParameter).fromModelObject(consisAsser):
                if isinstance(consisParamRel.toModelObject, ModelVariable):
                    val.modelXbrl.error(u"xbrlcae:variablesNotAllowed",
                        _(u"Consistency assertion %(xlinkLabel)s has relationship to a %(elementTo)s %(xlinkLabelTo)s"),
                        modelObject=consisAsser, xlinkLabel=consisAsser.xlinkLabel, 
                        elementTo=consisParamRel.toModelObject.localName, xlinkLabelTo=consisParamRel.toModelObject.xlinkLabel)
                elif isinstance(consisParamRel.toModelObject, ModelParameter):
                    consisAsser.orderedVariableRelationships.append(consisParamRel)
            consisAsser.compile()
            modelRel.toModelObject.hasConsistencyAssertion = True
    val.modelXbrl.profileActivity(u"... consistency assertion setup", minTimeToShow=1.0)

    # check for assertion severity
    for arcrole, relType in ((XbrlConst.assertionSatisfiedSeverity, u"satisfied"),
                             (XbrlConst.assertionUnsatisfiedSeverity, u"unsatisfied")):
        assertionSeverities = defaultdict(list)
        for modelRel in val.modelXbrl.relationshipSet(arcrole).modelRelationships:
            assertion = modelRel.fromModelObject
            severity = modelRel.toModelObject
            if not isinstance(assertion, (ModelVariableSetAssertion, ModelConsistencyAssertion)):
                val.modelXbrl.error(u"seve:assertionSeveritySourceError",
                    _(u"Source of assertion-%(relType)s-severity relationship is not an assertion element: %(sourceElement)s"),
                    modelObject=(modelRel, assertion), relType=relType, sourceElement=assertion.qname)
            if not isinstance(severity, ModelAssertionSeverity):
                val.modelXbrl.error(u"seve:assertionSeverityTargetError",
                    _(u"Target of assertion-%(relType)s-severity relationship is not an severity element: %(targetElement)s"),
                    modelObject=(modelRel, severity), relType=relType, targetElement=severity.qname)
            assertionSeverities[assertion].append(severity)
        for assertion, severities in assertionSeverities.items():
            if len(severities) > 1:
                val.modelXbrl.error(u"seve:multipleAssertionSeveritiesNotAllowed",
                    _(u"Assertion has more than one severity (%(numSevereties)s) in assertion-%(relType)s-severity relationships"),
                    modelObject=[assertion] + list(severities), relType=relType, numSeverities=len(severities))
        del assertionSeverities # dereference
        
    # validate default dimensions in instances and accumulate multi-instance-default dimension aspects
    xpathContext.defaultDimensionAspects = set(val.modelXbrl.qnameDimensionDefaults.keys())
    for instanceQname in instanceQnames:
        if (instanceQname not in (XbrlConst.qnStandardInputInstance,XbrlConst.qnStandardOutputInstance) and
            val.parameters and instanceQname in val.parameters):
            for namedInstance in val.parameters[instanceQname][1]:
                ValidateXbrlDimensions.loadDimensionDefaults(namedInstance)
                xpathContext.defaultDimensionAspects |= _DICT_SET(namedInstance.qnameDimensionDefaults.keys())

    # check for variable set dependencies across output instances produced
    for instanceQname, modelVariableSets in instanceProducingVariableSets.items():
        for modelVariableSet in modelVariableSets:
            for varScopeRel in val.modelXbrl.relationshipSet(XbrlConst.variablesScope).toModelObject(modelVariableSet):
                if varScopeRel.fromModelObject is not None:
                    sourceVariableSet = varScopeRel.fromModelObject
                    if sourceVariableSet.outputInstanceQname != instanceQname:
                        val.modelXbrl.error(u"xbrlvarscopee:differentInstances",
                            _(u"Variable set %(xlinkLabel1)s in instance %(instance1)s has variables scope relationship to varaible set %(xlinkLabel2)s in instance %(instance2)s"),
                            modelObject=modelVariableSet, 
                            xlinkLabel1=sourceVariableSet.xlinkLabel, instance1=sourceVariableSet.outputInstanceQname,
                            xlinkLabel2=modelVariableSet.xlinkLabel, instance2=modelVariableSet.outputInstanceQname)
                    if sourceVariableSet.aspectModel != modelVariableSet.aspectModel:
                        val.modelXbrl.error(u"xbrlvarscopee:conflictingAspectModels",
                            _(u"Variable set %(xlinkLabel1)s aspectModel (%(aspectModel1)s) differs from varaible set %(xlinkLabel2)s aspectModel (%(aspectModel2)s)"),
                            modelObject=modelVariableSet, 
                            xlinkLabel1=sourceVariableSet.xlinkLabel, aspectModel1=sourceVariableSet.aspectModel,
                            xlinkLabel2=modelVariableSet.xlinkLabel, aspectModel2=modelVariableSet.aspectModel)
    val.modelXbrl.profileActivity(u"... instances scopes and setup", minTimeToShow=1.0)

    val.modelXbrl.profileStat(_(u"formulaValidation"))
    if (initialErrorCount < val.modelXbrl.logCount.get(logging._checkLevel(u'ERROR'), 0) or
        compileOnly or 
        getattr(val, u"validateFormulaCompileOnly", False)):
        return  # don't try to execute
        

    # formula output instances    
    if instanceQnames:      
        val.modelXbrl.modelManager.showStatus(_(u"initializing formula output instances"))
        schemaRefs = [val.modelXbrl.modelDocument.relativeUri(referencedDoc.uri)
                        for referencedDoc in val.modelXbrl.modelDocument.referencesDocument.keys()
                            if referencedDoc.type == ModelDocument.Type.SCHEMA]
        
    outputXbrlInstance = None
    for instanceQname in instanceQnames:
        if instanceQname == XbrlConst.qnStandardInputInstance:
            continue    # always present the standard way
        if val.parameters and instanceQname in val.parameters:
            namedInstance = val.parameters[instanceQname][1] # this is a sequence
        else:   # empty intermediate instance 
            uri = val.modelXbrl.modelDocument.filepath[:-4] + u"-output-XBRL-instance"
            if instanceQname != XbrlConst.qnStandardOutputInstance:
                uri = uri + u"-" + instanceQname.localName
            uri = uri + u".xml"
            namedInstance = ModelXbrl.create(val.modelXbrl.modelManager, 
                                             newDocumentType=ModelDocument.Type.INSTANCE,
                                             url=uri,
                                             schemaRefs=schemaRefs,
                                             isEntry=True)
            ValidateXbrlDimensions.loadDimensionDefaults(namedInstance) # need dimension defaults 
        xpathContext.inScopeVars[instanceQname] = namedInstance
        if instanceQname == XbrlConst.qnStandardOutputInstance:
            outputXbrlInstance = namedInstance
    val.modelXbrl.profileActivity(u"... output instances setup", minTimeToShow=1.0)
    val.modelXbrl.profileStat(_(u"formulaInstancesSetup"))
    timeFormulasStarted = time.time()
        
    val.modelXbrl.modelManager.showStatus(_(u"running formulae"))
    
    # IDs may be "|" or whitespace separated
    runIDs = (formulaOptions.runIDs or u'').replace(u'|',u' ').split()
    if runIDs:
        val.modelXbrl.info(u"formula:trace",
                           _(u"Formua/assertion IDs restriction: %(ids)s"), 
                           modelXbrl=val.modelXbrl, ids=u', '.join(runIDs))
        
    # evaluate consistency assertions
    try:
        if hasattr(val, u"maxFormulaRunTime") and val.maxFormulaRunTime > 0:
            maxFormulaRunTimeTimer = Timer(val.maxFormulaRunTime * 60.0, xpathContext.runTimeExceededCallback)
            maxFormulaRunTimeTimer.start()
        else:
            maxFormulaRunTimeTimer = None
        # evaluate variable sets not in consistency assertions
        val.modelXbrl.profileActivity(u"... evaluations", minTimeToShow=1.0)
        for instanceQname in orderedInstancesList:
            for modelVariableSet in instanceProducingVariableSets[instanceQname]:
                # produce variable evaluations if no dependent variables-scope relationships
                if not val.modelXbrl.relationshipSet(XbrlConst.variablesScope).toModelObject(modelVariableSet):
                    if (not runIDs or 
                        modelVariableSet.id in runIDs or
                        (modelVariableSet.hasConsistencyAssertion and 
                         any(modelRel.fromModelObject.id in runIDs
                             for modelRel in val.modelXbrl.relationshipSet(XbrlConst.consistencyAssertionFormula).toModelObject(modelVariableSet)
                             if isinstance(modelRel.fromModelObject, ModelConsistencyAssertion)))):
                        from arelle.FormulaEvaluator import evaluate
                        try:
                            varSetId = (modelVariableSet.id or modelVariableSet.xlinkLabel)
                            val.modelXbrl.profileActivity(u"... evaluating " + varSetId, minTimeToShow=10.0)
                            val.modelXbrl.modelManager.showStatus(_(u"evaluating {0}").format(varSetId))
                            val.modelXbrl.profileActivity(u"... evaluating " + varSetId, minTimeToShow=1.0)
                            evaluate(xpathContext, modelVariableSet)
                            val.modelXbrl.profileStat(modelVariableSet.localName + u"_" + varSetId)
                        except XPathContext.XPathException, err:
                            val.modelXbrl.error(err.code,
                                _(u"Variable set \n%(variableSet)s \nException: \n%(error)s"), 
                                modelObject=modelVariableSet, variableSet=unicode(modelVariableSet), error=err.message)
        if maxFormulaRunTimeTimer:
            maxFormulaRunTimeTimer.cancel()
    except XPathContext.RunTimeExceededException:
        val.modelXbrl.info(u"formula:maxRunTime",
            _(u"Formula execution ended after %(mins)s minutes"), 
            modelObject=val.modelXbrl, mins=val.maxFormulaRunTime)
        
    # log assertion result counts
    asserTests = {}
    for exisValAsser in val.modelXbrl.modelVariableSets:
        if isinstance(exisValAsser, ModelVariableSetAssertion) and \
           (not runIDs or exisValAsser.id in runIDs):
            asserTests[exisValAsser.id] = (exisValAsser.countSatisfied, exisValAsser.countNotSatisfied)
            if formulaOptions.traceAssertionResultCounts:
                val.modelXbrl.info(u"formula:trace",
                    _(u"%(assertionType)s Assertion %(id)s evaluations : %(satisfiedCount)s satisfied, %(notSatisfiedCount)s not satisfied"),
                    modelObject=exisValAsser,
                    assertionType=u"Existence" if isinstance(exisValAsser, ModelExistenceAssertion) else u"Value", 
                    id=exisValAsser.id, satisfiedCount=exisValAsser.countSatisfied, notSatisfiedCount=exisValAsser.countNotSatisfied)

    for modelRel in val.modelXbrl.relationshipSet(XbrlConst.consistencyAssertionFormula).modelRelationships:
        if modelRel.fromModelObject is not None and modelRel.toModelObject is not None and \
           isinstance(modelRel.toModelObject,ModelFormula) and \
           (not runIDs or modelRel.fromModelObject.id in runIDs):
            consisAsser = modelRel.fromModelObject
            asserTests[consisAsser.id] = (consisAsser.countSatisfied, consisAsser.countNotSatisfied)
            if formulaOptions.traceAssertionResultCounts:
                val.modelXbrl.info(u"formula:trace",
                   _(u"Consistency Assertion %(id)s evaluations : %(satisfiedCount)s satisfied, %(notSatisfiedCount)s not satisfied"),
                    modelObject=consisAsser, id=consisAsser.id, 
                    satisfiedCount=consisAsser.countSatisfied, notSatisfiedCount=consisAsser.countNotSatisfied)
            
    if asserTests: # pass assertion results to validation if appropriate
        val.modelXbrl.log(None, u"asrtNoLog", None, assertionResults=asserTests);

    # display output instance
    if outputXbrlInstance:
        if val.modelXbrl.formulaOutputInstance:
            # close prior instance, usually closed by caller to validate as it may affect UI on different thread
            val.modelXbrl.formulaOutputInstance.close()
        val.modelXbrl.formulaOutputInstance = outputXbrlInstance
        
    val.modelXbrl.modelManager.showStatus(_(u"formulae finished"), 2000)
        
    instanceProducingVariableSets.clear() # dereference
    parameterQnames.clear()
    instanceQnames.clear()
    parameterDependencies.clear()
    instanceDependencies.clear()
    dependencyResolvedParameters.clear()
    orderedInstancesSet.clear()
    del orderedParameters, orderedInstances, orderedInstancesList
    xpathContext.close()  # dereference everything
    val.modelXbrl.profileStat(_(u"formulaExecutionTotal"), time.time() - timeFormulasStarted)

def checkVariablesScopeVisibleQnames(val, nameVariables, definedNamesSet, modelVariableSet):
    for visibleVarSetRel in val.modelXbrl.relationshipSet(XbrlConst.variablesScope).toModelObject(modelVariableSet):
        varqname = visibleVarSetRel.variableQname # name (if any) of the formula result
        if varqname:
            if varqname not in nameVariables:
                nameVariables[varqname] = visibleVarSetRel.fromModelObject
            if varqname not in definedNamesSet:
                definedNamesSet.add(varqname)
        visibleVarSet = visibleVarSetRel.fromModelObject
        for modelRel in val.modelXbrl.relationshipSet(XbrlConst.variableSet).fromModelObject(visibleVarSet):
            varqname = modelRel.variableQname
            if varqname:
                if varqname not in nameVariables:
                    nameVariables[varqname] = modelRel.toModelObject
                if varqname not in definedNamesSet:
                    definedNamesSet.add(varqname)
        checkVariablesScopeVisibleQnames(val, nameVariables, definedNamesSet, visibleVarSet)

def checkFilterAspectModel(val, variableSet, filterRelationships, xpathContext, uncoverableAspects=None):
    result = set() # all of the aspects found to be covered
    if uncoverableAspects is None:
        # protect 2.7 conversion
        oppositeAspectModel = (_DICT_SET(set([u'dimensional',u'non-dimensional'])) - _DICT_SET(set([variableSet.aspectModel]))).pop()
        try:
            uncoverableAspects = aspectModels[oppositeAspectModel] - aspectModels[variableSet.aspectModel]
        except KeyError:    # bad aspect model, not an issue for this test
            return result
    acfAspectsCovering = {}
    for varFilterRel in filterRelationships:
        _filter = varFilterRel.toModelObject # use _filter instead of filter to prevent 2to3 confusion
        isAllAspectCoverFilter = False
        if isinstance(_filter, ModelAspectCover):
            for aspect in _filter.aspectsCovered(None, xpathContext):
                if aspect in acfAspectsCovering:
                    otherFilterCover, otherFilterLabel = acfAspectsCovering[aspect]
                    if otherFilterCover != varFilterRel.isCovered:
                        val.modelXbrl.error(u"xbrlacfe:inconsistentAspectCoverFilters",
                            _(u"Variable set %(xlinkLabel)s, aspect cover filter %(filterLabel)s, aspect %(aspect)s, conflicts with %(filterLabel2)s with inconsistent cover attribute"),
                            modelObject=variableSet, xlinkLabel=variableSet.xlinkLabel, filterLabel=_filter.xlinkLabel, 
                            aspect=unicode(aspect) if isinstance(aspect,QName) else Aspect.label[aspect],
                            filterLabel2=otherFilterLabel)
                else:
                    acfAspectsCovering[aspect] = (varFilterRel.isCovered, _filter.xlinkLabel)
            isAllAspectCoverFilter = _filter.isAll
        if True: # changed for test case 50210 v03 varFilterRel.isCovered:
            try:
                aspectsCovered = _filter.aspectsCovered(None)
                if (not isAllAspectCoverFilter and 
                    (any(isinstance(aspect,QName) for aspect in aspectsCovered) and Aspect.DIMENSIONS in uncoverableAspects
                     or (aspectsCovered & uncoverableAspects))):
                    val.modelXbrl.error(u"xbrlve:filterAspectModelMismatch",
                        _(u"Variable set %(xlinkLabel)s, aspect model %(aspectModel)s filter %(filterName)s %(filterLabel)s can cover aspect not in aspect model"),
                        modelObject=variableSet, xlinkLabel=variableSet.xlinkLabel, aspectModel=variableSet.aspectModel, 
                        filterName=_filter.localName, filterLabel=_filter.xlinkLabel)
                result |= aspectsCovered                    
            except Exception:
                pass
            if hasattr(_filter, u"filterRelationships"): # check and & or filters
                result |= checkFilterAspectModel(val, variableSet, _filter.filterRelationships, xpathContext, uncoverableAspects)
    return result
        
def checkFormulaRules(val, formula, nameVariables):
    if not (formula.hasRule(Aspect.CONCEPT) or formula.source(Aspect.CONCEPT)):
        if XmlUtil.hasDescendant(formula, XbrlConst.formula, u"concept"):
            val.modelXbrl.error(u"xbrlfe:incompleteConceptRule",
                _(u"Formula %(xlinkLabel)s concept rule does not have a nearest source and does not have a child element"),
                modelObject=formula, xlinkLabel=formula.xlinkLabel)
        else:
            val.modelXbrl.error(u"xbrlfe:missingConceptRule",
                _(u"Formula %(xlinkLabel)s omits a rule for the concept aspect"),
                modelObject=formula, xlinkLabel=formula.xlinkLabel)
    if not isinstance(formula, ModelTuple):
        if (not (formula.hasRule(Aspect.SCHEME) or formula.source(Aspect.SCHEME)) or
            not (formula.hasRule(Aspect.VALUE) or formula.source(Aspect.VALUE))):
            if XmlUtil.hasDescendant(formula, XbrlConst.formula, u"entityIdentifier"):
                val.modelXbrl.error(u"xbrlfe:incompleteEntityIdentifierRule",
                    _(u"Formula %(xlinkLabel)s entity identifier rule does not have a nearest source and does not have either a @scheme or a @value attribute"),
                    modelObject=formula, xlinkLabel=formula.xlinkLabel)
            else:
                val.modelXbrl.error(u"xbrlfe:missingEntityIdentifierRule",
                    _(u"Formula %(xlinkLabel)s omits a rule for the entity identifier aspect"),
                    modelObject=formula, xlinkLabel=formula.xlinkLabel)
        if not (formula.hasRule(Aspect.PERIOD_TYPE) or formula.source(Aspect.PERIOD_TYPE)):
            if XmlUtil.hasDescendant(formula, XbrlConst.formula, u"period"):
                val.modelXbrl.error(u"xbrlfe:incompletePeriodRule",
                    _(u"Formula %(xlinkLabel)s period rule does not have a nearest source and does not have a child element"),
                    modelObject=formula, xlinkLabel=formula.xlinkLabel)
            else:
                val.modelXbrl.error(u"xbrlfe:missingPeriodRule",
                    _(u"Formula %(xlinkLabel)s omits a rule for the period aspect"),
                    modelObject=formula, xlinkLabel=formula.xlinkLabel)
        # for unit need to see if the qname is statically determinable to determine if numeric
        concept = val.modelXbrl.qnameConcepts.get(formula.evaluateRule(None, Aspect.CONCEPT))
        if concept is None: # is there a source with a static QName filter
            sourceFactVar = nameVariables.get(formula.source(Aspect.CONCEPT))
            if isinstance(sourceFactVar, ModelFactVariable):
                for varFilterRels in (formula.groupFilterRelationships, sourceFactVar.filterRelationships):
                    for varFilterRel in varFilterRels:
                        _filter = varFilterRel.toModelObject
                        if isinstance(_filter,ModelConceptName):  # relationship not constrained to real filters
                            for conceptQname in _filter.conceptQnames:
                                concept = val.modelXbrl.qnameConcepts.get(conceptQname)
                                if concept is not None and concept.isNumeric:
                                    break
        if concept is not None: # from concept aspect rule or from source factVariable concept Qname filter
            if concept.isNumeric:
                if not (formula.hasRule(Aspect.MULTIPLY_BY) or formula.hasRule(Aspect.DIVIDE_BY) or formula.source(Aspect.UNIT)):
                    if XmlUtil.hasDescendant(formula, XbrlConst.formula, u"unit"):
                        val.modelXbrl.error(u"xbrlfe:missingSAVForUnitRule",
                            _(u"Formula %(xlinkLabel)s unit rule does not have a source and does not have a child element"),
                            modelObject=formula, xlinkLabel=formula.xlinkLabel)
                    else:
                        val.modelXbrl.error(u"xbrlfe:missingUnitRule",
                            _(u"Formula %(xlinkLabel)s omits a rule for the unit aspect"),
                            modelObject=formula, xlinkLabel=formula.xlinkLabel)
            elif (formula.hasRule(Aspect.MULTIPLY_BY) or formula.hasRule(Aspect.DIVIDE_BY) or 
                  formula.source(Aspect.UNIT, acceptFormulaSource=False)):
                val.modelXbrl.error(u"xbrlfe:conflictingAspectRules",
                    _(u"Formula %(xlinkLabel)s has a rule for the unit aspect of a non-numeric concept %(concept)s"),
                    modelObject=formula, xlinkLabel=formula.xlinkLabel, concept=concept.qname)
            aspectPeriodType = formula.evaluateRule(None, Aspect.PERIOD_TYPE)
            if ((concept.periodType == u"duration" and aspectPeriodType == u"instant") or
                (concept.periodType == u"instant" and aspectPeriodType in (u"duration",u"forever"))):
                val.modelXbrl.error(u"xbrlfe:conflictingAspectRules",
                    _(u"Formula %(xlinkLabel)s has a rule for the %(aspectPeriodType)s period aspect of a %(conceptPeriodType)s concept %(concept)s"),
                    modelObject=formula, xlinkLabel=formula.xlinkLabel, concept=concept.qname, aspectPeriodType=aspectPeriodType, conceptPeriodType=concept.periodType)
        
        # check dimension elements
        for eltName, dim, badUsageErr, missingSavErr in ((u"explicitDimension", u"explicit", u"xbrlfe:badUsageOfExplicitDimensionRule", u"xbrlfe:missingSAVForExplicitDimensionRule"),
                                                         (u"typedDimension", u"typed", u"xbrlfe:badUsageOfTypedDimensionRule", u"xbrlfe:missingSAVForTypedDimensionRule")):
            for dimElt in XmlUtil.descendants(formula, XbrlConst.formula, eltName):
                dimQname = qname(dimElt, dimElt.get(u"dimension"))
                dimConcept = val.modelXbrl.qnameConcepts.get(dimQname)
                if dimQname and (dimConcept is None or (not dimConcept.isExplicitDimension if dim == u"explicit" else not dimConcept.isTypedDimension)):
                    val.modelXbrl.error(badUsageErr,
                        _(u"Formula %(xlinkLabel)s dimension attribute %(dimension)s on the %(dimensionType)s dimension rule contains a QName that does not identify an (dimensionType)s dimension."),
                        modelObject=formula, xlinkLabel=formula.xlinkLabel, dimensionType=dim, dimension=dimQname,
                        messageCodes=(u"xbrlfe:badUsageOfExplicitDimensionRule", u"xbrlfe:badUsageOfTypedDimensionRule"))
                elif not XmlUtil.hasChild(dimElt, XbrlConst.formula, u"*") and not formula.source(Aspect.DIMENSIONS, dimElt):
                    val.modelXbrl.error(missingSavErr,
                        _(u"Formula %(xlinkLabel)s %(dimension)s dimension rule does not have any child elements and does not have a SAV for the %(dimensionType)s dimension that is identified by its dimension attribute."),
                        modelObject=formula, xlinkLabel=formula.xlinkLabel, dimensionType=dim, dimension=dimQname,
                        messageCodes=(u"xbrlfe:missingSAVForExplicitDimensionRule", u"xbrlfe:missingSAVForTypedDimensionRule"))
        
        # check aspect model expectations
        if formula.aspectModel == u"non-dimensional":
            unexpectedElts = XmlUtil.descendants(formula, XbrlConst.formula, (u"explicitDimension", u"typedDimension"))
            if unexpectedElts:
                val.modelXbrl.error(u"xbrlfe:unrecognisedAspectRule",
                    _(u"Formula %(xlinkLabel)s aspect model, %(aspectModel)s, includes an rule for aspect not defined in this aspect model: %(undefinedAspects)s"),
                    modelObject=formula, xlinkLabel=formula.xlinkLabel, aspectModel=formula.aspectModel, undefinedAspects=u", ".join([elt.localName for elt in unexpectedElts]))

    # check source qnames
    for sourceElt in ([formula] + 
                     XmlUtil.descendants(formula, XbrlConst.formula, u"*", u"source",u"*")):
        if sourceElt.get(u"source") is not None:
            qnSource = qname(sourceElt, sourceElt.get(u"source"), noPrefixIsNoNamespace=True)
            if qnSource == XbrlConst.qnFormulaUncovered:
                if formula.implicitFiltering != u"true":
                    val.modelXbrl.error(u"xbrlfe:illegalUseOfUncoveredQName",
                        _(u"Formula %(xlinkLabel)s, not implicit filtering element has formulaUncovered source: %(name)s"),
                        modelObject=formula, xlinkLabel=formula.xlinkLabel, name=sourceElt.localName) 
            elif qnSource not in nameVariables:
                val.modelXbrl.error(u"xbrlfe:nonexistentSourceVariable",
                    _(u"Variable set %(xlinkLabel)s, source %(name)s is not in the variable set"),
                    modelObject=formula, xlinkLabel=formula.xlinkLabel, name=qnSource)
            else:
                factVariable = nameVariables.get(qnSource)
                if isinstance(factVariable, ModelVariableSet):
                    pass
                elif not isinstance(factVariable, ModelFactVariable):
                    val.modelXbrl.error(u"xbrlfe:nonexistentSourceVariable",
                        _(u"Variable set %(xlinkLabel)s, source %(name)s not a factVariable but is a %(element)s"),
                        modelObject=formula, xlinkLabel=formula.xlinkLabel, name=qnSource, element=factVariable.localName)
                elif factVariable.fallbackValue is not None:
                    val.modelXbrl.error(u"xbrlfe:bindEmptySourceVariable",
                        _(u"Formula %(xlinkLabel)s: source %(name)s is a fact variable that has a fallback value"),
                        modelObject=formula, xlinkLabel=formula.xlinkLabel, name=qnSource)
                elif sourceElt.localName == u"formula" and factVariable.bindAsSequence == u"true":
                    val.modelXbrl.error(u"xbrlfe:defaultAspectValueConflicts",
                        _(u"Formula %(xlinkLabel)s: formula source %(name)s is a fact variable that binds as a sequence"),
                        modelObject=formula, xlinkLabel=formula.xlinkLabel, name=qnSource)
                
def checkTableRules(val, xpathContext, table):
    # check for covering aspect not in variable set aspect model
    checkFilterAspectModel(val, table, table.filterRelationships, xpathContext)

    checkDefinitionNodeRules(val, table, table, (XbrlConst.tableBreakdown, XbrlConst.tableBreakdownMMDD, XbrlConst.tableBreakdown201305, XbrlConst.tableAxis2011), xpathContext)
    
def checkDefinitionNodeRules(val, table, parent, arcrole, xpathContext):
    for rel in val.modelXbrl.relationshipSet(arcrole).fromModelObject(parent):
        axis = rel.toModelObject
        if axis is not None:
            if isinstance(axis, ModelFilterDefinitionNode):
                checkFilterAspectModel(val, table, axis.filterRelationships, xpathContext)
                #if not checkFilterAspectModel(val, table, axis.filterRelationships, xpathContext):
                    # this removed after 2013-01-06 PWD
                    #val.modelXbrl.error("xbrlte:axisFilterCoversNoAspects",
                    #    _("FilterAxis %(xlinkLabel)s does not cover any aspects."),
                    #    modelObject=axis, xlinkLabel=axis.xlinkLabel)
            else:
                if isinstance(axis, ModelRuleDefinitionNode):
                    # check dimension elements
                    for eltName, dim, badUsageErr in ((u"explicitDimension", u"explicit", u"xbrlfe:badUsageOfExplicitDimensionRule"),
                                                      (u"typedDimension", u"typed", u"xbrlfe:badUsageOfTypedDimensionRule")):
                        for dimElt in XmlUtil.descendants(axis, XbrlConst.formula, eltName):
                            dimQname = qname(dimElt, dimElt.get(u"dimension"))
                            dimConcept = val.modelXbrl.qnameConcepts.get(dimQname)
                            if dimQname and (dimConcept is None or (not dimConcept.isExplicitDimension if dim == u"explicit" else not dimConcept.isTypedDimension)):
                                val.modelXbrl.error(badUsageErr,
                                    _(u"RuleAxis %(xlinkLabel)s dimension attribute %(dimension)s on the %(dimensionType)s dimension rule contains a QName that does not identify an (dimensionType)s dimension."),
                                    modelObject=axis, xlinkLabel=axis.xlinkLabel, dimensionType=dim, dimension=dimQname,
                                    messageCodes=(u"xbrlfe:badUsageOfExplicitDimensionRule", u"xbrlfe:badUsageOfTypedDimensionRule"))
                            memQname = axis.evaluateRule(None, dimQname)
                            if dimConcept.isExplicitDimension and memQname is not None and memQname not in val.modelXbrl.qnameConcepts:  
                                val.modelXbrl.info(u"table:info",
                                                   _(u"RuleAxis rule %(xlinkLabel)s contains a member QName %(memQname)s which is not in the DTS."),
                                                   modelObject=axis, xlinkLabel=axis.xlinkLabel, memQname=memQname)
                    
                    # check aspect model expectations
                    if table.aspectModel == u"non-dimensional":
                        unexpectedElts = XmlUtil.descendants(axis, XbrlConst.formula, (u"explicitDimension", u"typedDimension"))
                        if unexpectedElts:
                            val.modelXbrl.error(u"xbrlte:axisAspectModelMismatch",
                                _(u"RuleAxis %(xlinkLabel)s aspect model, %(aspectModel)s, includes an rule for aspect not defined in this aspect model: %(undefinedAspects)s"),
                                modelObject=axis, xlinkLabel=axis.xlinkLabel, aspectModel=table.aspectModel, undefinedAspects=u", ".join([elt.localName for elt in unexpectedElts]))
            
                    # check source qnames
                    for sourceElt in ([axis] + 
                                     XmlUtil.descendants(axis, XbrlConst.formula, u"*", u"source",u"*")):
                        if sourceElt.get(u"source") is not None:
                            qnSource = qname(sourceElt, sourceElt.get(u"source"), noPrefixIsNoNamespace=True)
                            val.modelXbrl.info(u"table:info",
                                               _(u"RuleAxis rule %(xlinkLabel)s contains a @source attribute %(qnSource)s which is not applicable to table rule axes."),
                                               modelObject=axis, xlinkLabel=axis.xlinkLabel, qnSource=qnSource)
                    conceptQname = axis.evaluateRule(None, Aspect.CONCEPT)
                    if conceptQname and conceptQname not in val.modelXbrl.qnameConcepts:  
                        val.modelXbrl.info(u"table:info",
                                           _(u"RuleAxis rule %(xlinkLabel)s contains a concept QName %(conceptQname)s which is not in the DTS."),
                                           modelObject=axis, xlinkLabel=axis.xlinkLabel, conceptQname=conceptQname)
                        
                elif isinstance(axis, ModelRelationshipDefinitionNode):
                    for qnameAttr in (u"relationshipSourceQname", u"arcQname", u"linkQname", u"dimensionQname"):
                        eltQname = axis.get(qnameAttr)
                        if eltQname and eltQname not in val.modelXbrl.qnameConcepts:  
                            val.modelXbrl.info(u"table:info",
                                               _(u"%(axis)s rule %(xlinkLabel)s contains a %(qnameAttr)s QName %(qname)s which is not in the DTS."),
                                               modelObject=axis, axis=axis.localName.title(), xlinkLabel=axis.xlinkLabel, 
                                               qnameAttr=qnameAttr, qname=eltQname)
                checkDefinitionNodeRules(val, table, axis, (XbrlConst.tableBreakdownTree, XbrlConst.tableBreakdownTreeMMDD, XbrlConst.tableBreakdownTree201305, XbrlConst.tableDefinitionNodeSubtree201301, XbrlConst.tableAxisSubtree2011), xpathContext)                    

def checkValidationMessages(val, modelVariableSet):
    for msgRelationship in (XbrlConst.assertionSatisfiedMessage, XbrlConst.assertionUnsatisfiedMessage):
        for modelRel in val.modelXbrl.relationshipSet(msgRelationship).fromModelObject(modelVariableSet):
            checkMessageExpressions(val, modelRel.toModelObject)
            
def checkMessageExpressions(val, message):
    if isinstance(message, ModelMessage) and not hasattr(message,u"expressions"):
        formatString = []
        expressions = []
        bracketNesting = 0
        skipTo = None
        expressionIndex = 0
        expression = None
        lastC = None
        for c in message.text:
            if skipTo:
                if c == skipTo:
                    skipTo = None
            if expression is not None and c in (u'\'', u'"'):
                skipTo = c
            elif lastC == c and c in (u'{',u'}'):
                lastC = None
            elif lastC == u'{': 
                bracketNesting += 1
                expression = []
                lastC = None
            elif c == u'}' and expression is not None: 
                expressions.append( u''.join(expression).strip() )
                expression = None
                formatString.append( u"0[{0}]".format(expressionIndex) )
                expressionIndex += 1
                lastC = c
            elif lastC == u'}':
                bracketNesting -= 1
                lastC = None
            else:
                lastC = c
                
            if expression is not None: expression.append(c)
            else: formatString.append(c)
            
        if lastC == u'}':
            bracketNesting -= 1
        if bracketNesting:
            val.modelXbrl.error(u"xbrlmsge:missingLeftCurlyBracketInMessage" if bracketNesting < 0 else u"xbrlmsge:missingRightCurlyBracketInMessage",
                _(u"Message %(xlinkLabel)s: unbalanced %(character)s character(s) in: %(text)s"),
                modelObject=message, xlinkLabel=message.xlinkLabel, 
                character=u'{' if bracketNesting < 0 else u'}', 
                text=message.text,
                messageCodes=(u"xbrlmsge:missingLeftCurlyBracketInMessage", u"xbrlmsge:missingRightCurlyBracketInMessage"))
        else:
            message.expressions = expressions
            message.formatString = u''.join( formatString )
        if not message.xmlLang:
            val.modelXbrl.error(u"xbrlmsge:xbrlmsge:missingMessageLanguage",
                _(u"Message %(xlinkLabel)s is missing an effective value for xml:lang: %(text)s."),
                modelObject=message, xlinkLabel=message.xlinkLabel, text=message.text)

def checkValidationMessageVariables(val, modelVariableSet, varNames, paramNames):
    if isinstance(modelVariableSet, ModelConsistencyAssertion):
        varSetVars = (qname(XbrlConst.ca,u'aspect-matched-facts'),
                      qname(XbrlConst.ca,u'acceptance-radius'),
                      qname(XbrlConst.ca,u'absolute-acceptance-radius-expression'),
                      qname(XbrlConst.ca,u'proportional-acceptance-radius-expression'))
    elif isinstance(modelVariableSet, ModelExistenceAssertion):
        varSetVars = (XbrlConst.qnEaTestExpression,)
    elif isinstance(modelVariableSet, ModelValueAssertion):
        varSetVars = (XbrlConst.qnVaTestExpression,)
    for msgRelationship in (XbrlConst.assertionSatisfiedMessage, XbrlConst.assertionUnsatisfiedMessage):
        for modelRel in val.modelXbrl.relationshipSet(msgRelationship).fromModelObject(modelVariableSet):
            message = modelRel.toModelObject
            message.compile()
            for msgVarQname in message.variableRefs():
                if msgVarQname not in varNames and msgVarQname not in varSetVars and msgVarQname not in paramNames:
                    val.modelXbrl.error(u"err:XPST0008",
                        _(u"Undefined variable dependency in message %(xlinkLabel)s, %(name)s"),
                        modelObject=message, xlinkLabel=message.xlinkLabel, name=msgVarQname)
                elif (msgVarQname in varNames and 
                      isinstance(modelVariableSet, ModelExistenceAssertion) and
                      isinstance(varNames[msgVarQname].toModelObject,ModelVariable)):
                    val.modelXbrl.error(u"err:XPST0008",
                        _(u"Existence Assertion depends on evaluation variable in message %(xlinkLabel)s, %(name)s"),
                        modelObject=message, xlinkLabel=message.xlinkLabel, name=msgVarQname)
