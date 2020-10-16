# Summary of FHIR Original (current) JSON-LD Conversions

## Step 1: Structural transformation process

### R4 Transformation
As of 10/16/2020:
* There are 2912 FHIR JSON files in examples-json.zip.  
* 2911 of these were successfully transformed by the preprocessor.  One of them was not a FHIR resource
* 2906 of these were successfully transformed into RDF triples by the JAVA JSON-LD processor
* 2906 of the files were processed by the comparison routine
```text
    ---------------------------------------
    Number of files processed: 2906
      Number of match failures: 121
        Number of content mismatch: 121
      Number of files skipped: 2120
        Number of code systems: 501
        Number of missing FHIR ttl files: 753
          Number of missing extensions: 363
          Number of missing for other reasons: 192
          Number of missing profiles: 198
        Number of file exceeds max triples: 90
        Number of value sets: 776
      Number of successful matches: 665
    
    ----------------------------------------
    Number of details: 713
      Number of adjusted decimals: 67
      Number of expected files with incorrect contained mapping: 9
      Number of incomplete transforms (UNKNOWN in output): 0
      Number of SERIOUS ISSUE: rdf:type rdf:List found in graph: 0
      Number of missing metadata in source: 644
      Number of FHIR.link elements removed from actual: 152
      Number of FHIR.link elements removed from expected: 0
      Number of File has too many triples for detailed compare: 0
      Number of adjusted type arcs: 508
```  

Of the 20906 files that were processed:
* 2120 were skipped
    * 776 Value sets resources, which aren't emitted in the existing FHIR build
    * 753 Missing because:
        * 363 Extensions 
        * 198 Profiles 
        * 192 Other unspecified reasons
    * 501 Code system resources, which aren't emitted in the existing FHIR build
    *  90 files exceed 5000 triples in length
* **786 files were compared**
    * 665 successfull matches
    * 121 match failures
    
### Analysis of 142 match failures
#### Issue 1: significance of fullUrl and its relationship to links in a bundle
[xds-example.json](http://hl7.org/fhir/xds-example.json) is a bundle that uses `fullUrl`.  The question
is what to do with the embedded links (e.g. `Patient/a2`, `Practitioner/a3`, etc.) The current FHIR transformation
does not make the connection between the assigned fullUrl (`http://localhost:9556/svc/fhir/Patient/a2`) and the 
embedded link (`Patient/a2`).  The current FHIR RDF emits:
```turtle
<http://hl7.org/fhir/Patient/a2> a fhir:Patient .
<http://localhost:9556/svc/fhir/Patient/a2> a fhir:Patient;
  fhir:Resource.id [ fhir:value "a2"];
  fhir:Resource.meta [
     fhir:Meta.lastUpdated [ fhir:value "2013-07-01T13:11:33Z"^^xsd:dateTime ]
  ];
  ...
```
This is not correct, as the `Observation.subject` should be resolved relative to the "base" URL, 
which (as we understand it) is the purpose for the `fullUrl` in the bundle container.  This means that the three links,
```turtle
<http://hl7.org/fhir/Patient/a2> a fhir:Patient .
<http://hl7.org/fhir/Practitioner/a3> a fhir:Practitioner .
<http://hl7.org/fhir/Practitioner/a4> a fhir:Practitioner .
```
Should NOT be emitted by the RDF.

#### Issue 2: URI's for badly formed and compositional concept codes.
[riskassessment-example-prognosis.json](http://hl7.org/fhir/riskassessment-example-prognosis.json) has a compositional
SNOMED-CT concept "code":
```json
  "outcome": {
        "coding": [
          {
            "system": "http://snomed.info/sct",
            "code": "249943000:363698007\u003d72098002,260868000\u003d6934004"
          }
        ],
        "text": "permanent weakness of the left arm"
      },
```
The differentiation of concept _codes_ from compositional expressions should NOT be the function of language parsers.
As such, the JSON-LD emits:
```turtle
    [] ns1:RiskAssessment.prediction.outcome [ ns1:CodeableConcept.coding [ 
                    a <http://snomed.info/id/249943000%253A363698007%253D72098002%252C260868000%253D6934004> ;
                    ns1:Coding.code [ ns1:value "249943000:363698007=72098002,260868000=6934004" ] ;
                    ns1:Coding.system [ ns1:value "http://snomed.info/sct" ] ;
                    ns1:index 0 ] ;
            ns1:CodeableConcept.text [ ] ] ;
    ns1:RiskAssessment.prediction.qualitativeRisk [ ns1:CodeableConcept.coding [ ns1:Coding.code [ ns1:value "moderate" ] ;
                    ns1:Coding.display [ ns1:value "moderate likelihood" ] ;
                    ns1:Coding.system [ ns1:value "http://terminology.hl7.org/CodeSystem/risk-probability" ] ] ] .
```
Where the existing turtle does not have the type arc.

#### Issue 3: Existing TTL generator not parsing URLs correctly
[orgrole-example-hie](http://build.fhir.org/orgrole-example-hie.json) got the types listed
below.  This is because they are NOT using the official regular expressions and have parsed:
'http://hl7.org/fhir/ig/vhdir/Endpoint/foundingfathersHIE' as an "ig" instead of an "Endpoint"

```text
----- Missing Triples -----

<http://hl7.org/fhir/ig/vhdir/Endpoint/foundingfathersHIE> a <http://hl7.org/fhir/ig> .

<http://hl7.org/fhir/ig/vhdir/Organization/foundingfathers> a <http://hl7.org/fhir/ig> .

<http://hl7.org/fhir/ig/vhdir/Organization/monumentHIE> a <http://hl7.org/fhir/ig> .


----- Added Triples -----

<http://hl7.org/fhir/ig/vhdir/Endpoint/foundingfathersHIE> a <http://hl7.org/fhir/Endpoint> .

<http://hl7.org/fhir/ig/vhdir/Organization/foundingfathers> a <http://hl7.org/fhir/Organization> .

<http://hl7.org/fhir/ig/vhdir/Organization/monumentHIE> a <http://hl7.org/fhir/Organization> .
```

#### Issue 4: Resources with no `id` or `resourceType`
data/fhir-r4/examples-json/json-edge-cases.json
```text
  File "/Users/solbrig/.local/share/virtualenvs/FHIRJsonLDAmiaPaper-ikFPjg5o/lib/python3.8/site-packages/dirlistproc/DirectoryListProcessor.py", line 138, in _call_proc
    rslt = proc(ifn, ofn, self.opts)
  File "fhir_jsonld_amia/json_preprocessor.py", line 436, in convert_file
    out_json = to_r4(opts.in_json, opts, ifn)
  File "fhir_jsonld_amia/json_preprocessor.py", line 394, in to_r4
    dict_processor(fhir_json)
  File "fhir_jsonld_amia/json_preprocessor.py", line 320, in dict_processor
    add_contained_urls(container, id_map)
  File "fhir_jsonld_amia/json_preprocessor.py", line 203, in add_contained_urls
    id_map[contained_id] = (contained_type + '/' + getattr(resource, ID_KEY) + contained_id, contained_type)

***** ERROR: data/fhir-r4/examples-json/json-edge-cases.json
'JsonObj' object has no attribute 'id'
```
it turns out that neither `resourceType` or `id` is required. 

#### Issue 5: New Preprocessor not parsing concept codes correctly
data/fhir-r4/original/java/plandefinition-example-cardiology-os.json includes the SCT concept code "look up value".  This
is not getting correctly encoded, which results in the following error:
```
  
  File "/Users/solbrig/.local/share/virtualenvs/FHIRJsonLDAmiaPaper-ikFPjg5o/lib/python3.8/site-packages/rdflib/graph.py", line 1078, in parse
    parser.parse(source, self, **args)
***** ERROR: data/fhir-r4/original/java/plandefinition-example-cardiology-os.nq
at line 418 of <>:
Bad syntax (']' expected) at ^ in:
"...b'eConcept.coding [\n         fhir:index 0;\n         a sct:look'^b' up value;\n         fhir:Coding.system [ fhir:value "http://'..."
```

### R5 Transformation
There are currently 2881 FHIR JSON files in examples-json.zip. Of these, 2875 were successfully transformed using the
preprocessor.

Files that are not FHIR resources:
* hl7.fhir.r5.corexml.manifest.json
* xver-paths-4.5.json
* hl7.fhir.r5.core.manifest.json
* package-min-ver.json
* uml.json
* hl7.fhir.r5.expansions.manifest.json

Addtiional conversion issues
* testscript-example-multisystem.json - problem: "origin" element 0 already has an index
* testscript-example-multisystem.json - problem: "destination" element 0 already has an index
* testscript-example-multisystem.json - problem: "destination" element 1 already has an index
* parameters-example.json does not have an identifier
* json-edge-cases.json does not have an identifier

## Step 2: Convert the 2875 Preprocessed JSON files into RDF
Of the 2875 source files, 2834 were successfully transformed into RDF format.  The exceptins were due to missing
context definitons for:

* administrableproductdefinition.context.jsonld (1 instance)
* capabilitystatement2.context.jsonld (5 instances)
* citation.context.jsonld (1 instance)
* clinicaluseissue.context.jsonld (1 instance)
* conditiondefinition.context.jsonld (1 instance)
* evidencereport.context.jsonld (1 instance)
* ingredient.context.jsonld (4 instances)
* manufactureditemdefinition.context.jsonld (2 instances)
* medicationusage.context.jsonld (8 instances)
* medicinalproductdefinition.context.jsonld (2 instances)
* nutritionintake.context.jsonld (2 instances)
* packagedproductdefinition.context.jsonld (1 instance)
* permission.context.jsonld (1 instance)
* regulatedauthorization.context.jsonld (2 instances)
* subscriptionstatus.context.jsonld (7 instances)
* subscriptiontopic.context.jsonld (1 issue)
* substancedefinition.context.jsonld (1 issue)

## Step 3: Compare the 2835 converted files to the current FHIR RDF
Of the 2834 input files:
* 289 were identical to the original
* 1320 differed in content to the original
    * 277 contained UNKNOWN uri's (were not completely transformed)
    * 2 had additional or missing subjects
        * orgrole-example-hie
        * orgrole-example-services
    * 212 had mismatched content
* 831 did not have FHIR RDF files to compare to:
    * 251 were FHIR profiles (e.g. `account.profile.ttl`)
    * 181 were questionairres (`...-questionairre.ttl`)
    * 357 were extensions (`/extension-....ttl`)
    * 42 were other (see: Other missing ttl files below)
* 402 were code systems (not currently tested)
* 824 were value sets (not currently tested)

### Analysis
#### Individual issues
binary-example.json has a `resourceType` entry.  This was a bug where "DomainResource" was recognized but not 
"Resource" roots.

### The types of  
####
The key, `reference` is used in multiple contexts.  As an example, the [Consent](http://build.fhir.org/consent.html) resource
has an attribute `reference` whose type is `Reference`.  We have addressed this issue by treating strings as true reference
objects and objects as not.

The key, `index` is used in the [TestScript](http://build.fhir.org/testscript.html) resource.  To address this issue, we
propose changing the plain `index` to `fhir:index` in our transformations.

The claimresponse context, 'claimresponse.adjudication.context.jsonld' is not being generated.  
#### FHIR Profiles
We have a couple of issues with the RDF representation of fhir profiles:
1) The _html_ representation of the profiles is generated (e.g. [account.profile.ttl.html](http://build.fhir.org/account.profile.ttl.html)), but
there is no raw turtle.  The "raw" link just redirects to the html page.
2) Neither the ttl nor the html are included in any of the FHIR zip files.  

* **TODO:** File an issue report with the FHIR community
* **TODO:** Extract at least a representative sample from the profiles and test them to make sure our conversions
are working.


#### UNKNOWN uri's
1) A portion of these were being generated because we have been adding multiple contexts to the 
outermost level -- as an example, specimen.context.jsonld + substance.context.jsonld.  These have overlapping keys,
but with different types, meaning that they are not interpreted correctly.  Part of the solution was adding the
contexts directly _to_ the containing entries (typically `contained`).

   This, however, leads to another issue -- the existing FHIR is not generating RDF for the inner contained elements.  
As an example, 
    ```json
    {
      "resourceType": "Specimen",
      "id": "101",
      "contained": [
        {
          "resourceType": "Substance",
          "id": "hep",
            ...
          }
        }
        ...
    ```
    _should_ generate a number of triples with the hep substance, including:
    
    `<http://hl7.org/fhir/Substance/hep> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://hl7.org/fhir/Substance> .`
    
    This is not currently the case.  We believe that we are doing this correctly and the current FHIR implementation is wrong.

2) There is an issue with the Medication resource.  The R4 Model shows:

3) General context generation issue:

    ![R4 contract](images/r4contract.png)

    `group` was not included in the `contract.term.context.jsonld` file -- corrected by manual edit:
    ```json
        "action": {
          "@id": "fhir:Contract.term.action",
          "@context": "contract.term.action.context.jsonld"
        },
        "group": {
          "@id": "fhir:Contract.term.group",
          "@context": "contract.term.context.jsonld"
        },
        "index": {
          "@id": "fhir:index",
          "@type": "http://www.w3.org/2001/XMLSchema#integer"
        }
    ```
   TODO: Need a ticket to fix this

4) Bundle ResourceType missing:
    Not sure why this is, but `resourceType` is not being emitted in `bundle.context.jsonld`:
    ```
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "id": {
      "@id": "fhir:Resource.id",
      "@context": "string.context.jsonld"
    },
    "resourceType": {
      "@id": "rdf:type",
      "@type": "@id"
    },
    "meta": {
      "@id": "fhir:Resource.meta",
      "@context": "meta.context.jsonld"
    },
   ```
   Manually added this. TODO: Need a ticket to fix this
   
5) Reference link issue

    See: r4 paymentreconciliation-example for details.  
    ![paymentreconcilliation](images/paymentreconciliation.png)
    
    The general problem is the following structure:
    ```json
    "detail": [
       ...
      "request": {
        "reference": "http://www.BenefitsInc.com/fhir/oralhealthclaim/225476332699"
      },
    ```
    Needs to produce the following output:
    ```turtle
     fhir:PaymentReconciliation.detail.request 
       [ fhir:Reference.reference 
           [ ns1:value "http://www.BenefitsInc.com/fhir/oralhealthclaim/225476332699" ] ;
             ns1:link <http://www.BenefitsInc.com/fhir/oralhealthclaim/225476332699> 
       ] ;
    ```

    The fundamental problem is, as JSON-LD can't add tags, we need to _recognize that the range of `request` is `Reference`_
    in order to add the additional element below in the preprocessing step:
    
    ```json
        "detail": [
           ...
         "request": {
            "reference": {
               "value": "http://www.BenefitsInc.com/fhir/oralhealthclaim/225476332699"
            },
           fhir:link {
             "@id": "<http://www.BenefitsInc.com/fhir/oralhealthclaim/225476332699>"
           }
         },
    ```
    
### Missing links (no pun intended)
The FHIR [canonical](http://hl7.org/fhir/datatypes.html#canonical) data type presents a different sort of problem.  While
we are making some assumptions about the uniqueness of tags, we can map `id` and `reference` to their appropriate targets.
`canonical`, however, provides no way to determine that someting is of this type without having access to the underlying
definitions.  As an example, [ActivityDefinition](http://hl7.org/fhir/activitydefinition.html), and its example, 
[administer-zika-virus-exposure-assessment](http://hl7.org/fhir/administer-zika-virus-exposure-assessment.html) has 
```json
  "library": [
    "Library/zika-virus-intervention-logic"
  ],
```

We have to, somehow, recognize that `libarary` is of type `canonical` so that we can add the `fhir:link` tag.  What we
have at the moment is:
```json
   "library": [
      {
         "value": "Library/zika-virus-intervention-logic",
         "index": 0
      }
   ],
```
and we need to add a link:
```json
   "library": [
      {
         "value": "Library/zika-virus-intervention-logic",
         "index": 0
         "fhir:link": {
            "@id": "Library/zika-virus-intervention-logic"
         }
      }
   ],
```
Also, while the current FHIR RDF does not add a type arc, there are two possible ways that this might (should?) occur:

1) the definition of `library` is `canonical(Library)`, meaning that we KNOW what the type is no matter the URL 
2) the URL could be parsed just like in other places, which will also yield a type.
    
## Other missing ttl files
* examples-ttl/capabilitystatement2.profile.ttl
* examples-ttl/cm-address-type-v3.ttl
* examples-ttl/cm-address-use-v2.ttl
* examples-ttl/cm-address-use-v3.ttl
* examples-ttl/cm-administrative-gender-v2.ttl
* examples-ttl/cm-administrative-gender-v3.ttl
* examples-ttl/cm-composition-status-v3.ttl
* examples-ttl/cm-contact-point-system-v2.ttl
* examples-ttl/cm-contact-point-use-v2.ttl
* examples-ttl/cm-contact-point-use-v3.ttl
* examples-ttl/cm-data-absent-reason-v3.ttl
* examples-ttl/cm-detectedissue-severity-v3.ttl
* examples-ttl/cm-document-reference-status-v3.ttl
* examples-ttl/cm-name-use-v2.ttl
* examples-ttl/cm-name-use-v3.ttl
* examples-ttl/conceptmaps.ttl
* examples-ttl/cqf-questionnaire.profile.ttl
* examples-ttl/dataelements.ttl
* examples-ttl/definition.ttl
* examples-ttl/device-extensions-Device-din.ttl
* examples-ttl/elementdefinition-de.profile.ttl
* examples-ttl/event.ttl
* examples-ttl/external-resources.ttl
* examples-ttl/familymemberhistory-genetic.profile.ttl
* examples-ttl/fivews.ttl
* examples-ttl/integer64.profile.ttl
* examples-ttl/json-edge-cases.ttl
* examples-ttl/participant.ttl
* examples-ttl/participantcontactable.ttl
* examples-ttl/participantliving.ttl
* examples-ttl/patient-extensions-Patient-age.ttl
* examples-ttl/patient-extensions-Patient-birthOrderBoolean.ttl
* examples-ttl/patient-extensions-Patient-mothersMaidenName.ttl
* examples-ttl/product.ttl
* examples-ttl/profiles-others.ttl
* examples-ttl/profiles-resources.ttl
* examples-ttl/profiles-types.ttl
* examples-ttl/provenance-relevant-history.profile.ttl
* examples-ttl/questionnaireresponse-extensions-QuestionnaireResponse-item-subject.ttl
* examples-ttl/request.ttl
* examples-ttl/search-parameters.ttl
* examples-ttl/valuesets.ttl
    
    
 
