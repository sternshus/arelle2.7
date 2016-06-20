u'''
Created on Dec 20, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from __future__ import division
import math, re, sre_constants
from arelle.ModelObject import ModelObject, ModelAttribute
from arelle.ModelValue import (qname, dateTime, DateTime, DATE, DATETIME, dayTimeDuration,
                         YearMonthDuration, DayTimeDuration, time, Time)
from arelle.FunctionUtil import anytypeArg, atomicArg, stringArg, numericArg, integerArg, qnameArg, nodeArg
from arelle import FunctionXs, XPathContext, XbrlUtil, XmlUtil, UrlUtil, ModelDocument, XmlValidate
from arelle.Locale import format_picture
from arelle.XmlValidate import VALID_NO_CONTENT
from decimal import Decimal
from lxml import etree

DECIMAL_5 = Decimal(.5)
    
class fnFunctionNotAvailable(Exception):
    def __init__(self):
        self.args =  (u"fn function not available",)
    def __repr__(self):
        return self.args[0]
    
def call(xc, p, localname, contextItem, args):
    try:
        if localname not in fnFunctions: raise fnFunctionNotAvailable
        return fnFunctions[localname](xc, p, contextItem, args)
    except fnFunctionNotAvailable:
        raise XPathContext.FunctionNotAvailable(u"fn:{0}".format(localname))
        
def node_name(xc, p, contextItem, args):
    node = nodeArg(xc, args, 0, u"node()?", missingArgFallback=contextItem, emptyFallback=())
    if node != (): 
        return qname(node)
    return () 

def nilled(xc, p, contextItem, args):
    node = nodeArg(xc, args, 0, u"node()?", missingArgFallback=contextItem, emptyFallback=())
    if node != () and isinstance(node,ModelObject):
        return node.get(u"{http://www.w3.org/2001/XMLSchema-instance}nil") == u"true"
    return ()

def string(xc, p, contextItem, args):
    if len(args) > 1: raise XPathContext.FunctionNumArgs()
    item = anytypeArg(xc, args, 0, u"item()?", missingArgFallback=contextItem)
    if item == (): 
        return u''
    if isinstance(item, ModelObject) and getattr(item,u"xValid", 0) == VALID_NO_CONTENT:
        x = item.stringValue # represents inner text of this and all subelements
    else:
        x = xc.atomize(p, item)
    return FunctionXs.xsString( xc, p, x ) 

def data(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    return xc.atomize(p, args[0])

def base_uri(xc, p, contextItem, args):
    item = anytypeArg(xc, args, 0, u"node()?", missingArgFallback=contextItem)
    if item == (): 
        return u''
    if isinstance(item, (ModelObject, ModelDocument)):
        return UrlUtil.ensureUrl(item.modelDocument.uri)
    return u''

def document_uri(xc, p, contextItem, args):
    return xc.modelXbrl.modelDocument.uri

def error(xc, p, contextItem, args):
    if len(args) > 2: raise XPathContext.FunctionNumArgs()
    qn = qnameArg(xc, p, args, 0, u'QName?', emptyFallback=None)
    msg = stringArg(xc, args, 1, u"xs:string", emptyFallback=u'')
    raise XPathContext.XPathException(p, (qn or u"err:FOER0000"), msg)

def trace(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def fn_dateTime(xc, p, contextItem, args):
    if len(args) != 2: raise XPathContext.FunctionNumArgs()
    date = anytypeArg(xc, args, 0, u"xs:date", missingArgFallback=())
    time = anytypeArg(xc, args, 1, u"xs:time", missingArgFallback=())
    if date is None or time is None:
        return ()
    return dateTime(date) + dayTimeDuration(time)

def fn_abs(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    x = numericArg(xc, p, args)
    if math.isinf(x): 
        x = float(u'inf')
    elif not math.isnan(x): 
        x = abs(x)
    return x

def fn_ceiling(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    math.ceil(numericArg(xc, p, args))

def fn_floor(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    math.floor(numericArg(xc, p, args))

def fn_round(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    x = numericArg(xc, p, args)
    if math.isinf(x) or math.isnan(x): 
        return x
    return _INT(x + (DECIMAL_5 if isinstance(x,Decimal) else .5))  # round towards +inf

def fn_round_half_to_even(xc, p, contextItem, args):
    if len(args) > 2 or len(args) == 0: raise XPathContext.FunctionNumArgs()
    x = numericArg(xc, p, args)
    if len(args) == 2:
        precision = args[1]
        if len(precision) != 1 or not isinstance(precision[0],_INT_TYPES): raise XPathContext.FunctionArgType(2,u"integer")
        precision = precision[0]
        return round(x, precision)
    return round(x)

def codepoints_to_string(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    try:
        return u''.join(unichr(c) for c in args[0])
    except TypeError:
        XPathContext.FunctionArgType(1,u"xs:integer*")

def string_to_codepoints(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    unicode = stringArg(xc, args, 0, u"xs:string", emptyFallback=())
    if unicode == (): return ()
    return tuple(ord(c) for c in unicode)

def compare(xc, p, contextItem, args):
    if len(args) == 3: raise fnFunctionNotAvailable()
    if len(args) != 2: raise XPathContext.FunctionNumArgs()
    comparand1 = stringArg(xc, args, 0, u"xs:string?", emptyFallback=())
    comparand2 = stringArg(xc, args, 1, u"xs:string?", emptyFallback=())
    if comparand1 == () or comparand2 == (): return ()
    if comparand1 == comparand2: return 0
    if comparand1 < comparand2: return -1
    return 1

def codepoint_equal(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def concat(xc, p, contextItem, args):
    if len(args) < 2: raise XPathContext.FunctionNumArgs()
    atomizedArgs = []
    for i in xrange(len(args)):
        item = anytypeArg(xc, args, i, u"xs:anyAtomicType?")
        if item != ():
            atomizedArgs.append( FunctionXs.xsString( xc, p, xc.atomize(p, item) ) )
    return u''.join(atomizedArgs)

def string_join(xc, p, contextItem, args):
    if len(args) != 2: raise XPathContext.FunctionNumArgs()
    joiner = stringArg(xc, args, 1, u"xs:string")
    atomizedArgs = []
    for x in xc.atomize( p, args[0] ):
        if isinstance(x, _STR_BASE):
            atomizedArgs.append(x)
        else:
            raise XPathContext.FunctionArgType(0,u"xs:string*")
    return joiner.join(atomizedArgs)

def substring(xc, p, contextItem, args):
    l = len(args)
    if l < 2 or l > 3: raise XPathContext.FunctionNumArgs()
    string = stringArg(xc, args, 0, u"xs:string?")
    start = _INT(round( numericArg(xc, p, args, 1) )) - 1
    if l == 3:
        length = _INT(round( numericArg(xc, p, args, 2) ))
        if start < 0:
            length += start
            if length < 0: length = 0
            start = 0 
        return string[start:start + length]
    if start < 0: start = 0
    return string[start:]

def string_length(xc, p, contextItem, args):
    if len(args) > 1: raise XPathContext.FunctionNumArgs()
    return len( stringArg(xc, args, 0, u"xs:string", missingArgFallback=contextItem) )

nonSpacePattern = re.compile(ur"\S+")
def normalize_space(xc, p, contextItem, args):
    if len(args) > 1: raise XPathContext.FunctionNumArgs()
    return u' '.join( nonSpacePattern.findall( stringArg(xc, args, 0, u"xs:string", missingArgFallback=contextItem) ) )

def normalize_unicode(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def upper_case(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    return stringArg(xc, args, 0, u"xs:string").upper()

def lower_case(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    return stringArg(xc, args, 0, u"xs:string").lower()

def translate(xc, p, contextItem, args):
    if len(args) != 3: raise XPathContext.FunctionNumArgs()
    arg = stringArg(xc, args, 0, u"xs:string?", emptyFallback=())
    mapString = stringArg(xc, args, 1, u"xs:string", emptyFallback=())
    transString = stringArg(xc, args, 2, u"xs:string", emptyFallback=())
    if arg == (): return ()
    out = []
    for c in arg:
        if c in mapString:
            i = mapString.index(c)
            if i < len(transString):
                out.append(transString[i])
        else:
            out.append(c)
    return u''.join(out)

def encode_for_uri(xc, p, contextItem, args):
    from urllib import quote
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    return quote(stringArg(xc, args, 0, u"xs:string"))

def iri_to_uri(xc, p, contextItem, args):
    return encode_for_uri(xc, p, contextItem, args)

def escape_html_uri(xc, p, contextItem, args):
    return encode_for_uri(xc, p, contextItem, args)

def contains(xc, p, contextItem, args):
    return substring_functions(xc, args, contains=True)

def starts_with(xc, p, contextItem, args):
    return substring_functions(xc, args, startEnd=True)

def ends_with(xc, p, contextItem, args):
    return substring_functions(xc, args, startEnd=False)

def substring_before(xc, p, contextItem, args):
    return substring_functions(xc, args, beforeAfter=True)

def substring_after(xc, p, contextItem, args):
    return substring_functions(xc, args, beforeAfter=False)

def substring_functions(xc, args, contains=None, startEnd=None, beforeAfter=None):
    if len(args) == 3: raise fnFunctionNotAvailable()
    if len(args) != 2: raise XPathContext.FunctionNumArgs()
    string = stringArg(xc, args, 0, u"xs:string?")
    portion = stringArg(xc, args, 1, u"xs:string")
    if contains == True:
        return portion in string
    elif startEnd == True:
        return string.startswith(portion)
    elif startEnd == False:
        return string.endswith(portion)
    elif beforeAfter is not None:
        if portion == u'': return u''
        try:
            if beforeAfter: return string.partition( portion )[0]
            else: return string.rpartition( portion )[2]
        except ValueError:
            return u''
    raise fnFunctionNotAvailable()  # wrong arguments?

def regexFlags(xc, p, args, n):
    f = 0
    flagsArg = stringArg(xc, args, n, u"xs:string", missingArgFallback=u"", emptyFallback=u"")
    for c in flagsArg:
        if c == u's': f |= re.S
        elif c == u'm': f |= re.M
        elif c == u'i': f |= re.I
        elif c == u'x': f |= re.X
        else:
            raise XPathContext.XPathException(p, u'err:FORX0001', _(u'Regular expression interpretation flag unrecognized: {0}').format(flagsArg))
    return f
            
def matches(xc, p, contextItem, args):
    if not 2 <= len(args) <= 3: raise XPathContext.FunctionNumArgs()
    input = stringArg(xc, args, 0, u"xs:string?", emptyFallback=u"")
    pattern = stringArg(xc, args, 1, u"xs:string", emptyFallback=u"")
    try:
        return bool(re.search(pattern,input,flags=regexFlags(xc, p, args, 2)))
    except sre_constants.error, err:
        raise XPathContext.XPathException(p, u'err:FORX0002', _(u'fn:matches regular expression pattern error: {0}').format(err))
        

def replace(xc, p, contextItem, args):
    if not 3 <= len(args) <= 4: raise XPathContext.FunctionNumArgs()
    input = stringArg(xc, args, 0, u"xs:string?", emptyFallback=u"")  # empty string is default
    pattern = stringArg(xc, args, 1, u"xs:string", emptyFallback=u"")
    fnReplacement = stringArg(xc, args, 2, u"xs:string", emptyFallback=u"")
    if re.findall(ur"(^|[^\\])[$]|[$][^0-9]", fnReplacement):
        raise XPathContext.XPathException(p, u'err:FORX0004', _(u'fn:replace pattern \'$\' error in: {0}').format(fnReplacement))
    reReplacement = re.sub(ur"[\\][$]", u"$", 
                         re.sub(ur"(^|[^\\])[$]([1-9])", ur"\\\2", fnReplacement))
    try:
        return re.sub(pattern,reReplacement,input,flags=regexFlags(xc, p, args, 3))
    except sre_constants.error, err:
        raise XPathContext.XPathException(p, u'err:FORX0002', _(u'fn:replace regular expression pattern error: {0}').format(err))

def tokenize(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def resolve_uri(xc, p, contextItem, args):
    if len(args) != 2: raise XPathContext.FunctionNumArgs()
    relative = stringArg(xc, args, 0, u"xs:string?", emptyFallback=())
    base = stringArg(xc, args, 1, u"xs:string", emptyFallback=())
    return xc.modelXbrl.modelManager.cntlr.webCache.normalizeUrl(relative,base)

def true(xc, p, contextItem, args):
    return True

def false(xc, p, contextItem, args):
    return False

def _not(xc, p, contextItem, args):
    return not boolean(xc, p, contextItem, args)

def years_from_duration(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'duration', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DayTimeDuration): return 0
    if isinstance(d, YearMonthDuration): return d.years
    raise XPathContext.FunctionArgType(1,u"xs:duration")    

def months_from_duration(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'duration', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DayTimeDuration): return 0
    if isinstance(d, YearMonthDuration): return d.months
    raise XPathContext.FunctionArgType(1,u"xs:duration")    

def days_from_duration(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'duration', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DayTimeDuration): return d.days
    if isinstance(d, YearMonthDuration): return d.dayHrsMinsSecs[0]
    raise XPathContext.FunctionArgType(1,u"xs:duration")    

def hours_from_duration(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'duration', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DayTimeDuration): return 0
    if isinstance(d, YearMonthDuration): return d.dayHrsMinsSecs[1]
    raise XPathContext.FunctionArgType(1,u"xs:duration")    

def minutes_from_duration(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'duration', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DayTimeDuration): return 0
    if isinstance(d, YearMonthDuration): return d.dayHrsMinsSecs[2]
    raise XPathContext.FunctionArgType(1,u"xs:duration")    

def seconds_from_duration(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'duration', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DayTimeDuration): return 0
    if isinstance(d, YearMonthDuration): return d.dayHrsMinsSecs[2]
    raise XPathContext.FunctionArgType(1,u"xs:duration")    

def year_from_dateTime(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.year
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def month_from_dateTime(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.month
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def day_from_dateTime(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.day
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def hours_from_dateTime(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.hour
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def minutes_from_dateTime(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.minute
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def seconds_from_dateTime(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.second
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def timezone_from_dateTime(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.tzinfo
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def year_from_date(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.year
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def month_from_date(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.month
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def day_from_date(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.day
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def timezone_from_date(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'dateTime', missingArgFallback=())
    if d == (): return d
    if isinstance(d, DateTime): return d.tzinfo
    raise XPathContext.FunctionArgType(1,u"xs:dateTime")    

def hours_from_time(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'time', missingArgFallback=())
    if d == (): return d
    if isinstance(d, Time): return d.hour
    raise XPathContext.FunctionArgType(1,u"xs:time")    

def minutes_from_time(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'time', missingArgFallback=())
    if d == (): return d
    if isinstance(d, Time): return d.minute
    raise XPathContext.FunctionArgType(1,u"xs:time")    

def seconds_from_time(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'time', missingArgFallback=())
    if d == (): return d
    if isinstance(d, Time): return d.second
    raise XPathContext.FunctionArgType(1,u"xs:time")    

def timezone_from_time(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    d = anytypeArg(xc, args, 0, u'time', missingArgFallback=())
    if d == (): return d
    if isinstance(d, Time): return d.tzinfo
    raise XPathContext.FunctionArgType(1,u"xs:time")    

def adjust_dateTime_to_timezone(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def adjust_date_to_timezone(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def adjust_time_to_timezone(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def resolve_QName(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def QName(xc, p, contextItem, args):
    if len(args) != 2: raise XPathContext.FunctionNumArgs()
    ns = stringArg(xc, args, 0, u"xs:string?")
    prefixedName = stringArg(xc, args, 1, u"xs:string")
    return qname(ns, prefixedName)


def prefix_from_QName(xc, p, contextItem, args):
    return QName_functions(xc, p, args, prefix=True)

def local_name_from_QName(xc, p, contextItem, args):
    return QName_functions(xc, p, args, localName=True)

def namespace_uri_from_QName(xc, p, contextItem, args):
    return QName_functions(xc, p, args, namespaceURI=True)

def QName_functions(xc, p, args, prefix=False, localName=False, namespaceURI=False):
    qn = qnameArg(xc, p, args, 0, u'QName?', emptyFallback=())
    if qn != ():
        if prefix: return qn.prefix
        if localName: return qn.localName
        if namespaceURI: return qn.namespaceURI
    return ()

def namespace_uri_for_prefix(xc, p, contextItem, args):
    prefix = nodeArg(xc, args, 0, u'string?', emptyFallback=u'')
    node = nodeArg(xc, args, 1, u'element()', emptyFallback=())
    if node is not None and isinstance(node,ModelObject):
        return XmlUtil.xmlns(node, prefix)
    return ()

def in_scope_prefixes(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def name(xc, p, contextItem, args):
    return Node_functions(xc, contextItem, args, name=True)

def local_name(xc, p, contextItem, args):
    return Node_functions(xc, contextItem, args, localName=True)

def namespace_uri(xc, p, contextItem, args):
    return Node_functions(xc, contextItem, args, namespaceURI=True)

def Node_functions(xc, contextItem, args, name=None, localName=None, namespaceURI=None):
    node = nodeArg(xc, args, 0, u'node()?', missingArgFallback=contextItem, emptyFallback=())
    if node != () and isinstance(node, ModelObject):
        if name: return node.prefixedName
        if localName: return node.localName
        if namespaceURI: return node.namespaceURI
    return u''

NaN = float(u'NaN')

def number(xc, p, contextItem, args):
    # TBD: add argument of type of number to convert to (fallback is float)
    n = numericArg(xc, p, args, missingArgFallback=contextItem, emptyFallback=NaN, convertFallback=NaN)
    return float(n)

def lang(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def root(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def boolean(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    inputSequence = args[0]
    if inputSequence is None or len(inputSequence) == 0:
        return False
    item = inputSequence[0]
    if isinstance(item, (ModelObject, ModelAttribute, etree._ElementTree)):
        return True
    if len(inputSequence) == 1:
        if isinstance(item, bool):
            return item
        if isinstance(item, _STR_BASE):
            return len(item) > 0
        if isinstance(item, _NUM_TYPES):
            return not math.isnan(item) and item != 0
    raise XPathContext.XPathException(p, u'err:FORG0006', _(u'Effective boolean value indeterminate'))

def index_of(xc, p, contextItem, args):
    if len(args) == 3: raise fnFunctionNotAvailable()
    if len(args) != 2: raise XPathContext.FunctionNumArgs()
    seq = xc.atomize(p, args[0])
    srch = xc.atomize(p, args[1])
    if isinstance(srch,(tuple,list)):
        if len(srch) != 1: raise XPathContext.FunctionArgType(1,u'xs:anyAtomicType')
        srch = srch[0]
    indices = []
    pos = 0
    for x in seq:
        pos += 1
        if x == srch:
            indices.append(pos)
    return indices

def empty(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    return len(xc.flattenSequence(args[0])) == 0

def exists(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    return len(xc.flattenSequence(args[0])) > 0

def distinct_values(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    sequence = args[0]
    if len(sequence) == 0: return []
    return list(set(xc.atomize(p, sequence)))

def insert_before(xc, p, contextItem, args):
    if len(args) != 3: raise XPathContext.FunctionNumArgs()
    sequence = args[0]
    if isinstance(sequence, tuple): sequence = list(sequence)
    elif not isinstance(sequence, list): sequence = [sequence]
    index = integerArg(xc, p, args, 1, u"xs:integer", convertFallback=0) - 1
    insertion = args[2]
    if isinstance(insertion, tuple): insertion = list(insertion)
    elif not isinstance(insertion, list): insertion = [insertion]
    return sequence[:index] + insertion + sequence[index:]

def remove(xc, p, contextItem, args):
    if len(args) != 2: raise XPathContext.FunctionNumArgs()
    sequence = args[0]
    index = integerArg(xc, p, args, 1, u"xs:integer", convertFallback=0) - 1
    return sequence[:index] + sequence[index+1:]

def reverse(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    sequence = args[0]
    if len(sequence) == 0: return []
    return list( reversed(sequence) )

def subsequence(xc, p, contextItem, args):
    if len(args) not in (2,3): raise XPathContext.FunctionNumArgs()
    l = len(args)
    if l < 2 or l > 3: raise XPathContext.FunctionNumArgs()
    sequence = args[0]
    start = _INT(round( numericArg(xc, p, args, 1) )) - 1
    if l == 3:
        length = _INT(round( numericArg(xc, p, args, 2) ))
        if start < 0:
            length += start
            if length < 0: length = 0
            start = 0 
        return sequence[start:start + length]
    if start < 0: start = 0
    return sequence[start:]

def unordered(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    return args[0]

def zero_or_one(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    if len(args[0]) > 1:
        raise XPathContext.FunctionNumArgs(errCode=u'err:FORG0003',
                                           errText=_(u'fn:zero-or-one called with a sequence containing more than one item'))
    return args[0]

def one_or_more(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    if len(args[0]) < 1:
        raise XPathContext.FunctionNumArgs(errCode=u'err:FORG0004',
                                           errText=_(u'fn:one-or-more called with a sequence containing no items'))
    return args[0]

def exactly_one(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    if len(args[0]) != 1:
        raise XPathContext.FunctionNumArgs(errCode=u'err:FORG0005',
                                           errText=_(u'fn:exactly-one called with a sequence containing zero or more than one item'))
    return args[0]

def deep_equal(xc, p, contextItem, args):
    if len(args) != 2: raise XPathContext.FunctionNumArgs()
    return XbrlUtil.nodesCorrespond(xc.modelXbrl, args[0], args[1])

def count(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    return len(xc.flattenSequence(args[0]))

def avg(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    addends = xc.atomize( p, args[0] )
    try:
        l = len(addends)
        if l == 0: 
            return ()  # xpath allows empty sequence argument
        hasFloat = False
        hasDecimal = False
        for a in addends:
            if math.isnan(a) or math.isinf(a):
                return NaN
            if isinstance(a, float):
                hasFloat = True
            elif isinstance(a, Decimal):
                hasDecimal = True
        if hasFloat and hasDecimal: # promote decimals to float
            addends = [float(a) if isinstance(a, Decimal) else a
                       for a in addends]
        return sum( addends ) / len( args[0] )
    except TypeError:
        raise XPathContext.FunctionArgType(1,u"sumable values", addends, errCode=u'err:FORG0001')

def fn_max(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    comparands = xc.atomize( p, args[0] )
    try:
        if len(comparands) == 0: 
            return ()  # xpath allows empty sequence argument
        if any(isinstance(c, float) and math.isnan(c) for c in comparands):
            return NaN
        return max( comparands )
    except TypeError:
        raise XPathContext.FunctionArgType(1,u"comparable values", comparands, errCode=u'err:FORG0001')

def fn_min(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    comparands = xc.atomize( p, args[0] )
    try:
        if len(comparands) == 0: 
            return ()  # xpath allows empty sequence argument
        if any(isinstance(c, float) and math.isnan(c) for c in comparands):
            return NaN
        return min( comparands )
    except TypeError:
        raise XPathContext.FunctionArgType(1,u"comparable values", comparands, errCode=u'err:FORG0001')

def fn_sum(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    addends = xc.atomize( p, args[0] )
    try:
        if len(addends) == 0: 
            return 0  # xpath allows empty sequence argument
        hasFloat = False
        hasDecimal = False
        for a in addends:
            if math.isnan(a):
                return NaN
            if isinstance(a, float):
                hasFloat = True
            elif isinstance(a, Decimal):
                hasDecimal = True
        if hasFloat and hasDecimal: # promote decimals to float
            addends = [float(a) if isinstance(a, Decimal) else a
                       for a in addends]
        return sum( addends )
    except TypeError:
        raise XPathContext.FunctionArgType(1,u"summable sequence", addends, errCode=u'err:FORG0001')

def id(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def idref(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def doc(xc, p, contextItem, args):
    if len(args) != 1: raise XPathContext.FunctionNumArgs()
    uri = stringArg(xc, args, 0, u"xs:string", emptyFallback=None)
    if uri is None:
        return ()
    if xc.progHeader is None or xc.progHeader.element is None:
        raise XPathContext.XPathException(p, u'err:FODC0005', _(u'Function xf:doc no formula resource element for {0}').format(uri))
    if not UrlUtil.isValid(uri):
        raise XPathContext.XPathException(p, u'err:FODC0005', _(u'Function xf:doc $uri is not valid {0}').format(uri))
    normalizedUri = xc.modelXbrl.modelManager.cntlr.webCache.normalizeUrl(
                                uri, 
                                xc.progHeader.element.modelDocument.baseForElement(xc.progHeader.element))
    if normalizedUri in xc.modelXbrl.urlDocs:
        return xc.modelXbrl.urlDocs[normalizedUri].xmlDocument
    modelDocument = ModelDocument.load(xc.modelXbrl, normalizedUri)
    if modelDocument is None:
        raise XPathContext.XPathException(p, u'err:FODC0005', _(u'Function xf:doc $uri not successfully loaded {0}').format(uri))
    # assure that document is validated
    XmlValidate.validate(xc.modelXbrl, modelDocument.xmlRootElement)
    return modelDocument.xmlDocument

def doc_available(xc, p, contextItem, args):
    return isinstance(doc(xc, p, contextItem, args), etree._ElementTree)

def collection(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def position(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def last(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

def current_dateTime(xc, p, contextItem, args):
    from datetime import datetime
    return dateTime(datetime.now(), type=DATETIME)

def current_date(xc, p, contextItem, args):
    from datetime import date
    return dateTime(date.today(), type=DATE)

def current_time(xc, p, contextItem, args):
    from datetime import datetime
    return time(datetime.now())

def implicit_timezone(xc, p, contextItem, args):
    from datetime import datetime
    return datetime.now().tzinfo

def default_collation(xc, p, contextItem, args):
    # only unicode is supported
    return u"http://www.w3.org/2005/xpath-functions/collation/codepoint"

def static_base_uri(xc, p, contextItem, args):
    raise fnFunctionNotAvailable()

# added in XPATH 3
def  format_number(xc, p, args):
    if len(args) != 2: raise XPathContext.FunctionNumArgs()
    value = numericArg(xc, p, args, 0, missingArgFallback=u'NaN', emptyFallback=u'NaN')
    picture = stringArg(xc, args, 1, u"xs:string", missingArgFallback=u'', emptyFallback=u'')
    try:
        return format_picture(xc.modelXbrl.locale, value, picture)
    except ValueError, err:
        raise XPathContext.XPathException(p, u'err:FODF1310', unicode(err) )
    
fnFunctions = {
    u'node-name': node_name,
    u'nilled': nilled,
    u'string': string,
    u'data': data,
    u'base-uri': base_uri,
    u'document-uri': document_uri,
    u'error': error,
    u'trace': trace,
    u'dateTime': fn_dateTime,
    u'abs': fn_abs,
    u'ceiling': fn_ceiling,
    u'floor': fn_floor,
    u'round': fn_round,
    u'round-half-to-even': fn_round_half_to_even,
    u'codepoints-to-string': codepoints_to_string,
    u'string-to-codepoints': string_to_codepoints,
    u'compare': compare,
    u'codepoint-equal': codepoint_equal,
    u'concat': concat,
    u'string-join': string_join,
    u'substring': substring,
    u'string-length': string_length,
    u'normalize-space': normalize_space,
    u'normalize-unicode': normalize_unicode,
    u'upper-case': upper_case,
    u'lower-case': lower_case,
    u'translate': translate,
    u'encode-for-uri': encode_for_uri,
    u'iri-to-uri': iri_to_uri,
    u'escape-html-uri': escape_html_uri,
    u'contains': contains,
    u'starts-with': starts_with,
    u'ends-with': ends_with,
    u'substring-before': substring_before,
    u'substring-after': substring_after,
    u'matches': matches,
    u'replace': replace,
    u'tokenize': tokenize,
    u'resolve-uri': resolve_uri,
    u'true': true,
    u'false': false,
    u'not': _not,
    u'years-from-duration': years_from_duration,
    u'months-from-duration': months_from_duration,
    u'days-from-duration': days_from_duration,
    u'hours-from-duration': hours_from_duration,
    u'minutes-from-duration': minutes_from_duration,
    u'seconds-from-duration': seconds_from_duration,
    u'year-from-dateTime': year_from_dateTime,
    u'month-from-dateTime': month_from_dateTime,
    u'day-from-dateTime': day_from_dateTime,
    u'hours-from-dateTime': hours_from_dateTime,
    u'minutes-from-dateTime': minutes_from_dateTime,
    u'seconds-from-dateTime': seconds_from_dateTime,
    u'timezone-from-dateTime': timezone_from_dateTime,
    u'year-from-date': year_from_date,
    u'month-from-date': month_from_date,
    u'day-from-date': day_from_date,
    u'timezone-from-date': timezone_from_date,
    u'hours-from-time': hours_from_time,
    u'minutes-from-time': minutes_from_time,
    u'seconds-from-time': seconds_from_time,
    u'timezone-from-time': timezone_from_time,
    u'adjust-dateTime-to-timezone': adjust_dateTime_to_timezone,
    u'adjust-date-to-timezone': adjust_date_to_timezone,
    u'adjust-time-to-timezone': adjust_time_to_timezone,
    u'resolve-QName': resolve_QName,
    u'QName': QName,
    u'prefix-from-QName': prefix_from_QName,
    u'local-name-from-QName': local_name_from_QName,
    u'namespace-uri-from-QName': namespace_uri_from_QName,
    u'namespace-uri-for-prefix': namespace_uri_for_prefix,
    u'in-scope-prefixes': in_scope_prefixes,
    u'name': name,
    u'local-name': local_name,
    u'namespace-uri': namespace_uri,
    u'number': number,
    u'lang': lang,
    u'root': root,
    u'boolean': boolean,
    u'index-of': index_of,
    u'empty': empty,
    u'exists': exists,
    u'distinct-values': distinct_values,
    u'insert-before': insert_before,
    u'remove': remove,
    u'reverse': reverse,
    u'subsequence': subsequence,
    u'unordered': unordered,
    u'zero-or-one': zero_or_one,
    u'one-or-more': one_or_more,
    u'exactly-one': exactly_one,
    u'deep-equal': deep_equal,
    u'count': count,
    u'avg': avg,
    u'max': fn_max,
    u'min': fn_min,
    u'sum': fn_sum,
    u'id': id,
    u'idref': idref,
    u'doc': doc,
    u'doc-available': doc_available,
    u'collection': collection,
    u'position': position,
    u'last': last,
    u'current-dateTime': current_dateTime,
    u'current-date': current_date,
    u'current-time': current_time,
    u'implicit-timezone': implicit_timezone,
    u'default-collation': default_collation,
    u'static-base-uri': static_base_uri,
    u'format-number': format_number,
    }

