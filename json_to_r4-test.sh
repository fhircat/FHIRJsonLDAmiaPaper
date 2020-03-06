#!/usr/bin/env bash

rm data/test-jsonld-pre/*
rm data/test-jsonld-r4/*
rm data/test-report/*

pipenv run python fhir_jsonld_amia/json_to_r4.py -id data/test-json -od data/test-jsonld-pre -c -fs http://hl7.org/fhir/
cd fhir_jsonld_js
yarn jsonld -c expand -n ../data/test-jsonld-pre -m ../data/test-jsonld-r4
cd ..
pipenv run python fhir_jsonld_amia/compare_rdf.py -id data/test-jsonld-r4 -od data/test-report -td data/test-ttl