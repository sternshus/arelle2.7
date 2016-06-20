from arelle.ModelValue import qname
import os

xsd = u"http://www.w3.org/2001/XMLSchema"
qnXsdSchema = qname(u"{http://www.w3.org/2001/XMLSchema}xsd:schema")
qnXsdAppinfo = qname(u"{http://www.w3.org/2001/XMLSchema}xsd:appinfo")
qnXsdDefaultType = qname(u"{http://www.w3.org/2001/XMLSchema}xsd:anyType")
xsi = u"http://www.w3.org/2001/XMLSchema-instance"
qnXsiNil = qname(xsi,u"xsi:nil") # need default prefix in qname
qnXmlLang = qname(u"{http://www.w3.org/XML/1998/namespace}xml:lang")
builtinAttributes = set([qnXsiNil,
                     qname(xsi,u"xsi:type"),
                     qname(xsi,u"xsi:schemaLocation")
                     ,qname(xsi,u"xsi:noNamespaceSchemaLocation")])
xml = u"http://www.w3.org/XML/1998/namespace"
xbrli = u"http://www.xbrl.org/2003/instance"
qnNsmap = qname(u"nsmap") # artificial parent for insertion of xmlns in saving xml documents
qnXbrliXbrl = qname(u"{http://www.xbrl.org/2003/instance}xbrli:xbrl")
qnXbrliItem = qname(u"{http://www.xbrl.org/2003/instance}xbrli:item")
qnXbrliNumerator = qname(u"{http://www.xbrl.org/2003/instance}xbrli:numerator")
qnXbrliDenominator = qname(u"{http://www.xbrl.org/2003/instance}xbrli:denominator")
qnXbrliTuple = qname(u"{http://www.xbrl.org/2003/instance}xbrli:tuple")
qnXbrliContext = qname(u"{http://www.xbrl.org/2003/instance}xbrli:context")
qnXbrliPeriod = qname(u"{http://www.xbrl.org/2003/instance}xbrli:period")
qnXbrliIdentifier = qname(u"{http://www.xbrl.org/2003/instance}xbrli:identifier")
qnXbrliUnit = qname(u"{http://www.xbrl.org/2003/instance}xbrli:unit")
qnXbrliStringItemType = qname(u"{http://www.xbrl.org/2003/instance}xbrli:stringItemType")
qnXbrliMonetaryItemType = qname(u"{http://www.xbrl.org/2003/instance}xbrli:monetaryItemType")
qnXbrliDateItemType = qname(u"{http://www.xbrl.org/2003/instance}xbrli:dateItemType")
qnXbrliDurationItemType = qname(u"{http://www.xbrl.org/2003/instance}xbrli:durationItemType")
qnXbrliPure = qname(u"{http://www.xbrl.org/2003/instance}xbrli:pure")
qnXbrliShares = qname(u"{http://www.xbrl.org/2003/instance}xbrli:shares")
qnInvalidMeasure = qname(u"{http://arelle.org}arelle:invalidMeasureQName")
qnXbrliDateUnion = qname(u"{http://www.xbrl.org/2003/instance}xbrli:dateUnion")
qnDateUnionXsdTypes = [qname(u"{http://www.w3.org/2001/XMLSchema}xsd:date"),qname(u"{http://www.w3.org/2001/XMLSchema}xsd:dateTime")]
qnXbrliDecimalsUnion = qname(u"{http://www.xbrl.org/2003/instance}xbrli:decimalsType")
qnXbrliPrecisionUnion = qname(u"{http://www.xbrl.org/2003/instance}xbrli:precisionType")
qnXbrliNonZeroDecimalUnion = qname(u"{http://www.xbrl.org/2003/instance}xbrli:nonZeroDecimal")
link = u"http://www.xbrl.org/2003/linkbase"
qnLinkLoc = qname(u"{http://www.xbrl.org/2003/linkbase}link:loc")
qnLinkLabelLink = qname(u"{http://www.xbrl.org/2003/linkbase}link:labelLink")
qnLinkLabelArc = qname(u"{http://www.xbrl.org/2003/linkbase}link:labelArc")
qnLinkLabel = qname(u"{http://www.xbrl.org/2003/linkbase}link:label")
qnLinkReferenceLink = qname(u"{http://www.xbrl.org/2003/linkbase}link:referenceLink")
qnLinkReferenceArc = qname(u"{http://www.xbrl.org/2003/linkbase}link:referenceArc")
qnLinkReference = qname(u"{http://www.xbrl.org/2003/linkbase}link:reference")
qnLinkPart = qname(u"{http://www.xbrl.org/2003/linkbase}link:part")
qnLinkFootnoteLink = qname(u"{http://www.xbrl.org/2003/linkbase}link:footnoteLink")
qnLinkFootnoteArc = qname(u"{http://www.xbrl.org/2003/linkbase}link:footnoteArc")
qnLinkFootnote = qname(u"{http://www.xbrl.org/2003/linkbase}link:footnote")
qnLinkPresentationLink = qname(u"{http://www.xbrl.org/2003/linkbase}link:presentationLink")
qnLinkPresentationArc = qname(u"{http://www.xbrl.org/2003/linkbase}link:presentationArc")
qnLinkCalculationLink = qname(u"{http://www.xbrl.org/2003/linkbase}link:calculationLink")
qnLinkCalculationArc = qname(u"{http://www.xbrl.org/2003/linkbase}link:calculationArc")
qnLinkDefinitionLink = qname(u"{http://www.xbrl.org/2003/linkbase}link:definitionLink")
qnLinkDefinitionArc = qname(u"{http://www.xbrl.org/2003/linkbase}link:definitionArc")
gen = u"http://xbrl.org/2008/generic"
qnGenLink = qname(u"{http://xbrl.org/2008/generic}gen:link")
qnGenArc = qname(u"{http://xbrl.org/2008/generic}gen:arc")
elementReference = u"http://xbrl.org/arcrole/2008/element-reference"
genReference = u"http://xbrl.org/2008/reference"
qnGenReference = qname(u"{http://xbrl.org/2008/reference}reference")
elementLabel = u"http://xbrl.org/arcrole/2008/element-label"
genLabel = u"http://xbrl.org/2008/label"
qnGenLabel = qname(u"{http://xbrl.org/2008/label}label")
elementReference = u"http://xbrl.org/arcrole/2008/element-reference"
xbrldt = u"http://xbrl.org/2005/xbrldt"
qnXbrldtHypercubeItem = qname(u"{http://xbrl.org/2005/xbrldt}xbrldt:hypercubeItem")
qnXbrldtDimensionItem = qname(u"{http://xbrl.org/2005/xbrldt}xbrldt:dimensionItem")
qnXbrldtContextElement = qname(u"{http://xbrl.org/2005/xbrldt}xbrldt:contextElement")
xbrldi = u"http://xbrl.org/2006/xbrldi"
qnXbrldiExplicitMember = qname(u"{http://xbrl.org/2006/xbrldi}xbrldi:explicitMember")
qnXbrldiTypedMember = qname(u"{http://xbrl.org/2006/xbrldi}xbrldi:typedMember")
xlink = u"http://www.w3.org/1999/xlink"
xl = u"http://www.xbrl.org/2003/XLink"
qnXlExtended = qname(u"{http://www.xbrl.org/2003/XLink}xl:extended")
qnXlLocator = qname(u"{http://www.xbrl.org/2003/XLink}xl:locator")
qnXlResource = qname(u"{http://www.xbrl.org/2003/XLink}xl:resource")
qnXlExtendedType = qname(u"{http://www.xbrl.org/2003/XLink}xl:extendedType")
qnXlLocatorType = qname(u"{http://www.xbrl.org/2003/XLink}xl:locatorType")
qnXlResourceType = qname(u"{http://www.xbrl.org/2003/XLink}xl:resourceType")
qnXlArcType = qname(u"{http://www.xbrl.org/2003/XLink}xl:arcType")
xhtml = u"http://www.w3.org/1999/xhtml"
ixbrl = u"http://www.xbrl.org/2008/inlineXBRL"
ixbrl11 = u"http://www.xbrl.org/2013/inlineXBRL"
ixbrlAll = set([ixbrl, ixbrl11])
qnIXbrlResources = qname(u"{http://www.xbrl.org/2008/inlineXBRL}resources")
qnIXbrlTuple = qname(u"{http://www.xbrl.org/2008/inlineXBRL}tuple")
qnIXbrlNonNumeric = qname(u"{http://www.xbrl.org/2008/inlineXBRL}nonNumeric")
qnIXbrlNonFraction = qname(u"{http://www.xbrl.org/2008/inlineXBRL}nonFraction")
qnIXbrlFraction = qname(u"{http://www.xbrl.org/2008/inlineXBRL}fraction")
qnIXbrlNumerator = qname(u"{http://www.xbrl.org/2008/inlineXBRL}numerator")
qnIXbrlDenominator = qname(u"{http://www.xbrl.org/2008/inlineXBRL}denominator")
qnIXbrlFootnote = qname(u"{http://www.xbrl.org/2008/inlineXBRL}footnote")
qnIXbrl11Resources = qname(u"{http://www.xbrl.org/2013/inlineXBRL}resources")
qnIXbrl11Tuple = qname(u"{http://www.xbrl.org/2013/inlineXBRL}tuple")
qnIXbrl11NonNumeric = qname(u"{http://www.xbrl.org/2013/inlineXBRL}nonNumeric")
qnIXbrl11NonFraction = qname(u"{http://www.xbrl.org/2013/inlineXBRL}nonFraction")
qnIXbrl11Fraction = qname(u"{http://www.xbrl.org/2013/inlineXBRL}fraction")
qnIXbrl11Numerator = qname(u"{http://www.xbrl.org/2013/inlineXBRL}numerator")
qnIXbrl11Denominator = qname(u"{http://www.xbrl.org/2013/inlineXBRL}denominator")
qnIXbrl11Footnote = qname(u"{http://www.xbrl.org/2013/inlineXBRL}footnote")
ixAttributes = set(qname(n, noPrefixIsNoNamespace=True)
                   for n in (u"escape", u"footnoteRefs", u"format", u"name", u"order", u"scale", u"sign", 
                             u"target", u"tupleRef", u"tupleID"))
conceptLabel = u"http://www.xbrl.org/2003/arcrole/concept-label"
conceptReference = u"http://www.xbrl.org/2003/arcrole/concept-reference"
footnote = u"http://www.xbrl.org/2003/role/footnote"
factFootnote = u"http://www.xbrl.org/2003/arcrole/fact-footnote"
factExplanatoryFact = u"http://www.xbrl.org/2009/arcrole/fact-explanatoryFact"
parentChild = u"http://www.xbrl.org/2003/arcrole/parent-child"
summationItem = u"http://www.xbrl.org/2003/arcrole/summation-item"
essenceAlias = u"http://www.xbrl.org/2003/arcrole/essence-alias"
similarTuples = u"http://www.xbrl.org/2003/arcrole/similar-tuples"
requiresElement = u"http://www.xbrl.org/2003/arcrole/requires-element"
generalSpecial = u"http://www.xbrl.org/2003/arcrole/general-special"
dimStartsWith = u"http://xbrl.org/int/dim"
all = u"http://xbrl.org/int/dim/arcrole/all"
notAll = u"http://xbrl.org/int/dim/arcrole/notAll"
hypercubeDimension = u"http://xbrl.org/int/dim/arcrole/hypercube-dimension"
dimensionDomain = u"http://xbrl.org/int/dim/arcrole/dimension-domain"
domainMember = u"http://xbrl.org/int/dim/arcrole/domain-member"
dimensionDefault = u"http://xbrl.org/int/dim/arcrole/dimension-default"
dtrTypesStartsWith = u"http://www.xbrl.org/dtr/type/"
dtrNumeric = u"http://www.xbrl.org/dtr/type/numeric"
defaultLinkRole = u"http://www.xbrl.org/2003/role/link"
iso4217 = u"http://www.xbrl.org/2003/iso4217"
def qnIsoCurrency(token):
    return qname(iso4217, u"iso4217:" + token) if token else None
standardLabel = u"http://www.xbrl.org/2003/role/label"
genStandardLabel = u"http://www.xbrl.org/2008/role/label"
documentationLabel = u"http://www.xbrl.org/2003/role/documentation"
genDocumentationLabel = u"http://www.xbrl.org/2008/role/documentation"
standardReference = u"http://www.xbrl.org/2003/role/reference"
genStandardReference = u"http://www.xbrl.org/2010/role/reference"
periodStartLabel = u"http://www.xbrl.org/2003/role/periodStartLabel"
periodEndLabel = u"http://www.xbrl.org/2003/role/periodEndLabel"
verboseLabel = u"http://www.xbrl.org/2003/role/verboseLabel"
terseLabel = u"http://www.xbrl.org/2003/role/terseLabel"
conceptNameLabelRole = u"XBRL-concept-name" # fake label role to show concept QName instead of label
xlinkLinkbase = u"http://www.w3.org/1999/xlink/properties/linkbase"

utr = u"http://www.xbrl.org/2009/utr"

ver10 = u"http://xbrl.org/2010/versioning-base"
# 2010 names
vercb = u"http://xbrl.org/2010/versioning-concept-basic"
verce = u"http://xbrl.org/2010/versioning-concept-extended"
verrels = u"http://xbrl.org/2010/versioning-relationship-sets"
veria = u"http://xbrl.org/2010/versioning-instance-aspects"
# 2013 names
ver = u"http://xbrl.org/2013/versioning-base"
vercu = u"http://xbrl.org/2013/versioning-concept-use"
vercd = u"http://xbrl.org/2013/versioning-concept-details"
verdim = u"http://xbrl.org/2013/versioning-dimensions"
verPrefixNS = {u"ver":ver,
               u"vercu":vercu,
               u"vercd":vercd,
               u"verrels":verrels,
               u"verdim":verdim,
               }

# extended enumeration spec
enum = u"http://xbrl.org/2014/extensible-enumerations"
qnEnumerationItemType = qname(u"{http://xbrl.org/2014/extensible-enumerations}enum:enumerationItemType")
attrEnumerationDomain = u"{http://xbrl.org/2014/extensible-enumerations}domain"
attrEnumerationLinkrole = u"{http://xbrl.org/2014/extensible-enumerations}linkrole"
attrEnumerationUsable = u"{http://xbrl.org/2014/extensible-enumerations}headUsable"

# formula specs
variable = u"http://xbrl.org/2008/variable"
qnVariableSet = qname(u"{http://xbrl.org/2008/variable}variable:variableSet")
qnVariableVariable = qname(u"{http://xbrl.org/2008/variable}variable:variable")
qnVariableFilter = qname(u"{http://xbrl.org/2008/variable}variable:filter")
qnVariableFilterArc = qname(u"{http://xbrl.org/2008/variable}variable:variableFilterArc")
qnParameter = qname(u"{http://xbrl.org/2008/variable}variable:parameter")
qnFactVariable = qname(u"{http://xbrl.org/2008/variable}variable:factVariable")
qnGeneralVariable = qname(u"{http://xbrl.org/2008/variable}variable:generalVariable")
qnPrecondition = qname(u"{http://xbrl.org/2008/variable}variable:precondition")
qnEqualityDefinition = qname(u"{http://xbrl.org/2008/variable}variable:equalityDefinition")
qnEqualityTestA = qname(u"{http://xbrl.org/2008/variable/aspectTest}aspectTest:a")
qnEqualityTestB = qname(u"{http://xbrl.org/2008/variable/aspectTest}aspectTest:b")
formula = u"http://xbrl.org/2008/formula"
tuple = u"http://xbrl.org/2010/formula/tuple"
qnFormula = qname(u"{http://xbrl.org/2008/formula}formula:formula")
qnTuple = qname(u"{http://xbrl.org/2010/formula/tuple}tuple:tuple")
qnFormulaUncovered = qname(u"{http://xbrl.org/2008/formula}formula:uncovered")
qnFormulaDimensionSAV = qname(u"{http://xbrl.org/2008/formula}DimensionSAV") #signal that dimension aspect should use SAV of this dimension
qnFormulaOccEmpty = qname(u"{http://xbrl.org/2008/formula}occEmpty") #signal that OCC aspect should omit the SAV values
ca = u"http://xbrl.org/2008/assertion/consistency"
qnConsistencyAssertion = qname(u"{http://xbrl.org/2008/assertion/consistency}ca:consistencyAssertion")
qnCaAspectMatchedFacts = qname(u"{http://xbrl.org/2008/assertion/consistency}ca:aspect-matched-facts")
qnCaAcceptanceRadius = qname(u"{http://xbrl.org/2008/assertion/consistency}ca:ca:acceptance-radius")
qnCaAbsoluteAcceptanceRadiusExpression = qname(u"{http://xbrl.org/2008/assertion/consistency}ca:absolute-acceptance-radius-expression")
qnCaProportionalAcceptanceRadiusExpression = qname(u"{http://xbrl.org/2008/assertion/consistency}ca:proportional-acceptance-radius-expression")
ea = u"http://xbrl.org/2008/assertion/existence"
qnExistenceAssertion = qname(u"{http://xbrl.org/2008/assertion/existence}ea:existenceAssertion")
qnEaTestExpression = qname(ea,u'test-expression')
va = u"http://xbrl.org/2008/assertion/value"
qnValueAssertion = qname(u"{http://xbrl.org/2008/assertion/value}va:valueAssertion")
qnVaTestExpression = qname(va,u'test-expression')
variable = u"http://xbrl.org/2008/variable"
formulaStartsWith = u"http://xbrl.org/arcrole/20"
equalityDefinition = u"http://xbrl.org/arcrole/2008/equality-definition"
qnEqualityDefinition = qname(u"{http://xbrl.org/2008/variable}variable:equalityDefinition")
variableSet = u"http://xbrl.org/arcrole/2008/variable-set"
variableSetFilter = u"http://xbrl.org/arcrole/2008/variable-set-filter"
variableFilter = u"http://xbrl.org/arcrole/2008/variable-filter"
variableSetPrecondition = u"http://xbrl.org/arcrole/2008/variable-set-precondition"
equalityDefinition = u"http://xbrl.org/arcrole/2008/equality-definition"
consistencyAssertionFormula = u"http://xbrl.org/arcrole/2008/consistency-assertion-formula"
consistencyAssertionParameter = u"http://xbrl.org/arcrole/2008/consistency-assertion-parameter"
validation = u"http://xbrl.org/2008/validation"
qnAssertion = qname(u"{http://xbrl.org/2008/validation}validation:assertion")
qnVariableSetAssertion = qname(u"{http://xbrl.org/2008/validation}validation:variableSetAssertion")
qnAssertionSet = qname(u"{http://xbrl.org/2008/validation}validation:assertionSet")
assertionSet = u"http://xbrl.org/arcrole/2008/assertion-set"
assertionSatisfiedSeverity = u"http://xbrl.org/arcrole/2014/assertion-satisfied-severity"
assertionUnsatisfiedSeverity = u"http://xbrl.org/arcrole/2014/assertion-unsatisfied-severity"
qnAssertionSeverity = qname(u"{http://xbrl.org/2014/assertion-severity}sev:severity")

acf = u"http://xbrl.org/2010/filter/aspect-cover"
qnAspectCover = qname(u"{http://xbrl.org/2010/filter/aspect-cover}acf:aspectCover")
bf = u"http://xbrl.org/2008/filter/boolean"
qnAndFilter = qname(u"{http://xbrl.org/2008/filter/boolean}bf:andFilter")
qnOrFilter = qname(u"{http://xbrl.org/2008/filter/boolean}bf:orFilter")
booleanFilter = u"http://xbrl.org/arcrole/2008/boolean-filter"
cfi = u"http://xbrl.org/2010/custom-function"
functionImplementation = u"http://xbrl.org/arcrole/2010/function-implementation"
qnCustomFunctionSignature = qname(u"{http://xbrl.org/2008/variable}cfi:function")
qnCustomFunctionImplementation = qname(u"{http://xbrl.org/2010/custom-function}cfi:implementation")
crf = u"http://xbrl.org/2010/filter/concept-relation"
qnConceptRelation = qname(u"{http://xbrl.org/2010/filter/concept-relation}crf:conceptRelation")
cf = u"http://xbrl.org/2008/filter/concept"
qnConceptName = qname(u"{http://xbrl.org/2008/filter/concept}cf:conceptName")
qnConceptPeriodType = qname(u"{http://xbrl.org/2008/filter/concept}cf:conceptPeriodType")
qnConceptBalance = qname(u"{http://xbrl.org/2008/filter/concept}cf:conceptBalance")
qnConceptCustomAttribute = qname(u"{http://xbrl.org/2008/filter/concept}cf:conceptCustomAttribute")
qnConceptDataType = qname(u"{http://xbrl.org/2008/filter/concept}cf:conceptDataType")
qnConceptSubstitutionGroup = qname(u"{http://xbrl.org/2008/filter/concept}cf:conceptSubstitutionGroup")
cfcn = u"http://xbrl.org/2008/conformance/function"
df = u"http://xbrl.org/2008/filter/dimension"
qnExplicitDimension = qname(u"{http://xbrl.org/2008/filter/dimension}df:explicitDimension")
qnTypedDimension = qname(u"{http://xbrl.org/2008/filter/dimension}df:typedDimension")
ef = u"http://xbrl.org/2008/filter/entity"
qnEntityIdentifier = qname(u"{http://xbrl.org/2008/filter/entity}ef:identifier")
qnEntitySpecificIdentifier = qname(u"{http://xbrl.org/2008/filter/entity}ef:specificIdentifier")
qnEntitySpecificScheme = qname(u"{http://xbrl.org/2008/filter/entity}ef:specificScheme")
qnEntityRegexpIdentifier = qname(u"{http://xbrl.org/2008/filter/entity}ef:regexpIdentifier")
qnEntityRegexpScheme = qname(u"{http://xbrl.org/2008/filter/entity}ef:regexpScheme")
function = u"http://xbrl.org/2008/function"
fn = u"http://www.w3.org/2005/xpath-functions"
xfi = u"http://www.xbrl.org/2008/function/instance"
qnXfiRoot = qname(u"{http://www.xbrl.org/2008/function/instance}xfi:root")
xff = u"http://www.xbrl.org/2010/function/formula"
gf = u"http://xbrl.org/2008/filter/general"
qnGeneral = qname(u"{http://xbrl.org/2008/filter/general}gf:general")
instances = u"http://xbrl.org/2010/variable/instance"
qnInstance = qname(instances,u"instances:instance")
instanceVariable = u"http://xbrl.org/arcrole/2010/instance-variable"
formulaInstance = u"http://xbrl.org/arcrole/2010/formula-instance"
qnStandardInputInstance = qname(instances,u"instances:standard-input-instance")
qnStandardOutputInstance = qname(instances,u"instances:standard-output-instance")
mf = u"http://xbrl.org/2008/filter/match"
qnMatchConcept = qname(u"{http://xbrl.org/2008/filter/match}mf:matchConcept")
qnMatchDimension = qname(u"{http://xbrl.org/2008/filter/match}mf:matchDimension")
qnMatchEntityIdentifier = qname(u"{http://xbrl.org/2008/filter/match}mf:matchEntityIdentifier")
qnMatchLocation = qname(u"{http://xbrl.org/2008/filter/match}mf:matchLocation")
qnMatchPeriod = qname(u"{http://xbrl.org/2008/filter/match}mf:matchPeriod")
qnMatchSegment = qname(u"{http://xbrl.org/2008/filter/match}mf:matchSegment")
qnMatchScenario = qname(u"{http://xbrl.org/2008/filter/match}mf:matchScenario")
qnMatchNonXDTSegment = qname(u"{http://xbrl.org/2008/filter/match}mf:matchNonXDTSegment")
qnMatchNonXDTScenario = qname(u"{http://xbrl.org/2008/filter/match}mf:matchNonXDTScenario")
qnMatchUnit = qname(u"{http://xbrl.org/2008/filter/match}mf:matchUnit")
msg = u"http://xbrl.org/2010/message"
qnMessage = qname(u"{http://xbrl.org/2010/message}message")
assertionSatisfiedMessage = u"http://xbrl.org/arcrole/2010/assertion-satisfied-message"
assertionUnsatisfiedMessage = u"http://xbrl.org/arcrole/2010/assertion-unsatisfied-message"
standardMessage = u"http://www.xbrl.org/2010/role/message"
terseMessage = u"http://www.xbrl.org/2010/role/terseMessage"
verboseMessage = u"http://www.xbrl.org/2010/role/verboseMessage"
pf = u"http://xbrl.org/2008/filter/period"
qnPeriod = qname(u"{http://xbrl.org/2008/filter/period}pf:period")
qnPeriodStart = qname(u"{http://xbrl.org/2008/filter/period}pf:periodStart")
qnPeriodEnd = qname(u"{http://xbrl.org/2008/filter/period}pf:periodEnd")
qnPeriodInstant = qname(u"{http://xbrl.org/2008/filter/period}pf:periodInstant")
qnForever = qname(u"{http://xbrl.org/2008/filter/period}pf:forever")
qnInstantDuration = qname(u"{http://xbrl.org/2008/filter/period}pf:instantDuration")
registry = u"http://xbrl.org/2008/registry"
rf = u"http://xbrl.org/2008/filter/relative"
qnRelativeFilter = qname(u"{http://xbrl.org/2008/filter/relative}rf:relativeFilter")
ssf = u"http://xbrl.org/2008/filter/segment-scenario"
qnSegmentFilter = qname(u"{http://xbrl.org/2008/filter/segment-scenario}ssf:segment")
qnScenarioFilter = qname(u"{http://xbrl.org/2008/filter/segment-scenario}ssf:scenario")
tf = u"http://xbrl.org/2008/filter/tuple"
qnAncestorFilter = qname(u"{http://xbrl.org/2008/filter/tuple}tf:ancestorFilter")
qnLocationFilter = qname(u"{http://xbrl.org/2008/filter/tuple}tf:locationFilter")
qnParentFilter = qname(u"{http://xbrl.org/2008/filter/tuple}tf:parentFilter")
qnSiblingFilter = qname(u"{http://xbrl.org/2008/filter/tuple}tf:siblingFilter")
uf = u"http://xbrl.org/2008/filter/unit"
qnSingleMeasure = qname(u"{http://xbrl.org/2008/filter/unit}uf:singleMeasure")
qnGeneralMeasures = qname(u"{http://xbrl.org/2008/filter/unit}uf:generalMeasures")
vf = u"http://xbrl.org/2008/filter/value"
qnNilFilter = qname(u"{http://xbrl.org/2008/filter/value}vf:nil")
qnPrecisionFilter = qname(u"{http://xbrl.org/2008/filter/value}vf:precision")
xpath2err = u"http://www.w3.org/2005/xqt-errors"
variablesScope = u"http://xbrl.org/arcrole/2010/variables-scope"

# 2014-MM-DD current IWD
tableMMDD = u"http://xbrl.org/PWD/2014-MM-DD/table"
tableModelMMDD = u"http://xbrl.org/PWD/2014-MM-DD/table/model"
tableBreakdownMMDD = u"http://xbrl.org/arcrole/PWD/2014-MM-DD/table-breakdown"
tableBreakdownTreeMMDD = u"http://xbrl.org/arcrole/PWD/2014-MM-DD/breakdown-tree"
tableDefinitionNodeSubtreeMMDD = u"http://xbrl.org/arcrole/PWD/2014-MM-DD/definition-node-subtree"
tableFilterMMDD = u"http://xbrl.org/arcrole/PWD/2014-MM-DD/table-filter"
tableAspectNodeFilterMMDD = u"http://xbrl.org/arcrole/PWD/2014-MM-DD/aspect-node-filter"
tableParameterMMDD = u"http://xbrl.org/arcrole/PWD/2014-MM-DD/table-parameter"
qnTableTableMMDD = qname(u"{http://xbrl.org/PWD/2014-MM-DD/table}table:table")
qnTableBreakdownMMDD = qname(u"{http://xbrl.org/PWD/2014-MM-DD/table}table:breakdown")
qnTableRuleNodeMMDD = qname(u"{http://xbrl.org/PWD/2014-MM-DD/table}table:ruleNode")
qnTableRuleSetMMDD = qname(u"{http://xbrl.org/PWD/2014-MM-DD/table}table:ruleSet")
qnTableDefinitionNodeMMDD = qname(u"{http://xbrl.org/PWD/2014-MM-DD/table}table:definitionNode")
qnTableClosedDefinitionNodeMMDD = qname(u"{http://xbrl.org/PWD/2014-MM-DD/table}table:closedDefinitionNode")
qnTableConceptRelationshipNodeMMDD = qname(u"{http://xbrl.org/PWD/2014-MM-DD/table}table:conceptRelationshipNode")
qnTableDimensionRelationshipNodeMMDD = qname(u"{http://xbrl.org/PWD/2014-MM-DD/table}table:dimensionRelationshipNode")
qnTableAspectNodeMMDD = qname(u"{http://xbrl.org/PWD/2014-MM-DD/table}table:aspectNode")

# REC
table = u"http://xbrl.org/2014/table"
tableModel = u"http://xbrl.org/2014/table/model"
tableBreakdown = u"http://xbrl.org/arcrole/2014/table-breakdown"
tableBreakdownTree = u"http://xbrl.org/arcrole/2014/breakdown-tree"
tableDefinitionNodeSubtree = u"http://xbrl.org/arcrole/2014/definition-node-subtree"
tableFilter = u"http://xbrl.org/arcrole/2014/table-filter"
tableAspectNodeFilter = u"http://xbrl.org/arcrole/2014/aspect-node-filter"
tableParameter = u"http://xbrl.org/arcrole/2014/table-parameter"
qnTableTable = qname(u"{http://xbrl.org/2014/table}table:table")
qnTableBreakdown = qname(u"{http://xbrl.org/2014/table}table:breakdown")
qnTableRuleNode = qname(u"{http://xbrl.org/2014/table}table:ruleNode")
qnTableRuleSet = qname(u"{http://xbrl.org/2014/table}table:ruleSet")
qnTableDefinitionNode = qname(u"{http://xbrl.org/2014/table}table:definitionNode")
qnTableClosedDefinitionNode = qname(u"{http://xbrl.org/2014/table}table:closedDefinitionNode")
qnTableConceptRelationshipNode = qname(u"{http://xbrl.org/2014/table}table:conceptRelationshipNode")
qnTableDimensionRelationshipNode = qname(u"{http://xbrl.org/2014/table}table:dimensionRelationshipNode")
qnTableAspectNode = qname(u"{http://xbrl.org/2014/table}table:aspectNode")

# 2013-MM-DD current CR
u'''
table = "http://xbrl.org/CR/2013-11-13/table"
tableModel = "http://xbrl.org/CR/2013-11-13/table/model"
tableBreakdown = "http://xbrl.org/arcrole/CR/2013-11-13/table-breakdown"
tableBreakdownTree = "http://xbrl.org/arcrole/CR/2013-11-13/breakdown-tree"
tableDefinitionNodeSubtree = "http://xbrl.org/arcrole/CR/2013-11-13/definition-node-subtree"
tableFilter = "http://xbrl.org/arcrole/CR/2013-11-13/table-filter"
tableAspectNodeFilter = "http://xbrl.org/arcrole/CR/2013-11-13/aspect-node-filter"
tableParameter = "http://xbrl.org/arcrole/CR/2013-11-13/table-parameter"
qnTableTable = qname("{http://xbrl.org/CR/2013-11-13/table}table:table")
qnTableBreakdown = qname("{http://xbrl.org/CR/2013-11-13/table}table:breakdown")
qnTableRuleNode = qname("{http://xbrl.org/CR/2013-11-13/table}table:ruleNode")
qnTableRuleSet = qname("{http://xbrl.org/CR/2013-11-13/table}table:ruleSet")
qnTableDefinitionNode = qname("{http://xbrl.org/CR/2013-11-13/table}table:definitionNode")
qnTableClosedDefinitionNode = qname("{http://xbrl.org/CR/2013-11-13/table}table:closedDefinitionNode")
qnTableConceptRelationshipNode = qname("{http://xbrl.org/CR/2013-11-13/table}table:conceptRelationshipNode")
qnTableDimensionRelationshipNode = qname("{http://xbrl.org/CR/2013-11-13/table}table:dimensionRelationshipNode")
qnTableAspectNode = qname("{http://xbrl.org/CR/2013-11-13/table}table:aspectNode")
'''

# prior 2013-08-28 PWD
u''' not supported
table = "http://xbrl.org/PWD/2013-08-28/table"
tableModel = "http://xbrl.org/PWD/2013-08-28/table/model"
tableBreakdown = "http://xbrl.org/arcrole/PWD/2013-08-28/table-breakdown"
tableBreakdownTree = "http://xbrl.org/arcrole/PWD/2013-08-28/breakdown-tree"
tableDefinitionNodeSubtree = "http://xbrl.org/arcrole/PWD/2013-08-28/definition-node-subtree"
tableFilter = "http://xbrl.org/arcrole/PWD/2013-08-28/table-filter"
tableAspectNodeFilter = "http://xbrl.org/arcrole/PWD/2013-08-28/aspect-node-filter"
tableParameter = "http://xbrl.org/arcrole/PWD/2013-08-28/table-parameter"
qnTableTable = qname("{http://xbrl.org/PWD/2013-08-28/table}table:table")
qnTableBreakdown = qname("{http://xbrl.org/PWD/2013-08-28/table}table:breakdown")
qnTableRuleNode = qname("{http://xbrl.org/PWD/2013-08-28/table}table:ruleNode")
qnTableClosedDefinitionNode = qname("{http://xbrl.org/PWD/2013-08-28/table}table:closedDefinitionNode")
qnTableConceptRelationshipNode = qname("{http://xbrl.org/PWD/2013-08-28/table}table:conceptRelationshipNode")
qnTableDimensionRelationshipNode = qname("{http://xbrl.org/PWD/2013-08-28/table}table:dimensionRelationshipNode")
qnTableAspectNode = qname("{http://xbrl.org/PWD/2013-08-28/table}table:aspectNode")
'''

# prior 2013-05-17 PWD
table201305 = u"http://xbrl.org/PWD/2013-05-17/table"
tableModel201305 = u"http://xbrl.org/PWD/2013-05-17/table/model"
tableBreakdown201305 = u"http://xbrl.org/arcrole/PWD/2013-05-17/table-breakdown"
tableBreakdownTree201305 = u"http://xbrl.org/arcrole/PWD/2013-05-17/breakdown-tree"
tableDefinitionNodeSubtree201305 = u"http://xbrl.org/arcrole/PWD/2013-05-17/definition-node-subtree"
tableFilter201305 = u"http://xbrl.org/arcrole/PWD/2013-05-17/table-filter"
tableAspectNodeFilter201305 = u"http://xbrl.org/arcrole/PWD/2013-05-17/aspect-node-filter"
qnTableTable201305 = qname(u"{http://xbrl.org/PWD/2013-05-17/table}table:table")
qnTableBreakdown201305 = qname(u"{http://xbrl.org/PWD/2013-05-17/table}table:breakdown")
qnTableRuleNode201305 = qname(u"{http://xbrl.org/PWD/2013-05-17/table}table:ruleNode")
qnTableClosedDefinitionNode201305 = qname(u"{http://xbrl.org/PWD/2013-05-17/table}table:closedDefinitionNode")
qnTableConceptRelationshipNode201305 = qname(u"{http://xbrl.org/PWD/2013-05-17/table}table:conceptRelationshipNode")
qnTableDimensionRelationshipNode201305 = qname(u"{http://xbrl.org/PWD/2013-05-17/table}table:dimensionRelationshipNode")
qnTableAspectNode201305 = qname(u"{http://xbrl.org/PWD/2013-05-17/table}table:aspectNode")

# prior 2013-01-16 PWD
table201301 = u"http://xbrl.org/PWD/2013-01-16/table"
tableBreakdown201301 = u"http://xbrl.org/arcrole/PWD/2013-01-16/table-breakdown"
tableFilter201301 = u"http://xbrl.org/arcrole/PWD/2013-01-16/table-filter"
tableDefinitionNodeSubtree201301 = u"http://xbrl.org/arcrole/PWD/2013-01-16/definition-node-subtree"
tableTupleContent201301 = u"http://xbrl.org/arcrole/PWD/2013-01-16/tuple-content"
tableDefinitionNodeMessage201301 = u"http://xbrl.org/arcrole/PWD/2013-01-16/definition-node-message"
tableDefinitionNodeSelectionMessage201301 = u"http://xbrl.org/arcrole/PWD/2013-01-16/definition-node-selection-message"
qnTableTable201301 = qname(u"{http://xbrl.org/PWD/2013-01-16/table}table:table")
qnTableCompositionNode201301 = qname(u"{http://xbrl.org/PWD/2013-01-16/table}table:compositionNode")
qnTableFilterNode201301 = qname(u"{http://xbrl.org/PWD/2013-01-16/table}table:filterNode")
qnTableConceptRelationshipNode201301 = qname(u"{http://xbrl.org/PWD/2013-01-16/table}table:conceptRelationshipNode")
qnTableDimensionRelationshipNode201301 = qname(u"{http://xbrl.org/PWD/2013-01-16/table}table:dimensionRelationshipNode")
qnTableRuleNode201301 = qname(u"{http://xbrl.org/PWD/2013-01-16/table}table:ruleNode")
qnTableClosedDefinitionNode201301 = qname(u"{http://xbrl.org/PWD/2013-01-16/table}table:closedDefinitionNode")
qnTableSelectionNode201301 = qname(u"{http://xbrl.org/PWD/2013-01-16/table}table:selectionNode")
qnTableTupleNode201301 = qname(u"{http://xbrl.org/PWD/2013-01-16/table}table:tupleNode")

# Montreal 2011 table linkbase
table2011 = u"http://xbrl.org/2011/table"
tableAxis2011 = u"http://xbrl.org/arcrole/2011/table-axis"
tableAxisSubtree2011 = u"http://xbrl.org/arcrole/2011/axis/axis-subtree"
tableFilter2011 = u"http://xbrl.org/arcrole/2011/table-filter"
tableFilterNodeFilter2011 = u"http://xbrl.org/arcrole/2011/filter-node-filter"
tableAxisFilter2011 = u"http://xbrl.org/arcrole/2011/axis/axis-filter"
tableAxisFilter201205 = u"http://xbrl.org/arcrole/2011/axis-filter"
tableTupleContent2011 = u"http://xbrl.org/arcrole/2011/axis/tuple-content"
tableAxisMessage2011 = u"http://xbrl.org/arcrole/PWD/2013-01-16/axis-message"
tableAxisSelectionMessage2011 = u"http://xbrl.org/arcrole/PWD/2013-01-16/axis-selection-message"
qnTableTable2011 = qname(u"{http://xbrl.org/2011/table}table:table")
qnTableCompositionAxis2011 = qname(u"{http://xbrl.org/2011/table}table:compositionAxis")
qnTableFilterAxis2011 = qname(u"{http://xbrl.org/2011/table}table:filterAxis")
qnTableConceptRelationshipAxis2011 = qname(u"{http://xbrl.org/2011/table}table:conceptRelationshipAxis")
qnTableDimensionRelationshipAxis2011 = qname(u"{http://xbrl.org/2011/table}table:dimensionRelationshipAxis")
qnTableRuleAxis2011 = qname(u"{http://xbrl.org/2011/table}table:ruleAxis")
qnTablePredefinedAxis2011 = qname(u"{http://xbrl.org/2011/table}table:predefinedAxis")
qnTableSelectionAxis2011 = qname(u"{http://xbrl.org/2011/table}table:selectionAxis")
qnTableTupleAxis2011 = qname(u"{http://xbrl.org/2011/table}table:tupleAxis")

# Eurofiling 2010 table linkbase
euRend = u"http://www.eurofiling.info/2010/rendering"
euTableAxis = u"http://www.eurofiling.info/arcrole/2010/table-axis"
euAxisMember = u"http://www.eurofiling.info/arcrole/2010/axis-member"
qnEuTable = qname(u"{http://www.eurofiling.info/2010/rendering}rendering:table")
qnEuAxisCoord = qname(u"{http://www.eurofiling.info/2010/rendering}rendering:axisCoord")
euGroupTable = u"http://www.eurofiling.info/xbrl/arcrole/group-table"

xdtSchemaErrorNS = u"http://www.xbrl.org/2005/genericXmlSchemaError"
errMsgPrefixNS = {
    u"err": xpath2err,
    u"xbrldte": u"http://xbrl.org/2005/xbrldt/errors",
    u"xbrldie": u"http://xbrl.org/2005/xbrldi/errors",
    u"xbrlfe": u"http://xbrl.org/2008/formula/error",
    u"xbrlmsge": u"http://xbrl.org/2010/message/error",
    u"xbrlvarinste": u"http://xbrl.org/2010/variable/instance/error",
    u"xbrlve": u"http://xbrl.org/2008/variable/error",
    u"xbrlcae": u"http://xbrl.org/2008/assertion/consistency/error",
    u"xbrleae": u"http://xbrl.org/2008/assertion/existence/error",
    u"xbrldfe": u"http://xbrl.org/2008/filter/dimension/error",  
    u"xffe": u"http://www.xbrl.org/2010/function/formula/error",
    u"xfie": u"http://www.xbrl.org/2008/function/instance/error",
    u"xfxce":u"http://www.xbrl.org/2010/function/xml-creation/error",
    u"vere": u"http://xbrl.org/2010/versioning-base/error",
    u"vercue": u"http://xbrl.org/2010/versioning-concept-use/error",
    u"vercde" :u"http://xbrl.org/2010/versioning-concept-details/error",
    u"verdime": u"http://xbrl.org/2010/versioning-dimensions/error",
    u"verrelse": u"http://xbrl.org/2010/versioning-relationship-sets/error",
    u"veriae": u"http://xbrl.org/2010/versioning-instance-aspects/error",
    u"xbrlacfe": u"http://xbrl.org/2010/filter/aspect-cover/error",
    u"xbrlcfie": u"http://xbrl.org/2010/custom-function/error",
    u"xbrlmfe": u"http://xbrl.org/2008/filter/match/error",
    u"xbrlvarscopee": u"http://xbrl.org/2010/variable/variables-scope/error",
    u"xbrlte": u"http://xbrl.org/PWD/2014-MM-DD/table/error",
    u"utre": u"http://www.xbrl.org/2009/utr/errors",
    u"enumte": u"http://xbrl.org/2014/extensible-enumerations/taxonomy-errors",
    u"enumie": u"http://xbrl.org/2014/extensible-enumerations/instance-errors",
    u"seve": u"http://xbrl.org/2014/assertion-severity/error"
    }

arcroleGroupDetect = u"*detect*"

def baseSetArcroleLabel(arcrole): # with sort char in first position
    if arcrole == u"XBRL-dimensions": return _(u"1Dimension")
    if arcrole == u"XBRL-formulae": return _(u"1Formula")
    if arcrole == u"Table-rendering": return _(u"1Rendering")
    if arcrole == parentChild: return _(u"1Presentation")
    if arcrole == summationItem: return _(u"1Calculation")
    return u"2" + os.path.basename(arcrole).title()

def labelroleLabel(role): # with sort char in first position
    if role == standardLabel: return _(u"1Standard Label")
    elif role == conceptNameLabelRole: return _(u"0Name")
    return u"3" + os.path.basename(role).title()

def isStandardNamespace(namespaceURI):
    return namespaceURI in set([xsd, xbrli, link, gen, xbrldt, xbrldi])

standardNamespaceSchemaLocations = {
    xbrli: u"http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd",
    link: u"http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd",
    xl: u"http://www.xbrl.org/2003/xl-2003-12-31.xsd",
    xlink: u"http://www.w3.org/1999/xlink",
    xbrldt: u"http://www.xbrl.org/2005/xbrldt-2005.xsd",
    xbrldi: u"http://www.xbrl.org/2006/xbrldi-2006.xsd",
    gen: u"http://www.xbrl.org/2008/generic-link.xsd",
    genLabel: u"http://www.xbrl.org/2008/generic-label.xsd",
    genReference: u"http://www.xbrl.org/2008/generic-reference.xsd"
    }

def isNumericXsdType(xsdType):
    return xsdType in set([u"integer", u"positiveInteger", u"negativeInteger", u"nonNegativeInteger", u"nonPositiveInteger",
                       u"long", u"unsignedLong", u"int", u"unsignedInt", u"short", u"unsignedShort",
                       u"byte", u"unsignedByte", u"decimal", u"float", u"double"])
    
standardLabelRoles = set([
                    u"http://www.xbrl.org/2003/role/label",
                    u"http://www.xbrl.org/2003/role/terseLabel",
                    u"http://www.xbrl.org/2003/role/verboseLabel",
                    u"http://www.xbrl.org/2003/role/positiveLabel",
                    u"http://www.xbrl.org/2003/role/positiveTerseLabel",
                    u"http://www.xbrl.org/2003/role/positiveVerboseLabel",
                    u"http://www.xbrl.org/2003/role/negativeLabel",
                    u"http://www.xbrl.org/2003/role/negativeTerseLabel",
                    u"http://www.xbrl.org/2003/role/negativeVerboseLabel",
                    u"http://www.xbrl.org/2003/role/zeroLabel",
                    u"http://www.xbrl.org/2003/role/zeroTerseLabel",
                    u"http://www.xbrl.org/2003/role/zeroVerboseLabel",
                    u"http://www.xbrl.org/2003/role/totalLabel",
                    u"http://www.xbrl.org/2003/role/periodStartLabel",
                    u"http://www.xbrl.org/2003/role/periodEndLabel",
                    u"http://www.xbrl.org/2003/role/documentation",
                    u"http://www.xbrl.org/2003/role/definitionGuidance",
                    u"http://www.xbrl.org/2003/role/disclosureGuidance",
                    u"http://www.xbrl.org/2003/role/presentationGuidance",
                    u"http://www.xbrl.org/2003/role/measurementGuidance",
                    u"http://www.xbrl.org/2003/role/commentaryGuidance",
                    u"http://www.xbrl.org/2003/role/exampleGuidance"])

standardReferenceRoles = set([
                    u"http://www.xbrl.org/2003/role/reference",
                    u"http://www.xbrl.org/2003/role/definitionRef",
                    u"http://www.xbrl.org/2003/role/disclosureRef",
                    u"http://www.xbrl.org/2003/role/mandatoryDisclosureRef",
                    u"http://www.xbrl.org/2003/role/recommendedDisclosureRef",
                    u"http://www.xbrl.org/2003/role/unspecifiedDisclosureRef",
                    u"http://www.xbrl.org/2003/role/presentationRef",
                    u"http://www.xbrl.org/2003/role/measurementRef",
                    u"http://www.xbrl.org/2003/role/commentaryRef",
                    u"http://www.xbrl.org/2003/role/exampleRef"])

standardLinkbaseRefRoles = set([
                    u"http://www.xbrl.org/2003/role/calculationLinkbaseRef",
                    u"http://www.xbrl.org/2003/role/definitionLinkbaseRef",
                    u"http://www.xbrl.org/2003/role/labelLinkbaseRef",
                    u"http://www.xbrl.org/2003/role/presentationLinkbaseRef",
                    u"http://www.xbrl.org/2003/role/referenceLinkbaseRef"])

standardRoles = standardLabelRoles | standardReferenceRoles | standardLinkbaseRefRoles | set([   
                    u"http://www.xbrl.org/2003/role/link",
                    u"http://www.xbrl.org/2003/role/footnote"])

def isStandardRole(role):
    return role in standardRoles

def isTotalRole(role):
    return role in set([u"http://www.xbrl.org/2003/role/totalLabel",
                    u"http://xbrl.us/us-gaap/role/label/negatedTotal",
                    u"http://www.xbrl.org/2009/role/negatedTotalLabel"])
    
def isNetRole(role):
    return role in set([u"http://www.xbrl.org/2009/role/netLabel",
                    u"http://www.xbrl.org/2009/role/negatedNetLabel"])
    
def isLabelRole(role):
    return role in standardLabelRoles or role == genLabel

def isNumericRole(role):
    return role in set([u"http://www.xbrl.org/2003/role/totalLabel",
                    u"http://www.xbrl.org/2003/role/positiveLabel",
                    u"http://www.xbrl.org/2003/role/negativeLabel",
                    u"http://www.xbrl.org/2003/role/zeroLabel",
                    u"http://www.xbrl.org/2003/role/positiveTerseLabel",
                    u"http://www.xbrl.org/2003/role/negativeTerseLabel",
                    u"http://www.xbrl.org/2003/role/zeroTerseLabel",
                    u"http://www.xbrl.org/2003/role/positiveVerboseLabel",
                    u"http://www.xbrl.org/2003/role/negativeVerboseLabel",
                    u"http://www.xbrl.org/2003/role/zeroVerboseLabel",
                    u"http://www.xbrl.org/2009/role/negatedLabel",
                    u"http://www.xbrl.org/2009/role/negatedPeriodEndLabel",
                    u"http://www.xbrl.org/2009/role/negatedPeriodStartLabel",
                    u"http://www.xbrl.org/2009/role/negatedTotalLabel",
                    u"http://www.xbrl.org/2009/role/negatedNetLabel",
                    u"http://www.xbrl.org/2009/role/negatedTerseLabel"])
    
def isStandardArcrole(role):
    return role in set([u"http://www.w3.org/1999/xlink/properties/linkbase",
                    u"http://www.xbrl.org/2003/arcrole/concept-label",
                    u"http://www.xbrl.org/2003/arcrole/concept-reference",
                    u"http://www.xbrl.org/2003/arcrole/fact-footnote",
                    u"http://www.xbrl.org/2003/arcrole/parent-child",
                    u"http://www.xbrl.org/2003/arcrole/summation-item",
                    u"http://www.xbrl.org/2003/arcrole/general-special",
                    u"http://www.xbrl.org/2003/arcrole/essence-alias",
                    u"http://www.xbrl.org/2003/arcrole/similar-tuples",
                    u"http://www.xbrl.org/2003/arcrole/requires-element"])
    
standardArcroleCyclesAllowed = { 
                    u"http://www.xbrl.org/2003/arcrole/concept-label":(u"any", None),
                    u"http://www.xbrl.org/2003/arcrole/concept-reference":(u"any", None),
                    u"http://www.xbrl.org/2003/arcrole/fact-footnote":(u"any",None),
                    u"http://www.xbrl.org/2003/arcrole/parent-child":(u"undirected", u"xbrl.5.2.4.2"),
                    u"http://www.xbrl.org/2003/arcrole/summation-item":(u"any", u"xbrl.5.2.5.2"),
                    u"http://www.xbrl.org/2003/arcrole/general-special":(u"undirected", u"xbrl.5.2.6.2.1"),
                    u"http://www.xbrl.org/2003/arcrole/essence-alias":(u"undirected", u"xbrl.5.2.6.2.1"),
                    u"http://www.xbrl.org/2003/arcrole/similar-tuples":(u"any", u"xbrl.5.2.6.2.3"),
                    u"http://www.xbrl.org/2003/arcrole/requires-element":(u"any", u"xbrl.5.2.6.2.4")}

def standardArcroleArcElement(arcrole):
    return {u"http://www.xbrl.org/2003/arcrole/concept-label":u"labelArc",
            u"http://www.xbrl.org/2003/arcrole/concept-reference":u"referenceArc",
            u"http://www.xbrl.org/2003/arcrole/fact-footnote":u"footnoteArc",
            u"http://www.xbrl.org/2003/arcrole/parent-child":u"presentationArc",
            u"http://www.xbrl.org/2003/arcrole/summation-item":u"calculationArc",
            u"http://www.xbrl.org/2003/arcrole/general-special":u"definitionArc",
            u"http://www.xbrl.org/2003/arcrole/essence-alias":u"definitionArc",
            u"http://www.xbrl.org/2003/arcrole/similar-tuples":u"definitionArc",
            u"http://www.xbrl.org/2003/arcrole/requires-element":u"definitionArc"}[arcrole]
            
def isDefinitionOrXdtArcrole(arcrole):
    return isDimensionArcrole(arcrole) or arcrole in set([
            u"http://www.xbrl.org/2003/arcrole/general-special",
            u"http://www.xbrl.org/2003/arcrole/essence-alias",
            u"http://www.xbrl.org/2003/arcrole/similar-tuples",
            u"http://www.xbrl.org/2003/arcrole/requires-element"])
            
def isStandardResourceOrExtLinkElement(element):
    return element.namespaceURI == link and element.localName in set([
          u"definitionLink", u"calculationLink", u"presentationLink", u"labelLink", u"referenceLink", u"footnoteLink", 
          u"label", u"footnote", u"reference"])
    
def isStandardArcElement(element):
    return element.namespaceURI == link and element.localName in set([
          u"definitionArc", u"calculationArc", u"presentationArc", u"labelArc", u"referenceArc", u"footnoteArc"])
        
def isStandardArcInExtLinkElement(element):
    return isStandardArcElement(element) and isStandardResourceOrExtLinkElement(element.getparent())

standardExtLinkQnames = set([qname(u"{http://www.xbrl.org/2003/linkbase}definitionLink"), 
                         qname(u"{http://www.xbrl.org/2003/linkbase}calculationLink"), 
                         qname(u"{http://www.xbrl.org/2003/linkbase}presentationLink"), 
                         qname(u"{http://www.xbrl.org/2003/linkbase}labelLink"),     
                         qname(u"{http://www.xbrl.org/2003/linkbase}referenceLink"), 
                         qname(u"{http://www.xbrl.org/2003/linkbase}footnoteLink")]) 

standardExtLinkQnamesAndResources = set([qname(u"{http://www.xbrl.org/2003/linkbase}definitionLink"), 
                                     qname(u"{http://www.xbrl.org/2003/linkbase}calculationLink"), 
                                     qname(u"{http://www.xbrl.org/2003/linkbase}presentationLink"), 
                                     qname(u"{http://www.xbrl.org/2003/linkbase}labelLink"), 
                                     qname(u"{http://www.xbrl.org/2003/linkbase}referenceLink"), 
                                     qname(u"{http://www.xbrl.org/2003/linkbase}footnoteLink"), 
                                     qname(u"{http://www.xbrl.org/2003/linkbase}label"), 
                                     qname(u"{http://www.xbrl.org/2003/linkbase}footnote"), 
                                     qname(u"{http://www.xbrl.org/2003/linkbase}reference")])

def isStandardExtLinkQname(qName):
    return qName in standardExtLinkQnamesAndResources
    
def isStandardArcQname(qName):
    return qName in set([
          qname(u"{http://www.xbrl.org/2003/linkbase}definitionArc"), 
          qname(u"{http://www.xbrl.org/2003/linkbase}calculationArc"), 
          qname(u"{http://www.xbrl.org/2003/linkbase}presentationArc"), 
          qname(u"{http://www.xbrl.org/2003/linkbase}labelArc"),
          qname(u"{http://www.xbrl.org/2003/linkbase}referenceArc"), 
          qname(u"{http://www.xbrl.org/2003/linkbase}footnoteArc")])
    
def isDimensionArcrole(arcrole):
    return arcrole.startswith(u"http://xbrl.org/int/dim/arcrole/")

consecutiveArcrole = { # can be list of or single arcrole
    all: (dimensionDomain,hypercubeDimension), notAll: (dimensionDomain,hypercubeDimension),
    hypercubeDimension: dimensionDomain,
    dimensionDomain: (domainMember, all, notAll),
    domainMember: (domainMember, all, notAll),
    dimensionDefault: ()}

def isTableRenderingArcrole(arcrole):
    return arcrole in set([# current PWD 2013-05-17
                       tableBreakdown, tableBreakdownTree, tableFilter, tableParameter,
                       tableDefinitionNodeSubtree, tableAspectNodeFilter,
                       # current IWD
                       tableBreakdownMMDD, tableBreakdownTreeMMDD, tableFilterMMDD, tableParameterMMDD,
                       tableDefinitionNodeSubtreeMMDD, tableAspectNodeFilterMMDD, 
                       # Prior PWD, Montreal and 2013-01-16 
                       tableBreakdown201305, tableBreakdownTree201305, tableFilter201305,
                       tableDefinitionNodeSubtree201305, tableAspectNodeFilter201305,
                       
                       tableBreakdown201301, tableFilter201301,
                       tableDefinitionNodeSubtree201301, 
                       tableTupleContent201301, 
                       tableDefinitionNodeMessage201301, tableDefinitionNodeSelectionMessage201301,
                       
                       tableAxis2011, tableFilter2011, 
                       tableAxisSubtree2011, 
                       tableFilterNodeFilter2011, tableAxisFilter2011, tableAxisFilter201205,
                       tableTupleContent201301, tableTupleContent2011,
                       tableAxisSubtree2011, tableAxisFilter2011,
                       # original Eurofiling
                       euTableAxis, euAxisMember,])
   
tableIndexingArcroles = frozenset((euGroupTable,))
def isTableIndexingArcrole(arcrole):
    return arcrole in tableIndexingArcroles
    
def isFormulaArcrole(arcrole):
    return arcrole in set([u"http://xbrl.org/arcrole/2008/assertion-set",
                       u"http://xbrl.org/arcrole/2008/variable-set",
                       u"http://xbrl.org/arcrole/2008/variable-set-filter",
                       u"http://xbrl.org/arcrole/2008/variable-filter",
                       u"http://xbrl.org/arcrole/2008/boolean-filter",
                       u"http://xbrl.org/arcrole/2008/variable-set-precondition",
                       u"http://xbrl.org/arcrole/2008/consistency-assertion-formula",
                       u"http://xbrl.org/arcrole/2010/function-implementation",
                       u"http://xbrl.org/arcrole/2010/assertion-satisfied-message",
                       u"http://xbrl.org/arcrole/2010/assertion-unsatisfied-message",
                       u"http://xbrl.org/arcrole/2014/assertion-satisfied-severity",
                       u"http://xbrl.org/arcrole/2014/assertion-unsatisfied-severity",
                       u"http://xbrl.org/arcrole/2010/instance-variable",
                       u"http://xbrl.org/arcrole/2010/formula-instance",
                       u"http://xbrl.org/arcrole/2010/function-implementation",
                       u"http://xbrl.org/arcrole/2010/variables-scope"])

def isResourceArcrole(arcrole):
    return (arcrole in set([u"http://www.xbrl.org/2003/arcrole/concept-label",
                        u"http://www.xbrl.org/2003/arcrole/concept-reference",
                        u"http://www.xbrl.org/2003/arcrole/fact-footnote",
                        u"http://xbrl.org/arcrole/2008/element-label",
                        u"http://xbrl.org/arcrole/2008/element-reference"])
            or isFormulaArcrole(arcrole))
    
