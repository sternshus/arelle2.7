u'''
Created on Oct 9, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
import csv, io, json, re, sys
from lxml import etree
from arelle.FileSource import FileNamedStringIO
from io import open
if sys.version[0] >= u'3':
    csvOpenMode = u'w'
    csvOpenNewline = u''
else:
    csvOpenMode = u'wb' # for 2.7
    csvOpenNewline = None

CSV = 0
HTML = 1
XML = 2
JSON = 3
TYPENAMES = [u"CSV", u"HTML", u"XML", u"JSON"]
nonNameCharPattern =  re.compile(ur"[^\w\-\.:]")

class View(object):
    # note that cssExtras override any css entries provided by this module if they have the same name
    def __init__(self, modelXbrl, outfile, rootElementName, lang=None, style=u"table", cssExtras=u""):
        self.modelXbrl = modelXbrl
        self.lang = lang
        if isinstance(outfile, FileNamedStringIO):
            if outfile.fileName in (u"html", u"xhtml"):
                self.type = HTML
            elif outfile.fileName == u"csv":
                self.type = CSV
            elif outfile.fileName == u"json":
                self.type = JSON
            else:
                self.type = XML
        elif outfile.endswith(u".html") or outfile.endswith(u".htm") or outfile.endswith(u".xhtml"):
            self.type = HTML
        elif outfile.endswith(u".xml"):
            self.type = XML
        elif outfile.endswith(u".json"):
            self.type = JSON
        else:
            self.type = CSV
        self.outfile = outfile
        if style == u"rendering": # for rendering, preserve root element name
            self.rootElementName = rootElementName
        else: # root element is formed from words in title or description
            self.rootElementName = rootElementName[0].lower() + nonNameCharPattern.sub(u"", rootElementName.title())[1:]
        self.numHdrCols = 0
        self.treeCols = 0  # set to number of tree columns for auto-tree-columns
        if modelXbrl:
            if not lang: 
                self.lang = modelXbrl.modelManager.defaultLang
        if self.type == CSV:
            if isinstance(self.outfile, FileNamedStringIO):
                self.csvFile = self.outfile
            else:
                # note: BOM signature required for Excel to open properly with characters > 0x7f 
                self.csvFile = open(outfile, csvOpenMode, newline=csvOpenNewline, encoding=u'utf-8-sig')
            self.csvWriter = csv.writer(self.csvFile, dialect=u"excel")
        elif self.type == HTML:
            if style == u"rendering":
                html = io.StringIO(
u'''
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="content-type" content="text/html;charset=utf-8" />
        <STYLE type="text/css"> 
            table {font-family:Arial,sans-serif;vertical-align:middle;white-space:normal;}
            th {background:#eee;}
            td {} 
            .tableHdr{border-top:.5pt solid windowtext;border-right:none;border-bottom:none;border-left:.5pt solid windowtext;}
            .zAxisHdr{border-top:.5pt solid windowtext;border-right:.5pt solid windowtext;border-bottom:none;border-left:.5pt solid windowtext;}
            .xAxisSpanLeg,.yAxisSpanLeg,.yAxisSpanArm{border-top:none;border-right:none;border-bottom:none;border-left:.5pt solid windowtext;}
            .xAxisHdrValue{border-top:.5pt solid windowtext;border-right:none;border-bottom:none;border-left:1.0pt solid windowtext;}
            .xAxisHdr{border-top:.5pt solid windowtext;border-right:none;border-bottom:none;border-left:.5pt solid windowtext;} 
            .yAxisHdrWithLeg{vertical-align:middle;border-top:.5pt solid windowtext;border-right:none;border-bottom:none;border-left:.5pt solid windowtext;}
            .yAxisHdrWithChildrenFirst{border-top:none;border-right:none;border-bottom:.5pt solid windowtext;border-left:.5pt solid windowtext;}
            .yAxisHdrAbstract{border-top:.5pt solid windowtext;border-right:none;border-bottom:none;border-left:.5pt solid windowtext;}
            .yAxisHdrAbstractChildrenFirst{border-top:none;border-right:none;border-bottom:.5pt solid windowtext;border-left:.5pt solid windowtext;}
            .yAxisHdr{border-top:.5pt solid windowtext;border-right:none;border-bottom:none;border-left:.5pt solid windowtext;}
            .cell{border-top:1.0pt solid windowtext;border-right:.5pt solid windowtext;border-bottom:.5pt solid windowtext;border-left:.5pt solid windowtext;}
            .abstractCell{border-top:1.0pt solid windowtext;border-right:.5pt solid windowtext;border-bottom:.5pt solid windowtext;border-left:.5pt solid windowtext;background:#e8e8e8;}
            .blockedCell{border-top:1.0pt solid windowtext;border-right:.5pt solid windowtext;border-bottom:.5pt solid windowtext;border-left:.5pt solid windowtext;background:#eee;}
            .tblCell{border-top:.5pt solid windowtext;border-right:.5pt solid windowtext;border-bottom:.5pt solid windowtext;border-left:.5pt solid windowtext;}
            ''' + cssExtras + u'''
        </STYLE>
    </head>
    <body>
        <table border="1" cellspacing="0" cellpadding="4" style="font-size:8pt;">
        </table>
    </body>
</html>
'''
                )
            else:
                html = io.StringIO(
u'''
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="content-type" content="text/html;charset=utf-8" />
        <STYLE type="text/css"> 
            table {font-family:Arial,sans-serif;vertical-align:middle;white-space:normal;
                    border-top:.5pt solid windowtext;border-right:1.5pt solid windowtext;border-bottom:1.5pt solid windowtext;border-left:.5pt solid windowtext;}
            th {background:#eee;}
            td {} 
            .tableHdr{border-top:.5pt solid windowtext;border-right:none;border-bottom:.5pt solid windowtext;border-left:.5pt solid windowtext;}
            .rowSpanLeg{width:1.0em;border-top:none;border-right:none;border-bottom:none;border-left:.5pt solid windowtext;}
            .tableCell{border-top:.5pt solid windowtext;border-right:none;border-bottom:none;border-left:.5pt solid windowtext;}
            .tblCell{border-top:.5pt solid windowtext;border-right:none;border-bottom:.5pt solid windowtext;border-left:.5pt solid windowtext;}
        </STYLE>
    </head>
    <body>
        <table cellspacing="0" cellpadding="4" style="font-size:8pt;">
        </table>
    </body>
</html>
'''
                )
            self.xmlDoc = etree.parse(html)
            html.close()
            self.tblElt = None
            for self.tblElt in self.xmlDoc.iter(tag=u"{http://www.w3.org/1999/xhtml}table"):
                break
        elif self.type == XML:
            html = io.StringIO(u"<{0}/>".format(self.rootElementName))
            self.xmlDoc = etree.parse(html)
            html.close()
            self.docEltLevels = [self.xmlDoc.getroot()]
            self.tblElt = self.docEltLevels[0]
        elif self.type == JSON:
            self.entries = []
            self.entryLevels = [self.entries]
            self.jsonObject = {self.rootElementName: self.entries}
        
    def addRow(self, cols, asHeader=False, treeIndent=0, colSpan=1, xmlRowElementName=None, xmlRowEltAttr=None, xmlRowText=None, xmlCol0skipElt=False, xmlColElementNames=None, lastColSpan=None):
        if asHeader and len(cols) > self.numHdrCols:
            self.numHdrCols = len(cols)
        if self.type == CSV:
            self.csvWriter.writerow(cols if not self.treeCols else
                                    ([None for i in xrange(treeIndent)] +
                                     cols[0:1] + 
                                     [None for i in xrange(treeIndent, self.treeCols - 1)] +
                                     cols[1:]))
        elif self.type == HTML:
            tr = etree.SubElement(self.tblElt, u"{http://www.w3.org/1999/xhtml}tr")
            td = None
            for i, col in enumerate(cols + [None for emptyCol in xrange(self.numHdrCols - colSpan + 1 - len(cols))]):
                attrib = {}
                if asHeader:
                    attrib[u"class"] = u"tableHdr"
                    colEltTag = u"{http://www.w3.org/1999/xhtml}th"
                else:
                    colEltTag = u"{http://www.w3.org/1999/xhtml}td"
                    attrib[u"class"] = u"tableCell"
                if i == 0:
                    if self.treeCols - 1 > treeIndent:
                        attrib[u"colspan"] = unicode(self.treeCols - treeIndent + colSpan - 1)
                    elif colSpan > 1:
                        attrib[u"colspan"] = unicode(colSpan)
                if i == 0 and self.treeCols:
                    for indent in xrange(treeIndent):
                        etree.SubElement(tr, colEltTag,
                                         attrib={u"class":u"rowSpanLeg"},
                                         ).text = u'\u00A0'  # produces &nbsp;
                td = etree.SubElement(tr, colEltTag, attrib=attrib)
                td.text = unicode(col) if col else u'\u00A0'  # produces &nbsp;
            if lastColSpan and td is not None:
                td.set(u"colspan", unicode(lastColSpan))
        elif self.type == XML:
            if asHeader:
                # save column element names
                self.xmlRowElementName = xmlRowElementName or u"row"
                self.columnEltNames = [col[0].lower() + nonNameCharPattern.sub(u'', col[1:])
                                       for col in cols]
            else:
                if treeIndent < len(self.docEltLevels) and self.docEltLevels[treeIndent] is not None:
                    parentElt = self.docEltLevels[treeIndent]
                else:
                    # problem, error message? unexpected indent
                    parentElt = self.docEltLevels[0] 
                # escape attributes content
                escapedRowEltAttr = dict(((k, v.replace(u"&",u"&amp;").replace(u"<",u"&lt;"))
                                          for k,v in xmlRowEltAttr.items())
                                         if xmlRowEltAttr else ())
                rowElt = etree.SubElement(parentElt, xmlRowElementName or self.xmlRowElementName, attrib=escapedRowEltAttr)
                if treeIndent + 1 >= len(self.docEltLevels): # extend levels as needed
                    for extraColIndex in xrange(len(self.docEltLevels) - 1, treeIndent + 1):
                        self.docEltLevels.append(None)
                self.docEltLevels[treeIndent + 1] = rowElt
                if not xmlColElementNames: xmlColElementNames = self.columnEltNames
                if len(cols) == 1 and not xmlCol0skipElt:
                    rowElt.text = xmlRowText if xmlRowText else cols[0]
                else:
                    isDimensionName = isDimensionValue = False
                    elementName = u"element" # need a default
                    for i, col in enumerate(cols):
                        if (i != 0 or not xmlCol0skipElt) and col:
                            if i < len(xmlColElementNames):
                                elementName = xmlColElementNames[i]
                                if elementName == u"dimensions":
                                    elementName = u"dimension" # one element per dimension
                                    isDimensionName = True
                            if isDimensionName:
                                isDimensionValue = True
                                isDimensionName = False
                                dimensionName = unicode(col)
                            else:
                                elt = etree.SubElement(rowElt, elementName)
                                elt.text = unicode(col).replace(u"&",u"&amp;").replace(u"<",u"&lt;")
                                if isDimensionValue:
                                    elt.set(u"name", dimensionName)
                                    isDimensionName = True
                                    isDimensionValue = False
        elif self.type == JSON:
            if asHeader:
                # save column element names
                self.xmlRowElementName = xmlRowElementName
                self.columnEltNames = [col[0].lower() + nonNameCharPattern.sub(u'', col[1:])
                                       for col in cols]
            else:
                if treeIndent < len(self.entryLevels) and self.entryLevels[treeIndent] is not None:
                    entries = self.entryLevels[treeIndent]
                else:
                    # problem, error message? unexpected indent
                    entries = self.entryLevels[0] 
                entry = []
                if xmlRowElementName:
                    entry.append(xmlRowElementName)
                elif self.xmlRowElementName:
                    entry.append(self.xmlRowElementName)
                if xmlRowEltAttr:
                    entry.append(xmlRowEltAttr)
                else:
                    entry.append({})
                entries.append(entry)
                if treeIndent + 1 >= len(self.entryLevels): # extend levels as needed
                    for extraColIndex in xrange(len(self.entryLevels) - 1, treeIndent + 1):
                        self.entryLevels.append(None)
                self.entryLevels[treeIndent + 1] = entry
                if not xmlColElementNames: xmlColElementNames = self.columnEltNames
                if len(cols) == 1 and not xmlCol0skipElt:
                    entry.append(xmlRowText if xmlRowText else cols[0])
                else:
                    content = {}
                    entry.append(content)
                    for i, col in enumerate(cols):
                        if (i != 0 or not xmlCol0skipElt) and col and i < len(xmlColElementNames):
                                elementName = xmlColElementNames[i]
                                if elementName == u"dimensions":
                                    value = dict((unicode(cols[i]),unicode(cols[i+1])) for i in xrange(i, len(cols), 2))
                                else:
                                    value = unicode(col)
                                content[elementName] = value
        if asHeader and lastColSpan: 
            self.numHdrCols += lastColSpan - 1
                                
    def close(self, noWrite=False):
        if self.type == CSV:
            if not isinstance(self.outfile, FileNamedStringIO):
                self.csvFile.close()
        elif not noWrite:
            fileType = TYPENAMES[self.type]
            try:
                from arelle import XmlUtil
                if isinstance(self.outfile, FileNamedStringIO):
                    fh = self.outfile
                else:
                    fh = open(self.outfile, u"w", encoding=u"utf-8")
                if self.type == JSON:
                    fh.write(json.dumps(self.jsonObject, ensure_ascii=False))
                else:
                    XmlUtil.writexml(fh, self.xmlDoc, encoding=u"utf-8",
                                     xmlcharrefreplace= (self.type == HTML) )
                if not isinstance(self.outfile, FileNamedStringIO):
                    fh.close()
                self.modelXbrl.info(u"info", _(u"Saved output %(type)s to %(file)s"), file=self.outfile, type=fileType)
            except (IOError, EnvironmentError), err:
                self.modelXbrl.exception(u"arelle:htmlIOError", _(u"Failed to save output %(type)s to %(file)s: \s%(error)s"), file=self.outfile, type=fileType, error=err)
        self.modelXbrl = None
        if self.type == HTML:
            self.tblElt = None
        elif self.type == XML:
            self.docEltLevels = None
        self.__dict__.clear() # dereference everything after closing document

