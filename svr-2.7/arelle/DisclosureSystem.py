u'''
Created on Dec 16, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
import os, re
from collections import defaultdict
from lxml import etree
from arelle import UrlUtil
from arelle.PluginManager import pluginClassMethods
from arelle.UrlUtil import isHttpUrl

def compileAttrPattern(elt, attrName, flags=None):
    attr = elt.get(attrName)
    if attr is None: attr = u""
    if flags is not None:
        return re.compile(attr, flags)
    else:
        return re.compile(attr)

class ErxlLoc(object):
    def __init__(self, family, version, href, attType, elements, namespace):
        self.family = family
        self.version = version
        self.href = href
        self.attType = attType
        self.elements = elements
        self.namespace = namespace

class DisclosureSystem(object):
    def __init__(self, modelManager):
        self.modelManager = modelManager
        self.clear()
        
    def clear(self):
        self.selection = None
        self.standardTaxonomiesDict = {}
        self.familyHrefs = {}
        self.standardLocalHrefs = set()
        self.standardAuthorities = set()
        self.baseTaxonomyNamespaces = set()
        self.standardPrefixes = {}
        self.names = None
        self.name = None
        self.validationType = None
        self.EFM = False
        self.GFM = False
        self.EFMorGFM = False
        self.HMRC = False
        self.SBRNL = False
        for pluginXbrlMethod in pluginClassMethods(u"DisclosureSystem.Types"):
            for typeName, typeTestVariable in pluginXbrlMethod(self):
                setattr(self, typeTestVariable, False)
        self.validateFileText = False
        self.schemaValidateSchema = None
        self.blockDisallowedReferences = False
        self.maxSubmissionSubdirectoryEntryNesting = 0
        self.defaultXmlLang = None
        self.xmlLangPattern = None
        self.defaultLanguage = None
        self.language = None
        self.standardTaxonomiesUrl = None
        self.mappingsUrl = os.path.join(self.modelManager.cntlr.configDir, u"mappings.xml")
        self.mappedFiles = {}
        self.mappedPaths = []
        self.utrUrl = u"http://www.xbrl.org/utr/utr.xml"
        self.utrTypeEntries = None
        self.identifierSchemePattern = None
        self.identifierValuePattern = None
        self.identifierValueName = None
        self.contextElement = None
        self.roleDefinitionPattern = None
        self.labelCheckPattern = None
        self.labelTrimPattern = None
        self.deiNamespacePattern = None
        self.deiAmendmentFlagElement = None
        self.deiCurrentFiscalYearEndDateElement = None
        self.deiDocumentFiscalYearFocusElement = None
        self.deiDocumentPeriodEndDateElement = None
        self.deiFilerIdentifierElement = None
        self.deiFilerNameElement = None
        self.logLevelFilter = None
        self.logCodeFilter = None
        self.version = (0,0,0)

    @property
    def dir(self):
        return self.dirlist(u"dir")
    
    @property
    def urls(self):
        _urls = [os.path.join(self.modelManager.cntlr.configDir, u"disclosuresystems.xml")]
        # get custom config xml file url
        for pluginXbrlMethod in pluginClassMethods(u"DisclosureSystem.ConfigURL"):
            _urls.append(pluginXbrlMethod(self))
        return _urls
    
    @property
    def url(self): # needed for status messages (not used in this module)
        return u", ".join(os.path.basename(url) for url in self.urls)
    
    def dirlist(self, listFormat):
        self.modelManager.cntlr.showStatus(_(u"parsing disclosuresystems.xml"))
        namepaths = []
        try:
            for url in self.urls:
                xmldoc = etree.parse(url)
                for dsElt in xmldoc.iter(tag=u"DisclosureSystem"):
                    if dsElt.get(u"names"):
                        names = dsElt.get(u"names").split(u"|")
                        if listFormat == u"help": # terse help
                            namepaths.append(u'{0}: {1}'.format(names[-1],names[0]))
                        elif listFormat == u"help-verbose":
                            namepaths.append(u'{0}: {1}\n{2}\n'.format(names[-1],
                                                                      names[0], 
                                                                      dsElt.get(u"description").replace(u'\\n',u'\n')))
                        elif listFormat == u"dir":
                            namepaths.append((names[0],
                                              dsElt.get(u"description")))
        except (EnvironmentError,
                etree.LxmlError), err:
            self.modelManager.cntlr.addToLog(u"disclosuresystems.xml: import error: {0}".format(err))
        self.modelManager.cntlr.showStatus(u"")
        return namepaths

    def select(self, name):
        self.clear()
        status = _(u"loading disclosure system and mappings")
        try:
            if name:
                isSelected = False
                for url in self.urls:
                    xmldoc = etree.parse(url)
                    for dsElt in xmldoc.iter(tag=u"DisclosureSystem"):
                        namesStr = dsElt.get(u"names")
                        if namesStr:
                            names = namesStr.split(u"|")
                            if name in names:
                                self.names = names
                                self.name = self.names[0]
                                self.validationType = dsElt.get(u"validationType")
                                self.EFM = self.validationType == u"EFM"
                                self.GFM = self.validationType == u"GFM"
                                self.EFMorGFM = self.EFM or self.GFM
                                self.HMRC = self.validationType == u"HMRC"
                                self.SBRNL = self.validationType == u"SBR-NL"
                                for pluginXbrlMethod in pluginClassMethods(u"DisclosureSystem.Types"):
                                    for typeName, typeTestVariable in pluginXbrlMethod(self):
                                        setattr(self, typeTestVariable, self.validationType == typeName)
                                self.validateFileText = dsElt.get(u"validateFileText") == u"true"
                                self.blockDisallowedReferences = dsElt.get(u"blockDisallowedReferences") == u"true"
                                try:
                                    self.maxSubmissionSubdirectoryEntryNesting = int(dsElt.get(u"maxSubmissionSubdirectoryEntryNesting"))
                                except (ValueError, TypeError):
                                    self.maxSubmissionSubdirectoryEntryNesting = 0
                                self.defaultXmlLang = dsElt.get(u"defaultXmlLang")
                                self.xmlLangPattern = compileAttrPattern(dsElt,u"xmlLangPattern")
                                self.defaultLanguage = dsElt.get(u"defaultLanguage")
                                self.standardTaxonomiesUrl = self.modelManager.cntlr.webCache.normalizeUrl(
                                                 dsElt.get(u"standardTaxonomiesUrl"),
                                                 url)
                                if dsElt.get(u"mappingsUrl"):
                                    self.mappingsUrl = self.modelManager.cntlr.webCache.normalizeUrl(
                                                 dsElt.get(u"mappingsUrl"),
                                                 url)
                                if dsElt.get(u"utrUrl"): # may be mapped by mappingsUrl entries, see below
                                    self.utrUrl = self.modelManager.cntlr.webCache.normalizeUrl(
                                                 dsElt.get(u"utrUrl"),
                                                 url)
                                self.identifierSchemePattern = compileAttrPattern(dsElt,u"identifierSchemePattern")
                                self.identifierValuePattern = compileAttrPattern(dsElt,u"identifierValuePattern")
                                self.identifierValueName = dsElt.get(u"identifierValueName")
                                self.contextElement = dsElt.get(u"contextElement")
                                self.roleDefinitionPattern = compileAttrPattern(dsElt,u"roleDefinitionPattern")
                                self.labelCheckPattern = compileAttrPattern(dsElt,u"labelCheckPattern", re.DOTALL)
                                self.labelTrimPattern = compileAttrPattern(dsElt,u"labelTrimPattern", re.DOTALL)
                                self.deiNamespacePattern = compileAttrPattern(dsElt,u"deiNamespacePattern")
                                self.deiAmendmentFlagElement = dsElt.get(u"deiAmendmentFlagElement")
                                self.deiCurrentFiscalYearEndDateElement = dsElt.get(u"deiCurrentFiscalYearEndDateElement")
                                self.deiDocumentFiscalYearFocusElement = dsElt.get(u"deiDocumentFiscalYearFocusElement")
                                self.deiDocumentPeriodEndDateElement = dsElt.get(u"deiDocumentPeriodEndDateElement")
                                self.deiFilerIdentifierElement = dsElt.get(u"deiFilerIdentifierElement")
                                self.deiFilerNameElement = dsElt.get(u"deiFilerNameElement")
                                self.logLevelFilter = dsElt.get(u"logLevelFilter")
                                self.logCodeFilter = dsElt.get(u"logCodeFilter")
                                self.selection = self.name
                                isSelected = True
                                break
                    if isSelected:
                        break
            self.loadMappings()
            self.utrUrl = self.mappedUrl(self.utrUrl) # utr may be mapped, change to its mapped entry
            self.loadStandardTaxonomiesDict()
            self.utrTypeEntries = None # clear any prior loaded entries
            # set log level filters (including resetting prior disclosure systems values if no such filter)
            self.modelManager.cntlr.setLogLevelFilter(self.logLevelFilter)  # None or "" clears out prior filter if any
            self.modelManager.cntlr.setLogCodeFilter(self.logCodeFilter)
            status = _(u"loaded")
            result = True
        except (EnvironmentError,
                etree.LxmlError), err:
            status = _(u"exception during loading")
            result = False
            self.modelManager.cntlr.addToLog(u"disclosuresystems.xml: import error: {0}".format(err))
            etree.clear_error_log()
        self.modelManager.cntlr.showStatus(_(u"Disclosure system and mappings {0}: {1}").format(status,name), 3500)
        return result
    
    def loadStandardTaxonomiesDict(self):
        if self.selection:
            self.standardTaxonomiesDict = defaultdict(set)
            self.familyHrefs = defaultdict(set)
            self.standardLocalHrefs = defaultdict(set)
            self.standardAuthorities = set()
            self.standardPrefixes = {}
            if not self.standardTaxonomiesUrl:
                return
            basename = os.path.basename(self.standardTaxonomiesUrl)
            self.modelManager.cntlr.showStatus(_(u"parsing {0}").format(basename))
            file = None
            try:
                from arelle.FileSource import openXmlFileStream
                for filepath in (self.standardTaxonomiesUrl, 
                                 os.path.join(self.modelManager.cntlr.configDir,u"xbrlschemafiles.xml")):
                    file = openXmlFileStream(self.modelManager.cntlr, filepath, stripDeclaration=True)[0]
                    xmldoc = etree.parse(file)
                    file.close()
                    for erxlElt in xmldoc.iter(tag=u"Erxl"):
                        v = erxlElt.get(u"version")
                        if v and re.match(ur"[0-9]+([.][0-9]+)*$", v):
                            vSplit = v.split(u'.') # at least 3 digits always!
                            self.version = tuple(int(n) for n in vSplit) + tuple(0 for n in xrange(3 - len(vSplit)))
                        break
                    for locElt in xmldoc.iter(tag=u"Loc"):
                        href = None
                        localHref = None
                        namespaceUri = None
                        prefix = None
                        attType = None
                        family = None
                        elements = None
                        version = None
                        for childElt in locElt.iterchildren():
                            ln = childElt.tag
                            value = childElt.text.strip()
                            if ln == u"Href":
                                href = value
                            elif ln == u"LocalHref":
                                localHref = value
                            elif ln == u"Namespace":
                                namespaceUri = value
                            elif ln == u"Prefix":
                                prefix = value
                            elif ln == u"AttType":
                                attType = value
                            elif ln == u"Family":
                                family = value
                            elif ln == u"Elements":
                                elements = value
                            elif ln == u"Version":
                                version = value
                        if href:
                            if namespaceUri and (attType == u"SCH" or attType == u"ENT"):
                                self.standardTaxonomiesDict[namespaceUri].add(href)
                                if localHref:
                                    self.standardLocalHrefs[namespaceUri].add(localHref)
                                authority = UrlUtil.authority(namespaceUri)
                                self.standardAuthorities.add(authority)
                                if family == u"BASE":
                                    self.baseTaxonomyNamespaces.add(namespaceUri)
                                if prefix:
                                    self.standardPrefixes[namespaceUri] = prefix
                            if href not in self.standardTaxonomiesDict:
                                self.standardTaxonomiesDict[href] = u"Allowed" + attType
                            if family:
                                self.familyHrefs[family].add(ErxlLoc(family, version, href, attType, elements, namespaceUri))
                        elif attType == u"SCH" and family == u"BASE":
                            self.baseTaxonomyNamespaces.add(namespaceUri)

            except (EnvironmentError,
                    etree.LxmlError), err:
                self.modelManager.cntlr.addToLog(u"{0}: import error: {1}".format(basename,err))
                etree.clear_error_log()
                if file:
                    file.close()

    def loadMappings(self):
        basename = os.path.basename(self.mappingsUrl)
        self.modelManager.cntlr.showStatus(_(u"parsing {0}").format(basename))
        try:
            xmldoc = etree.parse(self.mappingsUrl)
            for elt in xmldoc.iter(tag=u"mapFile"):
                self.mappedFiles[elt.get(u"from")] = elt.get(u"to")
            for elt in xmldoc.iter(tag=u"mapPath"):
                self.mappedPaths.append((elt.get(u"from"), elt.get(u"to")))
        except (EnvironmentError,
                etree.LxmlError), err:
            self.modelManager.cntlr.addToLog(u"{0}: import error: {1}".format(basename,err))
            etree.clear_error_log()
            
    def mappedUrl(self, url):
        if url in self.mappedFiles:
            mappedUrl = self.mappedFiles[url]
        else:  # handle mapped paths
            mappedUrl = url
            for mapFrom, mapTo in self.mappedPaths:
                if url.startswith(mapFrom):
                    mappedUrl = mapTo + url[len(mapFrom):]
                    break
        return mappedUrl

    def uriAuthorityValid(self, uri):
        return UrlUtil.authority(uri) in self.standardAuthorities
    
    def disallowedHrefOfNamespace(self, href, namespaceUri):
        if namespaceUri in self.standardTaxonomiesDict:
            if href in self.standardTaxonomiesDict[namespaceUri]:
                return False
        if namespaceUri in self.standardLocalHrefs and not isHttpUrl(href):
            normalizedHref = href.replace(u"\\",u"/")
            if any(normalizedHref.endswith(localHref)
                   for localHref in self.standardLocalHrefs[namespaceUri]):
                return False
        return False

    def hrefValid(self, href):
        return href in self.standardTaxonomiesDict


