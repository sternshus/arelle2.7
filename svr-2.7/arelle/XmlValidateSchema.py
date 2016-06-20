u'''
Created on Apr 10, 2013

@author: Mark V Systems Limited
(c) Copyright 2013 Mark V Systems Limited, All rights reserved.
'''
import time
from arelle import ModelXbrl, XbrlConst, XmlValidate
from arelle.ModelObject import ModelObject
from arelle.ModelDtsObject import ModelAttribute, ModelConcept, ModelType
from arelle.ModelValue import qname
from arelle.Locale import format_string
from lxml import etree

XMLSchemaURI = u"http://www.w3.org/2001/XMLSchema.xsd"

def validate(modelDocument, schemaElement, targetNamespace):
    modelXbrl = modelDocument.modelXbrl 
    modelManager = modelXbrl.modelManager
    u"""
    if not hasattr(modelManager, "xmlSchemaSchema"):
        if getattr(modelManager, "modelXmlSchemaIsLoading", False):
            return
        startedAt = time.time()
        modelManager.modelXmlSchemaIsLoading = True
        priorValidateDisclosureSystem = modelManager.validateDisclosureSystem
        modelManager.validateDisclosureSystem = False
        modelManager.xmlSchemaSchema = ModelXbrl.load(modelManager, XMLSchemaURI, _("validate schema"))
        modelManager.validateDisclosureSystem = priorValidateDisclosureSystem
        '''
        filePath = modelManager.cntlr.webCache.getfilename(XMLSchemaURI)
        modelManager.showStatus(_("lxml compiling XML Schema for Schemas"))
        modelManager.xmlSchemaSchema = etree.XMLSchema(file=filePath)
        '''
        modelXbrl.info("info:xmlSchemaValidator", format_string(modelXbrl.modelManager.locale, 
                                            _("schema for XML schemas loaded into lxml %.3f secs"), 
                                            time.time() - startedAt),
                                            modelDocument=XMLSchemaURI)
        modelManager.showStatus("")
        del modelManager.modelXmlSchemaIsLoading
    '''
    #startedAt = time.time()
    #validationSuccess = modelManager.xmlSchemaSchema.validate(schemaElement)
    #modelXbrl.info("info:xmlSchemaValidator", format_string(modelXbrl.modelManager.locale, 
    #                                    _("schema validated in %.3f secs"), 
    #                                    time.time() - startedAt),
    #                                    modelDocument=modelDocument)
    if not validationSuccess:
        for error in modelManager.xmlSchemaSchema.error_log:
            modelXbrl.error("xmlSchema:syntax",
                    _("%(error)s, %(fileName)s, line %(line)s, column %(column)s, %(sourceAction)s source element"),
                    modelObject=modelDocument, fileName=modelDocument.basename, 
                    error=error.message, line=error.line, column=error.column, sourceAction=("xml schema"))
        modelManager.xmlSchemaSchema._clear_error_log()
    '''
    """
    #XmlValidate.validate(modelXbrl, schemaElement) # use arelle schema validation

    declaredNamespaces = set(doc.targetNamespace
                             for doc, docRef in modelDocument.referencesDocument.items()
                             if docRef.referenceType in (u"include", u"import"))

    if targetNamespace:
        declaredNamespaces.add(targetNamespace)
        
    if targetNamespace in (u"http://www.w3.org/2001/XMLSchema",
                           u"http://www.w3.org/XML/1998/namespace",
                           ): # or (
        #                targetNamespace and targetNamespace.startswith("http://www.w3.org/1999/xhtml")):
        return # don't validate w3c schemas
    
    # check schema semantics
    def resolvedQnames(elt, qnDefs):
        for attrName, attrType, mdlObjects, isQualifiedForm in qnDefs:
            attr = elt.get(attrName)
            if attr is not None:
                try:
                    qnValue = elt.schemaNameQname(attr, 
                                                  isQualifiedForm=isQualifiedForm or elt.isQualifiedForm, 
                                                  prefixException=ValueError)
                    if qnValue.namespaceURI == XbrlConst.xsd:
                        if attrType != ModelType:
                            raise ValueError(u"{0} can not have xml schema namespace".format(attrName))
                        if qnValue.localName not in set([
                                u"anySimpleType", u"anyType",
                                u"string", u"boolean", u"float", u"double", u"decimal", u"duration", u"dateTime", u"time", u"date", 
                                u"gYearMonth", u"gYear", u"gMonthDay", u"gDay", u"gMonth", 
                                u"hexBinary", u"base64Binary", 
                                u"anyURI", u"QName", u"NOTATION", 
                                u"normalizedString", u"token", u"language", 
                                u"IDREFS", u"ENTITIES", u"NMTOKEN", u"NMTOKENS", u"NCName", 
                                u"ID", u"IDREF", 
                                u"integer", u"nonPositiveInteger", u"negativeInteger", 
                                u"long", u"int", u"short", u"byte", 
                                u"nonNegativeInteger", u"unsignedLong", u"unsignedInt", u"unsignedShort", u"unsignedByte", 
                                u"positiveInteger"]):
                            raise ValueError(u"{0} qname {1} not recognized".format(attrName, attr))
                    # qname must be defined in an imported or included schema
                    elif qnValue.namespaceURI and qnValue.namespaceURI not in declaredNamespaces:
                        raise ValueError(u"Namespace is not defined by an import or include element")
                    elif qnValue not in mdlObjects:
                        raise ValueError(u"{0} is not defined".format(attrName))
                    elif not isinstance(mdlObjects[qnValue], attrType):
                        raise ValueError(u"{0} not resolved to expected object type".format(attrName))
                except ValueError, err:
                    modelXbrl.error(u"xmlSchema:valueError",
                        _(u"Element attribute %(typeName)s value error: %(value)s, %(error)s"),
                        modelObject=elt,
                        typeName=attrName,
                        value=attr,
                        error=err)
                    
    def checkSchemaElements(parentElement):
        for elt in parentElement.iterchildren():
            if isinstance(elt,ModelObject) and elt.namespaceURI == XbrlConst.xsd:
                ln = elt.localName
                if ln == u"element":
                    resolvedQnames(elt, ((u"ref", ModelConcept, modelXbrl.qnameConcepts, False),
                                         (u"substitutionGroup", ModelConcept, modelXbrl.qnameConcepts, True),
                                         (u"type", ModelType, modelXbrl.qnameTypes, True)))
                elif ln == u"attribute":
                    resolvedQnames(elt, ((u"ref", ModelAttribute, modelXbrl.qnameAttributes, False),
                                         (u"type", ModelType, modelXbrl.qnameTypes, True)))
            checkSchemaElements(elt)

    checkSchemaElements(schemaElement)
    
