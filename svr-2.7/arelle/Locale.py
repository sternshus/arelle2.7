u'''
Created on Jan 26, 2011

This module is a local copy of python locale in order to allow
passing in localconv as an argument to functions without affecting
system-wide settings.  (The system settings can remain in 'C' locale.)

@author: Mark V Systems Limited (incorporating python locale module code)
(original python authors: Martin von Loewis, improved by Georg Brandl)

(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
import sys, subprocess
from itertools import imap
try:
    import regex as re
except ImportError:
    import re
import collections
import unicodedata

CHAR_MAX = 127
LC_ALL = 6
LC_COLLATE = 3
LC_CTYPE = 0
LC_MESSAGES = 5
LC_MONETARY = 4
LC_NUMERIC = 1
LC_TIME = 2

C_LOCALE = None # culture-invariant locale

def getUserLocale(localeCode=u''):
    # get system localeconv and reset system back to default
    import locale
    global C_LOCALE
    conv = None
    if sys.platform == u"darwin" and not localeCode:
        # possibly this MacOS bug: http://bugs.python.org/issue18378
        # macOS won't provide right default code for english-european culture combinations
        localeQueryResult = subprocess.getstatusoutput(u"defaults read -g AppleLocale")  # MacOS only
        if localeQueryResult[0] == 0 and u'_' in localeQueryResult[1]: # successful
            localeCode = localeQueryResult[1]
    try:
        locale.setlocale(locale.LC_ALL, _STR_8BIT(localeCode))  # str needed for 3to2 2.7 python to work
        conv = locale.localeconv()
    except locale.Error:
        if sys.platform == u"darwin":
            # possibly this MacOS bug: http://bugs.python.org/issue18378
            # the fix to this bug will loose the monetary/number configuration with en_BE, en_FR, etc
            # so use this alternative which gets the right culture code for numbers even if english default language
            localeCulture = u'-' + localeCode[3:]
            # find culture (for any language) in available locales
            for availableLocale in availableLocales():
                if len(availableLocale) >= 5 and localeCulture in availableLocale:
                    try:
                        locale.setlocale(locale.LC_ALL, availableLocale.replace(u'-',u'_'))
                        conv = locale.localeconv() # should get monetary and numeric codes
                        break
                    except locale.Error:
                        pass # this one didn't work
    locale.setlocale(locale.LC_ALL, _STR_8BIT(u'C'))  # str needed for 3to2 2.7 python to work
    if conv is None: # some other issue prevents getting culture code, use 'C' defaults (no thousands sep, no currency, etc)
        conv = locale.localeconv() # use 'C' environment, e.g., en_US
    if C_LOCALE is None: # load culture-invariant C locale
        C_LOCALE = locale.localeconv()
    return conv

def getLanguageCode():
    if sys.platform == u"darwin":
        # possibly this MacOS bug: http://bugs.python.org/issue18378
        # even when fixed, macOS won't provide right default code for some language-culture combinations
        localeQueryResult = subprocess.getstatusoutput(u"defaults read -g AppleLocale")  # MacOS only
        if localeQueryResult[0] == 0 and localeQueryResult[1]: # successful
            return localeQueryResult[1][:5].replace(u"_",u"-")
    import locale
    try:
        return locale.getdefaultlocale()[0].replace(u"_",u"-")
    except (AttributeError, ValueError): #language code and encoding may be None if their values cannot be determined.
        return u"en"    

def getLanguageCodes(lang=None):
    if lang is None:
        lang = getLanguageCode()
    # allow searching on the lang with country part, either python or standard form, or just language
    return [lang, lang.replace(u"-",u"_"), lang.partition(u"-")[0]]


iso3region = {
u"AU": u"aus",
u"AT": u"aut",
u"BE": u"bel",
u"BR": u"bra",
u"CA": u"can",
u"CN": u"chn",
u"CZ": u"cze",
u"DA": u"dnk",
u"FN": u"fin",
u"FR": u"fra",
u"DE": u"deu",
u"GR": u"grc",
u"HK": u"hkg",
u"HU": u"hun",
u"IS": u"isl",
u"IE": u"irl",
u"IT": u"ita",
u"JA": u"jpn",
u"KO": u"kor",
u"MX": u"mex",
u"NL": u"nld",
u"NZ": u"nzl",
u"NO": u"nor",
u"PL": u"pol",
u"PT": u"prt",
u"RU": u"rus",
u"SG": u"sgp",
u"SL": u"svk",
u"ES": u"esp",
u"SV": u"swe",
u"CH": u"che",
u"TW": u"twn",
u"TR": u"tur",
u"UK": u"gbr",
u"US": u"usa"}

_availableLocales = None
def availableLocales():
    global _availableLocales
    if _availableLocales is not None:
        return _availableLocales
    else:
        localeQueryResult = subprocess.getstatusoutput(u"locale -a")  # Mac and Unix only
        if localeQueryResult[0] == 0: # successful
            _availableLocales = set(locale.partition(u".")[0].replace(u"_", u"-")
                                    for locale in localeQueryResult[1].split(u"\n"))
        else:
            _availableLocales = set()
        return _availableLocales

_languageCodes = None
def languageCodes():  # dynamically initialize after gettext is loaded
    global _languageCodes
    if _languageCodes is not None:
        return _languageCodes
    else:        
        _languageCodes = { # language name (in English), code, and setlocale string which works in windows
            _(u"Afrikaans (South Africa)"): u"af-ZA afrikaans",
            _(u"Albanian (Albania)"): u"sq-AL albanian",
            _(u"Arabic (Algeria)"): u"ar-DZ arb_algeria",
            _(u"Arabic (Bahrain)"): u"ar-BH arabic_bahrain",
            _(u"Arabic (Egypt)"): u"ar-EG arb_egy",
            _(u"Arabic (Iraq)"): u"ar-IQ arb_irq",
            _(u"Arabic (Jordan)"): u"ar-JO arb_jor",
            _(u"Arabic (Kuwait)"): u"ar-KW arb_kwt",
            _(u"Arabic (Lebanon)"): u"ar-LB arb_lbn",
            _(u"Arabic (Libya)"): u"ar-LY arb_lby",
            _(u"Arabic (Morocco)"): u"ar-MA arb_morocco",
            _(u"Arabic (Oman)"): u"ar-OM arb_omn",
            _(u"Arabic (Qatar)"): u"ar-QA arabic_qatar",
            _(u"Arabic (Saudi Arabia)"): u"ar-SA arb_sau",
            _(u"Arabic (Syria)"): u"ar-SY arb_syr",
            _(u"Arabic (Tunisia)"): u"ar-TN arb_tunisia",
            _(u"Arabic (U.A.E.)"): u"ar-AE arb_are",
            _(u"Arabic (Yemen)"): u"ar-YE arb_yem",
            _(u"Basque (Spain)"): u"eu-ES basque",
            _(u"Bulgarian (Bulgaria)"): u"bg-BG bulgarian",
            _(u"Belarusian (Belarus)"): u"be-BY belarusian",
            _(u"Catalan (Spain)"): u"ca-ES catalan",
            _(u"Chinese (PRC)"): u"zh-CN chs",
            _(u"Chinese (Taiwan)"): u"zh-TW cht",
            _(u"Chinese (Singapore)"): u"zh-SG chs",
            _(u"Croatian (Croatia)"): u"hr-HR croatian",
            _(u"Czech (Czech Republic)"): u"cs-CZ czech",
            _(u"Danish (Denmark)"): u"da-DK danish",
            _(u"Dutch (Belgium)"): u"nl-BE nlb",
            _(u"Dutch (Netherlands)"): u"nl-NL nld",
            _(u"English (Australia)"): u"en-AU ena",
            _(u"English (Belize)"): u"en-BZ eng_belize",
            _(u"English (Canada)"): u"en-CA enc",
            _(u"English (Caribbean)"): u"en-029 eng_caribbean",
            _(u"English (Ireland)"): u"en-IE eni",
            _(u"English (Jamaica)"): u"en-JM enj",
            _(u"English (New Zealand)"): u"en-NZ enz",
            _(u"English (South Africa)"): u"en-ZA ens",
            _(u"English (Trinidad)"): u"en-TT eng",
            _(u"English (United States)"): u"en-US enu",
            _(u"English (United Kingdom)"): u"en-GB eng",
            _(u"Estonian (Estonia)"): u"et-EE estonian",
            _(u"Faeroese (Faroe Islands)"): u"fo-FO faroese",
            _(u"Farsi (Iran)"): u"fa-IR persian",
            _(u"Finnish (Finland)"): u"fi-FI fin",
            _(u"French (Belgium)"): u"fr-BE frb",
            _(u"French (Canada)"): u"fr-CA frc",
            _(u"French (France)"): u"fr-FR fra",
            _(u"French (Luxembourg)"): u"fr-LU frl",
            _(u"French (Switzerland)"): u"fr-CH frs",
            _(u"German (Austria)"): u"de-AT dea",
            _(u"German (Germany)"): u"de-DE deu",
            _(u"German (Luxembourg)"): u"de-LU del",
            _(u"German (Switzerland)"): u"de-CH des",
            _(u"Greek (Greece)"): u"el-GR ell",
            _(u"Hebrew (Israel)"): u"he-IL hebrew",
            _(u"Hindi (India)"): u"hi-IN hindi",
            _(u"Hungarian (Hungary)"): u"hu-HU hun",
            _(u"Icelandic (Iceland)"): u"is-IS icelandic",
            _(u"Indonesian (Indonesia)"): u"id-ID indonesian",
            _(u"Italian (Italy)"): u"it-IT ita",
            _(u"Italian (Switzerland)"): u"it-CH its",
            _(u"Japanese (Japan)"): u"ja-JP jpn",
            _(u"Korean (Korea)"): u"ko-KR kor",
            _(u"Latvian (Latvia)"): u"lv-LV latvian",
            _(u"Lithuanian (Lituania)"): u"lt-LT lithuanian",
            _(u"Malaysian (Malaysia)"): u"ms-MY malay",
            _(u"Maltese (Malta)"): u"mt-MT maltese",
            _(u"Norwegian (Bokmal)"): u"no-NO nor",
            _(u"Norwegian (Nynorsk)"): u"no-NO non",
            _(u"Persian (Iran)"): u"fa-IR persian",
            _(u"Polish (Poland)"): u"pl-PL plk",
            _(u"Portuguese (Brazil)"): u"pt-BR ptb",
            _(u"Portuguese (Portugal)"): u"pt-PT ptg",
            _(u"Romanian (Romania)"): u"ro-RO rom",
            _(u"Russian (Russia)"): u"ru-RU rus",
            _(u"Serbian (Cyrillic)"): u"sr-RS srb",
            _(u"Serbian (Latin)"): u"sr-RS srl",
            _(u"Slovak (Slovakia)"): u"sk-SK sky",
            _(u"Slovenian (Slovania)"): u"sl-SI slovenian",
            _(u"Spanish (Argentina)"): u"es-AR esr",
            _(u"Spanish (Bolivia)"): u"es-BO esb",
            _(u"Spanish (Colombia)"): u"es-CO eso",
            _(u"Spanish (Chile)"): u"es-CL esl",
            _(u"Spanish (Costa Rica)"): u"es-CR esc",
            _(u"Spanish (Dominican Republic)"): u"es-DO esd",
            _(u"Spanish (Ecuador)"): u"es-EC esf",
            _(u"Spanish (El Salvador)"): u"es-SV ese",
            _(u"Spanish (Guatemala)"): u"es-GT esg",
            _(u"Spanish (Honduras)"): u"es-HN esh",
            _(u"Spanish (Mexico)"): u"es-MX esm",
            _(u"Spanish (Nicaragua)"): u"es-NI esi",
            _(u"Spanish (Panama)"): u"es-PA esa",
            _(u"Spanish (Paraguay)"): u"es-PY esz",
            _(u"Spanish (Peru)"): u"es-PE esr",
            _(u"Spanish (Puerto Rico)"): u"es-PR esu",
            _(u"Spanish (Spain)"): u"es-ES esn",
            _(u"Spanish (United States)"): u"es-US est",
            _(u"Spanish (Uruguay)"): u"es-UY esy",
            _(u"Spanish (Venezuela)"): u"es-VE esv",
            _(u"Swedish (Sweden)"): u"sv-SE sve",
            _(u"Swedish (Finland)"): u"sv-FI svf",
            _(u"Thai (Thailand)"): u"th-TH thai",
            _(u"Turkish (Turkey)"): u"tr-TR trk",
            _(u"Ukrainian (Ukraine)"): u"uk-UA ukr",
            _(u"Urdu (Pakistan)"): u"ur-PK urdu",
            _(u"Vietnamese (Vietnam)"): u"vi-VN vietnamese",
        }
        return _languageCodes

def rtlString(source, lang):
    if lang and source and lang[0:2] in set([u"ar",u"he"]):
        line = []
        lineInsertion = 0
        words = []
        rtl = True
        for c in source:
            bidi = unicodedata.bidirectional(c)
            if rtl:
                if bidi == u'L':
                    if words:
                        line.insert(lineInsertion, u''.join(words))
                        words = []
                    rtl = False
                elif bidi in (u'R', u'NSM', u'AN'):
                    pass
                else:
                    if words:
                        line.insert(lineInsertion, u''.join(words))
                        words = []
                    line.insert(lineInsertion, c)
                    continue
            else:
                if bidi == u'R' or bidi == u'AN':
                    if words:
                        line.append(u''.join(words))
                        words = []
                    rtl = True
            words.append(c)
        if words:
            if rtl:
                line.insert(0, u''.join(words))
        return u''.join(line)
    else:
        return source

# Iterate over grouping intervals
def _grouping_intervals(grouping):
    last_interval = 3 # added by Mark V to prevent compile error but not necessary semantically
    for interval in grouping:
        # if grouping is -1, we are done
        if interval == CHAR_MAX:
            return
        # 0: re-use last group ad infinitum
        if interval == 0:
            while True:
                yield last_interval
        yield interval
        last_interval = interval

#perform the grouping from right to left
def _group(conv, s, monetary=False):
    thousands_sep = conv[monetary and u'mon_thousands_sep' or u'thousands_sep']
    grouping = conv[monetary and u'mon_grouping' or u'grouping']
    if not grouping:
        return (s, 0)
    result = u""
    seps = 0
    if s[-1] == u' ':
        stripped = s.rstrip()
        right_spaces = s[len(stripped):]
        s = stripped
    else:
        right_spaces = u''
    left_spaces = u''
    groups = []
    for interval in _grouping_intervals(grouping):
        if not s or s[-1] not in u"0123456789":
            # only non-digit characters remain (sign, spaces)
            left_spaces = s
            s = u''
            break
        groups.append(s[-interval:])
        s = s[:-interval]
    if s:
        groups.append(s)
    groups.reverse()
    return (
        left_spaces + thousands_sep.join(groups) + right_spaces,
        len(thousands_sep) * (len(groups) - 1)
    )

# Strip a given amount of excess padding from the given string
def _strip_padding(s, amount):
    lpos = 0
    while amount and s[lpos] == u' ':
        lpos += 1
        amount -= 1
    rpos = len(s) - 1
    while amount and s[rpos] == u' ':
        rpos -= 1
        amount -= 1
    return s[lpos:rpos+1]

_percent_re = re.compile(ur'%(?:\((?P<key>.*?)\))?'
                         ur'(?P<modifiers>[-#0-9 +*.hlL]*?)[eEfFgGdiouxXcrs%]')

def format(conv, percent, value, grouping=False, monetary=False, *additional):
    u"""Returns the locale-aware substitution of a %? specifier
    (percent).

    additional is for format strings which contain one or more
    '*' modifiers."""
    # this is only for one-percent-specifier strings and this should be checked
    match = _percent_re.match(percent)
    if not match or len(match.group())!= len(percent):
        raise ValueError((u"format() must be given exactly one %%char "
                         u"format specifier, %s not valid") % repr(percent))
    return _format(conv, percent, value, grouping, monetary, *additional)

def _format(conv, percent, value, grouping=False, monetary=False, *additional):
    if additional:
        formatted = percent % ((value,) + additional)
    else:
        formatted = percent % value
    # floats and decimal ints need special action!
    if percent[-1] in u'eEfFgG':
        seps = 0
        parts = formatted.split(u'.')
        if grouping:
            parts[0], seps = _group(conv, parts[0], monetary=monetary)
        decimal_point = conv[monetary and u'mon_decimal_point' or u'decimal_point']
        formatted = decimal_point.join(parts)
        if seps:
            formatted = _strip_padding(formatted, seps)
    elif percent[-1] in u'diu':
        seps = 0
        if grouping:
            formatted, seps = _group(conv, formatted, monetary=monetary)
        if seps:
            formatted = _strip_padding(formatted, seps)
    return formatted

def format_string(conv, f, val, grouping=False):
    u"""Formats a string in the same way that the % formatting would use,
    but takes the current locale into account.
    Grouping is applied if the third parameter is true."""
    percents = list(_percent_re.finditer(f))
    new_f = _percent_re.sub(u'%s', f)

    if isinstance(val, collections.Mapping):
        new_val = []
        for perc in percents:
            if perc.group()[-1]==u'%':
                new_val.append(u'%')
            else:
                new_val.append(format(conv, perc.group(), val, grouping))
    else:
        if not isinstance(val, tuple):
            val = (val,)
        new_val = []
        i = 0
        for perc in percents:
            if perc.group()[-1]==u'%':
                new_val.append(u'%')
            else:
                starcount = perc.group(u'modifiers').count(u'*')
                new_val.append(_format(conv,
                                       perc.group(),
                                       val[i],
                                       grouping,
                                       False,
                                       *val[i+1:i+1+starcount]))
                i += (1 + starcount)
    val = tuple(new_val)

    return new_f % val

def currency(conv, val, symbol=True, grouping=False, international=False):
    u"""Formats val according to the currency settings
    in the current locale."""

    # check for illegal values
    digits = conv[international and u'int_frac_digits' or u'frac_digits']
    if digits == 127:
        raise ValueError(u"Currency formatting is not possible using "
                         u"the 'C' locale.")

    s = format(u'%%.%if' % digits, abs(val), grouping, monetary=True)
    # '<' and '>' are markers if the sign must be inserted between symbol and value
    s = u'<' + s + u'>'

    if symbol:
        smb = conv[international and u'int_curr_symbol' or u'currency_symbol']
        precedes = conv[val<0 and u'n_cs_precedes' or u'p_cs_precedes']
        separated = conv[val<0 and u'n_sep_by_space' or u'p_sep_by_space']

        if precedes:
            s = smb + (separated and u' ' or u'') + s
        else:
            s = s + (separated and u' ' or u'') + smb

    sign_pos = conv[val<0 and u'n_sign_posn' or u'p_sign_posn']
    sign = conv[val<0 and u'negative_sign' or u'positive_sign']

    if sign_pos == 0:
        s = u'(' + s + u')'
    elif sign_pos == 1:
        s = sign + s
    elif sign_pos == 2:
        s = s + sign
    elif sign_pos == 3:
        s = s.replace(u'<', sign)
    elif sign_pos == 4:
        s = s.replace(u'>', sign)
    else:
        # the default if nothing specified;
        # this should be the most fitting sign position
        s = sign + s

    return s.replace(u'<', u'').replace(u'>', u'')

def ftostr(conv, val):
    u"""Convert float to integer, taking the locale into account."""
    return format(conv, u"%.12g", val)

def atof(conv, string, func=float):
    u"Parses a string as a float according to the locale settings."
    #First, get rid of the grouping
    ts = conv[u'thousands_sep']
    if ts:
        string = string.replace(ts, u'')
    #next, replace the decimal point with a dot
    dd = conv[u'decimal_point']
    if dd:
        string = string.replace(dd, u'.')
    #finally, parse the string
    return func(string)

def atoi(conv, unicode):
    u"Converts a string to an integer according to the locale settings."
    return atof(conv, unicode, _INT)

# decimal formatting
from decimal import getcontext, Decimal

def format_picture(conv, value, picture):
    monetary = False
    decimal_point = conv[u'decimal_point']
    thousands_sep = conv[monetary and u'mon_thousands_sep' or u'thousands_sep']
    percent = u'%'
    per_mille = u'\u2030'
    minus_sign = u'-'
    #grouping = conv[monetary and 'mon_grouping' or 'grouping']

    if isinstance(value, float):
        value = Decimal.from_float(value)
    elif isinstance(value, _STR_NUM_TYPES):
        value = Decimal(value)
    elif not isinstance(value, Decimal):
        raise ValueError(_(u'Picture requires a number convertable to decimal or float').format(picture))
        
    if value.is_nan():
        return u'NaN'
    
    isNegative = value.is_signed()
    
    pic, sep, negPic = picture.partition(u';')
    if negPic and u';' in negPic:
        raise ValueError(_(u'Picture contains multiple picture sepearators {0}').format(picture))
    if isNegative and negPic:
        pic = negPic
    
    if len([c for c in pic if c in (percent, per_mille) ]) > 1:
        raise ValueError(_(u'Picture contains multiple percent or per_mille charcters {0}').format(picture))
    if percent in pic:
        value *= 100
    elif per_mille in pic:
        value *= 1000
        
    intPart, sep, fractPart = pic.partition(decimal_point)
    prefix = u''
    numPlaces = 0
    intPlaces = 0
    grouping = 0
    fractPlaces = 0
    suffix = u''
    if fractPart:
        if decimal_point in fractPart:
            raise ValueError(_(u'Sub-picture contains decimal point sepearators {0}').format(pic))
    
        for c in fractPart:
            if c.isdecimal():
                numPlaces += 1
                fractPlaces += 1
                if suffix:
                    raise ValueError(_(u'Sub-picture passive character {0} between active characters {1}').format(c, fractPart))
            else:
                suffix += c

    intPosition = 0                
    for c in reversed(intPart):
        if c.isdecimal() or c == u'#' or c == thousands_sep:
            if prefix:
                raise ValueError(_(u'Sub-picture passive character {0} between active characters {1}').format(c, intPart))
        if c.isdecimal():
            numPlaces += 1
            intPlaces += 1
            intPosition += 1
            prefix = u''
        elif c == u'#':
            numPlaces += 1
            intPosition += 1
        elif c == thousands_sep:
            if not grouping:
                grouping = intPosition
        else:
            prefix = c + prefix

    if not numPlaces and prefix != minus_sign:
            raise ValueError(_(u'Sub-picture must contain at least one digit position or sign character {0}').format(pic))
    if intPlaces == 0 and fractPlaces == 0:
        intPlaces = 1
    
    return format_decimal(None, value, intPlaces=intPlaces, fractPlaces=fractPlaces, 
                          sep=thousands_sep, dp=decimal_point, grouping=grouping,
                          pos=prefix,
                          neg=prefix if negPic else prefix + minus_sign,
                          trailpos=suffix,
                          trailneg=suffix)

def format_decimal(conv, value, intPlaces=1, fractPlaces=2, curr=u'', sep=None, grouping=None, dp=None, pos=None, neg=None, trailpos=None, trailneg=None):
    u"""Convert Decimal to a formatted string including currency if any.

    intPlaces:  required number of digits before the decimal point
    fractPlaces:  required number of places after the decimal point
    curr:    optional currency symbol before the sign (may be blank)
    sep:     optional grouping separator (comma, period, space, or blank)
    dp:      decimal point indicator (comma or period)
             only specify as blank when places is zero
    pos:     optional sign for positive numbers: '+', space or blank
    neg:     optional sign for negative numbers: '-', '(', space or blank
    trailneg:optional trailing minus indicator:  '-', ')', space or blank

    >>> d = Decimal('-1234567.8901')
    >>> format(d, curr='$')
    '-$1,234,567.89'
    >>> format(d, places=0, sep='.', dp='', neg='', trailneg='-')
    '1.234.568-'
    >>> format(d, curr='$', neg='(', trailneg=')')
    '($1,234,567.89)'
    >>> format(Decimal(123456789), sep=' ')
    '123 456 789.00'
    >>> format(Decimal('-0.02'), neg='<', trailneg='>')
    '<0.02>'

    """
    if conv is not None:
        if dp is None:
            dp = conv[u'decimal_point'] or u'.'
        if sep is None:
            sep = conv[u'thousands_sep'] or u','
        if pos is None and trailpos is None:
            possign = conv[u'positive_sign']
            pospos = conv[u'p_sign_posn']
            if pospos in(u'0', 0):
                pos = u'('; trailpos = u')'
            elif pospos in (u'1', 1, u'3', 3):
                pos = possign; trailpos = u''
            elif pospos in (u'2', 2, u'4', 4):
                pos = u''; trailpos = possign
            else:
                pos = u''; trailpos = u''
        if neg is None and trailneg is None:
            negsign = conv[u'negative_sign']
            negpos = conv[u'n_sign_posn']
            if negpos in (u'0', 0):
                neg = u'('; trailneg = u')'
            elif negpos in (u'1', 1, u'3', 3):
                neg = negsign; trailneg = u''
            elif negpos in (u'2', 2, u'4', 4):
                neg = u''; trailneg = negsign
            elif negpos == 127:
                neg = u'-'; trailneg = u''
            else:
                neg = u''; trailneg = u''
        if grouping is None:
            groups = conv[u'grouping']
            grouping = groups[0] if groups else 3
    else:
        if dp is None:
            dp = u'.'
        if sep is None:
            sep = u','
        if neg is None and trailneg is None:
            neg = u'-'; trailneg = u''
        if grouping is None:
            grouping = 3
    q = Decimal(10) ** -fractPlaces      # 2 places --> '0.01'
    sign, digits, exp = value.quantize(q).as_tuple()
    result = []
    digits = list(imap(unicode, digits))
    build, next = result.append, digits.pop
    build(trailneg if sign else trailpos)
    if value.is_finite():
        for i in xrange(fractPlaces):
            build(next() if digits else u'0')
        if fractPlaces:
            build(dp)
        i = 0
        while digits or intPlaces > 0:
            build(next() if digits else u'0')
            intPlaces -= 1
            i += 1
            if grouping and i == grouping and digits:
                i = 0
                build(sep)
    elif value.is_nan():
        result.append(u"NaN")
    elif value.is_infinite():
        result.append(u"ytinifnI")
    build(curr)
    build(neg if sign else pos)
    return u''.join(reversed(result))
