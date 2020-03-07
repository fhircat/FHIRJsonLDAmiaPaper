# FHIRJsonLDAmiaPaper

Source for FHIR JSON-LD AMIA submission

## Setup

Install pipenv and packages
```
pipenv install  
```

Install yarn and node packages
```
cd fhir_jsonld_js; yarn install 
```

## Data

Downloaded from https://build.fhir.org on 3/4/2020. 

`data/examples-json`: Decompressed from https://build.fhir.org/examples-json.zip
`data/examples-ttl`: Decompressed from https://build.fhir.org/examples-ttl.zip

## Steps

Steps: 

1. Convert JSON to JSONLD. Compare JSONLD to FHIR RDF.

```shell script
# This will convert JSON to JSONLD, using the R4 preprocessing, and expand with context files. 
python fhir_jsonld_amia/json_to_r4.py -id data/examples-json -od data/jsonld-pre -ed jsonld-r4 -c 
```

2. Convert FHIR RDF to JSON. Cmopare the generated JSON to FHIR JSON.  

Commands: 

1. Convert all fhir json to R4 ready

pipenv run python fhir_jsonld_amia/json_to_r4.py -id data/examples-json -od data/jsonld-pre -c -fs http://hl7.org/fhir/
cd fhir_jsonld_js; yarn jsonld -c expand -n ../data/jsonld-pre -m ../data/jsonld-r4
pipenv run python fhir_jsonld_amia/compare_rdf.py -id data/jsonld-r4 -od data/compare-report -td data/examples-ttl 

### Test

pipenv run python fhir_jsonld_amia/json_to_r4.py -id data/test-json -od data/test-jsonld-pre -c
cd fhir_jsonld_js; yarn jsonld -c expand -n ../data/test-jsonld-pre -m ../data/test-jsonld-r4

## Results

Run 3/4/2020

Convert FHIR JSON to R4

Step 1: Total=3026 Successful=3024
Step 2: Total 3024 Converted 2998
Missing contexts: 

  'https://fhircat.org/fhir/contexts/r5/conditiondefinition.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/manufactureditemdefinition.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/administrableproductdefinition.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/packagedproductdefinition.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/permission.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/topic.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/clinicaluseissue.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/ingredient.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/medicationusage.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/medicinalproductdefinition.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/capabilitystatement2.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/substancedefinition.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/regulatedauthorization.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/nutritionintake.context.jsonld',
  'https://fhircat.org/fhir/contexts/r5/nutritionproduct.context.jsonld'


