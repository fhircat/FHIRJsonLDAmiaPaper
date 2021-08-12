# Issues with the current FHIR RDF Conversion
Note that these issues are all based an October 20, 2020 dump of the FHIR resources.  New bugs may have been introduced
and existing bugs may have been fixed.

1) The coding type arc isn't escaped in R5 build
Using plandefinition-example-cardiology-os.json, there is a code field that is "look up value". In the FHIR R4
examples-ttl.zip, this is emitted as `a sct:look%20up%20value;`.  In the R5 examples-ttl.zip, however, it comes
out as `a sct:look up value;`.
