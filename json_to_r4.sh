#!/usr/bin/env bash

rm data/jsonld-pre/*
rm data/jsonld-r4/*
rm data/compare-report/*

pipenv run python fhir_jsonld_amia/json_to_r4.py -id data/examples-json -od data/jsonld-pre -c -fs http://hl7.org/fhir/
cd fhir_jsonld_js
yarn jsonld -c expand -n ../data/jsonld-pre -m ../data/jsonld-r4
cd ..
pipenv run python fhir_jsonld_amia/compare_rdf.py -id data/jsonld-r4 -od data/compare-report -td data/examples-ttl