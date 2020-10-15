from typing import List

from rdflib import Graph, Namespace, URIRef, RDFS

FHIR = Namespace("http://hl7.org/fhir/")


class FSVProcessor:
    def __init__(self, fsv_file_path: str) -> None:
        self.g = Graph()
        self.g.load(fsv_file_path, format="turtle")

    @staticmethod
    def flat_path(path: List[str]) -> URIRef:
        return FHIR['.'.join(path)]

    def is_canonical(self, path: List[str], check_valid: bool=True) -> bool:
        """
        Determine whether the supplied path references a canonical variable

        :param path: List of JSON strings from root
        :param check_valid: True means make sure the path exists
        :return: True if range of path is canonical type
        """
        # Work backwards from the full path, following ranges where necessary
        path_base = self.flat_path(path)
        if (path_base, None, None) in self.g:
            path_range = self.g.value(path_base, RDFS.range)
            return path_range is not None and path_range == FHIR.canonical

        path_range = None

        # Full path isn't there, back up until we find a range
        for idx in range(len(path)-1, 1, -1):
            path_base = self.flat_path(path[:idx])
            if (path_base, None, None) in self.g:
                path_range = self.g.value(path_base, RDFS.range)
                break
        if not path_range:
            return False

        # Process the new range
        new_path = [str(path_range)[len(str(FHIR)):]] + path[idx:]
        return self.is_canonical(new_path)



if __name__ == '__main__':
    fsv = FSVProcessor('../data/fhir-r4/fhir.ttl')
    assert fsv.is_canonical(['CapabilityStatement', 'rest', 'searchParam', 'definition'])
    assert not fsv.is_canonical(['CapabilityStatement', 'rest'])
    # check_worked = False
    # try:
    #     fsv.is_canonical(['foo'])
    # except AssertionError as e:
    #     check_worked = True
    # assert check_worked, "Check valid isn't working"
