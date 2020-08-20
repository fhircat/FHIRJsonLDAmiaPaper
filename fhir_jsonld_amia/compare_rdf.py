# See original source code at https://github.com/fhircat/fhir_rdf_validator/blob/master/fhir_rdf_validator/compare_rdf.py
import json
import os
import re
import sys
from argparse import Namespace, ArgumentParser
from contextlib import redirect_stdout
from io import StringIO
from os import path
from typing import Union, Optional, List, Tuple

import dirlistproc
from rdflib import Graph, RDF, URIRef, BNode
from rdflib.compare import graph_diff, similar

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
    # Prefixes appear to be useful
    # g_text = re.sub(r'@prefix.*\n', '', g.serialize(format="turtle").decode())
    g_text = g.serialize(format="turtle").decode()
    print(g_text)


def subj_diff(expected: Graph, actual: Graph) -> Optional[str]:
    """
    Validate the non-bnode subjects

    :param expected:
    :param actual:
    :return:
    """
    expected_subjs = set([str(s) for s in expected.subjects() if isinstance(s, URIRef)])
    actual_subjs = set([str(s) for s in actual.subjects() if isinstance(s, URIRef)])
    expected_only = sorted(list(expected_subjs.difference(actual_subjs)))
    actual_only = ((actual_subjs.difference(expected_subjs)))
    if expected_only or actual_only:
        exp_str = "----- Missing Subjects -----\n\t"
        act_str = "----- Added Subjects -----\n\t"
        if expected_only:
            exp_str += '\n\t'.join(expected_only)
        if actual_only:
            act_str += '\n\t'.join(expected_only)
        return exp_str + '\n' + act_str
    return None

def remove_subgraph(pred: URIRef, g: Graph) -> None:
    """ Remove the subgraph that is the target of pred """

    def rem_obj(subj: BNode) -> None:
        for p, o in g.predicate_objects(subj):
            if isinstance(o, BNode):
                rem_obj(o)
            g.remove((subj, p, o))

    for s, o in g.subject_objects(pred):
        if isinstance(o, BNode):
            rem_obj(o)
        g.remove((s, pred, o))

def compare_rdf(expected: Union[Graph, str], actual: Union[Graph, str], fmt: Optional[str] = "turtle",
                detailed: bool=True) \
        -> Tuple[Optional[str], int, int, int]:
    """
    Compare expected to actual, returning a string if there is a difference
    :param expected: expected RDF. Can be Graph, file name, uri or text
    :param actual: actual RDF. Can be Graph, file name, uri or text
    :param fmt: RDF format
    :param detailed: True means do an in depth compare, False means just report if mismatch
    :return: String describing difference, # in both, # in expected only, # in actual only
    """

    def rem_metadata(g: Graph) -> Graph:
        # Remove list declarations from target
        for s in g.subjects(RDF.type, RDF.List):
            g.remove((s, RDF.type, RDF.List))
        return g

    expected_graph = rem_metadata(to_graph(expected, fmt))
    actual_graph = rem_metadata(to_graph(actual, fmt))

    # TODO: Get the URLs into FHIR R5
    for s, o in list(actual_graph.subject_objects(RDF.type)):
        if "http://terminology.hl7.org/CodeSystem/" in str(o):
            actual_graph.remove((s, RDF.type, o))

    # We assume that similar may give false negatives, but is pretty good on the positive side
    if similar(expected_graph, actual_graph):
        return None, len(expected_graph), 0, 0
    if not detailed:
        return "Files do not match", len(expected_graph), 0, 0

    in_both, in_old, in_new = graph_diff(expected_graph, actual_graph)

    old_len = len(list(in_old))
    new_len = len(list(in_new))
    if old_len or new_len:
        # Start by checking the subjects
        diffs = subj_diff(in_old, in_new)
        if diffs:
            return diffs, len(in_both), len(in_old), len(in_new)
        txt = StringIO()
        with redirect_stdout(txt):
            print("----- Missing Triples -----")
            if old_len:
                print_triples(in_old)
            print("----- Added Triples -----")
            if new_len:
                print_triples(in_new)
        return txt.getvalue(), len(in_both), len(in_old), len(in_new)
    return None, len(in_both), len(in_old), len(in_new)


def compare_files(actual_file_name: str, expected_file_name: str, opts: Namespace) -> bool:
    """
    Compare

    :param actual_file_name: Name of generated RDF file -- assumed to be ntriples (nt) format
    :param expected_file_name: Name of expected RDF file if specific else ".ttl" form of actual_file_name
    :param opts: Parameters
    :return: True if conversion is successful
    """
    print(f'Processing {actual_file_name}')
    actual_file = actual_file_name
    expected_file = expected_file_name if opts.outfile else \
                    actual_file_name.replace(opts.indir, opts.turtledir).replace(opts.infilesuffix, '.ttl')
    if not path.exists(expected_file):
        print(f'{os.path.join(os.path.dirname(__file__), expected_file)} not found')
        return False
    report_file = actual_file_name.replace(opts.indir, opts.outdir).replace(opts.infilesuffix, '.txt') if not opts.outfile else None
    with open(actual_file, 'r') as f:
        actual_str = f.read()
    if 'UNKNOWN' in actual_str:
        print(f'{actual_file_name} is not completely mapped')
        return False
    with open(expected_file, 'r') as file:
        expected_str = file.read()
    # TODO: A monkey patch (kludge) to fix the issue in comparing when jsonld has ^^xsd:string and ^^xsd:anyURI
    actual_str = actual_str.replace("^^<http://www.w3.org/2001/XMLSchema#anyURI>", "")

    actual_graph = Graph().parse(data=actual_str, format='nquads')

    # TODO: File a report to FHIR that meta is missing in FHIR RDF Turtle
    remove_subgraph(URIRef('http://hl7.org/fhir/Resource.meta'), actual_graph)

    # TODO: Address fhir date/dateTime context sensitive issue
    expected_str = expected_str.replace("^^xsd:date ", "^^xsd:dateTime ").replace("^^xsd:gYear ", "^^xsd:dateTime ")\
        .replace("^^xsd:gYearMonth ", "^^xsd:dateTime ")
    expected_graph = to_graph(expected_str, 'turtle')
    result, len_in_both, len_in_new, len_in_old = compare_rdf(expected_graph, actual_graph, detailed=not opts.skipdetailedcompare)

    if result:
        if report_file:
            with open(report_file, 'w') as file:
                file.write(result)
        else:
            print(result)
    print('[COUNT] ', actual_file_name, len_in_both, len_in_new, len_in_old)
    return True


def input_filter(filename: str, dirpath: str, opts: Namespace) -> bool:
    # Code systems aren't currently converted to RDF
    return bool(opts.infile) or not filename.startswith('codesystem-')


def addargs(parser: ArgumentParser) -> None:
    parser.add_argument("-td", "--turtledir", help="Turtle directory")
    parser.add_argument("-sdc", "--skipdetailedcompare", help="Do a fast non-detailed compare", action="store_true")
    parser.add_argument("-ifs", "--infilesuffix", help="Input file suffix (default: .nq", default='.nq')


def main(argv: Optional[Union[str, List[str]]] = None) -> object:
    """
    Apply R4 edits to FHIR JSON files

    :param argv: Argument list.  Can be unparsed string, a list of strings or nothing. If nothing, we use sys.argv
    :return: 0 if all RDF files that had valid FHIR in them were successful, 1 otherwise
    """
    def gen_dlp(args: List[str]) -> dirlistproc.DirectoryListProcessor:
        return dirlistproc.DirectoryListProcessor(args, "Add FHIR R4 edits to JSON file", '.nq', '.json',
                                                  addargs=addargs)

    dlp = gen_dlp(argv)
    if dlp.opts.infile:
        dlp.infile_suffix = ''
    else:
        dlp.infile_suffix = dlp.opts.infilesuffix
    if dlp.opts.outfile:
        dlp.outfile_suffix = ''
    if not (dlp.opts.infile or dlp.opts.indir):
        gen_dlp(argv if argv is not None else sys.argv[1:] + ["--help"])  # Does not exist

    dlp.opts.converted_files = []           # If converting inline

    nfiles, nsuccess = dlp.run(compare_files, file_filter_2=input_filter)

    return 0 if nfiles == nsuccess else 1


if __name__ == '__main__':
    main()
