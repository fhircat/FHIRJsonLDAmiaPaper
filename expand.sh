#!/usr/bin/env bash

dir="fhir-r5"
if [ "$1" != "" ]; then
  dir=$1
fi

echo $dir
pushd data/$dir
rm  examples-json/*
rm  examples-ttl/*

unzip examples-json.zip -d examples-json
unzip examples-ttl.zip -d examples-ttl
popd
