u'''
Created on Apr 5, 2013

@author: Mark V Systems Limited
(c) Copyright 2013 Mark V Systems Limited, All rights reserved.
'''
from arelle import ModelDocument, ViewFile
import os

def viewRssFeed(modelXbrl, outfile, cols):
    modelXbrl.modelManager.showStatus(_(u"viewing RSS feed"))
    view = ViewRssFeed(modelXbrl, outfile, cols)
    view.viewRssFeed(modelXbrl.modelDocument)
    view.close()
    
class ViewRssFeed(ViewFile.View):
    def __init__(self, modelXbrl, outfile, cols):
        super(ViewRssFeed, self).__init__(modelXbrl, outfile, u"RSS Feed")
        self.cols = cols
        
    def viewRssFeed(self, modelDocument):
        if self.cols:
            if isinstance(self.cols,unicode): self.cols = self.cols.replace(u',').split()
            unrecognizedCols = []
            for col in self.cols:
                if col not in (u"Company Name", u"Accession Number", u"Form", u"Filing Date", u"CIK", u"Status", u"Period", u"Yr End", u"Results"):
                    unrecognizedCols.append(col)
            if unrecognizedCols:
                self.modelXbrl.error(u"arelle:unrecognizedRssReportColumn",
                                     _(u"Unrecognized columns: %(cols)s"),
                                     modelXbrl=self.modelXbrl, cols=u','.join(unrecognizedCols))
        else:
            self.cols = [u"Company Name", u"Accession Number", u"Form", u"Filing Date", u"CIK", u"Status", u"Period", u"Yr End", u"Results"]
        self.addRow(self.cols, asHeader=True)

        if modelDocument.type == ModelDocument.Type.RSSFEED:
            for rssItem in modelDocument.rssItems:
                cols = []
                for col in self.cols:
                    if col == u"Company Name":
                        cols.append(rssItem.companyName)
                    elif col == u"Accession Number":
                        cols.append(rssItem.accessionNumber)
                    elif col == u"Form":
                        cols.append(rssItem.formType)
                    elif col == u"Filing Date":
                        cols.append(rssItem.filingDate)
                    elif col == u"CIK":
                        cols.append(rssItem.cikNumber)
                    elif col == u"Status":
                        cols.append(rssItem.status)
                    elif col == u"Period":
                        cols.append(rssItem.period)
                    elif col == u"Yr End":
                        cols.append(rssItem.fiscalYearEnd)
                    elif col == u"Results":
                        cols.append(u" ".join(unicode(result) for result in (rssItem.results or [])) +
                                    ((u" " + unicode(rssItem.assertions)) if rssItem.assertions else u""))
                    else:
                        cols.append(u"")
                self.addRow(cols, xmlRowElementName=u"rssItem")
