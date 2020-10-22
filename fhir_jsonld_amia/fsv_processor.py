import os
import pickle
from typing import List, Optional

from rdflib import Graph, Namespace, URIRef, RDFS

FHIR = Namespace("http://hl7.org/fhir/")


class FSVProcessor:
    def __init__(self, fsv_file_path: str) -> None:
        self.g = Graph()
        # Try to speed up the FSV load a bit
        fsv_pickle_path = fsv_file_path.replace('.ttl', '.pickle')
        if os.path.exists(fsv_pickle_path):
            with open(fsv_pickle_path, 'rb') as pf:
                self.g = pickle.load(pf)
        else:
            self.g.load(fsv_file_path, format="turtle")
            with open(fsv_pickle_path, 'wb') as pf:
                pickle.dump(self.g, pf)

    @staticmethod
    def flat_path(path: List[str]) -> URIRef:
        return FHIR['.'.join(path)]

    def _traverse_path(self, path:List[str], target_types: List[URIRef]) -> Optional[URIRef]:
        """
        Return the matching URI in target_types for path else None

        :param path: List of JSON strings from root
        :param target_types: List of types to test
        :return: True if range of path is target_type type
        """
        # Work backwards from the full path, following ranges where necessary
        path_base = self.flat_path(path)
        if (path_base, None, None) in self.g:
            path_range = self.g.value(path_base, RDFS.range)
            return path_range if path_range in target_types else None

        path_range = None

        # Full path isn't there, back up until we find a range
        for idx in range(len(path)-1, 1, -1):
            path_base = self.flat_path(path[:idx])
            if (path_base, None, None) in self.g:
                path_range = self.g.value(path_base, RDFS.range)
                break
        if not path_range:
            return None

        # Process the new range
        new_path = [str(path_range)[len(str(FHIR)):]] + path[idx:]
        return self._traverse_path(new_path, target_types)

    def is_canonical(self, path: List[str], check_valid: bool=True) -> bool:
        """
        Determine whether the supplied path references a canonical variable

        :param path: List of JSON strings from root
        :param check_valid: True means make sure the path exists
        :return: True if range of path is canonical type
        """
        return self._traverse_path(path, [FHIR.canonical]) is not None

    def is_date(self, path: List[str]) -> Optional[URIRef]:
        return self._traverse_path(path, [FHIR.date, FHIR.time, FHIR.dateTime])


if __name__ == '__main__':
    fsv = FSVProcessor('../data/fhir-r4/fhir.ttl')
    assert fsv.is_canonical(['CapabilityStatement', 'rest', 'searchParam', 'definition'])
    assert not fsv.is_canonical(['CapabilityStatement', 'rest'])
    assert fsv.is_date(['DocumentReference', 'context', 'period', 'start'])
