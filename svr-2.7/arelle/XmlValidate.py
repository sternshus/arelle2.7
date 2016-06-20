u'''
Created on Feb 20, 2011

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
import os
try:
    from regex import compile as re_compile
except ImportError:
    from re import compile as re_compile
from decimal import Decimal, InvalidOperation
from arelle import XbrlConst, XmlUtil
from arelle.ModelValue import (qname, qnameEltPfxName, qnameClarkName, 
                               dateTime, DATE, DATETIME, DATEUNION, 
                               anyURI, INVALIDixVALUE, gYearMonth, gMonthDay, gYear, gMonth, gDay)
from arelle.ModelObject import ModelObject, ModelAttribute
from arelle import UrlUtil
validateElementSequence = None  #dynamic import to break dependency loops
modelGroupCompositorTitle = None
ModelInlineValueObject = None

UNVALIDATED = 0 # note that these values may be used a constants in code for better efficiency
UNKNOWN = 1
INVALID = 2
NONE = 3
VALID = 4 # values >= VALID are valid
VALID_ID = 5
VALID_NO_CONTENT = 6 # may be a complex type with children

normalizeWhitespacePattern = re_compile(ur"\s")
collapseWhitespacePattern = re_compile(ur"\s+")
languagePattern = re_compile(u"[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*$")
NCNamePattern = re_compile(u"^[_A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]"
                            ur"[_\-\." 
                               u"\xB7A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\u0300-\u036F\u203F-\u2040]*$")
QNamePattern = re_compile(u"^([_A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]"
                             ur"[_\-\." 
                               u"\xB7A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\u0300-\u036F\u203F-\u2040]*:)?"
                          u"[_A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]"
                            ur"[_\-\." 
                               u"\xB7A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\u0300-\u036F\u203F-\u2040]*$")
namePattern = re_compile(u"^[_A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]"
                            ur"[_\-\.:" 
                               u"\xB7A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\u0300-\u036F\u203F-\u2040]*$")

NMTOKENPattern = re_compile(ur"[_\-\.:" 
                               u"\xB7A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\u0300-\u036F\u203F-\u2040]+$")

decimalPattern = re_compile(ur"^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)$")
integerPattern = re_compile(ur"^[+-]?([0-9]+)$")
floatPattern = re_compile(ur"^(\+|-)?([0-9]+(\.[0-9]*)?|\.[0-9]+)([Ee](\+|-)?[0-9]+)?$|^(\+|-)?INF$|^NaN$")

lexicalPatterns = {
    u"duration": re_compile(u"-?P((([0-9]+Y([0-9]+M)?([0-9]+D)?|([0-9]+M)([0-9]+D)?|([0-9]+D))(T(([0-9]+H)([0-9]+M)?([0-9]+(\.[0-9]+)?S)?|([0-9]+M)([0-9]+(\.[0-9]+)?S)?|([0-9]+(\.[0-9]+)?S)))?)|(T(([0-9]+H)([0-9]+M)?([0-9]+(\.[0-9]+)?S)?|([0-9]+M)([0-9]+(\.[0-9]+)?S)?|([0-9]+(\.[0-9]+)?S))))$"),
    u"gYearMonth": re_compile(ur"-?([1-9][0-9]{3,}|0[0-9]{3})-(0[1-9]|1[0-2])(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$"),
    u"gYear": re_compile(ur"-?([1-9][0-9]{3,}|0[0-9]{3})(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$"),
    u"gMonthDay": re_compile(ur"--(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$"),
    u"gDay": re_compile(ur"---(0[1-9]|[12][0-9]|3[01])(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$"),
    u"gMonth": re_compile(ur"--(0[1-9]|1[0-2])(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$"), 
    u"language": re_compile(ur"[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*$"),   
    }

# patterns difficult to compile into python
xmlSchemaPatterns = {
    ur"\c+": NMTOKENPattern,
    ur"\i\c*": namePattern,
    ur"[\i-[:]][\c-[:]]*": NCNamePattern,
    }

# patterns to replace \c and \i in names
iNameChar = u"[_A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]"
cNameChar = ur"[_\-\.:"   u"\xB7A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\u0300-\u036F\u203F-\u2040]"

baseXsdTypePatterns = {
                u"Name": namePattern,
                u"language": languagePattern,
                u"NMTOKEN": NMTOKENPattern,
                u"NCName": NCNamePattern,
                u"ID": NCNamePattern,
                u"IDREF": NCNamePattern,
                u"ENTITY": NCNamePattern, 
                u"QName": QNamePattern,               
            }
predefinedAttributeTypes = {
    qname(u"{http://www.w3.org/XML/1998/namespace}xml:lang"):(u"language",None),
    qname(u"{http://www.w3.org/XML/1998/namespace}xml:space"):(u"NCName",{u"enumeration":set([u"default",u"preserve"])})}

xAttributesSharedEmptyDict = {}

def validate(modelXbrl, elt, recurse=True, attrQname=None, ixFacts=False):
    global ModelInlineValueObject
    if ModelInlineValueObject is None:
        from arelle.ModelInstanceObject import ModelInlineValueObject
    isIxFact = isinstance(elt, ModelInlineValueObject)
    facets = None

    # attrQname can be provided for attributes that are global and LAX
    if (getattr(elt,u"xValid", UNVALIDATED) == UNVALIDATED) and (not isIxFact or ixFacts):
        qnElt = elt.qname if ixFacts and isIxFact else elt.elementQname
        modelConcept = modelXbrl.qnameConcepts.get(qnElt)
        if modelConcept is not None:
            isNillable = modelConcept.isNillable
            type = modelConcept.type
            if modelConcept.isAbstract:
                baseXsdType = u"noContent"
            else:
                baseXsdType = modelConcept.baseXsdType
                facets = modelConcept.facets
        elif qnElt == XbrlConst.qnXbrldiExplicitMember: # not in DTS
            baseXsdType = u"QName"
            type = None
            isNillable = False
        elif qnElt == XbrlConst.qnXbrldiTypedMember: # not in DTS
            baseXsdType = u"noContent"
            type = None
            isNillable = False
        else:
            baseXsdType = None
            type = None
            isNillable = True # allow nil if no schema definition
        isNil = elt.get(u"{http://www.w3.org/2001/XMLSchema-instance}nil") in (u"true", u"1")
        if attrQname is None:
            if isNil and not isNillable:
                if ModelInlineValueObject is not None and isinstance(elt, ModelInlineValueObject):
                    errElt = u"{0} fact {1}".format(elt.elementQname, elt.qname)
                else:
                    errElt = elt.elementQname
                modelXbrl.error(u"xmlValidation:nilNonNillableElement",
                    _(u"Element %(element)s fact %(fact)s type %(typeName)s is nil but element has not been defined nillable"),
                    modelObject=elt, element=errElt, fact=elt.qname, transform=elt.format,
                    typeName=modelConcept.baseXsdType if modelConcept is not None else u"unknown",
                    value=XmlUtil.innerText(elt, ixExclude=True))
            try:
                if isNil:
                    text = u""
                elif baseXsdType == u"noContent":
                    text = elt.textValue # no descendant text nodes
                else:
                    text = elt.stringValue # include descendant text nodes
                    if len(text) == 0 and modelConcept is not None:
                        if modelConcept.default is not None:
                            text = modelConcept.default
                        elif modelConcept.fixed is not None:
                            text = modelConcept.fixed
            except Exception, err:
                if ModelInlineValueObject is not None and isinstance(elt, ModelInlineValueObject):
                    errElt = u"{0} fact {1}".format(elt.elementQname, elt.qname)
                else:
                    errElt = elt.elementQname
                if isIxFact and err.__class__.__name__ == u"FunctionArgType":
                    modelXbrl.error(u"ixTransform:valueError",
                        _(u"Inline element %(element)s fact %(fact)s type %(typeName)s transform %(transform)s value error: %(value)s"),
                        modelObject=elt, element=errElt, fact=elt.qname, transform=elt.format,
                        typeName=modelConcept.baseXsdType if modelConcept is not None else u"unknown",
                        value=XmlUtil.innerText(elt, ixExclude=True))
                else:
                    modelXbrl.error(u"xmlValidation:valueError",
                        _(u"Element %(element)s error %(error)s value: %(value)s"),
                        modelObject=elt, element=errElt, error=unicode(err), value=elt.text)
                elt.sValue = elt.xValue = text = INVALIDixVALUE
                elt.xValid = INVALID
            if text is not INVALIDixVALUE:
                validateValue(modelXbrl, elt, None, baseXsdType, text, isNillable, isNil, facets)
                # note that elt.sValue and elt.xValue are not innerText but only text elements on specific element (or attribute)
            if type is not None:
                definedAttributes = type.attributes
            else:
                definedAttributes = {}
            presentAttributes = set()
        # validate attributes
        # find missing attributes for default values
        for attrTag, attrValue in elt.items():
            qn = qnameClarkName(attrTag)
            #qn = qname(attrTag, noPrefixIsNoNamespace=True)
            baseXsdAttrType = None
            facets = None
            if attrQname is not None: # validate all attributes and element
                if attrQname != qn:
                    continue
            elif type is not None:
                presentAttributes.add(qn)
                if qn in definedAttributes: # look for concept-type-specific attribute definition
                    modelAttr = definedAttributes[qn]
                elif qn.namespaceURI:   # may be a globally defined attribute
                    modelAttr = modelXbrl.qnameAttributes.get(qn)
                else:
                    modelAttr = None
                if modelAttr is not None:
                    baseXsdAttrType = modelAttr.baseXsdType
                    facets = modelAttr.facets
            if baseXsdAttrType is None: # look for global attribute definition
                attrObject = modelXbrl.qnameAttributes.get(qn)
                if attrObject is not None:
                    baseXsdAttrType = attrObject.baseXsdType
                    facets = attrObject.facets
                elif attrTag == u"{http://xbrl.org/2006/xbrldi}dimension": # some fallbacks?
                    baseXsdAttrType = u"QName"
                elif attrTag == u"id":
                    baseXsdAttrType = u"ID"
                elif elt.namespaceURI == u"http://www.w3.org/2001/XMLSchema":
                    if attrTag in set([u"type", u"ref", u"base", u"refer", u"itemType"]):
                        baseXsdAttrType = u"QName"
                    elif attrTag in set([u"name"]):
                        baseXsdAttrType = u"NCName"
                    elif attrTag in set([u"default", u"fixed", u"form"]):
                        baseXsdAttrType = u"string"
                elif elt.namespaceURI == u"http://xbrl.org/2006/xbrldi":
                    if attrTag == u"dimension":
                        baseXsdAttrType = u"QName"
                elif qn in predefinedAttributeTypes:
                    baseXsdAttrType, facets = predefinedAttributeTypes[qn]
            validateValue(modelXbrl, elt, attrTag, baseXsdAttrType, attrValue, facets=facets)
        # if no attributes assigned above, there won't be an xAttributes, if so assign a shared dict to save memory
        try:
            elt.xAttributes
        except AttributeError:
            elt.xAttributes = xAttributesSharedEmptyDict
            
        if type is not None:
            if attrQname is None:
                missingAttributes = type.requiredAttributeQnames - presentAttributes - elt.slottedAttributesNames
                if missingAttributes:
                    modelXbrl.error(u"xmlSchema:attributesRequired",
                        _(u"Element %(element)s type %(typeName)s missing required attributes: %(attributes)s"),
                        modelObject=elt,
                        element=qnElt,
                        typeName=baseXsdType,
                        attributes=u','.join(unicode(a) for a in missingAttributes))
                extraAttributes = presentAttributes - _DICT_SET(definedAttributes.keys()) - XbrlConst.builtinAttributes
                if extraAttributes:
                    attributeWildcards = type.attributeWildcards
                    extraAttributes -= set(a
                                           for a in extraAttributes
                                           if validateAnyWildcard(qnElt, a, attributeWildcards))
                    if isIxFact:
                        extraAttributes -= XbrlConst.ixAttributes
                    if extraAttributes:
                        modelXbrl.error(u"xmlSchema:attributesExtraneous",
                            _(u"Element %(element)s type %(typeName)s extraneous attributes: %(attributes)s"),
                            modelObject=elt,
                            element=qnElt,
                            typeName=baseXsdType,
                            attributes=u','.join(unicode(a) for a in extraAttributes))
                # add default attribute values
                for attrQname in (type.defaultAttributeQnames - presentAttributes):
                    modelAttr = type.attributes[attrQname]
                    validateValue(modelXbrl, elt, attrQname.clarkNotation, modelAttr.baseXsdType, modelAttr.default, facets=modelAttr.facets)
            if recurse:
                global validateElementSequence, modelGroupCompositorTitle
                if validateElementSequence is None:
                    from arelle.XmlValidateParticles import validateElementSequence, modelGroupCompositorTitle
                try:
                    #childElts = list(elt) # uses __iter__ for inline facts
                    childElts = [e for e in elt if isinstance(e, ModelObject)]
                    if isNil:
                        if childElts or elt.text:
                            modelXbrl.error(u"xmlSchema:nilElementHasContent",
                                _(u"Element %(element)s is nil but has contents"),
                                modelObject=elt,
                                element=qnElt)
                    else:
                        errResult = validateElementSequence(modelXbrl, type, childElts, ixFacts)
                        if errResult is not None and errResult[2]:
                            iElt, occured, errDesc, errArgs = errResult
                            errElt = childElts[iElt] if iElt < len(childElts) else elt
                            errArgs[u"modelObject"] = errElt
                            errArgs[u"element"] = errElt.qname
                            errArgs[u"parentElement"] = elt.qname
                            if u"compositor" in errArgs:  # compositor is an object, provide friendly string
                                errArgs[u"compositor"] = modelGroupCompositorTitle(errArgs[u"compositor"])
                            modelXbrl.error(*errDesc,**errArgs)
                                                        
                            # when error is in an xbrli element, check any further unvalidated children
                            if qnElt.namespaceURI == XbrlConst.xbrli and iElt < len(childElts):
                                for childElt in childElts[iElt:]:
                                    if (getattr(childElt,u"xValid", UNVALIDATED) == UNVALIDATED):
                                        validate(modelXbrl, childElt, ixFacts=ixFacts)
                    recurse = False # cancel child element validation below, recursion was within validateElementSequence
                except AttributeError, ex:
                    raise ex
                    #pass  # HF Why is this here????
    if recurse: # if there is no complex or simple type (such as xbrli:measure) then this code is used
        for child in (elt.modelTupleFacts if ixFacts and isIxFact else elt):
            if isinstance(child, ModelObject):     
                validate(modelXbrl, child, recurse, attrQname, ixFacts)

def validateValue(modelXbrl, elt, attrTag, baseXsdType, value, isNillable=False, isNil=False, facets=None):
    if baseXsdType:
        try:
            u'''
            if (len(value) == 0 and attrTag is None and not isNillable and 
                baseXsdType not in ("anyType", "string", "normalizedString", "token", "NMTOKEN", "anyURI", "noContent")):
                raise ValueError("missing value for not nillable element")
            '''
            xValid = VALID
            whitespaceReplace = (baseXsdType == u"normalizedString")
            whitespaceCollapse = (not whitespaceReplace and baseXsdType != u"string")
            isList = baseXsdType in set([u"IDREFS", u"ENTITIES", u"NMTOKENS"])
            if isList:
                baseXsdType = baseXsdType[:-1] # remove plural
            pattern = baseXsdTypePatterns.get(baseXsdType)
            if facets:
                if u"pattern" in facets:
                    pattern = facets[u"pattern"]
                    # note multiple patterns are or'ed togetner, which isn't yet implemented!
                if u"whiteSpace" in facets:
                    whitespaceReplace, whitespaceCollapse = {u"preserve":(False,False), u"replace":(True,False), u"collapse":(False,True)}[facets[u"whiteSpace"]]
            if whitespaceReplace:
                value = normalizeWhitespacePattern.sub(u' ', value)
            elif whitespaceCollapse:
                value = collapseWhitespacePattern.sub(u' ', value.strip())
            if baseXsdType == u"noContent":
                if len(value) > 0 and not value.isspace():
                    raise ValueError(u"value content not permitted")
                # note that sValue and xValue are not innerText but only text elements on specific element (or attribute)
                xValue = sValue = None
                xValid = VALID_NO_CONTENT # notify others that element may contain subelements (for stringValue needs)
            elif not value and isNil and isNillable: # rest of types get None if nil/empty value
                xValue = sValue = None
            else:
                if pattern is not None:
                    if ((isList and any(pattern.match(v) is None for v in value.split())) or
                        (not isList and pattern.match(value) is None)):
                        raise ValueError(u"pattern facet " + facets[u"pattern"].pattern if facets and u"pattern" in facets else u"pattern mismatch")
                if facets:
                    if u"enumeration" in facets and value not in facets[u"enumeration"]:
                        raise ValueError(u"{0} is not in {1}".format(value, facets[u"enumeration"]))
                    if u"length" in facets and len(value) != facets[u"length"]:
                        raise ValueError(u"length {0}, expected {1}".format(len(value), facets[u"length"]))
                    if u"minLength" in facets and len(value) < facets[u"minLength"]:
                        raise ValueError(u"length {0}, minLength {1}".format(len(value), facets[u"minLength"]))
                    if u"maxLength" in facets and len(value) > facets[u"maxLength"]:
                        raise ValueError(u"length {0}, maxLength {1}".format(len(value), facets[u"maxLength"]))
                if baseXsdType in set([u"string", u"normalizedString", u"language", u"token", u"NMTOKEN",u"Name",u"NCName",u"IDREF",u"ENTITY"]):
                    xValue = sValue = value
                elif baseXsdType == u"ID":
                    xValue = sValue = value
                    xValid = VALID_ID
                elif baseXsdType == u"anyURI":
                    if value:  # allow empty strings to be valid anyURIs
                        if UrlUtil.relativeUrlPattern.match(value) is None:
                            raise ValueError(u"IETF RFC 2396 4.3 syntax")
                    # encode PSVI xValue similarly to Xerces and other implementations
                    xValue = anyURI(UrlUtil.anyUriQuoteForPSVI(value))
                    sValue = value
                elif baseXsdType in (u"decimal", u"float", u"double"):
                    if baseXsdType == u"decimal":
                        if decimalPattern.match(value) is None:
                            raise ValueError(u"lexical pattern mismatch")
                        xValue = Decimal(value)
                        sValue = float(value) # s-value uses Number (float) representation
                    else:
                        if floatPattern.match(value) is None:
                            raise ValueError(u"lexical pattern mismatch")
                        xValue = sValue = float(value)
                    if facets:
                        if u"totalDigits" in facets and len(value.replace(u".",u"")) > facets[u"totalDigits"]:
                            raise ValueError(u"totalDigits facet {0}".format(facets[u"totalDigits"]))
                        if u"fractionDigits" in facets and ( u'.' in value and
                            len(value[value.index(u'.') + 1:]) > facets[u"fractionDigits"]):
                            raise ValueError(u"fraction digits facet {0}".format(facets[u"fractionDigits"]))
                        if u"maxInclusive" in facets and xValue > facets[u"maxInclusive"]:
                            raise ValueError(u" > maxInclusive {0}".format(facets[u"maxInclusive"]))
                        if u"maxExclusive" in facets and xValue >= facets[u"maxExclusive"]:
                            raise ValueError(u" >= maxInclusive {0}".format(facets[u"maxExclusive"]))
                        if u"minInclusive" in facets and xValue < facets[u"minInclusive"]:
                            raise ValueError(u" < minInclusive {0}".format(facets[u"minInclusive"]))
                        if u"minExclusive" in facets and xValue <= facets[u"minExclusive"]:
                            raise ValueError(u" <= minExclusive {0}".format(facets[u"minExclusive"]))
                elif baseXsdType in set([u"integer",
                                     u"nonPositiveInteger",u"negativeInteger",u"nonNegativeInteger",u"positiveInteger",
                                     u"long",u"unsignedLong",
                                     u"int",u"unsignedInt",
                                     u"short",u"unsignedShort",
                                     u"byte",u"unsignedByte"]):
                    xValue = sValue = _INT(value)
                    if ((baseXsdType in set([u"nonNegativeInteger",u"unsignedLong",u"unsignedInt"]) 
                         and xValue < 0) or
                        (baseXsdType == u"nonPositiveInteger" and xValue > 0) or
                        (baseXsdType == u"positiveInteger" and xValue <= 0) or
                        (baseXsdType == u"byte" and not -128 <= xValue < 127) or
                        (baseXsdType == u"unsignedByte" and not 0 <= xValue < 255) or
                        (baseXsdType == u"short" and not -32768 <= xValue < 32767) or
                        (baseXsdType == u"unsignedShort" and not 0 <= xValue < 65535) or
                        (baseXsdType == u"positiveInteger" and xValue <= 0)):
                        raise ValueError(u"{0} is not {1}".format(value, baseXsdType))
                    if facets:
                        if u"totalDigits" in facets and len(value.replace(u".",u"")) > facets[u"totalDigits"]:
                            raise ValueError(u"totalDigits facet {0}".format(facets[u"totalDigits"]))
                        if u"fractionDigits" in facets and ( u'.' in value and
                            len(value[value.index(u'.') + 1:]) > facets[u"fractionDigits"]):
                            raise ValueError(u"fraction digits facet {0}".format(facets[u"fractionDigits"]))
                        if u"maxInclusive" in facets and xValue > facets[u"maxInclusive"]:
                            raise ValueError(u" > maxInclusive {0}".format(facets[u"maxInclusive"]))
                        if u"maxExclusive" in facets and xValue >= facets[u"maxExclusive"]:
                            raise ValueError(u" >= maxInclusive {0}".format(facets[u"maxExclusive"]))
                        if u"minInclusive" in facets and xValue < facets[u"minInclusive"]:
                            raise ValueError(u" < minInclusive {0}".format(facets[u"minInclusive"]))
                        if u"minExclusive" in facets and xValue <= facets[u"minExclusive"]:
                            raise ValueError(u" <= minExclusive {0}".format(facets[u"minExclusive"]))
                elif baseXsdType == u"boolean":
                    if value in (u"true", u"1"):  
                        xValue = sValue = True
                    elif value in (u"false", u"0"): 
                        xValue = sValue = False
                    else: raise ValueError
                elif baseXsdType == u"QName":
                    xValue = qnameEltPfxName(elt, value, prefixException=ValueError)
                    #xValue = qname(elt, value, castException=ValueError, prefixException=ValueError)
                    sValue = value
                    u''' not sure here, how are explicitDimensions validated, but bad units not?
                    if xValue.namespaceURI in modelXbrl.namespaceDocs:
                        if (xValue not in modelXbrl.qnameConcepts and 
                            xValue not in modelXbrl.qnameTypes and
                            xValue not in modelXbrl.qnameAttributes and
                            xValue not in modelXbrl.qnameAttributeGroups):
                            raise ValueError("qname not defined " + str(xValue))
                    '''
                elif baseXsdType in (u"XBRLI_DECIMALSUNION", u"XBRLI_PRECISIONUNION"):
                    xValue = sValue = value if value == u"INF" else _INT(value)
                elif baseXsdType in (u"XBRLI_NONZERODECIMAL"):
                    xValue = sValue = _INT(value)
                    if xValue == 0:
                        raise ValueError(u"invalid value")
                elif baseXsdType == u"XBRLI_DATEUNION":
                    xValue = dateTime(value, type=DATEUNION, castException=ValueError)
                    sValue = value
                elif baseXsdType == u"dateTime":
                    xValue = dateTime(value, type=DATETIME, castException=ValueError)
                    sValue = value
                elif baseXsdType == u"date":
                    xValue = dateTime(value, type=DATE, castException=ValueError)
                    sValue = value
                elif baseXsdType == u"regex-pattern":
                    # for facet compiling
                    try:
                        sValue = value
                        if value in xmlSchemaPatterns:
                            xValue = xmlSchemaPatterns[value]
                        else:
                            if ur"\i" in value or ur"\c" in value:
                                value = value.replace(ur"\i", iNameChar).replace(ur"\c", cNameChar)
                            xValue = re_compile(value + u"$") # must match whole string
                    except Exception, err:
                        raise ValueError(err)
                else:
                    if baseXsdType in lexicalPatterns:
                        match = lexicalPatterns[baseXsdType].match(value)
                        if match is None:
                            raise ValueError(u"lexical pattern mismatch")
                        if baseXsdType == u"gMonthDay":
                            month, day, zSign, zHrMin, zHr, zMin = match.groups()
                            if int(day) > {2:29, 4:30, 6:30, 9:30, 11:30, 1:31, 3:31, 5:31, 7:31, 8:31, 10:31, 12:31}[int(month)]:
                                raise ValueError(u"invalid day {0} for month {1}".format(day, month))
                            xValue = gMonthDay(month, day)
                        elif baseXsdType == u"gYearMonth":
                            year, month, zSign, zHrMin, zHr, zMin = match.groups()
                            xValue = gYearMonth(year, month)
                        elif baseXsdType == u"gYear":
                            year, zSign, zHrMin, zHr, zMin = match.groups()
                            xValue = gYear(year)
                        elif baseXsdType == u"gMonth":
                            month, zSign, zHrMin, zHr, zMin = match.groups()
                            xValue = gMonth(month)
                        elif baseXsdType == u"gDay":
                            day, zSign, zHrMin, zHr, zMin = match.groups()
                            xValue = gDay(day)
                        else:
                            xValue = value
                    else: # no lexical pattern, forget compiling value
                        xValue = value
                    sValue = value
        except (ValueError, InvalidOperation), err:
            if ModelInlineValueObject is not None and isinstance(elt, ModelInlineValueObject):
                errElt = u"{0} fact {1}".format(elt.elementQname, elt.qname)
            else:
                errElt = elt.elementQname
            if attrTag:
                modelXbrl.error(u"xmlSchema:valueError",
                    _(u"Element %(element)s attribute %(attribute)s type %(typeName)s value error: %(value)s, %(error)s"),
                    modelObject=elt,
                    element=errElt,
                    attribute=XmlUtil.clarkNotationToPrefixedName(elt,attrTag,isAttribute=True),
                    typeName=baseXsdType,
                    value=value if len(value) < 31 else value[:30] + u'...',
                    error=err)
            else:
                modelXbrl.error(u"xmlSchema:valueError",
                    _(u"Element %(element)s type %(typeName)s value error: %(value)s, %(error)s"),
                    modelObject=elt,
                    element=errElt,
                    typeName=baseXsdType,
                    value=value if len(value) < 31 else value[:30] + u'...',
                    error=err)
            xValue = None
            sValue = value
            xValid = INVALID
    else:
        xValue = sValue = None
        xValid = UNKNOWN
    if attrTag:
        try:  # dynamically allocate attributes (otherwise given shared empty set)
            xAttributes = elt.xAttributes
        except AttributeError:
            elt.xAttributes = xAttributes = {}
        xAttributes[attrTag] = ModelAttribute(elt, attrTag, xValid, xValue, sValue, value)
    else:
        elt.xValid = xValid
        elt.xValue = xValue
        elt.sValue = sValue

def validateFacet(typeElt, facetElt):
    facetName = facetElt.localName
    value = facetElt.get(u"value")
    if facetName in (u"length", u"minLength", u"maxLength", u"totalDigits", u"fractionDigits"):
        baseXsdType = u"integer"
        facets = None
    elif facetName in (u"minInclusive", u"maxInclusive", u"minExclusive", u"maxExclusive"):
        baseXsdType = typeElt.baseXsdType
        facets = None
    elif facetName == u"whiteSpace":
        baseXsdType = u"string"
        facets = {u"enumeration": set([u"replace",u"preserve",u"collapse"])}
    elif facetName == u"pattern":
        baseXsdType = u"regex-pattern"
        facets = None
    else:
        baseXsdType = u"string"
        facets = None
    validateValue(typeElt.modelXbrl, facetElt, None, baseXsdType, value, facets=facets)
    if facetElt.xValid == VALID:
        return facetElt.xValue
    return None

def validateAnyWildcard(qnElt, qnAttr, attributeWildcards):
    # note wildcard is a set of possibly multiple values from inherited attribute groups
    for attributeWildcard in attributeWildcards:
        if attributeWildcard.allowsNamespace(qnAttr.namespaceURI):
            return True
    return False