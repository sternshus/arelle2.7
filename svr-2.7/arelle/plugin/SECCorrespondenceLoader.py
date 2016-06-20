# -*- coding: utf-8 -*-

u'''
SECCorrespondenceLoader is a plug-in to both GUI menu and command line/web service
that loads a Correspondence tar.gz file.

(c) Copyright 2014 Mark V Systems Limited, All rights reserved.
'''
import datetime, re, os, time
from arelle import FileSource, ModelDocument
from arelle.ModelRssObject import ModelRssObject
from arelle.XmlValidate import UNVALIDATED, VALID

class SECCorrespondenceItem(object):
    def __init__(self, modelXbrl, fileName, entryUrl):
        self.cikNumber = None
        self.accessionNumber = None
        self.fileNumber = None
        self.companyName = None
        self.formType = None
        pubDate = os.path.basename(modelXbrl.uri).partition(u".")[0]
        try:
            self.pubDate = datetime.datetime(int(pubDate[0:4]), int(pubDate[4:6]), int(pubDate[6:8]))
            self.acceptanceDatetime = self.pubDate
            self.filingDate = self.pubDate.date()
        except ValueError:
            self.pubDate = self.acceptanceDatetime = self.filingDate = None
        self.filingDate = None
        self.period = None
        self.assignedSic = None
        self.fiscalYearEnd = None
        self.htmlUrl = None
        self.url = entryUrl
        self.zippedUrl = entryUrl
        self.htmURLs = ((fileName, entryUrl),)
        self.status = u"not tested"
        self.results = None
        self.assertions = None
        self.objectIndex = len(modelXbrl.modelObjects)
        modelXbrl.modelObjects.append(self)
        
    def setResults(self, modelXbrl):
        self.results = []
        self.assertionUnsuccessful = False
        # put error codes first, sorted, then assertion result (dict's)
        self.status = u"pass"
        for error in modelXbrl.errors:
            if isinstance(error,dict):  # assertion results
                self.assertions = error
                for countSuccessful, countNotsuccessful in error.items():
                    if countNotsuccessful > 0:
                        self.assertionUnsuccessful = True
                        self.status = u"unsuccessful"
            else:   # error code results
                self.results.append(error)
                self.status = u"fail" # error code
        self.results.sort()
    
    def objectId(self,refId=u""):
        u"""Returns a string surrogate representing the object index of the model document, 
        prepended by the refId string.
        :param refId: A string to prefix the refId for uniqueless (such as to use in tags for tkinter)
        :type refId: str
        """
        return u"_{0}_{1}".format(refId, self.objectIndex)


def secCorrespondenceLoader(modelXbrl, mappedUri, filepath, **kwargs):
    if (mappedUri.startswith(u"http://www.sec.gov/Archives/edgar/Feed/") and 
        mappedUri.endswith(u".nc.tar.gz")):
        
        # daily feed loader (the rss object)
        rssObject = ModelRssObject(modelXbrl, uri=mappedUri, filepath=filepath)
        
        # location for expanded feed files
        tempdir = os.path.join(modelXbrl.modelManager.cntlr.userAppDir, u"tmp", u"edgarFeed")
        
        # remove prior files
        if os.path.exists(tempdir):
            os.system(u"rm -fr {}".format(tempdir)) # rmtree does not work with this many files!
        os.makedirs(tempdir, exist_ok=True)
        # untar to /temp/arelle/edgarFeed for faster operation
        startedAt = time.time()
        modelXbrl.fileSource.open()
        modelXbrl.fileSource.fs.extractall(tempdir)
        modelXbrl.info(u"info", u"untar edgarFeed temp files in %.2f sec" % (time.time() - startedAt), 
                       modelObject=modelXbrl)
            
        # find <table> with <a>Download in it
        for instanceFile in sorted(os.listdir(tempdir)): # modelXbrl.fileSource.dir:
            if instanceFile != u".":
                rssObject.rssItems.append(
                    SECCorrespondenceItem(modelXbrl, instanceFile, mappedUri + u'/' + instanceFile))
        return rssObject
    elif u"rssItem" in kwargs and u".nc.tar.gz/" in mappedUri:
        rssItem = kwargs[u"rssItem"]
        text = None # no instance information
        # parse document
        try:
            startedAt = time.time()
            file, encoding = modelXbrl.fileSource.file(
               os.path.join(modelXbrl.modelManager.cntlr.userAppDir, u"tmp", u"edgarFeed", 
                            os.path.basename(rssItem.url)))
            s = file.read()
            file.close()
            for match in re.finditer(ur"[<]([^>]+)[>]([^<\n\r]*)", s, re.MULTILINE):
                tag = match.group(1).lower()
                v = match.group(2)
                if tag == u"accession-number":
                    rssItem.accessionNumber = v
                elif tag == u"form-type":
                    rssItem.formType = v
                    if v != u"UPLOAD":
                        rssItem.doNotProcessRSSitem = True # skip this RSS item in validate loop, don't load DB
                elif tag == u"filing-date":
                    try:
                        rssItem.filingDate = datetime.date(int(v[0:4]), int(v[4:6]), int(v[6:8]))
                    except (ValueError, IndexError):
                        pass
                elif tag == u"conformed-name":
                    rssItem.companyName = v
                elif tag == u"cik":
                    rssItem.cikNumber = v
                elif tag == u"assigned-sic":
                    rssItem.assignedSic = v
                elif tag == u"fiscal-year-end":
                    try: 
                        rssItem.fiscalYearEnd = v[0:2] + u'-' + v[2:4]
                    except (IndexError, TypeError):
                        pass 
            match = re.search(u"<PDF>(.*)</PDF>", s, re.DOTALL)
            if match:
                import uu, io
                pageText = []
                uuIn = io.BytesIO(match.group(1).encode(encoding))
                uuOut = io.BytesIO()
                uu.decode(uuIn, uuOut)
                from pyPdf import PdfFileReader
                uuOut.seek(0,0)
                try:
                    pdfIn = PdfFileReader(uuOut)
                    for pageNum in xrange(pdfIn.getNumPages()):
                        pageText.append(pdfIn.getPage(pageNum).extractText())
                except:
                    # do we want a warning here that the PDF can't be read with this library?
                    pass
                uuIn.close()
                uuOut.close()
                text = u''.join(pageText)
            else:
                match = re.search(u"<TEXT>(.*)</TEXT>", s, re.DOTALL)
                if match:
                    text = match.group(1)
        except (IOError, EnvironmentError):
            pass # give up, no instance
        # daily rss item loader, provide unpopulated instance document to be filled in by RssItem.Xbrl.Loaded
        if not text:
            rssItem.doNotProcessRSSitem = True # skip this RSS item in validate loop, don't load DB
            instDoc = ModelDocument.create(modelXbrl, 
                                           ModelDocument.Type.UnknownXML,
                                           rssItem.url,
                                           isEntry=True,
                                           base=u'', # block pathname from becomming absolute
                                           initialXml=u'<DummyXml/>')
        else:
            instDoc = ModelDocument.create(modelXbrl, 
                                           ModelDocument.Type.INSTANCE,
                                           rssItem.url,
                                           isEntry=True,
                                           base=u'', # block pathname from becomming absolute
                                           initialXml=u'''
<xbrli:xbrl xmlns:doc="http://arelle.org/doc/2014-01-31" 
    xmlns:link="http://www.xbrl.org/2003/linkbase" 
    xmlns:xlink="http://www.w3.org/1999/xlink" 
    xmlns:xbrli="http://www.xbrl.org/2003/instance">
    <link:schemaRef xlink:type="simple" xlink:href="http://arelle.org/2014/doc-2014-01-31.xsd"/>
   <xbrli:context id="pubDate">
      <xbrli:entity>
         <xbrli:identifier scheme="http://www.sec.gov/CIK">{cik}</xbrli:identifier>
      </xbrli:entity>
      <xbrli:period>
         <xbrli:instant>{pubDate}</xbrli:instant>
      </xbrli:period>
    </xbrli:context>
    <doc:Correspondence contextRef="pubDate">{text}</doc:Correspondence>
</xbrli:xbrl>
            '''.format(cik=rssItem.cikNumber,
                       pubDate=rssItem.pubDate.date(),
                       text=text.strip().replace(u"&",u"&amp;").replace(u"<",u"&lt;")))
            #modelXbrl.info("info", "loaded in %.2f sec" % (time.time() - startedAt),
            #               modelDocument=instDoc)
        return instDoc

    return None

def secCorrespondenceCloser(modelDocument):
    if (modelDocument.uri.startswith(u"http://www.sec.gov/Archives/edgar/Feed/") and 
        modelDocument.uri.endswith(u".nc.tar.gz")):
        # remove prior files
        if os.path.exists(u"/tmp/arelle/edgarFeed"):
            os.system(u"rm -fr /tmp/arelle/edgarFeed")
        


__pluginInfo__ = {  
    u'name': u'SEC Correspondence Loader',
    u'version': u'0.9',
    u'description': u"This plug-in loads SEC Correspondence.  ",
    u'license': u'Apache-2',
    u'author': u'Mark V Systems Limited',
    u'copyright': u'(c) Copyright 2014 Mark V Systems Limited, All rights reserved. \n'
                 u'PyPDF (c) Copyright 2012 Jeet Sukumaran',
    # classes of mount points (required)
    u'ModelDocument.PullLoader': secCorrespondenceLoader,
    u'ModelDocument.CustomCloser': secCorrespondenceCloser,
}
