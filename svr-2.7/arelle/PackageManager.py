u'''
Separated on Jul 28, 2013 from DialogOpenArchive.py

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from __future__ import with_statement
import sys, os, io, time, json
from fnmatch import fnmatch
from lxml import etree
if sys.version[0] >= u'3':
    from urlparse import urljoin
else:
    from urlparse import urljoin
openFileSource = None
from arelle import Locale
from arelle.UrlUtil import isHttpUrl
try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict # python 3.0 lacks OrderedDict, json file will be in weird order 

EMPTYDICT = {}

def parsePackage(mainWin, metadataFile):
    unNamedCounter = 1
    
    txmyPkgNSes = (u"http://www.corefiling.com/xbrl/taxonomypackage/v1",
                   u"http://xbrl.org/PWD/2014-01-15/taxonomy-package")
    catalogNSes = (u"urn:oasis:names:tc:entity:xmlns:xml:catalog",)
    
    pkg = {}

    currentLang = Locale.getLanguageCode()
    tree = etree.parse(metadataFile)
    root = tree.getroot()
    ns = root.tag.partition(u"}")[0][1:]
    nsPrefix = u"{{{}}}".format(ns)
    
    if ns in  txmyPkgNSes:  # package file
        for eltName in (u"name", u"description", u"version"):
            pkg[eltName] = u''
            for m in root.iterchildren(tag=nsPrefix + eltName):
                pkg[eltName] = m.text.strip()
                break # take first entry if several
    else: # oasis catalog, use dirname as the package name
        # metadataFile may be a File object (with name) or string filename 
        fileName = getattr(metadataFile, u'fileName',      # for FileSource named objects 
                           getattr(metadataFile, u'name',  # for io.file named objects
                                   metadataFile))         # for string
        pkg[u"name"] = os.path.basename(os.path.dirname(fileName))
        pkg[u"description"] = u"oasis catalog"
        pkg[u"version"] = u"(none)"

    remappings = {}
    for tag, prefixAttr, replaceAttr in (
         (nsPrefix + u"remapping", u"prefix", u"replaceWith"), # taxonomy package
         (nsPrefix + u"rewriteSystem", u"systemIdStartString", u"rewritePrefix")): # oasis catalog
        for m in tree.iter(tag=tag):
            prefixValue = m.get(prefixAttr)
            replaceValue = m.get(replaceAttr)
            if prefixValue and replaceValue is not None:
                remappings[prefixValue] = replaceValue

    pkg[u"remappings"] = remappings

    nameToUrls = {}
    pkg[u"nameToUrls"] = nameToUrls

    for entryPointSpec in tree.iter(tag=nsPrefix + u"entryPoint"):
        name = None
        
        # find closest match name node given xml:lang match to current language or no xml:lang
        for nameNode in entryPointSpec.iter(tag=nsPrefix + u"name"):
            xmlLang = nameNode.get(u'{http://www.w3.org/XML/1998/namespace}lang')
            if name is None or not xmlLang or currentLang == xmlLang:
                name = nameNode.text
                if currentLang == xmlLang: # most prefer one with the current locale's language
                    break

        if not name:
            name = _(u"<unnamed {0}>").format(unNamedCounter)
            unNamedCounter += 1

        epDocCount = 0
        for epDoc in entryPointSpec.iterchildren(nsPrefix + u"entryPointDocument"):
            if epDocCount:
                mainWin.addToLog(_(u"WARNING: skipping multiple-document entry point (not supported)"))
                continue
            epDocCount += 1
            epUrl = epDoc.get(u'href')
            base = epDoc.get(u'{http://www.w3.org/XML/1998/namespace}base') # cope with xml:base
            if base:
                resolvedUrl = urljoin(base, epUrl)
            else:
                resolvedUrl = epUrl
    
            #perform prefix remappings
            remappedUrl = resolvedUrl
            for prefix, replace in remappings.items():
                remappedUrl = remappedUrl.replace(prefix, replace, 1)
            nameToUrls[name] = (remappedUrl, resolvedUrl)

    return pkg

# taxonomy package manager
# plugin control is static to correspond to statically loaded modules
packagesJsonFile = None
packagesConfig = None
packagesConfigChanged = False
packagesMappings = {}
_cntlr = None

def init(cntlr):
    global packagesJsonFile, packagesConfig, packagesMappings, _cntlr
    try:
        packagesJsonFile = cntlr.userAppDir + os.sep + u"taxonomyPackages.json"
        with io.open(packagesJsonFile, u'rt', encoding=u'utf-8') as f:
            packagesConfig = json.load(f)
        packagesConfigChanged = False
    except Exception:
        # on GAE no userAppDir, will always come here
        packagesConfig = {  # savable/reloadable plug in configuration
            u"packages": [], # list taxonomy packages loaded and their remappings
            u"remappings": {}  # dict by prefix of remappings in effect
        }
        packagesConfigChanged = False # don't save until something is added to pluginConfig
    pluginMethodsForClasses = {} # dict by class of list of ordered callable function objects
    _cntlr = cntlr
    
def reset():  # force reloading modules and plugin infos
    packagesConfig.clear()  # dict of loaded module pluginInfo objects by module names
    packagesMappings.clear() # dict by class of list of ordered callable function objects
    
def orderedPackagesConfig():
    return OrderedDict(
        ((u'packages', [OrderedDict(sorted(_packageInfo.items(), 
                                          key=lambda k: {u'name': u'01',
                                                         u'status': u'02',
                                                         u'version': u'03',
                                                         u'fileDate': u'04',
                                                         u'URL': u'05',
                                                         u'description': u'06',
                                                         u'remappings': u'07'}.get(k[0],k[0])))
                       for _packageInfo in packagesConfig[u'packages']]),
         (u'remappings',OrderedDict(sorted(packagesConfig[u'remappings'].items())))))
    
def save(cntlr):
    global packagesConfigChanged
    if packagesConfigChanged and cntlr.hasFileSystem:
        with io.open(packagesJsonFile, u'wt', encoding=u'utf-8') as f:
            jsonStr = _STR_UNICODE(json.dumps(orderedPackagesConfig(), ensure_ascii=False, indent=2)) # might not be unicode in 2.7
            f.write(jsonStr)
        packagesConfigChanged = False
    
def close():  # close all loaded methods
    packagesConfig.clear()
    packagesMappings.clear()
    global webCache
    webCache = None
    
u''' packagesConfig structure

{
 'packages':  [list of package dicts in order of application],
 'remappings': dict of prefix:url remappings
}

package dict
{
    'name': package name
    'status': enabled | disabled
    'version': version (such as 2009)
    'fileDate': 2001-01-01
    'url': web http (before caching) or local file location
    'description': text
    'remappings': dict of prefix:url of each remapping
}

'''

def packageNamesWithNewerFileDates():
    names = set()
    for package in packagesConfig[u"packages"]:
        freshenedFilename = _cntlr.webCache.getfilename(package[u"URL"], checkModifiedTime=True, normalize=True)
        try:
            if package[u"fileDate"] < time.strftime(u'%Y-%m-%dT%H:%M:%S UTC', time.gmtime(os.path.getmtime(freshenedFilename))):
                names.add(package[u"name"])
        except Exception:
            pass
    return names

def packageInfo(URL, reload=False, packageManifestName=None):
    #TODO several directories, eg User Application Data
    packageFilename = _cntlr.webCache.getfilename(URL, reload=reload, normalize=True)
    if packageFilename:
        from arelle.FileSource import TAXONOMY_PACKAGE_FILE_NAMES
        filesource = None
        try:
            global openFileSource
            if openFileSource is None:
                from arelle.FileSource import openFileSource
            filesource = openFileSource(packageFilename, _cntlr)
            # allow multiple manifests [[metadata, prefix]...] for multiple catalogs
            packages = []
            if filesource.isZip:
                if packageManifestName:
                    packageFiles = [fileName
                                    for fileName in filesource.dir
                                    if fnmatch(fileName, packageManifestName)]
                else:
                    packageFiles = filesource.taxonomyPackageMetadataFiles
                if len(packageFiles) < 1:
                    raise IOError(_(u"Taxonomy package contained no metadata file: {0}.")
                                  .format(u', '.join(packageFiles)))
                for packageFile in packageFiles:
                    packageFileUrl = filesource.file(filesource.url + os.sep + packageFile)[0]
                    packageFilePrefix = os.sep.join(os.path.split(packageFile)[:-1])
                    if packageFilePrefix:
                        packageFilePrefix += os.sep
                    packageFilePrefix = filesource.baseurl + os.sep +  packageFilePrefix
                    packages.append([packageFileUrl, packageFilePrefix])
            elif os.path.basename(filesource.url) in TAXONOMY_PACKAGE_FILE_NAMES: # individual manifest file
                packageFile = packageFileUrl = filesource.url
                packageFilePrefix = os.sep.join(os.path.split(packageFile)[:-1])
                if packageFilePrefix:
                    packageFilePrefix += os.sep
                packages.append([packageFileUrl, packageFilePrefix])
            else:
                raise IOError(_(u"File must be a taxonomy package (zip file), catalog file, or manifest (): {0}.")
                              .format(packageFilename, u', '.join(TAXONOMY_PACKAGE_FILE_NAMES)))
            remappings = {}
            packageNames = []
            descriptions = []
            for packageFileUrl, packageFilePrefix in packages:    
                parsedPackage = parsePackage(_cntlr, packageFileUrl)
                packageNames.append(parsedPackage[u'name'])
                if parsedPackage.get(u'description'):
                    descriptions.append(parsedPackage[u'description'])
                for prefix, remapping in parsedPackage[u"remappings"].items():
                    remappings[prefix] = (remapping if isHttpUrl(remapping)
                                          else (packageFilePrefix +remapping.replace(u"/", os.sep)))
            package = {u'name': u", ".join(packageNames),
                       u'status': u'enabled',
                       u'version': parsedPackage[u'version'],
                       u'fileDate': time.strftime(u'%Y-%m-%dT%H:%M:%S UTC', time.gmtime(os.path.getmtime(packageFilename))),
                       u'URL': URL,
                       u'manifestName': packageManifestName,
                       u'description': u"; ".join(descriptions),
                       u'remappings': remappings,
                       }
            filesource.close()
            return package
        except EnvironmentError:
            pass
        if filesource:
            filesource.close()
    return None

def rebuildRemappings():
    remappings = packagesConfig[u"remappings"]
    remappings.clear()
    for _packageInfo in packagesConfig[u"packages"]:
        if _packageInfo[u'status'] == u'enabled':
            for prefix, remapping in _packageInfo[u'remappings'].items():
                if prefix not in remappings:
                    remappings[prefix] = remapping

def isMappedUrl(url):
    return (packagesConfig is not None and 
            any(url.startswith(mapFrom) 
                for mapFrom in packagesConfig.get(u'remappings', EMPTYDICT).keys()))

def mappedUrl(url):
    if packagesConfig is not None:
        for mapFrom, mapTo in packagesConfig.get(u'remappings', EMPTYDICT).items():
            if url.startswith(mapFrom):
                url = mapTo + url[len(mapFrom):]
                break
    return url

def addPackage(url, packageManifestName=None):
    newPackageInfo = packageInfo(url, packageManifestName=packageManifestName)
    if newPackageInfo and newPackageInfo.get(u"name"):
        name = newPackageInfo.get(u"name")
        version = newPackageInfo.get(u"version")
        j = -1
        packagesList = packagesConfig[u"packages"]
        for i, _packageInfo in enumerate(packagesList):
            if _packageInfo[u'name'] == name and _packageInfo[u'version'] == version:
                j = i
                break
        if 0 <= j < len(packagesList): # replace entry
            packagesList[j] = newPackageInfo
        else:
            packagesList.append(newPackageInfo)
        global packagesConfigChanged
        packagesConfigChanged = True
        rebuildRemappings()
        return newPackageInfo
    return None

def reloadPackageModule(name):
    packageUrls = []
    packagesList = packagesConfig[u"packages"]
    for _packageInfo in packagesList:
        if _packageInfo[u'name'] == name:
            packageUrls.append(_packageInfo[u'URL'])
    result = False
    for url in packageUrls:
        addPackage(url)
        result = True
    return result

def removePackageModule(name):
    packageIndices = []
    packagesList = packagesConfig[u"packages"]
    for i, _packageInfo in enumerate(packagesList):
        if _packageInfo[u'name'] == name:
            packageIndices.insert(0, i) # must remove in reverse index order
    result = False
    for i in packageIndices:
        del packagesList[i]
        result = True
    if result:
        global packagesConfigChanged
        packagesConfigChanged = True
        rebuildRemappings()
    return result
