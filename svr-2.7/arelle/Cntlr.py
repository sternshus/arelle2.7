# -*- coding: utf-8 -*-
u"""
:mod:`arelle.cntlr`
~~~~~~~~~~~~~~~~~~~

.. py:module:: arelle.cntlr
   :copyright: Copyright 2010-2012 Mark V Systems Limited, All rights reserved.
   :license: Apache-2.
   :synopsis: Common controller class to initialize for platform and setup common logger functions
"""
from __future__ import division
from __future__ import with_statement
from arelle import PythonUtil # define 2.x or 3.x string types
import tempfile, os, io, sys, logging, gettext, json, re, subprocess, math
from arelle import ModelManager
from arelle.Locale import getLanguageCodes
from arelle import PluginManager, PackageManager
from collections import defaultdict
from io import open
osPrcs = None
isPy3 = (sys.version[0] >= u'3')

class Cntlr(object):
    u"""    
    Initialization sets up for platform
    
    - Platform directories for application, configuration, locale, and cache
    - Context menu click event (TKinter)
    - Clipboard presence
    - Update URL
    - Reloads prior config user preferences (saved in json file)
    - Sets up proxy and web cache
    - Sets up logging
    
    A controller subclass object is instantiated, CntlrWinMain for the GUI and CntlrCmdLine for command 
    line batch operation.  (Other controller modules and/or objects may be subordinate to a CntlrCmdLine,
    such as CntlrWebMain, and CntlrQuickBooks).
    
    This controller base class initialization sets up specifics such as directory paths, 
    for its environment (Mac, Windows, or Unix), sets up a web file cache, and retrieves a 
    configuration dictionary of prior user choices (such as window arrangement, validation choices, 
    and proxy settings).
    
    The controller sub-classes (such as CntlrWinMain, CntlrCmdLine, and CntlrWebMain) most likely will 
    load an XBRL related object, such as an XBRL instance, taxonomy, 
    testcase file, versioning report, or RSS feed, by requesting the model manager to load and 
    return a reference to its modelXbrl object.  The modelXbrl object loads the entry modelDocument 
    object(s), which in turn load documents they discover (for the case of instance, taxonomies, and 
    versioning reports), but defer loading instances for test case and RSS feeds.  The model manager 
    may be requested to validate the modelXbrl object, or views may be requested as below.  
    (Validating a testcase or RSS feed will validate the test case variations or RSS feed items, one by one.)
    
        .. attribute:: isMac
        True if system is MacOS
        
        .. attribute:: isMSW
        True if system is Microsoft Windows
        
        .. attribute:: userAppDir
        Full pathname to application directory (for persistent json files, cache, etc).
        
        .. attribute:: configDir
        Full pathname to config directory as installed (validation options, redirection URLs, common xsds).
        
        .. attribute:: imagesDir
        Full pathname to images directory as installed (images for GUI and web server).
        
        .. attribute:: localeDir
        Full pathname to locale directory as installed (for support of gettext localization feature).
        
        .. attribute:: hasClipboard
        True if a system platform clipboard is implemented on current platform
        
        .. attribute:: updateURL
        URL string of application download file (on arelle.org server).  Usually redirected to latest released application installable module.
        
    """
    __version__ = u"1.0.0"
    
    def __init__(self, hasGui=False, logFileName=None, logFileMode=None, logFileEncoding=None, logFormat=None):
        self.hasWin32gui = False
        self.hasGui = hasGui
        self.hasFileSystem = True # no file system on Google App Engine servers
        self.isGAE = False
        self.isCGI = False
        self.systemWordSize = int(round(math.log(sys.maxsize, 2)) + 1) # e.g., 32 or 64

        self.moduleDir = os.path.dirname(__file__)
        # for python 3.2 remove __pycache__
        if self.moduleDir.endswith(u"__pycache__"):
            self.moduleDir = os.path.dirname(self.moduleDir)
        if self.moduleDir.endswith(u"python32.zip/arelle"):
            u'''
            distZipFile = os.path.dirname(self.moduleDir)
            d = os.path.join(self.userAppDir, "arelle")
            self.configDir = os.path.join(d, "config")
            self.imagesDir = os.path.join(d, "images")
            import zipfile
            distZip = zipfile.ZipFile(distZipFile, mode="r")
            distNames = distZip.namelist()
            distZip.extractall(path=self.userAppDir,
                               members=[f for f in distNames if "/config/" in f or "/images/" in f]
                               )
            distZip.close()
            '''
            resources = os.path.dirname(os.path.dirname(os.path.dirname(self.moduleDir)))
            self.configDir = os.path.join(resources, u"config")
            self.imagesDir = os.path.join(resources, u"images")
            self.localeDir = os.path.join(resources, u"locale")
            self.pluginDir = os.path.join(resources, u"plugin")
        elif self.moduleDir.endswith(u"library.zip\\arelle") or self.moduleDir.endswith(u"library.zip/arelle"): # cx_Freexe
            resources = os.path.dirname(os.path.dirname(self.moduleDir))
            self.configDir = os.path.join(resources, u"config")
            self.imagesDir = os.path.join(resources, u"images")
            self.localeDir = os.path.join(resources, u"locale")
            self.pluginDir = os.path.join(resources, u"plugin")
        else:
            self.configDir = os.path.join(self.moduleDir, u"config")
            self.imagesDir = os.path.join(self.moduleDir, u"images")
            self.localeDir = os.path.join(self.moduleDir, u"locale")
            self.pluginDir = os.path.join(self.moduleDir, u"plugin")
        
        serverSoftware = os.getenv(u"SERVER_SOFTWARE", u"")
        if serverSoftware.startswith(u"Google App Engine/") or serverSoftware.startswith(u"Development/"):
            self.hasFileSystem = False # no file system, userAppDir does not exist
            self.isGAE = True
        else:
            gatewayInterface = os.getenv(u"GATEWAY_INTERFACE", u"")
            if gatewayInterface.startswith(u"CGI/"):
                self.isCGI = True
            
        configHomeDir = None  # look for path configDir/CONFIG_HOME in argv and environment parameters
        for i, arg in enumerate(sys.argv):  # check if config specified in a argv 
            if arg.startswith(u"--xdgConfigHome="):
                configHomeDir = arg[16:]
                break
            elif arg == u"--xdgConfigHome" and i + 1 < len(sys.argv):
                configHomeDir = sys.argv[i + 1]
                break
        if not configHomeDir: # not in argv, may be an environment parameter
            configHomeDir = os.getenv(u'XDG_CONFIG_HOME')
        if not configHomeDir:  # look for path configDir/CONFIG_HOME
            configHomeDirFile = os.path.join(self.configDir, u"XDG_CONFIG_HOME")
            if os.path.exists(configHomeDirFile):
                try:
                    with io.open(configHomeDirFile, u'rt', encoding=u'utf-8') as f:
                        configHomeDir = f.read().strip()
                    if configHomeDir and not os.path.isabs(configHomeDir):
                        configHomeDir = os.path.abspath(configHomeDir)  # make into a full path if relative
                except EnvironmentError:
                    configHomeDir = None
        if self.hasFileSystem and configHomeDir and os.path.exists(configHomeDir):
            # check if a cache exists in this directory (e.g. from XPE or other tool)
            impliedAppDir = os.path.join(configHomeDir, u"arelle")
            if os.path.exists(impliedAppDir):
                self.userAppDir = impliedAppDir
            elif os.path.exists(os.path.join(configHomeDir, u"cache")):
                self.userAppDir = configHomeDir # use the XDG_CONFIG_HOME because cache is already a subdirectory
            else:
                self.userAppDir = impliedAppDir
        if sys.platform == u"darwin":
            self.isMac = True
            self.isMSW = False
            if self.hasFileSystem and not configHomeDir:
                self.userAppDir = os.path.expanduser(u"~") + u"/Library/Application Support/Arelle"
            # note that cache is in ~/Library/Caches/Arelle
            self.contextMenuClick = u"<Button-2>"
            self.hasClipboard = hasGui  # clipboard always only if Gui (not command line mode)
            self.updateURL = u"http://arelle.org/downloads/8"
        elif sys.platform.startswith(u"win"):
            self.isMac = False
            self.isMSW = True
            if self.hasFileSystem and not configHomeDir:
                tempDir = tempfile.gettempdir()
                if tempDir.lower().endswith(u'local\\temp'):
                    impliedAppDir = tempDir[:-10] + u'local'
                else:
                    impliedAppDir = tempDir
                self.userAppDir = os.path.join( impliedAppDir, u"Arelle")
            if hasGui:
                try:
                    import win32clipboard
                    self.hasClipboard = True
                except ImportError:
                    self.hasClipboard = False
                try:
                    import win32gui
                    self.hasWin32gui = True # active state for open file dialogs
                except ImportError:
                    pass
            else:
                self.hasClipboard = False
            self.contextMenuClick = u"<Button-3>"
            if u"64 bit" in sys.version:
                self.updateURL = u"http://arelle.org/downloads/9"
            else: # 32 bit
                self.updateURL = u"http://arelle.org/downloads/10"
        else: # Unix/Linux
            self.isMac = False
            self.isMSW = False
            if self.hasFileSystem and not configHomeDir:
                    self.userAppDir = os.path.join( os.path.expanduser(u"~/.config"), u"arelle")
            if hasGui:
                try:
                    import gtk
                    self.hasClipboard = True
                except ImportError:
                    self.hasClipboard = False
            else:
                self.hasClipboard = False
            self.contextMenuClick = u"<Button-3>"
        try:
            from arelle import webserver
            self.hasWebServer = True
        except ImportError:
            self.hasWebServer = False
        # assert that app dir must exist
        self.config = None
        if self.hasFileSystem:
            if not os.path.exists(self.userAppDir):
                os.makedirs(self.userAppDir)
            # load config if it exists
            self.configJsonFile = self.userAppDir + os.sep + u"config.json"
            if os.path.exists(self.configJsonFile):
                try:
                    with io.open(self.configJsonFile, u'rt', encoding=u'utf-8') as f:
                        self.config = json.load(f)
                except Exception, ex:
                    self.config = None # restart with a new config
        if not self.config:
            self.config = {
                u'fileHistory': [],
                u'windowGeometry': u"{0}x{1}+{2}+{3}".format(800, 500, 200, 100),                
            }
            
        # start language translation for domain
        self.setUiLanguage(self.config.get(u"userInterfaceLangOverride",None), fallbackToDefault=True)
            
        from arelle.WebCache import WebCache
        self.webCache = WebCache(self, self.config.get(u"proxySettings"))
        
        # start plug in server (requres web cache initialized, but not logger)
        PluginManager.init(self)

        # requires plug ins initialized
        self.modelManager = ModelManager.initialize(self)
 
        # start taxonomy package server (requres web cache initialized, but not logger)
        PackageManager.init(self)
 
        self.startLogging(logFileName, logFileMode, logFileEncoding, logFormat)
        
        # Cntlr.Init after logging started
        for pluginMethod in PluginManager.pluginClassMethods(u"Cntlr.Init"):
            pluginMethod(self)
            
    def setUiLanguage(self, lang, fallbackToDefault=False):
        try:
            gettext.translation(u"arelle", 
                                self.localeDir, 
                                getLanguageCodes(lang)).install()
            if not isPy3: # 2.7 gettext provides string instead of unicode from .mo files
                installedGettext = __builtins__[u'_']
                def convertGettextResultToUnicode(msg):
                    translatedMsg = installedGettext(msg)
                    if isinstance(translatedMsg, _STR_UNICODE):
                        return translatedMsg
                    return translatedMsg.decode(u'utf-8')
                __builtins__[u'_'] = convertGettextResultToUnicode
        except Exception:
            if fallbackToDefault or (lang and lang.lower().startswith(u"en")):
                gettext.install(u"arelle", 
                                self.localeDir)
        
    def startLogging(self, logFileName=None, logFileMode=None, logFileEncoding=None, logFormat=None, 
                     logLevel=None, logHandler=None):
        # add additional logging levels (for python 2.7, all of these are ints)
        logging.addLevelName(logging.INFO + 1, u"INFO-SEMANTIC")
        logging.addLevelName(logging.WARNING + 1, u"WARNING-SEMANTIC")
        logging.addLevelName(logging.WARNING + 2, u"ASSERTION-SATISFIED")
        logging.addLevelName(logging.WARNING + 3, u"INCONSISTENCY")
        logging.addLevelName(logging.ERROR - 2, u"ERROR-SEMANTIC")
        logging.addLevelName(logging.ERROR - 1, u"ASSERTION-NOT-SATISFIED")

        if logHandler is not None:
            self.logger = logging.getLogger(u"arelle")
            self.logHandler = logHandler
            self.logger.addHandler(logHandler)
        elif logFileName: # use default logging
            self.logger = logging.getLogger(u"arelle")
            if logFileName in (u"logToPrint", u"logToStdErr"):
                self.logHandler = LogToPrintHandler(logFileName)
            elif logFileName == u"logToBuffer":
                self.logHandler = LogToBufferHandler()
                self.logger.logRefObjectProperties = True
            elif logFileName.endswith(u".xml"):
                self.logHandler = LogToXmlHandler(filename=logFileName, mode=logFileMode or u"a")  # should this be "w" mode??
                self.logger.logRefObjectProperties = True
                if not logFormat:
                    logFormat = u"%(message)s"
            else:
                self.logHandler = logging.FileHandler(filename=logFileName, 
                                                      mode=logFileMode or u"a",  # should this be "w" mode??
                                                      encoding=logFileEncoding or u"utf-8")
            self.logHandler.setFormatter(LogFormatter(logFormat or u"%(asctime)s [%(messageCode)s] %(message)s - %(file)s\n"))
            self.logger.addHandler(self.logHandler)
        else:
            self.logger = None
        if self.logger:
            try:
                self.logger.setLevel((logLevel or u"debug").upper())
            except ValueError:
                loggingLevelNums = logging._levelNames if sys.version < u'3.4' else logging._levelToName
                self.addToLog(_(u"Unknown log level name: {0}, please choose from {1}").format(
                    logLevel, u', '.join(logging.getLevelName(l).lower()
                                        for l in sorted([i for i in logging.loggingLevelNums.keys()
                                                         if isinstance(i,_INT_TYPES) and i > 0]))),
                              level=logging.ERROR, messageCode=u"arelle:logLevel")
            self.logger.messageCodeFilter = None
            self.logger.messageLevelFilter = None
                
    def setLogLevelFilter(self, logLevelFilter):
        if self.logger:
            self.logger.messageLevelFilter = re.compile(logLevelFilter) if logLevelFilter else None
            
    def setLogCodeFilter(self, logCodeFilter):
        if self.logger:
            self.logger.messageCodeFilter = re.compile(logCodeFilter) if logCodeFilter else None
                        
    def addToLog(self, message, messageCode=u"", messageArgs=None, file=u"", level=logging.INFO):
        u"""Add a simple info message to the default logger
           
        :param message: Text of message to add to log.
        :type message: str
        : param messageArgs: optional dict of message format-string key-value pairs
        :type messageArgs: dict
        :param messageCode: Message code (e.g., a prefix:id of a standard error)
        :param messageCode: str
        :param file: File name (and optional line numbers) pertaining to message
        :type file: str
        """
        if self.logger is not None:
            if messageArgs:
                args = (message, messageArgs)
            else:
                args = (message,)  # pass no args if none provided
            refs = []
            if file:
                refs.append( {u"href": file} )
            self.logger.log(level, *args, extra={u"messageCode":messageCode,u"refs":refs})
        else:
            try:
                print message
            except UnicodeEncodeError:
                # extra parentheses in print to allow for 3-to-2 conversion
                print (message
                       .encode(sys.stdout.encoding, u'backslashreplace')
                       .decode(sys.stdout.encoding, u'strict'))
            
    def showStatus(self, message, clearAfter=None):
        u"""Dummy method for specialized controller classes to specialize, 
        provides user feedback on status line of GUI or web page
        
        :param message: Message to display on status widget.
        :type message: str
        :param clearAfter: Time, in ms., after which to clear the message (e.g., 5000 for 5 sec.)
        :type clearAfter: int
        """
        pass
    
    def close(self, saveConfig=False):
        u"""Closes the controller and its logger, optionally saving the user preferences configuration
           
           :param saveConfig: save the user preferences configuration
           :type saveConfig: bool
        """
        PluginManager.save(self)
        PackageManager.save(self)
        if saveConfig:
            self.saveConfig()
        if self.logger is not None:
            try:
                self.logHandler.close()
            except Exception: # fails on some earlier pythons (3.1)
                pass
        
    def saveConfig(self):
        u"""Save user preferences configuration (in json configuration file)."""
        if self.hasFileSystem:
            with io.open(self.configJsonFile, u'wt', encoding=u'utf-8') as f:
                jsonStr = _STR_UNICODE(json.dumps(self.config, ensure_ascii=False, indent=2)) # might not be unicode in 2.7
                f.write(jsonStr)  # 2.7 getss unicode this way
            
    # default non-threaded viewModelObject                 
    def viewModelObject(self, modelXbrl, objectId):
        u"""Notify any watching views to show and highlight selected object.  Generally used
        to scroll list control to object and highlight it, or if tree control, to find the object
        and open tree branches as needed for visibility, scroll to and highlight the object.
           
        :param modelXbrl: ModelXbrl (DTS) whose views are to be notified
        :type modelXbrl: ModelXbrl
        :param objectId: Selected object id (string format corresponding to ModelObject.objectId() )
        :type objectId: str
        """
        modelXbrl.viewModelObject(objectId)
            
    def reloadViews(self, modelXbrl):
        u"""Notification to reload views (probably due to change within modelXbrl).  Dummy
        for subclasses to specialize when they have a GUI or web page.
           
        :param modelXbrl: ModelXbrl (DTS) whose views are to be notified
        :type modelXbrl: ModelXbrl
        """
        pass
    
    def rssWatchUpdateOption(self, **args):
        u"""Notification to change rssWatch options, as passed in, usually from a modal dialog."""
        pass
    
    def onPackageEnablementChanged(self):
        u"""Notification that package enablement changed, usually from a modal dialog."""
        pass
        
    # default web authentication password
    def internet_user_password(self, host, realm):
        u"""Request (for an interactive UI or web page) to obtain user ID and password (usually for a proxy 
        or when getting a web page that requires entry of a password).  This function must be overridden
        in a subclass that provides interactive user interface, as the superclass provides only a dummy
        method. 
           
        :param host: The host that is requesting the password
        :type host: str
        :param realm: The domain on the host that is requesting the password
        :type realm: str
        :returns: tuple -- ('myusername','mypassword')
        """
        return (u'myusername',u'mypassword')
    
    # default web authentication password
    def internet_logon(self, url, quotedUrl, dialogCaption, dialogText):
        u"""Web file retieval results in html that appears to require user logon,
        if interactive allow the user to log on. 
           
        :url: The URL as requested (by an import, include, href, schemaLocation, ...)
        :quotedUrl: The processed and retrievable URL
        :dialogCaption: The dialog caption for the situation
        :dialogText:  The dialog text for the situation at hand
        :returns: string -- 'retry' if user logged on and file can be retried, 
                            'cancel' to abandon retrieval
                            'no' if the file is expected and valid contents (not a logon request)
        """
        return u'cancel'
    
    # if no text, then return what is on the clipboard, otherwise place text onto clipboard
    def clipboardData(self, text=None):
        u"""Places text onto the clipboard (if text is not None), otherwise retrieves and returns text from the clipboard.
        Only supported for those platforms that have clipboard support in the current python implementation (macOS
        or ActiveState Windows Python).
           
        :param text: Text to place onto clipboard if not None, otherwise retrieval of text from clipboard.
        :type text: str
        :returns: str -- text from clipboard if parameter text is None, otherwise returns None if text is provided
        """
        if self.hasClipboard:
            try:
                if sys.platform == u"darwin":
                    import subprocess
                    if text is None:
                        p = subprocess.Popen([u'pbpaste'], stdout=subprocess.PIPE)
                        retcode = p.wait()
                        text = p.stdout.read().decode(u'utf-8')  # default utf8 may not be right for mac
                        return text
                    else:
                        p = subprocess.Popen([u'pbcopy'], stdin=subprocess.PIPE)
                        p.stdin.write(text.encode(u'utf-8'))  # default utf8 may not be right for mac
                        p.stdin.close()
                        retcode = p.wait()
                elif sys.platform.startswith(u"win"):
                    import win32clipboard
                    win32clipboard.OpenClipboard()
                    if text is None:
                        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT):
                            return win32clipboard.GetClipboardData().decode(u"utf8")
                    else:
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardData(win32clipboard.CF_TEXT, text.encode(u"utf8"))
                    win32clipboard.CloseClipboard()
                else: # Unix/Linux
                    import gtk
                    clipbd = gtk.Clipboard(display=gtk.gdk.display_get_default(), selection=u"CLIPBOARD")
                    if text is None:
                        return clipbd.wait_for_text().decode(u"utf8")
                    else:
                        clipbd.set_text(text.encode(u"utf8"), len=-1)
            except Exception:
                pass
        return None
    
    @property
    def memoryUsed(self):
        try:
            global osPrcs
            if self.isMSW:
                if osPrcs is None:
                    import win32process as osPrcs
                return osPrcs.GetProcessMemoryInfo(osPrcs.GetCurrentProcess())[u'WorkingSetSize'] / 1024
            elif sys.platform == u"sunos5": # ru_maxrss is broken on sparc
                if osPrcs is None:
                    import resource as osPrcs
                return int(subprocess.getoutput(u"ps -p {0} -o rss".format(os.getpid())).rpartition(u'\n')[2])
            else: # unix or linux where ru_maxrss works
                import resource as osPrcs
                return osPrcs.getrusage(osPrcs.RUSAGE_SELF).ru_maxrss # in KB
        except Exception:
            pass
        return 0

class LogFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        super(LogFormatter, self).__init__(fmt, datefmt)
        
    def format(self, record):
        # provide a file parameter made up from refs entries
        fileLines = defaultdict(set)
        for ref in record.refs:
            href = ref.get(u"href")
            if href:
                fileLines[href.partition(u"#")[0]].add(ref.get(u"sourceLine", 0))
        record.file = u", ".join(file + u" " + u', '.join(unicode(line) 
                                                       for line in sorted(lines, key=lambda l: l)
                                                       if line)
                                for file, lines in sorted(fileLines.items()))
        try:
            formattedMessage = super(LogFormatter, self).format(record)
        except (KeyError, TypeError, ValueError), ex:
            formattedMessage = u"Message: "
            if getattr(record, u"messageCode", u""):
                formattedMessage += u"[{0}] ".format(record.messageCode)
            if getattr(record, u"msg", u""):
                formattedMessage += record.msg + u" "
            if isinstance(record.args, dict) and u'error' in record.args: # args may be list or empty
                formattedMessage += record.args[u'error']
            formattedMessage += u" \nMessage log error: " + unicode(ex)
        del record.file
        return formattedMessage

class LogToPrintHandler(logging.Handler):
    u"""
    .. class:: LogToPrintHandler()
    
    A log handler that emits log entries to standard out as they are logged.
    
    CAUTION: Output is utf-8 encoded, which is fine for saving to files, but may not display correctly in terminal windows.

    :param logOutput: 'logToStdErr' to cause log printint to stderr instead of stdout
    :type logOutput: str
    """
    def __init__(self, logOutput):
        super(LogToPrintHandler, self).__init__()
        if logOutput == u"logToStdErr":
            self.logFile = sys.stderr
        else:
            self.logFile = None
        
    def emit(self, logRecord):
        file = sys.stderr if self.logFile else None
        logEntry = self.format(logRecord)
        if not isPy3:
            logEntry = logEntry.encode(u"utf-8", u"replace")
        try:
            print >>file, logEntry
        except UnicodeEncodeError:
            # extra parentheses in print to allow for 3-to-2 conversion
            print >>file, (logEntry
                   .encode(sys.stdout.encoding, u'backslashreplace')
                   .decode(sys.stdout.encoding, u'strict'))

class LogHandlerWithXml(logging.Handler):        
    def __init__(self):
        super(LogHandlerWithXml, self).__init__()
        
    def recordToXml(self, logRec):
        def entityEncode(arg, truncateAt=32767):  # be sure it's a string, vs int, etc, and encode &, <, ".
            s = unicode(arg)
            s = s if len(s) <= truncateAt else s[:truncateAt] + u'...'
            return s.replace(u"&",u"&amp;").replace(u"<",u"&lt;").replace(u'"',u'&quot;')
        
        def propElts(properties, indent, truncatAt=128):
            nestedIndent = indent + u' '
            return indent.join(u'<property name="{0}" value="{1}"{2}>'.format(
                                    entityEncode(p[0]),
                                    entityEncode(p[1], truncateAt=truncatAt),
                                    u'/' if len(p) == 2 
                                    else u'>' + nestedIndent + propElts(p[2],nestedIndent) + indent + u'</property')
                                for p in properties 
                                if 2 <= len(p) <= 3)
        
        msg = self.format(logRec)
        if logRec.args:
            args = u"".join([u' {0}="{1}"'.format(n, entityEncode(v, truncateAt=128)) 
                            for n, v in logRec.args.items()])
        else:
            args = u""
        refs = u"\n ".join(u'\n <ref href="{0}"{1}{2}{3}>'.format(
                        entityEncode(ref[u"href"]), 
                        u' sourceLine="{0}"'.format(ref[u"sourceLine"]) if u"sourceLine" in ref else u'',
                        u''.join(u' {}="{}"'.format(k,entityEncode(v)) 
                                                  for k,v in ref[u"customAttributes"].items())
                             if u'customAttributes' in ref else u'',
                        (u">\n  " + propElts(ref[u"properties"],u"\n  ", 32767) + u"\n </ref" ) if u"properties" in ref else u'/')
                       for ref in logRec.refs)
        return (u'<entry code="{0}" level="{1}">'
                u'\n <message{2}>{3}</message>{4}'
                u'</entry>\n'.format(logRec.messageCode, 
                                    logRec.levelname.lower(), 
                                    args, 
                                    entityEncode(msg), 
                                    refs))
    
class LogToXmlHandler(LogHandlerWithXml):
    u"""
    .. class:: LogToXmlHandler(filename)
    
    A log handler that writes log entries to named XML file (utf-8 encoded) upon closing the application.
    """
    def __init__(self, filename, mode=u'w'):
        super(LogToXmlHandler, self).__init__()
        self.filename = filename
        self.logRecordBuffer = []
        self.filemode = mode
    def flush(self):
        if self.filename == u"logToStdOut.xml":
            print u'<?xml version="1.0" encoding="utf-8"?>'
            print u'<log>'
            for logRec in self.logRecordBuffer:
                logRecXml = self.recordToXml(logRec)
                try:
                    print logRecXml
                except UnicodeEncodeError:
                    # extra parentheses in print to allow for 3-to-2 conversion
                    print (logRecXml
                           .encode(sys.stdout.encoding, u'backslashreplace')
                           .decode(sys.stdout.encoding, u'strict'))
            print u'</log>'
        else:
            print u"filename=" + self.filename
            with open(self.filename, self.filemode, encoding=u'utf-8') as fh:
                fh.write(u'<?xml version="1.0" encoding="utf-8"?>\n')
                fh.write(u'<log>\n')
                for logRec in self.logRecordBuffer:
                    fh.write(self.recordToXml(logRec))
                fh.write(u'</log>\n')  
    def emit(self, logRecord):
        self.logRecordBuffer.append(logRecord)

class LogToBufferHandler(LogHandlerWithXml):
    u"""
    .. class:: LogToBufferHandler()
    
    A log handler that writes log entries to a memory buffer for later retrieval (to a string) in XML, JSON, or text lines,
    usually for return to a web service or web page call.
    """
    def __init__(self):
        super(LogToBufferHandler, self).__init__()
        self.logRecordBuffer = []
        
    def flush(self):
        pass # do nothing
    
    def getXml(self):
        u"""Returns an XML document (as a string) representing the messages in the log buffer, and clears the buffer.
        
        :reeturns: str -- XML document string of messages in the log buffer.
        """
        xml = [u'<?xml version="1.0" encoding="utf-8"?>\n',
               u'<log>']
        for logRec in self.logRecordBuffer:
            xml.append(self.recordToXml(logRec))
        xml.append(u'</log>')  
        self.logRecordBuffer = []
        return u'\n'.join(xml)
    
    def getJson(self):
        u"""Returns an JSON string representing the messages in the log buffer, and clears the buffer.
        
        :returns: str -- json representation of messages in the log buffer
        """
        entries = []
        for logRec in self.logRecordBuffer:
            message = { u"text": self.format(logRec) }
            if logRec.args:
                for n, v in logRec.args.items():
                    message[n] = v
            entry = {u"code": logRec.messageCode,
                     u"level": logRec.levelname.lower(),
                     u"refs": logRec.refs,
                     u"message": message}
            entries.append(entry)
        self.logRecordBuffer = []
        return json.dumps( {u"log": entries} )
    
    def getLines(self):
        u"""Returns a list of the message strings in the log buffer, and clears the buffer.
        
        :returns: [str] -- list of strings representing messages corresponding to log buffer entries
        """
        lines = [self.format(logRec) for logRec in self.logRecordBuffer]
        self.logRecordBuffer = []
        return lines
    
    def getText(self, separator=u'\n'):
        u"""Returns a string of the lines in the log buffer, separated by newline or provided separator.
        
        :param separator: Line separator (default is platform os newline character)
        :type separator: str
        :returns: str -- joined lines of the log buffer.
        """
        return separator.join(self.getLines())
    
    def emit(self, logRecord):
        self.logRecordBuffer.append(logRecord)

