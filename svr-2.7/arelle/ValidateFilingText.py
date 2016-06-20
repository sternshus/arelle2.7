u'''
Created on Oct 17, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
#import xml.sax, xml.sax.handler
from __future__ import with_statement
from lxml.etree import XML, DTD, SubElement, XMLSyntaxError
import os, re, io
from arelle import XbrlConst
from arelle.ModelObject import ModelObject
from io import open

XMLdeclaration = re.compile(ur"<\?xml.*\?>", re.DOTALL)
XMLpattern = re.compile(ur".*(<|&lt;|&#x3C;|&#60;)[A-Za-z_]+[A-Za-z0-9_:]*[^>]*(/>|>|&gt;|/&gt;).*", re.DOTALL)
CDATApattern = re.compile(ur"<!\[CDATA\[(.+)\]\]")
#EFM table 5-1 and all &xxx; patterns
docCheckPattern = re.compile(ur"&\w+;|[^0-9A-Za-z`~!@#$%&\*\(\)\.\-+ \[\]\{\}\|\\:;\"'<>,_?/=\t\n\r\m\f]") # won't match &#nnn;
namedEntityPattern = re.compile(u"&[_A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]"
                                ur"[_\-\.:" 
                                u"\xB7A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\u0300-\u036F\u203F-\u2040]*;")
#entityPattern = re.compile("&#[0-9]+;|"  
#                           "&#x[0-9a-fA-F]+;|" 
#                           "&[_A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]"
#                                r"[_\-\.:" 
#                                "\xB7A-Za-z0-9\xC0-\xD6\xD8-\xF6\xF8-\xFF\u0100-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\u0300-\u036F\u203F-\u2040]*;")


edbodyDTD = None

u''' replace with lxml DTD validation
bodyTags = {
    'a': (),
    'address': (),
    'b': (),
    'big': (),
    'blockquote': (),
    'br': (),
    'caption': (),
    'center': (),
    'cite': (),
    'code': (),
    'dd': (),
    'dfn': (),
    'dir': (),
    'div': (),
    'dl': (),
    'dt': (),
    'em': (),
    'font': (),
    'h1': (),
    'h2': (),
    'h3': (),
    'h4': (),
    'h5': (),
    'h6': (),
    'hr': (),
    'i': (),
    'img': (),
    'kbd': (),
    'li': (),
    'listing': (),
    'menu': (),
    'ol': (),
    'p': (),
    'plaintext': (),
    'pre': (),
    'samp': (),
    'small': (),
    'strike': (),
    'strong': (),
    'sub': (),
    'sup': (),
    'table': (),
    'td': (),
    'th': (),
    'tr': (),
    'tt': (),
    'u': (),
    'ul': (),
    'var': (),
    'xmp': ()
    }

htmlAttributes = {
    'align': ('h1','h2','h3','h4','h5','h6','hr', 'img', 'p','caption','div','table','td','th','tr'),
    'alink': ('body'),
    'alt': ('img'),
    'bgcolor': ('body','table', 'tr', 'th', 'td'),
    'border': ('table', 'img'),
    'cellpadding': ('table'),
    'cellspacing': ('table'),
    'class': ('*'),
    'clear': ('br'),
    'color': ('font'),
    'colspan': ('td','th'),
    'compact': ('dir','dl','menu','ol','ul'),
    'content': ('meta'),
    'dir': ('h1','h2','h3','h4','h5','h6','hr','p','img','caption','div','table','td','th','tr','font',
            'center','ol','li','ul','bl','a','big','pre','dir','address','blockqoute','menu','blockquote',
              'em', 'strong', 'dfn', 'code', 'samp', 'kbd', 'var', 'cite', 'sub', 'sup', 'tt', 'i', 'b', 'small', 'u', 'strike'),
    'lang': ('h1','h2','h3','h4','h5','h6','hr','p','img','caption','div','table','td','th','tr','font',
            'center','ol','li','ul','bl','a','big','pre','dir','address','blockqoute','menu','blockquote',
              'em', 'strong', 'dfn', 'code', 'samp', 'kbd', 'var', 'cite', 'sub', 'sup', 'tt', 'i', 'b', 'small', 'u', 'strike'),
    'height': ('td','th', 'img'),
    'href': ('a'),
    'id': ('*'),
    'link': ('body'),
    'name': ('meta','a', 'img'),
    'noshade': ('hr'),
    'nowrap': ('td','th'),
    'prompt': ('isindex'),
    'rel': ('link','a'),
    'rev': ('link','a'),
    'rowspan': ('td','th'),
    'size': ('hr','font'),
    'src': ('img'),
    'start': ('ol'),
    'style': ('*'),
    'text': ('body'),
    'title': ('*'),
    'type': ('li','ol','ul'),
    'valign': ('td','th','tr'),
    'vlink': ('body'),
    'width': ('hr','pre', 'table','td','th', 'img')
    }
'''

xhtmlEntities = {
    u'&nbsp;': u'&#160;',
    u'&iexcl;': u'&#161;',
    u'&cent;': u'&#162;',
    u'&pound;': u'&#163;',
    u'&curren;': u'&#164;',
    u'&yen;': u'&#165;',
    u'&brvbar;': u'&#166;',
    u'&sect;': u'&#167;',
    u'&uml;': u'&#168;',
    u'&copy;': u'&#169;',
    u'&ordf;': u'&#170;',
    u'&laquo;': u'&#171;',
    u'&not;': u'&#172;',
    u'&shy;': u'&#173;',
    u'&reg;': u'&#174;',
    u'&macr;': u'&#175;',
    u'&deg;': u'&#176;',
    u'&plusmn;': u'&#177;',
    u'&sup2;': u'&#178;',
    u'&sup3;': u'&#179;',
    u'&acute;': u'&#180;',
    u'&micro;': u'&#181;',
    u'&para;': u'&#182;',
    u'&middot;': u'&#183;',
    u'&cedil;': u'&#184;',
    u'&sup1;': u'&#185;',
    u'&ordm;': u'&#186;',
    u'&raquo;': u'&#187;',
    u'&frac14;': u'&#188;',
    u'&frac12;': u'&#189;',
    u'&frac34;': u'&#190;',
    u'&iquest;': u'&#191;',
    u'&Agrave;': u'&#192;',
    u'&Aacute;': u'&#193;',
    u'&Acirc;': u'&#194;',
    u'&Atilde;': u'&#195;',
    u'&Auml;': u'&#196;',
    u'&Aring;': u'&#197;',
    u'&AElig;': u'&#198;',
    u'&Ccedil;': u'&#199;',
    u'&Egrave;': u'&#200;',
    u'&Eacute;': u'&#201;',
    u'&Ecirc;': u'&#202;',
    u'&Euml;': u'&#203;',
    u'&Igrave;': u'&#204;',
    u'&Iacute;': u'&#205;',
    u'&Icirc;': u'&#206;',
    u'&Iuml;': u'&#207;',
    u'&ETH;': u'&#208;',
    u'&Ntilde;': u'&#209;',
    u'&Ograve;': u'&#210;',
    u'&Oacute;': u'&#211;',
    u'&Ocirc;': u'&#212;',
    u'&Otilde;': u'&#213;',
    u'&Ouml;': u'&#214;',
    u'&times;': u'&#215;',
    u'&Oslash;': u'&#216;',
    u'&Ugrave;': u'&#217;',
    u'&Uacute;': u'&#218;',
    u'&Ucirc;': u'&#219;',
    u'&Uuml;': u'&#220;',
    u'&Yacute;': u'&#221;',
    u'&THORN;': u'&#222;',
    u'&szlig;': u'&#223;',
    u'&agrave;': u'&#224;',
    u'&aacute;': u'&#225;',
    u'&acirc;': u'&#226;',
    u'&atilde;': u'&#227;',
    u'&auml;': u'&#228;',
    u'&aring;': u'&#229;',
    u'&aelig;': u'&#230;',
    u'&ccedil;': u'&#231;',
    u'&egrave;': u'&#232;',
    u'&eacute;': u'&#233;',
    u'&ecirc;': u'&#234;',
    u'&euml;': u'&#235;',
    u'&igrave;': u'&#236;',
    u'&iacute;': u'&#237;',
    u'&icirc;': u'&#238;',
    u'&iuml;': u'&#239;',
    u'&eth;': u'&#240;',
    u'&ntilde;': u'&#241;',
    u'&ograve;': u'&#242;',
    u'&oacute;': u'&#243;',
    u'&ocirc;': u'&#244;',
    u'&otilde;': u'&#245;',
    u'&ouml;': u'&#246;',
    u'&divide;': u'&#247;',
    u'&oslash;': u'&#248;',
    u'&ugrave;': u'&#249;',
    u'&uacute;': u'&#250;',
    u'&ucirc;': u'&#251;',
    u'&uuml;': u'&#252;',
    u'&yacute;': u'&#253;',
    u'&thorn;': u'&#254;',
    u'&yuml;': u'&#255;',
    u'&quot;': u'&#34;',
    u'&amp;': u'&#38;#38;',
    u'&lt;': u'&#38;#60;',
    u'&gt;': u'&#62;',
    u'&apos;': u'&#39;',
    u'&OElig;': u'&#338;',
    u'&oelig;': u'&#339;',
    u'&Scaron;': u'&#352;',
    u'&scaron;': u'&#353;',
    u'&Yuml;': u'&#376;',
    u'&circ;': u'&#710;',
    u'&tilde;': u'&#732;',
    u'&ensp;': u'&#8194;',
    u'&emsp;': u'&#8195;',
    u'&thinsp;': u'&#8201;',
    u'&zwnj;': u'&#8204;',
    u'&zwj;': u'&#8205;',
    u'&lrm;': u'&#8206;',
    u'&rlm;': u'&#8207;',
    u'&ndash;': u'&#8211;',
    u'&mdash;': u'&#8212;',
    u'&lsquo;': u'&#8216;',
    u'&rsquo;': u'&#8217;',
    u'&sbquo;': u'&#8218;',
    u'&ldquo;': u'&#8220;',
    u'&rdquo;': u'&#8221;',
    u'&bdquo;': u'&#8222;',
    u'&dagger;': u'&#8224;',
    u'&Dagger;': u'&#8225;',
    u'&permil;': u'&#8240;',
    u'&lsaquo;': u'&#8249;',
    u'&rsaquo;': u'&#8250;',
    u'&euro;': u'&#8364;',
    u'&fnof;': u'&#402;',
    u'&Alpha;': u'&#913;',
    u'&Beta;': u'&#914;',
    u'&Gamma;': u'&#915;',
    u'&Delta;': u'&#916;',
    u'&Epsilon;': u'&#917;',
    u'&Zeta;': u'&#918;',
    u'&Eta;': u'&#919;',
    u'&Theta;': u'&#920;',
    u'&Iota;': u'&#921;',
    u'&Kappa;': u'&#922;',
    u'&Lambda;': u'&#923;',
    u'&Mu;': u'&#924;',
    u'&Nu;': u'&#925;',
    u'&Xi;': u'&#926;',
    u'&Omicron;': u'&#927;',
    u'&Pi;': u'&#928;',
    u'&Rho;': u'&#929;',
    u'&Sigma;': u'&#931;',
    u'&Tau;': u'&#932;',
    u'&Upsilon;': u'&#933;',
    u'&Phi;': u'&#934;',
    u'&Chi;': u'&#935;',
    u'&Psi;': u'&#936;',
    u'&Omega;': u'&#937;',
    u'&alpha;': u'&#945;',
    u'&beta;': u'&#946;',
    u'&gamma;': u'&#947;',
    u'&delta;': u'&#948;',
    u'&epsilon;': u'&#949;',
    u'&zeta;': u'&#950;',
    u'&eta;': u'&#951;',
    u'&theta;': u'&#952;',
    u'&iota;': u'&#953;',
    u'&kappa;': u'&#954;',
    u'&lambda;': u'&#955;',
    u'&mu;': u'&#956;',
    u'&nu;': u'&#957;',
    u'&xi;': u'&#958;',
    u'&omicron;': u'&#959;',
    u'&pi;': u'&#960;',
    u'&rho;': u'&#961;',
    u'&sigmaf;': u'&#962;',
    u'&sigma;': u'&#963;',
    u'&tau;': u'&#964;',
    u'&upsilon;': u'&#965;',
    u'&phi;': u'&#966;',
    u'&chi;': u'&#967;',
    u'&psi;': u'&#968;',
    u'&omega;': u'&#969;',
    u'&thetasym;': u'&#977;',
    u'&upsih;': u'&#978;',
    u'&piv;': u'&#982;',
    u'&bull;': u'&#8226;',
    u'&hellip;': u'&#8230;',
    u'&prime;': u'&#8242;',
    u'&Prime;': u'&#8243;',
    u'&oline;': u'&#8254;',
    u'&frasl;': u'&#8260;',
    u'&weierp;': u'&#8472;',
    u'&image;': u'&#8465;',
    u'&real;': u'&#8476;',
    u'&trade;': u'&#8482;',
    u'&alefsym;': u'&#8501;',
    u'&larr;': u'&#8592;',
    u'&uarr;': u'&#8593;',
    u'&rarr;': u'&#8594;',
    u'&darr;': u'&#8595;',
    u'&harr;': u'&#8596;',
    u'&crarr;': u'&#8629;',
    u'&lArr;': u'&#8656;',
    u'&uArr;': u'&#8657;',
    u'&rArr;': u'&#8658;',
    u'&dArr;': u'&#8659;',
    u'&hArr;': u'&#8660;',
    u'&forall;': u'&#8704;',
    u'&part;': u'&#8706;',
    u'&exist;': u'&#8707;',
    u'&empty;': u'&#8709;',
    u'&nabla;': u'&#8711;',
    u'&isin;': u'&#8712;',
    u'&notin;': u'&#8713;',
    u'&ni;': u'&#8715;',
    u'&prod;': u'&#8719;',
    u'&sum;': u'&#8721;',
    u'&minus;': u'&#8722;',
    u'&lowast;': u'&#8727;',
    u'&radic;': u'&#8730;',
    u'&prop;': u'&#8733;',
    u'&infin;': u'&#8734;',
    u'&ang;': u'&#8736;',
    u'&and;': u'&#8743;',
    u'&or;': u'&#8744;',
    u'&cap;': u'&#8745;',
    u'&cup;': u'&#8746;',
    u'&int;': u'&#8747;',
    u'&there;': u'&#8756;',
    u'&sim;': u'&#8764;',
    u'&cong;': u'&#8773;',
    u'&asymp;': u'&#8776;',
    u'&ne;': u'&#8800;',
    u'&equiv;': u'&#8801;',
    u'&le;': u'&#8804;',
    u'&ge;': u'&#8805;',
    u'&sub;': u'&#8834;',
    u'&sup;': u'&#8835;',
    u'&nsub;': u'&#8836;',
    u'&sube;': u'&#8838;',
    u'&supe;': u'&#8839;',
    u'&oplus;': u'&#8853;',
    u'&otimes;': u'&#8855;',
    u'&perp;': u'&#8869;',
    u'&sdot;': u'&#8901;',
    u'&lceil;': u'&#8968;',
    u'&rceil;': u'&#8969;',
    u'&lfloor;': u'&#8970;',
    u'&rfloor;': u'&#8971;',
    u'&lang;': u'&#9001;',
    u'&rang;': u'&#9002;',
    u'&loz;': u'&#9674;',
    u'&spades;': u'&#9824;',
    u'&clubs;': u'&#9827;',
    u'&hearts;': u'&#9829;',
    u'&diams;': u'&#9830;',
    }

def checkfile(modelXbrl, filepath):
    result = []
    lineNum = 1
    foundXmlDeclaration = False
    file, encoding = modelXbrl.fileSource.file(filepath)
    with file as f:
        while True:
            line = f.readline()
            if line == u"":
                break;
            # check for disallowed characters or entity codes
            for match in docCheckPattern.finditer(line):
                text = match.group()
                if text.startswith(u"&"):
                    if not text in xhtmlEntities:
                        modelXbrl.error((u"EFM.5.02.02.06", u"GFM.1.01.02"),
                            _(u"Disallowed entity code %(text)s in file %(file)s line %(line)s column %(column)s"),
                            modelDocument=filepath, text=text, file=os.path.basename(filepath), line=lineNum, column=match.start())
                elif modelXbrl.modelManager.disclosureSystem.EFM:
                    modelXbrl.error(u"EFM.5.02.01.01",
                        _(u"Disallowed character '%(text)s' in file %(file)s at line %(line)s col %(column)s"),
                        modelDocument=filepath, text=text, file=os.path.basename(filepath), line=lineNum, column=match.start())
            if lineNum == 1:
                xmlDeclarationMatch = XMLdeclaration.search(line)
                if xmlDeclarationMatch: # remove it for lxml
                    start,end = xmlDeclarationMatch.span()
                    line = line[0:start] + line[end:]
                    foundXmlDeclaration = True
            result.append(line)
            lineNum += 1
    result = u''.join(result)
    if not foundXmlDeclaration: # may be multiline, try again
        xmlDeclarationMatch = XMLdeclaration.search(result)
        if xmlDeclarationMatch: # remove it for lxml
            start,end = xmlDeclarationMatch.span()
            result = result[0:start] + result[end:]
            foundXmlDeclaration = True
    return (io.StringIO(initial_value=result), encoding)

def loadDTD(modelXbrl):
    global edbodyDTD
    if edbodyDTD is None:
        with open(os.path.join(modelXbrl.modelManager.cntlr.configDir, u"edbody.dtd")) as fh:
            edbodyDTD = DTD(fh)
        
def removeEntities(text):
    u''' ARELLE-128
    entitylessText = []
    findAt = 0
    while (True):
        entityStart = text.find('&',findAt)
        if entityStart == -1: break
        entityEnd = text.find(';',entityStart)
        if entityEnd == -1: break
        entitylessText.append(text[findAt:entityStart])
        findAt = entityEnd + 1
    entitylessText.append(text[findAt:])
    return ''.join(entitylessText)
    '''
    return namedEntityPattern.sub(u"", text)

def validateTextBlockFacts(modelXbrl):
    #handler = TextBlockHandler(modelXbrl)
    loadDTD(modelXbrl)
    checkedGraphicsFiles = set() #  only check any graphics file reference once per fact
    
    for f1 in modelXbrl.facts:
        # build keys table for 6.5.14
        concept = f1.concept
        if f1.xsiNil != u"true" and \
           concept is not None and \
           concept.isTextBlock and \
           XMLpattern.match(f1.value):
            #handler.fact = f1
            # test encoded entity tags
            for match in namedEntityPattern.finditer(f1.value):
                entity = match.group()
                if not entity in xhtmlEntities:
                    modelXbrl.error((u"EFM.6.05.16", u"GFM.1.2.15"),
                        _(u"Fact %(fact)s contextID %(contextID)s has disallowed entity %(entity)s"),
                        modelObject=f1, fact=f1.qname, contextID=f1.contextID, entity=entity, error=entity)
            # test html
            for xmltext in [f1.value] + CDATApattern.findall(f1.value):
                u'''
                try:
                    xml.sax.parseString(
                        "<?xml version='1.0' encoding='utf-8' ?>\n<body>\n{0}\n</body>\n".format(
                         removeEntities(xmltext)).encode('utf-8'),handler,handler)
                except (xml.sax.SAXParseException,
                        xml.sax.SAXException,
                        UnicodeDecodeError) as err:
                    # ignore errors which are not errors (e.g., entity codes checked previously
                    if not err.endswith("undefined entity"):
                        handler.modelXbrl.error(("EFM.6.05.15", "GFM.1.02.14"),
                            _("Fact %(fact)s contextID %(contextID)s has text which causes the XML error %(error)s"),
                            modelObject=f1, fact=f1.qname, contextID=f1.contextID, error=err)
                '''
                xmlBodyWithoutEntities = u"<body>\n{0}\n</body>\n".format(removeEntities(xmltext))
                try:
                    textblockXml = XML(xmlBodyWithoutEntities)
                    if not edbodyDTD.validate( textblockXml ):
                        errors = edbodyDTD.error_log.filter_from_errors()
                        htmlError = any(e.type_name in (u"DTD_INVALID_CHILD", u"DTD_UNKNOWN_ATTRIBUTE") 
                                        for e in errors)
                        modelXbrl.error(u"EFM.6.05.16" if htmlError else (u"EFM.6.05.15.dtdError", u"GFM.1.02.14"),
                            _(u"Fact %(fact)s contextID %(contextID)s has text which causes the XML error %(error)s"),
                            modelObject=f1, fact=f1.qname, contextID=f1.contextID, 
                            error=u', '.join(e.message for e in errors),
                            messageCodes=(u"EFM.6.05.16", u"EFM.6.05.15.dtdError", u"GFM.1.02.14"))
                    for elt in textblockXml.iter():
                        eltTag = elt.tag
                        for attrTag, attrValue in elt.items():
                            if ((attrTag == u"href" and eltTag == u"a") or 
                                (attrTag == u"src" and eltTag == u"img")):
                                if u"javascript:" in attrValue:
                                    modelXbrl.error(u"EFM.6.05.16.activeContent",
                                        _(u"Fact %(fact)s of context %(contextID)s has javascript in '%(attribute)s' for <%(element)s>"),
                                        modelObject=f1, fact=f1.qname, contextID=f1.contextID,
                                        attribute=attrTag, element=eltTag)
                                elif attrValue.startswith(u"http://www.sec.gov/Archives/edgar/data/") and eltTag == u"a":
                                    pass
                                elif u"http:" in attrValue or u"https:" in attrValue or u"ftp:" in attrValue:
                                    modelXbrl.error(u"EFM.6.05.16.externalReference",
                                        _(u"Fact %(fact)s of context %(contextID)s has an invalid external reference in '%(attribute)s' for <%(element)s>"),
                                        modelObject=f1, fact=f1.qname, contextID=f1.contextID,
                                        attribute=attrTag, element=eltTag)
                                if attrTag == u"src" and attrValue not in checkedGraphicsFiles:
                                    if attrValue.lower()[-4:] not in (u'.jpg', u'.gif'):
                                        modelXbrl.error(u"EFM.6.05.16.graphicFileType",
                                            _(u"Fact %(fact)s of context %(contextID)s references a graphics file which isn't .gif or .jpg '%(attribute)s' for <%(element)s>"),
                                            modelObject=f1, fact=f1.qname, contextID=f1.contextID,
                                            attribute=attrValue, element=eltTag)
                                    else:   # test file contents
                                        try:
                                            if validateGraphicFile(f1, attrValue) != attrValue.lower()[-3:]:
                                                modelXbrl.error(u"EFM.6.05.16.graphicFileContent",
                                                    _(u"Fact %(fact)s of context %(contextID)s references a graphics file which doesn't have expected content '%(attribute)s' for <%(element)s>"),
                                                    modelObject=f1, fact=f1.qname, contextID=f1.contextID,
                                                    attribute=attrValue, element=eltTag)
                                        except IOError, err:
                                            modelXbrl.error(u"EFM.6.05.16.graphicFileError",
                                                _(u"Fact %(fact)s of context %(contextID)s references a graphics file which isn't openable '%(attribute)s' for <%(element)s>, error: %(error)s"),
                                                modelObject=f1, fact=f1.qname, contextID=f1.contextID,
                                                attribute=attrValue, element=eltTag, error=err)
                                    checkedGraphicsFiles.add(attrValue)
                        if eltTag == u"table" and any(a is not None for a in elt.iterancestors(u"table")):
                            modelXbrl.error(u"EFM.6.05.16.nestedTable",
                                _(u"Fact %(fact)s of context %(contextID)s has nested <table> elements."),
                                modelObject=f1, fact=f1.qname, contextID=f1.contextID)
                except (XMLSyntaxError,
                        UnicodeDecodeError), err:
                    #if not err.endswith("undefined entity"):
                    modelXbrl.error((u"EFM.6.05.15", u"GFM.1.02.14"),
                        _(u"Fact %(fact)s contextID %(contextID)s has text which causes the XML error %(error)s"),
                        modelObject=f1, fact=f1.qname, contextID=f1.contextID, error=err)
                    
                checkedGraphicsFiles.clear()
                
            #handler.fact = None
                #handler.modelXbrl = None
    
def copyHtml(sourceXml, targetHtml):
    for sourceChild in sourceXml.iterchildren():
        targetChild = SubElement(targetHtml,
                                 sourceChild.localName if sourceChild.namespaceURI == XbrlConst.xhtml else sourceChild.tag)
        for attrTag, attrValue in sourceChild.items():
            targetChild.set(attrTag, attrValue)
        copyHtml(sourceChild, targetChild)
        
def validateFootnote(modelXbrl, footnote):
    #handler = TextBlockHandler(modelXbrl)
    loadDTD(modelXbrl)
    checkedGraphicsFiles = set() # only check any graphics file reference once per footnote
    
    try:
        footnoteHtml = XML(u"<body/>")
        copyHtml(footnote, footnoteHtml)
        if not edbodyDTD.validate( footnoteHtml ):
            modelXbrl.error(u"EFM.6.05.34.dtdError",
                _(u"Footnote %(xlinkLabel)s causes the XML error %(error)s"),
                modelObject=footnote, xlinkLabel=footnote.get(u"{http://www.w3.org/1999/xlink}label"),
                error=u', '.join(e.message for e in edbodyDTD.error_log.filter_from_errors()))
        for elt in footnoteHtml.iter():
            eltTag = elt.tag
            for attrTag, attrValue in elt.items():
                if ((attrTag == u"href" and eltTag == u"a") or 
                    (attrTag == u"src" and eltTag == u"img")):
                    if u"javascript:" in attrValue:
                        modelXbrl.error(u"EFM.6.05.34.activeContent",
                            _(u"Footnote %(xlinkLabel)s has javascript in '%(attribute)s' for <%(element)s>"),
                            modelObject=footnote, xlinkLabel=footnote.get(u"{http://www.w3.org/1999/xlink}label"),
                            attribute=attrTag, element=eltTag)
                    elif attrValue.startswith(u"http://www.sec.gov/Archives/edgar/data/") and eltTag == u"a":
                        pass
                    elif u"http:" in attrValue or u"https:" in attrValue or u"ftp:" in attrValue:
                        modelXbrl.error(u"EFM.6.05.34.externalReference",
                            _(u"Footnote %(xlinkLabel)s has an invalid external reference in '%(attribute)s' for <%(element)s>: %(value)s"),
                            modelObject=footnote, xlinkLabel=footnote.get(u"{http://www.w3.org/1999/xlink}label"),
                            attribute=attrTag, element=eltTag, value=attrValue)
                    if attrTag == u"src" and attrValue not in checkedGraphicsFiles:
                        if attrValue.lower()[-4:] not in (u'.jpg', u'.gif'):
                            modelXbrl.error(u"EFM.6.05.34.graphicFileType",
                                _(u"Footnote %(xlinkLabel)s references a graphics file which isn't .gif or .jpg '%(attribute)s' for <%(element)s>"),
                                modelObject=footnote, xlinkLabel=footnote.get(u"{http://www.w3.org/1999/xlink}label"),
                                attribute=attrValue, element=eltTag)
                        else:   # test file contents
                            try:
                                if validateGraphicFile(footnote, attrValue) != attrValue.lower()[-3:]:
                                    modelXbrl.error(u"EFM.6.05.34.graphicFileContent",
                                        _(u"Footnote %(xlinkLabel)s references a graphics file which doesn't have expected content '%(attribute)s' for <%(element)s>"),
                                        modelObject=footnote, xlinkLabel=footnote.get(u"{http://www.w3.org/1999/xlink}label"),
                                        attribute=attrValue, element=eltTag)
                            except IOError, err:
                                modelXbrl.error(u"EFM.6.05.34.graphicFileError",
                                    _(u"Footnote %(xlinkLabel)s references a graphics file which isn't openable '%(attribute)s' for <%(element)s>, error: %(error)s"),
                                    modelObject=footnote, xlinkLabel=footnote.get(u"{http://www.w3.org/1999/xlink}label"),
                                    attribute=attrValue, element=eltTag, error=err)
                        checkedGraphicsFiles.add(attrValue)
            if eltTag == u"table" and any(a is not None for a in elt.iterancestors(u"table")):
                modelXbrl.error(u"EFM.6.05.34.nestedTable",
                    _(u"Footnote %(xlinkLabel)s has nested <table> elements."),
                    modelObject=footnote, xlinkLabel=footnote.get(u"{http://www.w3.org/1999/xlink}label"))
    except (XMLSyntaxError,
            UnicodeDecodeError), err:
        #if not err.endswith("undefined entity"):
        modelXbrl.error(u"EFM.6.05.34",
            _(u"Footnote %(xlinkLabel)s causes the XML error %(error)s"),
            modelObject=footnote, xlinkLabel=footnote.get(u"{http://www.w3.org/1999/xlink}label"),
            error=edbodyDTD.error_log.filter_from_errors())

u'''
    if parent is None:
        parent = footnote
    
    if parent != footnote:
        for attrName, attrValue in footnote.items():
            if not (attrName in htmlAttributes and \
                (footnote.localName in htmlAttributes[attrName] or '*' in htmlAttributes[attrName])):
                modelXbrl.error("EFM.6.05.34",
                    _("Footnote %(xlinkLabel)s has attribute '%(attribute)s' not allowed for <%(element)s>"),
                    modelObject=parent, xlinkLabel=parent.get("{http://www.w3.org/1999/xlink}label"),
                    attribute=attrName, element=footnote.localName)
            elif (attrName == "href" and footnote.localName == "a") or \
                 (attrName == "src" and footnote.localName == "img"):
                if "javascript:" in attrValue:
                    modelXbrl.error("EFM.6.05.34",
                        _("Footnote %(xlinkLabel)s has javascript in '%(attribute)s' for <%(element)s>"),
                        modelObject=parent, xlinkLabel=parent.get("{http://www.w3.org/1999/xlink}label"),
                        attribute=attrName, element=footnote.localName)
                elif attrValue.startswith("http://www.sec.gov/Archives/edgar/data/") and footnote.localName == "a":
                    pass
                elif "http:" in attrValue or "https:" in attrValue or "ftp:" in attrValue:
                    modelXbrl.error("EFM.6.05.34",
                        _("Footnote %(xlinkLabel)s has an invalid external reference in '%(attribute)s' for <%(element)s>: %(value)s"),
                        modelObject=parent, xlinkLabel=parent.get("{http://www.w3.org/1999/xlink}label"),
                        attribute=attrName, element=footnote.localName, value=attrValue)
            
    for child in footnote.iterchildren():
        if isinstance(child,ModelObject): #element
            if not child.localName in bodyTags:
                modelXbrl.error("EFM.6.05.34",
                    _("Footnote %(xlinkLabel)s has disallowed html tag: <%(element)s>"),
                    modelObject=parent, xlinkLabel=parent.get("{http://www.w3.org/1999/xlink}label"),
                    element=child.localName)
            else:
                validateFootnote(modelXbrl, child, footnote)

    #handler.modelXbrl = None


class TextBlockHandler(xml.sax.ContentHandler, xml.sax.ErrorHandler): 

    def __init__ (self, modelXbrl): 
        self.modelXbrl = modelXbrl 
        
    def startDocument(self):
        self.nestedBodyCount = 0
    
    def startElement(self, name, attrs): 
        if name == "body":
            self.nestedBodyCount += 1
            if self.nestedBodyCount == 1:   # outer body is ok
                return
        if not name in bodyTags:
            self.modelXbrl.error("EFM.6.05.16",
                _("Fact %(fact)s of context %(contextID)s has disallowed html tag: <%(element)s>"),
                modelObject=self.fact, fact=self.fact.qname, contextID=self.fact.contextID,
                element=name)
        else:
            for item in attrs.items():
                if not (item[0] in htmlAttributes and \
                    (name in htmlAttributes[item[0]] or '*' in htmlAttributes[item[0]])):
                    self.modelXbrl.error("EFM.6.05.16",
                        _("Fact %(fact)s of context %(contextID)s has attribute '%(attribute)s' not allowed for <%(element)s>"),
                        modelObject=self.fact, fact=self.fact.qname, contextID=self.fact.contextID,
                        attribute=item[0], element=name)
                elif (item[0] == "href" and name == "a") or \
                     (item[0] == "src" and name == "img"):
                    if "javascript:" in item[1]:
                        self.modelXbrl.error("EFM.6.05.16",
                            _("Fact %(fact)s of context %(contextID)s has javascript in '%(attribute)s' for <%(element)s>"),
                            modelObject=self.fact, fact=self.fact.qname, contextID=self.fact.contextID,
                            attribute=item[0], element=name)
                    elif item[1].startswith("http://www.sec.gov/Archives/edgar/data/") and name == "a":
                        pass
                    elif "http:" in item[1] or "https:" in item[1] or "ftp:" in item[1]:
                        self.modelXbrl.error("EFM.6.05.16",
                            _("Fact %(fact)s of context %(contextID)s has an invalid external reference in '%(attribute)s' for <%(element)s>"),
                            modelObject=self.fact, fact=self.fact.qname, contextID=self.fact.contextID,
                            attribute=item[0], element=name)

    def characters (self, ch):
        if ">" in ch:
            self.modelXbrl.error("EFM.6.05.15",
                _("Fact %(fact)s of context %(contextID)s has a '>' in text, not well-formed XML: '%(text)s'"),
                 modelObject=self.fact, fact=self.fact.qname, contextID=self.fact.contextID, text=ch)

    def endElement(self, name):
        if name == "body":
            self.nestedBodyCount -= 1
            
    def error(self, err):
        self.modelXbrl.error("EFM.6.05.15",
            _("Fact %(fact)s of context %(contextID)s has text which causes the XML error %(error)s line %(line)s column %(column)s"),
             modelObject=self.fact, fact=self.fact.qname, contextID=self.fact.contextID, 
             error=err.getMessage(), line=err.getLineNumber(), column=err.getColumnNumber())
    
    def fatalError(self, err):
        msg = err.getMessage()
        self.modelXbrl.error("EFM.6.05.15",
            _("Fact %(fact)s of context %(contextID)s has text which causes the XML fatal error %(error)s line %(line)s column %(column)s"),
             modelObject=self.fact, fact=self.fact.qname, contextID=self.fact.contextID, 
             error=err.getMessage(), line=err.getLineNumber(), column=err.getColumnNumber())
    
    def warning(self, err):
        self.modelXbrl.warning("EFM.6.05.15",
            _("Fact %(fact)s of context %(contextID)s has text which causes the XML warning %(error)s line %(line)s column %(column)s"),
             modelObject=self.fact, fact=self.fact.qname, contextID=self.fact.contextID, 
             error=err.getMessage(), line=err.getLineNumber(), column=err.getColumnNumber())
'''

def validateGraphicFile(elt, graphicFile):
    base = elt.modelDocument.baseForElement(elt)
    normalizedUri = elt.modelXbrl.modelManager.cntlr.webCache.normalizeUrl(graphicFile, base)
    if not elt.modelXbrl.fileSource.isInArchive(normalizedUri):
        normalizedUri = elt.modelXbrl.modelManager.cntlr.webCache.getfilename(normalizedUri)
    # all Edgar graphic files must be resolved locally
    #normalizedUri = elt.modelXbrl.modelManager.cntlr.webCache.getfilename(normalizedUri)
    with elt.modelXbrl.fileSource.file(normalizedUri,binary=True)[0] as fh:
        data = fh.read(11)
        if data[:4] == '\xff\xd8\xff\xe0' and data[6:] == 'JFIF\0': 
            return u"jpg"
        if data[:3] == "GIF" and data[3:6] in ('89a', '89b', '87a'):
            return u"gif"
    return None