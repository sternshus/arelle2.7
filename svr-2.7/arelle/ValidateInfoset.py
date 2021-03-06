u'''
Created on Feb 15, 2012

@author: Mark V Systems Limited
(c) Copyright 2012 Mark V Systems Limited, All rights reserved.
'''
from collections import defaultdict
from arelle.ModelDocument import Type
from arelle.ModelValue import qname
from arelle import XmlUtil, XbrlConst
from arelle.ValidateXbrlCalcs import inferredPrecision, inferredDecimals            

def validate(val, modelXbrl, infosetModelXbrl):
    infoset = infosetModelXbrl.modelDocument
    if infoset.type == Type.INSTANCE:
        # compare facts (assumed out of order)
        infosetFacts = defaultdict(list)
        for fact in infosetModelXbrl.facts:
            infosetFacts[fact.qname].append(fact)
        if len(modelXbrl.factsInInstance) != len(infosetModelXbrl.factsInInstance):
            modelXbrl.error(u"arelle:infosetTest",
                _(u"Fact counts mismatch, testcase instance %(foundFactCount)s, infoset instance %(expectedFactCount)s"),
                modelObject=(modelXbrl.modelDocument, infosetModelXbrl.modelDocument), 
                            foundFactCount=len(modelXbrl.factsInInstance),
                            expectedFactCount=len(infosetModelXbrl.factsInInstance))
        else:
            for i, instFact in enumerate(modelXbrl.facts):
                infosetFact = None
                for fact in infosetFacts[instFact.qname]:
                    if fact.isTuple and fact.isDuplicateOf(instFact, deemP0Equal=True):
                        infosetFact = fact
                        break
                    elif fact.isItem and fact.isVEqualTo(instFact, deemP0Equal=True):
                        infosetFact = fact
                        break
                if infosetFact is None: # takes precision/decimals into account
                    if fact is not None:
                        fact.isVEqualTo(instFact, deemP0Equal=True)
                    modelXbrl.error(u"arelle:infosetTest",
                        _(u"Fact %(factNumber)s mismatch %(concept)s"),
                        modelObject=instFact,
                                    factNumber=(i+1), 
                                    concept=instFact.qname)
                else:
                    ptvPeriodType = infosetFact.get(u"{http://www.xbrl.org/2003/ptv}periodType")
                    ptvBalance = infosetFact.get(u"{http://www.xbrl.org/2003/ptv}balance")
                    ptvDecimals = infosetFact.get(u"{http://www.xbrl.org/2003/ptv}decimals")
                    ptvPrecision = infosetFact.get(u"{http://www.xbrl.org/2003/ptv}precision")
                    if ptvPeriodType and ptvPeriodType != instFact.concept.periodType:
                        modelXbrl.error(u"arelle:infosetTest",
                            _(u"Fact %(factNumber)s periodType mismatch %(concept)s expected %(expectedPeriodType)s found %(foundPeriodType)s"),
                            modelObject=(instFact, infosetFact),
                                        factNumber=(i+1), 
                                        concept=instFact.qname,
                                        expectedPeriodType=ptvPeriodType,
                                        foundPeriodType=instFact.concept.periodType)
                    if ptvBalance and ptvBalance != instFact.concept.balance:
                        modelXbrl.error(u"arelle:infosetTest",
                            _(u"Fact %(factNumber)s balance mismatch %(concept)s expected %(expectedBalance)s found %(foundBalance)s"),
                            modelObject=(instFact, infosetFact),
                                        factNumber=(i+1), 
                                        concept=instFact.qname,
                                        expectedBalance=ptvBalance,
                                        foundBalance=instFact.concept.balance)
                    if ptvDecimals and ptvDecimals != unicode(inferredDecimals(fact)):
                        modelXbrl.error(u"arelle:infosetTest",
                            _(u"Fact %(factNumber)s inferred decimals mismatch %(concept)s expected %(expectedDecimals)s found %(inferredDecimals)s"),
                            modelObject=(instFact, infosetFact),
                                        factNumber=(i+1), 
                                        concept=instFact.qname,
                                        expectedDecimals=ptvDecimals,
                                        inferredDecimals=unicode(inferredDecimals(fact)))
                    if ptvPrecision and ptvPrecision != unicode(inferredPrecision(fact)):
                        modelXbrl.error(u"arelle:infosetTest",
                            _(u"Fact %(factNumber)s inferred precision mismatch %(concept)s expected %(expectedPrecision)s found %(inferredPrecision)s"),
                            modelObject=(instFact, infosetFact),
                                        factNumber=(i+1), 
                                        concept=instFact.qname,
                                        expectedPrecisions=ptvPrecision,
                                        inferredPrecision=unicode(inferredPrecision(fact)))
            
    elif infoset.type == Type.ARCSINFOSET:
        # compare arcs
        for arcElt in XmlUtil.children(infoset.xmlRootElement, u"http://www.xbrl.org/2003/ptv", u"arc"):
            linkType = arcElt.get(u"linkType")
            arcRole = arcElt.get(u"arcRole")
            extRole = arcElt.get(u"extRole")
            fromObj = resolvePath(modelXbrl, arcElt.get(u"fromPath"))
            if fromObj is None:
                modelXbrl.error(u"arelle:infosetTest",
                    _(u"Arc fromPath not found: %(fromPath)s"),
                    modelObject=arcElt, fromPath=arcElt.get(u"fromPath"))
                continue
            if linkType in (u"label", u"reference"):
                labelLang = arcElt.get(u"labelLang")
                resRole = arcElt.get(u"resRole")
                if linkType == u"label":
                    expectedLabel = XmlUtil.text(arcElt)
                    foundLabel = fromObj.label(preferredLabel=resRole,fallbackToQname=False,lang=None,strip=True,linkrole=extRole)
                    if foundLabel != expectedLabel:
                        modelXbrl.error(u"arelle:infosetTest",
                            _(u"Label expected='%(expectedLabel)s', found='%(foundLabel)s'"),
                            modelObject=arcElt, expectedLabel=expectedLabel, foundLabel=foundLabel)
                    continue
                elif linkType == u"reference":
                    expectedRef = XmlUtil.innerText(arcElt)
                    referenceFound = False
                    for refrel in modelXbrl.relationshipSet(XbrlConst.conceptReference,extRole).fromModelObject(fromObj):
                        ref = refrel.toModelObject
                        if resRole == ref.role:
                            foundRef = XmlUtil.innerText(ref)
                            if foundRef != expectedRef:
                                modelXbrl.error(u"arelle:infosetTest",
                                    _(u"Reference inner text expected='%(expectedRef)s, found='%(foundRef)s'"),
                                    modelObject=arcElt, expectedRef=expectedRef, foundRef=foundRef)
                            referenceFound = True
                            break
                    if referenceFound:
                        continue
                modelXbrl.error(u"arelle:infosetTest",
                    _(u"%(linkType)s not found containing '%(text)s' linkRole %(linkRole)s"),
                    modelObject=arcElt, linkType=linkType.title(), text=XmlUtil.innerText(arcElt), linkRole=extRole)
            else:
                toObj = resolvePath(modelXbrl, arcElt.get(u"toPath"))
                if toObj is None:
                    modelXbrl.error(u"arelle:infosetTest",
                        _(u"Arc toPath not found: %(toPath)s"),
                        modelObject=arcElt, toPath=arcElt.get(u"toPath"))
                    continue
                weight = arcElt.get(u"weight")
                if weight is not None:
                    weight = float(weight)
                order = arcElt.get(u"order")
                if order is not None:
                    order = float(order)
                preferredLabel = arcElt.get(u"preferredLabel")
                found = False
                for rel in modelXbrl.relationshipSet(arcRole, extRole).fromModelObject(fromObj):
                    if (rel.toModelObject == toObj and 
                        (weight is None or rel.weight == weight) and 
                        (order is None or rel.order == order)):
                        found = True
                if not found:
                    modelXbrl.error(u"arelle:infosetTest",
                        _(u"Arc not found: from %(fromPath)s, to %(toPath)s, role %(arcRole)s, linkRole $(extRole)s"),
                        modelObject=arcElt, fromPath=arcElt.get(u"fromPath"), toPath=arcElt.get(u"toPath"), arcRole=arcRole, linkRole=extRole)
                    continue
        # validate dimensions of each fact
        factElts = XmlUtil.children(modelXbrl.modelDocument.xmlRootElement, None, u"*")
        for itemElt in XmlUtil.children(infoset.xmlRootElement, None, u"item"):
            try:
                qnElt = XmlUtil.child(itemElt,None,u"qnElement")
                factQname = qname(qnElt, XmlUtil.text(qnElt))
                sPointer = int(XmlUtil.child(itemElt,None,u"sPointer").text)
                factElt = factElts[sPointer - 1] # 1-based xpath indexing
                if factElt.qname != factQname:
                    modelXbrl.error(u"arelle:infosetTest",
                        _(u"Fact %(sPointer)s mismatch Qname, expected %(qnElt)s, observed %(factQname)s"),
                        modelObject=itemElt, sPointer=sPointer, qnElt=factQname, factQname=factElt.qname)
                elif not factElt.isItem or factElt.context is None:
                    modelXbrl.error(u"arelle:infosetTest",
                        _(u"Fact %(sPointer)s has no context: %(qnElt)s"),
                        modelObject=(itemElt,factElt), sPointer=sPointer, qnElt=factQname)
                else:
                    context = factElt.context
                    memberElts = XmlUtil.children(itemElt,None,u"member")
                    numNonDefaults = 0
                    for memberElt in memberElts:
                        dimElt = XmlUtil.child(memberElt, None, u"qnDimension")
                        qnDim = qname(dimElt, XmlUtil.text(dimElt))
                        isDefault = XmlUtil.text(XmlUtil.child(memberElt, None, u"bDefaulted")) == u"true"
                        if not isDefault:
                            numNonDefaults += 1
                        if not ((qnDim in context.qnameDims and not isDefault) or
                                (qnDim in factElt.modelXbrl.qnameDimensionDefaults and isDefault)):
                            modelXbrl.error(u"arelle:infosetTest",
                                _(u"Fact %(sPointer)s (qnElt)s dimension mismatch %(qnDim)s"),
                                modelObject=(itemElt, factElt, context), sPointer=sPointer, qnElt=factQname, qnDim=qnDim)
                    if numNonDefaults != len(context.qnameDims):
                        modelXbrl.error(u"arelle:infosetTest",
                            _(u"Fact %(sPointer)s (qnElt)s dimensions count mismatch"),
                            modelObject=(itemElt, factElt, context), sPointer=sPointer, qnElt=factQname)
            except (IndexError, ValueError, AttributeError), err:
                modelXbrl.error(u"arelle:infosetTest",
                    _(u"Invalid entity fact dimensions infoset sPointer: %(test)s, error details: %(error)s"),
                    modelObject=itemElt, test=XmlUtil.innerTextList(itemElt), error=unicode(err))

def resolvePath(modelXbrl, namespaceId):
    ns, sep, id = (namespaceId or u"#").partition(u"#")
    docs = modelXbrl.namespaceDocs.get(ns)
    if docs: # a list of schema modelDocs with this namespace
        doc = docs[0]
        if id in doc.idObjects:
            return doc.idObjects[id]
    return None

def validateRenderingInfoset(modelXbrl, comparisonFile, sourceDoc):
    from lxml import etree
    try:
        comparisonDoc = etree.parse(comparisonFile)
        sourceIter = sourceDoc.iter()
        comparisonIter = comparisonDoc.iter()
        sourceElt = sourceIter, None.next()
        comparisonElt = comparisonIter, None.next()
        # skip over nsmap elements used to create output trees
        while (sourceElt is not None and sourceElt.tag == u"nsmap"):
            sourceElt = sourceIter, None.next()
        while (comparisonElt is not None and sourceElt.tag == u"nsmap"):
            comparisonElt = comparisonIter, None.next()
        while (sourceElt is not None and comparisonElt is not None):
            while (isinstance(sourceElt, etree._Comment)):
                sourceElt = sourceIter, None.next()
            while (isinstance(comparisonElt, etree._Comment)):
                comparisonElt = comparisonIter, None.next()
            sourceEltTag = sourceElt.tag if sourceElt is not None else u'(no more elements)'
            comparisonEltTag = comparisonElt.tag if comparisonElt is not None else u'(no more elements)'
            if sourceEltTag != comparisonEltTag:
                modelXbrl.error(u"arelle:infosetElementMismatch",
                    _(u"Infoset expecting %(elt1)s found %(elt2)s source line %(elt1line)s comparison line %(elt2line)s"),
                    modelObject=modelXbrl, elt1=sourceEltTag, elt2=comparisonEltTag,
                    elt1line=sourceElt.sourceline, elt2line=comparisonElt.sourceline)
            else:
                text1 = (sourceElt.text or u'').strip() or u'(none)'
                text2 = (comparisonElt.text or u'').strip() or u'(none)'
                if text1 != text2:
                    modelXbrl.error(u"arelle:infosetTextMismatch",
                        _(u"Infoset comparison element %(elt)s expecting text %(text1)s found %(text2)s source line %(elt1line)s comparison line %(elt2line)s"),
                        modelObject=modelXbrl, elt=sourceElt.tag, text1=text1, text2=text2,
                        elt1line=sourceElt.sourceline, elt2line=comparisonElt.sourceline)
                attrs1 = dict(sourceElt.items())
                attrs2 = dict(comparisonElt.items())
                # remove attributes not to be compared
                for attr in (u"{http://www.w3.org/XML/1998/namespace}base",
                             ):
                    if attr in attrs1: del attrs1[attr]
                    if attr in attrs2: del attrs2[attr]
                if attrs1 != attrs2:
                    modelXbrl.error(u"arelle:infosetAttributesMismatch",
                        _(u"Infoset comparison element %(elt)s expecting attributes %(attrs1)s found %(attrs2)s source line %(elt1line)s comparison line %(elt2line)s"),
                        modelObject=modelXbrl, elt=sourceElt.tag, 
                        attrs1=u', '.join(u'{0}="{1}"'.format(k,v) for k,v in sorted(attrs1.items())), 
                        attrs2=u', '.join(u'{0}="{1}"'.format(k,v) for k,v in sorted(attrs2.items())),
                        elt1line=sourceElt.sourceline, elt2line=comparisonElt.sourceline)
            sourceElt = sourceIter, None.next()
            comparisonElt = comparisonIter, None.next()
    except (IOError, etree.LxmlError), err:
        modelXbrl.error(u"arelle:infosetFileError",
            _(u"Infoset comparison file %(xmlfile)s error %(error)s"),
            modelObject=modelXbrl, xmlfile=comparisonFile, error=unicode(err))


