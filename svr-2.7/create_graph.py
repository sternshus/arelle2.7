import sys

from arelle import CntlrCmdLine
sys.argv = ['','-f', 'http://www.sec.gov/Archives/edgar/data/66740/000155837015002024/mmm-20150930.xml',
         '--disclosureSystem', 'efm-strict-all-years', '--store-to-XBRL-DB',
         'rdfTurtleFile,None,None,None,/home/redward/Downloads/turtle_3m.rdf,None,rdfDB']

result = CntlrCmdLine.xbrlTurtleGraphModel('http://www.sec.gov/Archives/edgar/data/66740/000155837015002024/mmm-20150930.xml')

x = 5
