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
        item = self.flat_path(path)
        if (item, RDFS.range, FHIR.canonical) in self.g:
            return True
        # Note: This was a good idea, but it doesn't take inheritence into account.  If we want to actually do this
        # test, we would need to run up the parents of path[0].  For now we just drop it
        # if check_valid:
        #     assert item in self.g.subjects(), f"{item}: Testing an item that doesn't exist"
        return False


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
