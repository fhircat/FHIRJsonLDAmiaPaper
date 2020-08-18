# FHIRJsonLDAmiaPaper

Source for FHIR JSON-LD AMIA submission

## Setup

Install pipenv and packages
```
> pipenv install  
```

Upgrade nodejs to > 13.*
```
> brew update
> brew upgrade node
> npm install -g npm
```

Install yarn and node packages
```
> cd fhir_jsonld_js; yarn install 
> cd ..
```
Unzip appropriate FHIR examples
```
> ./expand.sh ['fhir-r5' or 'fhir-r4']  (default: 'fhir-r5')
```

## Directories
**fhir-r4**   - Image of current HL7 R4 content
* compare-report - transformation reports on a per file basis
    * 
* examples-json - Vanilla HL7 R4 example JSON files
* examples-ttl  - HL7 R4 RDF output as transformed by current build process
    * account-example.ttl
    *   ...
* jsonld-pre    - example-json preprocessed by fhir_jsonld_amia/json_to_r4.py
    * account-example.json
    *   ...
* jsonld-r4 - jsonld-pre files as processed by `fhir_jsonld_js/yarn jsonld`
    * account-example.nq 
    *   ...
* examples-json.zip - Downloaded from https://build.fhir.org on 8/17/2020. 
* examples-ttl.zip - Downloaded from https://build.fhir.org on 8/17/2020. 

**fhir-r5**   - Image of current HL7 R5 content
* compare-report - transformation reports on a per file basis
  * 
* examples-json - Vanilla HL7 R4 example JSON files
* examples-ttl  - HL7 R4 RDF output as transformed by current build process
  * account-example.ttl
  *   ...
* jsonld-pre    - example-json preprocessed by fhir_jsonld_amia/json_to_r4.py
  * account-example.json
  *   ...
* jsonld-r4 - jsonld-pre files as processed by `fhir_jsonld_js/yarn jsonld`
   * account-example.nq 
* examples-json.zip - Downloaded from https://hl7.org/fhir/ on 8/17/2020. 
* examples-ttl.zip - Downloaded from https://hl7.org/fhir/ on 8/17/2020. 

## Steps


The three scripts that are used to convert all files and compare the results are: 

1. Preprocess JSON file to insert @context, OWL header and structural changes

```shell script
pipenv run python fhir_jsonld_amia/json_to_r4.py -id <input_directory> -od <output_directory> -c -fs http://hl7.org/fhir/
```

`input_directory`: Where the JSON files are stored. 
`output_directory`: Where the generated JSONLD files are stored. 

2. Expand the JSONLD files

This is done by using the [jsonld-js](https://github.com/digitalbazaar/jsonld.js/) nodejs package.  

``` 
cd fhir_jsonld_js; yarn jsonld -c expand -n <jsonld_pre_directory> -m <expanded_files_directory>
```

`jsonld_pre_directory`: where the preprocessed JSONLD files is stored
`expanded_files_directory`: the directory where the expanded files are going to be stored. 

3. Compare the expanded files with the FHIR examples in Turtle format. 

``` 
pipenv run python fhir_jsonld_amia/compare_rdf.py -id <expanded_files> -td <fhir_examples> -od <report_directory> 
```

Right now this script only compare JSONLD files with Turtle. 

### FHIR-R4

Here are the commands to make conversions of fhir-r4 files. 

```
pipenv run python fhir_jsonld_amia/json_to_r4.py -id data/fhir-r4/examples-json -od data/fhir-r4/jsonld-pre -c -fs http://hl7.org/fhir/
cd fhir_jsonld_js; yarn jsonld -c expand -n ../data/fhir-r4/jsonld-pre -m ../data/fhir-r4/jsonld-r4
pipenv run python fhir_jsonld_amia/compare_rdf.py -id data/fhir-r4/jsonld-r4 -od data/fhir-r4/compare-report -td data/fhir-r4/examples-ttl
``` 

### Test

Here are the commands to do tests with small set of files. Just put the files in the data/test directory and run the commands. 

```
pipenv run python fhir_jsonld_amia/json_to_r4.py -id data/test/examples-json -od data/test/jsonld-pre -c -fs https://hl7.org/fhir/
cd fhir_jsonld_js; yarn jsonld -c expand -n ../data/test/jsonld-pre -m ../data/test/jsonld-r4
pipenv run python fhir_jsonld_amia/compare_rdf.py -id data/test/jsonld-r4 -od data/test/compare-report -td data/test/examples-ttl
```

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


