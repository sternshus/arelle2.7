u"""
:mod:`arelle.ModelInstanceObjuect`
~~~~~~~~~~~~~~~~~~~

.. module:: arelle.ModelInstanceObject
   :copyright: Copyright 2010-2012 Mark V Systems Limited, All rights reserved.
   :license: Apache-2.
   :synopsis: This module contains Instance-specialized ModelObject classes: ModelFact (xbrli:item 
   and xbrli:tuple elements of an instance document), ModelInlineFact specializes ModelFact when 
   in an inline XBRL document, ModelContext (xblrli:context element), ModelDimensionValue 
   (xbrldi:explicitMember and xbrli:typedMember elements), and ModelUnit (xbrli:unit elements). 

    Model facts represent XBRL instance facts (that are elements in the instance document).  
    Model inline facts represent facts in a source xhtml document, but may accumulate text 
    across multiple mixed-content elements in the instance document, according to the rendering 
    transform in effect.  All inline facts are lxml proxy objects for the inline fact and have a 
    cached value representing the transformed value content.  PSVI values for the inline fact's 
    value and attributes are on the model inline fact object (not necessarily the element that 
    held the mixed-content text).

    Model context objects are the lxml proxy object of the context XML element, but cache and 
    interface context semantics that may either be internal to the context, or inferred from 
    the DTS (such as default dimension values).   PSVI values for elements internal to the context, 
    including segment and scenario elements, are on the individual model object lxml custom proxy 
    elements.  For fast comparison of dimensions and segment/scenario, hash values are retained 
    for each comparable item.

    Model dimension objects not only represent proxy objects for the XML elements, but have resolved 
    model DTS concepts of the dimension and member, and access to the typed member contents.

    Model unit objects represent algebraically usable set objects for the numerator and denominator 
    measure sets.
"""
from collections import defaultdict
from lxml import etree
from arelle import XmlUtil, XbrlConst, XbrlUtil, UrlUtil, Locale, ModelValue, XmlValidate
from arelle.ValidateXbrlCalcs import inferredPrecision, inferredDecimals, roundValue
from arelle.PrototypeInstanceObject import DimValuePrototype
from math import isnan
from arelle.ModelObject import ModelObject
from decimal import Decimal, InvalidOperation
from hashlib import md5
from arelle.HashUtil import md5hash, Md5Sum
Aspect = None
utrEntries = None
utrSymbol = None
POSINF = float(u"inf")
NEGINF = float(u"-inf")

class NewFactItemOptions():
    u"""
    .. class:: NewFactItemOptions(savedOptions=None, xbrlInstance=None)
    
    NewFactItemOptions persists contextual parameters for interactive creation of new facts,
    such as when entering into empty table linkbase rendering pane cells.
    
    If savedOptions is provided (from configuration saved json file), then persisted last used
    values of item contextual options are used.  If no saved options, then the first fact in
    an existing instance (xbrlInstance) is used to glean prototype contextual parameters.
    
    Note that all attributes of this class must be compatible with json conversion, e.g., datetime
    must be persisted in string, not datetime object, form.
    
    Properties of this class (all str):
    
    - entityIdentScheme
    - entityIdentValue
    - startDate
    - endDate
    - monetaryUnit (str prefix:localName, e.g, iso4217:JPY)
    - monetaryDecimals (decimals attribute for numeric monetary facts)
    - nonMonetaryDecimals (decimals attribute for numeric non-monetary facts, e.g., shares)
    
    :param savedOptions: prior persisted dict of this class's attributes
    :param xbrlInstance: an open instance document from which to glean prototpye contextual parameters.
    """
    def __init__(self, savedOptions=None, xbrlInstance=None):
        self.entityIdentScheme = u""
        self.entityIdentValue = u""
        self.startDate = u""  # use string  values so structure can be json-saved
        self.endDate = u""
        self.monetaryUnit = u""
        self.monetaryDecimals = u""
        self.nonMonetaryDecimals = u""
        if savedOptions is not None:
            self.__dict__.update(savedOptions)
        elif xbrlInstance is not None:
            for fact in xbrlInstance.facts:
                cntx = fact.context
                unit = fact.unit
                if fact.isItem and cntx is not None:
                    if not self.entityIdentScheme:
                        self.entityIdentScheme, self.entityIdentValue = cntx.entityIdentifier
                    if not self.startDate and cntx.isStartEndPeriod:
                        self.startDate = XmlUtil.dateunionValue(cntx.startDatetime)
                    if not self.startDate and (cntx.isStartEndPeriod or cntx.isInstantPeriod):
                        self.endDate = XmlUtil.dateunionValue(cntx.endDatetime, subtractOneDay=True)
                    if fact.isNumeric and unit is not None:
                        if fact.concept.isMonetary:
                            if not self.monetaryUnit and unit.measures[0] and unit.measures[0][0].namespaceURI == XbrlConst.iso4217:
                                self.monetaryUnit = unit.measures[0][0].localName
                            if not self.monetaryDecimals:
                                self.monetaryDecimals = fact.decimals
                        elif not self.nonMonetaryDecimals:
                            self.nonMonetaryDecimals = fact.decimals
                if self.entityIdentScheme and self.startDate and self.monetaryUnit and self.monetaryDecimals and self.nonMonetaryDecimals:
                    break 
                
    @property
    def startDateDate(self):
        u"""(datetime) -- date-typed date value of startDate (which is persisted in str form)"""
        return XmlUtil.datetimeValue(self.startDate)

    @property
    def endDateDate(self):  # return a date-typed date
        u"""(datetime) -- date-typed date value of endDate (which is persisted in str form)"""
        return XmlUtil.datetimeValue(self.endDate, addOneDay=True)
                
    
class ModelFact(ModelObject):
    u"""
    .. class:: ModelFact(modelDocument)
    
    Model fact (both instance document facts and inline XBRL facts)
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument

        .. attribute:: modelTupleFacts
        
        ([ModelFact]) - List of child facts in source document order
    """
    def init(self, modelDocument):
        super(ModelFact, self).init(modelDocument)
        self.modelTupleFacts = []
        
    @property
    def concept(self):
        u"""(ModelConcept) -- concept of the fact."""
        return self.elementDeclaration()  # logical (fact) declaration in own modelXbrl, not physical element (if inline)
        
    @property
    def contextID(self):
        u"""(str) -- contextRef attribute"""
        return self.get(u"contextRef")

    @property
    def context(self):
        u"""(ModelContext) -- context of the fact if any else None (e.g., tuple)"""
        try:
            return self._context
        except AttributeError:
            if not self.modelXbrl.contexts: return None # don't attempt before contexts are loaded
            self._context = self.modelXbrl.contexts.get(self.contextID)
            return self._context
    
    @property
    def unit(self):
        u"""(ModelUnit) -- unit of the fact if any else None (e.g., non-numeric or tuple)"""
        return self.modelXbrl.units.get(self.unitID)
    
    @property
    def unitID(self):
        u"""(str) -- unitRef attribute"""
        return self.get(u"unitRef")
    
    @property
    def utrEntries(self):
        u"""(set(UtrEntry)) -- set of UtrEntry objects that match this fact and unit"""
        if self.unit is not None and self.concept is not None:
            return self.unit.utrEntries(self.concept.type)
        return None
    
    def unitSymbol(self):
        u"""(str) -- utr symbol for this fact and unit"""
        if self.unit is not None and self.concept is not None:
            return self.unit.utrSymbol(self.concept.type)
        return u""

    @property
    def conceptContextUnitLangHash(self):
        u"""(int) -- Hash value of fact's concept QName, dimensions-aware 
        context hash, unit hash, and xml:lang hash, useful for fast comparison of facts for EFM 6.5.12"""
        try:
            return self._conceptContextUnitLangHash
        except AttributeError:
            context = self.context
            unit = self.unit
            self._conceptContextUnitLangHash = hash( 
                (self.qname,
                 context.contextDimAwareHash if context is not None else None,
                 unit.hash if unit is not None else None,
                 self.xmlLang) )
            return self._conceptContextUnitLangHash

    @property
    def isItem(self):
        u"""(bool) -- concept.isItem"""
        try:
            return self._isItem
        except AttributeError:
            concept = self.concept
            self._isItem = (concept is not None) and concept.isItem
            return self._isItem

    @property
    def isTuple(self):
        u"""(bool) -- concept.isTuple"""
        try:
            return self._isTuple
        except AttributeError:
            concept = self.concept
            self._isTuple = (concept is not None) and concept.isTuple
            return self._isTuple

    @property
    def isNumeric(self):
        u"""(bool) -- concept.isNumeric (note this is false for fractions)"""
        try:
            return self._isNumeric
        except AttributeError:
            concept = self.concept
            self._isNumeric = (concept is not None) and concept.isNumeric
            return self._isNumeric

    @property
    def isFraction(self):
        u"""(bool) -- concept.isFraction"""
        try:
            return self._isFraction
        except AttributeError:
            concept = self.concept
            self._isFraction = (concept is not None) and concept.isFraction
            return self._isFraction
        
    @property
    def parentElement(self):
        u"""(ModelObject) -- parent element (tuple or xbrli:xbrl)"""
        return self.getparent()

    @property
    def ancestorQnames(self):
        u"""(set) -- Set of QNames of ancestor elements (tuple and xbrli:xbrl)"""
        try:
            return self._ancestorQnames
        except AttributeError:
            self._ancestorQnames = set( ModelValue.qname(ancestor) for ancestor in self.iterancestors() )
            return self._ancestorQnames

    @property
    def decimals(self):
        u"""(str) -- Value of decimals attribute, or fixed or default value for decimals on concept type declaration"""
        try:
            return self._decimals
        except AttributeError:
            decimals = self.get(u"decimals")
            if decimals:
                self._decimals = decimals
            else:   #check for fixed decimals on type
                concept = self.concept
                if concept is not None:
                    type = concept.type
                    self._decimals = type.fixedOrDefaultAttrValue(u"decimals") if type is not None else None
                else:
                    self._decimals = None    
            return  self._decimals

    @decimals.setter
    def decimals(self, value):
        self._decimals = value
        self.set(u"decimals", value)
        
    @property
    def precision(self):
        u"""(str) -- Value of precision attribute, or fixed or default value for precision on concept type declaration"""
        try:
            return self._precision
        except AttributeError:
            precision = self.get(u"precision")
            if precision:
                self._precision = precision
            else:   #check for fixed decimals on type
                concept = self.concept
                if concept is not None:
                    type = self.concept.type
                    self._precision = type.fixedOrDefaultAttrValue(u"precision") if type is not None else None
                else:
                    self._precision = None    
            return  self._precision

    @property
    def xmlLang(self):
        u"""(str) -- xml:lang attribute, if none and non-numeric, disclosure-system specified default lang"""
        lang = XmlUtil.ancestorOrSelfAttr(self, u"{http://www.w3.org/XML/1998/namespace}lang")
        if lang is None and self.modelXbrl.modelManager.validateDisclosureSystem:
            concept = self.concept
            if concept is not None and not concept.isNumeric:
                lang = self.modelXbrl.modelManager.disclosureSystem.defaultXmlLang
        return lang
    
    @property
    def xsiNil(self):
        u"""(str) -- value of xsi:nil or 'false' if absent"""
        return self.get(u"{http://www.w3.org/2001/XMLSchema-instance}nil", u"false")
    
    @property
    def isNil(self):
        u"""(bool) -- True if xsi:nil is 'true'"""
        return self.xsiNil in (u"true",u"1")
    
    @isNil.setter
    def isNil(self, value):
        u""":param value: if true, set xsi:nil to 'true', if false, remove xsi:nil attribute """
        if value:
            XmlUtil.setXmlns(self.modelDocument, u"xsi", u"http://www.w3.org/2001/XMLSchema-instance")
            self.set(u"{http://www.w3.org/2001/XMLSchema-instance}nil", u"true")
            self.attrib.pop(u"decimals", u"0")  # can't leave decimals or precision
            self.attrib.pop(u"precision", u"0")
            del self._decimals
            del self._precision
        else: # also remove decimals and precision, if they were there
            self.attrib.pop(u"{http://www.w3.org/2001/XMLSchema-instance}nil", u"false")
    
    @property
    def value(self):
        u"""(str) -- Text value of fact or default or fixed if any, otherwise None"""
        v = self.textValue
        if not v and self.concept is not None:
            if self.concept.default is not None:
                v = self.concept.default
            elif self.concept.fixed is not None:
                v = self.concept.fixed
        return v
    
    @property
    def fractionValue(self):
        u"""( (str,str) ) -- (text value of numerator, text value of denominator)"""
        return (XmlUtil.text(XmlUtil.child(self, None, u"numerator")),
                XmlUtil.text(XmlUtil.child(self, None, u"denominator")))
    
    @property
    def effectiveValue(self):
        u"""(str) -- Effective value for views, (nil) if isNil, None if no value, 
        locale-formatted string of decimal value (if decimals specified) , otherwise string value"""
        concept = self.concept
        if concept is None or concept.isTuple:
            return None
        if self.isNil:
            return u"(nil)"
        try:
            if concept.isNumeric:
                val = self.value
                try:
                    # num = float(val)
                    dec = self.decimals
                    num = roundValue(val, self.precision, dec) # round using reported decimals
                    if dec is None or dec == u"INF":  # show using decimals or reported format
                        dec = len(val.partition(u".")[2])
                    else: # max decimals at 28
                        dec = max( min(int(dec), 28), -28) # 2.7 wants short int, 3.2 takes regular int, don't use _INT here
                    return Locale.format(self.modelXbrl.locale, u"%.*f", (dec, num), True)
                except ValueError: 
                    return u"(error)"
            return self.value
        except Exception, ex:
            return unicode(ex)  # could be transform value of inline fact

    @property
    def vEqValue(self):
        u"""(float or str) -- v-equal value, float if numeric, otherwise string value"""
        if self.concept.isNumeric:
            return float(self.value)
        return self.value
    
    def isVEqualTo(self, other, deemP0Equal=False, deemP0inf=False):
        u"""(bool) -- v-equality of two facts
        
        Note that facts may be in different instances
        """
        if self.isTuple or other.isTuple:
            return False
        if self.isNil:
            return other.isNil
        if other.isNil:
            return False
        if not self.context.isEqualTo(other.context):
            return False
        if self.concept.isNumeric:
            if other.concept.isNumeric:
                if not self.unit.isEqualTo(other.unit):
                    return False
                if self.modelXbrl.modelManager.validateInferDecimals:
                    d = min((inferredDecimals(self), inferredDecimals(other))); p = None
                    if isnan(d):
                        if deemP0Equal:
                            return True
                        elif deemP0inf: # for test cases deem P0 as INF comparison
                            return self.xValue == other.xValue
                else:
                    d = None; p = min((inferredPrecision(self), inferredPrecision(other)))
                    if p == 0:
                        if deemP0Equal:
                            return True
                        elif deemP0inf: # for test cases deem P0 as INF comparison
                            return self.xValue == other.xValue
                return roundValue(self.value,precision=p,decimals=d) == roundValue(other.value,precision=p,decimals=d)
            else:
                return False
        selfValue = self.value
        otherValue = other.value
        if isinstance(selfValue,unicode) and isinstance(otherValue,unicode):
            return selfValue.strip() == otherValue.strip()
        else:
            return selfValue == otherValue
        
    def isDuplicateOf(self, other, topLevel=True, deemP0Equal=False, unmatchedFactsStack=None): 
        u"""(bool) -- fact is duplicate of other fact
        
        Note that facts may be in different instances
        
        :param topLevel:  fact parent is xbrli:instance, otherwise nested in a tuple
        :type topLevel: bool
        :param deemPOEqual: True to deem any precision=0 facts equal ignoring value
        :type deepPOEqual: bool
        """
        if unmatchedFactsStack is not None: 
            if topLevel: del unmatchedFactsStack[0:]
            entryDepth = len(unmatchedFactsStack)
            unmatchedFactsStack.append(self)
        if self.isItem:
            if (self == other or
                self.qname != other.qname or
                self.parentElement.qname != other.parentElement.qname):
                return False    # can't be identical
            # parent test can only be done if in same instauce
            if self.modelXbrl == other.modelXbrl and self.parentElement != other.parentElement:
                return False
            if not (self.context.isEqualTo(other.context,dimensionalAspectModel=False) and
                    (not self.isNumeric or self.unit.isEqualTo(other.unit))):
                return False
        elif self.isTuple:
            if (self == other or
                self.qname != other.qname or
                (topLevel and self.parentElement.qname != other.parentElement.qname)):
                return False    # can't be identical
            if len(self.modelTupleFacts) != len(other.modelTupleFacts):
                return False
            for child1 in self.modelTupleFacts:
                if child1.isItem:
                    if not any(child1.isVEqualTo(child2, deemP0Equal) for child2 in other.modelTupleFacts if child1.qname == child2.qname):
                        return False
                elif child1.isTuple:
                    if not any(child1.isDuplicateOf( child2, False, deemP0Equal, unmatchedFactsStack) 
                               for child2 in other.modelTupleFacts):
                        return False
        else:
            return False
        if unmatchedFactsStack is not None: 
            del unmatchedFactsStack[entryDepth:]
        return True
    
    @property
    def md5sum(self):  # note this must work in --skipDTS and streaming modes
        _toHash = [self.qname]
        if self.context is not None: # not a tuple and has a valid unit
            # don't use self.xmlLang because its value may depend on disclosure system (assumption)
            _lang = XmlUtil.ancestorOrSelfAttr(self, u"{http://www.w3.org/XML/1998/namespace}lang")
            if _lang:
                _toHash.append(XbrlConst.qnXmlLang)
                _toHash.append(_lang)
            if self.isNil:
                _toHash.append(XbrlConst.qnXsiNil)
                _toHash.append(u"true")
            elif self.value:
                _toHash.append(self.value)
            _toHash.append(self.context.md5sum)
            if self.unit is not None:
                _toHash.append(self.unit.md5sum)
        return md5hash(_toHash)
    
    @property
    def propertyView(self):
        try:
            concept = self.concept
            lbl = ((u"label", concept.label(lang=self.modelXbrl.modelManager.defaultLang)),)
        except (KeyError, AttributeError):
            lbl = ()
        if self.isNumeric and self.unit is not None:
            unitValue = self.unitID
            unitSymbol = self.unitSymbol()
            if unitSymbol: 
                unitValue += u" (" + unitSymbol + u")"
        return lbl + (
               ((u"namespace", self.qname.namespaceURI),
                (u"name", self.qname.localName),
                (u"QName", self.qname)) + 
               ((((u"contextRef", self.contextID, self.context.propertyView) if self.context is not None else ()),
                 ((u"unitRef", unitValue, self.unit.propertyView) if self.isNumeric and self.unit is not None else ()),
                 (u"decimals", self.decimals),
                 (u"precision", self.precision),
                 (u"xsi:nil", self.xsiNil),
                 (u"value", self.effectiveValue.strip()))
                 if self.isItem else () ))
        
    def __repr__(self):
        return (u"modelFact[{0}, qname: {1}, contextRef: {2}, unitRef: {3}, value: {4}, {5}, line {6}]"
                .format(self.objectIndex, self.qname, self.get(u"contextRef"), self.get(u"unitRef"),
                        self.effectiveValue.strip() if self.isItem else u'(tuple)',
                        self.modelDocument.basename, self.sourceline))
    
    @property
    def viewConcept(self):
        return self.concept
    
class ModelInlineValueObject(object):
    def init(self, modelDocument):
        super(ModelInlineValueObject, self).init(modelDocument)
        
    @property
    def sign(self):
        u"""(str) -- sign attribute of inline element"""
        return self.get(u"sign")
    
    @property
    def format(self):
        u"""(QName) -- format attribute of inline element"""
        return self.prefixedNameQname(self.get(u"format"))

    @property
    def scale(self):
        u"""(str) -- scale attribute of inline element"""
        return self.get(u"scale")
    
    
    @property
    def value(self):
        u"""(str) -- Overrides and corresponds to value property of ModelFact, 
        for relevant inner text nodes aggregated and transformed as needed."""
        try:
            return self._ixValue
        except AttributeError:
            v = XmlUtil.innerText(self, 
                                  ixExclude=True, 
                                  ixEscape=(self.get(u"escape") in (u"true",u"1")), 
                                  ixContinuation=(self.elementQname == XbrlConst.qnIXbrl11NonNumeric),
                                  strip=True) # transforms are whitespace-collapse
            f = self.format
            if f is not None:
                if (f.namespaceURI in FunctionIxt.ixtNamespaceURIs and
                    f.localName in FunctionIxt.ixtFunctions):
                    try:
                        v = FunctionIxt.ixtFunctions[f.localName](v)
                    except Exception, err:
                        self._ixValue = ModelValue.INVALIDixVALUE
                        raise err
            if self.localName == u"nonNumeric" or self.localName == u"tuple":
                self._ixValue = v
            else:  # determine string value of transformed value
                negate = -1 if self.sign else 1
                try:
                    # concept may be unknown or invalid but transformation would still occur
                    # use decimal so all number forms work properly
                    num = Decimal(v)
                except (ValueError, InvalidOperation):
                    self._ixValue = ModelValue.INVALIDixVALUE
                    raise ValueError(u"Invalid value for {} number: {}".format(self.localName, v))
                try:
                    scale = self.scale
                    if scale is not None:
                        num *= 10 ** Decimal(scale)
                    self._ixValue = u"{}".format(num * negate)
                except (ValueError, InvalidOperation):
                    self._ixValue = ModelValue.INVALIDixVALUE
                    raise ValueError(u"Invalid value for {} scale {} for number {}".format(self.localName, scale, v))
            return self._ixValue

    @property
    def textValue(self):
        u"""(str) -- override xml-level textValue for transformed value text()
            will raise any value errors if transforming string or numeric has an error
        """
        return self.value
    
    @property
    def stringValue(self):
        u"""(str) -- override xml-level stringValue for transformed value descendants text
            will raise any value errors if transforming string or numeric has an error
        """
        return self.value
    
    
class ModelInlineFact(ModelInlineValueObject, ModelFact):
    u"""
    .. class:: ModelInlineFact(modelDocument)
    
    Model inline fact (inline XBRL facts)
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelInlineFact, self).init(modelDocument)
        
    @property
    def qname(self):
        u"""(QName) -- QName of concept from the name attribute, overrides and corresponds to the qname property of a ModelFact (inherited from ModelObject)"""
        try:
            return self._factQname
        except AttributeError:
            self._factQname = self.prefixedNameQname(self.get(u"name")) if self.get(u"name") else None
            return self._factQname

    @property
    def tupleID(self):
        u"""(str) -- tupleId attribute of inline element"""
        try:
            return self._tupleId
        except AttributeError:
            self._tupleId = self.get(u"tupleID")
            return self._tupleId
    
    @property
    def tupleRef(self):
        u"""(str) -- tupleRef attribute of inline element"""
        try:
            return self._tupleRef
        except AttributeError:
            self._tupleRef = self.get(u"tupleRef")
            return self._tupleRef

    @property
    def order(self):
        u"""(float) -- order attribute of inline element or None if absent or float conversion error"""
        try:
            return self._order
        except AttributeError:
            try:
                orderAttr = self.get(u"order")
                self._order = Decimal(orderAttr)
            except (ValueError, TypeError, InvalidOperation):
                self._order = None
            return self._order

    @property
    def fractionValue(self):
        u"""( (str,str) ) -- (text value of numerator, text value of denominator)"""
        return (XmlUtil.text(XmlUtil.descendant(self, self.namespaceURI, u"numerator")),
                XmlUtil.text(XmlUtil.descendant(self, self.namespaceURI, u"denominator")))
    
    @property
    def footnoteRefs(self):
        u"""([str]) -- list of footnoteRefs attribute contents of inline element"""
        return self.get(u"footnoteRefs", u"").split()

    def __iter__(self):
        if self.localName == u"fraction":
            n = XmlUtil.descendant(self, self.namespaceURI, u"numerator")
            d = XmlUtil.descendant(self, self.namespaceURI, u"denominator")
            if n is not None and d is not None:
                yield n
                yield d
        for tupleFact in self.modelTupleFacts:
            yield tupleFact
     
    @property
    def propertyView(self):
        if self.localName == u"nonFraction" or self.localName == u"fraction":
            numProperties = ((u"format", self.format),
                (u"scale", self.scale),
                (u"html value", XmlUtil.innerText(self)))
        else:
            numProperties = ()
        return ((u"file", self.modelDocument.basename),
                (u"line", self.sourceline)) + \
               super(ModelInlineFact,self).propertyView + \
               numProperties
        
    def __repr__(self):
        return (u"modelInlineFact[{0}]{1})".format(self.objectId(),self.propertyView))
    
class ModelInlineFraction(ModelInlineFact):
    def init(self, modelDocument):
        super(ModelInlineFraction, self).init(modelDocument)
        
    @property
    def textValue(self):
        return u""  # no text value for fraction

class ModelInlineFractionTerm(ModelInlineValueObject, ModelObject):
    def init(self, modelDocument):
        super(ModelInlineFractionTerm, self).init(modelDocument)
        
    @property
    def qname(self):
        if self.localName == u"numerator":
            return XbrlConst.qnXbrliNumerator
        elif self.localName == u"denomiantor":
            return XbrlConst.qnXbrliDenominator
        return self.elementQname
    
    @property
    def concept(self):
        return self.modelXbrl.qnameConcepts.get(self.qname) # for fraction term type determination

    def __iter__(self):
        if False: yield None # generator with nothing to generate
    
               
class ModelContext(ModelObject):
    u"""
    .. class:: ModelContext(modelDocument)
    
    Model context
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument

        .. attribute:: segDimValues
        
        (dict) - Dict by dimension ModelConcept of segment dimension ModelDimensionValues

        .. attribute:: scenDimValues
        
        (dict) - Dict by dimension ModelConcept of scenario dimension ModelDimensionValues

        .. attribute:: qnameDims
        
        (dict) - Dict by dimension concept QName of ModelDimensionValues (independent of whether segment or scenario)

        .. attribute:: errorDimValues
        
        (list) - List of ModelDimensionValues whose dimension concept could not be determined or which were duplicates

        .. attribute:: segNonDimValues
        
        (list) - List of segment child non-dimension ModelObjects

        .. attribute:: scenNonDimValues
        
        (list) - List of scenario child non-dimension ModelObjects
    """
    def init(self, modelDocument):
        super(ModelContext, self).init(modelDocument)
        self.segDimValues = {}
        self.scenDimValues = {}
        self.qnameDims = {}
        self.errorDimValues = []
        self.segNonDimValues = []
        self.scenNonDimValues = []
        self._isEqualTo = {}
        
    @property
    def isStartEndPeriod(self):
        u"""(bool) -- True for startDate/endDate period"""
        try:
            return self._isStartEndPeriod
        except AttributeError:
            self._isStartEndPeriod = XmlUtil.hasChild(self.period, XbrlConst.xbrli, (u"startDate",u"endDate"))
            return self._isStartEndPeriod
                                
    @property
    def isInstantPeriod(self):
        u"""(bool) -- True for instant period"""
        try:
            return self._isInstantPeriod
        except AttributeError:
            self._isInstantPeriod = XmlUtil.hasChild(self.period, XbrlConst.xbrli, u"instant")
            return self._isInstantPeriod

    @property
    def isForeverPeriod(self):
        u"""(bool) -- True for forever period"""
        try:
            return self._isForeverPeriod
        except AttributeError:
            self._isForeverPeriod = XmlUtil.hasChild(self.period, XbrlConst.xbrli, u"forever")
            return self._isForeverPeriod

    @property
    def startDatetime(self):
        u"""(datetime) -- startDate attribute"""
        try:
            return self._startDatetime
        except AttributeError:
            self._startDatetime = XmlUtil.datetimeValue(XmlUtil.child(self.period, XbrlConst.xbrli, u"startDate"))
            return self._startDatetime

    @property
    def endDatetime(self):
        u"""(datetime) -- endDate or instant attribute, with adjustment to end-of-day midnight as needed"""
        try:
            return self._endDatetime
        except AttributeError:
            self._endDatetime = XmlUtil.datetimeValue(XmlUtil.child(self.period, XbrlConst.xbrli, (u"endDate",u"instant")), addOneDay=True)
            return self._endDatetime
        
    @property
    def instantDatetime(self):
        u"""(datetime) -- instant attribute, with adjustment to end-of-day midnight as needed"""
        try:
            return self._instantDatetime
        except AttributeError:
            self._instantDatetime = XmlUtil.datetimeValue(XmlUtil.child(self.period, XbrlConst.xbrli, u"instant"), addOneDay=True)
            return self._instantDatetime
    
    @property
    def period(self):
        u"""(ModelObject) -- period element"""
        try:
            return self._period
        except AttributeError:
            self._period = XmlUtil.child(self, XbrlConst.xbrli, u"period")
            return self._period

    @property
    def periodHash(self):
        u"""(int) -- hash of period start and end datetimes"""
        try:
            return self._periodHash
        except AttributeError:
            self._periodHash = hash((self.startDatetime,self.endDatetime)) # instant hashes (None, inst), forever hashes (None,None)
            return self._periodHash

    @property
    def entity(self):
        u"""(ModelObject) -- entity element"""
        try:
            return self._entity
        except AttributeError:
            self._entity = XmlUtil.child(self, XbrlConst.xbrli, u"entity")
            return self._entity

    @property
    def entityIdentifierElement(self):
        u"""(ModelObject) -- entity identifier element"""
        try:
            return self._entityIdentifierElement
        except AttributeError:
            self._entityIdentifierElement = XmlUtil.child(self.entity, XbrlConst.xbrli, u"identifier")
            return self._entityIdentifierElement

    @property
    def entityIdentifier(self):
        u"""( (str,str) ) -- tuple of (scheme value, identifier value)"""
        try:
            return self._entityIdentifier
        except AttributeError:
            eiElt = self.entityIdentifierElement
            if eiElt is not None:
                self._entityIdentifier = (eiElt.get(u"scheme"), eiElt.xValue or eiElt.textValue) # no xValue if --skipDTS
            else:
                self._entityIdentifier = (u"(Error)", u"(Error)")
            return self._entityIdentifier

    @property
    def entityIdentifierHash(self):
        u"""(int) -- hash of entityIdentifier"""
        try:
            return self._entityIdentifierHash
        except AttributeError:
            self._entityIdentifierHash = hash(self.entityIdentifier)
            return self._entityIdentifierHash

    @property
    def hasSegment(self):
        u"""(bool) -- True if a xbrli:segment element is present"""
        return XmlUtil.hasChild(self.entity, XbrlConst.xbrli, u"segment")

    @property
    def segment(self):
        u"""(ModelObject) -- xbrli:segment element"""
        return XmlUtil.child(self.entity, XbrlConst.xbrli, u"segment")

    @property
    def hasScenario(self):
        u"""(bool) -- True if a xbrli:scenario element is present"""
        return XmlUtil.hasChild(self, XbrlConst.xbrli, u"scenario")
    
    @property
    def scenario(self):
        u"""(ModelObject) -- xbrli:scenario element"""
        return XmlUtil.child(self, XbrlConst.xbrli, u"scenario")
    
    def dimValues(self, contextElement):
        u"""(dict) -- Indicated context element's dimension dict (indexed by ModelConcepts)
        
        :param contextElement: 'segment' or 'scenario'
        :returns: dict of ModelDimension objects indexed by ModelConcept dimension object, or empty dict
        """
        if contextElement == u"segment":
            return self.segDimValues
        elif contextElement == u"scenario":
            return self.scenDimValues
        return {}
    
    def hasDimension(self, dimQname):
        u"""(bool) -- True if dimension concept qname is reported by context (in either context element), not including defaulted dimensions."""
        return dimQname in self.qnameDims
    
    # returns ModelDimensionValue for instance dimensions, else QName for defaults
    def dimValue(self, dimQname):
        u"""(ModelDimension or QName) -- ModelDimension object if dimension is reported (in either context element), or QName of dimension default if there is a default, otherwise None"""
        try:
            return self.qnameDims[dimQname]
        except KeyError:
            try:
                return self.modelXbrl.qnameDimensionDefaults[dimQname]
            except KeyError:
                return None
    
    def dimMemberQname(self, dimQname, includeDefaults=False):
        u"""(QName) -- QName of explicit dimension if reported (or defaulted if includeDefaults is True), else None"""
        dimValue = self.dimValue(dimQname)
        if isinstance(dimValue, (ModelDimensionValue,DimValuePrototype)) and dimValue.isExplicit:
            return dimValue.memberQname
        elif isinstance(dimValue, ModelValue.QName):
            return dimValue
        if dimValue is None and includeDefaults and dimQname in self.modelXbrl.qnameDimensionDefaults:
            return self.modelXbrl.qnameDimensionDefaults[dimQname]
        return None
    
    def dimAspects(self, defaultDimensionAspects=None):
        u"""(set) -- For formula and instance aspects processing, set of all dimensions reported or defaulted."""
        if defaultDimensionAspects:
            return _DICT_SET(self.qnameDims.keys()) | defaultDimensionAspects
        return _DICT_SET(self.qnameDims.keys())
    
    @property
    def dimsHash(self):
        u"""(int) -- A hash of the set of reported dimension values."""
        try:
            return self._dimsHash
        except AttributeError:
            self._dimsHash = hash( frozenset(self.qnameDims.values()) )
            return self._dimsHash
    
    def nonDimValues(self, contextElement):
        u"""([ModelObject]) -- ContextElement is either string or Aspect code for segment or scenario, returns nonXDT ModelObject children of context element.
        
        :param contextElement: one of 'segment', 'scenario', Aspect.NON_XDT_SEGMENT, Aspect.NON_XDT_SCENARIO, Aspect.COMPLETE_SEGMENT, Aspect.COMPLETE_SCENARIO
        :type contextElement: str or Aspect type 
        :returns: list of ModelObjects 
        """
        if contextElement in (u"segment", Aspect.NON_XDT_SEGMENT):
            return self.segNonDimValues
        elif contextElement in (u"scenario", Aspect.NON_XDT_SCENARIO):
            return self.scenNonDimValues
        elif contextElement == Aspect.COMPLETE_SEGMENT and self.hasSegment:
            return XmlUtil.children(self.segment, None, u"*")
        elif contextElement == Aspect.COMPLETE_SCENARIO and self.hasScenario:
            return XmlUtil.children(self.scenario, None, u"*")
        return []
    
    @property
    def segmentHash(self):
        u"""(int) -- Hash of the segment, based on s-equality values"""
        return XbrlUtil.equalityHash( self.segment ) # self-caching
        
    @property
    def scenarioHash(self):
        u"""(int) -- Hash of the scenario, based on s-equality values"""
        return XbrlUtil.equalityHash( self.scenario ) # self-caching
    
    @property
    def nonDimSegmentHash(self):
        u"""(int) -- Hash, of s-equality values, of non-XDT segment objects"""
        try:
            return self._nonDimSegmentHash
        except AttributeError:
            self._nonDimSegmentHash = XbrlUtil.equalityHash(self.nonDimValues(u"segment"))
            return self._nonDimSegmentHash
        
    @property
    def nonDimScenarioHash(self):
        u"""(int) -- Hash, of s-equality values, of non-XDT scenario objects"""
        try:
            return self._nonDimScenarioHash
        except AttributeError:
            self._nonDimScenarioHash = XbrlUtil.equalityHash(self.nonDimValues(u"scenario"))
            return self._nonDimScenarioHash
        
    @property
    def nonDimHash(self):
        u"""(int) -- Hash, of s-equality values, of non-XDT segment and scenario objects"""
        try:
            return self._nonDimsHash
        except AttributeError:
            self._nonDimsHash = hash( (self.nonDimSegmentHash, self.nonDimScenarioHash) ) 
            return self._nonDimsHash
        
    @property
    def contextDimAwareHash(self):
        u"""(int) -- Hash of period, entityIdentifier, dim, and nonDims"""
        try:
            return self._contextDimAwareHash
        except AttributeError:
            self._contextDimAwareHash = hash( (self.periodHash, self.entityIdentifierHash, self.dimsHash, self.nonDimHash) )
            return self._contextDimAwareHash
        
    @property
    def contextNonDimAwareHash(self):
        u"""(int) -- Hash of period, entityIdentifier, segment, and scenario (s-equal based)"""
        try:
            return self._contextNonDimAwareHash
        except AttributeError:
            self._contextNonDimAwareHash = hash( (self.periodHash, self.entityIdentifierHash, self.segmentHash, self.scenarioHash) )
            return self._contextNonDimAwareHash
        
    @property
    def md5sum(self):
        try:
            return self._md5sum
        except AttributeError:
            _toHash = [self.entityIdentifier[0], self.entityIdentifier[1]]
            if self.isInstantPeriod:
                _toHash.append(self.instantDatetime)
            elif self.isStartEndPeriod:
                _toHash.append(self.startDatetime)
                _toHash.append(self.endDatetime)
            elif self.isForeverPeriod:
                _toHash.append(u"forever")
            if self.qnameDims:
                _toHash.extend([dim.md5sum for dim in self.qnameDims.values()])
            self._md5sum = md5hash(_toHash)
            return self._md5sum
    
    def isPeriodEqualTo(self, cntx2):
        u"""(bool) -- True if periods are datetime equal (based on 2.1 date offsets)"""
        if self.isForeverPeriod:
            return cntx2.isForeverPeriod
        elif self.isStartEndPeriod:
            if not cntx2.isStartEndPeriod:
                return False
            return self.startDatetime == cntx2.startDatetime and self.endDatetime == cntx2.endDatetime
        elif self.isInstantPeriod:
            if not cntx2.isInstantPeriod:
                return False
            return self.instantDatetime == cntx2.instantDatetime
        else:
            return False
        
    def isEntityIdentifierEqualTo(self, cntx2):
        u"""(bool) -- True if entityIdentifier values are equal (scheme and text value)"""
        return self.entityIdentifierHash == cntx2.entityIdentifierHash
    
    def isEqualTo(self, cntx2, dimensionalAspectModel=None):
        if dimensionalAspectModel is None: dimensionalAspectModel = self.modelXbrl.hasXDT
        try:
            return self._isEqualTo[(cntx2,dimensionalAspectModel)]
        except KeyError:
            result = self.isEqualTo_(cntx2, dimensionalAspectModel)
            self._isEqualTo[(cntx2,dimensionalAspectModel)] = result
            return result
        
    def isEqualTo_(self, cntx2, dimensionalAspectModel):
        u"""(bool) -- If dimensionalAspectModel is absent, True is assumed.  
        False means comparing based on s-equality of segment, scenario, while 
        True means based on dimensional values and nonDimensional values separately."""
        if cntx2 is None:
            return False
        if cntx2 == self:   # same context
            return True
        if (self.periodHash != cntx2.periodHash or
            self.entityIdentifierHash != cntx2.entityIdentifierHash):
            return False 
        if dimensionalAspectModel:
            if (self.dimsHash != cntx2.dimsHash or
                self.nonDimHash != cntx2.nonDimHash):
                return False
        else:
            if (self.segmentHash != cntx2.segmentHash or
                self.scenarioHash != cntx2.scenarioHash):
                return False
        if self.periodHash != cntx2.periodHash or not self.isPeriodEqualTo(cntx2) or not self.isEntityIdentifierEqualTo(cntx2):
            return False
        if dimensionalAspectModel:
            if _DICT_SET(self.qnameDims.keys()) != _DICT_SET(cntx2.qnameDims.keys()):
                return False
            for dimQname, ctx1Dim in self.qnameDims.items():
                if not ctx1Dim.isEqualTo(cntx2.qnameDims[dimQname]):
                    return False
            for nonDimVals1, nonDimVals2 in ((self.segNonDimValues,cntx2.segNonDimValues),
                                             (self.scenNonDimValues,cntx2.scenNonDimValues)):
                if len(nonDimVals1) !=  len(nonDimVals2):
                    return False
                for i, nonDimVal1 in enumerate(nonDimVals1):
                    if not XbrlUtil.sEqual(self.modelXbrl, nonDimVal1, nonDimVals2[i]):
                        return False                    
        else:
            if self.hasSegment:
                if not cntx2.hasSegment:
                    return False
                if not XbrlUtil.sEqual(self.modelXbrl, self.segment, cntx2.segment):
                    return False
            elif cntx2.hasSegment:
                return False
    
            if self.hasScenario:
                if not cntx2.hasScenario:
                    return False
                if not XbrlUtil.sEqual(self.modelXbrl, self.scenario, cntx2.scenario):
                    return False
            elif cntx2.hasScenario:
                return False
        
        return True

    @property
    def propertyView(self):
        scheme, entityId = self.entityIdentifier
        return (((u"entity", entityId, ((u"scheme", scheme),)),) +
                (((u"forever", u""),) if self.isForeverPeriod else
                 ((u"instant", XmlUtil.dateunionValue(self.instantDatetime, subtractOneDay=True)),) if self.isInstantPeriod else
                 ((u"startDate", XmlUtil.dateunionValue(self.startDatetime)),(u"endDate", XmlUtil.dateunionValue(self.endDatetime, subtractOneDay=True)))) +
                ((u"dimensions", u"({0})".format(len(self.qnameDims)),
                  tuple(mem.propertyView for dim,mem in sorted(self.qnameDims.items())))
                  if self.qnameDims else (),
                ))

    def __repr__(self):
        return (u"modelContext[{0}, period: {1}, {2}{3} line {4}]"
                .format(self.id,
                        u"forever" if self.isForeverPeriod else
                        u"instant " + XmlUtil.dateunionValue(self.instantDatetime, subtractOneDay=True) if self.isInstantPeriod else
                        u"duration " + XmlUtil.dateunionValue(self.startDatetime) + u" - " + XmlUtil.dateunionValue(self.endDatetime, subtractOneDay=True),
                        u"dimensions: ({0}) {1},".format(len(self.qnameDims),
                        tuple(mem.propertyView for dim,mem in sorted(self.qnameDims.items())))
                        if self.qnameDims else u"",
                        self.modelDocument.basename, self.sourceline))

class ModelDimensionValue(ModelObject):
    u"""
    .. class:: ModelDimensionValue(modelDocument)
    
    Model dimension value (both explicit and typed, non-default values)
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelDimensionValue, self).init(modelDocument)
        
    def __hash__(self):
        if self.isExplicit:
            return hash( (self.dimensionQname, self.memberQname) )
        else: # need XPath equal so that QNames aren't lexically compared (for fact and context equality in comparing formula results)
            return hash( (self.dimensionQname, XbrlUtil.equalityHash(XmlUtil.child(self), equalMode=XbrlUtil.XPATH_EQ)) )

    @property
    def md5sum(self):
        if self.isExplicit:
            return md5hash([self.dimensionQname, self.memberQname])
        else:
            return md5hash([self.dimensionQname, self.typedMember])
    
    @property
    def dimensionQname(self):
        u"""(QName) -- QName of the dimension concept"""
        dimAttr = self.xAttributes.get(u"dimension", None)
        if dimAttr is not None and dimAttr.xValid >= 4:
            return dimAttr.xValue
        return None
        #return self.prefixedNameQname(self.get("dimension"))
        
    @property
    def dimension(self):
        u"""(ModelConcept) -- Dimension concept"""
        try:
            return self._dimension
        except AttributeError:
            self._dimension = self.modelXbrl.qnameConcepts.get(self.dimensionQname)
            return  self._dimension
        
    @property
    def isExplicit(self):
        u"""(bool) -- True if explicitMember element"""
        return self.localName == u"explicitMember"
    
    @property
    def typedMember(self):
        u"""(ModelConcept) -- Child ModelObject that is the dimension member element
        
        (To get <typedMember> element use 'self').
        """
        for child in self.iterchildren():
            if isinstance(child, ModelObject):  # skip comment and processing nodes
                return child
        return None

    @property
    def isTyped(self):
        u"""(bool) -- True if typedMember element"""
        return self.localName == u"typedMember"

    @property
    def memberQname(self):
        u"""(QName) -- QName of an explicit dimension member"""
        try:
            return self._memberQname
        except AttributeError:
            if self.isExplicit and self.xValid >= 4:
                self._memberQname = self.xValue
            else:
                self._memberQname = None
            #self._memberQname = self.prefixedNameQname(self.textValue) if self.isExplicit else None
            return self._memberQname
        
    @property
    def member(self):
        u"""(ModelConcept) -- Concept of an explicit dimension member"""
        try:
            return self._member
        except AttributeError:
            self._member = self.modelXbrl.qnameConcepts.get(self.memberQname)
            return  self._member
        
    def isEqualTo(self, other, equalMode=XbrlUtil.XPATH_EQ):
        u"""(bool) -- True if explicit member QNames equal or typed member nodes correspond, given equalMode (s-equal, s-equal2, or xpath-equal for formula)
        
        :param equalMode: XbrlUtil.S_EQUAL (ordinary S-equality from 2.1 spec), XbrlUtil.S_EQUAL2 (XDT definition of equality, adding QName comparisions), or XbrlUtil.XPATH_EQ (XPath EQ on all types)
        """
        if other is None:
            return False
        if self.isExplicit: # other is either ModelDimensionValue or the QName value of explicit dimension
            return self.memberQname == (other.memberQname if isinstance(other, (ModelDimensionValue,DimValuePrototype)) else other)
        else: # typed dimension compared to another ModelDimensionValue or other is the value nodes
            return XbrlUtil.nodesCorrespond(self.modelXbrl, self.typedMember, 
                                            other.typedMember if isinstance(other, (ModelDimensionValue,DimValuePrototype)) else other, 
                                            equalMode=equalMode, excludeIDs=XbrlUtil.NO_IDs_EXCLUDED)
        
    @property
    def contextElement(self):
        u"""(str) -- 'segment' or 'scenario'"""
        return self.getparent().localName
    
    @property
    def propertyView(self):
        if self.isExplicit:
            return (unicode(self.dimensionQname),unicode(self.memberQname))
        else:
            return (unicode(self.dimensionQname), XmlUtil.xmlstring( XmlUtil.child(self), stripXmlns=True, prettyPrint=True ) )
        
def measuresOf(parent):
    if parent.xValid >= 4: # has DTS and is validated
        return sorted([m.xValue 
                       for m in parent.iterchildren(tag=u"{http://www.xbrl.org/2003/instance}measure") 
                       if isinstance(m, ModelObject) and m.xValue])
    else:  # probably skipDTS
        return sorted([m.prefixedNameQname(m.textValue) or XbrlConst.qnInvalidMeasure
                       for m in parent.iterchildren(tag=u"{http://www.xbrl.org/2003/instance}measure") 
                       if isinstance(m, ModelObject)])

def measuresStr(m):
    return m.localName if m.namespaceURI in (XbrlConst.xbrli, XbrlConst.iso4217) else unicode(m)

class ModelUnit(ModelObject):
    u"""
    .. class:: ModelUnit(modelDocument)
    
    Model unit
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelUnit, self).init(modelDocument)
        
    @property
    def measures(self):
        u"""([QName],[Qname]) -- Returns a tuple of multiply measures list and divide members list 
        (empty if not a divide element).  Each list of QNames is in prefixed-name order."""
        try:
            return self._measures
        except AttributeError:
            if self.isDivide:
                self._measures = (measuresOf(XmlUtil.descendant(self, XbrlConst.xbrli, u"unitNumerator")),
                                  measuresOf(XmlUtil.descendant(self, XbrlConst.xbrli, u"unitDenominator")))
            else:
                self._measures = (measuresOf(self),[])
            return self._measures

    @property
    def hash(self):
        u"""(bool) -- Hash of measures in both multiply and divide lists."""
        try:
            return self._hash
        except AttributeError:
            # should this use frozenSet of each measures element?
            self._hash = hash( ( tuple(self.measures[0]),tuple(self.measures[1]) ) )
            return self._hash

    @property
    def md5hash(self):
        u"""(bool) -- md5 Hash of measures in both multiply and divide lists."""
        try:
            return self._md5hash
        except AttributeError:
            md5hash = md5()
            for i, measures in enumerate(self.measures):
                if i:
                    md5hash.update("divisor")
                for measure in measures:
                    if measure.namespaceURI:
                        md5hash.update(measure.namespaceURI.encode(u'utf-8',u'replace'))
                    md5hash.update(measure.localName.encode(u'utf-8',u'replace'))
            # should this use frozenSet of each measures element?
            self._md5hash = md5hash.hexdigest()
            return self._md5hash
    
    @property
    def md5sum(self):
        try:
            return self._md5sum
        except AttributeError:
            if self.isDivide: # hash of mult and div hex strings of hashes of measures
                self._md5sum = md5hash([md5hash([md5hash(m) for m in md]).toHex() 
                                        for md in self.measures])
            else: # sum of hash sums
                self._md5sum = md5hash([md5hash(m) for m in self.measures[0]])
            return self._md5sum
 
    @property
    def isDivide(self):
        u"""(bool) -- True if unit has a divide element"""
        return XmlUtil.hasChild(self, XbrlConst.xbrli, u"divide")
    
    @property
    def isSingleMeasure(self):
        u"""(bool) -- True for a single multiply and no divide measures"""
        measures = self.measures
        return len(measures[0]) == 1 and len(measures[1]) == 0
    
    def isEqualTo(self, unit2):
        u"""(bool) -- True if measures are equal"""
        if unit2 is None or unit2.hash != self.hash: 
            return False
        return unit2 is self or self.measures == unit2.measures
    
    @property
    def value(self):
        u"""(str) -- String value for view purposes, space separated list of string qnames 
        of multiply measures, and if any divide, a '/' character and list of string qnames 
        of divide measure qnames."""
        mul, div = self.measures
        return u' '.join([measuresStr(m) for m in mul] + ([u'/'] + [measuresStr(d) for d in div] if div else []))

    def utrEntries(self, modelType):
        try:
            return self._utrEntries[modelType]
        except AttributeError:
            self._utrEntries = {}
            return self.utrEntries(modelType)
        except KeyError:
            global utrEntries
            if utrEntries is None:
                from arelle.ValidateUtr import utrEntries
            self._utrEntries[modelType] = utrEntries(modelType, self)
            return self._utrEntries[modelType]
    
    def utrSymbol(self, modelType):
        try:
            return self._utrSymbols[modelType]
        except AttributeError:
            self._utrSymbols = {}
            return self.utrSymbol(modelType)
        except KeyError:
            global utrSymbol
            if utrSymbol is None:
                from arelle.ValidateUtr import utrSymbol
            self._utrSymbols[modelType] = utrSymbol(modelType, self.measures)
            return self._utrSymbols[modelType]
                
    
    @property
    def propertyView(self):
        measures = self.measures
        if measures[1]:
            return tuple((u'mul',m) for m in measures[0]) + \
                   tuple((u'div',d) for d in measures[1]) 
        else:
            return tuple((u'measure',m) for m in measures[0])

from arelle.ModelDtsObject import ModelResource
class ModelInlineFootnote(ModelResource):
    u"""
    .. class:: ModelInlineFootnote(modelDocument)
    
    Model inline footnote (inline XBRL facts)
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelInlineFootnote, self).init(modelDocument)
        
    @property
    def qname(self):
        u"""(QName) -- QName of generated object"""
        return XbrlConst.qnLinkFootnote
    
    @property
    def footnoteID(self):
        return self.get(u"footnoteID")

    @property
    def value(self):
        u"""(str) -- Overrides and corresponds to value property of ModelFact, 
        for relevant inner text nodes aggregated and transformed as needed."""
        try:
            return self._ixValue
        except AttributeError:
            self._ixValue = XmlUtil.innerText(self, 
                                  ixExclude=True, 
                                  ixContinuation=(self.namespaceURI != XbrlConst.ixbrl),
                                  strip=True) # transforms are whitespace-collapse

            return self._ixValue
        
    @property
    def textValue(self):
        u"""(str) -- override xml-level stringValue for transformed value descendants text"""
        return self.value
        
    @property
    def stringValue(self):
        u"""(str) -- override xml-level stringValue for transformed value descendants text"""
        return self.value
    
    @property
    def role(self):
        u"""(str) -- xlink:role attribute"""
        return self.get(u"footnoteRole") or XbrlConst.footnote
        
    @property
    def xlinkLabel(self):
        u"""(str) -- xlink:label attribute"""
        return self.get(u"footnoteID")

    @property
    def xmlLang(self):
        u"""(str) -- xml:lang attribute"""
        return XmlUtil.ancestorOrSelfAttr(self, u"{http://www.w3.org/XML/1998/namespace}lang")
    
    @property
    def attributes(self):
        # for output of derived instance, includes all output-applicable attributes
        attributes = {u"{http://www.w3.org/1999/xlink}type":u"resource",
                      u"{http://www.w3.org/1999/xlink}label":self.xlinkLabel,
                      u"{http://www.w3.org/1999/xlink}role": self.role}
        lang = self.xmlLang
        if lang:
            attributes[u"{http://www.w3.org/XML/1998/namespace}lang"] = lang
        return attributes

    def viewText(self, labelrole=None, lang=None):
        u"""(str) -- Text of contained (inner) text nodes except for any whose localName 
        starts with URI, for label and reference parts displaying purposes."""
        return u" ".join([XmlUtil.text(resourceElt)
                           for resourceElt in self.iter()
                              if isinstance(resourceElt,ModelObject) and 
                                  not resourceElt.localName.startswith(u"URI")])    
        
    @property
    def propertyView(self):
        return ((u"file", self.modelDocument.basename),
                (u"line", self.sourceline)) + \
               super(ModelInlineFact,self).propertyView + \
               ((u"html value", XmlUtil.innerText(self)),)
        
    def __repr__(self):
        return (u"modelInlineFootnote[{0}]{1})".format(self.objectId(),self.propertyView))
               
        
from arelle.ModelFormulaObject import Aspect
from arelle import FunctionIxt
           
from arelle.ModelObjectFactory import elementSubstitutionModelClass
elementSubstitutionModelClass.update((
     (XbrlConst.qnXbrliItem, ModelFact),
     (XbrlConst.qnXbrliTuple, ModelFact),
     (XbrlConst.qnIXbrlTuple, ModelInlineFact),
     (XbrlConst.qnIXbrl11Tuple, ModelInlineFact),
     (XbrlConst.qnIXbrlNonNumeric, ModelInlineFact),
     (XbrlConst.qnIXbrl11NonNumeric, ModelInlineFact),
     (XbrlConst.qnIXbrlNonFraction, ModelInlineFact),
     (XbrlConst.qnIXbrl11NonFraction, ModelInlineFact),
     (XbrlConst.qnIXbrlFraction, ModelInlineFraction),
     (XbrlConst.qnIXbrl11Fraction, ModelInlineFraction),
     (XbrlConst.qnIXbrlNumerator, ModelInlineFractionTerm),
     (XbrlConst.qnIXbrl11Numerator, ModelInlineFractionTerm),
     (XbrlConst.qnIXbrlDenominator, ModelInlineFractionTerm),
     (XbrlConst.qnIXbrl11Denominator, ModelInlineFractionTerm),
     (XbrlConst.qnIXbrlFootnote, ModelInlineFootnote),
     (XbrlConst.qnIXbrl11Footnote, ModelInlineFootnote),
     (XbrlConst.qnXbrliContext, ModelContext),
     (XbrlConst.qnXbrldiExplicitMember, ModelDimensionValue),
     (XbrlConst.qnXbrldiTypedMember, ModelDimensionValue),
     (XbrlConst.qnXbrliUnit, ModelUnit),
    ))
