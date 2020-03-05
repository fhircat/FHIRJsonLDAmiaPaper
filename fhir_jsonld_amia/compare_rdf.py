# See original source code at https://github.com/fhircat/fhir_rdf_validator/blob/master/fhir_rdf_validator/compare_rdf.py

import re
import sys
from argparse import Namespace, ArgumentParser
from contextlib import redirect_stdout
from io import StringIO
from typing import Union, Optional, List
from os import path

import dirlistproc
from rdflib import Graph, RDF, URIRef
from rdflib.compare import to_isomorphic, IsomorphicGraph, graph_diff


def to_graph(inp: Union[Graph, str], fmt: Optional[str] = "turtle") -> Graph:
    """
    Convert inp into a graph
    :param inp: Graph, file name, url or text
    :param fmt: expected format of inp
    :return: Graph representing inp
    """
    if isinstance(inp, Graph):
        return inp
    g = Graph()
    if not inp.strip().startswith('{') and '\n' not in inp and '\r' not in inp:
        with open(inp) as f:
            inp = f.read()
    g.parse(data=inp, format=fmt)
    return g


def print_triples(g: Graph) -> None:
    """
    Print the contents of g into stdout
    :param g: graph to print
    """
    g_text = re.sub(r'@prefix.*\n', '', g.serialize(format="turtle").decode())
    print(g_text)


def compare_rdf(expected: Union[Graph, str], actual: Union[Graph, str], fmt: Optional[str] = "turtle") -> Optional[str]:
    """
    Compare expected to actual, returning a string if there is a difference
    :param expected: expected RDF. Can be Graph, file name, uri or text
    :param actual: actual RDF. Can be Graph, file name, uri or text
    :param fmt: RDF format
    :return: None if they match else summary of difference
    """
    def rem_metadata(g: Graph) -> IsomorphicGraph:
        # Remove list declarations from target
        for s in g.subjects(RDF.type, RDF.List):
            g.remove((s, RDF.type, RDF.List))
        g_iso = to_isomorphic(g)
        return g_iso

    expected_graph = to_graph(expected, fmt)
    expected_isomorphic = rem_metadata(expected_graph)
    actual_graph = to_graph(actual, fmt)
    actual_isomorphic = rem_metadata(actual_graph)

    # TODO: Get the URLs into FHIR R5
    for s, o in list(actual_isomorphic.subject_objects(RDF.type)):
        if "http://terminology.hl7.org/CodeSystem/" in str(o):
            actual_isomorphic.remove((s, RDF.type, o))

    # Graph compare takes a Looong time
    in_both, in_old, in_new = graph_diff(expected_isomorphic, actual_isomorphic)
    # if old_iso != new_iso:
    #     in_both, in_old, in_new = graph_diff(old_iso, new_iso)
    old_len = len(list(in_old))
    new_len = len(list(in_new))
    if old_len or new_len:
        txt = StringIO()
        with redirect_stdout(txt):
            print("----- Missing Triples -----")
            if old_len:
                print_triples(in_old)
            print("----- Added Triples -----")
            if new_len:
                print_triples(in_new)
        return txt.getvalue()
    return None


def compare_files(ifn: str, ofn: str, opts: Namespace) -> bool:
    """
    Convert ifn to ofn

    :param ifn: Name of rdf file
    :param ofn: Name of jsonld file
    :param opts: Parameters
    :return: True if conversion is successful
    """
    print(f'Processing {ifn}')
    r4_file = ifn
    ttl_file = ifn.replace(opts.indir, opts.turtledir).replace('.json', '.ttl')
    if not path.exists(ttl_file):
        return False
    report_file = ifn.replace(opts.indir, opts.outdir).replace('.json', '.txt')
    with open(r4_file, 'r') as file:
        r4_str = file.read()
    with open(ttl_file, 'r') as file:
        ttl_str = file.read()
    # TODO: A monkey patch (kludge) to fix the issue in comparing when jsonld has ^^xsd:string and ^^xsd:anyURI
    r4_str = r4_str.replace('"@type": "http://www.w3.org/2001/XMLSchema#string",', '').replace('"@type": "http://www.w3.org/2001/XMLSchema#anyURI",', '')
    r4_graph = to_graph(r4_str, 'json-ld')
    # TODO: Address fhir date/dateTime context sensitive issue
    ttl_str = ttl_str.replace("^^xsd:date ", "^^xsd:dateTime ")
    ttl_graph = to_graph(ttl_str, 'turtle')
    result = compare_rdf(ttl_graph, r4_graph)
    with open(report_file, 'w') as file:
        file.write(result)
    return True


def addargs(parser: ArgumentParser) -> None:
    parser.add_argument("-td", "--turtledir", help="Turtle directory")


def main(argv: Optional[Union[str, List[str]]] = None) -> object:
    """
    Apply R4 edits to FHIR JSON files

    :param argv: Argument list.  Can be unparsed string, a list of strings or nothing. If nothing, we use sys.argv
    :return: 0 if all RDF files that had valid FHIR in them were successful, 1 otherwise
    """
    def gen_dlp(args: List[str]) -> dirlistproc.DirectoryListProcessor:
        return dirlistproc.DirectoryListProcessor(args, "Add FHIR R4 edits to JSON file", '.json', '.json', addargs=addargs)

    dlp = gen_dlp(argv)
    if not (dlp.opts.infile or dlp.opts.indir):
        gen_dlp(argv if argv is not None else sys.argv[1:] + ["--help"])  # Does not exist

    dlp.opts.converted_files = []           # If converting inline

    nfiles, nsuccess = dlp.run(compare_files)

    return 0 if nfiles == nsuccess else 1


if __name__ == '__main__':
    main()