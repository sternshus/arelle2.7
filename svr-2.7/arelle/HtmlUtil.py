u'''
Created on April 14, 2011

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
try:
    import regex as re
except ImportError:
    import re

def attrValue(unicode, name):
    # retrieves attribute in a string, such as xyz="abc" or xyz='abc' or xyz=abc; 
    prestuff, matchedName, valuePart = unicode.lower().partition(u"charset")
    value = []
    endSep = None
    beforeEquals = True
    for c in valuePart:
        if value:
            if c == endSep or c.isspace() or c in (u';'):
                break
            value.append(c)
        elif beforeEquals:
            if c == u'=':
                beforeEquals = False
        else:
            if c in (u'"', u"'"):
                endSep = c
            elif c == u';':
                break
            elif not c.isspace():
                value.append(c)
    return u''.join(value)
