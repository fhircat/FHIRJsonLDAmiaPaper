from typing import Optional, Dict, Tuple

from rdflib import RDF, XSD, OWL, Graph, Namespace
from rdflib.term import Node, BNode, URIRef

FHIR = Namespace('http://hl7.org/fhir/')
FHIR_META = FHIR['Resource.meta']

FHIR_STR = str(FHIR)
RDF_STR = str(RDF)
XSD_STR = str(XSD)
OWL_STR = str(OWL)


BNODE_NS = Namespace('http://bnodes.r.us/')


class SkGraph(Graph):

    def __init__(self, g: Graph, bn_prefix: str):
        self._bn_prefix = bn_prefix
        self._bn_number = 0
        self._bn_map: Dict[BNode, URIRef] = dict()
        super().__init__()
        self.bind(None, BNODE_NS)
        # Sort the input as best we can possibly can
        # First three entries are used for sort, the final t is used for adding
        for _, _, _, t in sorted([(t[0] if not isinstance(t[0], BNode) else 'z',
                                   t[1],
                                   t[2] if not isinstance(t[2], BNode) else 'z', t) for t in g]):
            self.add(t)

    def add(self, t: Tuple):
        super().add((self._map(t[0]), self._map(t[1]), self._map(t[2])))

    def _map(self, n: Node) -> Node:
        if isinstance(n, BNode):
            if n not in self._bn_map:
                self._bn_number += 1
                self._bn_map[n] = BNODE_NS[f"_{self._bn_prefix}{self._bn_number}"]
            return self._bn_map[n]
        return n


class BNodeMgr:
    def __init__(self):
        self._bnmap = dict()
        self._idx = 0

    def id_for(self, e: Node) -> str:
        if not isinstance(e, BNode):
            str_e = str(e)
            if str_e.startswith(FHIR_STR):
                str_e = str_e.replace(FHIR_STR, 'fhir:')
            elif str_e.startswith(RDF_STR):
                str_e = str_e.replace(RDF_STR, 'rdf:')
            elif str_e.startswith(XSD_STR):
                str_e = str_e.replace(XSD_STR, 'xsd:')
            elif str_e.startswith(OWL_STR):
                str_e = str_e.replace(OWL_STR, 'owl:')
            return str_e

        if e not in self._bnmap:
            self._idx += 1
            self._bnmap[e] = f"_:{self._idx}"
        return self._bnmap[e]


class LoggingGraph(Graph):
    """ Graph object that logs adds and removes """
    def __init__(self, g: Graph):
        self._additions = list()
        self._deletions = list()
        self.changed = True                # Can be used to test for changes since last check
        super().__init__()
        for e in g:
            super().add(e)

    def add(self, t, reason: Optional[str] = ''):
        self._additions.append((t, reason))
        self.changed = True
        super().add(t)

    def remove(self, t, reason: Optional[str] = ''):
        for real_triple in self.triples(t):
            self.changed = True
            self._deletions.append((real_triple, reason))
            super().remove(real_triple)

    def log(self) -> str:
        rval = list()
        bnode_map = BNodeMgr()
        for a, r in sorted(self._additions):
            rval.append(f"ADD: {r} {bnode_map.id_for(a[0])} {bnode_map.id_for(a[1])} {bnode_map.id_for(a[2])}")
        for d, r in sorted(self._deletions):
            rval.append(f"REMOVE: {r} {bnode_map.id_for(d[0])} {bnode_map.id_for(d[1])} {bnode_map.id_for(d[2])}")
        return '\n'.join(rval)
