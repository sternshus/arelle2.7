u'''
Created on Dec 20, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
import datetime, re
from arelle import (XPathContext, ModelValue)
from arelle.FunctionUtil import (anytypeArg, atomicArg, stringArg, numericArg, qnameArg, nodeArg)
from arelle.XPathParser import ProgHeader
from math import isnan, fabs, isinf
from decimal import Decimal, InvalidOperation
    
class FORG0001(Exception):
    def __init__(self, message=None):
        self.message = message
        self.args = ( self.__repr__(), )
    def __repr__(self):
        return _(u"Exception: FORG0001, invalid constructor")

class FONS0004(Exception):
    def __init__(self, message=None):
        self.message = message
        self.args = ( self.__repr__(), )
    def __repr__(self):
        return _(u"Exception: FONS0004, no namespace found for prefix")

class xsFunctionNotAvailable(Exception):
    def __init__(self):
        self.args =  (_(u"xs function not available"),)
    def __repr__(self):
        return self.args[0]
    
def call(xc, p, localname, args):
    source = atomicArg(xc, p, args, 0, u"value?", missingArgFallback=() )
    if source == (): return source
    try:
        if localname not in xsFunctions: raise xsFunctionNotAvailable
        return xsFunctions[localname](xc, p, source)
    except (FORG0001, ValueError, TypeError), ex:
        if hasattr(ex, u"message") and ex.message:
            exMsg = u", " + ex.message
        else:
            exMsg = u""
        raise XPathContext.XPathException(p, u'err:FORG0001', 
                                          _(u'invalid cast from {0} to xs:{1}{2}').format(
                                            type(source).__name__,
                                            localname,
                                            exMsg))
    except xsFunctionNotAvailable:
        raise XPathContext.FunctionNotAvailable(u"xs:{0}".format(localname))
      
objtype = {
        #'untypedAtomic': untypedAtomic,
        u'dateTime':  ModelValue.DateTime,
        u'date': ModelValue.DateTime,
        u'time': ModelValue.Time,
        #'duration': duration,
        u'yearMonthDuration': ModelValue.YearMonthDuration,
        u'dayTimeDuration': ModelValue.DayTimeDuration,
        u'float': float,
        u'double': float,
        u'decimal': Decimal,
        u'integer': _INT,
        u'nonPositiveInteger': _INT,
        u'negativeInteger': _INT,
        u'long': _INT,
        u'int': _INT,
        u'short': _INT,
        u'byte': _INT,
        u'nonNegativeInteger': _INT,
        u'unsignedLong': _INT,
        u'unsignedInt': _INT,
        u'unsignedShort': _INT,
        u'unsignedByte': _INT,
        u'positiveInteger': _INT,
        #'gYearMonth': gYearMonth,
        #'gYear': gYear,
        #'gMonthDay': gMonthDay,
        #'gDay': gDay,
        #'gMonth': gMonth,
        u'string': unicode,
        u'normalizedString': unicode,
        u'token': unicode,
        u'language': unicode,
        u'NMTOKEN': unicode,
        u'Name': unicode,
        u'NCName': unicode,
        u'ID': unicode,
        u'IDREF': unicode,
        u'ENTITY': unicode,
        u'boolean': bool,
        #'base64Binary': byte,
        #'hexBinary': byte,
        u'anyURI': ModelValue.AnyURI,
        u'QName': ModelValue.QName,
        u'NOTATION': unicode,
      }
        
def untypedAtomic(xc, p, source):
    raise xsFunctionNotAvailable()
  
def dateTime(xc, p, source):
    if isinstance(source,datetime.datetime): return source
    return ModelValue.dateTime(source, type=ModelValue.DATETIME, castException=FORG0001)
  
def dateTimeInstantEnd(xc, p, source):
    if isinstance(source,datetime.datetime): return source  # true for either datetime.date or datetime.datetime
    return ModelValue.dateTime(source, addOneDay=True, type=ModelValue.DATETIME, castException=FORG0001)

def xbrliDateUnion(xc, p, source):
    if isinstance(source,datetime.date): return source  # true for either datetime.date or datetime.datetime
    return ModelValue.dateTime(source, type=ModelValue.DATEUNION, castException=FORG0001)
  
def date(xc, p, source):
    return ModelValue.dateTime(source, type=ModelValue.DATE, castException=FORG0001)
  
def time(xc, p, source):
    return ModelValue.time(source, castException=FORG0001)
  
def duration(xc, p, source):
    raise xsFunctionNotAvailable()
  
def yearMonthDuration(xc, p, source):
    return ModelValue.yearMonthDuration(source)
  
def dayTimeDuration(xc, p, source):
    return ModelValue.dayTimeDuration(source)
  
def xs_float(xc, p, source):
    try:
        return float(source)
    except ValueError:
        raise FORG0001
  
def double(xc, p, source):
    try:
        return float(source)
    except ValueError:
        raise FORG0001
  
def decimal(xc, p, source):
    try:
        return Decimal(source)
    except InvalidOperation:
        raise FORG0001
  
def integer(xc, p, source):
    try:
        return _INT(source)
    except ValueError:
        raise FORG0001
  
def nonPositiveInteger(xc, p, source):
    try:
        i = _INT(source)
        if i <= 0: return i
    except ValueError:
        pass
    raise FORG0001
  
def negativeInteger(xc, p, source):
    try:
        i = _INT(source)
        if i < 0: return i
    except ValueError:
        pass
    raise FORG0001
  
def long(xc, p, source):
    try:
        return _INT(source)
    except ValueError:
        raise FORG0001
  
def xs_int(xc, p, source):
    try:
        i = _INT(source)
        if i <= 2147483647 and i >= -2147483648: return i
    except ValueError:
        pass
    raise FORG0001
  
def short(xc, p, source):
    try:
        i = _INT(source)
        if i <= 32767 and i >= -32767: return i
    except ValueError:
        pass
    raise FORG0001
  
def byte(xc, p, source):
    try:
        i = _INT(source)
        if i <= 127 and i >= -128: return i
    except ValueError:
        pass
    raise FORG0001
  
def nonNegativeInteger(xc, p, source):
    try:
        i = _INT(source)
        if i >= 0: return i
    except ValueError:
        pass
    raise FORG0001
  
def unsignedLong(xc, p, source):
    try:
        i = _INT(source)
        if i >= 0: return i
    except ValueError:
        pass
    raise FORG0001
  
def unsignedInt(xc, p, source):
    try:
        i = _INT(source)
        if i <= 4294967295 and i >= 0: return i
    except ValueError:
        pass
    raise FORG0001
    
def unsignedShort(xc, p, source):
    try:
        i = _INT(source)
        if i <= 65535 and i >= 0: return i
    except ValueError:
        pass
    raise FORG0001
  
def unsignedByte(xc, p, source):
    try:
        i = _INT(source)
        if i <= 255 and i >= 0: return i
    except ValueError:
        pass
    raise FORG0001
  
def positiveInteger(xc, p, source):
    try:
        i = _INT(source)
        if i > 0: return i
    except ValueError:
        pass
    raise FORG0001
  
def gYearMonth(xc, p, source):
    raise xsFunctionNotAvailable()
  
def gYear(xc, p, source):
    raise xsFunctionNotAvailable()
  
def gMonthDay(xc, p, source):
    raise xsFunctionNotAvailable()
  
def gDay(xc, p, source):
    raise xsFunctionNotAvailable()
  
def gMonth(xc, p, source):
    raise xsFunctionNotAvailable()
  
def xsString(xc, p, source):
    if isinstance(source,bool):
        return u'true' if source else u'false'
    elif isinstance(source,float):
        if isnan(source):
            return u"NaN"
        elif isinf(source):
            return u"INF"
        u'''
        numMagnitude = fabs(source)
        if numMagnitude < 1000000 and numMagnitude > .000001:
            # don't want floating notation which python does for more than 4 decimal places
            s = 
        '''
        s = unicode(source)
        if s.endswith(u".0"):
            s = s[:-2]
        return s
    elif isinstance(source,Decimal):
        if isnan(source):
            return u"NaN"
        elif isinf(source):
            return u"INF"
        return unicode(source)
    elif isinstance(source,ModelValue.DateTime):
        return (u'{0:%Y-%m-%d}' if source.dateOnly else u'{0:%Y-%m-%dT%H:%M:%S}').format(source)
    return unicode(source)
  
def normalizedString(xc, p, source):
    return unicode(source)
  
tokenPattern = re.compile(ur"^\s*([-\.:\w]+)\s*$")
def token(xc, p, source):
    s = unicode(source)
    if tokenPattern.match(s): return s
    raise FORG0001
  
languagePattern = re.compile(u"[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*")
def language(xc, p, source):
    s = unicode(source)
    if languagePattern.match(s): return s
    raise FORG0001
  
def NMTOKEN(xc, p, source):
    raise xsFunctionNotAvailable()
  
def Name(xc, p, source):
    raise xsFunctionNotAvailable()
  
def NCName(xc, p, source):
    raise xsFunctionNotAvailable()
  
def ID(xc, p, source):
    raise xsFunctionNotAvailable()
  
def IDREF(xc, p, source):
    raise xsFunctionNotAvailable()
  
def ENTITY(xc, p, source):
    raise xsFunctionNotAvailable()
  
def boolean(xc, p, source):
    if isinstance(source,bool):
        return source
    elif isinstance(source, _NUM_TYPES):
        if source == 1:
            return True
        elif source == 0:
            return False
    elif isinstance(source,unicode):
        b = source.lower()
        if b in (u'true',u'yes'):
            return True
        elif b in (u'false',u'no'):
            return False
    raise FORG0001
  
def base64Binary(xc, p, source):
    raise xsFunctionNotAvailable()
  
def hexBinary(xc, p, source):
    raise xsFunctionNotAvailable()
  
def anyURI(xc, p, source):
    return ModelValue.anyURI(source)
  
def QName(xc, p, source):
    if isinstance(p, ProgHeader):
        element = p.element
    elif xc.progHeader:
        element = xc.progHeader.element
    else:
        element = xc.sourceElement
    return ModelValue.qname(element, source, castException=FORG0001, prefixException=FONS0004)
  
def NOTATION(xc, p, source):
    raise xsFunctionNotAvailable()

xsFunctions = {
    u'untypedAtomic': untypedAtomic,
    u'dateTime': dateTime,
    u'DATETIME_START': dateTime,
    u'DATETIME_INSTANT_END': dateTimeInstantEnd,
    u'XBRLI_DATEUNION': xbrliDateUnion,
    u'date': date,
    u'time': time,
    u'duration': duration,
    u'yearMonthDuration': yearMonthDuration,
    u'dayTimeDuration': dayTimeDuration,
    u'float': xs_float,
    u'double': double,
    u'decimal': decimal,
    u'integer': integer,
    u'nonPositiveInteger': nonPositiveInteger,
    u'negativeInteger': negativeInteger,
    u'long': long,
    u'int': xs_int,
    u'short': short,
    u'byte': byte,
    u'nonNegativeInteger': nonNegativeInteger,
    u'unsignedLong': unsignedLong,
    u'unsignedInt': unsignedInt,
    u'unsignedShort': unsignedShort,
    u'unsignedByte': unsignedByte,
    u'positiveInteger': positiveInteger,
    u'gYearMonth': gYearMonth,
    u'gYear': gYear,
    u'gMonthDay': gMonthDay,
    u'gDay': gDay,
    u'gMonth': gMonth,
    u'string': xsString,
    u'normalizedString': normalizedString,
    u'token': token,
    u'language': language,
    u'NMTOKEN': NMTOKEN,
    u'Name': Name,
    u'NCName': NCName,
    u'ID': ID,
    u'IDREF': IDREF,
    u'ENTITY': ENTITY,
    u'boolean': boolean,
    u'base64Binary': base64Binary,
    u'hexBinary': hexBinary,
    u'anyURI': anyURI,
    u'QName': QName,
    u'NOTATION': NOTATION,
    }
