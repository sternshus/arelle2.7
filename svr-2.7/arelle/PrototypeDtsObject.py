from arelle import XmlUtil, XbrlConst
from arelle.ModelValue import QName
from arelle.XmlValidate import VALID
from collections import defaultdict
import decimal, os
ModelDocument = None

class LinkPrototype():      # behaves like a ModelLink for relationship prototyping
    def __init__(self, modelDocument, parent, qname, role):
        self.modelDocument = modelDocument
        self._parent = parent
        self.modelXbrl = modelDocument.modelXbrl
        self.qname = self.elementQname = qname
        self.role = role
        # children are arc and loc elements or prototypes
        self.childElements = []
        self.text = self.textValue = None
        self.attributes = {u"{http://www.w3.org/1999/xlink}type":u"extended"}
        if role:
            self.attributes[u"{http://www.w3.org/1999/xlink}role"] = role 
        self.labeledResources = defaultdict(list)
        
    def clear(self):
        self.__dict__.clear() # dereference here, not an lxml object, don't use superclass clear()
        
    def __iter__(self):
        return iter(self.childElements)
    
    def getparent(self):
        return self._parent
    
    def iterchildren(self):
        return iter(self.childElements)
        
    def get(self, key, default=None):
        return self.attributes.get(key, default)
    
    def __getitem(self, key):
        return self.attributes[key]
    
class LocPrototype():
    def __init__(self, modelDocument, parent, label, locObject, role=None):
        self.modelDocument = modelDocument
        self._parent = parent
        self.modelXbrl = modelDocument.modelXbrl
        self.qname = self.elementQname = XbrlConst.qnLinkLoc
        self.text = self.textValue = None
        # children are arc and loc elements or prototypes
        self.attributes = {u"{http://www.w3.org/1999/xlink}type":u"locator",
                           u"{http://www.w3.org/1999/xlink}label":label}
        # add an href if it is a 1.1 id
        if isinstance(locObject,_STR_BASE): # it is an id
            self.attributes[u"{http://www.w3.org/1999/xlink}href"] = u"#" + locObject
        if role:
            self.attributes[u"{http://www.w3.org/1999/xlink}role"] = role 
        self.locObject = locObject
        
    def clear(self):
        self.__dict__.clear() # dereference here, not an lxml object, don't use superclass clear()
        
    @property
    def xlinkLabel(self):
        return self.attributes.get(u"{http://www.w3.org/1999/xlink}label")

    def dereference(self):
        if isinstance(self.locObject,_STR_BASE): # dereference by ID
            return self.modelDocument.idObjects[self.locObject]
        else: # it's an object pointer
            return self.locObject
    
    def getparent(self):
        return self._parent
        
    def get(self, key, default=None):
        return self.attributes.get(key, default)
        
    def __getitem(self, key):
        return self.attributes[key]
    
class ArcPrototype():
    def __init__(self, modelDocument, parent, qname, fromLabel, toLabel, linkrole, arcrole, order=u"1"):
        self.modelDocument = modelDocument
        self._parent = parent
        self.modelXbrl = modelDocument.modelXbrl
        self.qname = self.elementQname = qname
        self.linkrole = linkrole
        self.arcrole = arcrole
        self.order = order
        self.text = self.textValue = None
        # children are arc and loc elements or prototypes
        self.attributes = {u"{http://www.w3.org/1999/xlink}type":u"arc",
                           u"{http://www.w3.org/1999/xlink}from": fromLabel,
                           u"{http://www.w3.org/1999/xlink}to": toLabel,
                           u"{http://www.w3.org/1999/xlink}arcrole": arcrole}
        # must look validated (because it can't really be validated)
        self.xValid = VALID
        self.xValue = self.sValue = None
        self.xAttributes = {}
        
    @property
    def orderDecimal(self):
        return decimal.Decimal(self.order)

    def clear(self):
        self.__dict__.clear() # dereference here, not an lxml object, don't use superclass clear()
    
    def getparent(self):
        return self._parent
        
    def get(self, key, default=None):
        return self.attributes.get(key, default)
    
    def items(self):
        return self.attributes.items()

    def __getitem(self, key):
        return self.attributes[key]

class DocumentPrototype():
    def __init__(self, modelXbrl, uri, base=None, referringElement=None, isEntry=False, isDiscovered=False, isIncluded=None, namespace=None, reloadCache=False, **kwargs):
        global ModelDocument
        if ModelDocument is None:
            from arelle import ModelDocument
        self.modelXbrl = modelXbrl
        self.skipDTS = modelXbrl.skipDTS
        self.modelDocument = self
        if referringElement is not None:
            if referringElement.localName == u"schemaRef":
                self.type = ModelDocument.Type.SCHEMA
            elif referringElement.localName == u"linkbaseRef":
                self.type = ModelDocument.Type.LINKBASE
            else:
                self.type = ModelDocument.Type.UnknownXML
        else:
            self.type = ModelDocument.Type.UnknownXML
        normalizedUri = modelXbrl.modelManager.cntlr.webCache.normalizeUrl(uri, base)
        self.filepath = modelXbrl.modelManager.cntlr.webCache.getfilename(normalizedUri, filenameOnly=True)
        self.uri = modelXbrl.modelManager.cntlr.webCache.normalizeUrl(self.filepath)
        self.basename = os.path.basename(self.filepath)
        self.targetNamespace = None
        self.referencesDocument = {}
        self.hrefObjects = []
        self.schemaLocationElements = set()
        self.referencedNamespaces = set()
        self.inDTS = False
        self.xmlRootElement = None
  
        
    def clear(self):
        self.__dict__.clear() # dereference here, not an lxml object, don't use superclass clear()
        
