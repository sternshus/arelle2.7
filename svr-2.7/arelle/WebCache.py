u'''
Created on Oct 5, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from __future__ import division
from __future__ import with_statement
import os, posixpath, sys, re, shutil, time, calendar, io, json, logging
from io import open
if sys.version[0] >= u'3':
    from urllib import quote, unquote
    from urllib import ContentTooShortError
    from urllib2 import URLError, HTTPError
    from httplib import IncompleteRead
    from urllib import request
    from urllib import request as proxyhandlers
else: # python 2.7.2
    from urllib import quote, unquote
    from urllib import ContentTooShortError
    from httplib import IncompleteRead
    from urllib2 import URLError, HTTPError
    import urllib2 as proxyhandlers
from arelle.FileSource import SERVER_WEB_CACHE
from arelle.UrlUtil import isHttpUrl
addServerWebCache = None
    
DIRECTORY_INDEX_FILE = u"!~DirectoryIndex~!"
INF = float(u"inf")

def proxyDirFmt(httpProxyTuple):
    if isinstance(httpProxyTuple,(tuple,list)) and len(httpProxyTuple) == 5:
        useOsProxy, urlAddr, urlPort, user, password = httpProxyTuple
        if useOsProxy:
            return None
        elif urlAddr:
            if user and password:
                userPart = u"{0}:{1}@".format(user, password)
            else:
                userPart = u""
            if urlPort:
                portPart = u":{0}".format(urlPort)
            else:
                portPart = u""
            return {u"http": u"http://{0}{1}{2}".format(userPart, urlAddr, portPart) }
            #return {"http": "{0}{1}{2}".format(userPart, urlAddr, portPart) }
        else:
            return {}  # block use of any proxy
    else:
        return None # use system proxy
    
def proxyTuple(url): # system, none, or http:[user[:passowrd]@]host[:port]
    if url == u"none":
        return (False, u"", u"", u"", u"")
    elif url == u"system":
        return (True, u"", u"", u"", u"")
    userpwd, sep, hostport = url.rpartition(u"://")[2].rpartition(u"@")
    urlAddr, sep, urlPort = hostport.partition(u":")
    user, sep, password = userpwd.partition(u":")
    return (False, urlAddr, urlPort, user, password)
    
def lastModifiedTime(headers):
    if headers:
        headerTimeStamp = headers[u"last-modified"]
        if headerTimeStamp:
            from email.utils import parsedate
            hdrTime = parsedate(headerTimeStamp)
            if hdrTime:
                return time.mktime(hdrTime)
    return None
    

class WebCache(object):
    
    default_timeout = None
    
    def __init__(self, cntlr, httpProxyTuple):
        self.cntlr = cntlr
        #self.proxies = request.getproxies()
        #self.proxies = {'ftp': 'ftp://63.192.17.1:3128', 'http': 'http://63.192.17.1:3128', 'https': 'https://63.192.17.1:3128'}
        self._timeout = None        
        
        self.resetProxies(httpProxyTuple)
        
        #self.opener.addheaders = [('User-agent', 'Mozilla/5.0')]

        #self.opener = WebCacheUrlOpener(cntlr, proxyDirFmt(httpProxyTuple)) # self.proxies)
        
        if cntlr.isGAE:
            self.cacheDir = SERVER_WEB_CACHE # GAE type servers
            self.encodeFileChars = re.compile(ur'[:^]') 
        elif sys.platform == u"darwin" and u"/Application Support/" in cntlr.userAppDir:
            self.cacheDir = cntlr.userAppDir.replace(u"Application Support",u"Caches")
            self.encodeFileChars = re.compile(ur'[:^]') 
            
        else:  #windows and unix
            self.cacheDir = cntlr.userAppDir + os.sep + u"cache"
            if sys.platform.startswith(u"win"):
                self.encodeFileChars = re.compile(ur'[<>:"\\|?*^]')
            else:
                self.encodeFileChars = re.compile(ur'[:^]') 
        self.decodeFileChars = re.compile(ur'\^[0-9]{3}')
        self.workOffline = False
        self._logDownloads = False
        self.maxAgeSeconds = 60.0 * 60.0 * 24.0 * 7.0 # seconds before checking again for file
        if cntlr.hasFileSystem:
            self.urlCheckJsonFile = cntlr.userAppDir + os.sep + u"cachedUrlCheckTimes.json"
            try:
                with io.open(self.urlCheckJsonFile, u'rt', encoding=u'utf-8') as f:
                    self.cachedUrlCheckTimes = json.load(f)
            except Exception:
                self.cachedUrlCheckTimes = {}
        else:
            self.cachedUrlCheckTimes = {}
        self.cachedUrlCheckTimesModified = False
            

    @property
    def timeout(self):
        return self._timeout or WebCache.default_timeout

    @timeout.setter
    def timeout(self, seconds):
        self._timeout = seconds

    @property
    def recheck(self):
        days = self.maxAgeSeconds / (60.0 * 60.0 * 24.0)
        if days == INF:
            return u"never" 
        elif days >= 30:
            return u"monthly"
        elif days >= 7:
            return u"weekly"
        elif days >=1:
            return u"daily"
        else:
            return u"(invalid)"

    @timeout.setter
    def recheck(self, recheckInterval):
        self.maxAgeSeconds = {u"daily": 1.0, u"weekly": 7.0, u"monthly": 30.0, u"never": INF
                              }.get(recheckInterval, 7.0) * (60.0 * 60.0 * 24.0) 

    @property
    def logDownloads(self):
        return self._logDownloads

    @timeout.setter
    def logDownloads(self, _logDownloads):
        self._logDownloads = _logDownloads

    def saveUrlCheckTimes(self):
        if self.cachedUrlCheckTimesModified:
            with io.open(self.urlCheckJsonFile, u'wt', encoding=u'utf-8') as f:
                jsonStr = _STR_UNICODE(json.dumps(self.cachedUrlCheckTimes, ensure_ascii=False, indent=0)) # might not be unicode in 2.7
                f.write(jsonStr)  # 2.7 gets unicode this way
        self.cachedUrlCheckTimesModified = False
        
    def resetProxies(self, httpProxyTuple):
        try:
            from ntlm import HTTPNtlmAuthHandler
            self.hasNTLM = True
        except ImportError:
            self.hasNTLM = False
        self.proxy_handler = proxyhandlers.ProxyHandler(proxyDirFmt(httpProxyTuple))
        self.proxy_auth_handler = proxyhandlers.ProxyBasicAuthHandler()
        self.http_auth_handler = proxyhandlers.HTTPBasicAuthHandler()
        if self.hasNTLM:
            self.ntlm_auth_handler = HTTPNtlmAuthHandler.HTTPNtlmAuthHandler()            
            self.opener = proxyhandlers.build_opener(self.proxy_handler, self.ntlm_auth_handler, self.proxy_auth_handler, self.http_auth_handler)
        else:
            self.opener = proxyhandlers.build_opener(self.proxy_handler, self.proxy_auth_handler, self.http_auth_handler)

        #self.opener.close()
        #self.opener = WebCacheUrlOpener(self.cntlr, proxyDirFmt(httpProxyTuple))
        
    
    def normalizeUrl(self, url, base=None):
        if url and not (isHttpUrl(url) or os.path.isabs(url)):
            if base is not None and not isHttpUrl(base) and u'%' in url:
                url = unquote(url)
            if base:
                if isHttpUrl(base):
                    scheme, sep, path = base.partition(u"://")
                    normedPath = scheme + sep + posixpath.normpath(os.path.dirname(path) + u"/" + url)
                else:
                    if u'%' in base:
                        base = unquote(base)
                    normedPath = os.path.normpath(os.path.join(os.path.dirname(base),url))
            else: # includes base == '' (for forcing relative path)
                normedPath = url
            if normedPath.startswith(u"file://"): normedPath = normedPath[7:]
            elif normedPath.startswith(u"file:\\"): normedPath = normedPath[6:]
            
            # no base, not normalized, must be relative to current working directory
            if base is None and not os.path.isabs(url): 
                normedPath = os.path.abspath(normedPath)
        else:
            normedPath = url
        
        if normedPath:
            if isHttpUrl(normedPath):
                scheme, sep, pathpart = normedPath.partition(u"://")
                pathpart = pathpart.replace(u'\\',u'/')
                endingSep = u'/' if pathpart[-1] == u'/' else u''  # normpath drops ending directory separator
                return scheme + u"://" + posixpath.normpath(pathpart) + endingSep
            normedPath = os.path.normpath(normedPath)
            if normedPath.startswith(self.cacheDir):
                normedPath = self.cacheFilepathToUrl(normedPath)
        return normedPath

    def encodeForFilename(self, pathpart):
        return self.encodeFileChars.sub(lambda m: u'^{0:03}'.format(ord(m.group(0))), pathpart)
    
    def urlToCacheFilepath(self, url):
        scheme, sep, path = url.partition(u"://")
        filepath = [self.cacheDir, scheme] 
        pathparts = path.split(u'/')
        user, sep, server = pathparts[0].partition(u"@")
        if not sep:
            server = user
            user = None
        host, sep, port = server.partition(u':')
        filepath.append(self.encodeForFilename(host))
        if port:
            filepath.append(u"^port" + port)
        if user:
            filepath.append(u"^user" + self.encodeForFilename(user) ) # user may have : or other illegal chars
        filepath.extend(self.encodeForFilename(pathpart) for pathpart in pathparts[1:])
        if url.endswith(u"/"):  # default index file
            filepath.append(DIRECTORY_INDEX_FILE)
        return os.sep.join(filepath)
    
    def cacheFilepathToUrl(self, cacheFilepath):
        urlparts = cacheFilepath[len(self.cacheDir)+1:].split(os.sep)
        urlparts[0] += u':/'  # add separator between http and file parts, less one '/'
        if urlparts[2].startswith(u"^port"):
            urlparts[1] += u":" + urlparts[2][5:]  # the port number
            del urlparts[2]
        if urlparts[2].startswith(u"^user"):
            urlparts[1] = urlparts[2][5:] + u"@" + urlparts[1]  # the user part
            del urlparts[2]
        if urlparts[-1] == DIRECTORY_INDEX_FILE:
            urlparts[-1] = u""  # restore default index file syntax
        return u'/'.join(self.decodeFileChars  # remove cacheDir part
                        .sub(lambda c: unichr( int(c.group(0)[1:]) ), # remove ^nnn encoding
                         urlpart) for urlpart in urlparts)
    
    def getfilename(self, url, base=None, reload=False, checkModifiedTime=False, normalize=False, filenameOnly=False):
        if url is None:
            return url
        if base is not None or normalize:
            url = self.normalizeUrl(url, base)
        urlScheme, schemeSep, urlSchemeSpecificPart = url.partition(u"://")
        if schemeSep and urlScheme in (u"http", u"https"):
            # form cache file name (substituting _ for any illegal file characters)
            filepath = self.urlToCacheFilepath(url)
            if self.cacheDir == SERVER_WEB_CACHE:
                # server web-cached files are downloaded when opening to prevent excessive memcache api calls
                return filepath
            # quotedUrl has scheme-specific-part quoted except for parameter separators
            quotedUrl = urlScheme + schemeSep + quote(urlSchemeSpecificPart, u'/?=&')
            # handle default directory requests
            if filepath.endswith(u"/"):
                filepath += DIRECTORY_INDEX_FILE
            if os.sep == u'\\':
                filepath = filepath.replace(u'/', u'\\')
            if self.workOffline or filenameOnly:
                return filepath
            filepathtmp = filepath + u".tmp"
            fileExt = os.path.splitext(filepath)[1]
            timeNow = time.time()
            timeNowStr = time.strftime(u'%Y-%m-%dT%H:%M:%S UTC', time.gmtime(timeNow))
            retrievingDueToRecheckInterval = False
            if not reload and os.path.exists(filepath):
                if url in self.cachedUrlCheckTimes and not checkModifiedTime:
                    cachedTime = calendar.timegm(time.strptime(self.cachedUrlCheckTimes[url], u'%Y-%m-%dT%H:%M:%S UTC'))
                else:
                    cachedTime = 0
                if timeNow - cachedTime > self.maxAgeSeconds:
                    # weekly check if newer file exists
                    newerOnWeb = False
                    try: # no provision here for proxy authentication!!!
                        remoteFileTime = lastModifiedTime( self.getheaders(quotedUrl) )
                        if remoteFileTime and remoteFileTime > os.path.getmtime(filepath):
                            newerOnWeb = True
                    except:
                        pass # for now, forget about authentication here
                    if not newerOnWeb:
                        # update ctime by copying file and return old file
                        self.cachedUrlCheckTimes[url] = timeNowStr
                        self.cachedUrlCheckTimesModified = True
                        return filepath
                    retrievingDueToRecheckInterval = True
                else:
                    return filepath
            filedir = os.path.dirname(filepath)
            if not os.path.exists(filedir):
                os.makedirs(filedir)
            # Retrieve over HTTP and cache, using rename to avoid collisions
            # self.modelManager.addToLog('web caching: {0}'.format(url))
            
            # download to a temporary name so it is not left readable corrupted if download fails
            retryCount = 5
            while retryCount > 0:
                try:
                    self.progressUrl = url
                    savedfile, headers, initialBytes = self.retrieve(
                    #savedfile, headers = self.opener.retrieve(
                                      quotedUrl,
                                      filename=filepathtmp,
                                      reporthook=self.reportProgress)
                    
                    # check if this is a real file or a wifi or web logon screen
                    if fileExt in set([u".xsd", u".xml", u".xbrl"]):
                        if "<html" in initialBytes:
                            if retrievingDueToRecheckInterval: 
                                return self.internetRecheckFailedRecovery(filepath, url, 
                                                                          u"file contents appear to be an html logon request", 
                                                                          timeNowStr) 
                            response = None  # found possible logon request
                            if self.cntlr.hasGui:
                                response = self.cntlr.internet_logon(url, quotedUrl, 
                                                                     _(u"Unexpected HTML in {0}").format(url),
                                                                     _(u"Is this a logon page? If so, click 'yes', else click 'no' if it is the expected XBRL content, or 'cancel' to abort retrieval: \n\n{0}")
                                                                     .format(initialBytes[:1500]))
                            if response == u"retry":
                                retryCount -= 1
                                continue
                            elif response != u"no":
                                self.cntlr.addToLog(_(u"Web file appears to be an html logon request, not retrieved: %(URL)s \nContents: \n%(contents)s"),
                                                    messageCode=u"webCache:invalidRetrieval",
                                                    messageArgs={u"URL": url, u"contents": initialBytes},
                                                    level=logging.ERROR)
                                return None
                    
                    retryCount = 0
                except (ContentTooShortError, IncompleteRead), err:
                    if retrievingDueToRecheckInterval: 
                        return self.internetRecheckFailedRecovery(filepath, url, err, timeNowStr) 
                    if retryCount > 1:
                        self.cntlr.addToLog(_(u"%(error)s \nunsuccessful retrieval of %(URL)s \n%(retryCount)s retries remaining"),
                                            messageCode=u"webCache:retryingOperation",
                                            messageArgs={u"error": err, u"URL": url, u"retryCount": retryCount},
                                            level=logging.ERROR)
                        retryCount -= 1
                        continue
                    self.cntlr.addToLog(_(u"%(error)s \nretrieving %(URL)s"),
                                        messageCode=u"webCache:contentTooShortError",
                                        messageArgs={u"URL": url, u"error": err},
                                        level=logging.ERROR)
                    if os.path.exists(filepathtmp):
                        os.remove(filepathtmp)
                    return None
                    # handle file is bad
                except (HTTPError, URLError), err:
                    try:
                        tryWebAuthentication = False
                        if err.code == 401:
                            tryWebAuthentication = True
                            if u'www-authenticate' in err.hdrs:
                                match = re.match(u'[ \t]*([^ \t]+)[ \t]+realm="([^"]*)"', err.hdrs[u'www-authenticate'])
                                if match:
                                    scheme, realm = match.groups()
                                    if scheme.lower() == u'basic':
                                        host = os.path.dirname(quotedUrl)
                                        userPwd = self.cntlr.internet_user_password(host, realm)
                                        if isinstance(userPwd,(tuple,list)):
                                            self.http_auth_handler.add_password(realm=realm,uri=host,user=userPwd[0],passwd=userPwd[1]) 
                                            retryCount -= 1
                                            continue
                                    self.cntlr.addToLog(_(u"'%(scheme)s' www-authentication for realm '%(realm)s' is required to access %(URL)s\n%(error)s"),
                                                        messageCode=u"webCache:unsupportedWWWAuthentication",
                                                        messageArgs={u"scheme": scheme, u"realm": realm, u"URL": url, u"error": err},
                                                        level=logging.ERROR)
                        elif err.code == 407:
                            tryWebAuthentication = True
                            if u'proxy-authenticate' in err.hdrs:
                                match = re.match(u'[ \t]*([^ \t]+)[ \t]+realm="([^"]*)"', err.hdrs[u'proxy-authenticate'])
                                if match:
                                    scheme, realm = match.groups()
                                    host = self.proxy_handler.proxies.get(u'http')
                                    if scheme.lower() == u'basic':
                                        userPwd = self.cntlr.internet_user_password(host, realm)
                                        if isinstance(userPwd,(tuple,list)):
                                            self.proxy_auth_handler.add_password(realm=realm,uri=host,user=userPwd[0],passwd=userPwd[1]) 
                                            retryCount -= 1
                                            continue
                                    self.cntlr.addToLog(_(u"'%(scheme)s' proxy-authentication for realm '%(realm)s' is required to access %(URL)s\n%(error)s"),
                                                        messageCode=u"webCache:unsupportedProxyAuthentication",
                                                        messageArgs={u"scheme": scheme, u"realm": realm, u"URL": url, u"error": err},
                                                        level=logging.ERROR)
                        if retrievingDueToRecheckInterval:
                            return self.internetRecheckFailedRecovery(filepath, url, err, timeNowStr) 
                        if tryWebAuthentication:
                            # may be a web login authentication request
                            response = None  # found possible logon request
                            if self.cntlr.hasGui:
                                response = self.cntlr.internet_logon(url, quotedUrl, 
                                                                     _(u"HTTP {0} authentication request").format(err.code),                                                                                                                                          _(u"Unexpected HTML in {0}").format(url),
                                                                     _(u"Is browser-based possible? If so, click 'yes', or 'cancel' to abort retrieval: \n\n{0}")
                                                                     .format(url))
                            if response == u"retry":
                                retryCount -= 1
                                continue
                            elif response != u"no":
                                self.cntlr.addToLog(_(u"Web file HTTP 401 (authentication required) response, not retrieved: %(URL)s"),
                                                    messageCode=u"webCache:authenticationRequired",
                                                    messageArgs={u"URL": url},
                                                    level=logging.ERROR)
                                return None
                                    
                    except AttributeError:
                        pass
                    if retrievingDueToRecheckInterval: 
                        return self.internetRecheckFailedRecovery(filepath, url, err, timeNowStr) 
                    self.cntlr.addToLog(_(u"%(error)s \nretrieving %(URL)s"),
                                        messageCode=u"webCache:retrievalError",
                                        messageArgs={u"error": err, u"URL": url},
                                        level=logging.ERROR)
                    return None
                
                except Exception, err:
                    if retryCount > 1:
                        self.cntlr.addToLog(_(u"%(error)s \nunsuccessful retrieval of %(URL)s \n%(retryCount)s retries remaining"),
                                            messageCode=u"webCache:retryingOperation",
                                            messageArgs={u"error": err, u"URL": url, u"retryCount": retryCount},
                                            level=logging.ERROR)
                        retryCount -= 1
                        continue
                    if retrievingDueToRecheckInterval: 
                        return self.internetRecheckFailedRecovery(filepath, url, err, timeNowStr) 
                    if self.cntlr.hasGui:
                        self.cntlr.addToLog(_(u"%(error)s \nunsuccessful retrieval of %(URL)s \nswitching to work offline"),
                                            messageCode=u"webCache:attemptingOfflineOperation",
                                            messageArgs={u"error": err, u"URL": url},
                                            level=logging.ERROR)
                        # try working offline
                        self.workOffline = True
                        return filepath
                    else:  # don't switch offline unexpectedly in scripted (batch) operation
                        self.cntlr.addToLog(_(u"%(error)s \nunsuccessful retrieval of %(URL)s"),
                                            messageCode=u"webCache:unsuccessfulRetrieval",
                                            messageArgs={u"error": err, u"URL": url},
                                            level=logging.ERROR)
                        if os.path.exists(filepathtmp):
                            os.remove(filepathtmp)
                        return None
                
                # rename temporarily named downloaded file to desired name                
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception, err:
                        self.cntlr.addToLog(_(u"%(error)s \nUnsuccessful removal of prior file %(filepath)s \nPlease remove with file manager."),
                                            messageCode=u"webCache:cachedPriorFileLocked",
                                            messageArgs={u"error": err, u"filepath": filepath},
                                            level=logging.ERROR)
                try:
                    os.rename(filepathtmp, filepath)
                    if self._logDownloads:
                        self.cntlr.addToLog(_(u"Downloaded %(URL)s"),
                                            messageCode=u"webCache:download",
                                            messageArgs={u"URL": url, u"filepath": filepath},
                                            level=logging.INFO)
                except Exception, err:
                    self.cntlr.addToLog(_(u"%(error)s \nUnsuccessful renaming of downloaded file to active file %(filepath)s \nPlease remove with file manager."),
                                        messageCode=u"webCache:cacheDownloadRenamingError",
                                        messageArgs={u"error": err, u"filepath": filepath},
                                        level=logging.ERROR)
                webFileTime = lastModifiedTime(headers)
                if webFileTime: # set mtime to web mtime
                    os.utime(filepath,(webFileTime,webFileTime))
                self.cachedUrlCheckTimes[url] = timeNowStr
                self.cachedUrlCheckTimesModified = True
                return filepath
        
        if url.startswith(u"file://"): url = url[7:]
        elif url.startswith(u"file:\\"): url = url[6:]
        if os.sep == u'\\':
            url = url.replace(u'/', u'\\')
        return url
    
    def internetRecheckFailedRecovery(self, filepath, url, err, timeNowStr):
        self.cntlr.addToLog(_(u"During refresh of web file ignoring error: %(error)s for %(URL)s"),
                            messageCode=u"webCache:unableToRefreshFile",
                            messageArgs={u"URL": url, u"error": err},
                            level=logging.info)
        # skip this checking cycle, act as if retrieval was ok
        self.cachedUrlCheckTimes[url] = timeNowStr
        self.cachedUrlCheckTimesModified = True
        return filepath
    
    def reportProgress(self, blockCount, blockSize, totalSize):
        if totalSize > 0:
            self.cntlr.showStatus(_(u"web caching {0}: {1:.0f} of {2:.0f} KB").format(
                    self.progressUrl,
                    blockCount * blockSize / 1024,
                    totalSize / 1024))
        else:
            self.cntlr.showStatus(_(u"web caching {0}: {1:.0f} KB").format(
                    self.progressUrl,
                    blockCount * blockSize / 1024))

    def clear(self):
        for cachedProtocol in (u"http", u"https"):
            cachedProtocolDir = os.path.join(self.cacheDir, cachedProtocol)
            if os.path.exists(cachedProtocolDir):
                shutil.rmtree(cachedProtocolDir, True)
        
    def getheaders(self, url):
        if url and isHttpUrl(url):
            try:
                fp = self.opener.open(url, timeout=self.timeout)
                headers = fp.info()
                fp.close()
                return headers
            except Exception:
                pass
        return {}
    
    def geturl(self, url):  # get the url that the argument url redirects or resolves to
        if url and isHttpUrl(url):
            try:
                fp = self.opener.open(url, timeout=self.timeout)
                actualurl = fp.geturl()
                fp.close()
                return actualurl
            except Exception:
                pass
        return None
        
    def retrieve(self, url, filename=None, filestream=None, reporthook=None, data=None):
        # return filename, headers (in dict), initial file bytes (to detect logon requests)
        headers = None
        initialBytes = ''
        fp = self.opener.open(url, data, timeout=self.timeout)
        try:
            headers = fp.info()
            if filename:
                tfp = open(filename, u'wb')
            elif filestream:
                tfp = filestream
            try:
                result = filename, headers
                bs = 1024*8
                size = -1
                read = 0
                blocknum = 0
                if reporthook:
                    if u"content-length" in headers:
                        size = int(headers[u"Content-Length"])
                    reporthook(blocknum, bs, size)
                while 1:
                    block = fp.read(bs)
                    if not block:
                        break
                    read += len(block)
                    tfp.write(block)
                    if blocknum == 0:
                        initialBytes = block
                    blocknum += 1
                    if reporthook:
                        reporthook(blocknum, bs, size)
            finally:
                if filename:
                    tfp.close()
        finally:
            if fp:
                fp.close()
        # raise exception if actual size does not match content-length header
        if size >= 0 and read < size:
            raise ContentTooShortError(
                _(u"retrieval incomplete: got only %i out of %i bytes")
                % (read, size), result)

        if filestream:
            tfp.seek(0)
        return filename, headers, initialBytes

u'''
class WebCacheUrlOpener(request.FancyURLopener):
    def __init__(self, cntlr, proxies=None):
        self.cntlr = cntlr
        super(WebCacheUrlOpener, self).__init__(proxies)
        self.version = 'Mozilla/5.0'

    def http_error_401(self, url, fp, errcode, errmsg, headers, data=None, retry=False):
        super(WebCacheUrlOpener, self).http_error_401(url, fp, errcode, errmsg, headers, data, True)
        
    def http_error_407(self, url, fp, errcode, errmsg, headers, data=None, retry=False):
        super(WebCacheUrlOpener, self).http_error_407(self, url, fp, errcode, errmsg, headers, data, True)
        
    def prompt_user_passwd(self, host, realm):
        return self.cntlr.internet_user_password(host, realm)
'''
    