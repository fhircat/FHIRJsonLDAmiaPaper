#!/usr/bin/env bash

usage="Usage: json_to_original-sh [-1, -2, -3 or -a] [-v]  [-java, -js or -all] [-cs contextsource] [-co compareopts] [directory]"
examples_dir="fhir-r5"
COMPAREOPTS="-sta -maxtc 3000 -dec -maxt 5000 -mb -tc -v"
VERBOSE=""

echo Processing FHIR release $dir
while [ "$#" -gt 0 ]; do
  case $1 in
    -java) PROC_JAVA=T; shift 1 ;;
    -js) PROC_JS=T; shift 1 ;;
    -1) P1=T; shift 1;;
    -2) P2=T; shift 1;;
    -3) P3=T; shift 1;;
    -a) P1=T; P2=T; P3=T; shift 1;;
    -all) PROC_JS=T; PROC_JAVA=T; shift 1;;
    -cs) CONTEXT_SERVER="$2"; shift 2;;
    -co) COMPAREOPTS=$2; shift 2;;
    --help) echo $usage; exit 1;;
    -v) VERBOSE="-v"; shift 1;;
    -*) echo $usage; exit 1;;
    *) dir=$1; shift 1;;
  esac
done

if  ! ([ $dir ]) ; then
   echo "data directory needs to be supplied (e.g. fhir-r5, fhir-r4, ...)"
   exit 1
fi
   
if [ $P2 ] || [ $P3 ]; then
   if ! ( [ $PROC_JS ] ||  [ $PROC_JAVA ] ); then
     echo "Need to specify -java or -js"
     exit 1
   fi
fi
echo Vals: p1=$P1 p2=$P2 p3=$P3 js=$PROC_JS java=$PROC_JAVA dir=$dir CONTEXT_SERVER=$CONTEXT_SERVER

if [ $P1 ]; then
        echo "Preprocessing data/$dir/examples-json to data/$dir/jsonld-pre/"
        if [ $CONTEXT_SERVER ]; then
          csparam="-cs $CONTEXT_SERVER"
        else
          csparam=""
        fi
 	rm -f data/$dir/jsonld-pre/python/*
        pipenv run python fhir_jsonld_amia/json_preprocessor.py -id data/$dir/examples-json -od data/$dir/jsonld-pre/python -c -fs http://hl7.org/fhir/ -vb http://build.fhir.org/ -s $csparam 
fi
if [ $P2 ]; then
        if [ $PROC_JAVA ]; then
            echo "Converting data/$dir/jsonld-pre/python to data/$dir/original/java"
            rm -f data/$dir/original/java/*
            java -jar fhir_jsonld_java/jsonld-cli-1.0-SNAPSHOT-jar-with-dependencies.jar -f ttl --input data/$dir/jsonld-pre/python --output data/$dir/original/java 
         fi
         if [ $PROC_JS ]; then
            echo "Converting data/$dir/jsonld-pre to data/$dir/original/js"
            rm -f data/$dir/original/js/*
            pushd fhir_jsonld_js
            yarn jsonld -c toRDF -n ../data/$dir/jsonld-pre/python -m ../data/$dir/original/js 
  	    popd
         fi
fi
if [ $P3 ]; then
        if [ $PROC_JAVA ]; then
           echo "Generating data/$dir/compare-report/java from  data/$dir/original/java and data/$dir/examples-ttl"
           rm -f data/$dir/compare-report/java/*
           pipenv run python fhir_jsonld_amia/compare_rdf.py -id data/$dir/original/java -od data/$dir/compare-report/java -td data/$examples_dir/examples-ttl $COMPAREOPTS $VERBOSE 
           # pipenv run python fhir_jsonld_amia/compare_rdf.py -id data/$dir/original/java -od data/$dir/compare-report/java -td data/$examples_dir/examples-ttl $COMPAREOPTS $VERBOSE 
        fi
        if [ $PROC_JS ]; then
           echo "Generating data/$dir/compare-report/js from  data/$dir/original/js and data/$dir/examples-ttl"
           rm -f data/$dir/compare-report/js/*
           pipenv run python fhir_jsonld_amia/compare_rdf.py -id data/$dir/original/js -od data/$dir/compare-report/js/ -td data/$examples_dir/examples-ttl $COMPAREOPTS 
        fi
fi
echo DONE!
