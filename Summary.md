# Summary of FHIR Original (current) JSON-LD Conversions

## Step 1: Structural transformation process
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
    
    
 
