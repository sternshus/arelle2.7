u'''
Created on Nov 11, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
import os
from arelle import XmlUtil
from arelle.ModelObject import ModelObject

edgr = u"http://www.sec.gov/Archives/edgar"
edgrDescription = u"{http://www.sec.gov/Archives/edgar}description"
edgrFile = u"{http://www.sec.gov/Archives/edgar}file"
edgrSequence = u"{http://www.sec.gov/Archives/edgar}sequence"
edgrType = u"{http://www.sec.gov/Archives/edgar}type"
edgrUrl = u"{http://www.sec.gov/Archives/edgar}url"

newRssWatchOptions = {
    u"feedSource": u"",
    u"feedSourceUri": None,
    u"matchTextExpr": u"",
    u"formulaFileUri": u"",
    u"logFileUri": u"",
    u"emailAddress": u"",
    u"validateXbrlRules": False,
    u"validateDisclosureSystemRules": False,
    u"validateCalcLinkbase": False,
    u"validateFormulaAssertions": False,
    u"alertMatchedFactText": False,
    u"alertAssertionUnsuccessful": False,
    u"alertValiditionError": False,
    u"latestPubDate": None,
}
        
        # Note: if adding to this list keep DialogRssWatch in sync
class ModelRssItem(ModelObject):
    def init(self, modelDocument):
        super(ModelRssItem, self).init(modelDocument)
        try:
            if (self.modelXbrl.modelManager.rssWatchOptions.latestPubDate and 
                self.pubDate <= self.modelXbrl.modelManager.rssWatchOptions.latestPubDate):
                self.status = _(u"tested")
            else:
                self.status = _(u"not tested")
        except AttributeError:
            self.status = _(u"not tested")
        self.results = None
        self.assertions = None
        
    @property
    def cikNumber(self):
        return XmlUtil.text(XmlUtil.descendant(self, edgr, u"cikNumber"))
    
    @property
    def accessionNumber(self):
        return XmlUtil.text(XmlUtil.descendant(self, edgr, u"accessionNumber"))
    
    @property
    def fileNumber(self):
        return XmlUtil.text(XmlUtil.descendant(self, edgr, u"fileNumber"))
    
    @property
    def companyName(self):
        return XmlUtil.text(XmlUtil.descendant(self, edgr, u"companyName"))
    
    @property
    def formType(self):
        return XmlUtil.text(XmlUtil.descendant(self, edgr, u"formType"))
    
    @property
    def pubDate(self):
        try:
            return self._pubDate
        except AttributeError:
            from arelle.UrlUtil import parseRfcDatetime
            self._pubDate = parseRfcDatetime(XmlUtil.text(XmlUtil.descendant(self, None, u"pubDate")))
            return self._pubDate
    @property
    def filingDate(self):
        try:
            return self._filingDate
        except AttributeError:
            import datetime
            self._filingDate = None
            date = XmlUtil.text(XmlUtil.descendant(self, edgr, u"filingDate"))
            d = date.split(u"/") 
            if d and len(d) == 3:
                self._filingDate = datetime.date(_INT(d[2]),_INT(d[0]),_INT(d[1]))
            return self._filingDate
    
    @property
    def period(self):
        per = XmlUtil.text(XmlUtil.descendant(self, edgr, u"period"))
        if per and len(per) == 8:
            return u"{0}-{1}-{2}".format(per[0:4],per[4:6],per[6:8])
        return None
    
    @property
    def assignedSic(self):
        return XmlUtil.text(XmlUtil.descendant(self, edgr, u"assignedSic"))
    
    @property
    def acceptanceDatetime(self):
        try:
            return self._acceptanceDatetime
        except AttributeError:
            import datetime
            self._acceptanceDatetime = None
            date = XmlUtil.text(XmlUtil.descendant(self, edgr, u"acceptanceDatetime"))
            if date and len(date) == 14:
                self._acceptanceDatetime = datetime.datetime(_INT(date[0:4]),_INT(date[4:6]),_INT(date[6:8]),_INT(date[8:10]),_INT(date[10:12]),_INT(date[12:14]))
            return self._acceptanceDatetime
    
    @property
    def fiscalYearEnd(self):
        yrEnd = XmlUtil.text(XmlUtil.descendant(self, edgr, u"fiscalYearEnd"))
        if yrEnd and len(yrEnd) == 4:
            return u"{0}-{1}".format(yrEnd[0:2],yrEnd[2:4])
        return None
    
    @property
    def htmlUrl(self):  # main filing document
        htmlDocElt = XmlUtil.descendant(self, edgr, u"xbrlFile", attrName=edgrSequence, attrValue=u"1")
        if htmlDocElt is not None:
            return htmlDocElt.get(edgrUrl)
        return None

    @property
    def url(self):
        try:
            return self._url
        except AttributeError:
            self._url = None
            for instDocElt in XmlUtil.descendants(self, edgr, u"xbrlFile"):
                if instDocElt.get(edgrType).endswith(u".INS"):
                    self._url = instDocElt.get(edgrUrl)
                    break
            return self._url
        
    @property
    def zippedUrl(self):
        enclosure = XmlUtil.childAttr(self, None, u"enclosure", u"url")
        if enclosure:
            # modify url to use zip file
            path, sep, file = self.url.rpartition(u"/")
            # return path + sep + self.accessionNumber + "-xbrl.zip" + sep + file
            return enclosure + sep + file
        else: # no zipped enclosure, just use unzipped file
            return self.url
        
        
    @property
    def htmURLs(self):
        try:
            return self._htmURLs
        except AttributeError:
            self._htmURLs = [
                (instDocElt.get(edgrDescription),instDocElt.get(edgrUrl))
                  for instDocElt in XmlUtil.descendants(self, edgr, u"xbrlFile")
                    if instDocElt.get(edgrFile).endswith(u".htm")]
            return self._htmURLs
        
    @property
    def primaryDocumentURL(self):
        try:
            return self._primaryDocumentURL
        except AttributeError:
            formType = self.formType
            self._primaryDocumentURL = None
            for instDocElt in XmlUtil.descendants(self, edgr, u"xbrlFile"):
                if instDocElt.get(edgrType) == formType:
                    self._primaryDocumentURL = instDocElt.get(edgrUrl)
                    break
            return self._primaryDocumentURL
        
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
    
    @property
    def propertyView(self):
        return ((u"CIK", self.cikNumber),
                (u"company", self.companyName),
                (u"published", self.pubDate),
                (u"form type", self.formType),
                (u"filing date", self.filingDate),
                (u"period", self.period),
                (u"year end", self.fiscalYearEnd),
                (u"status", self.status),
                (u"instance", os.path.basename(self.url)),
                )
    def __repr__(self):
        return (u"rssItem[{0}]{1})".format(self.objectId(),self.propertyView))

