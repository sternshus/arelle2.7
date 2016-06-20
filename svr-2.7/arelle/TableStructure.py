u'''
Created on Feb 02, 2014

@author: Mark V Systems Limited
(c) Copyright 2014 Mark V Systems Limited, All rights reserved.
'''
from __future__ import division
try:
    import regex as re
except ImportError:
    import re
from collections import defaultdict
import os, io, json
from datetime import datetime, timedelta
from arelle import XbrlConst
from arelle.ModelDtsObject import ModelConcept

# regular expression components
STMT = ur".* - statement - "
notDET = ur"(?!.*details)"
notCMPRH = ur"(?!.*comprehensive)"
isCMPRH = ur"(?=.*comprehensive)"
u''' common mis-spellings of parenthetical to match successfully (from 2013 SEC filings)
    paranthetical
    parenthical
    parentheical
    parenthtical
    parenthethical
    parenthentical
    prenthetical
    parenethetical
    
use a regular expression that is forgiving on at least the above
and doens't match variations of parent, transparent, etc.
'''
rePARENTHETICAL = ur"pa?r[ae]ne?tht?[aei]+n?t?h?i?c"
notPAR = u"(?!.*" + rePARENTHETICAL + u")"
isPAR = u"(?=.*" + rePARENTHETICAL + u")"

UGT_TOPICS = None

def RE(*args):
    return re.compile(u''.join(args), re.IGNORECASE)

# NOTE: This is an early experimental implementation of statement detection
# it is not in a finished status at this time.
EFMtableCodes = [
    # ELRs are parsed for these patterns in sort order until there is one match per code
    # sheet(s) may be plural
    
    # statement detection including root element of presentation link role
    (u"BS", RE(STMT, notDET, notPAR), (u"StatementOfFinancialPositionAbstract",)),
    (u"BSP", RE(STMT, notDET, isPAR), (u"StatementOfFinancialPositionAbstract",)),
    (u"IS", RE(STMT, notDET, notPAR), (u"IncomeStatementAbstract",)),
    (u"ISP", RE(STMT, notDET, isPAR), (u"IncomeStatementAbstract",)),
    (u"CI", RE(STMT, notDET, notPAR), (u"StatementOfIncomeAndComprehensiveIncomeAbstract",)),
    (u"CIP", RE(STMT, notDET, isPAR), (u"StatementOfIncomeAndComprehensiveIncomeAbstract",)),
    (u"EQ", RE(STMT, notDET, notPAR), (u"StatementOfStockholdersEquityAbstract",u"StatementOfPartnersCapitalAbstract")),
    (u"EQP", RE(STMT, notDET, isPAR), (u"StatementOfStockholdersEquityAbstract",u"StatementOfPartnersCapitalAbstract")),
    (u"CF", RE(STMT, notDET, notPAR), (u"StatementOfCashFlowsAbstract",)),
    (u"CFP", RE(STMT, notDET, isPAR), (u"StatementOfCashFlowsAbstract",)),
    (u"CA", RE(STMT, notDET, notPAR), (u"CapitalizationLongtermDebtAndEquityAbstract",)),
    (u"CAP", RE(STMT, notDET, isPAR), (u"CapitalizationLongtermDebtAndEquityAbstract",)),
    (u"IN", RE(STMT, notDET, notPAR), (u"ScheduleOfInvestmentsAbstract",)),
    (u"INP", RE(STMT, notDET, isPAR), (u"ScheduleOfInvestmentsAbstract",)),
                 
    # statement detection without considering root elements
    (u"DEI", RE(ur".* - (document|statement) - .*document\W+.*entity\W+.*information"), None),
    (u"BS", RE(STMT, notDET, notPAR, ur".*balance\W+sheet"), None),
    (u"BSP", RE(STMT, notDET, isPAR, ur".*balance\W+sheet"), None),
    (u"CF", RE(STMT, notDET, notPAR, ur".*cash\W*flow"), None),
    (u"IS", RE(STMT, notDET, notPAR, notCMPRH, ur".*(income|loss)"), None),
    (u"ISP", RE(STMT, notDET, isPAR, notCMPRH, ur".*(income|loss)"), None),
    (u"CI", RE(STMT, notDET, notPAR, isCMPRH, ur".*(income|loss|earnings)"), None),
    (u"CIP", RE(STMT, notDET, isPAR, isCMPRH, ur".*(income|loss|earnings)"), None),
    (u"CA", RE(STMT, notDET, notPAR, ur".*capitali[sz]ation"), None),
    (u"CAP", RE(STMT, notDET, isPAR, ur".*capitali[sz]ation"), None),
    (u"EQ", RE(STMT, notDET, notPAR, ur".*(equity|capital)"), None),
    (u"EQP", RE(STMT, notDET, isPAR, ur".*(equity|capital)"), None),
    (u"IS", RE(STMT, notDET, notPAR, ur".*(income|operations|earning)"), None),
    (u"EQ", RE(STMT, notDET, notPAR, ur".*def[ei][cs]it"), None),
    (u"ISP", RE(STMT, notDET, isPAR, ur".*(income|operations|earning)"), None),
    (u"CFP", RE(STMT, notDET, isPAR, ur".*cash\W*flow.*"), None),
    (u"IS", RE(STMT, notDET, notPAR, ur".*loss"), None),
    (u"ISP", RE(STMT, notDET, isPAR, ur".*loss"), None),
    (u"BS", RE(STMT, notDET, notPAR, ur".*(position|condition)"), None),
    (u"BSP", RE(STMT, notDET, isPAR, ur".*(position|condition)"), None),
    (u"SE", RE(STMT, notDET, notPAR, ur"(?=.*equity).*comprehensive"), None),
    (u"EQ", RE(STMT, notDET, notPAR, ur".*shareholder[']?s[']?\W+investment"), None),
    (u"EQP", RE(STMT, notDET, isPAR, ur".*shareholder[']?s[']?\W+investment"), None),
    (u"EQ", RE(STMT, notDET, notPAR, ur".*retained\W+earning"), None),
    (u"IN", RE(STMT, notDET, notPAR, ur".*investment"), None),
    (u"INP", RE(STMT, notDET, isPAR, ur".*investment"), None),
    (u"LA", RE(STMT, notDET, notPAR, ur"(?!.*changes)(?=.*assets).*liquidati"), None),
    (u"LC", RE(STMT, notDET, notPAR, ur"(?=.*changes)(?=.*assets).*liquidati"), None),
    (u"IS", RE(STMT, notDET, notPAR, ur"(?=.*disc).*operation"), None),
    (u"BS", RE(STMT, notDET, notPAR, ur"(?!.*changes).*assets"), None),
    (u"BSP", RE(STMT, notDET, isPAR, ur"(?!.*changes).*assets"), None),
    (u"EQ", RE(STMT, notDET, notPAR, ur"(?=.*changes).*assets"), None),
    (u"EQP", RE(STMT, notDET, isPAR, ur"(?=.*changes).*assets"), None),
    (u"FH", RE(STMT, notDET, notPAR, ur"(?=.*financial).*highlight"), None),
    (u"FHP", RE(STMT, notDET, isPAR, ur"(?=.*financial).*highlight"), None),
    (u"EQ", RE(STMT, notDET, notPAR, ur"(?=.*reserve).*trust"), None),
    (u"EQP", RE(STMT, notDET, isPAR, ur"(?=.*reserve).*trust"), None),
    (u"LC", RE(STMT, notDET, notPAR, ur"(?=.*activities).*liquidati"), None),
    (u"EQP", RE(STMT, notDET, isPAR, ur".*def[ei][cs]it"), None),
    (u"BSV", RE(STMT, notDET,notPAR, ur".*net\W+asset\W+value"), None), 
    (u"CFS", RE(STMT, notDET,notPAR, ur".*cash\W*flows\W+supplemental"), None),
    (u"LAP", RE(STMT, notDET, isPAR, ur".*(?!.*changes)(?=.*assets).*liquidati"), None)
    ]
HMRCtableCodes = [
    # ELRs are parsed for these patterns in sort order until there is one match per code
    # sheet(s) may be plural
    (u"DEI", RE(ur".*entity\W+.*information.*"), None),
    (u"BS", RE(ur".*balance\W+sheet.*"), None),
    (u"IS", RE(ur".*loss"), None),
    (u"CF", RE(ur".*cash\W*flow.*"), None),
    (u"SE", RE(ur".*(shareholder|equity).*"), None),
    ]

def evaluateRoleTypesTableCodes(modelXbrl):
    disclosureSystem = modelXbrl.modelManager.disclosureSystem
    
    if disclosureSystem.EFM or disclosureSystem.HMRC:
        detectMultipleOfCode = False
        if disclosureSystem.EFM:
            tableCodes = list( EFMtableCodes ) # separate copy of list so entries can be deleted
            # for Registration and resubmission allow detecting multiple of code
            detectMultipleOfCode = any(v and any(v.startswith(dt) for dt in (u'S-', u'F-', u'8-K', u'6-K'))
                                       for docTypeConcept in modelXbrl.nameConcepts.get(u'DocumentType', ())
                                       for docTypeFact in modelXbrl.factsByQname.get(docTypeConcept.qname, ())
                                       for v in (docTypeFact.value,))
        elif disclosureSystem.HMRC:
            tableCodes = list( HMRCtableCodes ) # separate copy of list so entries can be deleted
 
        codeRoleURI = {}  # lookup by code for roleURI
        roleURICode = {}  # lookup by roleURI
        
        # resolve structural model
        roleTypes = [roleType
                     for roleURI in modelXbrl.relationshipSet(XbrlConst.parentChild).linkRoleUris
                     for roleType in modelXbrl.roleTypes.get(roleURI,())]
        roleTypes.sort(key=lambda roleType: roleType.definition)
        # assign code to table link roles (Presentation ELRs)
        for roleType in roleTypes:
            definition = roleType.definition
            rootConcepts = None
            for i, tableCode in enumerate(tableCodes):
                code, pattern, rootConceptNames = tableCode
                if (detectMultipleOfCode or code not in codeRoleURI) and pattern.match(definition):
                    if rootConceptNames and rootConcepts is None:
                        rootConcepts = modelXbrl.relationshipSet(XbrlConst.parentChild, roleType.roleURI).rootConcepts
                    if (not rootConceptNames or
                        any(rootConcept.name in rootConceptNames for rootConcept in rootConcepts)):
                        codeRoleURI[code] = roleType.roleURI
                        roleURICode[roleType.roleURI] = code
                        if not detectMultipleOfCode:
                            del tableCodes[i] # done with looking at this code
                        break
        # find defined non-default axes in pre hierarchy for table
        for roleTypes in modelXbrl.roleTypes.values():
            for roleType in roleTypes:
                roleType._tableCode = roleURICode.get(roleType.roleURI)
    else:
        for roleTypes in modelXbrl.roleTypes.values():
            for roleType in roleTypes:
                roleType._tableCode = None

def evaluateTableIndex(modelXbrl):
    disclosureSystem = modelXbrl.modelManager.disclosureSystem
    if disclosureSystem.EFM:
        COVER    = u"1Cover"
        STMTS    = u"2Financial Statements"
        NOTES    = u"3Notes to Financial Statements"
        POLICIES = u"4Accounting Policies"
        TABLES   = u"5Notes Tables"
        DETAILS  = u"6Notes Details"
        UNCATEG  = u"7Uncategorized"
        roleDefinitionPattern = re.compile(ur"([0-9]+) - (Statement|Disclosure|Schedule|Document) - (.+)")
        # build EFM rendering-compatible index
        definitionElrs = dict((roleType.definition, roleType)
                              for roleURI in modelXbrl.relationshipSet(XbrlConst.parentChild).linkRoleUris
                              for roleType in modelXbrl.roleTypes.get(roleURI,()))
        isRR = any(ns.startswith(u"http://xbrl.sec.gov/rr/") for ns in modelXbrl.namespaceDocs.keys())
        tableGroup = None
        firstTableLinkroleURI = None
        firstDocumentLinkroleURI = None
        sortedRoleTypes = sorted(definitionElrs.items(), key=lambda item: item[0])
        for roleDefinition, roleType in sortedRoleTypes:
            match = roleDefinitionPattern.match(roleDefinition) if roleDefinition else None
            if not match: 
                roleType._tableIndex = (UNCATEG, roleType.roleURI)
                continue
            seq, tblType, tblName = match.groups()
            if isRR:
                tableGroup = COVER
            elif not tableGroup:
                tableGroup = (u"Paren" in tblName and COVER or tblType == u"Statement" and STMTS or
                              u"(Polic" in tblName and NOTES or u"(Table" in tblName and TABLES or
                              u"(Detail" in tblName and DETAILS or COVER)
            elif tableGroup == COVER:
                tableGroup = (tblType == u"Statement" and STMTS or u"Paren" in tblName and COVER or
                              u"(Polic" in tblName and NOTES or u"(Table" in tblName and TABLES or
                              u"(Detail" in tblName and DETAILS or NOTES)
            elif tableGroup == STMTS:
                tableGroup = ((tblType == u"Statement" or u"Paren" in tblName) and STMTS or
                              u"(Polic" in tblName and NOTES or u"(Table" in tblName and TABLES or
                              u"(Detail" in tblName and DETAILS or NOTES)
            elif tableGroup == NOTES:
                tableGroup = (u"(Polic" in tblName and POLICIES or u"(Table" in tblName and TABLES or 
                              u"(Detail" in tblName and DETAILS or tblType == u"Disclosure" and NOTES or UNCATEG)
            elif tableGroup == POLICIES:
                tableGroup = (u"(Table" in tblName and TABLES or u"(Detail" in tblName and DETAILS or 
                              (u"Paren" in tblName or u"(Polic" in tblName) and POLICIES or UNCATEG)
            elif tableGroup == TABLES:
                tableGroup = (u"(Detail" in tblName and DETAILS or 
                              (u"Paren" in tblName or u"(Table" in tblName) and TABLES or UNCATEG)
            elif tableGroup == DETAILS:
                tableGroup = ((u"Paren" in tblName or u"(Detail" in tblName) and DETAILS or UNCATEG)
            else:
                tableGroup = UNCATEG
            if firstTableLinkroleURI is None and tableGroup == COVER:
                firstTableLinkroleURI = roleType.roleURI
            if tblType == u"Document" and not firstDocumentLinkroleURI:
                firstDocumentLinkroleURI = roleType.roleURI
            roleType._tableIndex = (tableGroup, seq, tblName)
            roleType._tableChildren = []

        # flow allocate facts to roles (SEC presentation groups)
        if not modelXbrl.qnameDimensionDefaults: # may not have run validatino yet
            from arelle import ValidateXbrlDimensions
            ValidateXbrlDimensions.loadDimensionDefaults(modelXbrl)
        reportedFacts = set() # facts which were shown in a higher-numbered ELR table
        factsByQname = modelXbrl.factsByQname
        reportingPeriods = set()
        nextEnd = None
        deiFact = {}
        for conceptName in (u"DocumentPeriodEndDate", u"DocumentType", u"CurrentFiscalPeriodEndDate"):
            for concept in modelXbrl.nameConcepts[conceptName]:
                for fact in factsByQname[concept.qname]:
                    deiFact[conceptName] = fact
                    if fact.context is not None:
                        reportingPeriods.add((None, fact.context.endDatetime)) # for instant
                        reportingPeriods.add((fact.context.startDatetime, fact.context.endDatetime)) # for startEnd
                        nextEnd = fact.context.startDatetime
                        duration = (fact.context.endDatetime - fact.context.startDatetime).days + 1
                        break
        if u"DocumentType" in deiFact:
            fact = deiFact[u"DocumentType"]
            if u"-Q" in fact.xValue:
                # need quarterly and yr to date durations
                endDatetime = fact.context.endDatetime
                # if within 2 days of end of month use last day of month
                endDatetimeMonth = endDatetime.month
                if (endDatetime + timedelta(2)).month != endDatetimeMonth:
                    # near end of month
                    endOfMonth = True
                    while endDatetime.month == endDatetimeMonth:
                        endDatetime += timedelta(1) # go forward to next month
                else:
                    endOfMonth = False
                startYr = endDatetime.year
                startMo = endDatetime.month - 3
                if startMo < 0:
                    startMo += 12
                    startYr -= 1
                startDatetime = datetime(startYr, startMo, endDatetime.day, endDatetime.hour, endDatetime.minute, endDatetime.second)
                if endOfMonth:
                    startDatetime -= timedelta(1)
                    endDatetime -= timedelta(1)
                reportingPeriods.add((startDatetime, endDatetime))
                duration = 91
        # find preceding compatible default context periods
        while (nextEnd is not None):
            thisEnd = nextEnd
            prevMaxStart = thisEnd - timedelta(duration * .9)
            prevMinStart = thisEnd - timedelta(duration * 1.1)
            nextEnd = None
            for cntx in modelXbrl.contexts.values():
                if (cntx.isStartEndPeriod and not cntx.qnameDims and thisEnd == cntx.endDatetime and
                    prevMinStart <= cntx.startDatetime <= prevMaxStart):
                    reportingPeriods.add((None, cntx.endDatetime))
                    reportingPeriods.add((cntx.startDatetime, cntx.endDatetime))
                    nextEnd = cntx.startDatetime
                    break
                elif (cntx.isInstantPeriod and not cntx.qnameDims and thisEnd == cntx.endDatetime):
                    reportingPeriods.add((None, cntx.endDatetime))
        stmtReportingPeriods = set(reportingPeriods)       

        sortedRoleTypes.reverse() # now in descending order
        for i, roleTypes in enumerate(sortedRoleTypes):
            roleDefinition, roleType = roleTypes
            # find defined non-default axes in pre hierarchy for table
            tableFacts = set()
            tableGroup, tableSeq, tableName = roleType._tableIndex
            roleURIdims, priItemQNames = EFMlinkRoleURIstructure(modelXbrl, roleType.roleURI)
            for priItemQName in priItemQNames:
                for fact in factsByQname[priItemQName]:
                    cntx = fact.context
                    # non-explicit dims must be default
                    if (cntx is not None and
                        all(dimQn in modelXbrl.qnameDimensionDefaults
                            for dimQn in (roleURIdims.keys() - cntx.qnameDims.keys())) and
                        all(mdlDim.memberQname in roleURIdims[dimQn]
                            for dimQn, mdlDim in cntx.qnameDims.items()
                            if dimQn in roleURIdims)):
                        # the flow-up part, drop
                        cntxStartDatetime = cntx.startDatetime
                        cntxEndDatetime = cntx.endDatetime
                        if (tableGroup != STMTS or
                            (cntxStartDatetime, cntxEndDatetime) in stmtReportingPeriods and
                             (fact not in reportedFacts or
                              all(dimQn not in cntx.qnameDims # unspecified dims are all defaulted if reported elsewhere
                                  for dimQn in (cntx.qnameDims.keys() - roleURIdims.keys())))):
                            tableFacts.add(fact)
                            reportedFacts.add(fact)
            roleType._tableFacts = tableFacts
            
            # find parent if any
            closestParentType = None
            closestParentMatchLength = 0
            for _parentRoleDefinition, parentRoleType in sortedRoleTypes[i+1:]:
                matchLen = parentNameMatchLen(tableName, parentRoleType)
                if matchLen > closestParentMatchLength:
                    closestParentMatchLength = matchLen
                    closestParentType = parentRoleType
            if closestParentType is not None:
                closestParentType._tableChildren.insert(0, roleType)
                
            # remove lesser-matched children if there was a parent match
            unmatchedChildRoles = set()
            longestChildMatchLen = 0
            numChildren = 0
            for childRoleType in roleType._tableChildren:
                matchLen = parentNameMatchLen(tableName, childRoleType)
                if matchLen < closestParentMatchLength:
                    unmatchedChildRoles.add(childRoleType)
                elif matchLen > longestChildMatchLen:
                    longestChildMatchLen = matchLen
                    numChildren += 1
            if numChildren > 1: 
                # remove children that don't have the full match pattern length to parent
                for childRoleType in roleType._tableChildren:
                    if (childRoleType not in unmatchedChildRoles and 
                        parentNameMatchLen(tableName, childRoleType) < longestChildMatchLen):
                        unmatchedChildRoles.add(childRoleType)

            for unmatchedChildRole in unmatchedChildRoles:
                roleType._tableChildren.remove(unmatchedChildRole)

            for childRoleType in roleType._tableChildren:
                childRoleType._tableParent = roleType
                
            unmatchedChildRoles = None # dereference
        
        global UGT_TOPICS
        if UGT_TOPICS is None:
            try:
                from arelle import FileSource
                fh = FileSource.openFileStream(modelXbrl.modelManager.cntlr, 
                                               os.path.join(modelXbrl.modelManager.cntlr.configDir, u"ugt-topics.zip/ugt-topics.json"),
                                               u'r', u'utf-8')
                UGT_TOPICS = json.load(fh)
                fh.close()
                for topic in UGT_TOPICS:
                    topic[6] = set(topic[6]) # change concept abstracts list into concept abstracts set
                    topic[7] = set(topic[7]) # change concept text blocks list into concept text blocks set
                    topic[8] = set(topic[8]) # change concept names list into concept names set
            except Exception, ex:
                    UGT_TOPICS = None

        if UGT_TOPICS is not None:
            def roleUgtConcepts(roleType):
                roleConcepts = set()
                for rel in modelXbrl.relationshipSet(XbrlConst.parentChild, roleType.roleURI).modelRelationships:
                    if rel.toModelObject is not None:
                        roleConcepts.add(rel.toModelObject.name)
                    if rel.fromModelObject is not None:
                        roleConcepts.add(rel.fromModelObject.name)
                if hasattr(roleType, u"_tableChildren"):
                    for _tableChild in roleType._tableChildren:
                        roleConcepts |= roleUgtConcepts(_tableChild)
                return roleConcepts
            topicMatches = {} # topicNum: (best score, roleType)
    
            for roleDefinition, roleType in sortedRoleTypes:
                roleTopicType = u'S' if roleDefinition.startswith(u'S') else u'D'
                if getattr(roleType, u"_tableParent", None) is None:                
                    # rooted tables in reverse order
                    concepts = roleUgtConcepts(roleType)
                    for i, ugtTopic in enumerate(UGT_TOPICS):
                        if ugtTopic[0] == roleTopicType:
                            countAbstracts = len(concepts & ugtTopic[6])
                            countTextBlocks = len(concepts & ugtTopic[7])
                            countLineItems = len(concepts & ugtTopic[8])
                            if countAbstracts or countTextBlocks or countLineItems:
                                _score = (10 * countAbstracts +
                                          1000 * countTextBlocks +
                                          countLineItems / len(concepts))
                                if i not in topicMatches or _score > topicMatches[i][0]:
                                    topicMatches[i] = (_score, roleType)
            for topicNum, scoredRoleType in topicMatches.items():
                _score, roleType = scoredRoleType
                if _score > getattr(roleType, u"_tableTopicScore", 0):
                    ugtTopic = UGT_TOPICS[topicNum]
                    roleType._tableTopicScore = _score
                    roleType._tableTopicType = ugtTopic[0]
                    roleType._tableTopicName = ugtTopic[3]
                    roleType._tableTopicCode = ugtTopic[4]
                    # print ("Match score {:.2f} topic {} preGrp {}".format(_score, ugtTopic[3], roleType.definition))
        return firstTableLinkroleURI or firstDocumentLinkroleURI # did build _tableIndex attributes
    return None

def parentNameMatchLen(tableName, parentRoleType):
    lengthOfMatch = 0
    parentName = parentRoleType._tableIndex[2]
    parentNameLen = len(parentName.partition(u'(')[0])
    fullWordFound = False
    for c in tableName.partition(u'(')[0]:
        fullWordFound |= c.isspace()
        if lengthOfMatch >= parentNameLen or c != parentName[lengthOfMatch]:
            break
        lengthOfMatch += 1
    return fullWordFound and lengthOfMatch

def EFMlinkRoleURIstructure(modelXbrl, roleURI):
    relSet = modelXbrl.relationshipSet(XbrlConst.parentChild, roleURI)
    dimMems = {} # by dimension qname, set of member qnames
    priItems = set()
    for rootConcept in relSet.rootConcepts:
        EFMlinkRoleDescendants(relSet, rootConcept, dimMems, priItems)
    return dimMems, priItems
        
def EFMlinkRoleDescendants(relSet, concept, dimMems, priItems):
    if concept is not None:
        if concept.isDimensionItem:
            dimMems[concept.qname] = EFMdimMems(relSet, concept, set())
        else:
            if not concept.isAbstract:
                priItems.add(concept.qname)
            for rel in relSet.fromModelObject(concept):
                EFMlinkRoleDescendants(relSet, rel.toModelObject, dimMems, priItems)

def EFMdimMems(relSet, concept, memQNames):
    for rel in relSet.fromModelObject(concept):
        dimConcept = rel.toModelObject
        if isinstance(dimConcept, ModelConcept) and dimConcept.isDomainMember:
            memQNames.add(dimConcept.qname)
            EFMdimMems(relSet, dimConcept, memQNames)
    return memQNames

