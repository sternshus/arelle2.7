u'''
Created on Sept 1, 2013

@author: Mark V Systems Limited
(c) Copyright 2013 Mark V Systems Limited, All rights reserved.

(originally part of XmlValidate, moved to separate module)
'''
from __future__ import with_statement
from arelle import XbrlConst, XmlUtil, XmlValidate
from arelle.ModelObject import ModelObject
from lxml import etree
import os, re
from io import open

ixAttrType = {
    XbrlConst.ixbrl: {
        u"arcrole": u"anyURI",
        u"contextRef": u"NCName",
        u"decimals": u"XBRLI_DECIMALSUNION",
        u"escape": u"boolean",
        u"footnoteID": u"NCName",
        u"footnoteLinkRole": u"anyURI",
        u"footnoteRefs": u"IDREFS",
        u"footnoteRole": u"anyURI",
        u"format": u"QName",
        u"id": u"NCName",
        u"name": u"QName",
        u"precision": u"XBRLI_PRECISIONUNION",
        u"order": u"decimal",
        u"scale": u"integer",
        u"sign": {u"type": u"string", u"pattern": re.compile(u"-$")},
        u"target": u"NCName",
        u"title": u"string",
        u"tupleID": u"NCName",
        u"tupleRef": u"NCName",
        u"unitRef": u"NCName"},
    XbrlConst.ixbrl11: {
        u"arcrole": u"anyURI",
        u"contextRef": u"NCName",
        u"continuedAt": u"NCName",
        u"decimals": u"XBRLI_DECIMALSUNION",
        u"escape": u"boolean",
        u"footnoteRole": u"anyURI",
        u"format": u"QName",
        u"fromRefs": u"IDREFS",
        u"id": u"NCName",
        u"linkRole": u"anyURI",
        u"name": u"QName",
        u"precision": u"XBRLI_PRECISIONUNION",
        u"order": u"decimal",
        u"scale": u"integer",
        u"sign": {u"type": u"string", u"pattern": re.compile(u"-$")},
        u"target": u"NCName",
        u"title": u"string",
        u"toRefs": u"IDREFS",
        u"tupleID": u"NCName",
        u"tupleRef": u"NCName",
        u"unitRef": u"NCName"}
    }
ixAttrRequired = {
    XbrlConst.ixbrl: {
        u"footnote": (u"footnoteID",),
        u"fraction": (u"name", u"contextRef", u"unitRef"),
        u"nonFraction": (u"name", u"contextRef", u"unitRef"),
        u"nonNumeric": (u"name", u"contextRef"),
        u"tuple": (u"name",)},
    XbrlConst.ixbrl11: {  
        u"continuation": (u"id",),
        u"footnote": (u"id",),
        u"fraction": (u"name", u"contextRef", u"unitRef"),
        u"nonFraction": (u"name", u"contextRef", u"unitRef"),
        u"nonNumeric": (u"name", u"contextRef"),
        u"tuple": (u"name",)}                    
    }
ixHierarchyConstraints = {
    # localName: (-rel means doesnt't have relation, +rel means has rel,
    #   &rel means only listed rels
    #   ^rel means must have one of listed rels and can't have any non-listed rels
    #   ?rel means 0 or 1 cardinality
    #   +rel means 1 or more cardinality
    u"continuation": ((u"-ancestor",(u"hidden",)),),
    u"exclude": ((u"+ancestor",(u"continuation", u"footnote", u"nonNumeric")),),
    u"denominator": ((u"-descendant",(u'*',)),),
    u"numerator": ((u"-descendant",(u'*',)),),
    u"header": ((u"&child", (u'hidden',u'references',u'resources')), # can only have these children, no others
               (u"?child", (u'hidden',)),
               (u"?child", (u'resources',))),
    u"hidden": ((u"+parent", (u"header",)),
               (u"&child", (u'footnote', u'fraction', u'nonFraction', u'nonNumeric', u'tuple')),
               (u"+child", (u'footnote', u'fraction', u'nonFraction', u'nonNumeric', u'tuple'))),
    u"references": ((u"+parent",(u"header",)),),
    u"relationship": ((u"+parent",(u"resources",)),),
    u"resources": ((u"+parent",(u"header",)),),
    u"tuple": ((u"-child",(u"continuation", u"exclude", u"denominator", u"footnote", u"numerator", u"header", u"hidden",
                         u"references", u"relationship", u"resources")),)
    }

def xhtmlValidate(modelXbrl, elt):
    from lxml.etree import DTD, XMLSyntaxError
    ixNsStartTags = [u"{" + ns + u"}" for ns in XbrlConst.ixbrlAll]
    
    def checkAttribute(elt, isIxElt, attrTag, attrValue):
        if attrTag.startswith(u"{"):
            ns, sep, localName = attrTag[1:].partition(u"}")
            if isIxElt:
                if ns not in (XbrlConst.xml, XbrlConst.xsi):
                    modelXbrl.error(u"ix:qualifiedAttributeNotExpected",
                        _(u"Inline XBRL element %(element)s: has qualified attribute %(name)s"),
                        modelObject=elt, element=unicode(elt.elementQname), name=attrTag)
            else:
                if ns in XbrlConst.ixbrlAll:
                    modelXbrl.error(u"ix:inlineAttributeMisplaced",
                        _(u"Inline XBRL attributes are not allowed on html elements: ix:%(name)s"),
                        modelObject=elt, name=localName)
                elif ns not in set([XbrlConst.xml, XbrlConst.xsi, XbrlConst.xhtml]):
                    modelXbrl.error(u"ix:extensionAttributeMisplaced",
                        _(u"Extension attributes are not allowed on html elements: %(tag)s"),
                        modelObject=elt, tag=attrTag)
        elif isIxElt:
            try:
                _xsdType = ixAttrType[elt.namespaceURI][attrTag]
                if isinstance(_xsdType, dict):
                    baseXsdType = _xsdType[u"type"]
                    facets = _xsdType
                else:
                    baseXsdType = _xsdType
                    facets = None
                XmlValidate.validateValue(modelXbrl, elt, attrTag, baseXsdType, attrValue, facets=facets)
                
                disallowedXbrliAttrs = (set([u"scheme", u"periodType", u"balance", u"contextRef", u"unitRef", u"precision", u"decimals"]) -
                                        {u"fraction": set([u"contextRef", u"unitRef"]),
                                         u"nonFraction": set([u"contextRef", u"unitRef", u"decimals", u"precision"]),
                                         u"nonNumeric": set([u"contextRef"])}.get(elt.localName, set()))
                disallowedAttrs = [a for a in disallowedXbrliAttrs if elt.get(a) is not None]
                if disallowedAttrs:
                    modelXbrl.error(u"ix:inlineElementAttributes",
                        _(u"Inline XBRL element %(element)s has disallowed attributes %(attributes)s"),
                        modelObject=elt, element=elt.elementQname, attributes=u", ".join(disallowedAttrs))
            except KeyError:
                modelXbrl.error(u"ix:attributeNotExpected",
                    _(u"Attribute %(attribute)s is not expected on element element ix:%(element)s"),
                    modelObject=elt, attribute=attrTag, element=elt.localName)
                
    def checkHierarchyConstraints(elt):
        constraints = ixHierarchyConstraints.get(elt.localName)
        if constraints:
            for _rel, names in constraints:
                reqt = _rel[0]
                rel = _rel[1:]
                if reqt in (u'&', u'^'):
                    nameFilter = (u'*',)
                else:
                    nameFilter = names
                relations = {u"ancestor": XmlUtil.ancestor, 
                             u"parent": XmlUtil.parent, 
                             u"child": XmlUtil.children, 
                             u"descendant": XmlUtil.descendants}[rel](
                            elt, 
                            u'*' if nameFilter == (u'*',) else elt.namespaceURI,
                            nameFilter)
                if rel in (u"ancestor", u"parent"):
                    if relations is None: relations = []
                    else: relations = [relations]
                issue = u''
                if reqt == u'^':
                    if not any(r.localName in names and r.namespaceURI == elt.namespaceURI
                               for r in relations):
                        issue = u" and is missing one of " + u', '.join(names)
                if reqt in (u'&', u'^'):
                    disallowed = [unicode(r.elementQname)
                                  for r in relations
                                  if r.localName not in names or r.namespaceURI != elt.namespaceURI]
                    if disallowed:
                        issue += u" and may not have " + u", ".join(disallowed)
                if reqt == u'?' and len(relations) > 1:
                    issue = u" may only have 0 or 1 but {0} present ".format(len(relations))
                if reqt == u'+' and len(relations) == 0:
                    issue = u" must have more than 1 but none present "
                if ((reqt == u'+' and not relations) or
                    (reqt == u'-' and relations) or
                    (issue)):
                    code = u"ix:" + {
                           u'ancestor': u"ancestorNode",
                           u'parent': u"parentNode",
                           u'child': u"childNodes",
                           u'descendant': u"descendantNodes"}[rel] + {
                            u'+': u"Required",
                            u'-': u"Disallowed",
                            u'&': u"Allowed",
                            u'^': u"Specified"}.get(reqt, u"Specified")
                    msg = _(u"Inline XBRL 1.0 ix:{0} {1} {2} {3} {4} element").format(
                                elt.localName,
                                {u'+': u"must", u'-': u"may not", u'&': u"may only",
                                 u'?': u"may", u'+': u"must"}[reqt],
                                {u'ancestor': u"be nested in",
                                 u'parent': u"have parent",
                                 u'child': u"have child",
                                 u'descendant': u"have as descendant"}[rel],
                                u', '.join(unicode(r.elementQname) for r in relations)
                                if names == (u'*',) and relations else
                                u", ".join(u"ix:" + n for n in names),
                                issue)
                    modelXbrl.error(code, msg, 
                                    modelObject=[elt] + relations, requirement=reqt)
                
    def ixToXhtml(fromRoot):
        toRoot = etree.Element(fromRoot.localName)
        copyNonIxChildren(fromRoot, toRoot)
        for attrTag, attrValue in fromRoot.items():
            checkAttribute(fromRoot, False, attrTag, attrValue)
            if attrTag not in (u'version', # used in inline test cases but not valid xhtml
                               u'{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'):
                toRoot.set(attrTag, attrValue)
        return toRoot

    def copyNonIxChildren(fromElt, toElt):
        for fromChild in fromElt.iterchildren():
            if isinstance(fromChild, ModelObject):
                isIxNs = fromChild.namespaceURI in XbrlConst.ixbrlAll
                if isIxNs:
                    checkHierarchyConstraints(fromChild)
                    for attrTag, attrValue in fromChild.items():
                        checkAttribute(fromChild, True, attrTag, attrValue)
                    for attrTag in ixAttrRequired[fromChild.namespaceURI].get(fromChild.localName,[]):
                        if fromChild.get(attrTag) is None:
                            modelXbrl.error(u"ix:attributeRequired",
                                _(u"Attribute %(attribute)s required on element ix:%(element)s"),
                                modelObject=elt, attribute=attrTag, element=fromChild.localName)
                if not (fromChild.localName in set([u"references", u"resources"]) and isIxNs):
                    if fromChild.localName in set([u"footnote", u"nonNumeric", u"continuation"]) and isIxNs:
                        toChild = etree.Element(u"ixNestedContent")
                        toElt.append(toChild)
                        copyNonIxChildren(fromChild, toChild)
                        if fromChild.text is not None:
                            toChild.text = fromChild.text
                        if fromChild.tail is not None:
                            toChild.tail = fromChild.tail
                    elif isIxNs:
                        copyNonIxChildren(fromChild, toElt)
                    else:
                        toChild = etree.Element(fromChild.localName)
                        toElt.append(toChild)
                        copyNonIxChildren(fromChild, toChild)
                        for attrTag, attrValue in fromChild.items():
                            checkAttribute(fromChild, False, attrTag, attrValue)
                            toChild.set(attrTag, attrValue)
                        if fromChild.text is not None:
                            toChild.text = fromChild.text
                        if fromChild.tail is not None:
                            toChild.tail = fromChild.tail    
                            
    # copy xhtml elements to fresh tree
    with open(os.path.join(modelXbrl.modelManager.cntlr.configDir, u"xhtml1-strict-ix.dtd")) as fh:
        dtd = DTD(fh)
    try:
        if not dtd.validate( ixToXhtml(elt) ):
            modelXbrl.error(u"xhmlDTD:elementUnexpected",
                _(u"%(element)s error %(error)s"),
                modelObject=elt, element=elt.localName.title(),
                error=u', '.join(e.message for e in dtd.error_log.filter_from_errors()))
    except XMLSyntaxError, err:
        modelXbrl.error(u"xmlDTD:error",
            _(u"%(element)s error %(error)s"),
            modelObject=elt, element=elt.localName.title(), error=dtd.error_log.filter_from_errors())

