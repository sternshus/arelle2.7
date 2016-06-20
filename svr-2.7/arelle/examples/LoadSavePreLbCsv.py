u'''
This module is an example Arelle controller in non-interactive mode

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
from arelle import Cntlr
from arelle.ViewCsvRelationshipSet import viewRelationshipSet

class CntlrCsvPreLbExample(Cntlr.Cntlr):

    def __init__(self):
        super(self.__class__, self).__init__(logFileName=u"c:\\temp\\test-log.txt")
        
    def run(self):
        modelXbrl = self.modelManager.load(u"c:\\temp\\test.xbrl")

        # output presentation linkbase tree as a csv file
        viewRelationshipSet(modelXbrl, u"c:\\temp\\test-pre.csv", u"Presentation", u"http://www.xbrl.org/2003/arcrole/parent-child")

        # close the loaded instance
        self.modelManager.close()
        
        self.close()
            
if __name__ == u"__main__":
    CntlrCsvPreLbExample().run()
