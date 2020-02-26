import glob

from rdflib import Graph, XSD
from rdflib.namespace import SKOS

prefixes = f"""
@prefix : <http://phenopackets.org/> .
@prefix xsd: <{XSD}> .
@prefix skos: <{SKOS}> . 
@prefix NCBITaxon: <http://purl.obolibrary.org/obo/NCBITaxon_> . 
@prefix fhir: <http://hl7.org/fhir/> .
"""


# Convert all n3 files to turtle adding needed prefixes
# Convert each file seperately then merge all of the results
all_ttl = Graph()
all_ttl.parse(data=prefixes, format="turtle")
for ne_file in glob.iglob("*.n3"):
    g = Graph()
    g.load(ne_file, format="n3")
    g.parse(data=prefixes, format="turtle")
    all_ttl += g

    ttl_file = f"{ne_file.rsplit('.', 1)[0]}.ttl"
    g.serialize(ttl_file, format="turtle")
    print(f"Generated {ttl_file}")

all_ttl.serialize("all.ttl", format="turtle")
print("all.ttl generated")