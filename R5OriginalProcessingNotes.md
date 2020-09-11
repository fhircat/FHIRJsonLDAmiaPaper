# Notes on FHIR R5 Original Processing

## To address
* \# TODO: A monkey patch (kludge) to fix the issue in comparing when jsonld has ^^xsd:string and ^^xsd:anyURI
  actual_str = actual_str.replace("^^<http://www.w3.org/2001/XMLSchema#anyURI>", "")
* \# TODO: File a report to FHIR that meta is missing in FHIR RDF Turtle
    remove_subgraph(URIRef('http://hl7.org/fhir/Resource.meta'), actual_graph)

## Incomplete mapping




## Coded type arcs
The current FHIR R5 conversion doesn't work very hard to generate type arcs.  The conversion code has
the following process:




