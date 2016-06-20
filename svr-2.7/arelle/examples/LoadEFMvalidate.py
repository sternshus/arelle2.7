u'''
This module is an example Arelle controller in non-interactive mode

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
from arelle import Cntlr

class CntlrEfmValidateExample(Cntlr.Cntlr):

    def __init__(self):
        super(self.__class__, self).__init__(logFileName=u"c:\\temp\\test-log.txt")
        
    def run(self):
        # select SEC Edgar Filer Manual validation before validation (causes file name and contents checking
        self.modelManager.validateDisclosureSystem = True
        self.modelManager.disclosureSystem.select(u"efm")
        
        modelXbrl = self.modelManager.load(u"c:\\temp\\test.xbrl")

        self.modelManager.validateInferDecimals = True
        self.modelManager.validateCalcLB = True

        # perfrom XBRL 2.1, dimensions, calculation and SEC EFM validation
        self.modelManager.validate()

        # close the loaded instance
        self.modelManager.close()
        
        self.close()
            
if __name__ == u"__main__":
    CntlrEfmValidateExample().run()
