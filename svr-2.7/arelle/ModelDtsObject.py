u"""
:mod:`arelle.ModelDtsObjuect`
~~~~~~~~~~~~~~~~~~~

.. module:: arelle.ModelDtsObject
   :copyright: Copyright 2010-2012 Mark V Systems Limited, All rights reserved.
   :license: Apache-2.
   :synopsis: This module contains DTS-specialized ModelObject classes: ModelRoleType (role and arcrole types), ModelSchemaObject (parent class for top-level named schema element, attribute, attribute groups, etc), ModelConcept (xs:elements that may be concepts, typed dimension elements, or just plain XML definitions), ModelAttribute (xs:attribute), ModelAttributeGroup, ModelType (both top level named and anonymous simple and complex types), ModelEnumeration, ModelLink (xlink link elements), ModelResource (xlink resource elements), ModelLocator (subclass of ModelResource for xlink locators), and ModelRelationship (not an lxml proxy object, but a resolved relationship that reflects an effective arc between one source and one target). 

XBRL processing requires element-level access to schema elements.  Traditional XML processors, such as 
lxml (based on libxml), and Xerces (not available in the Python environment), provide opaque schema 
models that cannot be used by an XML processor.  Arelle implements its own elment, attribute, and 
type processing, in order to provide PSVI-validated element and attribute contents, and in order to 
access XBRL features that would otherwise be inaccessible in the XML library opaque schema models.

ModelConcept represents a schema element, regardless whether an XBRL item or tuple, or non-concept 
schema element.  The common XBRL and schema element attributes are provided by Python properties, 
cached when needed for efficiency, somewhat isolating from the XML level implementation.

There is thought that a future SQL-based implementation may be able to utilize ModelObject proxy 
objects to interface to SQL-obtained data.

ModelType represents an anonymous or explicit element type.  It includes methods that determine 
the base XBRL type (such as monetaryItemType), the base XML type (such as decimal), substitution 
group chains, facits, and attributes.

ModelAttributeGroup and ModelAttribute provide sufficient mechanism to identify element attributes, 
their types, and their default or fixed values.

There is also an inherently different model, modelRelationshipSet, which represents an individual 
base or dimensional-relationship set, or a collection of them (such as labels independent of 
extended link role), based on the semantics of XLink arcs.

PSVI-validated instance data are determined during loading for instance documents, and on demand 
for any other objects (such as when formula operations may access linkbase contents and need 
PSVI-validated contents of some linkbase elements).  These validated items are added to the 
ModelObject lxml custom proxy objects.

Linkbase objects include modelLink, representing extended link objects, modelResource, 
representing resource objects, and modelRelationship, which is not a lxml proxy object, but 
represents a resolved and effective arc in a relationship set.

ModelRelationshipSets are populated on demand according to specific or general characteristics.  
A relationship set can be a fully-specified base set, including arcrole, linkrole, link element 
qname, and arc element qname.  However by not specifying linkrole, link, or arc, a composite 
relationship set can be produced for an arcrole accumulating relationships across all extended 
link linkroles that have contributing arcs, which may be needed in building indexing or graphical 
topology top levels.

Relationship sets for dimensional arcroles will honor and traverse targetrole attributes across 
linkroles.  There is a pseudo-arcrole for dimensions that allows accumulating all dimensional 
relationships regardless of arcrole, which is useful for constructing certain graphic tree views.  

Relationship sets for table linkbases likewise have a pseudo-arcrole to accumulate all table 
relationships regardless of arcrole, for the same purpose.

Relationship sets can identify ineffective arcroles, which is a requirement for SEC and GFM 
validation.
"""
from collections import defaultdict
import os, sys
from lxml import etree
import decimal
from arelle import (XmlUtil, XbrlConst, XbrlUtil, UrlUtil, Locale, ModelValue, XmlValidate)
from arelle.XmlValidate import UNVALIDATED, VALID
from arelle.ModelObject import ModelObject

ModelFact = None

class ModelRoleType(ModelObject):
    u"""
    .. class:: ModelRoleType(modelDocument)
    
    ModelRoleType represents both role type and arcrole type definitions
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelRoleType, self).init(modelDocument)
        
    @property
    def isArcrole(self):
        u"""(bool) -- True if ModelRoleType declares an arcrole type"""
        return self.localName == u"arcroleType"
    
    @property
    def roleURI(self):
        u"""(str) -- Value of roleURI attribute"""
        return self.get(u"roleURI")
    
    @property
    def arcroleURI(self):
        u"""(str) -- Value of arcroleURI attribute"""
        return self.get(u"arcroleURI")
    
    @property
    def cyclesAllowed(self):
        u"""(str) -- Value of cyclesAllowed attribute"""
        return self.get(u"cyclesAllowed")

    @property
    def definition(self):
        u"""(str) -- Text of child definition element (stripped)"""
        try:
            return self._definition
        except AttributeError:
            definition = XmlUtil.child(self, XbrlConst.link, u"definition")
            self._definition = definition.textValue.strip() if definition is not None else None
            return self._definition

    @property
    def definitionNotStripped(self):
        u"""(str) -- Text of child definition element (not stripped)"""
        definition = XmlUtil.child(self, XbrlConst.link, u"definition")
        return definition.textValue if definition is not None else None
    
    @property
    def usedOns(self): 
        u"""( {QName} ) -- Set of PSVI QNames of descendant usedOn elements"""
        try:
            return self._usedOns
        except AttributeError:
            XmlValidate.validate(self.modelXbrl, self)
            self._usedOns = set(usedOn.xValue
                                for usedOn in self.iterdescendants(u"{http://www.xbrl.org/2003/linkbase}usedOn")
                                if isinstance(usedOn,ModelObject))
            return self._usedOns
        
    @property
    def tableCode(self):
        u""" table code from structural model for presentable table by ELR"""
        if self.isArcrole:
            return None
        try:
            return self._tableCode
        except AttributeError:
            from arelle import TableStructure
            TableStructure.evaluateRoleTypesTableCodes(self.modelXbrl)
            return self._tableCode
    
    @property
    def propertyView(self):
        if self.isArcrole:
            return ((u"arcrole Uri", self.arcroleURI),
                    (u"definition", self.definition),
                    (u"used on", self.usedOns),
                    (u"defined in", self.modelDocument.uri))
        else:
            return ((u"role Uri", self.roleURI),
                    (u"definition", self.definition),
                    (u"used on", self.usedOns),
                    (u"defined in", self.modelDocument.uri))
        
    def __repr__(self):
        return (u"{0}[{1}, uri: {2}, definition: {3}, {4} line {5}])"
                .format(u'modelArcroleType' if self.isArcrole else u'modelRoleType', 
                        self.objectIndex, 
                        self.arcroleURI if self.isArcrole else self.roleURI,
                        self.definition,
                        self.modelDocument.basename, self.sourceline))

    @property
    def viewConcept(self):  # concept trees view roles as themselves
        return self

class ModelNamableTerm(ModelObject):
    u"""
    .. class:: ModelNamableTerm(modelDocument)
    
    Particle Model namable term (can have @name attribute)
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelNamableTerm, self).init(modelDocument)
        
    @property
    def name(self):
        return self.getStripped(u"name")
    
    @property
    def qname(self):
        try:
            return self._xsdQname
        except AttributeError:
            name = self.name
            if self.name:
                if self.parentQname == XbrlConst.qnXsdSchema or self.isQualifiedForm:
                #if self.isQualifiedForm:
                    prefix = XmlUtil.xmlnsprefix(self.modelDocument.xmlRootElement,self.modelDocument.targetNamespace)
                    self._xsdQname = ModelValue.QName(prefix, self.modelDocument.targetNamespace, name)
                else:
                    self._xsdQname = ModelValue.QName(None, None, name)
            else:
                self._xsdQname = None
            return self._xsdQname
    
    @property
    def isGlobalDeclaration(self):
        parent = self.getparent()
        return parent.namespaceURI == XbrlConst.xsd and parent.localName == u"schema"

    def schemaNameQname(self, prefixedName, isQualifiedForm=True, prefixException=None):
        u"""Returns ModelValue.QName of prefixedName using this element and its ancestors' xmlns.
        
        :param prefixedName: A prefixed name string
        :type prefixedName: str
        :returns: QName -- the resolved prefixed name, or None if no prefixed name was provided
        """
        if prefixedName:    # passing None would return element qname, not prefixedName None Qname
            qn = ModelValue.qnameEltPfxName(self, prefixedName, prefixException=prefixException)
            # may be in an included file with no target namespace
            # a ref to local attribute or element wihich is qualified MAY need to assume targetNamespace
            if qn and not qn.namespaceURI and self.modelDocument.noTargetNamespace and not isQualifiedForm:
                qn = ModelValue.qname(self.modelDocument.targetNamespace, prefixedName)
            return qn
        else:
            return None
class ParticlesList(list):
    u"""List of particles which can provide string representation of contained particles"""
    def __repr__(self):
        particlesList = []
        for particle in self:
            if isinstance(particle, ModelConcept):
                mdlObj = particle.dereference()
                if isinstance(mdlObj, ModelObject):
                    p = unicode(mdlObj.qname)
                else:
                    p = u'None'
            elif isinstance(particle, ModelAny):
                p = u"any"
            else:
                p = u"{0}({1})".format(particle.localName, getattr(particle.dereference(), u"particles", u""))
            particlesList.append(p + (u"" if particle.minOccurs == particle.maxOccurs == 1 else
                                      u"{{{0}:{1}}}".format(particle.minOccursStr, particle.maxOccursStr)))
        return u", ".join(particlesList)

class ModelParticle():
    u"""Represents a particle (for multi-inheritance subclasses of particles)"""
    def addToParticles(self):
        u"""Finds particle parent (in xml element ancestry) and appends self to parent particlesList"""
        parent = self.getparent()
        while parent is not None:  # find a parent with particles list
            try:
                parent.particlesList.append(self)
                break
            except AttributeError:
                parent = parent.getparent()

    @property
    def maxOccurs(self):
        u"""(int) -- Value of maxOccurs attribute, sys.maxsize of unbounded, or 1 if absent"""
        try:
            return self._maxOccurs
        except AttributeError:
            m = self.get(u"maxOccurs")
            if m:
                if m == u"unbounded":
                    self._maxOccurs = sys.maxsize
                else:
                    self._maxOccurs = _INT(m)
                    if self._maxOccurs < 0: 
                        raise ValueError(_(u"maxOccurs must be positive").format(m))
            else:
                self._maxOccurs = 1
            return self._maxOccurs
        
    @property
    def maxOccursStr(self):
        u"""(str) -- String value of maxOccurs attribute"""
        if self.maxOccurs == sys.maxsize:
            return u"unbounded"
        return unicode(self.maxOccurs)
        
    @property
    def minOccurs(self):
        u"""(int) -- Value of minOccurs attribute or 1 if absent"""
        try:
            return self._minOccurs
        except AttributeError:
            m = self.get(u"minOccurs")
            if m:
                self._minOccurs = _INT(m)
                if self._minOccurs < 0: 
                    raise ValueError(_(u"minOccurs must be positive").format(m))
            else:
                self._minOccurs = 1
            return self._minOccurs
        
    @property
    def minOccursStr(self):
        u"""(str) -- String value of minOccurs attribute"""
        return unicode(self.minOccurs)        

anonymousTypeSuffix = u"@anonymousType"

class ModelConcept(ModelNamableTerm, ModelParticle):
    u"""
    .. class:: ModelConcept(modelDocument)
    
    Particle Model element term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelConcept, self).init(modelDocument)
        if self.name:  # don't index elements with ref and no name
            self.modelXbrl.qnameConcepts[self.qname] = self
            if not self.isQualifiedForm:
                self.modelXbrl.qnameConcepts[ModelValue.QName(None, None, self.name)] = self
            self.modelXbrl.nameConcepts[self.name].append(self)
        if not self.isGlobalDeclaration:
            self.addToParticles()
        self._baseXsdAttrType = {}
        
    @property
    def abstract(self):
        u"""(str) -- Value of abstract attribute or 'false' if absent"""
        return self.get(u"abstract", u'false')
    
    @property
    def isAbstract(self):
        u"""(bool) -- True if abstract"""
        return self.abstract in (u"true", u"1")
    
    @property
    def periodType(self):
        u"""(str) -- Value of periodType attribute"""
        return self.get(u"{http://www.xbrl.org/2003/instance}periodType")
    
    @property
    def balance(self):
        u"""(str) -- Value of balance attribute"""
        return self.get(u"{http://www.xbrl.org/2003/instance}balance")
    
    @property
    def typeQname(self):
        u"""(QName) -- Value of type attribute, if any, or if type contains an annonymously-named
        type definition (as sub-elements), then QName formed of element QName with anonymousTypeSuffix
        appended to localName.  If neither type attribute or nested type definition, then attempts
        to get type definition in turn from substitution group element."""
        try:
            return self._typeQname
        except AttributeError:
            if self.get(u"type"):
                self._typeQname = self.schemaNameQname(self.get(u"type"))
            else:
                # check if anonymous type exists (clark qname tag + suffix)
                qn = self.qname
                if qn is not None:
                    typeQname = ModelValue.QName(qn.prefix, qn.namespaceURI, qn.localName + anonymousTypeSuffix)
                else:
                    typeQname = None
                if typeQname in self.modelXbrl.qnameTypes:
                    self._typeQname = typeQname
                else:
                    # try substitution group for type
                    subs = self.substitutionGroup
                    if subs is not None:
                        self._typeQname = subs.typeQname
                    else:
                        self._typeQname =  XbrlConst.qnXsdDefaultType
            return self._typeQname
        
    @property
    def niceType(self):
        u"""Provides a type name suited for user interfaces: hypercubes as Table, dimensions as Axis, 
        types ending in ItemType have ItemType removed and first letter capitalized (e.g., 
        stringItemType as String).  Otherwise returns the type's localName portion.
        """
        if self.isHypercubeItem: return u"Table"
        if self.isDimensionItem: return u"Axis"
        if self.typeQname:
            if self.typeQname.localName.endswith(u"ItemType"):
                return self.typeQname.localName[0].upper() + self.typeQname.localName[1:-8]
            return self.typeQname.localName
        return None
        
    @property
    def baseXsdType(self):
        u"""(str) -- Value of localname of type (e.g., monetary for monetaryItemType)"""
        try:
            return self._baseXsdType
        except AttributeError:
            typeqname = self.typeQname
            if typeqname is not None and typeqname.namespaceURI == XbrlConst.xsd:
                self._baseXsdType = typeqname.localName
            else:
                type = self.type
                self._baseXsdType = type.baseXsdType if type is not None else u"anyType"
            return self._baseXsdType
        
    @property
    def facets(self):
        u"""(dict) -- Facets declared for element type"""
        return self.type.facets if self.type is not None else None
    
    u''' unused, remove???
    def baseXsdAttrType(self,attrName):
        try:
            return self._baseXsdAttrType[attrName]
        except KeyError:
            if self.type is not None:
                attrType = self.type.baseXsdAttrType(attrName)
            else:
                attrType = "anyType"
            self._baseXsdAttrType[attrName] = attrType
            return attrType
    '''
    
    @property
    def baseXbrliType(self):
        u"""(str) -- Attempts to return the base xsd type localName that this concept's type 
        is derived from.  If not determinable anyType is returned.  E.g., for monetaryItemType, 
        decimal is returned."""
        try:
            return self._baseXbrliType
        except AttributeError:
            typeqname = self.typeQname
            if typeqname is not None and typeqname.namespaceURI == XbrlConst.xbrli:
                self._baseXbrliType =  typeqname.localName
            else:
                self._baseXbrliType = self.type.baseXbrliType if self.type is not None else None
            return self._baseXbrliType
        
    @property
    def baseXbrliTypeQname(self):
        u"""(qname) -- Attempts to return the base xsd type QName that this concept's type 
        is derived from.  If not determinable anyType is returned.  E.g., for monetaryItemType, 
        decimal is returned."""
        try:
            return self._baseXbrliTypeQname
        except AttributeError:
            typeqname = self.typeQname
            if typeqname is not None and typeqname.namespaceURI == XbrlConst.xbrli:
                self._baseXbrliTypeQname = typeqname
            else:
                self._baseXbrliTypeQname = self.type.baseXbrliTypeQname if self.type is not None else None
            return self._baseXbrliTypeQname
        
    def instanceOfType(self, typeqname):
        u"""(bool) -- True if element is declared by, or derived from type of given qname"""
        if typeqname == self.typeQname:
            return True
        type = self.type
        if type is not None and self.type.isDerivedFrom(typeqname):
            return True
        subs = self.substitutionGroup
        if subs is not None: 
            return subs.instanceOfType(typeqname)
        return False
    
    @property
    def isNumeric(self):
        u"""(bool) -- True for elements of, or derived from, numeric base type (not including fractionItemType)"""
        try:
            return self._isNumeric
        except AttributeError:
            self._isNumeric = XbrlConst.isNumericXsdType(self.baseXsdType)
            return self._isNumeric
    
    @property
    def isFraction(self):
        u"""(bool) -- True if the baseXbrliType is fractionItemType"""
        try:
            return self._isFraction
        except AttributeError:
            self._isFraction = self.baseXbrliType == u"fractionItemType"
            return self._isFraction
    
    @property
    def isMonetary(self):
        u"""(bool) -- True if the baseXbrliType is monetaryItemType"""
        try:
            return self._isMonetary
        except AttributeError:
            self._isMonetary = self.baseXbrliType == u"monetaryItemType"
            return self._isMonetary
    
    @property
    def isShares(self):
        u"""(bool) -- True if the baseXbrliType is sharesItemType"""
        try:
            return self._isShares
        except AttributeError:
            self._isShares = self.baseXbrliType == u"sharesItemType"
            return self._isShares
    
    @property
    def isTextBlock(self):
        u"""(bool) -- Element's type.isTextBlock."""
        return self.type is not None and self.type.isTextBlock
    
    @property
    def type(self):
        u"""Element's modelType object (if any)"""
        try:
            return self._type
        except AttributeError:
            self._type = self.modelXbrl.qnameTypes.get(self.typeQname)
            return self._type
    
    @property
    def substitutionGroup(self):
        u"""modelConcept object for substitution group (or None)"""
        subsgroupqname = self.substitutionGroupQname
        if subsgroupqname is not None:
            return self.modelXbrl.qnameConcepts.get(subsgroupqname)
        return None
        
    @property
    def substitutionGroupQname(self):
        u"""(QName) -- substitution group"""
        try:
            return self._substitutionGroupQname
        except AttributeError:
            self._substitutionGroupQname = None
            if self.get(u"substitutionGroup"):
                self._substitutionGroupQname = self.schemaNameQname(self.get(u"substitutionGroup"))
            return self._substitutionGroupQname
        
    @property
    def substitutionGroupQnames(self):   # ordered list of all substitution group qnames
        u"""([QName]) -- Ordered list of QNames of substitution groups (recursively)"""
        qnames = []
        subs = self
        subNext = subs.substitutionGroup
        while subNext is not None:
            qnames.append(subNext.qname)
            subs = subNext
            subNext = subs.substitutionGroup
        return qnames
    
    @property
    def isQualifiedForm(self): # used only in determining qname, which itself is cached
        u"""(bool) -- True if element has form attribute qualified or its document default"""
        if self.get(u"form") is not None: # form is almost never used
            return self.get(u"form") == u"qualified"
        return self.modelDocument.isQualifiedElementFormDefault
        
    @property
    def nillable(self):
        u"""(str) --Value of the nillable attribute or its default"""
        return self.get(u"nillable", u'false')
    
    @property
    def isNillable(self):
        u"""(bool) -- True if nillable"""
        return self.get(u"nillable") == u'true'
        
    @property
    def block(self):
        u"""(str) -- block attribute"""
        return self.get(u"block")
    
    @property
    def default(self):
        u"""(str) -- default attribute"""
        return self.get(u"default")
    
    @property
    def fixed(self):
        u"""(str) -- fixed attribute"""
        return self.get(u"fixed")
    
    @property
    def final(self):
        u"""(str) -- final attribute"""
        return self.get(u"final")
    
    @property
    def isRoot(self):
        u"""(bool) -- True if parent of element definition is xsd schema element"""
        return self.getparent().localName == u"schema"
    
    def label(self,preferredLabel=None,fallbackToQname=True,lang=None,strip=False,linkrole=None,linkroleHint=None):
        u"""Returns effective label for concept, using preferredLabel role (or standard label if None), 
        absent label falls back to element qname (prefixed name) if specified, lang falls back to 
        tool-config language if none, leading/trailing whitespace stripped (trimmed) if specified.  
        Does not look for generic labels (use superclass genLabel for generic label).
        
        :param preferredLabel: label role (standard label if not specified)
        :type preferredLabel: str
        :param fallbackToQname: if True and no matching label, then element qname is returned
        :type fallbackToQname: bool
        :param lang: language code requested (otherwise configuration specified language is returned)
        :type lang: str
        :param strip: specifies removal of leading/trailing whitespace from returned label
        :type strip: bool
        :param linkrole: specifies linkrole desired (wild card if not specified)
        :type linkrole: str
        :returns: label matching parameters, or element qname if fallbackToQname requested and no matching label
        """
        if preferredLabel is None: preferredLabel = XbrlConst.standardLabel
        if preferredLabel == XbrlConst.conceptNameLabelRole: return unicode(self.qname)
        labelsRelationshipSet = self.modelXbrl.relationshipSet(XbrlConst.conceptLabel,linkrole)
        if labelsRelationshipSet:
            label = labelsRelationshipSet.label(self, preferredLabel, lang, linkroleHint=linkroleHint)
            if label is not None:
                if strip: return label.strip()
                return Locale.rtlString(label, lang=lang)
        return unicode(self.qname) if fallbackToQname else None
    
    def relationshipToResource(self, resourceObject, arcrole):    
        u"""For specified object and resource (all link roles), returns first 
        modelRelationshipObject that relates from this element to specified resourceObject. 

        :param resourceObject: resource to find relationship to
        :type resourceObject: ModelObject
        :param arcrole: specifies arcrole for search
        :type arcrole: str
        :returns: ModelRelationship
        """ 
        relationshipSet = self.modelXbrl.relationshipSet(arcrole)
        if relationshipSet:
            for modelRel in relationshipSet.fromModelObject(self):
                if modelRel.toModelObject == resourceObject:
                    return modelRel
        return None
    
    @property
    def isItem(self):
        u"""(bool) -- True for a substitution for xbrli:item but not xbrli:item itself"""
        try:
            return self._isItem
        except AttributeError:
            self._isItem = self.subGroupHeadQname == XbrlConst.qnXbrliItem and self.namespaceURI != XbrlConst.xbrli
            return self._isItem

    @property
    def isTuple(self): 
        u"""(bool) -- True for a substitution for xbrli:tuple but not xbrli:tuple itself"""
        try:
            return self._isTuple
        except AttributeError:
            self._isTuple = self.subGroupHeadQname == XbrlConst.qnXbrliTuple and self.namespaceURI != XbrlConst.xbrli
            return self._isTuple
        
    @property
    def isLinkPart(self):
        u"""(bool) -- True for a substitution for link:part but not link:part itself"""
        try:
            return self._isLinkPart
        except AttributeError:
            self._isLinkPart = self.subGroupHeadQname == XbrlConst.qnLinkPart and self.namespaceURI != XbrlConst.link
            return self._isLinkPart
        
    @property
    def isPrimaryItem(self):
        u"""(bool) -- True for a concept definition that is not a hypercube or dimension"""
        try:
            return self._isPrimaryItem
        except AttributeError:
            self._isPrimaryItem = self.isItem and not \
            (self.substitutesForQname(XbrlConst.qnXbrldtHypercubeItem) or self.substitutesForQname(XbrlConst.qnXbrldtDimensionItem))
            return self._isPrimaryItem

    @property
    def isDomainMember(self):
        u"""(bool) -- Same as isPrimaryItem (same definition in XDT)"""
        return self.isPrimaryItem   # same definition in XDT
        
    @property
    def isHypercubeItem(self):
        u"""(bool) -- True for a concept definition that is a hypercube"""
        try:
            return self._isHypercubeItem
        except AttributeError:
            self._isHypercubeItem = self.substitutesForQname(XbrlConst.qnXbrldtHypercubeItem)
            return self._isHypercubeItem
        
    @property
    def isDimensionItem(self):
        u"""(bool) -- True for a concept definition that is a dimension"""
        try:
            return self._isDimensionItem
        except AttributeError:
            self._isDimensionItem = self.substitutesForQname(XbrlConst.qnXbrldtDimensionItem)
            return self._isDimensionItem
        
    @property
    def isTypedDimension(self):
        u"""(bool) -- True for a concept definition that is a typed dimension"""
        try:
            return self._isTypedDimension
        except AttributeError:
            self._isTypedDimension = self.isDimensionItem and self.get(u"{http://xbrl.org/2005/xbrldt}typedDomainRef") is not None
            return self._isTypedDimension
        
    @property
    def isExplicitDimension(self):
        u"""(bool) -- True for a concept definition that is an explicit dimension"""
        return self.isDimensionItem and not self.isTypedDimension
    
    @property
    def typedDomainRef(self):
        u"""(str) -- typedDomainRef attribute"""
        return self.get(u"{http://xbrl.org/2005/xbrldt}typedDomainRef")

    @property
    def typedDomainElement(self):
        u"""(ModelConcept) -- the element definition for a typedDomainRef attribute (of a typed dimension element)"""
        try:
            return self._typedDomainElement
        except AttributeError:
            self._typedDomainElement = self.resolveUri(uri=self.typedDomainRef)
            return self._typedDomainElement
    
    @property
    def isEnumeration(self):
        u"""(bool) -- True if derived from enum:enumerationItemType"""
        try:
            return self._isEnum
        except AttributeError:
            self._isEnum = self.instanceOfType(XbrlConst.qnEnumerationItemType)
            return self._isEnum
        
    @property
    def enumDomainQname(self):
        u"""(QName) -- enumeration domain qname """
        return self.schemaNameQname(self.get(XbrlConst.attrEnumerationDomain))

    @property
    def enumDomain(self):
        u"""(ModelConcept) -- enumeration domain """
        try:
            return self._enumDomain
        except AttributeError:
            self._enumDomain = self.modelXbrl.qnameConcepts.get(self.enumDomainQname)
            return self._enumDomain
        
    @property
    def enumLinkrole(self):
        u"""(anyURI) -- enumeration linkrole """
        return self.get(XbrlConst.attrEnumerationLinkrole)
    
    @property
    def enumDomainUsable(self):
        u"""(string) -- enumeration usable attribute """
        return self.get(XbrlConst.attrEnumerationUsable) or u"false"

    @property
    def isEnumDomainUsable(self):
        u"""(bool) -- enumeration domain usability """
        try:
            return self._isEnumDomainUsable
        except AttributeError:
            self._isEnumDomainUsable = self.enumDomainUsable == u"true"
            return self._isEnumDomainUsable

    def substitutesForQname(self, subsQname):
        u"""(bool) -- True if element substitutes for specified qname"""
        subs = self
        subNext = subs.substitutionGroup
        while subNext is not None:
            if subsQname == subs.substitutionGroupQname:
                return True
            subs = subNext
            subNext = subs.substitutionGroup
        return False
        
    @property
    def subGroupHeadQname(self):
        u"""(QName) -- Head of substitution lineage of element (e.g., xbrli:item)"""
        subs = self
        subNext = subs.substitutionGroup
        while subNext is not None:
            subs = subNext
            subNext = subs.substitutionGroup
        return subs.qname

    def dereference(self):
        u"""(ModelConcept) -- If element is a ref (instead of name), provides referenced modelConcept object, else self"""
        ref = self.get(u"ref")
        if ref:
            qn = self.schemaNameQname(ref, isQualifiedForm=self.isQualifiedForm)
            return self.modelXbrl.qnameConcepts.get(qn)
        return self

    @property
    def propertyView(self):
        return ((u"label", self.label(lang=self.modelXbrl.modelManager.defaultLang)),
                (u"namespace", self.qname.namespaceURI),
                (u"name", self.name),
                (u"QName", self.qname),
                (u"id", self.id),
                (u"abstract", self.abstract),
                (u"type", self.typeQname),
                (u"subst grp", self.substitutionGroupQname),
                (u"period type", self.periodType) if self.periodType else (),
                (u"balance", self.balance) if self.balance else ())
        
    def __repr__(self):
        return (u"modelConcept[{0}, qname: {1}, type: {2}, abstract: {3}, {4}, line {5}]"
                .format(self.objectIndex, self.qname, self.typeQname, self.abstract,
                        self.modelDocument.basename, self.sourceline))

    @property
    def viewConcept(self):
        return self
            
class ModelAttribute(ModelNamableTerm):
    u"""
    .. class:: ModelAttribute(modelDocument)
    
    Attribute term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelAttribute, self).init(modelDocument)
        if self.isGlobalDeclaration:
            self.modelXbrl.qnameAttributes[self.qname] = self
            if not self.isQualifiedForm:
                self.modelXbrl.qnameAttributes[ModelValue.QName(None, None, self.name)] = self
        
    @property
    def typeQname(self):
        u"""(QName) -- QName of type of attribute"""
        if self.get(u"type"):
            return self.schemaNameQname(self.get(u"type"))
        elif getattr(self,u"xValid", 0) >= 4:
            # check if anonymous type exists
            typeqname = ModelValue.qname(self.qname.clarkNotation +  anonymousTypeSuffix)
            if typeqname in self.modelXbrl.qnameTypes:
                return typeqname
            # try substitution group for type
            u''' HF: I don't think attributes can have a substitution group ??
            subs = self.substitutionGroup
            if subs:
                return subs.typeQname
            '''
        return None
    
    @property
    def type(self):
        u"""(ModelType) -- Attribute's modelType object (if any)"""
        try:
            return self._type
        except AttributeError:
            self._type = self.modelXbrl.qnameTypes.get(self.typeQname)
            return self._type
    
    @property
    def baseXsdType(self):
        u"""(str) -- Attempts to return the base xsd type localName that this attribute's type 
        is derived from.  If not determinable *anyType* is returned"""
        try:
            return self._baseXsdType
        except AttributeError:
            typeqname = self.typeQname
            if typeqname is None:   # anyType is default type
                return u"anyType"
            if typeqname.namespaceURI == XbrlConst.xsd:
                return typeqname.localName
            type = self.type
            self._baseXsdType = type.baseXsdType if type is not None else None
            return self._baseXsdType
    
    @property
    def facets(self):
        u"""(dict) -- Returns self.type.facets or None (if type indeterminate)"""
        try:
            return self._facets
        except AttributeError:
            type = self.type
            self._facets = type.facets if type is not None else None
            return self._facets
    
    @property
    def isNumeric(self):
        u"""(bool) -- True for a numeric xsd base type (not including xbrl fractions)"""
        try:
            return self._isNumeric
        except AttributeError:
            self._isNumeric = XbrlConst.isNumericXsdType(self.baseXsdType)
            return self._isNumeric
    
    @property
    def isQualifiedForm(self): # used only in determining qname, which itself is cached
        u"""(bool) -- True if attribute has form attribute qualified or its document default"""
        if self.get(u"form") is not None: # form is almost never used
            return self.get(u"form") == u"qualified"
        return self.modelDocument.isQualifiedAttributeFormDefault
        
    @property
    def isRequired(self):
        u"""(bool) -- True if use is required"""
        return self.get(u"use") == u"required"
    
    @property
    def default(self):
        u"""(str) -- default attribute"""
        return self.get(u"default")
    
    @property
    def fixed(self):
        u"""(str) -- fixed attribute or None"""
        return self.get(u"fixed")
    
    def dereference(self):
        u"""(ModelAttribute) -- If element is a ref (instead of name), provides referenced modelAttribute object, else self"""
        ref = self.get(u"ref")
        if ref:
            qn = self.schemaNameQname(ref, isQualifiedForm=self.isQualifiedForm)
            return self.modelXbrl.qnameAttributes.get(qn)
        return self

class ModelAttributeGroup(ModelNamableTerm):
    u"""
    .. class:: ModelAttributeGroup(modelDocument)
    
    Attribute Group term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelAttributeGroup, self).init(modelDocument)
        if self.isGlobalDeclaration:
            self.modelXbrl.qnameAttributeGroups[self.qname] = self
        
    @property
    def isQualifiedForm(self): 
        u"""(bool) -- True, always qualified"""
        return True
    
    @property
    def attributes(self):
        u"""(dict) -- Dict by attribute QName of ModelAttributes"""
        try:
            return self._attributes
        except AttributeError:
            self._attributes = {}
            attrs, attrWildcardElts, attrGroups = XmlUtil.schemaAttributesGroups(self)
            self._attributeWildcards = set(attrWildcardElts)
            for attrGroupRef in attrGroups:
                attrGroupDecl = attrGroupRef.dereference()
                if attrGroupDecl is not None:
                    for attrRef in attrGroupDecl.attributes.values():
                        attrDecl = attrRef.dereference()
                        if attrDecl is not None:
                            self._attributes[attrDecl.qname] = attrDecl
                    self._attributeWildcards.update(attrGroupDecl.attributeWildcards)
            for attrRef in attrs:
                attrDecl = attrRef.dereference()
                if attrDecl is not None:
                    self._attributes[attrDecl.qname] = attrDecl
            return self._attributes
        
    @property
    def attributeWildcards(self):
        try:
            return self._attributeWildcards
        except AttributeError:
            self.attributes # loads attrWildcards
            return self._attributeWildcards
        
    def dereference(self):
        u"""(ModelAttributeGroup) -- If element is a ref (instead of name), provides referenced modelAttributeGroup object, else self"""
        ref = self.get(u"ref")
        if ref:
            qn = self.schemaNameQname(ref)
            return self.modelXbrl.qnameAttributeGroups.get(ModelValue.qname(self, ref))
        return self
        
class ModelType(ModelNamableTerm):
    u"""
    .. class:: ModelType(modelDocument)
    
    Type definition term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelType, self).init(modelDocument)
        self.modelXbrl.qnameTypes.setdefault(self.qname, self) # don't redefine types nested in anonymous types
        self.particlesList = ParticlesList()
        
    @property
    def name(self):
        nameAttr = self.getStripped(u"name")
        if nameAttr:
            return nameAttr
        # may be anonymous type of parent
        element = self.getparent()
        while element is not None:
            nameAttr = element.getStripped(u"name")
            if nameAttr:
                return nameAttr + anonymousTypeSuffix
            element = element.getparent()
        return None
    
    @property
    def isQualifiedForm(self):
        u"""(bool) -- True (for compatibility with other schema objects)"""
        return True
    
    @property
    def qnameDerivedFrom(self):
        u"""(QName) -- the type that this type is derived from"""
        typeOrUnion = XmlUtil.schemaBaseTypeDerivedFrom(self)
        if isinstance(typeOrUnion,list): # union
            return [self.schemaNameQname(t) for t in typeOrUnion]
        return self.schemaNameQname(typeOrUnion)
    
    @property
    def typeDerivedFrom(self):
        u"""(ModelType) -- type that this type is derived from"""
        qnameDerivedFrom = self.qnameDerivedFrom
        if isinstance(qnameDerivedFrom, list):
            return [self.modelXbrl.qnameTypes.get(qn) for qn in qnameDerivedFrom]
        elif isinstance(qnameDerivedFrom, ModelValue.QName):
            return self.modelXbrl.qnameTypes.get(qnameDerivedFrom)
        return None
    
    @property
    def particles(self):
        u"""([ModelParticles]) -- Particles of this type"""
        if self.particlesList:  # if non empty list, use it
            return self.particlesList
        typeDerivedFrom = self.typeDerivedFrom  # else try to get derived from list
        if isinstance(typeDerivedFrom, ModelType):
            return typeDerivedFrom.particlesList
        return self.particlesList  # empty list
    
    @property
    def baseXsdType(self):
        u"""(str) -- The xsd type localName that this type is derived from or: 
        *noContent* for an element that may not have text nodes, 
        *anyType* for an element that may have text nodes but their type is not specified, 
        or one of several union types for schema validation purposes: *XBRLI_DATEUNION*, 
        *XBRLI_DECIMALSUNION*, *XBRLI_PRECISIONUNION*, *XBRLI_NONZERODECIMAL*.
        """
        try:
            return self._baseXsdType
        except AttributeError:
            if self.qname == XbrlConst.qnXbrliDateUnion:
                self._baseXsdType = u"XBRLI_DATEUNION"
            elif self.qname == XbrlConst.qnXbrliDecimalsUnion:
                self._baseXsdType = u"XBRLI_DECIMALSUNION"
            elif self.qname == XbrlConst.qnXbrliPrecisionUnion:
                self._baseXsdType = u"XBRLI_PRECISIONUNION"
            elif self.qname == XbrlConst.qnXbrliNonZeroDecimalUnion:
                self._baseXsdType = u"XBRLI_NONZERODECIMAL"
            else:
                qnameDerivedFrom = self.qnameDerivedFrom
                if qnameDerivedFrom is None:
                    # want None if base type has no content (not mixed content, TBD)
                    #self._baseXsdType =  "anyType"
                    self._baseXsdType =  u"noContent"
                elif isinstance(qnameDerivedFrom,list): # union
                    if qnameDerivedFrom == XbrlConst.qnDateUnionXsdTypes: 
                        self._baseXsdType = u"XBRLI_DATEUNION"
                    elif len(qnameDerivedFrom) == 1:
                        qn0 = qnameDerivedFrom[0]
                        if qn0.namespaceURI == XbrlConst.xsd:
                            self._baseXsdType = qn0.localName
                        else:
                            typeDerivedFrom = self.modelXbrl.qnameTypes.get(qn0)
                            self._baseXsdType = typeDerivedFrom.baseXsdType if typeDerivedFrom is not None else u"anyType"
                    # TBD implement union types
                    else:
                        self._baseXsdType = u"anyType" 
                elif qnameDerivedFrom.namespaceURI == XbrlConst.xsd:
                    self._baseXsdType = qnameDerivedFrom.localName
                else:
                    typeDerivedFrom = self.modelXbrl.qnameTypes.get(qnameDerivedFrom)
                    #assert typeDerivedFrom is not None, _("Unable to determine derivation of {0}").format(qnameDerivedFrom)
                    self._baseXsdType = typeDerivedFrom.baseXsdType if typeDerivedFrom is not None else u"anyType"
                if self._baseXsdType == u"anyType" and XmlUtil.emptyContentModel(self):
                    self._baseXsdType = u"noContent"
            return self._baseXsdType
    
    @property
    def baseXbrliTypeQname(self):
        u"""(qname) -- The qname of the parent type in the xbrli namespace, if any, otherwise the localName of the parent in the xsd namespace."""
        try:
            return self._baseXbrliTypeQname
        except AttributeError:
            self._baseXbrliTypeQname = None
            if self.qname == XbrlConst.qnXbrliDateUnion:
                self._baseXbrliTypeQname = self.qname
            else:
                qnameDerivedFrom = self.qnameDerivedFrom
                if isinstance(qnameDerivedFrom,list): # union
                    if qnameDerivedFrom == XbrlConst.qnDateUnionXsdTypes: 
                        self._baseXbrliTypeQname = qnameDerivedFrom
                    # TBD implement union types
                    elif len(qnameDerivedFrom) == 1:
                        qn0 = qnameDerivedFrom[0]
                        if qn0.namespaceURI in (XbrlConst.xbrli, XbrlConst.xsd):
                            self._baseXbrliTypeQname = qn0
                        else:
                            typeDerivedFrom = self.modelXbrl.qnameTypes.get(qn0)
                            self._baseXbrliTypeQname = typeDerivedFrom.baseXbrliTypeQname if typeDerivedFrom is not None else None
                elif isinstance(qnameDerivedFrom, ModelValue.QName):
                    if qnameDerivedFrom.namespaceURI == XbrlConst.xbrli:  # xbrli type
                        self._baseXbrliTypeQname = qnameDerivedFrom
                    elif qnameDerivedFrom.namespaceURI == XbrlConst.xsd:    # xsd type
                        self._baseXbrliTypeQname = qnameDerivedFrom
                    else:
                        typeDerivedFrom = self.modelXbrl.qnameTypes.get(qnameDerivedFrom)
                        self._baseXbrliTypeQname = typeDerivedFrom.baseXbrliTypeQname if typeDerivedFrom is not None else None
                else:
                    self._baseXbrliType = None
            return self._baseXbrliTypeQname
    
    @property
    def baseXbrliType(self):
        u"""(str) -- The localName of the parent type in the xbrli namespace, if any, otherwise the localName of the parent in the xsd namespace."""
        try:
            return self._baseXbrliType
        except AttributeError:
            baseXbrliTypeQname = self.baseXbrliTypeQname
            if isinstance(baseXbrliTypeQname,list): # union
                if baseXbrliTypeQname == XbrlConst.qnDateUnionXsdTypes: 
                    self._baseXbrliType = u"XBRLI_DATEUNION"
                # TBD implement union types
                else:
                    self._baseXbrliType = u"anyType" 
            elif baseXbrliTypeQname is not None:
                self._baseXbrliType = baseXbrliTypeQname.localName
            else:
                self._baseXbrliType = None
            return self._baseXbrliType
    
    @property
    def isTextBlock(self):
        u"""(str) -- True if type is, or is derived from, us-types:textBlockItemType or dtr-types:escapedItemType"""
        if self.name == u"textBlockItemType" and u"/us-types/" in self.modelDocument.targetNamespace:
            return True
        if self.name == u"escapedItemType" and self.modelDocument.targetNamespace.startswith(XbrlConst.dtrTypesStartsWith):
            return True
        qnameDerivedFrom = self.qnameDerivedFrom
        if (not isinstance(qnameDerivedFrom, ModelValue.QName) or # textblock not a union type
            (qnameDerivedFrom.namespaceURI in(XbrlConst.xsd,XbrlConst.xbrli))):
            return False
        typeDerivedFrom = self.modelXbrl.qnameTypes.get(qnameDerivedFrom)
        return typeDerivedFrom.isTextBlock if typeDerivedFrom is not None else False

    @property
    def isDomainItemType(self):
        u"""(bool) -- True if type is, or is derived from, domainItemType in either a us-types or a dtr-types namespace."""
        if self.name == u"domainItemType" and \
           (u"/us-types/" in self.modelDocument.targetNamespace or
            self.modelDocument.targetNamespace.startswith(XbrlConst.dtrTypesStartsWith)):
            return True
        qnameDerivedFrom = self.qnameDerivedFrom
        if (not isinstance(qnameDerivedFrom, ModelValue.QName) or # domainItemType not a union type
            (qnameDerivedFrom.namespaceURI in(XbrlConst.xsd,XbrlConst.xbrli))):
            return False
        typeDerivedFrom = self.modelXbrl.qnameTypes.get(qnameDerivedFrom)
        return typeDerivedFrom.isDomainItemType if typeDerivedFrom is not None else False
    
    def isDerivedFrom(self, typeqname):
        u"""(bool) -- True if type is derived from type specified by QName"""
        qnamesDerivedFrom = self.qnameDerivedFrom # can be single qname or list of qnames if union
        if qnamesDerivedFrom is None:    # not derived from anything
            return typeqname is None
        if isinstance(qnamesDerivedFrom, list): # union
            if typeqname in qnamesDerivedFrom:
                return True
        else: # not union, single type
            if qnamesDerivedFrom == typeqname:
                return True
            qnamesDerivedFrom = (qnamesDerivedFrom,)
        for qnameDerivedFrom in qnamesDerivedFrom:
            typeDerivedFrom = self.modelXbrl.qnameTypes.get(qnameDerivedFrom)
            if typeDerivedFrom is not None and typeDerivedFrom.isDerivedFrom(typeqname):
                return True
        return False
        
    
    @property
    def attributes(self):
        u"""(dict) -- Dict of ModelAttribute attribute declarations keyed by attribute QName"""
        try:
            return self._attributes
        except AttributeError:
            self._attributes = {}
            attrs, attrWildcardElts, attrGroups = XmlUtil.schemaAttributesGroups(self)
            self._attributeWildcards = attrWildcardElts
            for attrRef in attrs:
                attrDecl = attrRef.dereference()
                if attrDecl is not None:
                    self._attributes[attrDecl.qname] = attrDecl
            for attrGroupRef in attrGroups:
                attrGroupDecl = attrGroupRef.dereference()
                if attrGroupDecl is not None:
                    for attrRef in attrGroupDecl.attributes.values():
                        attrDecl = attrRef.dereference()
                        if attrDecl is not None:
                            self._attributes[attrDecl.qname] = attrDecl
                    self._attributeWildcards.extend(attrGroupDecl.attributeWildcards)
            typeDerivedFrom = self.typeDerivedFrom
            for t in typeDerivedFrom if isinstance(typeDerivedFrom, list) else [typeDerivedFrom]:
                if isinstance(t, ModelType):
                    self._attributes.update(t.attributes)
                    self._attributeWildcards.extend(t.attributeWildcards)
            return self._attributes
                
    @property
    def attributeWildcards(self):
        u"""(dict) -- List of wildcard namespace strings (e.g., ##other)"""
        try:
            return self._attributeWildcards
        except AttributeError:
            self.attributes # loads attrWildcards
            return self._attributeWildcards

    @property
    def requiredAttributeQnames(self):
        u"""(set) -- Set of attribute QNames which have use=required."""
        try:
            return self._requiredAttributeQnames
        except AttributeError:
            self._requiredAttributeQnames = set(a.qname for a in self.attributes.values() if a.isRequired)
            return self._requiredAttributeQnames
            
    @property
    def defaultAttributeQnames(self):
        u"""(set) -- Set of attribute QNames which have a default specified"""
        try:
            return self._defaultAttributeQnames
        except AttributeError:
            self._defaultAttributeQnames = set(a.qname for a in self.attributes.values() if a.default is not None)
            return self._defaultAttributeQnames
            
    @property
    def elements(self):
        u"""([QName]) -- List of element QNames that are descendants (content elements)"""
        try:
            return self._elements
        except AttributeError:
            self._elements = XmlUtil.schemaDescendantsNames(self, XbrlConst.xsd, u"element")
            return self._elements
    
    @property
    def facets(self):
        u"""(dict) -- Dict of facets by their facet name, all are strings except enumeration, which is a set of enumeration values."""
        try:
            return self._facets
        except AttributeError:
            facets = self.constrainingFacets()
            self._facets = facets if facets else None
            return self._facets
    
    def constrainingFacets(self, facetValues=None):
        u"""helper function for facets discovery"""  
        facetValues = facetValues if facetValues else {}
        for facetElt in XmlUtil.schemaFacets(self, (
                    u"{http://www.w3.org/2001/XMLSchema}length", u"{http://www.w3.org/2001/XMLSchema}minLength", 
                    u"{http://www.w3.org/2001/XMLSchema}maxLength", 
                    u"{http://www.w3.org/2001/XMLSchema}pattern", u"{http://www.w3.org/2001/XMLSchema}whiteSpace",  
                    u"{http://www.w3.org/2001/XMLSchema}maxInclusive", u"{http://www.w3.org/2001/XMLSchema}minInclusive", 
                    u"{http://www.w3.org/2001/XMLSchema}maxExclusive", u"{http://www.w3.org/2001/XMLSchema}minExclusive", 
                    u"{http://www.w3.org/2001/XMLSchema}totalDigits", u"{http://www.w3.org/2001/XMLSchema}fractionDigits")):
            facetValue = XmlValidate.validateFacet(self, facetElt)
            facetName = facetElt.localName
            if facetName not in facetValues and facetValue is not None:  # facetValue can be zero but not None
                facetValues[facetName] = facetValue
        if u"enumeration" not in facetValues:
            for facetElt in XmlUtil.schemaFacets(self, (u"{http://www.w3.org/2001/XMLSchema}enumeration",)):
                facetValues.setdefault(u"enumeration",set()).add(facetElt.get(u"value"))
        typeDerivedFrom = self.typeDerivedFrom
        if isinstance(typeDerivedFrom, ModelType):
            typeDerivedFrom.constrainingFacets(facetValues)
        return facetValues
                
    def fixedOrDefaultAttrValue(self, attrName):
        u"""(str) -- Descendant attribute declaration value if fixed or default, argument is attribute name (string), e.g., 'precision'."""
        attr = XmlUtil.schemaDescendant(self, XbrlConst.xsd, u"attribute", attrName)
        if attr is not None:
            if attr.get(u"fixed"):
                return attr.get(u"fixed")
            elif attr.get(u"default"):
                return attr.get(u"default")
        return None

    def dereference(self):
        u"""(ModelType) -- If element is a ref (instead of name), provides referenced modelType object, else self"""
        return self
    
    @property
    def propertyView(self):
        return ((u"namespace", self.qname.namespaceURI),
                (u"name", self.name),
                (u"QName", self.qname),
                (u"xsd type", self.baseXsdType),
                (u"derived from", self.qnameDerivedFrom),
                (u"facits", self.facets))
        
    def __repr__(self):
        return (u"modelType[{0}, qname: {1}, derivedFrom: {2}, {3}, line {4}]"
                .format(self.objectIndex, self.qname, self.qnameDerivedFrom,
                        self.modelDocument.basename, self.sourceline))
    
class ModelGroupDefinition(ModelNamableTerm, ModelParticle):
    u"""
    .. class:: ModelGroupDefinition(modelDocument)
    
    Group definition particle term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelGroupDefinition, self).init(modelDocument)
        if self.isGlobalDeclaration:
            self.modelXbrl.qnameGroupDefinitions[self.qname] = self
        else:
            self.addToParticles()
        self.particlesList = self.particles = ParticlesList()

    def dereference(self):
        u"""(ModelGroupDefinition) -- If element is a ref (instead of name), provides referenced modelGroupDefinition object, else self"""
        ref = self.get(u"ref")
        if ref:
            qn = self.schemaNameQname(ref)
            return self.modelXbrl.qnameGroupDefinitions.get(qn)
        return self
        
    @property
    def isQualifiedForm(self):
        u"""(bool) -- True (for compatibility with other schema objects)"""
        return True
    
class ModelGroupCompositor(ModelObject, ModelParticle):
    u"""
    .. class:: ModelGroupCompositor(modelDocument)
    
    Particle Model group compositor term (sequence, choice, or all)
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelGroupCompositor, self).init(modelDocument)
        self.addToParticles()
        self.particlesList = self.particles = ParticlesList()

    def dereference(self):
        u"""(ModelGroupCompositor) -- If element is a ref (instead of name), provides referenced ModelGroupCompositor object, else self"""
        return self
        
class ModelAll(ModelGroupCompositor):
    u"""
    .. class:: ModelAll(modelDocument)
    
    Particle Model all term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelAll, self).init(modelDocument)
        
class ModelChoice(ModelGroupCompositor):
    u"""
    .. class:: ModelChoice(modelDocument)
    
    Particle Model choice term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelChoice, self).init(modelDocument)

class ModelSequence(ModelGroupCompositor):
    u"""
    .. class:: ModelSequence(modelDocument)
    
    Particle Model sequence term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelSequence, self).init(modelDocument)

class ModelAny(ModelObject, ModelParticle):
    u"""
    .. class:: ModelAny(modelDocument)
    
    Particle Model any term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelAny, self).init(modelDocument)
        self.addToParticles()

    def dereference(self):
        return self
        
    def allowsNamespace(self, namespaceURI):
        try:
            if self._isAny:
                return True
            if not namespaceURI:
                return u"##local" in self._namespaces
            if namespaceURI in self._namespaces:
                return True
            if namespaceURI == self.modelDocument.targetNamespace:
                if u"##targetNamespace" in self._namespaces:
                    return True
            else: # not equal namespaces
                if u"##other" in self._namespaces:
                    return True
            return False        
        except AttributeError:
            self._namespaces = self.get(u"namespace", u'').split()
            self._isAny = (not self._namespaces) or u"##any" in self._namespaces
            return self.allowsNamespace(namespaceURI)

class ModelAnyAttribute(ModelObject):
    u"""
    .. class:: ModelAnyAttribute(modelDocument)
    
    Any attribute definition term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelAnyAttribute, self).init(modelDocument)
        
    def allowsNamespace(self, namespaceURI):
        try:
            if self._isAny:
                return True
            if not namespaceURI:
                return u"##local" in self._namespaces
            if namespaceURI in self._namespaces:
                return True
            if namespaceURI == self.modelDocument.targetNamespace:
                if u"##targetNamespace" in self._namespaces:
                    return True
            else: # not equal namespaces
                if u"##other" in self._namespaces:
                    return True
            return False        
        except AttributeError:
            self._namespaces = self.get(u"namespace", u'').split()
            self._isAny = (not self._namespaces) or u"##any" in self._namespaces
            return self.allowsNamespace(namespaceURI)

class ModelEnumeration(ModelNamableTerm):
    u"""
    .. class:: ModelEnumeration(modelDocument)
    
    Facet enumeration term
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelEnumeration, self).init(modelDocument)
        
    @property
    def value(self):
        return self.get(u"value")
    
class ModelLink(ModelObject):
    u"""
    .. class:: ModelLink(modelDocument)
    
    XLink extended link element
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelLink, self).init(modelDocument)
        self.labeledResources = defaultdict(list)
        
    @property
    def role(self):
        return self.get(u"{http://www.w3.org/1999/xlink}role")

class ModelResource(ModelObject):
    u"""
    .. class:: ModelResource(modelDocument)
    
    XLink resource element
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelResource, self).init(modelDocument)
        if self.xmlLang:
            self.modelXbrl.langs.add(self.xmlLang)
        if self.localName == u"label":
            self.modelXbrl.labelroles.add(self.role)
        
    @property
    def role(self):
        u"""(str) -- xlink:role attribute"""
        return self.get(u"{http://www.w3.org/1999/xlink}role")
        
    @property
    def xlinkLabel(self):
        u"""(str) -- xlink:label attribute"""
        return self.get(u"{http://www.w3.org/1999/xlink}label")

    @property
    def xmlLang(self):
        u"""(str) -- xml:lang attribute"""
        return XmlUtil.ancestorOrSelfAttr(self, u"{http://www.w3.org/XML/1998/namespace}lang")
    
    def viewText(self, labelrole=None, lang=None):
        u"""(str) -- Text of contained (inner) text nodes except for any whose localName 
        starts with URI, for label and reference parts displaying purposes."""
        return u" ".join([XmlUtil.text(resourceElt)
                           for resourceElt in self.iter()
                              if isinstance(resourceElt,ModelObject) and 
                                  not resourceElt.localName.startswith(u"URI")])
    def dereference(self):
        return self
        
class ModelLocator(ModelResource):
    u"""
    .. class:: ModelLocator(modelDocument)
    
    XLink locator element
    
    :param modelDocument: owner document
    :type modelDocument: ModelDocument
    """
    def init(self, modelDocument):
        super(ModelLocator, self).init(modelDocument)
    
    def dereference(self):
        u"""(ModelObject) -- Resolve loc's href if resource is a loc with href document and id modelHref a tuple with 
        href's element, modelDocument, id"""
        return self.resolveUri(self.modelHref)
    
    @property
    def propertyView(self):
        global ModelFact
        if ModelFact is None:
            from arelle.ModelInstanceObject import ModelFact
        hrefObj = self.dereference()
        if isinstance(hrefObj,(ModelFact,ModelConcept)):
            return ((u"href", hrefObj.qname ), )
        elif isinstance(hrefObj, ModelResource):
            return ((u"href", hrefObj.viewText()),)
        else:
            return hrefObj.propertyView

class RelationStatus(object):
    Unknown = 0
    EFFECTIVE = 1
    OVERRIDDEN = 2
    PROHIBITED = 3
    INEFFECTIVE = 4
    
arcCustAttrsExclusions = set([XbrlConst.xlink, u"use",u"priority",u"order",u"weight",u"preferredLabel"])
    
class ModelRelationship(ModelObject):
    u"""
    .. class:: ModelRelationship(modelDocument, arcElement, fromModelObject, toModelObject)
    
    ModelRelationship is a ModelObject that does not proxy an lxml object (but instead references 
    ModelObject arc elements, and the from and to ModelObject elements.
    
    :param modelDocument: Owning modelDocument object
    :type modelDocument: ModelDocument
    :param arcElement: lxml arc element that was resolved into this relationship object
    :type arcElement: ModelObject
    :param fromModelObject: the from lxml resource element of the source of the relationship
    :type fromModelObject: ModelObject
    :param toModelObject: the to lxml resource element of the target of the relationship
    :type toModelObject: ModelObject
    
    Includes properties that proxy the referenced modelArc: localName, namespaceURI, prefixedName, sourceline, tag, elementQname, qname,
    and methods that proxy methods of modelArc: get() and itersiblings()    

        .. attribute:: arcElement
        
        ModelObject arc element of the effective relationship

        .. attribute:: fromModelObject
        
        ModelObject of the xlink:from (dereferenced if via xlink:locator)

        .. attribute:: toModelObject

        ModelObject of the xlink:to (dereferenced if via xlink:locator)
    """
    def __init__(self, modelDocument, arcElement, fromModelObject, toModelObject):
        # copy model object properties from arcElement
        self.arcElement = arcElement
        self.init(modelDocument)
        self.fromModelObject = fromModelObject
        self.toModelObject = toModelObject
        
    def clear(self):
        self.__dict__.clear() # dereference here, not an lxml object, don't use superclass clear()
        
    # simulate etree operations
    def get(self, attrname):
        u"""Method proxy for the arc element of the effective relationship so that the non-proxy 
        """
        return self.arcElement.get(attrname)
    
    @property
    def localName(self):
        u"""(str) -- Property proxy for localName of arc element"""
        return self.arcElement.localName
        
    @property
    def namespaceURI(self):
        u"""(str) -- Property proxy for namespaceURI of arc element"""
        return self.arcElement.namespaceURI
        
    @property
    def prefixedName(self):
        u"""(str) -- Property proxy for prefixedName of arc element"""
        return self.arcElement.prefixedName
        
    @property
    def sourceline(self):
        u"""(int) -- Property proxy for sourceline of arc element"""
        return self.arcElement.sourceline
        
    @property
    def tag(self):
        u"""(str) -- Property proxy for tag of arc element (clark notation)"""
        return self.arcElement.tag
    
    @property
    def elementQname(self):
        u"""(QName) -- Property proxy for elementQName of arc element"""
        return self.arcElement.elementQname
        
    @property
    def qname(self):
        u"""(QName) -- Property proxy for qname of arc element"""
        return self.arcElement.qname
    
    def itersiblings(self, **kwargs):
        u"""Method proxy for itersiblings() of lxml arc element"""
        return self.arcElement.itersiblings(**kwargs)
        
    def getparent(self):
        u"""(_ElementBase) -- Method proxy for getparent() of lxml arc element"""
        return self.arcElement.getparent()
        
    @property
    def fromLabel(self):
        u"""(str) -- Value of xlink:from attribute"""
        return self.arcElement.get(u"{http://www.w3.org/1999/xlink}from")
        
    @property
    def toLabel(self):
        u"""(str) -- Value of xlink:to attribute"""
        return self.arcElement.get(u"{http://www.w3.org/1999/xlink}to")
        
    @property
    def fromLocator(self):
        u"""(ModelLocator) -- Value of locator surrogate of relationship source, if any"""
        for fromResource in self.arcElement.getparent().labeledResources[self.fromLabel]:
            if isinstance(fromResource, ModelLocator) and self.fromModelObject is fromResource.dereference():
                return fromResource
        return None
        
    @property
    def toLocator(self):
        u"""(ModelLocator) -- Value of locator surrogate of relationship target, if any"""
        for toResource in self.arcElement.getparent().labeledResources[self.toLabel]:
            if isinstance(toResource, ModelLocator) and self.toModelObject is toResource.dereference():
                return toResource
        return None
    
    def locatorOf(self, dereferencedObject):
        u"""(ModelLocator) -- Value of locator surrogate of relationship target, if any"""
        fromLocator = self.fromLocator
        if fromLocator is not None and fromLocator.dereference() == dereferencedObject:
            return fromLocator
        toLocator = self.toLocator
        if toLocator is not None and toLocator.dereference() == dereferencedObject:
            return toLocator
        return None
        
    @property
    def arcrole(self):
        u"""(str) -- Value of xlink:arcrole attribute"""
        return self.arcElement.get(u"{http://www.w3.org/1999/xlink}arcrole")

    @property
    def order(self):
        u"""(float) -- Value of xlink:order attribute, or 1.0 if not specified"""
        try:
            return self.arcElement._order
        except AttributeError:
            o = self.arcElement.get(u"order")
            if o is None:
                order = 1.0
            else:
                try:
                    order = float(o)
                except (TypeError,ValueError) :
                    order = float(u"nan")
            self.arcElement._order = order
            return order

    @property
    def orderDecimal(self):
        u"""(decimal) -- Value of xlink:order attribute, NaN if not convertable to float, or None if not specified"""
        try:
            return decimal.Decimal(self.order)
        except decimal.InvalidOperation:
            return decimal.Decimal(u"NaN")

    @property
    def priority(self):
        u"""(int) -- Value of xlink:order attribute, or 0 if not specified"""
        try:
            return self.arcElement._priority
        except AttributeError:
            p = self.arcElement.get(u"priority")
            if p is None:
                priority = 0
            else:
                try:
                    priority = _INT(p)
                except (TypeError,ValueError) :
                    # XBRL validation error needed
                    priority = 0
            self.arcElement._priority = priority
            return priority

    @property
    def weight(self):
        u"""(float) -- Value of xlink:weight attribute, NaN if not convertable to float, or None if not specified"""
        try:
            return self.arcElement._weight
        except AttributeError:
            w = self.arcElement.get(u"weight")
            if w is None:
                weight = None
            else:
                try:
                    weight = float(w)
                except (TypeError,ValueError) :
                    # XBRL validation error needed
                    weight = float(u"nan")
            self.arcElement._weight = weight
            return weight

    @property
    def weightDecimal(self):
        u"""(decimal) -- Value of xlink:weight attribute, NaN if not convertable to float, or None if not specified"""
        try:
            return self.arcElement._weightDecimal
        except AttributeError:
            w = self.arcElement.get(u"weight")
            if w is None:
                weight = None
            else:
                try:
                    weight = decimal.Decimal(w)
                except (TypeError,ValueError,decimal.InvalidOperation) :
                    # XBRL validation error needed
                    weight = decimal.Decimal(u"nan")
            self.arcElement._weightDecimal = weight
            return weight

    @property
    def use(self):
        u"""(str) -- Value of use attribute"""
        return self.get(u"use")
    
    @property
    def isProhibited(self):
        u"""(bool) -- True if use is prohibited"""
        return self.use == u"prohibited"
    
    @property
    def prohibitedUseSortKey(self):
        u"""(int) -- 2 if use is prohibited, else 1, for use in sorting effective arcs before prohibited arcs"""
        return 2 if self.isProhibited else 1
    
    @property
    def preferredLabel(self):
        u"""(str) -- preferredLabel attribute or None if absent"""
        return self.get(u"preferredLabel")

    @property
    def variablename(self):
        u"""(str) -- name attribute"""
        return self.getStripped(u"name")

    @property
    def variableQname(self):
        u"""(QName) -- resolved name for a formula (or other arc) having a QName name attribute"""
        varName = self.variablename
        return ModelValue.qname(self.arcElement, varName, noPrefixIsNoNamespace=True) if varName else None

    @property
    def linkrole(self):
        u"""(str) -- Value of xlink:role attribute of parent extended link element"""
        return self.arcElement.getparent().get(u"{http://www.w3.org/1999/xlink}role")
    
    @property
    def linkQname(self):
        u"""(QName) -- qname of the parent extended link element"""
        return self.arcElement.getparent().elementQname
    
    @property
    def contextElement(self):
        u"""(str) -- Value of xbrldt:contextElement attribute (on applicable XDT arcs)"""
        return self.get(u"{http://xbrl.org/2005/xbrldt}contextElement")
    
    @property
    def targetRole(self):
        u"""(str) -- Value of xbrldt:targetRole attribute (on applicable XDT arcs)"""
        return self.get(u"{http://xbrl.org/2005/xbrldt}targetRole")
    
    @property
    def consecutiveLinkrole(self):
        u"""(str) -- Value of xbrldt:targetRole attribute, if provided, else parent linkRole (on applicable XDT arcs)"""
        return self.targetRole or self.linkrole
    
    @property
    def isUsable(self):
        u"""(bool) -- True if xbrldt:usable is true (on applicable XDT arcs, defaults to True if absent)"""
        return self.get(u"{http://xbrl.org/2005/xbrldt}usable") in (u"true",u"1", None)
    
    @property
    def closed(self):
        u"""(str) -- Value of xbrldt:closed (on applicable XDT arcs, defaults to 'false' if absent)"""
        return self.get(u"{http://xbrl.org/2005/xbrldt}closed") or u"false"
    
    @property
    def isClosed(self):
        u"""(bool) -- True if xbrldt:closed is true (on applicable XDT arcs, defaults to False if absent)"""
        try:
            return self._isClosed
        except AttributeError:
            self._isClosed = self.get(u"{http://xbrl.org/2005/xbrldt}closed") in (u"true",u"1")
            return self._isClosed

    @property
    def usable(self):
        u"""(str) -- Value of xbrldt:usable (on applicable XDT arcs, defaults to 'true' if absent)"""
        try:
            return self._usable
        except AttributeError:
            if self.arcrole in (XbrlConst.dimensionDomain, XbrlConst.domainMember):
                self._usable = self.get(u"{http://xbrl.org/2005/xbrldt}usable") or u"true"
            else:
                self._usable = None
            return self._usable

    @property
    def isComplemented(self):
        u"""(bool) -- True if complemented is true (on applicable formula/rendering arcs, defaults to False if absent)"""
        try:
            return self._isComplemented
        except AttributeError:
            self._isComplemented = self.get(u"complement") in (u"true",u"1")
            return self._isComplemented
    
    @property
    def isCovered(self):
        u"""(bool) -- True if cover is true (on applicable formula/rendering arcs, defaults to False if absent)"""
        try:
            return self._isCovered
        except AttributeError:
            self._isCovered = self.get(u"cover") in (u"true",u"1")
            return self._isCovered
        
    @property
    def axisDisposition(self):
        u"""(str) -- Value of axisDisposition (on applicable table linkbase arcs"""
        try:
            return self._tableAxis
        except AttributeError:
            aType = (self.get(u"axis") or # XII 2013
                     self.get(u"axisDisposition") or # XII 2011
                     self.get(u"axisType"))  # Eurofiling
            if aType in (u"xAxis",u"x"): self._axisDisposition = u"x"
            elif aType in (u"yAxis",u"y"): self._axisDisposition = u"y"
            elif aType in (u"zAxis",u"z"): self._axisDisposition = u"z"
            else: self._axisDisposition = None
            return self._axisDisposition
        
    @property
    def equivalenceHash(self): # not exact, use equivalenceKey if hashes are the same
        return hash((self.qname, 
                     self.linkQname,
                     self.linkrole,  # needed when linkrole=None merges multiple links
                     self.fromModelObject.objectIndex if self.fromModelObject is not None else -1, 
                     self.toModelObject.objectIndex if self.toModelObject is not None else -1, 
                     self.order, 
                     self.weight, 
                     self.preferredLabel))
        
    @property
    def equivalenceKey(self):
        u"""(tuple) -- Key to determine relationship equivalence per 2.1 spec"""
        # cannot be cached because this is unique per relationship
        return (self.qname, 
                self.linkQname,
                self.linkrole,  # needed when linkrole=None merges multiple links
                self.fromModelObject.objectIndex if self.fromModelObject is not None else -1, 
                self.toModelObject.objectIndex if self.toModelObject is not None else -1, 
                self.order, 
                self.weight, 
                self.preferredLabel) + \
                XbrlUtil.attributes(self.modelXbrl, self.arcElement, 
                    exclusions=arcCustAttrsExclusions, keyByTag=True) # use clark tag for key instead of qname
                
    def isIdenticalTo(self, otherModelRelationship):
        u"""(bool) -- Determines if relationship is identical to another, based on arc and identical from and to objects"""
        return (otherModelRelationship is not None and
                self.arcElement == otherModelRelationship.arcElement and
                self.fromModelObject is not None and otherModelRelationship.fromModelObject is not None and
                self.toModelObject is not None and otherModelRelationship.toModelObject is not None and
                self.fromModelObject == otherModelRelationship.fromModelObject and
                self.toModelObject == otherModelRelationship.toModelObject)

    def priorityOver(self, otherModelRelationship):
        u"""(bool) -- True if this relationship has priority over other relationship"""
        if otherModelRelationship is None:
            return True
        priority = self.priority
        otherPriority = otherModelRelationship.priority
        if priority > otherPriority:
            return True
        elif priority < otherPriority:
            return False
        if otherModelRelationship.isProhibited:
            return False
        return True
    
    @property
    def propertyView(self):
        return self.toModelObject.propertyView + \
               ((u"arcrole", self.arcrole),
                (u"weight", self.weight) if self.arcrole == XbrlConst.summationItem else (),
                (u"preferredLabel", self.preferredLabel)  if self.arcrole == XbrlConst.parentChild and self.preferredLabel else (),
                (u"contextElement", self.contextElement)  if self.arcrole in (XbrlConst.all, XbrlConst.notAll)  else (),
                (u"typedDomain", self.toModelObject.typedDomainElement.qname)  
                  if self.arcrole == XbrlConst.hypercubeDimension and
                     isinstance(self.toModelObject,ModelConcept) and
                     self.toModelObject.isTypedDimension and 
                     self.toModelObject.typedDomainElement is not None  else (),
                (u"closed", self.closed) if self.arcrole in (XbrlConst.all, XbrlConst.notAll)  else (),
                (u"usable", self.usable) if self.arcrole == XbrlConst.domainMember  else (),
                (u"targetRole", self.targetRole) if self.arcrole.startswith(XbrlConst.dimStartsWith) else (),
                (u"order", self.order),
                (u"priority", self.priority)) + \
               ((u"from", self.fromModelObject.qname),) if isinstance(self.fromModelObject,ModelConcept) else ()
        
    def __repr__(self):
        return (u"modelRelationship[{0}, linkrole: {1}, arcrole: {2}, from: {3}, to: {4}, {5}, line {6}]"
                .format(self.objectIndex, os.path.basename(self.linkrole), os.path.basename(self.arcrole),
                        self.fromModelObject.qname if self.fromModelObject is not None else u"??",
                        self.toModelObject.qname if self.toModelObject is not None else u"??",
                        self.modelDocument.basename, self.sourceline))

    @property
    def viewConcept(self):
        if isinstance(self.toModelObject, ModelConcept):
            return self.toModelObject
        elif isinstance(self.fromModelObject, ModelConcept):
            return self.fromModelObject
        return None
           
from arelle.ModelObjectFactory import elementSubstitutionModelClass
elementSubstitutionModelClass.update((
     (XbrlConst.qnXlExtended, ModelLink),
     (XbrlConst.qnXlLocator, ModelLocator),
     (XbrlConst.qnXlResource, ModelResource),
    ))
