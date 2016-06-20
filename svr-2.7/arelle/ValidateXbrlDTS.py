u'''
Created on Oct 17, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from arelle import (ModelDocument, ModelDtsObject, HtmlUtil, UrlUtil, XmlUtil, XbrlUtil, XbrlConst,
                    XmlValidate)
from arelle.ModelRelationshipSet import baseSetRelationship
from arelle.ModelObject import ModelObject, ModelComment
from arelle.ModelValue import qname
from lxml import etree
from arelle.PluginManager import pluginClassMethods
from collections import defaultdict
try:
    import regex as re
except ImportError:
    import re

instanceSequence = {u"schemaRef":1, u"linkbaseRef":2, u"roleRef":3, u"arcroleRef":4}
schemaTop = set([u"import", u"include", u"redefine"])
schemaBottom = set([u"element", u"attribute", u"notation", u"simpleType", u"complexType", u"group", u"attributeGroup"])
xsd1_1datatypes = set([qname(XbrlConst.xsd,u'anyAtomicType'), qname(XbrlConst.xsd,u'yearMonthDuration'), qname(XbrlConst.xsd,u'dayTimeDuration'), qname(XbrlConst.xsd,u'dateTimeStamp'), qname(XbrlConst.xsd,u'precisionDecimal')])
link_loc_spec_sections = {u"labelLink":u"5.2.2.1",
                          u"referenceLink":u"5.2.3.1",
                          u"calculationLink":u"5.2.5.1",
                          u"definitionLink":u"5.2.6.1",
                          u"presentationLink":u"5.2.4.1",
                          u"footnoteLink":u"4.11.1.1"}
standard_roles_for_ext_links = (u"xbrl.3.5.3", (XbrlConst.defaultLinkRole,))
standard_roles_definitions = {
    u"definitionLink": standard_roles_for_ext_links, 
    u"calculationLink": standard_roles_for_ext_links, 
    u"presentationLink": standard_roles_for_ext_links,
    u"labelLink": standard_roles_for_ext_links, 
    u"referenceLink": standard_roles_for_ext_links, 
    u"footnoteLink": standard_roles_for_ext_links,
    u"label": (u"xbrl.5.2.2.2.2", XbrlConst.standardLabelRoles),
    u"reference": (u"xbrl.5.2.3.2.1", XbrlConst.standardReferenceRoles),
    u"footnote": (u"xbrl.4.11.1.2", (XbrlConst.footnote,)),
    u"linkbaseRef": (u"xbrl.4.3.4", XbrlConst.standardLinkbaseRefRoles),
    u"loc": (u"xbrl.3.5.3.7", ())
    }
standard_roles_other = (u"xbrl.5.1.3", ())

inlineDisplayNonePattern = re.compile(ur"display\s*:\s*none")

def arcFromConceptQname(arcElement):
    modelRelationship = baseSetRelationship(arcElement)
    if modelRelationship is None:
        return arcElement.get(u"{http://www.w3.org/1999/xlink}from")
    else:
        return modelRelationship.fromModelObject.qname

def arcToConceptQname(arcElement):
    modelRelationship = baseSetRelationship(arcElement)
    if modelRelationship is None:
        return arcElement.get(u"{http://www.w3.org/1999/xlink}to")
    else:
        return modelRelationship.toModelObject.qname

def checkDTS(val, modelDocument, checkedModelDocuments):
    checkedModelDocuments.add(modelDocument)
    for referencedDocument in modelDocument.referencesDocument.keys():
        if referencedDocument not in checkedModelDocuments:
            checkDTS(val, referencedDocument, checkedModelDocuments)
            
    # skip processing versioning report here
    if modelDocument.type == ModelDocument.Type.VERSIONINGREPORT:
        return
    
    # skip processing if skipDTS requested
    if modelDocument.skipDTS:
        return
    
    # skip system schemas
    if modelDocument.type == ModelDocument.Type.SCHEMA:
        if XbrlConst.isStandardNamespace(modelDocument.targetNamespace):
            return
        val.hasLinkRole = val.hasLinkPart = val.hasContextFragment = val.hasAbstractItem = \
            val.hasTuple = val.hasNonAbstractElement = val.hasType = val.hasEnumeration = \
            val.hasDimension = val.hasDomain = val.hasHypercube = False

    
    # check for linked up hrefs
    isInstance = (modelDocument.type == ModelDocument.Type.INSTANCE or
                  modelDocument.type == ModelDocument.Type.INLINEXBRL)
    if modelDocument.type == ModelDocument.Type.INLINEXBRL:
        if not val.validateIXDS: # set up IXDS validation
            val.validateIXDS = True
            val.ixdsDocs = []
            val.ixdsFootnotes = {}
            val.ixdsHeaderCount = 0
            val.ixdsTuples = {}
            val.ixdsReferences = defaultdict(list)
            val.ixdsRelationships = []
        val.ixdsDocs.append(modelDocument)
        
    for hrefElt, hrefedDoc, hrefId in modelDocument.hrefObjects:
        hrefedElt = None
        if hrefedDoc is None:
            val.modelXbrl.error(u"xbrl:hrefFileNotFound",
                _(u"Href %(elementHref)s file not found"),
                modelObject=hrefElt, 
                elementHref=hrefElt.get(u"{http://www.w3.org/1999/xlink}href"))
        else:
            if hrefedDoc.type != ModelDocument.Type.UnknownNonXML:
                if hrefId:
                    if hrefId in hrefedDoc.idObjects:
                        hrefedElt = hrefedDoc.idObjects[hrefId]
                    else:
                        hrefedElt = XmlUtil.xpointerElement(hrefedDoc,hrefId)
                        if hrefedElt is None:
                            val.modelXbrl.error(u"xbrl.3.5.4:hrefIdNotFound",
                                _(u"Href %(elementHref)s not located"),
                                modelObject=hrefElt, 
                                elementHref=hrefElt.get(u"{http://www.w3.org/1999/xlink}href"))
                else:
                    hrefedElt = hrefedDoc.xmlRootElement
                
            if hrefId:  #check scheme regardless of whether document loaded 
                # check all xpointer schemes
                for scheme, path in XmlUtil.xpointerSchemes(hrefId):
                    if scheme != u"element":
                        val.modelXbrl.error(u"xbrl.3.5.4:hrefScheme",
                            _(u"Href %(elementHref)s unsupported scheme: %(scheme)s"),
                            modelObject=hrefElt, 
                            elementHref=hrefElt.get(u"{http://www.w3.org/1999/xlink}href"),
                            scheme=scheme)
                        break
                    elif val.validateDisclosureSystem:
                        val.modelXbrl.error((u"EFM.6.03.06", u"GFM.1.01.03"),
                            _(u"Href %(elementHref)s may only have shorthand xpointers"),
                            modelObject=hrefElt, 
                            elementHref=hrefElt.get(u"{http://www.w3.org/1999/xlink}href"))
            # check href'ed target if a linkbaseRef
            if hrefElt.namespaceURI == XbrlConst.link:
                if hrefElt.localName == u"linkbaseRef":
                    # check linkbaseRef target
                    if (hrefedDoc is None or
                        hrefedDoc.type < ModelDocument.Type.firstXBRLtype or  # range of doc types that can have linkbase
                        hrefedDoc.type > ModelDocument.Type.lastXBRLtype or
                        hrefedElt.namespaceURI != XbrlConst.link or hrefedElt.localName != u"linkbase"):
                        val.modelXbrl.error(u"xbrl.4.3.2:linkbaseRefHref",
                            _(u"LinkbaseRef %(linkbaseHref)s does not identify an link:linkbase element"),
                            modelObject=(hrefElt, hrefedDoc), 
                            linkbaseHref=hrefElt.get(u"{http://www.w3.org/1999/xlink}href"))
                    elif hrefElt.get(u"{http://www.w3.org/1999/xlink}role") is not None:
                        role = hrefElt.get(u"{http://www.w3.org/1999/xlink}role")
                        for linkNode in hrefedElt.iterchildren():
                            if (isinstance(linkNode,ModelObject) and
                                linkNode.get(u"{http://www.w3.org/1999/xlink}type") == u"extended"):
                                ln = linkNode.localName
                                ns = linkNode.namespaceURI
                                if (role == u"http://www.xbrl.org/2003/role/calculationLinkbaseRef" and \
                                    (ns != XbrlConst.link or ln != u"calculationLink")) or \
                                   (role == u"http://www.xbrl.org/2003/role/definitionLinkbaseRef" and \
                                    (ns != XbrlConst.link or ln != u"definitionLink")) or \
                                   (role == u"http://www.xbrl.org/2003/role/presentationLinkbaseRef" and \
                                    (ns != XbrlConst.link or ln != u"presentationLink")) or \
                                   (role == u"http://www.xbrl.org/2003/role/labelLinkbaseRef" and \
                                    (ns != XbrlConst.link or ln != u"labelLink")) or \
                                   (role == u"http://www.xbrl.org/2003/role/referenceLinkbaseRef" and \
                                    (ns != XbrlConst.link or ln != u"referenceLink")):
                                    val.modelXbrl.error(u"xbrl.4.3.4:linkbaseRefLinks",
                                        u"LinkbaseRef %(linkbaseHref)s role %(role)s has wrong extended link %(link)s",
                                        modelObject=hrefElt, 
                                        linkbaseHref=hrefElt.get(u"{http://www.w3.org/1999/xlink}href"),
                                        role=role, link=linkNode.prefixedName)
                elif hrefElt.localName == u"schemaRef":
                    # check schemaRef target
                    if (hrefedDoc.type != ModelDocument.Type.SCHEMA or
                        hrefedElt.namespaceURI != XbrlConst.xsd or hrefedElt.localName != u"schema"):
                        val.modelXbrl.error(u"xbrl.4.2.2:schemaRefHref",
                            _(u"SchemaRef %(schemaRef)s does not identify an xsd:schema element"),
                            modelObject=hrefElt, schemaRef=hrefElt.get(u"{http://www.w3.org/1999/xlink}href"))
                # check loc target 
                elif hrefElt.localName == u"loc":
                    linkElt = hrefElt.getparent()
                    if linkElt.namespaceURI ==  XbrlConst.link:
                        acceptableTarget = False
                        hrefEltKey = linkElt.localName
                        if hrefElt in val.remoteResourceLocElements:
                            hrefEltKey += u"ToResource"
                        for tgtTag in {
                                   u"labelLink":(u"{http://www.w3.org/2001/XMLSchema}element", u"{http://www.xbrl.org/2003/linkbase}label"),
                                   u"labelLinkToResource":(u"{http://www.xbrl.org/2003/linkbase}label",),
                                   u"referenceLink":(u"{http://www.w3.org/2001/XMLSchema}element", u"{http://www.xbrl.org/2003/linkbase}reference"),
                                   u"referenceLinkToResource":(u"{http://www.xbrl.org/2003/linkbase}reference",),
                                   u"calculationLink":(u"{http://www.w3.org/2001/XMLSchema}element",),
                                   u"definitionLink":(u"{http://www.w3.org/2001/XMLSchema}element",),
                                   u"presentationLink":(u"{http://www.w3.org/2001/XMLSchema}element",),
                                   u"footnoteLink":(u"XBRL-item-or-tuple",) }[hrefEltKey]:
                            if tgtTag == u"XBRL-item-or-tuple":
                                concept = val.modelXbrl.qnameConcepts.get(qname(hrefedElt))
                                acceptableTarget =  isinstance(concept, ModelDtsObject.ModelConcept) and \
                                                    (concept.isItem or concept.isTuple)
                            elif hrefedElt is not None and hrefedElt.tag == tgtTag:
                                acceptableTarget = True
                        if not acceptableTarget:
                            val.modelXbrl.error(u"xbrl.{0}:{1}LocTarget".format(
                                            {u"labelLink":u"5.2.2.1",
                                             u"referenceLink":u"5.2.3.1",
                                             u"calculationLink":u"5.2.5.1",
                                             u"definitionLink":u"5.2.6.1",
                                             u"presentationLink":u"5.2.4.1",
                                             u"footnoteLink":u"4.11.1.1"}[linkElt.localName],
                                             linkElt.localName),
                                 _(u"%(linkElement)s loc href %(locHref)s must identify a concept or label"),
                                 modelObject=hrefElt, linkElement=linkElt.localName,
                                 locHref=hrefElt.get(u"{http://www.w3.org/1999/xlink}href"),
                                 messageCodes=(u"xbrl.5.2.2.1:labelLinkLocTarget", u"xbrl.5.2.3.1:referenceLinkLocTarget", u"xbrl.5.2.5.1:calculationLinkLocTarget", u"xbrl.5.2.6.1:definitionLinkLocTarget", u"xbrl.5.2.4.1:presentationLinkLocTarget", u"xbrl.4.11.1.1:footnoteLinkLocTarget"))
                        if isInstance and not XmlUtil.isDescendantOf(hrefedElt, modelDocument.xmlRootElement):
                            val.modelXbrl.error(u"xbrl.4.11.1.1:instanceLoc",
                                _(u"Instance loc's href %(locHref)s not an element in same instance"),
                                 modelObject=hrefElt, locHref=hrefElt.get(u"{http://www.w3.org/1999/xlink}href"))
                    u''' is this ever needed???
                    else: # generic link or other non-2.1 link element
                        if (hrefElt.modelDocument.inDTS and 
                            ModelDocument.Type.firstXBRLtype <= hrefElt.modelDocument.type <= ModelDocument.Type.lastXBRLtype and # is a discovered linkbase
                            not ModelDocument.Type.firstXBRLtype <= hrefedDoc.type <= ModelDocument.Type.lastXBRLtype): # must discover schema or linkbase
                            val.modelXbrl.error("xbrl.3.2.3:linkLocTarget",
                                _("Locator %(xlinkLabel)s on link:loc in a discovered linkbase does not target a schema or linkbase"),
                                modelObject=(hrefedElt, hrefedDoc),
                                xlinkLabel=hrefElt.get("{http://www.w3.org/1999/xlink}label"))
                    '''
                    # non-standard link holds standard loc, href must be discovered document 
                    if (hrefedDoc.type < ModelDocument.Type.firstXBRLtype or  # range of doc types that can have linkbase
                        hrefedDoc.type > ModelDocument.Type.lastXBRLtype or
                        not hrefedDoc.inDTS):
                        val.modelXbrl.error(u"xbrl.3.5.3.7.2:instanceLocInDTS",
                            _(u"Loc's href %(locHref)s does not identify an element in an XBRL document discovered as part of the DTS"),
                            modelObject=hrefElt, locHref=hrefElt.get(u"{http://www.w3.org/1999/xlink}href"))

    # used in linkbase children navigation but may be errant linkbase elements                            
    val.roleRefURIs = {}
    val.arcroleRefURIs = {}
    val.elementIDs = set()
    val.annotationsCount = 0  
            
    # XML validation checks (remove if using validating XML)
    val.extendedElementName = None
    if (modelDocument.uri.startswith(val.modelXbrl.uriDir) and
        modelDocument.targetNamespace not in val.disclosureSystem.baseTaxonomyNamespaces and 
        modelDocument.xmlDocument):
        val.valUsedPrefixes = set()
        val.schemaRoleTypes = {}
        val.schemaArcroleTypes = {}
        val.referencedNamespaces = set()

        val.containsRelationship = False
        
        checkElements(val, modelDocument, modelDocument.xmlDocument)
        
        if (modelDocument.type == ModelDocument.Type.INLINEXBRL and 
            val.validateGFM and
            (val.documentTypeEncoding.lower() != u'utf-8' or val.metaContentTypeEncoding.lower() != u'utf-8')):
            val.modelXbrl.error(u"GFM.1.10.4",
                    _(u"XML declaration encoding %(encoding)s and meta content type encoding %(metaContentTypeEncoding)s must both be utf-8"),
                    modelXbrl=modelDocument, encoding=val.documentTypeEncoding, 
                    metaContentTypeEncoding=val.metaContentTypeEncoding)
        if val.validateSBRNL:
            for pluginXbrlMethod in pluginClassMethods(u"Validate.SBRNL.DTS.document"):
                pluginXbrlMethod(val, modelDocument)
        for pluginXbrlMethod in pluginClassMethods(u"Validate.XBRL.DTS.document"):
            pluginXbrlMethod(val, modelDocument)
        del val.valUsedPrefixes
        del val.schemaRoleTypes
        del val.schemaArcroleTypes

    val.roleRefURIs = None
    val.arcroleRefURIs = None
    val.elementIDs = None

def checkElements(val, modelDocument, parent):
    isSchema = modelDocument.type == ModelDocument.Type.SCHEMA
    if isinstance(parent, ModelObject):
        parentXlinkType = parent.get(u"{http://www.w3.org/1999/xlink}type")
        isInstance = parent.namespaceURI == XbrlConst.xbrli and parent.localName == u"xbrl"
        parentIsLinkbase = parent.namespaceURI == XbrlConst.link and parent.localName == u"linkbase"
        parentIsSchema = parent.namespaceURI == XbrlConst.xsd and parent.localName == u"schema"
        if isInstance or parentIsLinkbase:
            val.roleRefURIs = {}
            val.arcroleRefURIs = {}
        childrenIter = parent.iterchildren()
    else: # parent is document node, not an element
        parentXlinkType = None
        isInstance = False
        parentIsLinkbase = False
        childrenIter = (parent.getroot(),)
        if isSchema:
            val.inSchemaTop = True

    parentIsAppinfo = False
    if modelDocument.type == ModelDocument.Type.INLINEXBRL:
        if isinstance(parent,ModelObject): # element
            if (parent.localName == u"meta" and parent.namespaceURI == XbrlConst.xhtml and 
                (parent.get(u"http-equiv") or u"").lower() == u"content-type"):
                val.metaContentTypeEncoding = HtmlUtil.attrValue(parent.get(u"content"), u"charset")
        elif isinstance(parent,etree._ElementTree): # documentNode
            val.documentTypeEncoding = modelDocument.documentEncoding # parent.docinfo.encoding
            val.metaContentTypeEncoding = u""

    instanceOrder = 0
    if modelDocument.type == ModelDocument.Type.SCHEMA:
        ncnameTests = ((u"id",u"xbrl:xmlElementId"), 
                       (u"name",u"xbrl.5.1.1:conceptName"))
    else:
        ncnameTests = ((u"id",u"xbrl:xmlElementId"),)
    for elt in childrenIter:
        if isinstance(elt,ModelObject):
            for name, errCode in ncnameTests:
                if elt.get(name) is not None:
                    attrValue = elt.get(name)
                    u''' done in XmlValidate now
                    if not val.NCnamePattern.match(attrValue):
                        val.modelXbrl.error(errCode,
                            _("Element %(element)s attribute %(attribute)s '%(value)s' is not an NCname"),
                            modelObject=elt, element=elt.prefixedName, attribute=name, value=attrValue)
                    '''
                    if name == u"id" and attrValue in val.elementIDs:
                        val.modelXbrl.error(u"xmlschema2.3.2.10:idDuplicated",
                            _(u"Element %(element)s id %(value)s is duplicated"),
                            modelObject=elt, element=elt.prefixedName, attribute=name, value=attrValue)
                    val.elementIDs.add(attrValue)
                    
            # checks for elements in schemas only
            if isSchema:
                if elt.namespaceURI == XbrlConst.xsd:
                    localName = elt.localName
                    if localName == u"schema":
                        XmlValidate.validate(val.modelXbrl, elt)
                        targetNamespace = elt.get(u"targetNamespace")
                        if targetNamespace is not None:
                            if targetNamespace == u"":
                                val.modelXbrl.error(u"xbrl.5.1:emptyTargetNamespace",
                                    u"Schema element has an empty targetNamespace",
                                    modelObject=elt)
                            if val.validateEFM and len(targetNamespace) > 85:
                                l = len(targetNamespace.encode(u"utf-8"))
                                if l > 255:
                                    val.modelXbrl.error(u"EFM.6.07.30",
                                        _(u"Schema targetNamespace length (%(length)s) is over 255 bytes long in utf-8 %(targetNamespace)s"),
                                        modelObject=elt, length=l, targetNamespace=targetNamespace, value=targetNamespace)
                        if val.validateSBRNL:
                            if elt.get(u"targetNamespace") is None:
                                val.modelXbrl.error(u"SBR.NL.2.2.0.08",
                                    _(u'Schema element must have a targetNamespace attribute'),
                                    modelObject=elt)
                            if (elt.get(u"attributeFormDefault") != u"unqualified" or
                                elt.get(u"elementFormDefault") != u"qualified"):
                                val.modelXbrl.error(u"SBR.NL.2.2.0.09",
                                        _(u'Schema element attributeFormDefault must be "unqualified" and elementFormDefault must be "qualified"'),
                                        modelObject=elt)
                            for attrName in (u"blockDefault", u"finalDefault", u"version"):
                                if elt.get(attrName) is not None:
                                    val.modelXbrl.error(u"SBR.NL.2.2.0.10",
                                        _(u'Schema element must not have a %(attribute)s attribute'),
                                        modelObject=elt, attribute=attrName)
                    elif val.validateSBRNL:
                        if localName in (u"assert", u"openContent", u"fallback"):
                            val.modelXbrl.error(u"SBR.NL.2.2.0.01",
                                _(u'Schema contains XSD 1.1 content "%(element)s"'),
                                modelObject=elt, element=elt.qname)
                                                    
                        if localName == u"element":
                            for attr, presence, errCode in ((u"block", False, u"2.2.2.09"),
                                                            (u"final", False, u"2.2.2.10"),
                                                            (u"fixed", False, u"2.2.2.11"),
                                                            (u"form", False, u"2.2.2.12"),):
                                if (elt.get(attr) is not None) != presence:
                                    val.modelXbrl.error(u"SBR.NL.{0}".format(errCode),
                                        _(u'Schema element %(concept)s %(requirement)s contain attribute %(attribute)s'),
                                        modelObject=elt, concept=elt.get(u"name"), 
                                        requirement=(_(u"MUST NOT"),_(u"MUST"))[presence], attribute=attr,
                                        messageCodes=(u"SBR.NL.2.2.2.09", u"SBR.NL.2.2.2.10", u"SBR.NL.2.2.2.11", u"SBR.NL.2.2.2.12"))
                            eltName = elt.get(u"name")
                            if eltName is not None: # skip for concepts which are refs
                                type = qname(elt, elt.get(u"type"))
                                eltQname = elt.qname
                                if type in xsd1_1datatypes:
                                    val.modelXbrl.error(u"SBR.NL.2.2.0.01",
                                        _(u'Schema element %(concept)s contains XSD 1.1 datatype "%(xsdType)s"'),
                                        modelObject=elt, concept=elt.get(u"name"), xsdType=type)
                                if not parentIsSchema: # root element
                                    if elt.get(u"name") is not None and (elt.isItem or elt.isTuple):
                                        val.modelXbrl.error(u"SBR.NL.2.2.2.01",
                                            _(u'Schema concept definition is not at the root level: %(concept)s'),
                                            modelObject=elt, concept=elt.get(u"name"))
                                elif eltQname not in val.typedDomainQnames:
                                    for attr, presence, errCode in ((u"abstract", True, u"2.2.2.08"),
                                                                    (u"id", True, u"2.2.2.13"),
                                                                    (u"nillable", True, u"2.2.2.15"),
                                                                    (u"substitutionGroup", True, u"2.2.2.18"),):
                                        if (elt.get(attr) is not None) != presence:
                                            val.modelXbrl.error(u"SBR.NL.{0}".format(errCode),
                                                _(u'Schema root element %(concept)s %(requirement)s contain attribute %(attribute)s'),
                                                modelObject=elt, concept=elt.get(u"name"), 
                                                requirement=(_(u"MUST NOT"),_(u"MUST"))[presence], attribute=attr,
                                                messageCodes=(u"SBR.NL.2.2.2.08", u"SBR.NL.2.2.2.13", u"SBR.NL.2.2.2.15", u"SBR.NL.2.2.2.18"))
                                # semantic checks
                                if elt.isTuple:
                                    val.hasTuple = True
                                elif elt.isLinkPart:
                                    val.hasLinkPart = True
                                elif elt.isItem:
                                    if elt.isDimensionItem:
                                        val.hasDimension = True
                                    #elif elt.substitutesFor()
                                    if elt.isAbstract:
                                        val.hasAbstractItem = True
                                    else:
                                        val.hasNonAbstraceElement = True
                                if elt.isAbstract and elt.isItem:
                                    val.hasAbstractItem = True
                                if elt.typeQname is not None:
                                    val.referencedNamespaces.add(elt.typeQname.namespaceURI)
                                if elt.substitutionGroupQname is not None:
                                    val.referencedNamespaces.add(elt.substitutionGroupQname.namespaceURI)
                                if elt.isTypedDimension and elt.typedDomainElement is not None:
                                    val.referencedNamespaces.add(elt.typedDomainElement.namespaceURI)
                            else:
                                referencedElt = elt.dereference()
                                if referencedElt is not None:
                                    val.referencedNamespaces.add(referencedElt.modelDocument.targetNamespace)
                            if not parentIsSchema:
                                eltDecl = elt.dereference()
                                if (elt.get(u"minOccurs") is None or elt.get(u"maxOccurs") is None):
                                    val.modelXbrl.error(u"SBR.NL.2.2.2.14",
		                                _(u'Schema %(element)s must have minOccurs and maxOccurs'),
		                                modelObject=elt, element=eltDecl.qname)
                                elif elt.get(u"maxOccurs") != u"1" and eltDecl.isItem:
                                    val.modelXbrl.error(u"SBR.NL.2.2.2.30",
	                                    _(u"Tuple concept %(concept)s must have maxOccurs='1'"),
	                                    modelObject=elt, concept=eltDecl.qname)
                                if eltDecl.isItem and eltDecl.isAbstract:
                                    val.modelXbrl.error(u"SBR.NL.2.2.2.31",
                                        _(u"Abstract concept %(concept)s must not be a child of a tuple"),
	                                    modelObject=elt, concept=eltDecl.qname)
                        elif localName in (u"sequence",u"choice"):
                            for attrName in (u"minOccurs", u"maxOccurs"):
                                attrValue = elt.get(attrName)
                                if  attrValue is None:
                                    val.modelXbrl.error(u"SBR.NL.2.2.2.14",
		                                _(u'Schema %(element)s must have %(attrName)s'),
		                                modelObject=elt, element=elt.elementQname, attrName=attrName)
                                elif attrValue != u"1":
                                    val.modelXbrl.error(u"SBR.NL.2.2.2.33",
		                                _(u'Schema %(element)s must have %(attrName)s = "1"'),
		                                modelObject=elt, element=elt.elementQname, attrName=attrName)
                        elif localName in set([u"complexType",u"simpleType"]):
                            qnameDerivedFrom = elt.qnameDerivedFrom
                            if qnameDerivedFrom is not None:
                                if isinstance(qnameDerivedFrom, list): # union
                                    for qn in qnameDerivedFrom:
                                        val.referencedNamespaces.add(qn.namespaceURI)
                                else: # not union type
                                    val.referencedNamespaces.add(qnameDerivedFrom.namespaceURI)
                        elif localName == u"attribute":
                            if elt.typeQname is not None:
                                val.referencedNamespaces.add(elt.typeQname.namespaceURI)
                    if localName == u"redefine":
                        val.modelXbrl.error(u"xbrl.5.6.1:Redefine",
                            u"Redefine is not allowed",
                            modelObject=elt)
                    if localName in set([u"attribute", u"element", u"attributeGroup"]):
                        ref = elt.get(u"ref")
                        if ref is not None:
                            if qname(elt, ref) not in {u"attribute":val.modelXbrl.qnameAttributes, 
                                                       u"element":val.modelXbrl.qnameConcepts, 
                                                       u"attributeGroup":val.modelXbrl.qnameAttributeGroups}[localName]:
                                val.modelXbrl.error(u"xmlSchema:refNotFound",
                                    _(u"%(element)s ref %(ref)s not found"),
                                    modelObject=elt, element=localName, ref=ref)
                        if val.validateSBRNL and localName == u"attribute":
                            val.modelXbrl.error(u"SBR.NL.2.2.11.06",
                                _(u'xs:attribute must not be used'), modelObject=elt)
                        
                    if localName == u"appinfo":
                        if val.validateSBRNL:
                            if (parent.localName != u"annotation" or parent.namespaceURI != XbrlConst.xsd or
                                parent.getparent().localName != u"schema" or parent.getparent().namespaceURI != XbrlConst.xsd or
                                XmlUtil.previousSiblingElement(parent) != None):
                                val.modelXbrl.error(u"SBR.NL.2.2.0.12",
                                    _(u'Annotation/appinfo record must be be behind schema and before import'), modelObject=elt)
                            nextSiblingElement = XmlUtil.nextSiblingElement(parent)
                            if nextSiblingElement is not None and nextSiblingElement.localName != u"import":
                                val.modelXbrl.error(u"SBR.NL.2.2.0.14",
                                    _(u'Annotation/appinfo record must be followed only by import'),
                                    modelObject=elt)
                    if localName == u"annotation":
                        val.annotationsCount += 1
                        if val.validateSBRNL and not XmlUtil.hasChild(elt,XbrlConst.xsd,u"appinfo"):
                            val.modelXbrl.error(u"SBR.NL.2.2.0.12",
                                _(u'Schema file annotation missing appinfo element must be be behind schema and before import'),
                                modelObject=elt)
                        
                    if val.validateEFM and localName in set([u"element", u"complexType", u"simpleType"]):
                        name = elt.get(u"name")
                        if name and len(name) > 64:
                            l = len(name.encode(u"utf-8"))
                            if l > 200:
                                val.modelXbrl.error(u"EFM.6.07.29",
                                    _(u"Schema %(element)s has a name length (%(length)s) over 200 bytes long in utf-8, %(name)s."),
                                    modelObject=elt, element=localName, name=name, length=l)
    
                    if val.validateSBRNL and localName in set([u"all", u"documentation", u"any", u"anyAttribute", u"attributeGroup",
                                                                # comment out per R.H. 2011-11-16 "complexContent", "complexType", "extension", 
                                                                u"field", u"group", u"key", u"keyref",
                                                                u"list", u"notation", u"redefine", u"selector", u"unique"]):
                        val.modelXbrl.error(u"SBR.NL.2.2.11.{0:02}".format({u"all":1, u"documentation":2, u"any":3, u"anyAttribute":4, u"attributeGroup":7,
                                                                  u"complexContent":10, u"complexType":11, u"extension":12, u"field":13, u"group":14, u"key":15, u"keyref":16,
                                                                  u"list":17, u"notation":18, u"redefine":20, u"selector":22, u"unique":23}[localName]),
                            _(u'Schema file element must not be used "%(element)s"'),
                            modelObject=elt, element=elt.qname,
                            messageCodes=(u"SBR.NL.2.2.11.1", u"SBR.NL.2.2.11.2", u"SBR.NL.2.2.11.3", u"SBR.NL.2.2.11.4", u"SBR.NL.2.2.11.7", u"SBR.NL.2.2.11.10", u"SBR.NL.2.2.11.11", u"SBR.NL.2.2.11.12", 
                                          u"SBR.NL.2.2.11.13", u"SBR.NL.2.2.11.14", u"SBR.NL.2.2.11.15", u"SBR.NL.2.2.11.16", u"SBR.NL.2.2.11.17", u"SBR.NL.2.2.11.18", u"SBR.NL.2.2.11.20", u"SBR.NL.2.2.11.22", u"SBR.NL.2.2.11.23"))
                    if val.inSchemaTop:
                        if localName in schemaBottom:
                            val.inSchemaTop = False
                    elif localName in schemaTop:
                        val.modelXbrl.error(u"xmlschema.3.4.2:contentModel",
                            _(u"Element %(element)s is mis-located in schema file"),
                            modelObject=elt, element=elt.prefixedName)
                        
                # check schema roleTypes        
                if elt.localName in (u"roleType",u"arcroleType") and elt.namespaceURI == XbrlConst.link:
                    uriAttr, xbrlSection, roleTypes, localRoleTypes = {
                           u"roleType":(u"roleURI",u"5.1.3",val.modelXbrl.roleTypes, val.schemaRoleTypes), 
                           u"arcroleType":(u"arcroleURI",u"5.1.4",val.modelXbrl.arcroleTypes, val.schemaArcroleTypes)
                           }[elt.localName]
                    if not parent.localName == u"appinfo" and parent.namespaceURI == XbrlConst.xsd:
                        val.modelXbrl.error(u"xbrl.{0}:{1}Appinfo".format(xbrlSection,elt.localName),
                            _(u"%(element)s not child of xsd:appinfo"),
                            modelObject=elt, element=elt.qname,
                            messageCodes=(u"xbrl.5.1.3:roleTypeAppinfo", u"xbrl.5.1.4:arcroleTypeAppinfo"))
                    else: # parent is appinfo, element IS in the right location
                        XmlValidate.validate(val.modelXbrl, elt) # validate [arc]roleType
                        roleURI = elt.get(uriAttr)
                        if roleURI is None or not UrlUtil.isValid(roleURI):
                            val.modelXbrl.error(u"xbrl.{0}:{1}Missing".format(xbrlSection,uriAttr),
                                _(u"%(element)s missing or invalid %(attribute)s"),
                                modelObject=elt, element=elt.qname, attribute=uriAttr,
                                messageCodes=(u"xbrl.5.1.3:roleTypeMissing", u"xbrl.5.1.4:arcroleTypeMissing"))
                        if roleURI in localRoleTypes:
                            val.modelXbrl.error(u"xbrl.{0}:{1}Duplicate".format(xbrlSection,elt.localName),
                                _(u"Duplicate %(element)s %(attribute)s %(roleURI)s"),
                                modelObject=elt, element=elt.qname, attribute=uriAttr, roleURI=roleURI,
                                messageCodes=(u"xbrl.5.1.3:roleTypeDuplicate", u"xbrl.5.1.4:arcroleTypeDuplicate"))
                        else:
                            localRoleTypes[roleURI] = elt
                        for otherRoleType in roleTypes[roleURI]:
                            if elt != otherRoleType and not XbrlUtil.sEqual(val.modelXbrl, elt, otherRoleType):
                                val.modelXbrl.error(u"xbrl.{0}:{1}s-inequality".format(xbrlSection,elt.localName),
                                    _(u"%(element)s %(roleURI)s not s-equal in %(otherSchema)s"),
                                    modelObject=elt, element=elt.qname, roleURI=roleURI,
                                    otherSchema=otherRoleType.modelDocument.basename,
                                    messageCodes=(u"xbrl.5.1.3:roleTypes-inequality", u"xbrl.5.1.4:arcroleTypes-inequality"))
                        if elt.localName == u"arcroleType":
                            cycles = elt.get(u"cyclesAllowed")
                            if cycles not in (u"any", u"undirected", u"none"):
                                val.modelXbrl.error(u"xbrl.{0}:{1}CyclesAllowed".format(xbrlSection,elt.localName),
                                    _(u"%(element)s %(roleURI)s invalid cyclesAllowed %(value)s"),
                                    modelObject=elt, element=elt.qname, roleURI=roleURI, value=cycles,
                                    messageCodes=(u"xbrl.5.1.3:roleTypeCyclesAllowed", u"xbrl.5.1.4:arcroleTypeCyclesAllowed"))
                            if val.validateSBRNL:
                                val.modelXbrl.error(u"SBR.NL.2.2.4.01",
                                        _(u'ArcroleType is not allowed %(roleURI)s'),
                                        modelObject=elt, roleURI=roleURI)
                        else: # roleType
                            if val.validateSBRNL:
                                roleTypeModelObject = modelDocument.idObjects.get(elt.get(u"id"))
                                if roleTypeModelObject is not None and not roleTypeModelObject.genLabel(lang=u"nl"):
                                    val.modelXbrl.error(u"SBR.NL.2.3.8.05",
                                        _(u'RoleType %(roleURI)s must have a label in lang "nl"'),
                                        modelObject=elt, roleURI=roleURI)
                        if val.validateEFM and len(roleURI) > 85:
                            l = len(roleURI.encode(u"utf-8"))
                            if l > 255:
                                val.modelXbrl.error(u"EFM.6.07.30",
                                    _(u"Schema %(element)s %(attribute)s length (%(length)s) is over 255 bytes long in utf-8 %(roleURI)s"),
                                    modelObject=elt, element=elt.qname, attribute=uriAttr, length=l, roleURI=roleURI, value=roleURI)
                    # check for used on duplications
                    usedOns = set()
                    for usedOn in elt.iterdescendants(tag=u"{http://www.xbrl.org/2003/linkbase}usedOn"):
                        if isinstance(usedOn,ModelObject):
                            qName = qname(usedOn, XmlUtil.text(usedOn))
                            if qName not in usedOns:
                                usedOns.add(qName)
                            else:
                                val.modelXbrl.error(u"xbrl.{0}:{1}s-inequality".format(xbrlSection,elt.localName),
                                    _(u"%(element)s %(roleURI)s usedOn %(value)s on has s-equal duplicate"),
                                    modelObject=elt, element=elt.qname, roleURI=roleURI, value=qName,
                                    messageCodes=(u"xbrl.5.1.3:roleTypes-inequality", u"xbrl.5.1.4:arcroleTypes-inequality"))
                            if val.validateSBRNL:
                                val.valUsedPrefixes.add(qName.prefix)
                                if qName == XbrlConst.qnLinkCalculationLink:
                                    val.modelXbrl.error(u"SBR.NL.2.2.3.01",
                                        _(u"%(element)s usedOn must not be link:calculationLink"),
                                        modelObject=elt, element=parent.qname, value=qName)
                                if elt.localName == u"roleType" and qName in XbrlConst.standardExtLinkQnames:
                                    if not any((key[1] == roleURI  and key[2] == qName) 
                                               for key in val.modelXbrl.baseSets.keys()):
                                        val.modelXbrl.error(u"SBR.NL.2.2.3.02",
                                            _(u"%(element)s usedOn %(usedOn)s not addressed for role %(role)s"),
                                            modelObject=elt, element=parent.qname, usedOn=qName, role=roleURI)
                elif elt.localName == u"linkbase"  and elt.namespaceURI == XbrlConst.link:
                    XmlValidate.validate(val.modelXbrl, elt) # check linkbases inside schema files
                if val.validateSBRNL and not elt.prefix:
                        val.modelXbrl.error(u"SBR.NL.2.2.0.06",
                                u'Schema element is not prefixed: "%(element)s"',
                                modelObject=elt, element=elt.qname)
            elif modelDocument.type == ModelDocument.Type.LINKBASE:
                if elt.localName == u"linkbase":
                    XmlValidate.validate(val.modelXbrl, elt)
                if val.validateSBRNL and not elt.prefix:
                        val.modelXbrl.error(u"SBR.NL.2.2.0.06",
                            _(u'Linkbase element is not prefixed: "%(element)s"'),
                            modelObject=elt, element=elt.qname)
            # check of roleRefs when parent is linkbase or instance element
            xlinkType = elt.get(u"{http://www.w3.org/1999/xlink}type")
            xlinkRole = elt.get(u"{http://www.w3.org/1999/xlink}role")
            if elt.namespaceURI == XbrlConst.link:
                if elt.localName == u"linkbase":
                    if elt.parentQname is not None and elt.parentQname not in (XbrlConst.qnXsdAppinfo, XbrlConst.qnNsmap):
                        val.modelXbrl.error(u"xbrl.5.2:linkbaseRootElement",
                            u"Linkbase must be a root element or child of appinfo, and may not be nested in %(parent)s",
                            parent=elt.parentQname,
                            modelObject=elt)
                elif elt.localName in (u"roleRef",u"arcroleRef"):
                    uriAttr, xbrlSection, roleTypeDefs, refs = {
                           u"roleRef":(u"roleURI",u"3.5.2.4",val.modelXbrl.roleTypes,val.roleRefURIs), 
                           u"arcroleRef":(u"arcroleURI",u"3.5.2.5",val.modelXbrl.arcroleTypes,val.arcroleRefURIs)
                           }[elt.localName]
                    if parentIsAppinfo:
                        pass    #ignore roleTypes in appinfo (test case 160 v05)
                    elif not (parentIsLinkbase or isInstance or elt.parentQname == XbrlConst.qnIXbrlResources):
                        val.modelXbrl.info(u"info:{1}Location".format(xbrlSection,elt.localName),
                            _(u"Link:%(elementName)s not child of link:linkbase or xbrli:instance"),
                            modelObject=elt, elementName=elt.localName,
                            messageCodes=(u"info:roleRefLocation", u"info:arcroleRefLocation"))
                    else: # parent is linkbase or instance, element IS in the right location
        
                        # check for duplicate roleRefs when parent is linkbase or instance element
                        refUri = elt.get(uriAttr)
                        hrefAttr = elt.get(u"{http://www.w3.org/1999/xlink}href")
                        hrefUri, hrefId = UrlUtil.splitDecodeFragment(hrefAttr)
                        if refUri == u"":
                            val.modelXbrl.error(u"xbrl.3.5.2.4.5:{0}Missing".format(elt.localName),
                                _(u"%(element)s %(refURI)s missing"),
                                modelObject=elt, element=elt.qname, refURI=refUri,
                                messageCodes=(u"xbrl.3.5.2.4.5:roleRefMissing", u"xbrl.3.5.2.4.5:arcroleRefMissing"))
                        elif refUri in refs:
                            val.modelXbrl.error(u"xbrl.3.5.2.4.5:{0}Duplicate".format(elt.localName),
                                _(u"%(element)s is duplicated for %(refURI)s"),
                                modelObject=elt, element=elt.qname, refURI=refUri,
                                messageCodes=(u"xbrl.3.5.2.4.5:roleRefDuplicate", u"xbrl.3.5.2.4.5:arcroleRefDuplicate"))
                        elif refUri not in roleTypeDefs:
                            val.modelXbrl.error(u"xbrl.3.5.2.4.5:{0}NotDefined".format(elt.localName),
                                _(u"%(element)s %(refURI)s is not defined"),
                                modelObject=elt, element=elt.qname, refURI=refUri,
                                messageCodes=(u"xbrl.3.5.2.4.5:roleRefNotDefined", u"xbrl.3.5.2.4.5:arcroleRefNotDefined"))
                        else:
                            refs[refUri] = hrefUri
                            roleTypeElt = elt.resolveUri(uri=hrefAttr)
                            if roleTypeElt not in roleTypeDefs[refUri]:
                                val.modelXbrl.error(u"xbrl.3.5.2.4.5:{0}Mismatch".format(elt.localName),
                                    _(u"%(element)s %(refURI)s defined with different URI"),
                                    modelObject=(elt,roleTypeElt), element=elt.qname, refURI=refUri,
                                messageCodes=(u"xbrl.3.5.2.4.5:roleRefMismatch", u"xbrl.3.5.2.4.5:arcroleRefMismatch"))
                            
                        
                        if val.validateDisclosureSystem:
                            if elt.localName == u"arcroleRef":
                                if hrefUri not in val.disclosureSystem.standardTaxonomiesDict:
                                    val.modelXbrl.error((u"EFM.6.09.06", u"GFM.1.04.06"),
                                        _(u"Arcrole %(refURI)s arcroleRef %(xlinkHref)s must be a standard taxonomy"),
                                        modelObject=elt, refURI=refUri, xlinkHref=hrefUri)
                                if val.validateSBRNL:
                                    for attrName, errCode in ((u"{http://www.w3.org/1999/xlink}arcrole",u"SBR.NL.2.3.2.05"),(u"{http://www.w3.org/1999/xlink}role",u"SBR.NL.2.3.2.06")):
                                        if elt.get(attrName):
                                            val.modelXbrl.error(errCode,
                                                _(u"Arcrole %(refURI)s arcroleRef %(xlinkHref)s must not have an %(attribute)s attribute"),
                                                modelObject=elt, refURI=refUri, xlinkHref=hrefUri, attribute=attrName,
                                                messageCodes=(u"SBR.NL.2.3.2.05", u"SBR.NL.2.3.2.06"))
                            elif elt.localName == u"roleRef":
                                if val.validateSBRNL:
                                    for attrName, errCode in ((u"{http://www.w3.org/1999/xlink}arcrole",u"SBR.NL.2.3.10.09"),(u"{http://www.w3.org/1999/xlink}role",u"SBR.NL.2.3.10.10")):
                                        if elt.get(attrName):
                                            val.modelXbrl.error(errCode,
                                                _(u"Role %(refURI)s roleRef %(xlinkHref)s must not have an %(attribute)s attribute"),
                                                modelObject=elt, refURI=refUri, xlinkHref=hrefUri, attribute=attrName,
                                                messageCodes=(u"SBR.NL.2.3.10.09", u"SBR.NL.2.3.10.10"))
                    if val.validateSBRNL:
                        if not xlinkType:
                            val.modelXbrl.error(u"SBR.NL.2.3.0.01",
                                _(u"Xlink 1.1 simple type is not allowed (xlink:type is missing)"),
                                modelObject=elt)
    
            # checks for elements in linkbases
            if elt.namespaceURI == XbrlConst.link:
                if elt.localName in (u"schemaRef", u"linkbaseRef", u"roleRef", u"arcroleRef"):
                    if xlinkType != u"simple":
                        val.modelXbrl.error(u"xbrl.3.5.1.1:simpleLinkType",
                            _(u"Element %(element)s missing xlink:type=\"simple\""),
                            modelObject=elt, element=elt.qname)
                    href = elt.get(u"{http://www.w3.org/1999/xlink}href")
                    if not href or u"xpointer(" in href:
                        val.modelXbrl.error(u"xbrl.3.5.1.2:simpleLinkHref",
                            _(u"Element %(element)s missing or invalid href"),
                            modelObject=elt, element=elt.qname)
                    for name in (u"{http://www.w3.org/1999/xlink}role", u"{http://www.w3.org/1999/xlink}arcrole"):
                        if elt.get(name) == u"":
                            val.modelXbrl.error(u"xbrl.3.5.1.2:simpleLink" + name,
                                _(u"Element %(element)s has empty %(attribute)s"),
                                modelObject=elt, attribute=name,
                                messageCodes=(u"xbrl.3.5.1.2:simpleLink{http://www.w3.org/1999/xlink}role", u"xbrl.3.5.1.2:simpleLink{http://www.w3.org/1999/xlink}arcrole"))
                    if elt.localName == u"linkbaseRef" and \
                        elt.get(u"{http://www.w3.org/1999/xlink}arcrole") != XbrlConst.xlinkLinkbase:
                            val.modelXbrl.error(u"xbrl.4.3.3:linkbaseRefArcrole",
                                _(u"LinkbaseRef missing arcrole"),
                                modelObject=elt)
                elif elt.localName == u"loc":
                    if xlinkType != u"locator":
                        val.modelXbrl.error(u"xbrl.3.5.3.7.1:linkLocType",
                            _(u"Element %(element)s missing xlink:type=\"locator\""),
                            modelObject=elt, element=elt.qname)
                    for name, errName in ((u"{http://www.w3.org/1999/xlink}href",u"xbrl.3.5.3.7.2:linkLocHref"),
                                          (u"{http://www.w3.org/1999/xlink}label",u"xbrl.3.5.3.7.3:linkLocLabel")):
                        if elt.get(name) is None:
                            val.modelXbrl.error(errName,
                                _(u"Element %(element)s missing: %(attribute)s"),
                                modelObject=elt, element=elt.qname, attribute=name,
                                messageCodes=(u"xbrl.3.5.3.7.2:linkLocHref",u"xbrl.3.5.3.7.3:linkLocLabel"))
                elif xlinkType == u"resource":
                    if elt.localName == u"footnote" and elt.get(u"{http://www.w3.org/XML/1998/namespace}lang") is None:
                        val.modelXbrl.error(u"xbrl.4.11.1.2.1:footnoteLang",
                            _(u"Footnote %(xlinkLabel)s element missing xml:lang attribute"),
                            modelObject=elt, xlinkLabel=elt.get(u"{http://www.w3.org/1999/xlink}label"))
                    elif elt.localName == u"footnote" and elt.get(u"{http://www.w3.org/XML/1998/namespace}lang") is None:
                        val.modelXbrl.error(u"xbrl.5.2.2.2.1:labelLang",
                            _(u"Label %(xlinkLabel)s element missing xml:lang attribute"),
                            modelObject=elt, xlinkLabel=elt.get(u"{http://www.w3.org/1999/xlink}label"))
                    if val.validateSBRNL:
                        if elt.localName in (u"label", u"reference"):
                            if not XbrlConst.isStandardRole(xlinkRole):
                                val.modelXbrl.error(u"SBR.NL.2.3.10.13",
                                    _(u"Extended link %(element)s must have a standard xlink:role attribute (%(xlinkRole)s)"),
                                    modelObject=elt, element=elt.elementQname, xlinkRole=xlinkRole)
                        if elt.localName == u"reference": # look for custom reference parts
                            for linkPart in elt.iterchildren():
                                if linkPart.namespaceURI not in val.disclosureSystem.baseTaxonomyNamespaces:
                                    val.modelXbrl.error(u"SBR.NL.2.2.5.01",
                                        _(u"Link part %(element)s is not authorized"),
                                        modelObject=linkPart, element=linkPart.elementQname)
                    # TBD: add lang attributes content validation
            if xlinkRole is not None:
                if xlinkRole == u"" and xlinkType == u"simple":
                    val.modelXbrl.error(u"xbrl.3.5.1.3:emptySimpleLinkRole",
                        _(u"Simple link role %(xlinkRole)s is empty"),
                        modelObject=elt, xlinkRole=xlinkRole)
                elif xlinkRole == u"" and xlinkType == u"extended" and \
                     XbrlConst.isStandardResourceOrExtLinkElement(elt):
                    val.modelXbrl.error(u"xbrl.3.5.3.3:emptyStdExtLinkRole",
                        _(u"Standard extended link role %(xlinkRole)s is empty"),
                        modelObject=elt, xlinkRole=xlinkRole)
                elif not UrlUtil.isAbsolute(xlinkRole):
                    if XbrlConst.isStandardResourceOrExtLinkElement(elt):
                        val.modelXbrl.error(u"xbrl.3.5.2.4:roleNotAbsolute",
                            _(u"Role %(xlinkRole)s is not absolute"),
                            modelObject=elt, xlinkRole=xlinkRole)
                    elif val.isGenericLink(elt):
                        val.modelXbrl.error(u"xbrlgene:nonAbsoluteLinkRoleURI",
                            _(u"Generic link role %(xlinkRole)s is not absolute"),
                            modelObject=elt, xlinkRole=xlinkRole)
                    elif val.isGenericResource(elt):
                        val.modelXbrl.error(u"xbrlgene:nonAbsoluteResourceRoleURI",
                            _(u"Generic resource role %(xlinkRole)s is not absolute"),
                            modelObject=elt, xlinkRole=xlinkRole)
                elif XbrlConst.isStandardRole(xlinkRole):
                    if elt.namespaceURI == XbrlConst.link:
                        errCode, definedRoles = standard_roles_definitions.get(elt.localName, standard_roles_other)
                        if xlinkRole not in definedRoles:
                            val.modelXbrl.error(errCode,
                                _(u"Standard role %(xlinkRole)s is not defined for %(element)s"),
                                modelObject=elt, xlinkRole=xlinkRole, element=elt.qname,
                                messageCodes=(u"xbrl.5.2.2.2.2", u"xbrl.5.2.3.2.1", u"xbrl.4.11.1.2", u"xbrl.4.3.4", u"xbrl.3.5.3.7"))
                else:  # custom role
                    if xlinkRole not in val.roleRefURIs:
                        if XbrlConst.isStandardResourceOrExtLinkElement(elt):
                            val.modelXbrl.error(u"xbrl.3.5.2.4:missingRoleRef",
                                _(u"Role %(xlinkRole)s is missing a roleRef"),
                                modelObject=elt, xlinkRole=xlinkRole)
                        elif val.isGenericLink(elt):
                            val.modelXbrl.error(u"xbrlgene:missingRoleRefForLinkRole",
                                _(u"Generic link role %(xlinkRole)s is missing a roleRef"),
                                modelObject=elt, xlinkRole=xlinkRole)
                        elif val.isGenericResource(elt):
                            val.modelXbrl.error(u"xbrlgene:missingRoleRefForResourceRole",
                                _(u"Generic resource role %(xlinkRole)s is missing a roleRef"),
                                modelObject=elt, xlinkRole=xlinkRole)
                    modelsRole = val.modelXbrl.roleTypes.get(xlinkRole)
                    if modelsRole is None or len(modelsRole) == 0 or elt.qname not in modelsRole[0].usedOns:
                        if XbrlConst.isStandardResourceOrExtLinkElement(elt):
                            val.modelXbrl.error(u"xbrl.5.1.3.4:custRoleUsedOn",
                                _(u"Role %(xlinkRole)s missing usedOn for %(element)s"),
                                modelObject=elt, xlinkRole=xlinkRole, element=elt.qname)
                        elif val.isGenericLink(elt):
                            val.modelXbrl.error(u"xbrlgene:missingLinkRoleUsedOnValue",
                                _(u"Generic link role %(xlinkRole)s missing usedOn for {2}"),
                                modelObject=elt, xlinkRole=xlinkRole, element=elt.qname)
                        elif val.isGenericResource(elt):
                            val.modelXbrl.error(u"xbrlgene:missingResourceRoleUsedOnValue",
                                _(u"Generic resource role %(xlinkRole)s missing usedOn for %(element)s"),
                                modelObject=elt, xlinkRole=xlinkRole, element=elt.qname)
            elif xlinkType == u"extended" and val.validateSBRNL: # no @role on extended link
                val.modelXbrl.error(u"SBR.NL.2.3.10.13",
                    _(u"Extended link %(element)s must have an xlink:role attribute"),
                    modelObject=elt, element=elt.elementQname)
            if elt.get(u"{http://www.w3.org/1999/xlink}arcrole") is not None:
                arcrole = elt.get(u"{http://www.w3.org/1999/xlink}arcrole")
                if arcrole == u"" and \
                    elt.get(u"{http://www.w3.org/1999/xlink}type") == u"simple":
                    val.modelXbrl.error(u"xbrl.3.5.1.4:emptyXlinkArcrole",
                        _(u"Arcrole on %(element)s is empty"),
                        modelObject=elt, element=elt.qname)
                elif not UrlUtil.isAbsolute(arcrole):
                    if XbrlConst.isStandardArcInExtLinkElement(elt):
                        val.modelXbrl.error(u"xbrl.3.5.2.5:arcroleNotAbsolute",
                            _(u"Arcrole %(arcrole)s is not absolute"),
                            modelObject=elt, element=elt.qname, arcrole=arcrole)
                    elif val.isGenericArc(elt):
                        val.modelXbrl.error(u"xbrlgene:nonAbsoluteArcRoleURI",
                            _(u"Generic arc arcrole %(arcrole)s is not absolute"),
                            modelObject=elt, element=elt.qname, arcrole=arcrole)
                elif not XbrlConst.isStandardArcrole(arcrole):
                    if arcrole not in val.arcroleRefURIs:
                        if XbrlConst.isStandardArcInExtLinkElement(elt):
                            val.modelXbrl.error(u"xbrl.3.5.2.5:missingArcroleRef",
                                _(u"Arcrole %(arcrole)s is missing an arcroleRef"),
                                modelObject=elt, element=elt.qname, arcrole=arcrole)
                        elif val.isGenericArc(elt):
                            val.modelXbrl.error(u"xbrlgene:missingRoleRefForArcRole",
                                _(u"Generic arc arcrole %(arcrole)s is missing an arcroleRef"),
                                modelObject=elt, element=elt.qname, arcrole=arcrole)
                    modelsRole = val.modelXbrl.arcroleTypes.get(arcrole)
                    if modelsRole is None or len(modelsRole) == 0 or elt.qname not in modelsRole[0].usedOns:
                        if XbrlConst.isStandardArcInExtLinkElement(elt):
                            val.modelXbrl.error(u"xbrl.5.1.4.5:custArcroleUsedOn",
                                _(u"Arcrole %(arcrole)s missing usedOn for %(element)s"),
                                modelObject=elt, element=elt.qname, arcrole=arcrole)
                        elif val.isGenericArc(elt):
                            val.modelXbrl.error(u"xbrlgene:missingArcRoleUsedOnValue",
                                _(u"Generic arc arcrole %(arcrole)s missing usedOn for %(element)s"),
                                modelObject=elt, element=elt.qname, arcrole=arcrole)
                elif XbrlConst.isStandardArcElement(elt):
                    if XbrlConst.standardArcroleArcElement(arcrole) != elt.localName:
                        val.modelXbrl.error(u"xbrl.5.1.4.5:custArcroleUsedOn",
                            _(u"XBRL file {0} standard arcrole %(arcrole)s used on wrong arc %(element)s"),
                            modelObject=elt, element=elt.qname, arcrole=arcrole)
    
            #check resources
            if parentXlinkType == u"extended":
                if elt.localName not in (u"documentation", u"title") and \
                    xlinkType not in (u"arc", u"locator", u"resource"):
                    val.modelXbrl.error(u"xbrl.3.5.3.8.1:resourceType",
                        _(u"Element %(element)s appears to be a resource missing xlink:type=\"resource\""),
                        modelObject=elt, element=elt.qname)
                elif (xlinkType == u"locator" and elt.namespaceURI != XbrlConst.link and 
                      parent.namespaceURI == XbrlConst.link and parent.localName in link_loc_spec_sections): 
                    val.modelXbrl.error(u"xbrl.{0}:customLocator".format(link_loc_spec_sections[parent.localName]),
                        _(u"Element %(element)s is a custom locator in a standard %(link)s"),
                        modelObject=(elt,parent), element=elt.qname, link=parent.qname,
                        messageCodes=(u"xbrl.5.2.2.1:customLocator", u"xbrl.5.2.3.1:customLocator", u"xbrl.5.2.5.1:customLocator", u"xbrl.5.2.6.1:customLocator", u"xbrl.5.2.4.1:customLocator", u"xbrl.4.11.1.1:customLocator"))
                
            if xlinkType == u"resource":
                if not elt.get(u"{http://www.w3.org/1999/xlink}label"):
                    val.modelXbrl.error(u"xbrl.3.5.3.8.2:resourceLabel",
                        _(u"Element %(element)s missing xlink:label"),
                        modelObject=elt, element=elt.qname)
            elif xlinkType == u"arc":
                for name, errName in ((u"{http://www.w3.org/1999/xlink}from", u"xbrl.3.5.3.9.2:arcFrom"),
                                      (u"{http://www.w3.org/1999/xlink}to", u"xbrl.3.5.3.9.2:arcTo")):
                    if not elt.get(name):
                        val.modelXbrl.error(errName,
                            _(u"Element %(element)s missing xlink:%(attribute)s"),
                            modelObject=elt, element=elt.qname, attribute=name,
                            messageCodes=(u"xbrl.3.5.3.9.2:arcFrom", u"xbrl.3.5.3.9.2:arcTo"))
                if val.modelXbrl.hasXDT and elt.get(u"{http://xbrl.org/2005/xbrldt}targetRole") is not None:
                    targetRole = elt.get(u"{http://xbrl.org/2005/xbrldt}targetRole")
                    if not XbrlConst.isStandardRole(targetRole) and \
                       elt.qname == XbrlConst.qnLinkDefinitionArc and \
                       targetRole not in val.roleRefURIs:
                        val.modelXbrl.error(u"xbrldte:TargetRoleNotResolvedError",
                            _(u"TargetRole %(targetRole)s is missing a roleRef"),
                            modelObject=elt, element=elt.qname, targetRole=targetRole)
                val.containsRelationship = True
            xmlLang = elt.get(u"{http://www.w3.org/XML/1998/namespace}lang")
            if val.validateXmlLang and xmlLang is not None:
                if not val.disclosureSystem.xmlLangPattern.match(xmlLang):
                    val.modelXbrl.error(u"SBR.NL.2.3.8.01" if (val.validateSBRNL and xmlLang.startswith(u'nl')) else u"SBR.NL.2.3.8.02" if (val.validateSBRNL and xmlLang.startswith(u'en')) else u"arelle:langError",
                        _(u"Element %(element)s %(xlinkLabel)s has unauthorized xml:lang='%(lang)s'"),
                        modelObject=elt, element=elt.qname,
                        xlinkLabel=elt.get(u"{http://www.w3.org/1999/xlink}label"),
                        lang=elt.get(u"{http://www.w3.org/XML/1998/namespace}lang"),
                        messageCodes=(u"SBR.NL.2.3.8.01", u"SBR.NL.2.3.8.02", u"arelle:langError"))
                 
            if isInstance:
                if elt.namespaceURI == XbrlConst.xbrli:
                    expectedSequence = instanceSequence.get(elt.localName,9)
                else:
                    expectedSequence = 9    #itdms last
                if instanceOrder > expectedSequence:
                    val.modelXbrl.error(u"xbrl.4.7:instanceElementOrder",
                        _(u"Element %(element)s is out of order"),
                        modelObject=elt, element=elt.qname)
                else:
                    instanceOrder = expectedSequence

            if modelDocument.type == ModelDocument.Type.UnknownXML:
                if elt.localName == u"xbrl" and elt.namespaceURI == XbrlConst.xbrli:
                    if elt.getparent() is not None:
                        val.modelXbrl.error(u"xbrl.4:xbrlRootElement",
                            u"Xbrl must be a root element, and may not be nested in %(parent)s",
                            parent=elt.parentQname,
                            modelObject=elt)
                elif elt.localName == u"schema" and elt.namespaceURI == XbrlConst.xsd:
                    if elt.getparent() is not None:
                        val.modelXbrl.error(u"xbrl.5.1:schemaRootElement",
                            u"Schema must be a root element, and may not be nested in %(parent)s",
                            parent=elt.parentQname,
                            modelObject=elt)
                    
            if modelDocument.type == ModelDocument.Type.INLINEXBRL and elt.namespaceURI in XbrlConst.ixbrlAll: 
                if elt.localName == u"footnote":
                    if val.validateGFM:
                        if elt.get(u"{http://www.w3.org/1999/xlink}arcrole") != XbrlConst.factFootnote:
                            # must be in a nonDisplay div
                            if not any(inlineDisplayNonePattern.search(e.get(u"style") or u"")
                                       for e in XmlUtil.ancestors(elt, XbrlConst.xhtml, u"div")):
                                val.modelXbrl.error((u"EFM.N/A", u"GFM:1.10.16"),
                                    _(u"Inline XBRL footnote %(footnoteID)s must be in non-displayable div due to arcrole %(arcrole)s"),
                                    modelObject=elt, footnoteID=elt.get(u"footnoteID"), 
                                    arcrole=elt.get(u"{http://www.w3.org/1999/xlink}arcrole"))
                            
                        if not elt.get(u"{http://www.w3.org/XML/1998/namespace}lang"):
                            val.modelXbrl.error((u"EFM.N/A", u"GFM:1.10.13"),
                                _(u"Inline XBRL footnote %(footnoteID)s is missing an xml:lang attribute"),
                                modelObject=elt, footnoteID=id)
                    if elt.namespaceURI == XbrlConst.ixbrl:
                        val.ixdsFootnotes[elt.footnoteID] = elt
                    else:
                        checkIxContinuationChain(elt)  
                    if not elt.xmlLang:
                        val.modelXbrl.error(u"ix:footnoteID",
                            _(u"Inline XBRL footnotes require an in-scope xml:lang"),
                            modelObject=elt)
                elif elt.localName == u"fraction":
                    ixDescendants = XmlUtil.descendants(elt, elt.namespaceURI, u'*')
                    wrongDescendants = [d
                                        for d in ixDescendants
                                        if d.localName not in (u'numerator',u'denominator',u'fraction')]
                    if wrongDescendants:
                        val.modelXbrl.error(u"ix:fractionDescendants",
                            _(u"Inline XBRL fraction may only contain ix:numerator, ix:denominator, or ix:fraction, but contained %(wrongDescendants)s"),
                            modelObject=[elt] + wrongDescendants, wrongDescendants=u", ".join(unicode(d.elementQname) for d in wrongDescendants))
                    ixDescendants = XmlUtil.descendants(elt, elt.namespaceURI, (u'numerator',u'denominator'))
                    if not elt.isNil:
                        if set(d.localName for d in ixDescendants) != set([u'numerator',u'denominator']):
                            val.modelXbrl.error(u"ix:fractionTerms",
                                _(u"Inline XBRL fraction must have one ix:numerator and one ix:denominator when not nil"),
                                modelObject=[elt] + ixDescendants)
                    elif ixDescendants: # nil and has fraction term elements
                        val.modelXbrl.error(u"ix:fractionNilTerms",
                            _(u"Inline XBRL fraction must not have ix:numerator or ix:denominator when nil"),
                            modelObject=[elt] + ixDescendants)
                elif elt.localName in (u"denominator", u"numerator"):
                    wrongDescendants = [d for d in XmlUtil.descendants(elt, u'*', u'*')]
                    if wrongDescendants:
                        val.modelXbrl.error(u"ix:fractionTermDescendants",
                            _(u"Inline XBRL fraction term ix:%(name)s may only contain text nodes, but contained %(wrongDescendants)s"),
                            modelObject=[elt] + wrongDescendants, name=elt.localName, wrongDescendants=u", ".join(unicode(d.elementQname) for d in wrongDescendants))
                    if elt.get(u"format") is None and u'-' in XmlUtil.innerText(elt):
                        val.modelXbrl.error(u"ix:fractionTermNegative",
                            _(u"Inline XBRL ix:numerator or ix:denominator without format attribute must be non-negative"),
                            modelObject=elt)
                elif elt.localName == u"header":
                    if not any(inlineDisplayNonePattern.search(e.get(u"style") or u"")
                               for e in XmlUtil.ancestors(elt, XbrlConst.xhtml, u"div")):
                        val.modelXbrl.warning(u"ix:headerDisplayNone",
                            _(u"Warning, Inline XBRL ix:header is recommended to be nested in a <div> with style display:none"),
                            modelObject=elt)
                    val.ixdsHeaderCount += 1
                elif elt.localName == u"nonFraction":
                    if elt.isNil:
                        e2 = XmlUtil.ancestor(elt, elt.namespaceURI, u"nonFraction")
                        if e2 is not None:
                            val.modelXbrl.error(u"ix:nestedNonFractionIsNil",
                                _(u"Inline XBRL nil ix:nonFraction may not have an ancestor ix:nonFraction"),
                                modelObject=(elt,e2))
                    else:
                        d = XmlUtil.descendants(elt, u'*', u'*')
                        if d and (len(d) != 1 or d[0].namespaceURI != elt.namespaceURI or d[0].localName != u"nonFraction"):
                            val.modelXbrl.error(u"ix:nonFractionChildren",
                                _(u"Inline XBRL nil ix:nonFraction may only have on child ix:nonFraction"),
                                modelObject=[elt] + d)
                        for e in d:
                            if (e.namespaceURI == elt.namespaceURI and e.localName == u"nonFraction" and
                                (e.format != elt.format or e.scale != elt.scale or e.unitID != elt.unitID)):
                                val.modelXbrl.error(u"ix:nestedNonFractionProperties",
                                    _(u"Inline XBRL nested ix:nonFraction must have matching format, scale, and unitRef properties"),
                                    modelObject=(elt, e))
                    if elt.get(u"format") is None and u'-' in XmlUtil.innerText(elt):
                        val.modelXbrl.error(u"ix:nonFractionNegative",
                            _(u"Inline XBRL ix:nonFraction without format attribute must be non-negative"),
                            modelObject=elt)
                elif elt.localName == u"nonNumeric":
                    checkIxContinuationChain(elt)
                elif elt.localName == u"references":
                    val.ixdsReferences[elt.get(u"target")].append(elt)
                elif elt.localName == u"relationship":
                    val.ixdsRelationships.append(elt)
                elif elt.localName == u"tuple":
                    if not elt.tupleID:
                        if not elt.isNil:
                            if not XmlUtil.descendants(elt, elt.namespaceURI, (u"fraction", u"nonFraction", u"nonNumeric",  u"tuple")):
                                val.modelXbrl.error(u"ix:tupleID",
                                    _(u"Inline XBRL non-nil tuples without ix:fraction, ix:nonFraction, ix:nonNumeric or ix:tuple descendants require a tupleID"),
                                    modelObject=elt)
                    else:
                        val.ixdsTuples[elt.tupleID] = elt
            if val.validateDisclosureSystem:
                if xlinkType == u"extended":
                    if not xlinkRole or xlinkRole == u"":
                        val.modelXbrl.error((u"EFM.6.09.04", u"GFM.1.04.04"),
                            u"%(element)s is missing an xlink:role",
                            modelObject=elt, element=elt.qname)
                    eltNsName = (elt.namespaceURI,elt.localName)
                    if not val.extendedElementName:
                        val.extendedElementName = elt.qname
                    elif val.extendedElementName != elt.qname:
                        val.modelXbrl.error((u"EFM.6.09.07", u"GFM:1.04.07", u"SBR.NL.2.3.0.11"),
                            _(u"Extended element %(element)s must be the same as %(element2)s"),
                            modelObject=elt, element=elt.qname, element2=val.extendedElementName)
                if xlinkType == u"locator":
                    if val.validateSBRNL and elt.qname != XbrlConst.qnLinkLoc:
                        val.modelXbrl.error(u"SBR.NL.2.3.0.11",
                            _(u"Loc element %(element)s may not be contained in a linkbase with %(element2)s"),
                            modelObject=elt, element=elt.qname, element2=val.extendedElementName)
                if xlinkType == u"resource":
                    if not xlinkRole:
                        val.modelXbrl.error((u"EFM.6.09.04", u"GFM.1.04.04"),
                            _(u"%(element)s is missing an xlink:role"),
                            modelObject=elt, element=elt.qname)
                    elif not XbrlConst.isStandardRole(xlinkRole):
                        modelsRole = val.modelXbrl.roleTypes.get(xlinkRole)
                        if (modelsRole is None or len(modelsRole) == 0 or 
                            modelsRole[0].modelDocument.targetNamespace not in val.disclosureSystem.standardTaxonomiesDict):
                            val.modelXbrl.error((u"EFM.6.09.05", u"GFM.1.04.05", u"SBR.NL.2.3.10.14"),
                                _(u"Resource %(xlinkLabel)s role %(role)s is not a standard taxonomy role"),
                                modelObject=elt, xlinkLabel=elt.get(u"{http://www.w3.org/1999/xlink}label"), role=xlinkRole, element=elt.qname,
                                roleDefinition=val.modelXbrl.roleTypeDefinition(xlinkRole))
                    if val.validateSBRNL:
                        if elt.localName == u"reference":
                            for child in elt.iterdescendants():
                                if isinstance(child,ModelObject) and child.namespaceURI.startswith(u"http://www.xbrl.org") and child.namespaceURI != u"http://www.xbrl.org/2006/ref":
                                    val.modelXbrl.error(u"SBR.NL.2.3.3.01",
                                        _(u"Reference %(xlinkLabel)s has unauthorized part element %(element)s"),
                                        modelObject=elt, xlinkLabel=elt.get(u"{http://www.w3.org/1999/xlink}label"), 
                                        element=qname(child))
                            id = elt.get(u"id")
                            if not id:
                                val.modelXbrl.error(u"SBR.NL.2.3.3.02",
                                    _(u"Reference %(xlinkLabel)s is missing an id attribute"),
                                    modelObject=elt, xlinkLabel=elt.get(u"{http://www.w3.org/1999/xlink}label"))
                            elif id in val.DTSreferenceResourceIDs:
                                val.modelXbrl.error(u"SBR.NL.2.3.3.03",
                                    _(u"Reference %(xlinkLabel)s has duplicated id %(id)s also in linkbase %(otherLinkbase)s"),
                                    modelObject=elt, xlinkLabel=elt.get(u"{http://www.w3.org/1999/xlink}label"),
                                    id=id, otherLinkbase=val.DTSreferenceResourceIDs[id])
                            else:
                                val.DTSreferenceResourceIDs[id] = modelDocument.basename
                        if elt.qname not in {
                            XbrlConst.qnLinkLabelLink: (XbrlConst.qnLinkLabel,),
                            XbrlConst.qnLinkReferenceLink: (XbrlConst.qnLinkReference,),
                            XbrlConst.qnLinkPresentationLink: tuple(),
                            XbrlConst.qnLinkCalculationLink: tuple(),
                            XbrlConst.qnLinkDefinitionLink: tuple(),
                            XbrlConst.qnLinkFootnoteLink: (XbrlConst.qnLinkFootnote,),
                            # XbrlConst.qnGenLink: (XbrlConst.qnGenLabel, XbrlConst.qnGenReference, val.qnSbrLinkroleorder),
                             }.get(val.extendedElementName,(elt.qname,)):  # allow non-2.1 to be ok regardless per RH 2013-03-13
                            val.modelXbrl.error(u"SBR.NL.2.3.0.11",
                                _(u"Resource element %(element)s may not be contained in a linkbase with %(element2)s"),
                                modelObject=elt, element=elt.qname, element2=val.extendedElementName)
                if xlinkType == u"arc":
                    if elt.get(u"priority") is not None:
                        priority = elt.get(u"priority")
                        try:
                            if int(priority) >= 10:
                                val.modelXbrl.error((u"EFM.6.09.09", u"GFM.1.04.08"),
                                    _(u"Arc from %(xlinkFrom)s to %(xlinkTo)s priority %(priority)s must be less than 10"),
                                    modelObject=elt, 
                                    arcElement=elt.qname,
                                    xlinkFrom=elt.get(u"{http://www.w3.org/1999/xlink}from"),
                                    xlinkTo=elt.get(u"{http://www.w3.org/1999/xlink}to"),
                                    priority=priority)
                        except (ValueError) :
                            val.modelXbrl.error((u"EFM.6.09.09", u"GFM.1.04.08"),
                                _(u"Arc from %(xlinkFrom)s to %(xlinkTo)s priority %(priority)s is not an integer"),
                                modelObject=elt, 
                                arcElement=elt.qname,
                                xlinkFrom=elt.get(u"{http://www.w3.org/1999/xlink}from"),
                                xlinkTo=elt.get(u"{http://www.w3.org/1999/xlink}to"),
                                priority=priority)
                    if elt.namespaceURI == XbrlConst.link:
                        if elt.localName == u"presentationArc" and not elt.get(u"order"):
                            val.modelXbrl.error((u"EFM.6.12.01", u"GFM.1.06.01", u"SBR.NL.2.3.4.04"),
                                _(u"PresentationArc from %(xlinkFrom)s to %(xlinkTo)s must have an order"),
                                modelObject=elt, 
                                xlinkFrom=elt.get(u"{http://www.w3.org/1999/xlink}from"),
                                xlinkTo=elt.get(u"{http://www.w3.org/1999/xlink}to"),
                                conceptFrom=arcFromConceptQname(elt),
                                conceptTo=arcToConceptQname(elt))
                        elif elt.localName == u"calculationArc":
                            if not elt.get(u"order"):
                                val.modelXbrl.error((u"EFM.6.14.01", u"GFM.1.07.01"),
                                    _(u"CalculationArc from %(xlinkFrom)s to %(xlinkTo)s must have an order"),
                                    modelObject=elt, 
                                    xlinkFrom=elt.get(u"{http://www.w3.org/1999/xlink}from"),
                                    xlinkTo=elt.get(u"{http://www.w3.org/1999/xlink}to"),
                                    conceptFrom=arcFromConceptQname(elt),
                                    conceptTo=arcToConceptQname(elt))
                            try:
                                weightAttr = elt.get(u"weight")
                                weight = float(weightAttr)
                                if not weight in (1, -1):
                                    val.modelXbrl.error((u"EFM.6.14.02", u"GFM.1.07.02"),
                                        _(u"CalculationArc from %(xlinkFrom)s to %(xlinkTo)s weight %(weight)s must be 1 or -1"),
                                        modelObject=elt, 
                                        xlinkFrom=elt.get(u"{http://www.w3.org/1999/xlink}from"),
                                        xlinkTo=elt.get(u"{http://www.w3.org/1999/xlink}to"),
                                        conceptFrom=arcFromConceptQname(elt),
                                        conceptTo=arcToConceptQname(elt),
                                        weight=weightAttr)
                            except ValueError:
                                val.modelXbrl.error((u"EFM.6.14.02", u"GFM.1.07.02"),
                                    _(u"CalculationArc from %(xlinkFrom)s to %(xlinkTo)s must have an weight (value error in \"%(weight)s\")"),
                                    modelObject=elt, 
                                    xlinkFrom=elt.get(u"{http://www.w3.org/1999/xlink}from"),
                                    xlinkTo=elt.get(u"{http://www.w3.org/1999/xlink}to"),
                                    conceptFrom=arcFromConceptQname(elt),
                                    conceptTo=arcToConceptQname(elt),
                                    weight=weightAttr)
                        elif elt.localName == u"definitionArc":
                            if not elt.get(u"order"):
                                val.modelXbrl.error((u"EFM.6.16.01", u"GFM.1.08.01"),
                                    _(u"DefinitionArc from %(xlinkFrom)s to %(xlinkTo)s must have an order"),
                                    modelObject=elt, 
                                    xlinkFrom=elt.get(u"{http://www.w3.org/1999/xlink}from"),
                                    xlinkTo=elt.get(u"{http://www.w3.org/1999/xlink}to"),
                                    conceptFrom=arcFromConceptQname(elt),
                                    conceptTo=arcToConceptQname(elt))
                            if val.validateSBRNL and arcrole in (XbrlConst.essenceAlias, XbrlConst.similarTuples, XbrlConst.requiresElement):
                                val.modelXbrl.error({XbrlConst.essenceAlias: u"SBR.NL.2.3.2.02",
                                                  XbrlConst.similarTuples: u"SBR.NL.2.3.2.03", 
                                                  XbrlConst.requiresElement: u"SBR.NL.2.3.2.04"}[arcrole],
                                    _(u"DefinitionArc from %(xlinkFrom)s to %(xlinkTo)s has unauthorized arcrole %(arcrole)s"),
                                    modelObject=elt, 
                                    xlinkFrom=elt.get(u"{http://www.w3.org/1999/xlink}from"),
                                    xlinkTo=elt.get(u"{http://www.w3.org/1999/xlink}to"), 
                                    arcrole=arcrole,
                                    messageCodes=(u"SBR.NL.2.3.2.02", u"SBR.NL.2.3.2.03", u"SBR.NL.2.3.2.04")), 
                        elif elt.localName == u"referenceArc" and val.validateSBRNL:
                            if elt.get(u"order"):
                                val.modelXbrl.error(u"SBR.NL.2.3.3.05",
                                    _(u"ReferenceArc from %(xlinkFrom)s to %(xlinkTo)s has an order"),
                                    modelObject=elt, 
                                    xlinkFrom=elt.get(u"{http://www.w3.org/1999/xlink}from"),
                                    xlinkTo=elt.get(u"{http://www.w3.org/1999/xlink}to"))
                        if val.validateSBRNL and elt.get(u"use") == u"prohibited" and elt.getparent().tag in (
                                u"{http://www.xbrl.org/2003/linkbase}presentationLink", 
                                u"{http://www.xbrl.org/2003/linkbase}labelLink", 
                                u"{http://xbrl.org/2008/generic}link", 
                                u"{http://www.xbrl.org/2003/linkbase}referenceLink"):
                            val.modelXbrl.error(u"SBR.NL.2.3.0.10",
                                _(u"%(arc)s must not contain use='prohibited'"),
                                modelObject=elt, arc=elt.getparent().qname)
                    if val.validateSBRNL and elt.qname not in {
                        XbrlConst.qnLinkLabelLink: (XbrlConst.qnLinkLabelArc,),
                        XbrlConst.qnLinkReferenceLink: (XbrlConst.qnLinkReferenceArc,),
                        XbrlConst.qnLinkPresentationLink: (XbrlConst.qnLinkPresentationArc,),
                        XbrlConst.qnLinkCalculationLink: (XbrlConst.qnLinkCalculationArc,),
                        XbrlConst.qnLinkDefinitionLink: (XbrlConst.qnLinkDefinitionArc,),
                        XbrlConst.qnLinkFootnoteLink: (XbrlConst.qnLinkFootnoteArc,),
                        # XbrlConst.qnGenLink: (XbrlConst.qnGenArc,),
                         }.get(val.extendedElementName, (elt.qname,)):  # allow non-2.1 to be ok regardless per RH 2013-03-13
                        val.modelXbrl.error(u"SBR.NL.2.3.0.11",
                            _(u"Arc element %(element)s may not be contained in a linkbase with %(element2)s"),
                            modelObject=elt, element=elt.qname, element2=val.extendedElementName)
                    if val.validateSBRNL and elt.qname == XbrlConst.qnLinkLabelArc and elt.get(u"order"):
                        val.modelXbrl.error(u"SBR.NL.2.3.8.08",
                            _(u"labelArc may not be contain order (%(order)s)"),
                            modelObject=elt, order=elt.get(u"order"))
                if val.validateSBRNL:
                    # check attributes for prefixes and xmlns
                    val.valUsedPrefixes.add(elt.prefix)
                    if elt.namespaceURI not in val.disclosureSystem.baseTaxonomyNamespaces:
                        val.modelXbrl.error(u"SBR.NL.2.2.0.20",
                            _(u"%(fileType)s element %(element)s must not have custom namespace %(namespace)s"),
                            modelObject=elt, element=elt.qname, 
                            fileType=u"schema" if isSchema else u"linkbase" ,
                            namespace=elt.namespaceURI)
                    for attrTag, attrValue in elt.items():
                        prefix, ns, localName = XmlUtil.clarkNotationToPrefixNsLocalname(elt, attrTag, isAttribute=True)
                        if prefix: # don't count unqualified prefixes for using default namespace
                            val.valUsedPrefixes.add(prefix)
                        if ns and ns not in val.disclosureSystem.baseTaxonomyNamespaces:
                            val.modelXbrl.error(u"SBR.NL.2.2.0.20",
                                _(u"%(fileType)s element %(element)s must not have %(prefix)s:%(localName)s"),
                                modelObject=elt, element=elt.qname, 
                                fileType=u"schema" if isSchema else u"linkbase" ,
                                prefix=prefix, localName=localName)
                        if isSchema and localName in (u"base", u"ref", u"substitutionGroup", u"type"):
                            valuePrefix, sep, valueName = attrValue.partition(u":")
                            if sep:
                                val.valUsedPrefixes.add(valuePrefix)
                    # check for xmlns on a non-root element
                    parentElt = elt.getparent()
                    if parentElt is not None:
                        for prefix, ns in elt.nsmap.items():
                            if prefix not in parentElt.nsmap or parentElt.nsmap[prefix] != ns:
                                val.modelXbrl.error((u"SBR.NL.2.2.0.19" if isSchema else u"SBR.NL.2.3.1.01"),
                                    _(u"%(fileType)s element %(element)s must not have xmlns:%(prefix)s"),
                                    modelObject=elt, element=elt.qname, 
                                    fileType=u"schema" if isSchema else u"linkbase" ,
                                    prefix=prefix,
                                    messageCodes=(u"SBR.NL.2.2.0.19", u"SBR.NL.2.3.1.01"))
                            
                    if elt.localName == u"roleType" and not elt.get(u"id"): 
                        val.modelXbrl.error(u"SBR.NL.2.3.10.11",
                            _(u"RoleType %(roleURI)s missing id attribute"),
                            modelObject=elt, roleURI=elt.get(u"roleURI"))
                    elif elt.localName == u"loc" and elt.get(u"{http://www.w3.org/1999/xlink}role"): 
                        val.modelXbrl.error(u"SBR.NL.2.3.10.08",
                            _(u"Loc %(xlinkLabel)s has unauthorized role attribute"),
                            modelObject=elt, xlinkLabel=elt.get(u"{http://www.w3.org/1999/xlink}label"))
                    elif elt.localName == u"documentation": 
                        val.modelXbrl.error(u"SBR.NL.2.3.10.12" if elt.namespaceURI == XbrlConst.link else u"SBR.NL.2.2.11.02",
                            _(u"Documentation element must not be used: %(value)s"),
                            modelObject=elt, value=XmlUtil.text(elt),
                            messageCodes=(u"SBR.NL.2.3.10.12", u"SBR.NL.2.2.11.02"))
                    if elt.localName == u"linkbase":
                        schemaLocation = elt.get(u"{http://www.w3.org/2001/XMLSchema-instance}schemaLocation")
                        if schemaLocation:
                            schemaLocations = schemaLocation.split()
                            for sl in (XbrlConst.link, XbrlConst.xlink):
                                if sl in schemaLocations:
                                    val.modelXbrl.error(u"SBR.NL.2.3.0.07",
                                        _(u"Linkbase element must not have schemaLocation entry for %(schemaLocation)s"),
                                        modelObject=elt, schemaLocation=sl)
                        for attrName, errCode in ((u"id", u"SBR.NL.2.3.10.04"),
                                                  (u"{http://www.w3.org/2001/XMLSchema-instance}nil", u"SBR.NL.2.3.10.05"),
                                                  (u"{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation", u"SBR.NL.2.3.10.06"),
                                                  (u"{http://www.w3.org/2001/XMLSchema-instance}type", u"SBR.NL.2.3.10.07")):
                            if elt.get(attrName) is not None: 
                                val.modelXbrl.error(errCode,
                                    _(u"Linkbase element %(element)s must not have attribute %(attribute)s"),
                                    modelObject=elt, element=elt.qname, attribute=attrName,
                                    messageCodes=(u"SBR.NL.2.3.10.04", u"SBR.NL.2.3.10.05", u"SBR.NL.2.3.10.06", u"SBR.NL.2.3.10.07"))
                    for attrName, errCode in ((u"{http://www.w3.org/1999/xlink}actuate", u"SBR.NL.2.3.10.01"),
                                              (u"{http://www.w3.org/1999/xlink}show", u"SBR.NL.2.3.10.02"),
                                              (u"{http://www.w3.org/1999/xlink}title", u"SBR.NL.2.3.10.03")):
                        if elt.get(attrName) is not None: 
                            val.modelXbrl.error(errCode,
                                _(u"Linkbase element %(element)s must not have attribute xlink:%(attribute)s"),
                                modelObject=elt, element=elt.qname, attribute=attrName,
                                messageCodes=(u"SBR.NL.2.3.10.01", u"SBR.NL.2.3.10.02", u"SBR.NL.2.3.10.03"))
    
            checkElements(val, modelDocument, elt)
        elif isinstance(elt,ModelComment): # comment node
            if val.validateSBRNL:
                if elt.itersiblings(preceding=True):
                    val.modelXbrl.error(u"SBR.NL.2.2.0.05" if isSchema else u"SBR.NL.2.3.0.05",
                            _(u'%(fileType)s must have only one comment node before schema element: "%(value)s"'),
                            modelObject=elt, fileType=modelDocument.gettype().title(), value=elt.text,
                            messageCodes=(u"SBR.NL.2.2.0.05", u"SBR.NL.2.3.0.05"))

    # dereference at end of processing children of instance linkbase
    if isInstance or parentIsLinkbase:
        val.roleRefURIs = {}
        val.arcroleRefURIs = {}

def checkIxContinuationChain(elt, chain=None):
    if chain is None:
        chain = [elt]
    else:
        for otherElt in chain:
            if XmlUtil.isDescendantOf(elt, otherElt) or XmlUtil.isDescendantOf(otherElt, elt):
                elt.modelDocument.modelXbrl.error(u"ix:continuationDescendancy",
                                _(u"Inline XBRL continuation chain has elements which are descendants of each other."),
                                modelObject=(elt, otherElt))
            else:
                contAt = elt.get(u"_continuationElement")
                if contAt is not None:
                    chain.append(elt)
                checkIxContinuationChain(contAt, chain)
