u'''
Created on Nov 9, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from arelle import XmlUtil, XbrlConst
from arelle.ModelObject import ModelObject
from arelle.ModelValue import qname


def relateConceptMdlObjs(modelDocument, fromConceptMdlObjs, toConceptMdlObjs):
    for fromConceptMdlObj in fromConceptMdlObjs:
        fromConcept = fromConceptMdlObj
        if fromConcept is not None:
            fromConceptQname = fromConcept.qname
            for toConceptMdlObj in toConceptMdlObjs:
                toConcept = toConceptMdlObj.toConcept
                if toConcept is not None:
                    toConceptQname = toConcept.qname
                    modelDocument.relatedConcepts[fromConceptQname].add(toConceptQname)

class ModelVersObject(ModelObject):
    def init(self, modelDocument):
        super(ModelVersObject, self).init(modelDocument)
        
    @property
    def name(self):
        return self.localName

    def viewText(self, labelrole=None, lang=None):
        return u''

class ModelAssignment(ModelVersObject):
    def init(self, modelDocument):
        super(ModelAssignment, self).init(modelDocument)
        self.modelDocument.assignments[self.id] = self
        
    @property
    def categoryqname(self):
        for child in self.iterchildren():
            if isinstance(child, ModelObject):
                return u"{" + child.namespaceURI + u"}" + child.localName

    @property
    def categoryQName(self):
        for child in self.iterchildren():
            if isinstance(child, ModelObject):
                return child.prefixedName
        return None

    @property
    def propertyView(self):
        return ((u"id", self.id),
                (u"label", self.genLabel()),
                (u"category", self.categoryQName))

class ModelAction(ModelVersObject):
    def init(self, modelDocument):
        super(ModelAction, self).init(modelDocument)
        actionKey = self.id if self.id else u"action{0:05}".format(len(self.modelDocument.actions) + 1)
        self.modelDocument.actions[actionKey] = self
        self.events = []
        
    @property
    def assignmentRefs(self):
        return XmlUtil.childrenAttrs(self, XbrlConst.ver, u"assignmentRef", u"ref")
        
    @property
    def propertyView(self):
        return ((u"id", self.id),
                (u"label", self.genLabel()),
                (u"assgnmts", self.assignmentRefs))

class ModelUriMapped(ModelVersObject):
    def init(self, modelDocument):
        super(ModelUriMapped, self).init(modelDocument)
        
    @property
    def fromURI(self):
        return XmlUtil.childAttr(self, XbrlConst.ver, u"fromURI", u"value")
        
    @property
    def toURI(self):
        return XmlUtil.childAttr(self, XbrlConst.ver, u"toURI", u"value")

    @property
    def propertyView(self):
        return ((u"fromURI", self.fromURI),
                (u"toURI", self.toURI))
        
    def viewText(self, labelrole=None, lang=None):
        return u"{0} -> {1}".format(self.fromURI, self.toURI)
    
class ModelNamespaceRename(ModelUriMapped):
    def init(self, modelDocument):
        super(ModelNamespaceRename, self).init(modelDocument)
        self.modelDocument.namespaceRenameFrom[self.fromURI] = self
        self.modelDocument.namespaceRenameFromURI[self.fromURI] = self.toURI
        self.modelDocument.namespaceRenameTo[self.toURI] = self
        self.modelDocument.namespaceRenameToURI[self.toURI] = self.fromURI
        
class ModelRoleChange(ModelUriMapped):
    def init(self, modelDocument):
        super(ModelRoleChange, self).init(modelDocument)
        self.modelDocument.roleChanges[self.fromURI] = self

class ModelConceptChange(ModelVersObject):
    def init(self, modelDocument):
        super(ModelConceptChange, self).init(modelDocument)
        
    @property
    def actionId(self):
        return XmlUtil.parentId(self, XbrlConst.ver, u"action")
    
    @property
    def physical(self):
        return self.get(u"physical") or u"true" # default="true"
    
    @property
    def isPhysical(self):
        return self.physical == u"true"
    
    @property
    def fromConceptQname(self):
        fromConcept = XmlUtil.child(self, None, u"fromConcept") # can be vercu or vercb, schema validation will assure right elements
        if fromConcept is not None and fromConcept.get(u"name"):
            return qname(fromConcept, fromConcept.get(u"name"))
        else:
            return None
        
    @property
    def toConceptQname(self):
        toConcept = XmlUtil.child(self, None, u"toConcept")
        if toConcept is not None and toConcept.get(u"name"):
            return qname(toConcept, toConcept.get(u"name"))
        else:
            return None
        
    @property
    def fromConcept(self):
        # for href: return self.resolveUri(uri=self.fromConceptValue, dtsModelXbrl=self.modelDocument.fromDTS)
        return self.modelDocument.fromDTS.qnameConcepts.get(self.fromConceptQname)
    
    @property
    def toConcept(self):
        # return self.resolveUri(uri=self.toConceptValue, dtsModelXbrl=self.modelDocument.toDTS)
        return self.modelDocument.toDTS.qnameConcepts.get(self.toConceptQname)
        
    def setConceptEquivalence(self):
        if self.fromConcept is not None and self.toConcept is not None:
            self.modelDocument.equivalentConcepts[self.fromConcept.qname] = self.toConcept.qname

    @property
    def propertyView(self):
        fromConcept = self.fromConcept
        toConcept = self.toConcept
        return ((u"event", self.localName),
                 (u"fromConcept", fromConcept.qname) if fromConcept is not None else (),
                 (u"toConcept", toConcept.qname) if toConcept is not None else (),
                )

    def viewText(self, labelrole=XbrlConst.conceptNameLabelRole, lang=None):
        fromConceptQname = self.fromConceptQname
        fromConcept = self.fromConcept
        toConceptQname = self.toConceptQname
        toConcept = self.toConcept
        if (labelrole != XbrlConst.conceptNameLabelRole and
            (fromConceptQname is None or (fromConceptQname is not None and fromConcept is not None)) and
            (toConceptQname is None or (toConceptQname is not None and toConcept is not None))):
            if fromConceptQname is not None:
                if toConceptQname is not None:
                    return self.fromConcept.label(labelrole,True,lang) + u" -> " + self.toConcept.label(labelrole,True,lang)
                else:
                    return self.fromConcept.label(labelrole,True,lang)
            elif toConceptQname is not None:
                return self.toConcept.label(labelrole,True,lang)
            else:
                return u"(invalidConceptReference)"
        else:
            if fromConceptQname is not None:
                if toConceptQname is not None:
                    if toConceptQname.localName != fromConceptQname.localName:
                        return unicode(fromConceptQname) + u" -> " + unicode(toConceptQname)
                    else:
                        return u"( " + fromConceptQname.prefix + u": -> " + toConceptQname.prefix + u": ) " + toConceptQname.localName
                else:
                    return unicode(fromConceptQname)
            elif toConceptQname is not None:
                return unicode(toConceptQname)
            else:
                return u"(invalidConceptReference)"
            

class ModelConceptUseChange(ModelConceptChange):
    def init(self, modelDocument):
        super(ModelConceptUseChange, self).init(modelDocument)
        self.modelDocument.conceptUseChanges.append(self)
            
        
class ModelConceptDetailsChange(ModelConceptChange):
    def init(self, modelDocument):
        super(ModelConceptDetailsChange, self).init(modelDocument)
        self.modelDocument.conceptDetailsChanges.append(self)
        
    def customAttributeQname(self, eventName):
        custAttrElt = XmlUtil.child(self, None, eventName) # will be vercd or verce
        if custAttrElt is not None and custAttrElt.get(u"name"):
            return qname(custAttrElt, custAttrElt.get(u"name"))
        return None
        
    @property
    def fromCustomAttributeQname(self):
        return self.customAttributeQname(u"fromCustomAttribute")
        
    @property
    def toCustomAttributeQname(self):
        return self.customAttributeQname(u"toCustomAttribute")
        
    @property
    def fromResourceValue(self):
        return XmlUtil.childAttr(self, None, u"fromResource", u"value")
        
    @property
    def toResourceValue(self):
        return XmlUtil.childAttr(self, None, u"toResource", u"value")
        
    @property
    def fromResource(self):
        return self.resolveUri(uri=self.fromResourceValue, dtsModelXbrl=self.modelDocument.fromDTS)
        
    @property
    def toResource(self):
        return self.resolveUri(uri=self.toResourceValue, dtsModelXbrl=self.modelDocument.toDTS)
        
    @property
    def propertyView(self):
        fromConcept = self.fromConcept
        toConcept = self.toConcept
        fromCustomAttributeQname = self.fromCustomAttributeQname
        toCustomAttributeQname = self.toCustomAttributeQname
        return ((u"event", self.localName),
                 (u"fromConcept", fromConcept.qname) if fromConcept is not None else (),
                 (u"fromCustomAttribute", fromCustomAttributeQname) if fromCustomAttributeQname is not None else (),
                 (u"fromResource", self.fromResource.viewText() if self.fromResource is not None else u"(invalidContentResourceIdentifier)") if self.fromResourceValue else (),
                 (u"toConcept", toConcept.qname) if toConcept is not None else (),
                 (u"toCustomAttribute", toCustomAttributeQname) if toCustomAttributeQname is not None else (),
                 (u"toResource", self.toResource.viewText() if self.toResource is not None else u"(invalidContentResourceIdentifier)") if self.toResourceValue else (),
                )

class ModelRelationshipSetChange(ModelVersObject):
    def init(self, modelDocument):
        super(ModelRelationshipSetChange, self).init(modelDocument)
        self.modelDocument.relationshipSetChanges.append(self)
        self.fromRelationshipSet = None
        self.toRelationshipSet = None
        
    @property
    def propertyView(self):
        return ((u"event", self.localName),
                )

class ModelRelationshipSet(ModelVersObject):
    def init(self, modelDocument):
        super(ModelRelationshipSet, self).init(modelDocument)
        self.relationships = []
        
    @property
    def isFromDTS(self):
        return self.localName == u"fromRelationshipSet"
        
    @property
    def dts(self):
        return self.modelDocument.fromDTS if self.isFromDTS else self.modelDocument.toDTS
        
    @property
    def relationshipSetElement(self):
        return XmlUtil.child(self, XbrlConst.verrels, u"relationshipSet")

    @property
    def link(self):
        if self.relationshipSetElement.get(u"link"):
            return self.prefixedNameQname(self.relationshipSetElement.get(u"link"))
        else:
            return None
        
    @property
    def linkrole(self):
        if self.relationshipSetElement.get(u"linkrole"):
            return self.relationshipSetElement.get(u"linkrole")
        else:
            return None
        
    @property
    def arc(self):
        if self.relationshipSetElement.get(u"arc"):
            return self.prefixedNameQname(self.relationshipSetElement.get(u"arc"))
        else:
            return None
        
    @property
    def arcrole(self):
        if self.relationshipSetElement.get(u"arcrole"):
            return self.relationshipSetElement.get(u"arcrole")
        else:
            return None
        
    @property
    def propertyView(self):
        return self.modelRelationshipSetEvent.propertyView + \
               ((u"model", self.localName),
                (u"link", unicode(self.link)) if self.link else (),
                (u"linkrole", self.linkrole) if self.linkrole else (),
                (u"arc", unicode(self.arc)) if self.arc else (),
                (u"arcrole", self.arcrole) if self.arcrole else (),
                )

class ModelRelationships(ModelVersObject):
    def init(self, modelDocument):
        super(ModelRelationships, self).init(modelDocument)
        
    @property
    def fromName(self):
        if self.get(u"fromName"):
            return self.prefixedNameQname(self.get(u"fromName"))
        else:
            return None
        
    @property
    def toName(self):
        return self.prefixedNameQname(self.get(u"toName")) if self.get(u"toName") else None
        
    @property
    def fromConcept(self):
        # for href: return self.resolveUri(uri=self.fromConceptValue, dtsModelXbrl=self.modelDocument.fromDTS)
        return self.modelRelationshipSet.dts.qnameConcepts.get(self.fromName) if self.fromName else None
    
    @property
    def toConcept(self):
        # return self.resolveUri(uri=self.toConceptValue, dtsModelXbrl=self.modelDocument.toDTS)
        return self.modelRelationshipSet.dts.qnameConcepts.get(self.toName) if self.toName else None
        
    @property
    def axis(self):
        if self.get(u"axis"):
            return self.get(u"axis")
        else:
            return None
        
    @property
    def isFromDTS(self):
        return self.modelRelationshipSet.isFromDTS
        
    @property
    def fromRelationships(self):
        mdlRel = self.modelRelationshipSet
        relSet = mdlRel.dts.relationshipSet(mdlRel.arcrole, mdlRel.linkrole, mdlRel.link, mdlRel.arc)
        if relSet:
            return relSet.fromModelObject(self.fromConcept)
        return None
        
    @property
    def fromRelationship(self):
        fromRelationships = self.fromRelationships
        if not fromRelationships:
            return None
        toName = self.toName
        if self.toName:
            for rel in fromRelationships:
                if rel.toModelObject.qname == toName:
                    return rel
            return None
        else:   # return first (any) relationship
            return fromRelationships[0]
        
    @property
    def propertyView(self):
        return self.modelRelationshipSet.propertyView + \
                ((u"fromName", self.fromName) if self.fromName else (),
                 (u"toName", self.toName) if self.toName else (),
                 (u"axis", self.axis) if self.axis else (),
                )

class ModelInstanceAspectsChange(ModelVersObject):
    def init(self, modelDocument):
        super(ModelInstanceAspectsChange, self).init(modelDocument)
        self.modelDocument.instanceAspectChanges.append(self)
        self.fromAspects = None
        self.toAspects = None
        
    @property
    def propertyView(self):
        return ((u"event", self.localName),
                )

class ModelInstanceAspects(ModelVersObject):
    def init(self, modelDocument):
        super(ModelInstanceAspects, self).init(modelDocument)
        self.aspects = []
        
    @property
    def isFromDTS(self):
        return self.localName == u"fromAspects"
        
    @property
    def dts(self):
        return self.modelDocument.fromDTS if self.isFromDTS else self.modelDocument.toDTS
        
    @property
    def excluded(self):
        return self.get(u"excluded") if self.get(u"excluded") else None
        
    @property
    def propertyView(self):
        return self.aspectModelEvent.propertyView + \
               ((u"excluded", self.excluded) if self.excluded else (),
                )

class ModelInstanceAspect(ModelVersObject):
    def init(self, modelDocument):
        super(ModelInstanceAspect, self).init(modelDocument)
        self.aspectProperties = []

    @property
    def isFromDTS(self):
        return self.modelAspects.isFromDTS
    
    @property
    def propertyView(self):
        return self.modelAspects.propertyView + \
               ((u"aspect", self.localName),
                ) + self.elementAttributesTuple
                
class ModelConceptsDimsAspect(ModelInstanceAspect):
    def init(self, modelDocument):
        super(ModelConceptsDimsAspect, self).init(modelDocument)
        self.relatedConcepts = []

    @property
    def conceptName(self):
        return self.prefixedNameQname(self.get(u"name")) if self.get(u"name") else None
        
    @property
    def concept(self):
        # for href: return self.resolveUri(uri=self.fromConceptValue, dtsModelXbrl=self.modelDocument.fromDTS)
        return self.modelAspects.dts.qnameConcepts.get(self.conceptName) if self.conceptName else None
    
    @property
    def sourceDtsObject(self):
        if self.localName == u"explicitDimension":
            return self.concept
        return None

class ModelPeriodAspect(ModelInstanceAspect):
    def init(self, modelDocument):
        super(ModelPeriodAspect, self).init(modelDocument)
        self.relatedPeriods = []

class ModelMeasureAspect(ModelInstanceAspect):
    def init(self, modelDocument):
        super(ModelMeasureAspect, self).init(modelDocument)
        self.relatedMeasures = []



# this class is both for explicitDimension member and concepts concept elements
class ModelRelatedConcept(ModelVersObject):
    def init(self, modelDocument):
        super(ModelRelatedConcept, self).init(modelDocument)
        
    @property
    def conceptName(self):
        return self.prefixedNameQname(self.get(u"name")) if self.get(u"name") else None
        
    @property
    def concept(self):
        # for href: return self.resolveUri(uri=self.fromConceptValue, dtsModelXbrl=self.modelDocument.fromDTS)
        return self.modelAspect.modelAspects.dts.qnameConcepts.get(self.conceptName) if self.conceptName else None
    
    @property
    def sourceDtsObject(self):
        return self.concept

    @property
    def isFromDTS(self):
        return self.modelAspect.modelAspects.isFromDTS
    
    @property
    def hasNetwork(self):
        return XmlUtil.hasChild(self, XbrlConst.verdim, u"network")
    
    @property
    def hasDrsNetwork(self):
        return XmlUtil.hasChild(self, XbrlConst.verdim, u"drsNetwork")
    
    @property
    def arcrole(self):
        return XmlUtil.childAttr(self, XbrlConst.verdim, (u"network",u"drsNetwork"), u"arcrole")
    
    @property
    def linkrole(self):
        return XmlUtil.childAttr(self, XbrlConst.verdim, (u"network",u"drsNetwork"), u"linkrole")
    
    @property
    def arc(self):
        arc = XmlUtil.childAttr(self, XbrlConst.verdim, (u"network",u"drsNetwork"), u"arc")
        return self.prefixedNameQname(arc) if arc else None
    
    @property
    def link(self):
        link = XmlUtil.childAttr(self, XbrlConst.verdim, (u"network",u"drsNetwork"), u"link")
        return self.prefixedNameQname(link) if link else None
    
    @property
    def propertyView(self):
        return self.modelAspect.propertyView + \
               ((self.localName, u''),
                ) + self.elementAttributesTuple

# this class is both for properties of aspects period and measure
class ModelAspectProperty(ModelVersObject):
    def init(self, modelDocument):
        super(ModelRelatedConcept, self).init(modelDocument)
        
    @property
    def propertyView(self):
        return self.modelAspect.propertyView + \
               ((self.localName, u''),
                ) + self.elementAttributesTuple

from arelle.ModelObjectFactory import elementSubstitutionModelClass
elementSubstitutionModelClass.update((
    # 2010 names
    (qname(XbrlConst.ver10, u"assignment"), ModelAssignment),
    (qname(XbrlConst.ver10, u"action"), ModelAction),
    (qname(XbrlConst.ver10, u"namespaceRename"), ModelNamespaceRename),
    (qname(XbrlConst.ver10, u"roleChange"), ModelRoleChange),
    (qname(XbrlConst.vercb, u"conceptAdd"), ModelConceptUseChange),
    (qname(XbrlConst.vercb, u"conceptDelete"), ModelConceptUseChange),
    (qname(XbrlConst.vercb, u"conceptRename"), ModelConceptUseChange),
    (qname(XbrlConst.verce, u"conceptIDChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptTypeChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptSubstitutionGroupChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptDefaultChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptNillableChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptAbstractChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptBlockChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptFixedChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptFinalChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptPeriodTypeChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptBalanceChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptAttributeAdd"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptAttributeDelete"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptAttributeChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"tupleContentModelChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptLabelAdd"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptLabelDelete"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptLabelChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptReferenceAdd"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptReferenceDelete"), ModelConceptDetailsChange),
    (qname(XbrlConst.verce, u"conceptReferenceChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verrels, u"relationshipSetModelChange"), ModelRelationshipSetChange),
    (qname(XbrlConst.verrels, u"relationshipSetModelAdd"), ModelRelationshipSetChange),
    (qname(XbrlConst.verrels, u"relationshipSetModelDelete"), ModelRelationshipSetChange),
    (qname(XbrlConst.verrels, u"fromRelationshipSet"), ModelRelationshipSet),
    (qname(XbrlConst.verrels, u"toRelationshipSet"), ModelRelationshipSet),
    (qname(XbrlConst.verrels, u"relationships"), ModelRelationships),
    (qname(XbrlConst.veria, u"aspectModelChange"), ModelInstanceAspectsChange),
    (qname(XbrlConst.veria, u"aspectModelAdd"), ModelInstanceAspectsChange),
    (qname(XbrlConst.veria, u"aspectModelDelete"), ModelInstanceAspectsChange),
    (qname(XbrlConst.veria, u"fromAspects"), ModelInstanceAspects),
    (qname(XbrlConst.veria, u"toAspects"), ModelInstanceAspects),
    (qname(XbrlConst.veria, u"concept"), ModelInstanceAspect),
    (qname(XbrlConst.veria, u"explicitDimension"), ModelConceptsDimsAspect),
    (qname(XbrlConst.veria, u"typedDimension"), ModelConceptsDimsAspect),
    (qname(XbrlConst.veria, u"segment"), ModelInstanceAspect),
    (qname(XbrlConst.veria, u"scenario"), ModelInstanceAspect),
    (qname(XbrlConst.veria, u"entityIdentifier"), ModelInstanceAspect),
    (qname(XbrlConst.veria, u"period"), ModelPeriodAspect),
    (qname(XbrlConst.veria, u"location"), ModelInstanceAspect),
    (qname(XbrlConst.veria, u"unit"), ModelInstanceAspect),
    (qname(XbrlConst.veria, u"member"), ModelRelatedConcept),
    (qname(XbrlConst.veria, u"startDate"), ModelRelatedConcept),
    (qname(XbrlConst.veria, u"endDate"), ModelAspectProperty),
    (qname(XbrlConst.veria, u"instant"), ModelAspectProperty),
    (qname(XbrlConst.veria, u"forever"), ModelAspectProperty),
    (qname(XbrlConst.veria, u"multiplyBy"), ModelMeasureAspect),
    (qname(XbrlConst.veria, u"divideBy"), ModelMeasureAspect),
    (qname(XbrlConst.veria, u"measure"), ModelAspectProperty),
    # 2013 names
    (qname(XbrlConst.ver, u"assignment"), ModelAssignment),
    (qname(XbrlConst.ver, u"action"), ModelAction),
    (qname(XbrlConst.ver, u"namespaceRename"), ModelNamespaceRename),
    (qname(XbrlConst.ver, u"roleChange"), ModelRoleChange),
    (qname(XbrlConst.vercu, u"conceptAdd"), ModelConceptUseChange),
    (qname(XbrlConst.vercu, u"conceptDelete"), ModelConceptUseChange),
    (qname(XbrlConst.vercu, u"conceptRename"), ModelConceptUseChange),
    (qname(XbrlConst.vercd, u"conceptIDChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptTypeChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptSubstitutionGroupChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptDefaultChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptNillableChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptAbstractChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptBlockChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptFixedChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptFinalChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptPeriodTypeChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptBalanceChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptAttributeAdd"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptAttributeDelete"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptAttributeChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"attributeDefinitionChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"tupleContentModelChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptLabelAdd"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptLabelDelete"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptLabelChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptReferenceAdd"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptReferenceDelete"), ModelConceptDetailsChange),
    (qname(XbrlConst.vercd, u"conceptReferenceChange"), ModelConceptDetailsChange),
    (qname(XbrlConst.verdim, u"aspectModelChange"), ModelInstanceAspectsChange),
    (qname(XbrlConst.verdim, u"aspectModelAdd"), ModelInstanceAspectsChange),
    (qname(XbrlConst.verdim, u"aspectModelDelete"), ModelInstanceAspectsChange),
    (qname(XbrlConst.verdim, u"fromAspects"), ModelInstanceAspects),
    (qname(XbrlConst.verdim, u"toAspects"), ModelInstanceAspects),
    (qname(XbrlConst.verdim, u"concepts"), ModelConceptsDimsAspect),
    (qname(XbrlConst.verdim, u"explicitDimension"), ModelConceptsDimsAspect),
    (qname(XbrlConst.verdim, u"typedDimension"), ModelConceptsDimsAspect),
    (qname(XbrlConst.verdim, u"concept"), ModelRelatedConcept),
    (qname(XbrlConst.verdim, u"member"), ModelRelatedConcept),
     ))
