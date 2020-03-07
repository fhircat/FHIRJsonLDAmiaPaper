#!/usr/bin/env bash

dir="fhir-r5"
if [ "$1" != "" ]; then
  dir=$1
fi

echo $dir

rm data/$dir/jsonld-pre/*
rm data/$dir/jsonld-r4/*
rm data/$dir/compare-report/*

pipenv run python fhir_jsonld_amia/json_to_r4.py -id data/$dir/examples-json -od data/$dir/jsonld-pre -c -fs http://hl7.org/fhir/ -vb http://build.fhir.org/
cd fhir_jsonld_js
yarn jsonld -c expand -n ../data/$dir/jsonld-pre -m ../data/$dir/jsonld-r4
cd ..
pipenv run python fhir_jsonld_amia/compare_rdf.py -id data/$dir/jsonld-r4 -od data/$dir/compare-report -td data/$dir/examples-ttl