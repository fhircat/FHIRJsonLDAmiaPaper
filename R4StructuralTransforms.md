# Structural Transformations for FHIR RDF
There are a number of structural transformations that need to be done to a FHIR JSON instance
before it can be converted to RDF using JSON-LD.

## Naming Conventions


## Generating the JSON-LD Context files
Note: Check w/ Deepak Sharma and others.  What is being described here is the state of things as of October, 2020.
The JSON-LD context files are generated by:

``` bash
> git clone FHIRCat/org.hl7.fhir.core
> cd org.hl7.fhir.core/org.hl7.fhir.r4
> mvn -Dtest=org.hl7.fhir.r4.test.LDContextGeneratorTests test
> cd ../org.hl7.fhir.r5
> mvn -Dtest=org.hl7.fhir.r5.test.LDContextGeneratorTests test
```
**Warning:** For reasons that we aren't able to explain, the above scripts generates its output in the  `~/LDContext/R4`
and `~/LDContext/R5` directories.  

We keep the latest copy of the R4 and R5 (well, obviously not the _latest_. If we wanted the latest R5 contexts, we
would need to trigger a rebuild every time a commit was made to https://github.com/HL7/fhir...) in https://github.com/fhircat/jsonld_context_files

Note also, that there is a file [root.context.jsonld](https://github.com/fhircat/jsonld_context_files/blob/master/contextFiles/root.context.jsonld) that needs
to exist in both the R4 and R5 directories.

### JSON-LD Context Server
We keep a copy of https://github.com/fhircat/jsonld_context_files on the fhircat.org server.  Whenever the repository is
updated, you need to log onto fhircat.org:
```bash
> ssh -i ~/.ssh/id_ed25519 (user)@fhircat.org
$ cd /datatrive/temp/jsonld_context_files
$ sudo git pull
```
There are symlinks from the temp/jsonld_context_files into `/var/www/html/fhir-r4` and `/var/www/html/fhir-r5`, so the
web site is automatically updated by the above process.

You can verify that you've done at least part of this right by accessing https://fhircat.org/fhir-r4/original/contexts/root.context.jsonld and
https://fhircat.org/fhir-r5/original/contexts/root.context.jsonld.

__Note:__ The JSON-LD Javascript implementation chokes if you have a BOM header in any of your context files.  Beware, as a lot
of Java and other implementations put these in by default.  Note also that the Javascript error message, which shows up in the
[Playground](https://json-ld.org/playground/) is very misleading -- it says that you've got an invalid URL...

__Note:__ Both the [Javascript](https://github.com/digitalbazaar/jsonld.js) and the [Java](https://github.com/filip26/titanium-json-ld) JSON-LD 1.1 processors
support both file based (file://...) and relative context URI's.  One can gain several orders of magnitude performance improvement by
cloning the jsonld_context_files into a local directory and changing the root of the JSON-LD files from `https://fhircat.org/fhir-r4/original` to 
`file:///path to /jsonld_context_files/R4`.  Note also that, as of the time of this writing, the only JSON-LD 1.1 compliant python processor
([pyld](https://github.com/digitalbazaar/pyld)), does not handle `file://` based URLs _or_ relative paths.  It is my understanding that
[rdflib 6.0](https://github.com/RDFLib/rdflib) has rdflib-jsonld built in and has a beta JSON-LD 1.1 version.

## Setup
The instructions for using this package can be found in [README.md](README.md).


## Transformation tools
There are currently three software packages that implement the transformations described below:

### Python based FHIR JSON pre-processor
1) [json_preprocessor](https://github.com/FHIRCat/FHIRJsonLDAmiaPaper/fhir_jsonld/)
```text
usage: json_preprocessor.py [-h] [-i [INFILE [INFILE ...]]] [-id INDIR] [-o [OUTFILE [OUTFILE ...]]] [-od OUTDIR] [-f] [-s] [-c] [-fs FHIRSERVER] [-cs CONTEXTSERVER] [-vb VERSIONBASE]

Add FHIR R4 edits to JSON file

optional arguments:
  -h, --help            show this help message and exit
  -i [INFILE [INFILE ...]], --infile [INFILE [INFILE ...]]
                        Input file(s)
  -id INDIR, --indir INDIR
                        Input directory
  -o [OUTFILE [OUTFILE ...]], --outfile [OUTFILE [OUTFILE ...]]
                        Output file(s)
  -od OUTDIR, --outdir OUTDIR
                        Output directory
  -f, --flatten         Flatten output directory
  -s, --stoponerror     Stop on processing error
  -c, --addcontext      Add JSON-LD context references
  -fs FHIRSERVER, --fhirserver FHIRSERVER
                        FHIR server base
  -cs CONTEXTSERVER, --contextserver CONTEXTSERVER
                        Context server base
  -vb VERSIONBASE, --versionbase VERSIONBASE
                        Base URI for OWL version. Default: fhirserver
```
The [json_to_original.sh](json_to_original.md) script supplies the following defaults:

* $dir is either fhir-r4 or fhir-r5
* The default context server is https://fhircat.org/fhir-r5/original/contexts/

-id data/$dir/examples-json -od data/$dir/jsonld-pre/python -c -fs http://hl7.org/fhir/ -vb http://build.fhir.org/ -s $csparam

### Java based FHIR JSON-LD Preprocessor
The [Java FHIR JSON-LD CLI](https://github.com/fhircat/jsonld-cli) is a delightfully complete package that does both 
the preprocessing and the JSON-LD transformation phases.  It can be run by:
```bash
> wget https://github.com/fhircat/jsonld-cli/releases/download/v0.4.0-alpha/jsonld-cli-0.4.0-bin.tar.gz```
> tar -xzf v0.4.0-alpha/jsonld-cli-0.4.0-bin.tar.gz
> cd jsonld-cli-0.4.0/bin
> ./fhircatjsonld -h 
usage: FHIRCat JSON-LD Command Line Interface
 -f,--outputFormat <arg>     output format (one of: RDF/XML,N3,TURTLE,N-TRIPLE,TTL)
 -i,--input <arg>            input file path (single file or directory)
 -o,--output <arg>           output file (single file or directory) - standard output if omitted
 -p,--pre <arg>              output the intermediate 'pre'-JSON structures
 -vb,--versionbase <arg>     base URI for OWL version
 -cs,--contextserver <arg>   context server base
 -fs,--fhirserver <arg>      FHIR server base
 -v,--shexvalidate           apply ShEx validation
 -si,--sheximpl <arg>        the ShEx validation implementation
 -V,--verbose                print extra logging messages
 -h,--help                   print the usage help
```

### Javascript based FHIR JSON-LD Preprocessor
The Javascript Preprocessor lives in the fhir_jsonld_js directory.  You need to talk to Dazhi Jiao about where the
command line structural transformation lives.  Note that the online version of this transformation can be found at


## Transformation notes
* resource_type is JSON resourceType key
* dict_processor
    * any JSON dictionary that has a 
    
### Embedded Resources
* FHIR RDF does not differentiate a `reference` and an embedded resource.  The transformation code
recognizes an embedded resource by:
  1) It has a `resourceType` element. Example from careplan-example-f003-pharynx.json:
```json
{
  "resourceType": "CarePlan",
  "id": "f003",
  "text": {
    "status": "generated",
    "div": "..."
  },
  "contained": [
    {
      "resourceType": "CareTeam",
      "id": "careteam",
      "participant": [
        {
          "member": {
            "reference": "Practitioner/f001",
            "display": "E.M. van den broek"
          }
        }
      ]
    },
    {
      "resourceType": "Goal",
      "id": "goal",
      "lifecycleStatus": "completed",
      "achievementStatus": {
        "coding": [
          {
            "system": "http://terminology.hl7.org/CodeSystem/goal-achievement",
            "code": "achieved",
            "display": "Achieved"
          }
        ],
        "text": "Achieved"
      },
      "description": {
        "text": "Retropharyngeal abscess removal"
      },
      "subject": {
        "reference": "Patient/f001",
        "display": "P. van de Heuvel"
      },
      "note": [
        {
          "text": "goal accomplished without complications"
        }
      ]
    }
  ],
   ...
  "careTeam": [
    {
      "reference": "#careteam"
    }
  ],
    ...
  "goal": [
    {
      "reference": "#goal"
    }
  ],
```
This example represents three resource instances: `CarePlan`, `CareTeam`, and `Goal`.

`contained` elements can be referenced elsewhere within a document.  In the above example, the `#careteam` references the contained element whose id is `careteam`, and the goal, `goal`. As these resources are entirely self contained (i.e. do not exist outside the context of the containing resource), the subject URI of these embedded
resources are of the form "(contained type)/(container id)#(contained id)".  The (relative) subject URI of the `CareTeam` resource above would be "Goal/foo3#careteam". 

2) The resource is a bundle, then every `entry` within the bundle that has a `fullUrl` _and_ an accompanying `resource`
becomes a separate resource, whose subject URI is the `fullURL` and whose type is the embedded `resourceType`.  Example from bundle-example.json:
```json
{
  "resourceType": "Bundle",
  "id": "bundle-example",
      ...
  "entry": [
    {
      "fullUrl": "https://example.com/base/MedicationRequest/3123",
      "resource": {
        "resourceType": "MedicationRequest",
        "id": "3123",
        "text": {
          "status": "generated",
          "div": "..."
        },
        "status": "unknown",
        "intent": "order",
        "medicationReference": {
          "reference": "Medication/example"
        },
        "subject": {
          "reference": "Patient/347"
        }
      },
      "search": {
        "mode": "match",
        "score": 1
      }
    },
    {
      "fullUrl": "https://example.com/base/Medication/example",
      "resource": {
        "resourceType": "Medication",
      ...
```
The above bundle represents three resoure instances, `Bundle`, `MedicationRequest`, and `Medication`.

### Extensions
In JSON, FHIR Extensions take one of two forms. Using observation-example-1minute-apgar-score.json has:
```json
{
  "resourceType": "Observation",
  "id": "1minute-apgar-score",
     ...,
   "contained": [
    {
      "resourceType": "Patient",
      "id": "newborn",
        ...
      "birthDate": "2016-05-18",
      "_birthDate": {
        "extension": [
          {
            "url": "http://hl7.org/fhir/StructureDefinition/patient-birthTime",
            "valueDateTime": "2016-05-18T10:28:45Z"
          }
        ]
      }
    }
  ],
  "component": [
    {
      ...
      "valueCodeableConcept": {
        "coding": [
          {
            "extension": [
              {
                "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
                "valueDecimal": 0
              }
            ],
            "system": "http://loinc.org",
            "code": "LA6722-8",
            "display": "The baby\u0027s whole body is completely bluish-gray or pale",
      ...
    },
 ```
If the element is being extended is an object (e.g. `component[0].valueCodeableConcept.coding[0]`), the extension is
just added an "extension" tag directly to the object.   If, however, the element is a string, integer, etc., FHIR adds an extension by
adding a tag into the _parent_ object, whose value is an underscore ('_') prepended to the item being extended.  In the
above example, `contained[0].birthdate` is extended by inserting the `contained[0]._birthdate` element.

### Choices
The python implementation currently recognizes choice elements syntactically.  Any element name that matches the regular
expression: `value([A-Z].*)` with the exception of `valueSet` is considered to be a choice element, whose type is part in
parenthesis.  Note: While we originally went to great lengths to not need the FHIR StructureDefinition resource in order
to do this transformation, an issue finally arose that forced us to do as much.  As such, we _could_ revise the above 
to just look up the type of the element itself...

### References
The `"reference"` element in a FHIR [Reference](https://build.fhir.org/references.html#Reference) can take one of three
forms:
1) An absolute URL -- the identity of and, ideally, the URL from which the referenced resource can be retrieved:
    ```json
    { ...
      "subject": [
        {
          "reference": "https://megaclinic.com/patients/11793M6p2",
          "display": "Peter James Chalmers"
        }
      ]
   }
    ```
2) A relative URL -- the URL of the resource that is resolved in the context of the service from which the containing
resource was retrieved
    ```json
    { ...
      "subject": [
        {
          "reference": "Patient/p11743x2",
          "display": "Peter James Chalmers"
        }
      ]
   }
    ```
3) An "internal" URL -- a URL that begins with a hash mark ("#") that references an `"id"` within the `"contained"` section:
    ```json
    {
      "contained": [
        {
          "resourceType": "CareTeam",
          "id": "careteam",
          "participant": [
            {
              "member": {
                "reference": "Practitioner/f001",
                "display": "E.M. van den broek"
              }
            }
          ]
        },
     ],
     ...
      "careTeam": [
        {
           "reference": "#careteam"
        }
      ],
    }
    ```
The RDF processor needs to be able to generate the correct URL for each of these three situations, along with the
expected target type.  It also needs to generate this URL _without_ removing or altering the original form ... while
it would be possible to change 

    `"reference": "Patient/p11743x2"` 
to

    `"reference": "http://hl7.org/fhir/Patient/example"`

There would be no way to reverse this transformation, as we don't know whether we started with an absolute or relative
URL.  Note also that, assuming we are using the semi-official FHIR URL scheme, if "http://hl7.org/fhir/Account/example"
included a reference to "Patient/p11743x2", the default relative URI scheme would resolve to:
"http://hl7.org/fhir/ **Account** /Patient/p11743x2" instead of just "http://hl7.org/fhir/Patient/p11743x2".

### canonical types
The [FHIR canonical data type](https://build.fhir.org/datatypes.html#canonical) is the "fly in the ointment". While it
appears, at the moment, that all of elements of type "canonical" are named "aaaaaCanonical", there is nothing in the
spec that says that this has to be the case.  (It may also be that we failed to notice this when we were doing the 
conversion :-( ).  If you ignore lexical matching, there is no way to determine whether an entry is a string or a 
link.  

Line 551 in json_preprocessor.main calls the `FSVProcessor`, which loads fhir.ttl from the input directory. It has two
functions:
* `is_canonical(path)` - determines whether the element in path (a list of FHIR nodes) is the canonical type
* `is_date(path)` - determines whether the element in path is of type `fhir:date`, `fhir:time` or `fhir:dateTime`.



### uri types


### Datatypes


## Actual processing
### Drop
1) any JSON elements whose keys begin with '@'.  While this isn't strictly necessary, it is possible that JSON-LD
processing instructions may be embedded. (#286)
## Add
1) Whenever a `Coding` path is encountered which contains both `system` and `code`:
   1) Remove trailing "#" and "/"'ss from the system URI if necessary
   2) If result is "http://snomed.info/sct", use the curie prefix "sct:"
   3) If result is "http://loinc.org", use the curie prefix, "loinc:"
   4) Otherwise use the system URI with '/' appended if it doesn't already end in a '#' or a '/'
   5) URL escape the code (!)
   6) Add `"@type": "(system)(url escaped code)" to the `Coding` element
2) Any FHIR resource can "contain" (embed) other resources via the '"container"' mechanism.  The FHIR Bundle resource can
also "contain" other dependent resources.  In order to reconstruct JSON from RDF, one needs to know which resource was
the outermost and which were the contained.  The FHIR RDF transform accomplishes this by adding:
  `"nodeRole": "fhir:treeRoot"` to the outermost object
3) `"@id"` nodes -- see [Resource identifiers](#Resource identifiers) in the [Transform](#Transform) section below
4) 
### Transform

#### Resource types
We have to make two transformations to the `resourceType` element:
1) We have to add the `fhir:` prefix to the actual type: `"resourceType": "Patient"` becomes `"resourceType": "fhir:Patient"`
2) We have to add a JSON-LD context reference to allow the contents of the resource to be correctly interpreted:

    `"@context": (context server)(lower case type).context.jsonld`
The first transformation is needed because JSON-LD only allows one default URI (`"@base"`) for non-qualified identifiers.
We use the base to establish the root of of the subject identifiers.  As such, we have to qualify any string objects that
need to resolve to URL's

### Resource identifiers
Given the following:
```json
{
  "id": "p12345"
}
```
JSON-LD can either treat the identifier as a subject:
```json
{
  "@context": {"id":  "@id"}
}
```
or as a value:
```json
{
  "@context": {"id":  "fhir:id"}
}
```
But not both.  To address this, we add an explicit subject identifier using the following rules
1) If the JSON object that has the `"id"` also has a `"resourceType"` element, we aren't within a container _and_ 
the id does not start with "#", add:

  `"@id": "(resourceType)/(id)"` 

Otherwise, add:

  `"@id": "(fullUri associated with #id)"` if full URI is present
  
### "terminal" values
With the exception of `"nodeRole"`, `"index"` and `"div"`, all non-object, non-array elements are converted into objects:

```json
{
   ...,
  "k1": "v",
  "k2": 123,
  "k3": true,
  "k4": false,
  "nodeRole": "Patient",
  "div": "some stuff",
  "index": 0
}
```
becomes:
```json
{
   ...,
  "k1": {
    "value": "v"
  },
  "k2": {
    "value": 123
  },
  "k3": {
    "value": true
  },
  "k4": {
    "value": false
  },
  "nodeRole": "Patient",
  "div": "some stuff",
  "index": 0
}
```
Notes:
* "nodeRole" is 


## References
* https://www.json.org/json-en.html