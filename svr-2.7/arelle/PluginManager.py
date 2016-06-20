u'''
Created on March 1, 2012

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.

based on pull request 4

'''
from __future__ import with_statement
import os, sys, types, time, ast, imp, io, json, gettext
from arelle.Locale import getLanguageCodes
from arelle.FileSource import openFileStream
try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict # python 3.0 lacks OrderedDict, json file will be in weird order 
    
# plugin control is static to correspond to statically loaded modules
pluginJsonFile = None
pluginConfig = None
pluginConfigChanged = False
modulePluginInfos = {}
pluginMethodsForClasses = {}
_cntlr = None
_pluginBase = None

def init(cntlr):
    global pluginJsonFile, pluginConfig, modulePluginInfos, pluginMethodsForClasses, pluginConfigChanged, _cntlr, _pluginBase
    try:
        pluginJsonFile = cntlr.userAppDir + os.sep + u"plugins.json"
        with io.open(pluginJsonFile, u'rt', encoding=u'utf-8') as f:
            pluginConfig = json.load(f)
        pluginConfigChanged = False
    except Exception:
        # on GAE no userAppDir, will always come here
        pluginConfig = {  # savable/reloadable plug in configuration
            u"modules": {}, # dict of moduleInfos by module name
            u"classes": {}  # dict by class name of list of class modules in execution order
        }
        pluginConfigChanged = False # don't save until something is added to pluginConfig
    modulePluginInfos = {}  # dict of loaded module pluginInfo objects by module names
    pluginMethodsForClasses = {} # dict by class of list of ordered callable function objects
    _cntlr = cntlr
    _pluginBase = cntlr.pluginDir + os.sep
    
def reset():  # force reloading modules and plugin infos
    modulePluginInfos.clear()  # dict of loaded module pluginInfo objects by module names
    pluginMethodsForClasses.clear() # dict by class of list of ordered callable function objects
    
def orderedPluginConfig():
    return OrderedDict(
        ((u'modules',OrderedDict((moduleName, 
                                 OrderedDict(sorted(moduleInfo.items(), 
                                                    key=lambda k: {u'name': u'01',
                                                                   u'status': u'02',
                                                                   u'version': u'03',
                                                                   u'fileDate': u'04',                                                             u'version': u'05',
                                                                   u'description': u'05',
                                                                   u'moduleURL': u'06',
                                                                   u'localeURL': u'07',
                                                                   u'localeDomain': u'08',
                                                                   u'license': u'09',
                                                                   u'author': u'10',
                                                                   u'copyright': u'11',
                                                                   u'classMethods': u'12'}.get(k[0],k[0]))))
                                for moduleName, moduleInfo in sorted(pluginConfig[u'modules'].items()))),
         (u'classes',OrderedDict(sorted(pluginConfig[u'classes'].items())))))
    
def save(cntlr):
    global pluginConfigChanged
    if pluginConfigChanged and cntlr.hasFileSystem:
        pluginJsonFile = cntlr.userAppDir + os.sep + u"plugins.json"
        with io.open(pluginJsonFile, u'wt', encoding=u'utf-8') as f:
            jsonStr = _STR_UNICODE(json.dumps(orderedPluginConfig(), ensure_ascii=False, indent=2)) # might not be unicode in 2.7
            f.write(jsonStr)
        pluginConfigChanged = False
    
def close():  # close all loaded methods
    modulePluginInfos.clear()
    pluginMethodsForClasses.clear()
    global webCache
    webCache = None

u''' pluginInfo structure:

__pluginInfo__ = {
    'name': (required)
    'version': (required)
    'description': (optional)
    'moduleURL': (required) # added by plug in manager, not in source file
    'localeURL': (optional) # L10N internationalization for this module (subdirectory if relative)
    'localeDomain': (optional) # domain for L10N internationalization (e.g., 'arelle')
    'license': (optional)
    'author': (optional)
    'copyright': (optional)
    # classes of mount points (required)
    'a.b.c': method (function) to do something
    'a.b.c.d' : method (function) to do something
}

moduleInfo = {
    'name': (required)
    'status': enabled | disabled
    'version': (required)
    'fileDate': 2000-01-01
    'description': (optional)
    'moduleURL': (required) # same as file path, can be a URL (of a non-package .py file or a package directory)
    'localeURL': (optional) # for L10N internationalization within module
    'localeDomain': (optional) # domain for L10N internationalization
    'license': (optional)
    'author': (optional)
    'copyright': (optional)
    'classMethods': [list of class names that have methods in module]
}


'''
    
def modulesWithNewerFileDates():
    names = set()
    for moduleInfo in pluginConfig[u"modules"].values():
        freshenedFilename = _cntlr.webCache.getfilename(moduleInfo[u"moduleURL"], checkModifiedTime=True, normalize=True, base=_pluginBase)
        try:
            if moduleInfo[u"fileDate"] < time.strftime(u'%Y-%m-%dT%H:%M:%S UTC', time.gmtime(os.path.getmtime(freshenedFilename))):
                names.add(moduleInfo[u"name"])
        except Exception:
            pass
    return names

def moduleModuleInfo(moduleURL, reload=False):
    #TODO several directories, eg User Application Data
    moduleFilename = _cntlr.webCache.getfilename(moduleURL, reload=reload, normalize=True, base=_pluginBase)
    if moduleFilename:
        f = None
        try:
            # if moduleFilename is a directory containing an __ini__.py file, open that instead
            if os.path.isdir(moduleFilename) and os.path.isfile(os.path.join(moduleFilename, u"__init__.py")):
                moduleFilename = os.path.join(moduleFilename, u"__init__.py")
            f = openFileStream(_cntlr, moduleFilename)
            tree = ast.parse(f.read(), filename=moduleFilename)
            for item in tree.body:
                if isinstance(item, ast.Assign):
                    attr = item.targets[0].id
                    if attr == u"__pluginInfo__":
                        f.close()
                        moduleInfo = {}
                        classMethods = []
                        for i, key in enumerate(item.value.keys):
                            _key = key.s
                            _value = item.value.values[i]
                            _valueType = _value.__class__.__name__
                            if _valueType == u'Str':
                                moduleInfo[_key] = _value.s
                            elif _valueType == u'Name':
                                classMethods.append(_key)
                        moduleInfo[u'classMethods'] = classMethods
                        moduleInfo[u"moduleURL"] = moduleURL
                        moduleInfo[u"status"] = u'enabled'
                        moduleInfo[u"fileDate"] = time.strftime(u'%Y-%m-%dT%H:%M:%S UTC', time.gmtime(os.path.getmtime(moduleFilename)))
                        return moduleInfo
        except EnvironmentError:
            pass
        if f:
            f.close()
    return None

def moduleInfo(pluginInfo):
    moduleInfo = {}
    for name, value in pluginInfo.items():
        if isinstance(value, u'_STR_UNICODE'):
            moduleInfo[name] = value
        elif isinstance(value, types.FunctionType):
            moduleInfo.getdefault(u'classes',[]).append(name)

def loadModule(moduleInfo):
    name = moduleInfo[u'name']
    moduleURL = moduleInfo[u'moduleURL']
    moduleFilename = _cntlr.webCache.getfilename(moduleURL, normalize=True, base=_pluginBase)
    if moduleFilename:
        try:
            if os.path.basename(moduleFilename) == u"__init__.py" and os.path.isfile(moduleFilename):
                moduleFilename = os.path.dirname(moduleFilename) # want just the dirpart of package
            if os.path.isdir(moduleFilename) and os.path.isfile(os.path.join(moduleFilename, u"__init__.py")):
                moduleDir = os.path.dirname(moduleFilename)
                moduleName = os.path.basename(moduleFilename)
            else:
                moduleName = os.path.basename(moduleFilename).partition(u'.')[0]
                moduleDir = os.path.dirname(moduleFilename)
            file, path, description = imp.find_module(moduleName, [moduleDir])
            if file or path: # file returned if non-package module, otherwise just path for package
                try:
                    module = imp.load_module(moduleName, file, path, description)
                    pluginInfo = module.__pluginInfo__.copy()
                    elementSubstitutionClasses = None
                    if name == pluginInfo.get(u'name'):
                        pluginInfo[u"moduleURL"] = moduleURL
                        modulePluginInfos[name] = pluginInfo
                        if u'localeURL' in pluginInfo:
                            # set L10N internationalization in loaded module
                            localeDir = os.path.dirname(module.__file__) + os.sep + pluginInfo[u'localeURL']
                            try:
                                _gettext = gettext.translation(pluginInfo[u'localeDomain'], localeDir, getLanguageCodes())
                            except IOError:
                                _gettext = lambda x: x # no translation
                        else:
                            _gettext = lambda x: x
                        for key, value in pluginInfo.items():
                            if key == u'name':
                                if name:
                                    pluginConfig[u'modules'][name] = moduleInfo
                            elif isinstance(value, types.FunctionType):
                                classModuleNames = pluginConfig[u'classes'].setdefault(key, [])
                                if name and name not in classModuleNames:
                                    classModuleNames.append(name)
                            if key == u'ModelObjectFactory.ElementSubstitutionClasses':
                                elementSubstitutionClasses = value
                        module._ = _gettext
                        global pluginConfigChanged
                        pluginConfigChanged = True
                    if elementSubstitutionClasses:
                        try:
                            from arelle.ModelObjectFactory import elementSubstitutionModelClass
                            elementSubstitutionModelClass.update(elementSubstitutionClasses)
                        except Exception, err:
                            print >>sys.stderr, _(u"Exception loading plug-in {name}: processing ModelObjectFactory.ElementSubstitutionClasses").format(
                                    name=name, error=err)
                except (ImportError, AttributeError), err:
                    print >>sys.stderr, _(u"Exception loading plug-in {name}: {error}").format(
                            name=name, error=err)
                finally:
                    if file:
                        file.close() # non-package module
        except (EnvironmentError, ImportError, NameError), err: #find_module failed, no file to close
            print >>sys.stderr, _(u"Exception finding plug-in {name}: {error}").format(
                    name=name, error=err)

def pluginClassMethods(className):
    if pluginConfig:
        try:
            pluginMethodsForClass = pluginMethodsForClasses[className]
        except KeyError:
            # load all modules for class
            pluginMethodsForClass = []
            if className in pluginConfig[u"classes"]:
                for moduleName in pluginConfig[u"classes"].get(className):
                    if moduleName and moduleName in pluginConfig[u"modules"]:
                        moduleInfo = pluginConfig[u"modules"][moduleName]
                        if moduleInfo[u"status"] == u"enabled":
                            if moduleName not in modulePluginInfos:
                                loadModule(moduleInfo)
                            if moduleName in modulePluginInfos:
                                pluginInfo = modulePluginInfos[moduleName]
                                if className in pluginInfo:
                                    pluginMethodsForClass.append(pluginInfo[className])
            pluginMethodsForClasses[className] = pluginMethodsForClass
        for method in pluginMethodsForClass:
            yield method

def addPluginModule(url):
    moduleInfo = moduleModuleInfo(url)
    if moduleInfo and moduleInfo.get(u"name"):
        name = moduleInfo[u"name"]
        removePluginModule(name)  # remove any prior entry for this module
        pluginConfig[u"modules"][name] = moduleInfo
        # add classes
        for classMethod in moduleInfo[u"classMethods"]:
            classMethods = pluginConfig[u"classes"].setdefault(classMethod, [])
            if name not in classMethods:
                classMethods.append(name)
        global pluginConfigChanged
        pluginConfigChanged = True
        return moduleInfo
    return None

def reloadPluginModule(name):
    if name in pluginConfig[u"modules"]:
        url = pluginConfig[u"modules"][name].get(u"moduleURL")
        if url:
            moduleInfo = moduleModuleInfo(url, reload=True)
            if moduleInfo:
                addPluginModule(url)
                return True
    return False

def removePluginModule(name):
    moduleInfo = pluginConfig[u"modules"].get(name)
    if moduleInfo:
        for classMethod in moduleInfo[u"classMethods"]:
            classMethods = pluginConfig[u"classes"].get(classMethod)
            if classMethods and name in classMethods:
                classMethods.remove(name)
                if not classMethods: # list has become unused
                    del pluginConfig[u"classes"][classMethod] # remove class
        del pluginConfig[u"modules"][name]
        global pluginConfigChanged
        pluginConfigChanged = True
        return True
    return False # unable to remove