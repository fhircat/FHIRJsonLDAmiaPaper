import os
import sys
from argparse import Namespace, ArgumentParser
from contextlib import redirect_stdout
from io import StringIO
from os import path
from typing import Union, Optional, List, Tuple, Callable, Set, Dict

import dirlistproc
from rdflib import Graph, RDF, URIRef, BNode, Literal, XSD, OWL
from rdflib.compare import similar, graph_diff

from logging_graph import LoggingGraph, FHIR, FHIR_META, SkGraph
from summary import Heading, Counter

KNOWN_ERRORS: Dict[str, str] = {
    'diagnosticreport-example-ins-policy': "Graph diff issues",
    "diagnosticreport-example-lri": "Graph diff issues"
}


# For internal debugging.  Should be an empty list for submission
INCLUDE_ONLY = []


def visit_graph(g: Graph, predicate: Callable[[Tuple], bool], replacement: Callable[[Tuple], Optional[Tuple]],
                reason: Optional[str] = '') -> bool:
    """ Visit a copy of g and, for every triple that meets the predicate, replace t with replacement.
        Return true if any replacements were made
    """
    replacements_were_made = False
    for t in list(g):
        if predicate(t):
            g.remove(t, reason) if isinstance(g, LoggingGraph) else g.remove(t)
            new_t = replacement(t)
            if new_t is not None:
                g.add(new_t, reason) if isinstance(g, LoggingGraph) else g.add(new_t)
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


def bnodify(subj, g: LoggingGraph) -> None:
    """ Convert subject subj from a URI into a blank node in graph g """
    bnode_subject = BNode()
    for t in list(g.triples((subj, None, None))):
        g.remove(t, "Converting a legitimate subject to a BNODE (1)")
        g.add((bnode_subject, t[1], t[2]), "Converting a legitimate subject to a BNODE (2)")
    for t in list(g.triples((None, None, subj))):
        g.remove(t, "Converting a legitimate subject to a BNODE (3)")
        if t[1] != FHIR.link:
            g.add((t[0], t[1], bnode_subject), "Converting a legitimate subject to a BNODE (4)")


def print_triples(g: Graph, fmt: str, pfx: str) -> None:
    """
    Print the contents of g into stdout
    :param g: graph to print
    :param fmt: format to print the graph in
    :param pfx: Prefix for BNODE shortening
    """
    # Prefixes appear to be useful
    # g_text = re.sub(r'@prefix.*\n', '', g.serialize(format="turtle").decode())
    ng = SkGraph(g, pfx)
    ng.bind('fhir', FHIR)
    g_text = ng.serialize(format=fmt).decode()
    print(g_text)


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


def remove_list_identifiers(g: Graph, filename: str) -> Graph:
    """ Remove list declarations from the graph.

    Note: The only case where this function may be useful is when we get badly lost in the context space and begin
    to emit everything in the default (@vocab) context.
    """
    for rs in g.subjects(RDF.type, RDF.List):
        g.remove((rs, RDF.type, RDF.List))
        details.nlisttypesremoved.inc(filename)
    return g


def fix_strings(g: Graph) -> Graph:
    """ Remove explicit string datatypes from the graph """
    visit_graph(g,
                lambda t: isinstance(t[2], Literal) and t[2].datatype and t[2].datatype == XSD.string,
                lambda t: (t[0], t[1], Literal(str(t[2]))))
    return g


def triples_for(subjs: List[str], g: Graph) -> str:
    rval = []
    for s in subjs:
        line = f"{s}:\n"
        for p, o in g.predicate_objects(URIRef(s)):
            line += f"\t{str(p)}  {str(o)}\n"
        rval.append(line)
    return '\n'.join(rval)


summary = Heading("files processed")
summary.nsuccesses = Counter("successful matches")

summary.nfails = Heading("match failures")
summary.nfails.nmismatches = Counter("content mismatch")
summary.nfails.toobigtocheck = Counter("too big to know for sure")

summary.nskips = Heading("files skipped")
summary.nskips.ncodesystems = Counter("code systems")
summary.nskips.nvaluesets = Counter("value sets")
summary.nskips.ntargetmissing = Heading("missing FHIR ttl files")
summary.nskips.ntargetmissing.nprofiles = Counter("missing profiles")
summary.nskips.ntargetmissing.nextensions = Counter("missing extensions")
summary.nskips.ntargetmissing.nmissing = Counter("missing for other reasons")
summary.nskips.ntoolarge = Counter("file exceeds max triples")

details = Heading("details")
details.ntoomanytriples = Counter("File has too many triples for detailed compare")
details.nmissingsourcemetadata = Counter("missing metadata in source")
details.ntypearcadjustments = Counter("adjusted type arcs")
details.nadjusteddecimals = Counter("adjusted decimals")
details.ncontaiment = Counter("expected files with incorrect contained mapping")
details.nincompletes = Counter("incomplete transforms (UNKNOWN in output)")
details.nremovedact = Counter("FHIR.link elements removed from actual")
details.nremovedexp = Counter("FHIR.link elements removed from expected")
details.adjustedsubjects = Counter("Non-BNode subjects removed from expected")
details.bnodifiedsubjects = Counter("Subjects that were turned into BNodes")
details.nlisttypesremoved = Counter("SERIOUS ISSUE: rdf:type rdf:List found in graph", print_progress=True)
details.knownmatches = Counter("Passed quick graph compare")

contains: Set[str] = set()


class Diffs:

    def __init__(self, expected_graph: Graph, actual_graph: Graph) -> None:
        self.old_len, self.new_len = 0, 0
        if similar(expected_graph, actual_graph):
            self.expected_graph = expected_graph
            self.actual_graph = actual_graph
            self.in_both = self.expected_graph
            self.in_old = Graph()
            self.in_new = Graph()
            self.passed = True
        else:
            self.expected_graph = LoggingGraph(expected_graph)
            self.actual_graph = LoggingGraph(actual_graph)
            self.in_both: Graph = Graph()
            self.in_old = expected_graph
            self.in_new = actual_graph
            self.passed = False
        self._upd_lens()

    def _upd_lens(self):
        self.both_len, self.old_len, self.new_len = len(self.in_both), len(self.in_old), len(self.in_new)

    def recheck(self) -> bool:
        """ Recompute the differences between the graphs

        :returns: True if changes were detected
        """
        if not self.passed and self.changed:
            self.expected_graph.changed = False
            self.actual_graph.changed = False
            if not self.known_match:
                cur_lens = (self.both_len, self.old_len, self.new_len)
                self.in_both, self.in_old, self.in_new = graph_diff(self.expected_graph, self.actual_graph)
                self._upd_lens()
                self.passed = not self.diffs_exist
                return cur_lens != (self.both_len, self.old_len, self.new_len)
        return False

    @property
    def changed(self) -> bool:
        return self.expected_graph.changed or self.actual_graph.changed

    @property
    def diffs_exist(self) -> bool:
        return not self.passed and (bool(self.old_len) or bool(self.new_len))

    @property
    def known_match(self) -> bool:
        """ Return True if graphs DO match, false if we don't actually know """
        if similar(self.expected_graph, self.actual_graph):
            self.in_both, self.old_len, self.new_len = self.new_len, 0, 0
            self.passed = True
            return True
        return False

    @property
    def sure_match(self) -> bool:
        self.recheck()
        return not(self.old_len + self.new_len)

    def match_results(self, msg: Optional[str] = None) -> Tuple[Optional[str], int, int, int]:
        assert msg or self.sure_match, "Program error - returning success while not really successful"
        return msg, self.both_len, self.old_len, self.new_len

    def _subj_differences(self) -> Tuple[List[str], List[str]]:
        # Find all the non-bnode subjects that are in one graph but not the other
        self.recheck()
        expected_subjs = set([str(s) for s in self.in_old.subjects() if isinstance(s, URIRef)])
        actual_subjs = set([str(s) for s in self.in_new.subjects() if isinstance(s, URIRef)])

        return sorted(list(expected_subjs.difference(actual_subjs))), \
               sorted(list(actual_subjs.difference(expected_subjs)))

    def subj_diff(self, tweakcontained: bool) -> Optional[str]:
        """
        Adjust for additional subjects that appear in the JSON-LD graphs but not the current FHIR graphs

        :param tweakcontained: True means remove unmapped stuff from the new graph
        :return: Error message if subjects don't agree.  Bool is true if changes were made
        """

        # Find all the non-bnode subjects that are in one graph but not the other
        in_expected_only, in_actual_only = self._subj_differences()

        # If we have URI's that appear as subjects of RDF type arcs in the actual but not the expected,
        if tweakcontained and in_actual_only:
            for a in list(in_actual_only):
                auri = URIRef(a)

                # We need to determine which case we've got:
                #  1) The triple(s) headed by auri do not appear at all in the expected graph
                #  2) The triples appear, but are headed by BNodes in the expected graph.
                if (auri, RDF.type, None) in self.actual_graph:
                    in_actual_only.remove(a)
                    for exp_type in list(self.actual_graph.objects(auri, RDF.type)):
                        if (None, RDF.type, exp_type) in self.expected_graph:
                            if (None, FHIR['DomainResource.contained'], auri) in self.actual_graph:
                                bnodify(auri, self.actual_graph)
                            else:
                                self.actual_graph.remove((auri, RDF.type, None))
                        else:
                            self.actual_graph.remove((auri, RDF.type, exp_type), "Type arc not declared in expected")
                            # Now determine whether we also have to pull a FHIR:link
                            link_t = (None, FHIR.link, auri)
                            if link_t not in self.expected_graph and link_t in self.actual_graph:
                                self.actual_graph.remove(link_t, "fhir:link not declared in expected")

        if in_expected_only and not in_actual_only:
            # The problem we are attempting to address is an error in the current FHIR RDF generator, where the
            # DocumentReference.subject does not pay attention to the FullURL and instead generates a generic FHIR
            # identifier. The JSON-LD (Actual) file is correct - all links point to the fulLURL:
            #
            #     <http://localhost:9556/svc/fhir/Patient/a2> a fhir:Patient ;
            #           fhir:Patient.birthDate [ fhir:value "1956-05-27"^^xsd:date ] ;
            #           fhir:Patient.identifier [ fhir:Identifier.use [ fhir:value "usual" ] ;
            #           ...
            #           fhir:DocumentReference.subject [ fhir:Reference.reference [ fhir:value "Patient/a2" ] ;
            #               fhir:link <http://localhost:9556/svc/fhir/Patient/a2> ] ;
            #
            #  The FHIR RDF has omitted an extra type arc for the wrong URL and embedded a link to it in the
            #  document reference:
            #   <http://hl7.org/fhir/Patient/a2> a fhir:Patient .
            #       fhir:DocumentReference.subject [
            #           fhir:link <http://hl7.org/fhir/Patient/a2>;
            #           fhir:Reference.reference [ fhir:value "Patient/a2" ]
            #       ];
            #
            # Our challenge in this situation is a) remove the extra type arc (easy) and b) find and correct the
            # fhir:link itself... not so easy.  The best we can do will work most of the time -- locate the
            # fhir:Reference.reference.[].fhir:value in the expected, find the equivalent in the actual and then
            # replace the link.  Ugh.
            removed = set()
            for e in in_expected_only:
                bad_subject = URIRef(e)
                if len(list(self.expected_graph.triples((bad_subject, None, None)))) == 1:
                    if len(list(self.expected_graph.triples((bad_subject, RDF.type, None)))) == 1:
                        self.expected_graph.remove((bad_subject, RDF.type, None), "Remove subjects that should have been fullURIs")
                        for exp_link_subj in self.expected_graph.subjects(FHIR.link, bad_subject):
                            for exp_ref in self.expected_graph.objects(exp_link_subj, FHIR['Reference.reference']):
                                for exp_ref_value in self.expected_graph.objects(exp_ref, FHIR.value):
                                    # exp_ref_value is the reference value associated with with the wrong link
                                    for act_ref in self.actual_graph.subjects(FHIR.value, exp_ref_value):
                                        for act_link_subj in self.actual_graph.subjects(FHIR['Reference.reference'], act_ref):
                                            for good_subject in self.actual_graph.objects(act_link_subj, FHIR.link):
                                                self.expected_graph.add((exp_link_subj, FHIR.link, good_subject), "Changing reference to FullURI")
                                                self.expected_graph.remove((exp_link_subj, FHIR.link, bad_subject), "Changing reference to fullURI")
                                                removed.add(e)

            if len(set(in_expected_only) - removed) == 0:
                return None

        self.recheck()
        if self.known_match:
            return None
        in_expected_only, in_actual_only = self._subj_differences()

        if in_actual_only or in_expected_only:
            if in_expected_only:
                exp_str = "------ Expected Subjects -----\n"
                exp_str += triples_for(in_expected_only, self.expected_graph)
            else:
                exp_str = ''
            act_str = "----- Added Subjects -----\n"
            if in_actual_only:
                act_str += triples_for(in_actual_only, self.actual_graph)
            return exp_str + act_str

        return None


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

    # Step 1: remove any ^^"xsd:string" entries
    # Step 2: remove  rdf:type rdf:List entries (This shouldn't ever occur in real life)
    diffs = Diffs(remove_list_identifiers(fix_strings(to_graph(expected, "turtle")), filename),
                  remove_list_identifiers(fix_strings(to_graph(actual, "turtle")), filename))

    # Shortcut -- if the graphs match through the easy route, say we're good and move on
    if diffs.known_match:
        return diffs.match_results()

    if opts.skipdetailedcompare or (opts.maxcomparetriples and diffs.old_len > opts.maxcomparetriples):
        summary.nfails.toobigtocheck.inc(filename)
        return f"Graph not analyzed: too many triples: {diffs.old_len} <--> {diffs.new_len}", 0, diffs.old_len, diffs.new_len

    if diffs.sure_match:
        return diffs.match_results()

    # Remove the RDF type arcs -- are always in the form [] RDF.type concept-uri
    if opts.skiptypearcs:
        for cc, o in set(diffs.actual_graph.subject_objects(RDF.type)):
            if 'snomed.info/id/' not in str(o) and 'http://loinc.org' not in str(o) and\
                    (cc, FHIR['Coding.system'], None) in diffs.actual_graph:
                diffs.actual_graph.remove((cc, RDF.type, o), "Concept URI not mapped in expected")

    if diffs.changed:
        details.ntypearcadjustments.inc(filename)
    if diffs.sure_match:
        return diffs.match_results()

    if diffs.new_len:
        if opts.adjustdecimals:
            # It turns out that decimal problems aren't just in JSON -- different rdflib parsers deal with them differently
            # It looks like the only wan to fix this is to twiddle ALL decimals, both old and new, when there is an issue
            for s, p, o in diffs.in_new:
                if isinstance(o, Literal) and o.datatype == XSD.decimal:
                    visit_graph(diffs.expected_graph,
                                lambda t1: isinstance(t1[2], Literal) and t1[2].datatype == XSD.decimal,
                                lambda t2: (t2[0], t2[1], Literal(float(str(t2[2])), datatype=XSD.decimal)),
                                "Normalizing decimals")
                    visit_graph(diffs.actual_graph,
                                lambda t3: isinstance(t3[2], Literal) and t3[2].datatype == XSD.decimal,
                                lambda t3: (t3[0], t3[1], Literal(float(str(t3[2])), datatype=XSD.decimal)),
                                "Normalizing decimals")
                    break

    if diffs.changed:
        details.nadjusteddecimals.inc(filename)
    if diffs.sure_match:
        return diffs.match_results()

    if diffs.new_len:
        # The new RDF has considerably more links than the old.  The only way to get a hand on this is to assume that
        # additional FHIR:links are valid, so we will remove any that appear in the new data
        # NOTE: The triples returned by graph_diff have different BNodes than those in the original
        for s, o in diffs.in_new.subject_objects(FHIR.link):
            assert isinstance(o, URIRef), "We shouldn't be building ANY complex links"

            # If old and new subjects are both BNodes, we assume that this is a BNode comparison issue
            expected_subjects = list(diffs.expected_graph.subjects(FHIR.link, o))
            if isinstance(s, BNode) and expected_subjects and all(isinstance(e, BNode) for e in expected_subjects):
                continue

            # We either have:
            #    1) actual link exists and there is no link in expected
            #    2) actual is BNode and some expected are URI
            #    3) actual is a URI and expected is a BNODE
            if not expected_subjects:
                diffs.actual_graph.remove((s, FHIR.link, o), "Embedded BNode instead of link")
                details.nremovedact.inc(filename)
            elif isinstance(s, BNode):
                pass                    # Real difference -- JSON-LD creates BNode, original creates URIRef
            else:
                # This is a known difference between R4 and JSON conversions -- the JSON-LD conversions create
                # Typed subjects wherever possible, where the existing R4 often omits it.  To make these work, we
                # make a note of what we have done and change the subject to a BNode
                # bnodify(s, diffs.actual_graph)
                pass

            # for se in diffs.expected_graph.subjects(FHIR.link, o):
            #     diffs.expected_graph.remove((se, FHIR.link, o))
            #     details.nremovedexp.inc(filename)
            for sa in diffs.actual_graph.subjects(FHIR.link, o):
                # diffs.actual_graph.remove((sa, FHIR.link, o), "Link that was not generated in original RDF")
                # details.nremovedact.inc(filename)
                pass

    if diffs.sure_match:
        details.knownmatches.inc(filename)
        return diffs.match_results()

    if diffs.new_len and opts.maptobnodes:
        # If we have more non-bnodes in the expected than in the actual, we need to
        actual_subjects = set([s for p, s in diffs.in_new.predicate_objects()
                               if isinstance(s, URIRef) and p != RDF.type])
        expected_subjects = set([s for p, s in diffs.in_old.predicate_objects()
                                 if isinstance(s, URIRef) and p != RDF.type])
        extra_subjects = actual_subjects - expected_subjects
        for s in extra_subjects:
            # bnodify(s, diffs.actual_graph)
            pass

    if diffs.changed:
        details.adjustedsubjects.inc(filename)
    if diffs.sure_match:
        return diffs.match_results()

    # There are multiple situations where the correct RDF should be of the form:
    #    ns1:pred   [ ns1:link <http://hl7.org/fhir/Organization/f001> ;
    #                 ns1:value "Organization/f001" ] ;
    #
    # But the current FHIR rdf does not emit these.  If we find this pattern in the actual RDF, remove the links
    # from the expected RDF if there is no match
    for t in diffs.actual_graph.triples((None, FHIR.link, None)):
        if (None, t[1], t[2]) not in diffs.expected_graph:
            # diffs.actual_graph.remove(t, "Remove link that wasn't realized in expected")
            pass

    if diffs.changed:
        details.ncontaiment.inc(filename)
    if diffs.sure_match:
        return diffs.match_results()

    # Start by checking the subjects
    subject_differences = diffs.subj_diff(opts.tweakcontained)

    if subject_differences:
        summary.nfails.nmismatches.inc(filename)
        return diffs.match_results(subject_differences)

    if diffs.sure_match:
        return diffs.match_results()

    txt = StringIO()

    with redirect_stdout(txt):
        print(f"----- Missing Triples n={diffs.old_len} -----")
        if diffs.old_len:
            print_triples(diffs.in_old, fmt="turtle", pfx='e')
        print(f"----- Added Triples  n={diffs.new_len} -----")
        if diffs.new_len:
            print_triples(diffs.in_new, fmt="turtle", pfx='a')
        expected_graph_tweaks = diffs.expected_graph.log()
        if expected_graph_tweaks:
            print("----- Changes to Expected Graph -----")
            print(expected_graph_tweaks)
        actual_graph_tweaks = diffs.actual_graph.log()
        if actual_graph_tweaks:
            print("----- Changes to Actual Graph -----")
            print(actual_graph_tweaks)

    return diffs.match_results(txt.getvalue())


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
        details.nincompletes.inc(actual_file_name)
        result = "UNKNOWNS in output\n"
        actual_graph = None
    else:
        with open(expected_file, 'r') as file:
            expected_str = file.read()

        # TODO: A monkey patch (kludge) to fix the issue in comparing when jsonld has ^^xsd:string and ^^xsd:anyURI
        actual_str = actual_str.replace("^^<http://www.w3.org/2001/XMLSchema#anyURI>", "")

        # TODO: update the following when we start producing turtle
        actual_graph = Graph().parse(data=actual_str, format='nquads')
        actual_graph.bind('fhir', FHIR)
        actual_graph.bind('owl', OWL)
        actual_graph.serialize(actual_file.replace(opts.infilesuffix, '.ttl'), format="turtle")

        expected_graph = to_graph(expected_str, 'turtle')

        # If we've generated metadata and it isn't in the expected graph, remove it
        if (None, FHIR_META, None) in actual_graph and (None, FHIR_META, None) not in expected_graph:
            details.nmissingsourcemetadata.inc(actual_file_name)
        # Even WHEN FHIR metadata is present, it is incomplete
        remove_subgraph(FHIR_META, actual_graph)
        remove_subgraph(FHIR_META, expected_graph)

        result, len_in_both, len_in_new, len_in_old = compare_rdf(actual_file_name, expected_graph, actual_graph, opts)

    if result:
        if report_file:
            with open(report_file, 'w') as file:
                file.write(result)
        else:
            print(result)
        summary.nfails.nmismatches.inc(actual_file_name)
        if actual_graph:
            for s, p, o in actual_graph:
                if isinstance(o, URIRef) and 'contained' in str(p):
                    details.ncontaiment.inc(actual_file_name)
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
        summary.nskips.ncodesystems.inc(filename)
        return False
    if filename.startswith('valueset-') or '-valueset-' in filename:
        summary.nskips.nvaluesets.inc(filename)
        return False
    if any(filename.startswith(k) for k in KNOWN_ERRORS.keys()):
        for k, reason in KNOWN_ERRORS.items():
            if filename.startswith(k):
                print(f"Skipping {filename} because {KNOWN_ERRORS[k]}")
                return False
        assert False, "Big fat programming error"
    if INCLUDE_ONLY and not any(filename.startswith(e) for e in INCLUDE_ONLY):
        return False
    if opts.maxtriples:
        tot_triples = sum(1 for _ in open(os.path.join(dirpath, filename)))
        if tot_triples > opts.maxtriples:
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
    parser.add_argument("-v", "--verbose", help="Print progress", action="store_true")
    parser.add_argument("-tc", "--tweakcontained", help="Represent contained graphs as BNodes to match R4 error",
                        action="store_true")
    parser.add_argument('-mb', "--maptobnodes", help="Map URI's to BNodes to match FHIR ttl", action="store_true")


def main(argv: Optional[Union[str, List[str]]] = None) -> object:
    """
    Apply R4 edits to FHIR JSON files

    :param argv: Argument list.  Can be unparsed string, a list of strings or nothing. If nothing, we use sys.argv
    :return: 0 if all RDF files that had valid FHIR in them were successful, 1 otherwise
    """
    def gen_dlp(args: List[str]) -> dirlistproc.DirectoryListProcessor:
        return dirlistproc.DirectoryListProcessor(args, "Add FHIR R4 edits to JSON file", '.nq', '.json',
                                                  addargs=addargs)

    if INCLUDE_ONLY:
        print("=====> WARNING: INCLUDE_ONLY is set, only processing a subset")
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

    return 0 if nfiles == nsuccess else 1


if __name__ == '__main__':
    main()
