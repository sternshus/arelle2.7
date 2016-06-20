u'''
Created on July 5, 2011

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
try:
    import regex as re
except ImportError:
    import re
from arelle.PluginManager import pluginClassMethods
from arelle import XPathContext
from datetime import datetime

class ixtFunctionNotAvailable(Exception):
    def __init__(self):
        self.args =  (_(u"ixt function not available"),)
    def __repr__(self):
        return self.args[0]
    
def call(xc, p, localname, args):
    try:
        if localname not in ixtFunctions: raise ixtFunctionNotAvailable
        if len(args) != 1: raise XPathContext.FunctionNumArgs()
        if len(args[0]) != 1: raise XPathContext.FunctionArgType(1,u"xs:string")
        return ixtFunctions[localname](unicode(args[0][0]))
    except ixtFunctionNotAvailable:
        raise XPathContext.FunctionNotAvailable(u"xfi:{0}".format(localname))

dateslashPattern = re.compile(ur"^\s*(\d+)/(\d+)/(\d+)\s*$")
datedotPattern = re.compile(ur"^\s*(\d+)\.(\d+)\.(\d+)\s*$")
daymonthPattern = re.compile(ur"^\s*([0-9]{1,2})[^0-9]+([0-9]{1,2})\s*$")
monthdayPattern = re.compile(ur"^\s*([0-9]{1,2})[^0-9]+([0-9]{1,2})[A-Za-z]*\s*$")
daymonthyearPattern = re.compile(ur"^\s*([0-9]{1,2})[^0-9]+([0-9]{1,2})[^0-9]+([0-9]{4}|[0-9]{1,2})\s*$")
monthdayyearPattern = re.compile(ur"^\s*([0-9]{1,2})[^0-9]+([0-9]{1,2})[^0-9]+([0-9]{4}|[0-9]{1,2})\s*$")

dateUsPattern = re.compile(ur"^\s*(\w+)\s+(\d+),\s+(\d+)\s*$")
dateEuPattern = re.compile(ur"^\s*(\d+)\s+(\w+)\s+(\d+)\s*$")
daymonthDkPattern = re.compile(ur"^\s*([0-9]{1,2})[^0-9]+(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)([A-Za-z]*)([.]*)\s*$", re.IGNORECASE)
daymonthEnPattern = re.compile(ur"^\s*([0-9]{1,2})[^0-9]+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s*$")
monthdayEnPattern = re.compile(ur"^\s*(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)[^0-9]+([0-9]{1,2})[A-Za-z]{0,2}\s*$")
daymonthyearDkPattern = re.compile(ur"^\s*([0-9]{1,2})[^0-9]+(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)([A-Za-z]*)([.]*)[^0-9]*([0-9]{4}|[0-9]{1,2})\s*$", re.IGNORECASE)
daymonthyearEnPattern = re.compile(ur"^\s*([0-9]{1,2})[^0-9]+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)[^0-9]+([0-9]{4}|[0-9]{1,2})\s*$")
daymonthyearInPattern = re.compile(ur"^\s*([0-9\u0966-\u096F]{1,2})\s([\u0966-\u096F]{2}|[^\s0-9\u0966-\u096F]+)\s([0-9\u0966-\u096F]{2}|[0-9\u0966-\u096F]{4})\s*$")
monthdayyearEnPattern = re.compile(ur"^\s*(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)[^0-9]+([0-9]+)[^0-9]+([0-9]{4}|[0-9]{1,2})\s*$")
monthyearDkPattern = re.compile(ur"^\s*(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)([A-Za-z]*)([.]*)[^0-9]*([0-9]{4}|[0-9]{1,2})\s*$", re.IGNORECASE)
monthyearEnPattern = re.compile(ur"^\s*(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)[^0-9]+([0-9]{1,2}|[0-9]{4})\s*$")
monthyearInPattern = re.compile(ur"^\s*([^\s0-9\u0966-\u096F]+)\s([0-9\u0966-\u096F]{4})\s*$")
yearmonthEnPattern = re.compile(ur"^\s*([0-9]{1,2}|[0-9]{4})[^0-9]+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s*$")

erayearmonthjpPattern = re.compile(u"^[\\s\u00A0]*(\u660E\u6CBB|\u660E|\u5927\u6B63|\u5927|\u662D\u548C|\u662D|\u5E73\u6210|\u5E73)[\\s\u00A0]*([0-9]{1,2}|\u5143)[\\s\u00A0]*\u5E74[\\s\u00A0]*([0-9]{1,2})[\\s\u00A0]*\u6708[\\s\u00A0]*$")
erayearmonthdayjpPattern = re.compile(u"^[\\s\u00A0]*(\u660E\u6CBB|\u660E|\u5927\u6B63|\u5927|\u662D\u548C|\u662D|\u5E73\u6210|\u5E73)[\\s\u00A0]*([0-9]{1,2}|\u5143)[\\s\u00A0]*\u5E74[\\s\u00A0]*([0-9]{1,2})[\\s\u00A0]*\u6708[\\s\u00A0]*([0-9]{1,2})[\\s\u00A0]*\u65E5[\\s\u00A0]*$")
yearmonthcjkPattern = re.compile(u"^[\\s\u00A0]*([0-9]{4}|[0-9]{1,2})[\\s\u00A0]*\u5E74[\\s\u00A0]*([0-9]{1,2})[\\s\u00A0]*\u6708\\s*$")
yearmonthdaycjkPattern = re.compile(u"^[\\s\u00A0]*([0-9]{4}|[0-9]{1,2})[\\s\u00A0]*\u5E74[\\s\u00A0]*([0-9]{1,2})[\\s\u00A0]*\u6708[\\s\u00A0]*([0-9]{1,2})[\\s\u00A0]*\u65E5[\\s\u00A0]*$")

monthyearPattern = re.compile(u"^[\\s\u00A0]*([0-9]{1,2})[^0-9]+([0-9]{4}|[0-9]{1,2})[\\s\u00A0]*$")
yearmonthdayPattern = re.compile(u"^[\\s\u00A0]*([0-9]{4}|[0-9]{1,2})[^0-9]+([0-9]{1,2})[^0-9]+([0-9]{1,2})[\\s\u00A0]*$")

zeroDashPattern = re.compile(ur"^\s*([-]|\u002D|\u002D|\u058A|\u05BE|\u2010|\u2011|\u2012|\u2013|\u2014|\u2015|\uFE58|\uFE63|\uFF0D)\s*$")
numDotDecimalPattern = re.compile(ur"^\s*[0-9]{1,3}([, \xA0]?[0-9]{3})*(\.[0-9]+)?\s*$")
numDotDecimalInPattern = re.compile(ur"^(([0-9]{1,2}[, \xA0])?([0-9]{2}[, \xA0])*[0-9]{3})([.][0-9]+)?$|^([0-9]+)([.][0-9]+)?$")
numCommaDecimalPattern = re.compile(ur"^\s*[0-9]{1,3}([. \xA0]?[0-9]{3})*(,[0-9]+)?\s*$")
numUnitDecimalPattern = re.compile(ur"^([0]|([1-9][0-9]{0,2}([.,\uFF0C\uFF0E]?[0-9]{3})*))[^0-9,.\uFF0C\uFF0E]+([0-9]{1,2})[^0-9,.\uFF0C\uFF0E]*$")
numUnitDecimalInPattern = re.compile(ur"^(([0-9]{1,2}[, \xA0])?([0-9]{2}[, \xA0])*[0-9]{3})([^0-9]+)([0-9]{1,2})([^0-9]*)$|^([0-9]+)([^0-9]+)([0-9]{1,2})([^0-9]*)$")

monthnumber = {u"January":1, u"February":2, u"March":3, u"April":4, u"May":5, u"June":6, 
               u"July":7, u"August":8, u"September":9, u"October":10, u"November":11, u"December":12, 
               u"Jan":1, u"Feb":2, u"Mar":3, u"Apr":4, u"May":5, u"Jun":6, 
               u"Jul":7, u"Aug":8, u"Sep":9, u"Oct":10, u"Nov":11, u"Dec":12, 
               u"JAN":1, u"FEB":2, u"MAR":3, u"APR":4, u"MAY":5, u"JUN":6, 
               u"JUL":7, u"AUG":8, u"SEP":9, u"OCT":10, u"NOV":12, u"DEC":13, 
               u"JANUARY":1, u"FEBRUARY":2, u"MARCH":3, u"APRIL":4, u"MAY":5, u"JUNE":6, 
               u"JULY":7, u"AUGUST":8, u"SEPTEMBER":9, u"OCTOBER":10, u"NOVEMBER":11, u"DECEMBER":12,
               # danish
               u"jan":1, u"feb":2, u"mar": 3, u"apr":4, u"maj":5, u"jun":6,
               u"jul":7, u"aug":8, u"sep":9, u"okt":10, u"nov":11, u"dec":12,
               }

maxDayInMo = {u"01": u"30", u"02": u"29", u"03": u"31", u"04": u"30", u"05": u"31", u"06": u"30",
              u"07": u"31", u"08": u"31", u"09": u"30", u"10": u"31", u"11": u"30", u"12":u"31",
              1: u"30", 2: u"29", 3: u"31", 4: u"30", 5: u"31", 6: u"30",
              7: u"31", 8: u"31", 9: u"30", 10: u"31", 11: u"30", 12:u"31"}
gLastMoDay = [31,28,31,30,31,30,31,31,30,31,30,31]

gregorianHindiMonthNumber = {
                u"\u091C\u0928\u0935\u0930\u0940": u"01",
                u"\u092B\u0930\u0935\u0930\u0940": u"02", 
                u"\u092E\u093E\u0930\u094D\u091A": u"03", 
                u"\u0905\u092A\u094D\u0930\u0948\u0932": u"04",
                u"\u092E\u0908": u"05", 
                u"\u091C\u0942\u0928": u"06",
                u"\u091C\u0941\u0932\u093E\u0908": u"07", 
                u"\u0905\u0917\u0938\u094D\u0924": u"08",
                u"\u0938\u093F\u0924\u0902\u092C\u0930": u"09",
                u"\u0905\u0915\u094D\u0924\u0942\u092C\u0930": u"10",
                u"\u0928\u0935\u092E\u094D\u092C\u0930": u"11",
                u"\u0926\u093F\u0938\u092E\u094D\u092C\u0930": u"12"
                }

sakaMonthNumber = {
                u"Chaitra":1, u"\u091A\u0948\u0924\u094D\u0930":1,
                u"Vaisakha":2, u"Vaishakh":2, u"Vai\u015B\u0101kha":2, u"\u0935\u0948\u0936\u093E\u0916":2, u"\u092C\u0948\u0938\u093E\u0916":2,
                u"Jyaishta":3, u"Jyaishtha":3, u"Jyaistha":3, u"Jye\u1E63\u1E6Dha":3, u"\u091C\u094D\u092F\u0947\u0937\u094D\u0920":3,
                u"Asadha":4, u"Ashadha":4, u"\u0100\u1E63\u0101\u1E0Dha":4, u"\u0906\u0937\u093E\u0922":4, u"\u0906\u0937\u093E\u0922\u093C":4,
                u"Sravana":5, u"Shravana":5, u"\u015Ar\u0101va\u1E47a":5, u"\u0936\u094D\u0930\u093E\u0935\u0923":5, u"\u0938\u093E\u0935\u0928":5,
                u"Bhadra":6, u"Bhadrapad":6, u"Bh\u0101drapada":6, u"Bh\u0101dra":6, u"Pro\u1E63\u1E6Dhapada":6, u"\u092D\u093E\u0926\u094D\u0930\u092A\u0926":6, u"\u092D\u093E\u0926\u094B":6,
                u"Aswina":7, u"Ashwin":7, u"Asvina":7, u"\u0100\u015Bvina":7, u"\u0906\u0936\u094D\u0935\u093F\u0928":7, 
                u"Kartiak":8, u"Kartik":8, u"Kartika":8, u"K\u0101rtika":8, u"\u0915\u093E\u0930\u094D\u0924\u093F\u0915":8, 
                u"Agrahayana":9,u"Agrah\u0101ya\u1E47a":9,u"Margashirsha":9, u"M\u0101rga\u015B\u012Br\u1E63a":9, u"\u092E\u093E\u0930\u094D\u0917\u0936\u0940\u0930\u094D\u0937":9, u"\u0905\u0917\u0939\u0928":9,
                u"Pausa":10, u"Pausha":10, u"Pau\u1E63a":10, u"\u092A\u094C\u0937":10,
                u"Magha":11, u"Magh":11, u"M\u0101gha":11, u"\u092E\u093E\u0918":11,
                u"Phalguna":12, u"Phalgun":12, u"Ph\u0101lguna":12, u"\u092B\u093E\u0932\u094D\u0917\u0941\u0928":12,
                }
sakaMonthPattern = re.compile(ur"(C\S*ait|\u091A\u0948\u0924\u094D\u0930)|"
                              ur"(Vai|\u0935\u0948\u0936\u093E\u0916|\u092C\u0948\u0938\u093E\u0916)|"
                              ur"(Jy|\u091C\u094D\u092F\u0947\u0937\u094D\u0920)|"
                              ur"(dha|\u1E0Dha|\u0906\u0937\u093E\u0922|\u0906\u0937\u093E\u0922\u093C)|"
                              ur"(vana|\u015Ar\u0101va\u1E47a|\u0936\u094D\u0930\u093E\u0935\u0923|\u0938\u093E\u0935\u0928)|"
                              ur"(Bh\S+dra|Pro\u1E63\u1E6Dhapada|\u092D\u093E\u0926\u094D\u0930\u092A\u0926|\u092D\u093E\u0926\u094B)|"
                              ur"(in|\u0906\u0936\u094D\u0935\u093F\u0928)|"
                              ur"(K\S+rti|\u0915\u093E\u0930\u094D\u0924\u093F\u0915)|"
                              ur"(M\S+rga|Agra|\u092E\u093E\u0930\u094D\u0917\u0936\u0940\u0930\u094D\u0937|\u0905\u0917\u0939\u0928)|"
                              ur"(Pau|\u092A\u094C\u0937)|"
                              ur"(M\S+gh|\u092E\u093E\u0918)|"
                              ur"(Ph\S+lg|\u092B\u093E\u0932\u094D\u0917\u0941\u0928)")
sakaMonthLength = (30,31,31,31,31,31,30,30,30,30,30,30) # Chaitra has 31 days in Gregorian leap year
sakaMonthOffset = ((3,22,0),(4,21,0),(5,22,0),(6,22,0),(7,23,0),(8,23,0),(9,23,0),(10,23,0),(11,22,0),(12,22,0),(1,21,1),(2,20,1))

# common helper functions
def checkDate(y,m,d):
    try:
        datetime(_INT(y), _INT(m), _INT(d))
        return True
    except (ValueError):
        return False

def z2(arg):   # zero pad to 2 digits
    if len(arg) == 1:
        return u'0' + arg
    return arg

def yr(arg):   # zero pad to 4 digits
    if len(arg) == 1:
        return u'200' + arg
    elif len(arg) == 2:
        return u'20' + arg
    return arg

def yrin(arg, _mo, _day):   # zero pad to 4 digits
    if len(arg) == 2:
        if arg > u'21' or (arg == u'21' and _mo >= 10 and _day >= 11):
            return u'19' + arg
        else:
            return u'20' + arg
    return arg

def devanagariDigitsToNormal(devanagariDigits):
    normal = u''
    for d in devanagariDigits:
        if u'\u0966' <= d <= u'\u096F':
            normal += unichr( ord(d) - 0x0966 + ord(u'0') )
        else:
            normal += d
    return normal

def jpDigitsToNormal(jpDigits):
    normal = u''
    for d in jpDigits:
        if u'\uFF10' <= d <= u'\uFF19':
            normal += unichr( ord(d) - 0xFF10 + ord(u'0') )
        else:
            normal += d
    return normal

def sakaToGregorian(sYr, sMo, sDay): # replacement of plug-in sakaCalendar.py which is LGPL-v3 licensed
    gYr = sYr + 78  # offset from Saka to Gregorian year
    sStartsInLeapYr = gYr % 4 == 0 and (not gYr % 100 == 0 or gYr % 400 == 0) # Saka yr starts in leap yr
    if gYr < 0:
        raise ValueError(_(u"Saka calendar year not supported: {0} {1} {2} "), sYr, sMo, sDay)
    if  sMo < 1 or sMo > 12:
        raise ValueError(_(u"Saka calendar month error: {0} {1} {2} "), sYr, sMo, sDay)
    sMoLength = sakaMonthLength[sMo - 1]
    if sStartsInLeapYr and sMo == 1:
        sMoLength += 1 # Chaitra has 1 extra day when starting in gregorian leap years
    if sDay < 1 or sDay > sMoLength: 
        raise ValueError(_(u"Saka calendar day error: {0} {1} {2} "), sYr, sMo, sDay)
    gMo, gDayOffset, gYrOffset = sakaMonthOffset[sMo - 1] # offset Saka to Gregorian by Saka month
    if sStartsInLeapYr and sMo == 1:
        gDayOffset -= 1 # Chaitra starts 1 day earlier when starting in Gregorian leap years
    gYr += gYrOffset # later Saka months offset into next Gregorian year
    gMoLength = gLastMoDay[gMo - 1] # month length (days in month)
    if gMo == 2 and gYr % 4 == 0 and (not gYr % 100 == 0 or gYr % 400 == 0): # does Phalguna (Feb) end in a Gregorian leap year?
        gMoLength += 1 # Phalguna (Feb) is in a Gregorian leap year (Feb has 29 days)
    gDay = gDayOffset + sDay - 1
    if gDay > gMoLength: # overflow from Gregorial month of start of Saka month to next Gregorian month
        gDay -= gMoLength
        gMo += 1
        if gMo == 13:  # overflow from Gregorian year of start of Saka year to following Gregorian year
            gMo = 1
            gYr += 1
    return (gYr, gMo, gDay)

# see: http://www.i18nguy.com/l10n/emperor-date.html        
eraStart = {u'\u5E73\u6210': 1988, 
            u'\u5E73': 1988,
            u'\u660E\u6CBB': 1867,
            u'\u660E': 1867,
            u'\u5927\u6B63': 1911,
            u'\u5927': 1911,
            u'\u662D\u548C': 1925,
            u'\u662D': 1925
            }

def eraYear(era,yr):
    return eraStart[era] + (1 if yr == u'\u5143' else _INT(yr))

# transforms    

def booleanfalse(arg):
    return u'false'
    
def booleantrue(arg):
    return u'true'

def dateslashus(arg):
    m = dateslashPattern.match(arg)
    if m and m.lastindex == 3:
        return u"{0}-{1}-{2}".format(yr(m.group(3)), z2(m.group(1)), z2(m.group(2)))
    raise XPathContext.FunctionArgType(1,u"xs:date")
    
def dateslasheu(arg):
    m = dateslashPattern.match(arg)
    if m and m.lastindex == 3:
        return u"{0}-{1}-{2}".format(yr(m.group(3)), z2(m.group(2)), z2(m.group(1)))
    raise XPathContext.FunctionArgType(1,u"xs:date")
    
def datedotus(arg):
    m = datedotPattern.match(arg)
    if m and m.lastindex == 3:
        return u"{0}-{1}-{2}".format(yr(m.group(3)), z2(m.group(1)), z2(m.group(2)))
    raise XPathContext.FunctionArgType(1,u"xs:date")
    
def datedoteu(arg):
    m = datedotPattern.match(arg)
    if m and m.lastindex == 3:
        return u"{0}-{1}-{2}".format(yr(m.group(3)), z2(m.group(2)), z2(m.group(1)))
    raise XPathContext.FunctionArgType(1,u"xs:date")
    
def datelongus(arg):
    m = dateUsPattern.match(arg)
    if m and m.lastindex == 3:
        return u"{0}-{1:02}-{2}".format(yr(m.group(3)), monthnumber[m.group(1)], z2(m.group(2)))
    raise XPathContext.FunctionArgType(1,u"xs:date")
    
def datelongeu(arg):
    m = dateEuPattern.match(arg)
    if m and m.lastindex == 3:
        return u"{0}-{1:02}-{2}".format(yr(m.group(3)), monthnumber[m.group(2)], z2(m.group(1)))
    raise XPathContext.FunctionArgType(1,u"xs:date")
    
def datedaymonth(arg):
    m = daymonthPattern.match(arg)
    if m and m.lastindex == 2:
        mo = z2(m.group(2))
        day = z2(m.group(1))
        if u"01" <= day <= maxDayInMo.get(mo, u"00"): 
            return u"--{0}-{1}".format(mo, day)
    raise XPathContext.FunctionArgType(1,u"xs:gMonthDay")
    
def datemonthday(arg):
    m = monthdayPattern.match(arg)
    if m and m.lastindex == 2:
        mo = z2(m.group(1))
        day = z2(m.group(2))
        if u"01" <= day <= maxDayInMo.get(mo, u"00"): 
            return u"--{0}-{1}".format(mo, day)
    raise XPathContext.FunctionArgType(1,u"xs:gMonthDay")
    
def datedaymonthdk(arg):
    m = daymonthDkPattern.match(arg)
    if m and m.lastindex == 4:
        day = z2(m.group(1))
        mon3 = m.group(2).lower()
        mon3 = m.group(2).lower()
        monEnd = m.group(3)
        monPer = m.group(4)
        if (mon3 in monthnumber):
            mo = monthnumber[mon3]
            if (((not monEnd and not monPer) or
                 (not monEnd and monPer) or
                 (monEnd and not monPer)) and
                u"01" <= day <= maxDayInMo.get(mo, u"00")):
                return u"--{0:02}-{1}".format(mo, day)
    raise XPathContext.FunctionArgType(1,u"xs:gMonthDay")
    
def datedaymonthen(arg):
    m = daymonthEnPattern.match(arg)
    if m and m.lastindex == 2:
        _mo = monthnumber[m.group(2)]
        _day = z2(m.group(1))
        if u"01" <= _day <= maxDayInMo.get(_mo, u"00"): 
            return u"--{0:02}-{1}".format(_mo, _day)
    raise XPathContext.FunctionArgType(1,u"xs:gMonthDay")
    
def datemonthdayen(arg):
    m = monthdayEnPattern.match(arg)
    if m and m.lastindex == 2:
        _mo = monthnumber[m.group(1)]
        _day = z2(m.group(2))
        if u"01" <= _day <= maxDayInMo.get(_mo, u"00"): 
            return u"--{0:02}-{1}".format(_mo, _day)
    raise XPathContext.FunctionArgType(1,u"xs:gMonthDay")

def datedaymonthyear(arg):
    m = daymonthyearPattern.match(arg)
    if m and m.lastindex == 3 and checkDate(yr(m.group(3)), m.group(2), m.group(1)):
        return u"{0}-{1}-{2}".format(yr(m.group(3)), z2(m.group(2)), z2(m.group(1)))
    raise XPathContext.FunctionArgType(1,u"xs:date")
    
def datemonthdayyear(arg): 
    m = monthdayyearPattern.match(arg)
    if m and m.lastindex == 3:
        _yr = yr(m.group(3))
        _mo = z2(m.group(1))
        _day = z2(m.group(2))
        if checkDate(_yr, _mo, _day):
            return u"{0}-{1}-{2}".format(_yr, _mo, _day)
    raise XPathContext.FunctionArgType(1,u"xs:date")
    
def datemonthyear(arg):
    m = monthyearPattern.match(arg) # "(M)M*(Y)Y(YY)", with non-numeric separator,
    if m and m.lastindex == 2:
        _mo = z2(m.group(1))
        if u"01" <= _mo <= u"12":
            return u"{0}-{1:2}".format(yr(m.group(2)), _mo)
    raise XPathContext.FunctionArgType(1,u"xs:gYearMonth")
    
def datemonthyeardk(arg):
    m = monthyearDkPattern.match(arg)
    if m and m.lastindex == 4:
        mon3 = m.group(1).lower()
        monEnd = m.group(2)
        monPer = m.group(3)
        if mon3 in monthnumber and ((not monEnd and not monPer) or
                                    (not monEnd and monPer) or
                                    (monEnd and not monPer)):
            return u"{0}-{1:02}".format(yr(m.group(4)), monthnumber[mon3])
    raise XPathContext.FunctionArgType(1,u"xs:gYearMonth")
    
def datemonthyearen(arg):
    m = monthyearEnPattern.match(arg)
    if m and m.lastindex == 2:
        return u"{0}-{1:02}".format(yr(m.group(2)), monthnumber[m.group(1)])
    raise XPathContext.FunctionArgType(1,u"xs:gYearMonth")
    
def datemonthyearin(arg):
    m = monthyearInPattern.match(arg)
    try:
        return u"{0}-{1}".format(yr(devanagariDigitsToNormal(m.group(2))), 
                                   gregorianHindiMonthNumber[m.group(1)])
    except (AttributeError, IndexError, KeyError):
        pass
    raise XPathContext.FunctionArgType(1,u"xs:gYearMonth")
    
def dateyearmonthen(arg):
    m = yearmonthEnPattern.match(arg)
    if m and m.lastindex == 2:
        return u"{0}-{1:02}".format(yr(m.group(1)), monthnumber[m.group(2)])
    raise XPathContext.FunctionArgType(1,u"xs:gYearMonth")

def datedaymonthyeardk(arg):
    m = daymonthyearDkPattern.match(arg)
    if m and m.lastindex == 5:
        _yr = yr(m.group(5))
        _day = z2(m.group(1))
        _mon3 = m.group(2).lower()
        _monEnd = m.group(3)
        _monPer = m.group(4)
        if _mon3 in monthnumber and ((not _monEnd and not _monPer) or
                                     (not _monEnd and _monPer) or
                                     (_monEnd and not _monPer)):
            _mo = monthnumber[_mon3]
            if checkDate(_yr, _mo, _day):
                return u"{0}-{1:02}-{2}".format(_yr, _mo, _day)
    raise XPathContext.FunctionArgType(1,u"xs:date")

def datedaymonthyearen(arg):
    m = daymonthyearEnPattern.match(arg)
    if m and m.lastindex == 3:
        _yr = yr(m.group(3))
        _mo = monthnumber[m.group(2)]
        _day = z2(m.group(1))
        if checkDate(_yr, _mo, _day):
            return u"{0}-{1:02}-{2}".format(_yr, _mo, _day)
    raise XPathContext.FunctionArgType(1,u"xs:date")

def datedaymonthyearin(arg):
    m = daymonthyearInPattern.match(arg)
    try:
        _yr = yr(devanagariDigitsToNormal(m.group(3)))
        _mo = gregorianHindiMonthNumber.get(m.group(2), devanagariDigitsToNormal(m.group(2)))
        _day = z2(devanagariDigitsToNormal(m.group(1)))
        if checkDate(_yr, _mo, _day):
            return u"{0}-{1}-{2}".format(_yr, _mo, _day)
    except (AttributeError, IndexError, KeyError):
        pass
    raise XPathContext.FunctionArgType(1,u"xs:date")

def calindaymonthyear(arg):
    m = daymonthyearInPattern.match(arg)
    try:
        # Transformation registry 3 requires use of pattern comparisons instead of exact transliterations
        #_mo = _INT(sakaMonthNumber[m.group(2)])
        # pattern approach
        _mo = sakaMonthPattern.search(m.group(2)).lastindex
        _day = _INT(devanagariDigitsToNormal(m.group(1)))
        _yr = _INT(devanagariDigitsToNormal(yrin(m.group(3), _mo, _day)))
        #sakaDate = [_yr, _mo, _day]
        #for pluginMethod in pluginClassMethods("SakaCalendar.ToGregorian"):  # LGPLv3 plugin (moved to examples/plugin)
        #    gregorianDate = pluginMethod(sakaDate)
        #    return "{0}-{1:02}-{2:02}".format(gregorianDate[0], gregorianDate[1], gregorianDate[2])
        #raise NotImplementedError (_("ixt:calindaymonthyear requires plugin sakaCalendar.py, please install plugin.  "))
        gregorianDate = sakaToGregorian(_yr, _mo, _day) # native implementation for Arelle
        return u"{0}-{1:02}-{2:02}".format(gregorianDate[0], gregorianDate[1], gregorianDate[2])
    except (AttributeError, IndexError, KeyError, ValueError):
        pass
    raise XPathContext.FunctionArgType(1,u"xs:date")

def datemonthdayyearen(arg):
    m = monthdayyearEnPattern.match(arg)
    if m and m.lastindex == 3:
        _yr = yr(m.group(3))
        _mo = monthnumber[m.group(1)]
        _day = z2(m.group(2))
        if checkDate(_yr, _mo, _day):
            return u"{0}-{1:02}-{2}".format(_yr, _mo, _day)
    raise XPathContext.FunctionArgType(1,u"xs:date")
    
def dateerayearmonthdayjp(arg):
    m = erayearmonthdayjpPattern.match(jpDigitsToNormal(arg))
    if m and m.lastindex == 4:
        _yr = eraYear(m.group(1), m.group(2))
        _mo = z2(m.group(3))
        _day = z2(m.group(4))
        if checkDate(_yr, _mo, _day):
            return u"{0}-{1}-{2}".format(_yr, _mo, _day)
    raise XPathContext.FunctionArgType(1,u"xs:date")

def dateyearmonthday(arg):
    m = yearmonthdayPattern.match(jpDigitsToNormal(arg)) # (Y)Y(YY)*MM*DD with kangu full-width numerals
    if m and m.lastindex == 3:
        _yr = yr(m.group(1))
        _mo = z2(m.group(2))
        _day = z2(m.group(3))
        if checkDate(_yr, _mo, _day):
            return u"{0}-{1}-{2}".format(_yr, _mo, _day)
    raise XPathContext.FunctionArgType(1,u"xs:date")

def dateerayearmonthjp(arg):
    m = erayearmonthjpPattern.match(jpDigitsToNormal(arg))
    if m and m.lastindex == 3:
        _yr = eraYear(m.group(1), m.group(2))
        _mo = z2(m.group(3))
        if u"01" <= _mo <= u"12":
            return u"{0}-{1}".format(_yr, _mo)
    raise XPathContext.FunctionArgType(1,u"xs:gYearMonth")

def dateyearmonthdaycjk(arg):
    m = yearmonthdaycjkPattern.match(jpDigitsToNormal(arg))
    if m and m.lastindex == 3:
        _yr = yr(m.group(1))
        _mo = z2(m.group(2))
        _day = z2(m.group(3))
        if checkDate(_yr, _mo, _day):
            return u"{0}-{1}-{2}".format(_yr, _mo, _day)
    raise XPathContext.FunctionArgType(1,u"xs:date")

def dateyearmonthcjk(arg):
    m = yearmonthcjkPattern.match(jpDigitsToNormal(arg))
    if m and m.lastindex == 2:
        _mo =  z2(m.group(2))
        if u"01" <= _mo <= u"12":
            return u"{0}-{1}".format(yr(m.group(1)), _mo)
    raise XPathContext.FunctionArgType(1,u"xs:date")

def nocontent(arg):
    return u''

def numcommadecimal(arg):
    if numCommaDecimalPattern.match(arg):
        return arg.replace(u'.', u'').replace(u',', u'.').replace(u' ', u'').replace(u'\u00A0', u'')
    raise XPathContext.FunctionArgType(1,u"ixt:nonNegativeDecimalType")

def numcommadot(arg):
    return arg.replace(u',', u'')

def numdash(arg):
    return arg.replace(u'-',u'0')

def numspacedot(arg):
    return arg.replace(u' ', u'')

def numdotcomma(arg):
    return arg.replace(u'.', u'').replace(u',', u'.')

def numspacecomma(arg):
    return arg.replace(u' ', u'').replace(u',', u'.')

def zerodash(arg):
    if zeroDashPattern.match(arg):
        return u'0'
    raise XPathContext.FunctionArgType(1,u"ixt:zerodashType")

def numdotdecimal(arg):
    if numDotDecimalPattern.match(arg):
        return arg.replace(u',', u'').replace(u' ', u'').replace(u'\u00A0', u'')
    raise XPathContext.FunctionArgType(1,u"ixt:numdotdecimalType")

def numdotdecimalin(arg):
    m = numDotDecimalInPattern.match(arg)
    if m:
        m2 = [g for g in m.groups() if g is not None]
        if m2[-1].startswith(u"."):
            fract = m2[-1]
        else:
            fract = u""
        return m2[0].replace(u',',u'').replace(u' ',u'').replace(u'\xa0',u'') + fract
    raise XPathContext.FunctionArgType(1,u"ixt:numdotdecimalinType")

def numunitdecimal(arg):
    # remove comma (normal), full-width comma, and stops (periods)
    m = numUnitDecimalPattern.match(jpDigitsToNormal(arg))
    if m and m.lastindex > 1:
        return m.group(1).replace(u'.',u'').replace(u',',u'').replace(u'\uFF0C',u'').replace(u'\uFF0E',u'') + u'.' + z2(m.group(m.lastindex))
    raise XPathContext.FunctionArgType(1,u"ixt:nonNegativeDecimalType")

def numunitdecimalin(arg):
    m = numUnitDecimalInPattern.match(arg)
    if m:
        m2 = [g for g in m.groups() if g is not None]
        return m2[0].replace(u',',u'').replace(u' ',u'').replace(u'\xa0',u'') + u'.' + z2(m2[-2])
    raise XPathContext.FunctionArgType(1,u"ixt:numunitdecimalinType")
    
ixtFunctions = {
                
    # 3010-04-20 functions
    u'dateslashus': dateslashus,
    u'dateslasheu': dateslasheu,
    u'datedotus': datedotus,
    u'datedoteu': datedoteu,
    u'datelongus': datelongus,
    u'dateshortus': datelongus,
    u'datelongeu': datelongeu,
    u'dateshorteu': datelongeu,
    u'datelonguk': datelongeu,
    u'dateshortuk': datelongeu,
    u'numcommadot': numcommadot,
    u'numdash': numdash,
    u'numspacedot': numspacedot,
    u'numdotcomma': numdotcomma,
    u'numcomma': numdotcomma,
    u'numspacecomma': numspacecomma,    
                           
    # 2011-07-31 functions
    u'booleanfalse': booleanfalse,
    u'booleantrue': booleantrue,
    u'datedaymonth': datedaymonth,
    u'datedaymonthen': datedaymonthen,
    u'datedaymonthyear': datedaymonthyear,
    u'datedaymonthyearen': datedaymonthyearen,
    u'dateerayearmonthdayjp': dateerayearmonthdayjp,
    u'dateerayearmonthjp': dateerayearmonthjp,
    u'datemonthday': datemonthday,
    u'datemonthdayen': datemonthdayen,
    u'datemonthdayyear': datemonthdayyear,
    u'datemonthdayyearen': datemonthdayyearen,
    u'datemonthyearen': datemonthyearen,
    u'dateyearmonthdaycjk': dateyearmonthdaycjk,
    u'dateyearmonthen': dateyearmonthen,
    u'dateyearmonthcjk': dateyearmonthcjk,
    u'nocontent': nocontent,
    u'numcommadecimal': numcommadecimal,
    u'zerodash': zerodash,
    u'numdotdecimal': numdotdecimal,
    u'numunitdecimal': numunitdecimal,
    
    # transformation registry v-3 functions
    
    # same as v2: 'booleanfalse': booleanfalse,
    # same as v2: 'booleantrue': booleantrue,
    u'calindaymonthyear': calindaymonthyear, # TBD: calindaymonthyear,
    #'calinmonthyear': nocontent, # TBD: calinmonthyear,
    # same as v2: 'datedaymonth': datedaymonth,
    u'datedaymonthdk': datedaymonthdk,
    # same as v2: 'datedaymonthen': datedaymonthen,
    # same as v2: 'datedaymonthyear': datedaymonthyear,
    u'datedaymonthyeardk': datedaymonthyeardk,
    # same as v2: 'datedaymonthyearen': datedaymonthyearen,
    u'datedaymonthyearin': datedaymonthyearin,
    # same as v2: 'dateerayearmonthdayjp': dateerayearmonthdayjp,
    # same as v2: 'dateerayearmonthjp': dateerayearmonthjp,
    # same as v2: 'datemonthday': datemonthday,
    # same as v2: 'datemonthdayen': datemonthdayen,
    # same as v2: 'datemonthdayyear': datemonthdayyear, 
    # same as v2: 'datemonthdayyearen': datemonthdayyearen,
    u'datemonthyear': datemonthyear,
    u'datemonthyeardk': datemonthyeardk,
    # same as v2: 'datemonthyearen': datemonthyearen,
    u'datemonthyearin': datemonthyearin,
    # same as v2: 'dateyearmonthcjk': dateyearmonthcjk,
    u'dateyearmonthday': dateyearmonthday, # (Y)Y(YY)*MM*DD allowing kanji full-width numerals
    # same as v2: 'dateyearmonthdaycjk': dateyearmonthdaycjk,
    # same as v2: 'dateyearmonthen': dateyearmonthen,
    # same as v2: 'nocontent': nocontent,
    # same as v2: 'numcommadecimal': numcommadecimal,
    # same as v2: 'numdotdecimal': numdotdecimal,
    u'numdotdecimalin': numdotdecimalin,
    # same as v2: 'numunitdecimal': numunitdecimal,
    u'numunitdecimalin': numunitdecimalin,
    # same as v2: 'zerodash': zerodash,
}

deprecatedNamespaceURI = u'http://www.xbrl.org/2008/inlineXBRL/transformation' # the CR/PR pre-REC namespace

ixtNamespaceURIs = set([
    u'http://www.xbrl.org/inlineXBRL/transformation/2010-04-20', # transformation registry v1
    u'http://www.xbrl.org/inlineXBRL/transformation/2011-07-31', # transformation registry v2
    u'http://www.xbrl.org/inlineXBRL/transformation/2014-10-15', # transformation registry v3
    u'http://www.xbrl.org/2008/inlineXBRL/transformation'])
