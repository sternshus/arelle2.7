u'''
Created on Oct 17, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
try:
    import regex as re
except ImportError:
    import re
from arelle import (ModelDocument, XmlUtil, XbrlUtil, XbrlConst, 
                ValidateXbrlCalcs, ValidateXbrlDimensions, ValidateXbrlDTS, ValidateFormula, ValidateUtr)
from arelle import FunctionIxt
from arelle.ModelObject import ModelObject
from arelle.ModelDtsObject import ModelConcept
from arelle.ModelInstanceObject import ModelInlineFact
from arelle.ModelValue import qname
from arelle.PluginManager import pluginClassMethods
from arelle.XmlValidate import VALID
from collections import defaultdict
validateUniqueParticleAttribution = None # dynamic import

arcNamesTo21Resource = set([u"labelArc",u"referenceArc"])
xlinkTypeValues = set([None, u"simple", u"extended", u"locator", u"arc", u"resource", u"title", u"none"])
xlinkActuateValues = set([None, u"onLoad", u"onRequest", u"other", u"none"])
xlinkShowValues = set([None, u"new", u"replace", u"embed", u"other", u"none"])
xlinkLabelAttributes = set([u"{http://www.w3.org/1999/xlink}label", u"{http://www.w3.org/1999/xlink}from", u"{http://www.w3.org/1999/xlink}to"])
periodTypeValues = set([u"instant",u"duration"])
balanceValues = set([None, u"credit",u"debit"])
baseXbrliTypes = set([
        u"decimalItemType", u"floatItemType", u"doubleItemType", u"integerItemType",
        u"nonPositiveIntegerItemType", u"negativeIntegerItemType", u"longItemType", u"intItemType",
        u"shortItemType", u"byteItemType", u"nonNegativeIntegerItemType", u"unsignedLongItemType",
        u"unsignedIntItemType", u"unsignedShortItemType", u"unsignedByteItemType",
        u"positiveIntegerItemType", u"monetaryItemType", u"sharesItemType", u"pureItemType",
        u"fractionItemType", u"stringItemType", u"booleanItemType", u"hexBinaryItemType",
        u"base64BinaryItemType", u"anyURIItemType", u"QNameItemType", u"durationItemType",
        u"dateTimeItemType", u"timeItemType", u"dateItemType", u"gYearMonthItemType",
        u"gYearItemType", u"gMonthDayItemType", u"gDayItemType", u"gMonthItemType",
        u"normalizedStringItemType", u"tokenItemType", u"languageItemType", u"NameItemType", u"NCNameItemType"])

class ValidateXbrl(object):
    def __init__(self, testModelXbrl):
        self.testModelXbrl = testModelXbrl
        
    def close(self, reusable=True):
        if reusable:
            testModelXbrl = self.testModelXbrl
        self.__dict__.clear()   # dereference everything
        if reusable:
            self.testModelXbrl = testModelXbrl
        
    def validate(self, modelXbrl, parameters=None):
        self.parameters = parameters
        self.precisionPattern = re.compile(u"^([0-9]+|INF)$")
        self.decimalsPattern = re.compile(u"^(-?[0-9]+|INF)$")
        self.isoCurrencyPattern = re.compile(ur"^[A-Z]{3}$")
        self.modelXbrl = modelXbrl
        self.validateDisclosureSystem = modelXbrl.modelManager.validateDisclosureSystem
        self.disclosureSystem = modelXbrl.modelManager.disclosureSystem
        self.validateEFM = self.validateDisclosureSystem and self.disclosureSystem.EFM
        self.validateGFM = self.validateDisclosureSystem and self.disclosureSystem.GFM
        self.validateEFMorGFM = self.validateDisclosureSystem and self.disclosureSystem.EFMorGFM
        self.validateHMRC = self.validateDisclosureSystem and self.disclosureSystem.HMRC
        self.validateSBRNL = self.validateDisclosureSystem and self.disclosureSystem.SBRNL
        self.validateXmlLang = self.validateDisclosureSystem and self.disclosureSystem.xmlLangPattern
        self.validateCalcLB = modelXbrl.modelManager.validateCalcLB
        self.validateInferDecimals = modelXbrl.modelManager.validateInferDecimals
        self.validateUTR = (modelXbrl.modelManager.validateUtr or
                            (self.parameters and self.parameters.get(qname(u"forceUtrValidation",noPrefixIsNoNamespace=True),(None,u"false"))[1] == u"true") or
                            (self.validateEFM and 
                             any((concept.qname.namespaceURI in self.disclosureSystem.standardTaxonomiesDict) 
                                 for concept in self.modelXbrl.nameConcepts.get(u"UTR",()))))
        self.validateIXDS = False # set when any inline document found
        self.validateEnum = XbrlConst.enum in modelXbrl.namespaceDocs
        
        for pluginXbrlMethod in pluginClassMethods(u"Validate.XBRL.Start"):
            pluginXbrlMethod(self)

        # xlink validation
        modelXbrl.profileStat(None)
        modelXbrl.modelManager.showStatus(_(u"validating links"))
        modelLinks = set()
        self.remoteResourceLocElements = set()
        self.genericArcArcroles = set()
        for baseSetExtLinks in modelXbrl.baseSets.values():
            for baseSetExtLink in baseSetExtLinks:
                modelLinks.add(baseSetExtLink)    # ext links are unique (no dups)
        self.checkLinks(modelLinks)
        modelXbrl.profileStat(_(u"validateLinks"))

        modelXbrl.dimensionDefaultConcepts = {}
        modelXbrl.qnameDimensionDefaults = {}
        modelXbrl.qnameDimensionContextElement = {}
        # check base set cycles, dimensions
        modelXbrl.modelManager.showStatus(_(u"validating relationship sets"))
        for baseSetKey in modelXbrl.baseSets.keys():
            arcrole, ELR, linkqname, arcqname = baseSetKey
            if arcrole.startswith(u"XBRL-") or ELR is None or \
                linkqname is None or arcqname is None:
                continue
            elif arcrole in XbrlConst.standardArcroleCyclesAllowed:
                # TODO: table should be in this module, where it is used
                cyclesAllowed, specSect = XbrlConst.standardArcroleCyclesAllowed[arcrole]
            elif arcrole in self.modelXbrl.arcroleTypes and len(self.modelXbrl.arcroleTypes[arcrole]) > 0:
                cyclesAllowed = self.modelXbrl.arcroleTypes[arcrole][0].cyclesAllowed
                if arcrole in self.genericArcArcroles:
                    specSect = u"xbrlgene:violatedCyclesConstraint"
                else:
                    specSect = u"xbrl.5.1.4.3:cycles"
            else:
                cyclesAllowed = u"any"
                specSect = None
            if cyclesAllowed != u"any" or arcrole in (XbrlConst.summationItem,) \
                                      or arcrole in self.genericArcArcroles  \
                                      or arcrole.startswith(XbrlConst.formulaStartsWith) \
                                      or (modelXbrl.hasXDT and arcrole.startswith(XbrlConst.dimStartsWith)):
                relsSet = modelXbrl.relationshipSet(arcrole,ELR,linkqname,arcqname)
            if cyclesAllowed != u"any" and \
                   (XbrlConst.isStandardExtLinkQname(linkqname) and XbrlConst.isStandardArcQname(arcqname)) \
                   or arcrole in self.genericArcArcroles:
                noUndirected = cyclesAllowed == u"none"
                fromRelationships = relsSet.fromModelObjects()
                for relFrom, rels in fromRelationships.items():
                    cycleFound = self.fwdCycle(relsSet, rels, noUndirected, set([relFrom]))
                    if cycleFound is not None:
                        pathEndsAt = len(cycleFound)  # consistently find start of path
                        loopedModelObject = cycleFound[1].toModelObject
                        for i, rel in enumerate(cycleFound[2:]):
                            if rel.fromModelObject == loopedModelObject:
                                pathEndsAt = 3 + i # don't report extra path elements before loop
                                break
                        path = unicode(loopedModelObject.qname) + u" " + u" - ".join(
                            u"{0}:{1} {2}".format(rel.modelDocument.basename, rel.sourceline, rel.toModelObject.qname)
                            for rel in reversed(cycleFound[1:pathEndsAt]))
                        modelXbrl.error(specSect,
                            _(u"Relationships have a %(cycle)s cycle in arcrole %(arcrole)s \nlink role %(linkrole)s \nlink %(linkname)s, \narc %(arcname)s, \npath %(path)s"),
                            modelObject=cycleFound[1:pathEndsAt], cycle=cycleFound[0], path=path,
                            arcrole=arcrole, linkrole=ELR, linkname=linkqname, arcname=arcqname,
                            messageCodes=(u"xbrlgene:violatedCyclesConstraint", u"xbrl.5.1.4.3:cycles",
                                          # from XbrlCoinst.standardArcroleCyclesAllowed
                                          u"xbrl.5.2.4.2", u"xbrl.5.2.5.2", u"xbrl.5.2.6.2.1", u"xbrl.5.2.6.2.1", u"xbrl.5.2.6.2.3", u"xbrl.5.2.6.2.4")) 
                        break
                
            # check calculation arcs for weight issues (note calc arc is an "any" cycles)
            if arcrole == XbrlConst.summationItem:
                for modelRel in relsSet.modelRelationships:
                    weight = modelRel.weight
                    fromConcept = modelRel.fromModelObject
                    toConcept = modelRel.toModelObject
                    if fromConcept is not None and toConcept is not None:
                        if weight == 0:
                            modelXbrl.error(u"xbrl.5.2.5.2.1:zeroWeight",
                                _(u"Calculation relationship has zero weight from %(source)s to %(target)s in link role %(linkrole)s"),
                                modelObject=modelRel,
                                source=fromConcept.qname, target=toConcept.qname, linkrole=ELR), 
                        fromBalance = fromConcept.balance
                        toBalance = toConcept.balance
                        if fromBalance and toBalance:
                            if (fromBalance == toBalance and weight < 0) or \
                               (fromBalance != toBalance and weight > 0):
                                modelXbrl.error(u"xbrl.5.1.1.2:balanceCalcWeightIllegal" +
                                                (u"Negative" if weight < 0 else u"Positive"),
                                    _(u"Calculation relationship has illegal weight %(weight)s from %(source)s, %(sourceBalance)s, to %(target)s, %(targetBalance)s, in link role %(linkrole)s (per 5.1.1.2 Table 6)"),
                                    modelObject=modelRel, weight=weight,
                                    source=fromConcept.qname, target=toConcept.qname, linkrole=ELR, 
                                    sourceBalance=fromBalance, targetBalance=toBalance,
                                    messageCodes=(u"xbrl.5.1.1.2:balanceCalcWeightIllegalNegative", u"xbrl.5.1.1.2:balanceCalcWeightIllegalPositive"))
                        if not fromConcept.isNumeric or not toConcept.isNumeric:
                            modelXbrl.error(u"xbrl.5.2.5.2:nonNumericCalc",
                                _(u"Calculation relationship has illegal concept from %(source)s%(sourceNumericDecorator)s to %(target)s%(targetNumericDecorator)s in link role %(linkrole)s"),
                                modelObject=modelRel,
                                source=fromConcept.qname, target=toConcept.qname, linkrole=ELR, 
                                sourceNumericDecorator=u"" if fromConcept.isNumeric else _(u" (non-numeric)"), 
                                targetNumericDecorator=u"" if toConcept.isNumeric else _(u" (non-numeric)"))
            # check presentation relationships for preferredLabel issues
            elif arcrole == XbrlConst.parentChild:
                for modelRel in relsSet.modelRelationships:
                    preferredLabel = modelRel.preferredLabel
                    fromConcept = modelRel.fromModelObject
                    toConcept = modelRel.toModelObject
                    if preferredLabel is not None and isinstance(fromConcept, ModelConcept) and isinstance(toConcept, ModelConcept):
                        label = toConcept.label(preferredLabel=preferredLabel,fallbackToQname=False,strip=True)
                        if label is None:
                            modelXbrl.error(u"xbrl.5.2.4.2.1:preferredLabelMissing",
                                _(u"Presentation relationship from %(source)s to %(target)s in link role %(linkrole)s missing preferredLabel %(preferredLabel)s"),
                                modelObject=modelRel,
                                source=fromConcept.qname, target=toConcept.qname, linkrole=ELR, 
                                preferredLabel=preferredLabel)
                        elif not label: # empty string
                            modelXbrl.info(u"arelle:info.preferredLabelEmpty",
                                _(u"(Info xbrl.5.2.4.2.1) Presentation relationship from %(source)s to %(target)s in link role %(linkrole)s has empty preferredLabel %(preferredLabel)s"),
                                modelObject=modelRel,
                                source=fromConcept.qname, target=toConcept.qname, linkrole=ELR, 
                                preferredLabel=preferredLabel)
            # check essence-alias relationships
            elif arcrole == XbrlConst.essenceAlias:
                for modelRel in relsSet.modelRelationships:
                    fromConcept = modelRel.fromModelObject
                    toConcept = modelRel.toModelObject
                    if fromConcept is not None and toConcept is not None:
                        if fromConcept.type != toConcept.type or fromConcept.periodType != toConcept.periodType:
                            modelXbrl.error(u"xbrl.5.2.6.2.2:essenceAliasTypes",
                                _(u"Essence-alias relationship from %(source)s to %(target)s in link role %(linkrole)s has different types or periodTypes"),
                                modelObject=modelRel,
                                source=fromConcept.qname, target=toConcept.qname, linkrole=ELR)
                        fromBalance = fromConcept.balance
                        toBalance = toConcept.balance
                        if fromBalance and toBalance:
                            if fromBalance and toBalance and fromBalance != toBalance:
                                modelXbrl.error(u"xbrl.5.2.6.2.2:essenceAliasBalance",
                                    _(u"Essence-alias relationship from %(source)s to %(target)s in link role %(linkrole)s has different balances")).format(
                                    modelObject=modelRel,
                                    source=fromConcept.qname, target=toConcept.qname, linkrole=ELR)
            elif modelXbrl.hasXDT and arcrole.startswith(XbrlConst.dimStartsWith):
                ValidateXbrlDimensions.checkBaseSet(self, arcrole, ELR, relsSet)             
            elif (modelXbrl.hasFormulae or modelXbrl.hasTableRendering) and arcrole.startswith(XbrlConst.formulaStartsWith):
                ValidateFormula.checkBaseSet(self, arcrole, ELR, relsSet)
        modelXbrl.isDimensionsValidated = True
        modelXbrl.profileStat(_(u"validateRelationships"))
                            
        # instance checks
        modelXbrl.modelManager.showStatus(_(u"validating instance"))
        if modelXbrl.modelDocument.type == ModelDocument.Type.INSTANCE or \
           modelXbrl.modelDocument.type == ModelDocument.Type.INLINEXBRL:
            self.checkFacts(modelXbrl.facts)
            self.checkContexts(self.modelXbrl.contexts.values())
            self.checkUnits(self.modelXbrl.units.values())

            modelXbrl.profileStat(_(u"validateInstance"))

            if modelXbrl.hasXDT:            
                modelXbrl.modelManager.showStatus(_(u"validating dimensions"))
                u''' uncomment if using otherFacts in checkFact
                dimCheckableFacts = set(f 
                                        for f in modelXbrl.factsInInstance
                                        if f.concept.isItem and f.context is not None)
                while (dimCheckableFacts): # check one and all of its compatible family members
                    f = dimCheckableFacts.pop()
                    ValidateXbrlDimensions.checkFact(self, f, dimCheckableFacts)
                del dimCheckableFacts
                '''
                self.checkFactsDimensions(modelXbrl.facts) # check fact dimensions in document order
                self.checkContextsDimensions(modelXbrl.contexts.values())
                modelXbrl.profileStat(_(u"validateDimensions"))
                    
        # dimensional validity
        #concepts checks
        modelXbrl.modelManager.showStatus(_(u"validating concepts"))
        for concept in modelXbrl.qnameConcepts.values():
            conceptType = concept.type
            if (concept.qname is None or
                XbrlConst.isStandardNamespace(concept.qname.namespaceURI) or 
                not concept.modelDocument.inDTS):
                continue
            
            if concept.isTuple:
                # must be global
                if not concept.getparent().localName == u"schema":
                    self.modelXbrl.error(u"xbrl.4.9:tupleGloballyDeclared",
                        _(u"Tuple %(concept)s must be declared globally"),
                        modelObject=concept, concept=concept.qname)
                if concept.periodType:
                    self.modelXbrl.error(u"xbrl.4.9:tuplePeriodType",
                        _(u"Tuple %(concept)s must not have periodType"),
                        modelObject=concept, concept=concept.qname)
                if concept.balance:
                    self.modelXbrl.error(u"xbrl.4.9:tupleBalance",
                        _(u"Tuple %(concept)s must not have balance"),
                        modelObject=concept, concept=concept.qname)
                if conceptType is not None:
                    # check attribute declarations
                    for attribute in conceptType.attributes.values():
                        if attribute.qname is not None and attribute.qname.namespaceURI in (XbrlConst.xbrli, XbrlConst.link, XbrlConst.xlink, XbrlConst.xl):
                            self.modelXbrl.error(u"xbrl.4.9:tupleAttribute",
                                _(u"Tuple %(concept)s must not have attribute in this namespace %(attribute)s"),
                                modelObject=concept, concept=concept.qname, attribute=attribute.qname)
                    # check for mixed="true" or simple content
                    if XmlUtil.descendantAttr(conceptType, XbrlConst.xsd, (u"complexType", u"complexContent"), u"mixed") == u"true":
                        self.modelXbrl.error(u"xbrl.4.9:tupleMixedContent",
                            _(u"Tuple %(concept)s must not have mixed content"),
                            modelObject=concept, concept=concept.qname)
                    if XmlUtil.descendant(conceptType, XbrlConst.xsd, u"simpleContent"):
                        self.modelXbrl.error(u"xbrl.4.9:tupleSimpleContent",
                            _(u"Tuple %(concept)s must not have simple content"),
                            modelObject=concept, concept=concept.qname)
                    # child elements must be item or tuple
                    for elementQname in conceptType.elements:
                        childConcept = self.modelXbrl.qnameConcepts.get(elementQname)
                        if childConcept is None:
                            self.modelXbrl.error(u"xbrl.4.9:tupleElementUndefined",
                                _(u"Tuple %(concept)s element %(tupleElement)s not defined"),
                                modelObject=concept, concept=unicode(concept.qname), tupleElement=elementQname)
                        elif not (childConcept.isItem or childConcept.isTuple or # isItem/isTuple do not include item or tuple itself
                                  childConcept.qname == XbrlConst.qnXbrliItem or # subs group includes item as member
                                  childConcept.qname == XbrlConst.qnXbrliTuple):
                            self.modelXbrl.error(u"xbrl.4.9:tupleElementItemOrTuple",
                                _(u"Tuple %(concept)s must not have element %(tupleElement)s not an item or tuple"),
                                modelObject=concept, concept=concept.qname, tupleElement=elementQname)
            elif concept.isItem:
                if concept.periodType not in periodTypeValues: #("instant","duration"):
                    self.modelXbrl.error(u"xbrl.5.1.1.1:itemPeriodType",
                        _(u"Item %(concept)s must have a valid periodType"),
                        modelObject=concept, concept=concept.qname)
                if concept.isMonetary:
                    if concept.balance not in balanceValues: #(None, "credit","debit"):
                        self.modelXbrl.error(u"xbrl.5.1.1.2:itemBalance",
                            _(u"Item %(concept)s must have a valid balance %(balance)s"),
                            modelObject=concept, concept=concept.qname, balance=concept.balance)
                else:
                    if concept.balance:
                        self.modelXbrl.error(u"xbrl.5.1.1.2:itemBalance",
                            _(u"Item %(concept)s may not have a balance"),
                            modelObject=concept, concept=concept.qname)
                if concept.baseXbrliType not in baseXbrliTypes:
                    self.modelXbrl.error(u"xbrl.5.1.1.3:itemType",
                        _(u"Item %(concept)s type %(itemType)s invalid"),
                        modelObject=concept, concept=concept.qname, itemType=concept.baseXbrliType)
                if self.validateEnum and concept.isEnumeration:
                    if not concept.enumDomainQname:
                        self.modelXbrl.error(u"enumte:MissingDomainError",
                            _(u"Item %(concept)s enumeration type must specify a domain."),
                            modelObject=concept, concept=concept.qname)
                    elif concept.enumDomain is None or (not concept.enumDomain.isItem) or concept.enumDomain.isHypercubeItem or concept.enumDomain.isDimensionItem:
                        self.modelXbrl.error(u"enumte:InvalidDomainError",
                            _(u"Item %(concept)s enumeration type must be a xbrli:item that is neither a hypercube nor dimension."),
                            modelObject=concept, concept=concept.qname)
                    if not concept.enumLinkrole:
                        self.modelXbrl.error(u"enumte:MissingLinkRoleError",
                            _(u"Item %(concept)s enumeration type must specify a linkrole."),
                            modelObject=concept, concept=concept.qname)
                if modelXbrl.hasXDT:
                    if concept.isHypercubeItem and not concept.abstract == u"true":
                        self.modelXbrl.error(u"xbrldte:HypercubeElementIsNotAbstractError",
                            _(u"Hypercube item %(concept)s must be abstract"),
                            modelObject=concept, concept=concept.qname)
                    elif concept.isDimensionItem and not concept.abstract == u"true":
                        self.modelXbrl.error(u"xbrldte:DimensionElementIsNotAbstractError",
                            _(u"Dimension item %(concept)s must be abstract"),
                            modelObject=concept, concept=concept.qname)
            if modelXbrl.hasXDT:
                ValidateXbrlDimensions.checkConcept(self, concept)
        modelXbrl.profileStat(_(u"validateConcepts"))
        
        for pluginXbrlMethod in pluginClassMethods(u"Validate.XBRL.Finally"):
            pluginXbrlMethod(self)

        modelXbrl.profileStat() # reset after plugins
            
        modelXbrl.modelManager.showStatus(_(u"validating DTS"))
        self.DTSreferenceResourceIDs = {}
        checkedModelDocuments = set()
        ValidateXbrlDTS.checkDTS(self, modelXbrl.modelDocument, checkedModelDocuments)
        # ARELLE-220: check imported documents that aren't DTS discovered
        for importedModelDocument in (set(modelXbrl.urlDocs.values()) - checkedModelDocuments):
            ValidateXbrlDTS.checkDTS(self, importedModelDocument, checkedModelDocuments)
        del checkedModelDocuments, self.DTSreferenceResourceIDs
        
        global validateUniqueParticleAttribution
        if validateUniqueParticleAttribution is None:
            from arelle.XmlValidateParticles import validateUniqueParticleAttribution
        for modelType in modelXbrl.qnameTypes.values():
            validateUniqueParticleAttribution(modelXbrl, modelType.particlesList, modelType)
        modelXbrl.profileStat(_(u"validateDTS"))
        
        if self.validateCalcLB:
            modelXbrl.modelManager.showStatus(_(u"Validating instance calculations"))
            ValidateXbrlCalcs.validate(modelXbrl, inferDecimals=self.validateInferDecimals)
            modelXbrl.profileStat(_(u"validateCalculations"))
            
        if self.validateUTR:
            ValidateUtr.validateFacts(modelXbrl)
            modelXbrl.profileStat(_(u"validateUTR"))
            
        if self.validateIXDS:
            modelXbrl.modelManager.showStatus(_(u"Validating inline document set"))
            ixdsIdObjects = defaultdict(list)
            for ixdsDoc in self.ixdsDocs:
                for idObject in ixdsDoc.idObjects.values():
                    if idObject.namespaceURI in XbrlConst.ixbrlAll or idObject.elementQname in (XbrlConst.qnXbrliContext, XbrlConst.qnXbrliUnit):
                        ixdsIdObjects[idObject.id].append(idObject)
            for _id, objs in ixdsIdObjects.items():
                if len(objs) > 1:
                    modelXbrl.error(u"ix:uniqueIxId",
                        _(u"Inline XBRL id is not unique in the IXDS: %(id)s, for element(s) %{elements)s"),
                        modelObject=objs, id=_id, elements=set(unicode(obj.elementQname) for obj in objs))
            self.factsWithDeprecatedIxNamespace = []
            factFootnoteRefs = set()
            for f in modelXbrl.factsInInstance:
                for footnoteID in f.footnoteRefs:
                    if footnoteID not in self.ixdsFootnotes:
                        modelXbrl.error(u"ix:footnoteRef",
                            _(u"Inline XBRL fact's footnoteRef not found: %(id)s"),
                            modelObject=f, id=footnoteID)
                    factFootnoteRefs.add(footnoteID)
                if f.concept is None:
                    self.modelXbrl.error(u"xbrl:schemaImportMissing",
                            _(u"Fact %(fact)s missing schema definition or missing name attribute"),
                            modelObject=f, fact=f.qname)
                if f.localName in set([u"fraction", u"nonFraction", u"nonNumeric"]):
                    if f.context is None:
                        self.modelXbrl.error(u"ix:missingContext",
                            _(u"Fact %(fact)s is missing a context for contextRef %(context)s"),
                            modelObject=f, fact=f.qname, context=f.contextID)
                if f.localName in set([u"fraction", u"nonFraction"]):
                    if f.unit is None:
                        self.modelXbrl.error(u"ix:missingUnit",
                            _(u"Fact %(fact)s is missing a unit for unitRef %(unit)s"),
                            modelObject=f, fact=f.qname, unit=f.unitID)
                fmt = f.format
                if fmt:
                    if fmt.namespaceURI not in FunctionIxt.ixtNamespaceURIs:
                        self.modelXbrl.error(u"ix:invalidTransformation",
                            _(u"Fact %(fact)s has unrecognized transformation namespace %(namespace)s"),
                            modelObject=f, fact=f.qname, namespace=fmt.namespaceURI)
                    elif fmt.localName not in FunctionIxt.ixtFunctions:
                        self.modelXbrl.error(u"ix:invalidTransformation",
                            _(u"Fact %(fact)s has unrecognized transformation name %(name)s"),
                            modelObject=f, fact=f.qname, name=fmt.localName)
                    if fmt.namespaceURI == FunctionIxt.deprecatedNamespaceURI:
                        self.factsWithDeprecatedIxNamespace.append(f)
            for _id, objs in self.ixdsFootnotes.items():
                if len(objs) > 1:
                    modelXbrl.error(u"ix:uniqueFootnoteId",
                        _(u"Inline XBRL footnote id is not unique in the IXDS: %(id)s"),
                        modelObject=objs, id=_id)
                else:
                    if self.validateGFM:
                        elt = objs[0]
                        id = elt.footnoteID
                        if id and id not in factFootnoteRefs and elt.textValue:
                            self.modelXbrl.error((u"EFM.N/A", u"GFM:1.10.15"),
                                _(u"Inline XBRL non-empty footnote %(footnoteID)s is not referenced by any fact"),
                                modelObject=elt, footnoteID=id)
            if not self.ixdsHeaderCount:
                modelXbrl.error(u"ix:headerMissing",
                    _(u"Inline XBRL document set must have at least one ix:header element"),
                    modelObject=modelXbrl)
            if self.factsWithDeprecatedIxNamespace:
                self.modelXbrl.info(u"arelle:info",
                    _(u"%(count)s facts have deprecated transformation namespace %(namespace)s"),
                        modelObject=self.factsWithDeprecatedIxNamespace,
                        count=len(self.factsWithDeprecatedIxNamespace), 
                        namespace=FunctionIxt.deprecatedNamespaceURI)

            del self.factsWithDeprecatedIxNamespace
            for target, ixReferences in self.ixdsReferences.items():
                targetDefaultNamespace = None
                schemaRefUris = {}
                for i, ixReference in enumerate(ixReferences):
                    defaultNamepace = XmlUtil.xmlns(ixReference, None)
                    if i == 0:
                        targetDefaultNamespace = defaultNamepace 
                    elif targetDefaultNamespace != defaultNamepace:
                        modelXbrl.error(u"ix:referenceInconsistentDefaultNamespaces",
                            _(u"Inline XBRL document set must have consistent default namespaces for target %(target)s"),
                            modelObject=ixReferences, target=target)
                    for schemaRef in XmlUtil.children(ixReference, XbrlConst.link, u"schemaRef"):
                        href = schemaRef.get(u"{http://www.w3.org/1999/xlink}href")
                        prefix = XmlUtil.xmlnsprefix(schemaRef, href)
                        if href not in schemaRefUris:
                            schemaRefUris[href] = prefix
                        elif schemaRefUris[href] != prefix:
                            modelXbrl.error(u"ix:referenceNamespacePrefixInconsistency",
                                _(u"Inline XBRL document set must have consistent prefixes for target %(target)s: %(prefix1)s, %(prefix2)s"),
                                modelObject=ixReferences, target=target, prefix1=schemaRefUris[href], prefix2=prefix)
            for ixRel in self.ixdsRelationships:
                for fromRef in ixRel.get(u"fromRefs",u"").split():
                    refs = ixdsIdObjects.get(fromRef)
                    if refs is None or refs[0].namespaceURI != ixRel or refs[0].localName not in (u"fraction", u"nonFraction", u"nonNumeric", u"tuple"):
                        modelXbrl.error(u"ix:relationshipFromRef",
                            _(u"Inline XBRL fromRef %(ref)s is not a fraction, ix:nonFraction, ix:nonNumeric or ix:tuple."),
                            modelObject=ixRel, ref=fromRef)
                hasFootnoteToRef = None
                hasToRefMixture = False
                for toRef in ixRel.get(u"toRefs",u"").split():
                    refs = ixdsIdObjects.get(fromRef)
                    if refs is None or refs[0].namespaceURI != ixRel or refs[0].localName not in (u"footnote", u"fraction", u"nonFraction", u"nonNumeric", u"tuple"):
                        modelXbrl.error(u"ix:relationshipToRef",
                            _(u"Inline XBRL fromRef %(ref)s is not a footnote, fraction, ix:nonFraction, ix:nonNumeric or ix:tuple."),
                            modelObject=ixRel, ref=fromRef)
                    elif hasFootnoteToRef is None:
                        hasFootnoteToRef = refs[0].localName == u"footnote"
                    elif hasFootnoteToRef != (refs[0].localName == u"footnote"):
                        hasToRefMixture = True
                if hasToRefMixture:
                    modelXbrl.error(u"ix:relationshipToRefMix",
                        _(u"Inline XBRL fromRef is not only either footnotes, or ix:fraction, ix:nonFraction, ix:nonNumeric or ix:tuple."),
                        modelObject=ixRel)
            del ixdsIdObjects
            # tupleRefs already checked during loading
            modelXbrl.profileStat(_(u"validateInline"))
        
        if modelXbrl.hasFormulae or modelXbrl.modelRenderingTables:
            ValidateFormula.validate(self, 
                                     statusMsg=_(u"compiling formulae and rendering tables") if (modelXbrl.hasFormulae and modelXbrl.modelRenderingTables)
                                     else (_(u"compiling formulae") if modelXbrl.hasFormulae
                                           else _(u"compiling rendering tables")),
                                     # block executing formulas when validating if hasFormula is False (e.g., --formula=none)
                                     compileOnly=modelXbrl.modelRenderingTables and not modelXbrl.hasFormulae)
            
        for pluginXbrlMethod in pluginClassMethods(u"Validate.Finally"):
            pluginXbrlMethod(self)

        modelXbrl.modelManager.showStatus(_(u"ready"), 2000)
        
    def checkLinks(self, modelLinks):
        for modelLink in modelLinks:
            fromToArcs = {}
            locLabels = {}
            resourceLabels = {}
            resourceArcTos = []
            for arcElt in modelLink.iterchildren():
                if isinstance(arcElt,ModelObject):
                    xlinkType = arcElt.get(u"{http://www.w3.org/1999/xlink}type")
                    # locator must have an href
                    if xlinkType == u"locator":
                        if arcElt.get(u"{http://www.w3.org/1999/xlink}href") is None:
                            self.modelXbrl.error(u"xlink:locatorHref",
                                _(u"Xlink locator %(xlinkLabel)s missing href in extended link %(linkrole)s"),
                                modelObject=arcElt,
                                linkrole=modelLink.role, 
                                xlinkLabel=arcElt.get(u"{http://www.w3.org/1999/xlink}label")) 
                        locLabels[arcElt.get(u"{http://www.w3.org/1999/xlink}label")] = arcElt
                    elif xlinkType == u"resource":
                        resourceLabels[arcElt.get(u"{http://www.w3.org/1999/xlink}label")] = arcElt
                    # can be no duplicated arcs between same from and to
                    elif xlinkType == u"arc":
                        fromLabel = arcElt.get(u"{http://www.w3.org/1999/xlink}from")
                        toLabel = arcElt.get(u"{http://www.w3.org/1999/xlink}to")
                        fromTo = (fromLabel,toLabel)
                        if fromTo in fromToArcs:
                            self.modelXbrl.error(u"xlink:dupArcs",
                                _(u"Duplicate xlink arcs  in extended link %(linkrole)s from %(xlinkLabelFrom)s to %(xlinkLabelTo)s"),
                                modelObject=arcElt,
                                linkrole=modelLink.role, 
                                xlinkLabelFrom=fromLabel, xlinkLabelTo=toLabel)
                        else:
                            fromToArcs[fromTo] = arcElt
                        if arcElt.namespaceURI == XbrlConst.link:
                            if arcElt.localName in arcNamesTo21Resource: #("labelArc","referenceArc"):
                                resourceArcTos.append((toLabel, arcElt.get(u"use"), arcElt))
                        elif self.isGenericArc(arcElt):
                            arcrole = arcElt.get(u"{http://www.w3.org/1999/xlink}arcrole")
                            self.genericArcArcroles.add(arcrole)
                            if arcrole in (XbrlConst.elementLabel, XbrlConst.elementReference):
                                resourceArcTos.append((toLabel, arcrole, arcElt))
                    # values of type (not needed for validating parsers)
                    if xlinkType not in xlinkTypeValues: # ("", "simple", "extended", "locator", "arc", "resource", "title", "none"):
                        self.modelXbrl.error(u"xlink:type",
                            _(u"Xlink type %(xlinkType)s invalid in extended link %(linkrole)s"),
                            modelObject=arcElt, linkrole=modelLink.role, xlinkType=xlinkType)
                    # values of actuate (not needed for validating parsers)
                    xlinkActuate = arcElt.get(u"{http://www.w3.org/1999/xlink}actuate")
                    if xlinkActuate not in xlinkActuateValues: # ("", "onLoad", "onRequest", "other", "none"):
                        self.modelXbrl.error(u"xlink:actuate",
                            _(u"Actuate %(xlinkActuate)s invalid in extended link %(linkrole)s"),
                            modelObject=arcElt, linkrole=modelLink.role, xlinkActuate=xlinkActuate)
                    # values of show (not needed for validating parsers)
                    xlinkShow = arcElt.get(u"{http://www.w3.org/1999/xlink}show")
                    if xlinkShow not in xlinkShowValues: # ("", "new", "replace", "embed", "other", "none"):
                        self.modelXbrl.error(u"xlink:show",
                            _(u"Show %(xlinkShow)s invalid in extended link %(linkrole)s"),
                            modelObject=arcElt, linkrole=modelLink.role, xlinkShow=xlinkShow)
            # check from, to of arcs have a resource or loc
            for fromTo, arcElt in fromToArcs.items():
                fromLabel, toLabel = fromTo
                for name, value, sect in ((u"from", fromLabel, u"3.5.3.9.2"),(u"to",toLabel, u"3.5.3.9.3")):
                    if value not in locLabels and value not in resourceLabels:
                        self.modelXbrl.error(u"xbrl.{0}:arcResource".format(sect),
                            _(u"Arc in extended link %(linkrole)s from %(xlinkLabelFrom)s to %(xlinkLabelTo)s attribute '%(attribute)s' has no matching loc or resource label"),
                            modelObject=arcElt, 
                            linkrole=modelLink.role, xlinkLabelFrom=fromLabel, xlinkLabelTo=toLabel, 
                            attribute=name,
                            messageCodes=(u"xbrl.3.5.3.9.2:arcResource", u"xbrl.3.5.3.9.3:arcResource"))
                if arcElt.localName == u"footnoteArc" and arcElt.namespaceURI == XbrlConst.link and \
                   arcElt.get(u"{http://www.w3.org/1999/xlink}arcrole") == XbrlConst.factFootnote:
                    if fromLabel not in locLabels:
                        self.modelXbrl.error(u"xbrl.4.11.1.3.1:factFootnoteArcFrom",
                            _(u"Footnote arc in extended link %(linkrole)s from %(xlinkLabelFrom)s to %(xlinkLabelTo)s \"from\" is not a loc"),
                            modelObject=arcElt, 
                            linkrole=modelLink.role, xlinkLabelFrom=fromLabel, xlinkLabelTo=toLabel)
                    if toLabel not in resourceLabels or resourceLabels[toLabel].qname != XbrlConst.qnLinkFootnote:
                        self.modelXbrl.error(u"xbrl.4.11.1.3.1:factFootnoteArcTo",
                            _(u"Footnote arc in extended link %(linkrole)s from %(xlinkLabelFrom)s to %(xlinkLabelTo)s \"to\" is not a footnote resource"),
                            modelObject=arcElt, 
                            linkrole=modelLink.role, xlinkLabelFrom=fromLabel, xlinkLabelTo=toLabel)
            # check unprohibited label arcs to remote locs
            for resourceArcTo in resourceArcTos:
                resourceArcToLabel, resourceArcUse, arcElt = resourceArcTo
                if resourceArcToLabel in locLabels:
                    toLabel = locLabels[resourceArcToLabel]
                    if resourceArcUse == u"prohibited":
                        self.remoteResourceLocElements.add(toLabel)
                    else:
                        self.modelXbrl.error(u"xbrl.5.2.2.3:labelArcRemoteResource",
                            _(u"Unprohibited labelArc in extended link %(linkrole)s has illegal remote resource loc labeled %(xlinkLabel)s href %(xlinkHref)s"),
                            modelObject=arcElt, 
                            linkrole=modelLink.role, 
                            xlinkLabel=resourceArcToLabel,
                            xlinkHref=toLabel.get(u"{http://www.w3.org/1999/xlink}href"))
                elif resourceArcToLabel in resourceLabels:
                    toResource = resourceLabels[resourceArcToLabel]
                    if resourceArcUse == XbrlConst.elementLabel:
                        if not self.isGenericLabel(toResource):
                            self.modelXbrl.error(u"xbrlle.2.1.1:genericLabelTarget",
                                _(u"Generic label arc in extended link %(linkrole)s to %(xlinkLabel)s must target a generic label"),
                                modelObject=arcElt, 
                                linkrole=modelLink.role, 
                                xlinkLabel=resourceArcToLabel)
                    elif resourceArcUse == XbrlConst.elementReference:
                        if not self.isGenericReference(toResource):
                            self.modelXbrl.error(u"xbrlre.2.1.1:genericReferenceTarget",
                                _(u"Generic reference arc in extended link %(linkrole)s to %(xlinkLabel)s must target a generic reference"),
                                modelObject=arcElt, 
                                linkrole=modelLink.role, 
                                xlinkLabel=resourceArcToLabel)
            resourceArcTos = None # dereference arcs
        
    def checkFacts(self, facts, inTuple=None):  # do in document order
        for f in facts:
            concept = f.concept
            if concept is not None:
                if concept.isNumeric:
                    unit = f.unit
                    if f.unitID is None or unit is None:
                        self.modelXbrl.error(u"xbrl.4.6.2:numericUnit",
                             _(u"Fact %(fact)s context %(contextID)s is numeric and must have a unit"),
                             modelObject=f, fact=f.qname, contextID=f.contextID)
                    else:
                        if concept.isMonetary:
                            measures = unit.measures
                            if not measures or len(measures[0]) != 1 or len(measures[1]) != 0:
                                self.modelXbrl.error(u"xbrl.4.8.2:monetaryFactUnit-notSingleMeasure",
                                    _(u"Fact %(fact)s context %(contextID)s must have a single unit measure which is monetary %(unitID)s"),
                                     modelObject=f, fact=f.qname, contextID=f.contextID, unitID=f.unitID)
                            elif (measures[0][0].namespaceURI != XbrlConst.iso4217 or
                                  not self.isoCurrencyPattern.match(measures[0][0].localName)):
                                self.modelXbrl.error(u"xbrl.4.8.2:monetaryFactUnit-notMonetaryMeasure",
                                    _(u"Fact %(fact)s context %(contextID)s must have a monetary unit measure %(unitID)s"),
                                     modelObject=f, fact=f.qname, contextID=f.contextID, unitID=f.unitID)
                        elif concept.isShares:
                            measures = unit.measures
                            if not measures or len(measures[0]) != 1 or len(measures[1]) != 0:
                                self.modelXbrl.error(u"xbrl.4.8.2:sharesFactUnit-notSingleMeasure",
                                    _(u"Fact %(fact)s context %(contextID)s must have a single xbrli:shares unit %(unitID)s"),
                                    modelObject=f, fact=f.qname, contextID=f.contextID, unitID=f.unitID)
                            elif measures[0][0] != XbrlConst.qnXbrliShares:
                                self.modelXbrl.error(u"xbrl.4.8.2:sharesFactUnit-notSharesMeasure",
                                    _(u"Fact %(fact)s context %(contextID)s must have a xbrli:shares unit %(unitID)s"),
                                    modelObject=f, fact=f.qname, contextID=f.contextID, unitID=f.unitID)
                precision = f.precision
                hasPrecision = precision is not None
                if hasPrecision and precision != u"INF" and not precision.isdigit():
                    self.modelXbrl.error(u"xbrl.4.6.4:precision",
                        _(u"Fact %(fact)s context %(contextID)s precision %(precision)s is invalid"),
                        modelObject=f, fact=f.qname, contextID=f.contextID, precision=precision)
                decimals = f.decimals
                hasDecimals = decimals is not None
                if hasPrecision and not self.precisionPattern.match(precision):
                    self.modelXbrl.error(u"xbrl.4.6.4:precision",
                        _(u"Fact %(fact)s context %(contextID)s precision %(precision)s is invalid"),
                        modelObject=f, fact=f.qname, contextID=f.contextID, precision=precision)
                if hasPrecision and hasDecimals:
                    self.modelXbrl.error(u"xbrl.4.6.3:bothPrecisionAndDecimals",
                        _(u"Fact %(fact)s context %(contextID)s can not have both precision and decimals"),
                        modelObject=f, fact=f.qname, contextID=f.contextID)
                if hasDecimals and not self.decimalsPattern.match(decimals):
                    self.modelXbrl.error(u"xbrl.4.6.5:decimals",
                        _(u"Fact %(fact)s context %(contextID)s decimals %(decimals)s is invalid"),
                        modelObject=f, fact=f.qname, contextID=f.contextID, decimals=decimals)
                if concept.isItem:
                    context = f.context
                    if context is None:
                        self.modelXbrl.error(u"xbrl.4.6.1:itemContextRef",
                            _(u"Item %(fact)s must have a context"),
                            modelObject=f, fact=f.qname)
                    else:
                        periodType = concept.periodType
                        if (periodType == u"instant" and not context.isInstantPeriod) or \
                           (periodType == u"duration" and not (context.isStartEndPeriod or context.isForeverPeriod)):
                            self.modelXbrl.error(u"xbrl.4.7.2:contextPeriodType",
                                _(u"Fact %(fact)s context %(contextID)s has period type %(periodType)s conflict with context"),
                                modelObject=f, fact=f.qname, contextID=f.contextID, periodType=periodType)
                            
                    # check precision and decimals
                    if f.isNil:
                        if hasPrecision or hasDecimals:
                            self.modelXbrl.error(u"xbrl.4.6.3:nilPrecisionDecimals",
                                _(u"Fact %(fact)s context %(contextID)s can not be nil and have either precision or decimals"),
                                modelObject=f, fact=f.qname, contextID=f.contextID)
                    elif concept.isFraction:
                        if hasPrecision or hasDecimals:
                            self.modelXbrl.error(u"xbrl.4.6.3:fractionPrecisionDecimals",
                                _(u"Fact %(fact)s context %(contextID)s is a fraction concept and cannot have either precision or decimals"),
                                modelObject=f, fact=f.qname, contextID=f.contextID)
                            numerator, denominator = f.fractionValue
                            if not (numerator == u"INF" or numerator.isnumeric()):
                                self.modelXbrl.error(u"xbrl.5.1.1:fractionPrecisionDecimals",
                                    _(u"Fact %(fact)s context %(contextID)s is a fraction with invalid numerator %(numerator)s"),
                                    modelObject=f, fact=f.qname, contextID=f.contextID, numerator=numerator)
                            if not denominator.isnumeric() or _INT(denominator) == 0:
                                self.modelXbrl.error(u"xbrl.5.1.1:fractionPrecisionDecimals",
                                    _(u"Fact %(fact)s context %(contextID)s is a fraction with invalid denominator %(denominator)")).format(
                                    modelObject=f, fact=f.qname, contextID=f.contextID, denominator=denominator)
                    else:
                        if self.modelXbrl.modelDocument.type != ModelDocument.Type.INLINEXBRL:
                            for child in f.iterchildren():
                                if isinstance(child,ModelObject):
                                    self.modelXbrl.error(u"xbrl.5.1.1:itemMixedContent",
                                        _(u"Fact %(fact)s context %(contextID)s may not have child elements %(childElementName)s"),
                                        modelObject=f, fact=f.qname, contextID=f.contextID, childElementName=child.prefixedName)
                                    break
                        if concept.isNumeric:
                            if not hasPrecision and not hasDecimals:
                                self.modelXbrl.error(u"xbrl.4.6.3:missingPrecisionDecimals",
                                    _(u"Fact %(fact)s context %(contextID)s is a numeric concept and must have either precision or decimals"),
                                    modelObject=f, fact=f.qname, contextID=f.contextID)
                        else:
                            if hasPrecision or hasDecimals:
                                self.modelXbrl.error(u"xbrl.4.6.3:extraneousPrecisionDecimals",
                                    _(u"Fact %(fact)s context %(contextID)s is a non-numeric concept and must not have precision or decimals"),
                                    modelObject=f, fact=f.qname, contextID=f.contextID)
                        # not a real check
                        #if f.isNumeric and not f.isNil and f.precision :
                        #    try:
                        #        ValidateXbrlCalcs.roundValue(f.value, f.precision, f.decimals)
                        #    except Exception as err:
                        #        self.modelXbrl.error("arelle:info",
                        #            _("Fact %(fact)s value %(value)s context %(contextID)s rounding exception %(error)s"),
                        #            modelObject=f, fact=f.qname, value=f.value, contextID=f.contextID, error = err)
                    if self.validateEnum and concept.isEnumeration and getattr(f,u"xValid", 0) == 4 and not f.isNil:
                        memConcept = self.modelXbrl.qnameConcepts.get(f.xValue)
                        if not ValidateXbrlDimensions.enumerationMemberUsable(self, concept, memConcept):
                            self.modelXbrl.error(u"enumie:InvalidFactValue",
                                _(u"Fact %(fact)s context %(contextID)s enumeration %(value)s is not in the domain of %(concept)s"),
                                modelObject=f, fact=f.qname, contextID=f.contextID, value=f.xValue, concept=f.qname)
                elif concept.isTuple:
                    if f.contextID:
                        self.modelXbrl.error(u"xbrl.4.6.1:tupleContextRef",
                            _(u"Tuple %(fact)s must not have a context"),
                            modelObject=f, fact=f.qname)
                    if hasPrecision or hasDecimals:
                        self.modelXbrl.error(u"xbrl.4.6.3:tuplePrecisionDecimals",
                            _(u"Fact %(fact)s is a tuple and cannot have either precision or decimals"),
                            modelObject=f, fact=f.qname)
                    # custom attributes may be allowed by anyAttribute but not by 2.1
                    for attrQname, attrValue in XbrlUtil.attributes(self.modelXbrl, f):
                        if attrQname.namespaceURI in (XbrlConst.xbrli, XbrlConst.link, XbrlConst.xlink, XbrlConst.xl):
                            self.modelXbrl.error(u"xbrl.4.9:tupleAttribute",
                                _(u"Fact %(fact)s is a tuple and must not have attribute in this namespace %(attribute)s"),
                                modelObject=f, fact=f.qname, attribute=attrQname), 
                else:
                    self.modelXbrl.error(u"xbrl.4.6:notItemOrTuple",
                        _(u"Fact %(fact)s must be an item or tuple"),
                        modelObject=f, fact=f.qname)
                    
            if isinstance(f, ModelInlineFact):
                if not inTuple and f.order is not None: 
                    self.modelXbrl.error(u"ix:tupleOrder",
                        _(u"Fact %(fact)s must not have an order (%(order)s) unless in a tuple"),
                        modelObject=f, fact=f.qname, order=f.order)
                if f.isTuple or f.tupleID:
                    if inTuple is None:
                        inTuple = dict()
                    inTuple[f.qname] = f
                    self.checkIxTupleContent(f, inTuple)
            if f.modelTupleFacts:
                self.checkFacts(f.modelTupleFacts, inTuple=inTuple)
            if isinstance(f, ModelInlineFact) and (f.isTuple or f.tupleID):
                del inTuple[f.qname]
             
            # uncomment if anybody uses this   
            #for pluginXbrlMethod in pluginClassMethods("Validate.XBRL.Fact"):
            #    pluginXbrlMethod(self, f)
                
    def checkFactsDimensions(self, facts): # check fact dimensions in document order
        for f in facts:
            if f.concept.isItem and f.context is not None:
                ValidateXbrlDimensions.checkFact(self, f)
            elif f.modelTupleFacts:
                self.checkFactsDimensions(f.modelTupleFacts)
                
    def checkIxTupleContent(self, tf, parentTuples):
        if tf.isNil:
            if tf.modelTupleFacts:
                self.modelXbrl.error(u"ix:tupleNilContent",
                    _(u"Inline XBRL nil tuple has content"),
                    modelObject=[tf] + tf.modelTupleFacts)
        else:
            if not tf.modelTupleFacts:
                self.modelXbrl.error(u"ix:tupleContent",
                    _(u"Inline XBRL non-nil tuple requires content: ix:fraction, ix:nonFraction, ix:nonNumeric or ix:tuple"),
                    modelObject=tf)
        tfTarget = tf.get(u"target") 
        prevTupleFact = None
        for f in tf.modelTupleFacts:
            if f.qname in parentTuples:
                self.modelXbrl.error(u"ix:tupleRecursion",
                    _(u"Fact %(fact)s is recursively nested in tuple %(tuple)s"),
                    modelObject=(f, parentTuples[f.qname]), fact=f.qname, tuple=tf.qname)
            if f.order is None: 
                self.modelXbrl.error(u"ix:tupleOrder",
                    _(u"Fact %(fact)s missing an order in tuple %(tuple)s"),
                    modelObject=f, fact=f.qname, tuple=tf.qname)
            if f.get(u"target") != tfTarget:
                self.modelXbrl.error(u"ix:tupleItemTarget",
                    _(u"Fact %(fact)s has different target, %(factTarget)s, than tuple %(tuple)s, %(tupleTarget)s"),
                    modelObject=(tf, f), fact=f.qname, tuple=tf.qname, factTarget=f.get(u"target"), tupleTarget=tfTarget)
            if prevTupleFact is None:
                prevTupleFact = f
            elif (prevTupleFact.order == f.order and 
                  XmlUtil.collapseWhitespace(prevTupleFact.textValue) == XmlUtil.collapseWhitespace(f.textValue)):
                self.modelXbrl.error(u"ix:tupleContentDuplicate",
                    _(u"Inline XBRL at order %(order)s has non-matching content %(value)s"),
                    modelObject=(prevTupleFact, f), order=f.order, value=prevTupleFact.textValue.strip())
                
    def checkContexts(self, contexts):
        for cntx in contexts:
            if cntx.isStartEndPeriod:
                try: # if no datetime value would have been a schema error at loading time
                    if (cntx.endDatetime is not None and cntx.startDatetime is not None and
                        cntx.endDatetime <= cntx.startDatetime):
                        self.modelXbrl.error(u"xbrl.4.7.2:periodStartBeforeEnd",
                            _(u"Context %(contextID)s must have startDate less than endDate"),
                            modelObject=cntx, contextID=cntx.id)
                except (TypeError, ValueError), err:
                    self.modelXbrl.error(u"xbrl.4.7.2:contextDateError",
                        _(u"Context %(contextID) startDate or endDate: %(error)s"),
                        modelObject=cntx, contextID=cntx.id, error=err)
            elif cntx.isInstantPeriod:
                try:
                    cntx.instantDatetime #parse field
                except ValueError, err:
                    self.modelXbrl.error(u"xbrl.4.7.2:contextDateError",
                        _(u"Context %(contextID)s instant date: %(error)s"),
                        modelObject=cntx, contextID=cntx.id, error=err)
            self.segmentScenario(cntx.segment, cntx.id, u"segment", u"4.7.3.2")
            self.segmentScenario(cntx.scenario, cntx.id, u"scenario", u"4.7.4")
                
    def checkContextsDimensions(self, contexts):
        for cntx in contexts:
            ValidateXbrlDimensions.checkContext(self,cntx)
        
    def checkUnits(self, units):
        for unit in units:
            mulDivMeasures = unit.measures
            if mulDivMeasures:
                for measures in mulDivMeasures:
                    for measure in measures:
                        if measure.namespaceURI == XbrlConst.xbrli and not \
                            measure in (XbrlConst.qnXbrliPure, XbrlConst.qnXbrliShares):
                                self.modelXbrl.error(u"xbrl.4.8.2:measureElement",
                                    _(u"Unit %(unitID)s illegal measure: %(measure)s"),
                                    modelObject=unit, unitID=unit.id, measure=measure)
                for numeratorMeasure in mulDivMeasures[0]:
                    if numeratorMeasure in mulDivMeasures[1]:
                        self.modelXbrl.error(u"xbrl.4.8.4:measureBothNumDenom",
                            _(u"Unit %(unitID)s numerator measure: %(measure)s also appears as denominator measure"),
                            modelObject=unit, unitID=unit.id, measure=numeratorMeasure)        
    
        
    def fwdCycle(self, relsSet, rels, noUndirected, fromConcepts, cycleType=u"directed", revCycleRel=None):
        for rel in rels:
            if revCycleRel is not None and rel.isIdenticalTo(revCycleRel):
                continue # don't double back on self in undirected testing
            relTo = rel.toModelObject
            if relTo in fromConcepts: #forms a directed cycle
                return [cycleType,rel]
            fromConcepts.add(relTo)
            nextRels = relsSet.fromModelObject(relTo)
            foundCycle = self.fwdCycle(relsSet, nextRels, noUndirected, fromConcepts)
            if foundCycle is not None:
                foundCycle.append(rel)
                return foundCycle
            fromConcepts.discard(relTo)
            # look for back path in any of the ELRs visited (pass None as ELR)
            if noUndirected:
                foundCycle = self.revCycle(relsSet, relTo, rel, fromConcepts)
                if foundCycle is not None:
                    foundCycle.append(rel)
                    return foundCycle
        return None
    
    def revCycle(self, relsSet, toConcept, turnbackRel, fromConcepts):
        for rel in relsSet.toModelObject(toConcept):
            if not rel.isIdenticalTo(turnbackRel):
                relFrom = rel.fromModelObject
                if relFrom in fromConcepts:
                    return [u"undirected",rel]
                fromConcepts.add(relFrom)
                foundCycle = self.revCycle(relsSet, relFrom, turnbackRel, fromConcepts)
                if foundCycle is not None:
                    foundCycle.append(rel)
                    return foundCycle
                fwdRels = relsSet.fromModelObject(relFrom)
                foundCycle = self.fwdCycle(relsSet, fwdRels, True, fromConcepts, cycleType=u"undirected", revCycleRel=rel)
                if foundCycle is not None:
                    foundCycle.append(rel)
                    return foundCycle
                fromConcepts.discard(relFrom)
        return None
    
    def segmentScenario(self, element, contextId, name, sect, topLevel=True):
        if topLevel:
            if element is None:
                return  # nothing to check
        else:
            if element.namespaceURI == XbrlConst.xbrli:
                self.modelXbrl.error(u"xbrl.{0}:{1}XbrliElement".format(sect,name),
                    _(u"Context %(contextID)s %(contextElement)s cannot have xbrli element %(elementName)s"),
                    modelObject=element, contextID=contextId, contextElement=name, elementName=element.prefixedName,
                    messageCodes=(u"xbrl.4.7.3.2:segmentXbrliElement", u"xbrl.4.7.4:scenarioXbrliElement"))
            else:
                concept = self.modelXbrl.qnameConcepts.get(element.qname)
                if concept is not None and (concept.isItem or concept.isTuple):
                    self.modelXbrl.error(u"xbrl.{0}:{1}ItemOrTuple".format(sect,name),
                        _(u"Context %(contextID)s %(contextElement)s cannot have item or tuple element %(elementName)s"),
                        modelObject=element, contextID=contextId, contextElement=name, elementName=element.prefixedName,
                        messageCodes=(u"xbrl.4.7.3.2:segmentItemOrTuple", u"xbrl.4.7.4:scenarioItemOrTuple"))
        hasChild = False
        for child in element.iterchildren():
            if isinstance(child,ModelObject):
                self.segmentScenario(child, contextId, name, sect, topLevel=False)
                hasChild = True
        if topLevel and not hasChild:
            self.modelXbrl.error(u"xbrl.{0}:{1}Empty".format(sect,name),
                _(u"Context %(contextID)s %(contextElement)s cannot be empty"),
                modelObject=element, contextID=contextId, contextElement=name,
                messageCodes=(u"xbrl.4.7.3.2:segmentEmpty", u"xbrl.4.7.4:scenarioEmpty"))
        
    def isGenericObject(self, elt, genQname):
        return self.modelXbrl.isInSubstitutionGroup(elt.qname,genQname)
    
    def isGenericLink(self, elt):
        return self.isGenericObject(elt, XbrlConst.qnGenLink)
    
    def isGenericArc(self, elt):
        return self.isGenericObject(elt, XbrlConst.qnGenArc)
    
    def isGenericResource(self, elt):
        return self.isGenericObject(elt.getparent(), XbrlConst.qnGenLink)

    def isGenericLabel(self, elt):
        return self.isGenericObject(elt, XbrlConst.qnGenLabel)

    def isGenericReference(self, elt):
        return self.isGenericObject(elt, XbrlConst.qnGenReference)

    def executeCallTest(self, modelXbrl, name, callTuple, testTuple):
        self.modelXbrl = modelXbrl
        ValidateFormula.executeCallTest(self, name, callTuple, testTuple)
                
