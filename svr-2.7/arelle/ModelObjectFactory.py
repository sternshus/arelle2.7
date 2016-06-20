u'''
Created on Jun 10, 2011
Refactored on Jun 11, 2011 to ModelDtsObject, ModelInstanceObject, ModelTestcaseObject

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
from arelle.ModelObject import ModelObject

elementSubstitutionModelClass = {}

from lxml import etree
from arelle import XbrlConst, XmlUtil
from arelle.ModelValue import qnameNsLocalName
from arelle.ModelDtsObject import (ModelConcept, ModelAttribute, ModelAttributeGroup, ModelType, 
                                   ModelGroupDefinition, ModelAll, ModelChoice, ModelSequence,
                                   ModelAny, ModelAnyAttribute, ModelEnumeration,
                                   ModelRoleType, ModelLocator, ModelLink, ModelResource)
ModelDocument = ModelFact = None # would be circular imports, resolve at first use after static loading
from arelle.ModelRssItem import ModelRssItem
from arelle.ModelTestcaseObject import ModelTestcaseVariation
from arelle.ModelVersObject import (ModelAssignment, ModelAction, ModelNamespaceRename,
                                    ModelRoleChange, ModelVersObject, ModelConceptUseChange,
                                    ModelConceptDetailsChange, ModelRelationshipSetChange,
                                    ModelRelationshipSet, ModelRelationships)

def parser(modelXbrl, baseUrl, target=None):
    parser = etree.XMLParser(recover=True, huge_tree=True, target=target)
    return setParserElementClassLookup(parser, modelXbrl, baseUrl)

def setParserElementClassLookup(parser, modelXbrl, baseUrl=None):
    classLookup = DiscoveringClassLookup(modelXbrl, baseUrl)
    nsNameLookup = KnownNamespacesModelObjectClassLookup(modelXbrl, fallback=classLookup)
    parser.set_element_class_lookup(nsNameLookup)
    return (parser, nsNameLookup, classLookup)

SCHEMA = 1
LINKBASE = 2
VERSIONINGREPORT = 3
RSSFEED = 4

class KnownNamespacesModelObjectClassLookup(etree.CustomElementClassLookup):
    def __init__(self, modelXbrl, fallback=None):
        super(KnownNamespacesModelObjectClassLookup, self).__init__(fallback)
        self.modelXbrl = modelXbrl
        self.type = None

    def lookup(self, node_type, document, ns, ln):
        # node_type is "element", "comment", "PI", or "entity"
        if node_type == u"element":
            if ns == XbrlConst.xsd:
                if self.type is None:
                    self.type = SCHEMA
                if ln == u"element":
                    return ModelConcept
                elif ln == u"attribute":
                    return ModelAttribute
                elif ln == u"attributeGroup":
                    return ModelAttributeGroup
                elif ln == u"complexType" or ln == u"simpleType":
                    return ModelType
                elif ln == u"group":
                    return ModelGroupDefinition
                elif ln == u"sequence":
                    return ModelSequence
                elif ln == u"choice" or ln == u"all":
                    return ModelChoice
                elif ln == u"all":
                    return ModelAll
                elif ln == u"any":
                    return ModelAny
                elif ln == u"anyAttribute":
                    return ModelAnyAttribute
                elif ln == u"enumeration":
                    return ModelEnumeration
            elif ns == XbrlConst.link:
                if self.type is None:
                    self.type = LINKBASE
                if ln == u"roleType" or ln == u"arcroleType":
                    return ModelRoleType
            elif ns == u"http://edgar/2009/conformance":
                # don't force loading of test schema
                if ln == u"variation":
                    return ModelTestcaseVariation
                else:
                    return ModelObject
            elif ln == u"testcase" and (
                ns is None or ns in (u"http://edgar/2009/conformance",) or ns.startswith(u"http://xbrl.org/")):
                return ModelObject
            elif ln == u"variation" and (
                ns is None or ns in (u"http://edgar/2009/conformance",) or ns.startswith(u"http://xbrl.org/")):
                return ModelTestcaseVariation
            elif ln == u"testGroup" and ns == u"http://www.w3.org/XML/2004/xml-schema-test-suite/":
                return ModelTestcaseVariation
            elif ln == u"test-case" and ns == u"http://www.w3.org/2005/02/query-test-XQTSCatalog":
                return ModelTestcaseVariation
            elif ns == XbrlConst.ver:
                if self.type is None:
                    self.type = VERSIONINGREPORT
            elif ns == u"http://dummy":
                return etree.ElementBase
            if self.type is None and ln == u"rss":
                self.type = RSSFEED
            elif self.type == RSSFEED:
                if ln == u"item":
                    return ModelRssItem
                else:
                    return ModelObject
                
            # match specific element types or substitution groups for types
            return self.modelXbrl.matchSubstitutionGroup(
                                        qnameNsLocalName(ns, ln),
                                        elementSubstitutionModelClass)
        elif node_type == u"comment":
            from arelle.ModelObject import ModelComment
            return ModelComment
        elif node_type == u"PI":
            return etree.PIBase
        elif node_type == u"entity":
            return etree.EntityBase

class DiscoveringClassLookup(etree.PythonElementClassLookup):
    def __init__(self, modelXbrl, baseUrl, fallback=None):
        super(DiscoveringClassLookup, self).__init__(fallback)
        self.modelXbrl = modelXbrl
        self.streamingOrSkipDTS = modelXbrl.skipDTS or getattr(modelXbrl, u"isStreamingMode", False)
        self.baseUrl = baseUrl
        self.discoveryAttempts = set()
        global ModelFact, ModelDocument
        if ModelDocument is None:
            from arelle import ModelDocument
        if self.streamingOrSkipDTS and ModelFact is None:
            from arelle.ModelInstanceObject import ModelFact
        
    def lookup(self, document, proxyElement):
        # check if proxyElement's namespace is not known
        ns, sep, ln = proxyElement.tag.partition(u"}")
        if sep:
            ns = ns[1:]
        else:
            ln = ns
            ns = None
        if (ns and 
            ns not in self.discoveryAttempts and 
            ns not in self.modelXbrl.namespaceDocs):
            # is schema loadable?  requires a schemaLocation
            relativeUrl = XmlUtil.schemaLocation(proxyElement, ns)
            self.discoveryAttempts.add(ns)
            if relativeUrl:
                doc = ModelDocument.loadSchemalocatedSchema(self.modelXbrl, proxyElement, relativeUrl, ns, self.baseUrl)

        modelObjectClass = self.modelXbrl.matchSubstitutionGroup(
            qnameNsLocalName(ns, ln),
            elementSubstitutionModelClass)
        
        if modelObjectClass is not None:
            return modelObjectClass
        elif (self.streamingOrSkipDTS and 
              ns not in (XbrlConst.xbrli, XbrlConst.link)):
            # self.makeelementParentModelObject is set in streamingExtensions.py and ModelXbrl.createFact
            ancestor = proxyElement.getparent() or getattr(self.modelXbrl, u"makeelementParentModelObject", None)
            while ancestor is not None:
                tag = ancestor.tag # not a modelObject yet, just parser prototype
                if tag.startswith(u"{http://www.xbrl.org/2003/instance}") or tag.startswith(u"{http://www.xbrl.org/2003/linkbase}"):
                    if tag == u"{http://www.xbrl.org/2003/instance}xbrl":
                        return ModelFact # element not parented by context or footnoteLink
                    else:
                        break # cannot be a fact
                ancestor = ancestor.getparent()
                
        xlinkType = proxyElement.get(u"{http://www.w3.org/1999/xlink}type")
        if xlinkType == u"extended": return ModelLink
        elif xlinkType == u"locator": return ModelLocator
        elif xlinkType == u"resource": return ModelResource
        
        return ModelObject
