import os
import sys
from argparse import Namespace, ArgumentParser
from contextlib import redirect_stdout
from io import StringIO
from os import path
from typing import Union, Optional, List, Tuple, Callable, Set

import dirlistproc
from rdflib import Graph, RDF, URIRef, BNode, Literal, XSD, Namespace as RDFNamespace
from rdflib.compare import graph_diff, similar

from rdf_postprocessor import post_process
from summary import Heading, Counter

FHIR = RDFNamespace('http://hl7.org/fhir/')
FHIR_META = FHIR['Resource.meta']


def visit_graph(g: Graph, predicate: Callable[[Tuple], bool], replacement: Callable[[Tuple], Optional[Tuple]]) -> bool:
    """ Visit a copy of g and, for every triple that meets the predicate, replace t with replacement.
        Return true if any replacements were made
    """
    replacements_were_made = False
    for t in list(g):
        if predicate(t):
            g.remove(t)
            new_t = replacement(t)
            if new_t is not None:
                g.add(new_t)
            replacements_were_made = True
    return replacements_were_made


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


def print_triples(g: Graph, fmt: str) -> None:
    """
    Print the contents of g into stdout
    :param g: graph to print
    :param fmt: format to print the graph in
    """
    # Prefixes appear to be useful
    # g_text = re.sub(r'@prefix.*\n', '', g.serialize(format="turtle").decode())
    g_text = g.serialize(format=fmt).decode()
    print(g_text)


def subj_diff(expected: Graph, actual: Graph) -> Optional[str]:
    """
    Make sure that both graphs have the same non-BNODE subjects
    :param expected: Graph being compared against
    :param actual: Graph being compared
    :return: Error message if subjects don't agree
    """
    expected_subjs = set([str(s) for s in expected.subjects() if isinstance(s, URIRef)])
    actual_subjs = set([str(s) for s in actual.subjects() if isinstance(s, URIRef)])
    expected_only = sorted(list(expected_subjs.difference(actual_subjs)))
    actual_only = sorted(list(actual_subjs.difference(expected_subjs)))

    if expected_only or actual_only:
        exp_str = "----- Missing Subjects -----\n\t"
        act_str = "----- Added Subjects -----\n\t"
        if expected_only:
            exp_str += '\n\t'.join(expected_only)
        if actual_only:
            act_str += '\n\t'.join(actual_only)
        # TODO: These subjects appear to be legitimately added -- issue in FHIR conversion
        if len(expected_only) == 0:
            return None
        return exp_str + '\n' + act_str
    return None


def remove_subgraph(pred: URIRef, g: Graph) -> None:
    """ Remove the subgraph that is the target of pred """

    def rem_obj(subj: BNode) -> None:
        for rp, ro in g.predicate_objects(subj):
            if isinstance(ro, BNode):
                rem_obj(ro)
            g.remove((subj, rp, ro))

    for s, o in g.subject_objects(pred):
        if isinstance(o, BNode):
            rem_obj(o)
        g.remove((s, pred, o))


summary = Heading("files processed")
summary.nsuccesses = Counter("successful matches")

summary.nfails = Heading("match failures")
summary.nfails.nincompletes = Counter("incomplete transforms (UNKNOWN in output)", print_progress=True)
summary.nfails.nmismatches = Counter("content mismatch")

summary.nskips = Heading("files skipped")
summary.nskips.ncodesystems = Counter("code systems")
summary.nskips.nvaluesets = Counter("value sets")
summary.nskips.ntargetmissing = Heading("missing FHIR ttl files")
summary.nskips.ntargetmissing.nprofiles = Counter("missing profiles")
summary.nskips.ntargetmissing.nextensions = Counter("missing extensions")
summary.nskips.ntargetmissing.nmissing = Counter("missing for other reasons")
summary.nskips.ntoolarge = Counter("files with too many triples")

details = Heading("details")
details.ntoolarge = Counter("files too big for detailed comparison")
details.nmissingsourcemetadata = Counter("missing metadata in source")
details.ntypearcadjustments = Counter("adjusted type arcs")
details.nadjusteddecimals = Counter("adjusted decimals")
details.ncontaiment = Counter("expected files with incorrect contained mapping", print_progress=True)

# TODO: This is temporary
unknowns: Set[str] = set()
contains: Set[str] = set()

def compare_rdf(filename: str, expected: Union[Graph, str], actual: Union[Graph, str], opts: Namespace)\
        -> Tuple[Optional[str], int, int, int]:
    """
    Compare expected to actual, returning a string if there is a difference
    :param filename: File being tested
    :param expected: expected RDF. Can be Graph, file name, uri or text
    :param actual: actual RDF. Can be Graph, file name, uri or text
    :param opts: Input arguments
    :return: String describing difference, # in both, # in expected only, # in actual only
    """

    def remove_list_identifiers(g: Graph) -> Graph:
        """ Remove list declarations from the graph """
        for rs in g.subjects(RDF.type, RDF.List):
            g.remove((rs, RDF.type, RDF.List))
        return g

    def fix_strings(g: Graph) -> Graph:
        """ Remove explicit string datatypes from the graph """
        visit_graph(g,
                    lambda t: isinstance(t[2], Literal) and t[2].datatype and t[2].datatype == XSD.string,
                    lambda t: (t[0], t[1], Literal(str(t[2]))))
        return g

    expected_graph = remove_list_identifiers(fix_strings(to_graph(expected, "turtle")))
    actual_graph = remove_list_identifiers(fix_strings(to_graph(actual, "turtle")))

    # We assume that similar may give false negatives, but is pretty good on the positive side
    if similar(expected_graph, actual_graph):
        return None, len(expected_graph), 0, 0

    # It is possible, but not certain that the graphs differ
    expected_graph_length = len(expected_graph)

    if opts.skipdetailedcompare or (opts.maxcomparetriples and expected_graph_length > opts.maxcomparetriples):
        details.ntoolarge.inc(filename)
        summary.nfails.nmismatches.inc(filename)
        return "similar() comparison mismatch", expected_graph_length, expected_graph_length, len(actual_graph)

    in_both, in_old, in_new = graph_diff(expected_graph, actual_graph)
    old_len = len(list(in_old))
    new_len = len(list(in_new))
    recheck = False

    # Now that we know we've got differences, use actual differences as a guide to tweak the originals
    if new_len:
        if opts.skiptypearcs:
            for s, p, o in in_new:
                if isinstance(s, BNode) and p == RDF.type:
                    if visit_graph(actual_graph,
                                   lambda t: isinstance(t[0], BNode) and
                                             t[1] == RDF.type and 'snomed.info/id/' not in str(t[2]) and
                                             'http://loinc.org/' not in str(t[2]),
                                   lambda t: None):
                            recheck = True
                    break
    if recheck:
        details.ntypearcadjustments.inc(filename)
        in_both, in_old, in_new = graph_diff(expected_graph, actual_graph)
        old_len = len(list(in_old))
        new_len = len(list(in_new))
        recheck = False

    if new_len:
        if opts.adjustdecimals:
            # It turns out that decimal problems aren't just in JSON -- different rdflib parsers deal with them differently
            # It looks like the only wan to fix this is to twiddle ALL decimals, both old and new, when there is an issue
            for s, p, o in in_new:
                if isinstance(o, Literal) and o.datatype == XSD.decimal:
                    visit_graph(expected_graph,
                                lambda t: isinstance(t[2], Literal) and t[2].datatype == XSD.decimal,
                                lambda t: (t[0], t[1], Literal(float(str(t[2])), datatype=XSD.decimal)))
                    visit_graph(actual_graph,
                                lambda t: isinstance(t[2], Literal) and t[2].datatype == XSD.decimal,
                                lambda t: (t[0], t[1], Literal(float(str(t[2])), datatype=XSD.decimal)))
                    details.nadjusteddecimals.inc(filename)
                    recheck = True
                    break

    if recheck:
        in_both, in_old, in_new = graph_diff(expected_graph, actual_graph)
        old_len = len(list(in_old))
        new_len = len(list(in_new))
        recheck = False

    if old_len or new_len:
        # Start by checking the subjects
        diffs = subj_diff(in_old, in_new)
        if diffs:
            summary.nfails.nmismatches.inc(filename)
            return diffs, len(in_both), len(in_old), len(in_new)
        txt = StringIO()
        with redirect_stdout(txt):
            print("----- Missing Triples -----")
            if old_len:
                print_triples(in_old, fmt="turtle")
            print("----- Added Triples -----")
            if new_len:
                print_triples(in_new, fmt="turtle")
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
    if opts.verbose:
        print(f'Processing {actual_file_name}')
    actual_file = actual_file_name
    expected_file = expected_file_name if opts.outfile else \
                    actual_file_name.replace(opts.indir, opts.turtledir).replace(opts.infilesuffix, '.ttl')
    if not path.exists(expected_file):
        if opts.verbose:
            print(f'{os.path.join(os.path.dirname(__file__), expected_file)} not found')
        if ".profile.ttl" in expected_file:
            summary.nskips.ntargetmissing.nprofiles.inc(expected_file)
        elif "extension" in expected_file:
            summary.nskips.ntargetmissing.nextensions.inc(expected_file)
        else:
            summary.nskips.ntargetmissing.nmissing.inc(expected_file)
        return False
    report_file = actual_file_name.replace(opts.indir, opts.outdir).replace(opts.infilesuffix, '.txt') \
        if not opts.outfile else None
    with open(actual_file, 'r') as f:
        actual_str = f.read()
    if 'UNKNOWN' in actual_str:
        if opts.verbose:
            print(f'{actual_file_name} has unmapped elements')
        summary.nfails.nincompletes.inc(actual_file_name)
        unknowns.add(actual_file_name)
        return False
    with open(expected_file, 'r') as file:
        expected_str = file.read()

    # TODO: A monkey patch (kludge) to fix the issue in comparing when jsonld has ^^xsd:string and ^^xsd:anyURI
    actual_str = actual_str.replace("^^<http://www.w3.org/2001/XMLSchema#anyURI>", "")

    # It appears that the nquads parser and turtle parser handle decimals differently -- it looks like we've got to
    # do a double transform
    actual_graph = post_process(Graph().parse(data=actual_str, format='nquads'))
    expected_graph = to_graph(expected_str, 'turtle')

    # If we've generated metadata and it isn't in the expected graph, remove it
    if (None, FHIR_META, None) in actual_graph and (None, FHIR_META, None) not in expected_graph:
        details.nmissingsourcemetadata.inc(actual_file_name)
        remove_subgraph(FHIR_META, actual_graph)

    result, len_in_both, len_in_new, len_in_old = compare_rdf(actual_file_name, expected_graph, actual_graph, opts)

    if result:
        if report_file:
            with open(report_file, 'w') as file:
                file.write(result)
        else:
            if opts.verbose:
                print(result)
        summary.nfails.nmismatches.inc(actual_file_name)
        for s, p, o in actual_graph:
            if isinstance(o, URIRef) and 'contained' in str(p):
                details.ncontaiment.inc(actual_file_name)
                contains.add(actual_file_name)
                break
        return False
    summary.nsuccesses.inc(actual_file_name)
    return True


def input_filter(filename: str, dirpath: str, opts: Namespace) -> bool:
    # Code systems aren't currently converted to RDF
    if bool(opts.infile):
        # One file to be processed
        return True
    if filename.startswith('codesystem-'):
        if opts.verbose:
            print(f"{filename} skipped (codesystem)")
        summary.nskips.ncodesystems.inc(filename)
        return False
    if filename.startswith('valueset-') or '-valueset-' in filename:
        if opts.verbose:
            print(f"{filename} skipped (valueset)")
        summary.nskips.nvaluesets.inc(filename)
        return False
    if opts.maxtriples:
        tot_triples = sum(1 for _ in open(os.path.join(dirpath, filename)))
        if tot_triples > opts.maxtriples:
            if opts.verbose:
                print(f"{filename} skipped - {tot_triples} > max ({opts.maxtriples} ")
            summary.nskips.ntoolarge.inc(filename)
            return False
    return True


def addargs(parser: ArgumentParser) -> None:
    parser.add_argument("-td", "--turtledir", help="Turtle directory")
    parser.add_argument("-sdc", "--skipdetailedcompare", help="Do a fast non-detailed compare", action="store_true")
    parser.add_argument("-ifs", "--infilesuffix", help="Input file suffix (default: .nq)", default='.nq')
    parser.add_argument("-maxt", "--maxtriples", help="Number of triples to compare (default: unlimited)", type=int)
    parser.add_argument("-maxtc", "--maxcomparetriples", help="Detailed compare cutoff (default: unlimited)", type=int)
    parser.add_argument("-sta", "--skiptypearcs", help="Ignore missing type arcs in conversion", action="store_true")
    parser.add_argument("-dec", "--adjustdecimals", help="Fix decimal problems", action="store_true")
    parser.add_argument("-v", "--verbose", help="Emit more detailed output", action="store_true")


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

    nfiles, nsuccess = dlp.run(compare_files, file_filter_2=input_filter)
    print('-'*40)
    print('\n'.join(summary.summary()))
    print()
    print('-'*40)
    print('\n'.join(details.summary()))

    print('===== UNKNOWN w/o containment issues =====')
    uncontained_unknowns = unknowns.difference(contains)
    print('\n'.join(sorted(list(uncontained_unknowns))))

    print('===== Contains w/o UNKNOWN issues =====')
    unknown_contains = contains.difference(unknowns)
    print('\n'.join(sorted(list(unknown_contains))))

    print('==== Both =====')
    both = contains.intersection(unknowns)
    print('\n'.join(sorted(list(both))))

    return 0 if nfiles == nsuccess else 1




if __name__ == '__main__':
    main()
