#!/usr/bin/env bash

dir="fhir-r5"
if [ "$1" != "" ]; then
  dir=$1
fi

echo Processing FHIR release $dir


# 1) Run the preprocessor over the FHIR JSON
rm data/$dir/jsonld-pre/*
pipenv run python fhir_jsonld_amia/json_preprocessor.py -id data/$dir/examples-json -od data/$dir/jsonld-pre -c -fs http://hl7.org/fhir/ -vb http://build.fhir.org/ -s
exit

# 2) Convert the pre-processed JSON into RDF
rm data/$dir/original/*
cd fhir_jsonld_js
yarn jsonld -c toRDF -n ../data/$dir/jsonld-pre -m ../data/$dir/original
cd ..

# 3) Compare the JSON conversion to what was there to begin with
rm data/$dir/compare-report/*
pipenv run python fhir_jsonld_amia/compare_rdf.py -id data/$dir/original -od data/$dir/compare-report -td data/$dir/examples-ttl
