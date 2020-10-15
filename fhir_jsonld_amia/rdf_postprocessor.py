import re

from rdflib import Graph, Literal, XSD, RDF

"""
Post processing functions.  The JSON-LD pre-processor is model independent -- the transformations, while having certain
intimate knowledge of the FHIR resource structure, do not draw on individual schema definitions.

The post processor handles context specific information that has been injected in the JSON-LD transformation process
and uses it to tweak context sensitive fields
"""
# The following Regular expressions come from the FHIR datatypes model
gYear_re = re.compile(r'([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)$')
gYearMonth_re = re.compile(r'([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2]))$')
date_re = re.compile(r'([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|3[0-1]))?)?$')


def test_re():
    assert gYear_re.match('2018')
    assert gYear_re.match('0001')
    assert not gYear_re.match('2018-12')


def post_process(g: Graph) -> Graph:
    for s, p, o in list(g):
        # Massage date time tags
        if isinstance(o, Literal) and o.datatype == XSD.dateTime:
            dt = None
            date_str = str(o)
            if gYear_re.match(date_str):
                dt = XSD.gYear
            elif gYearMonth_re.match(date_str):
                dt = XSD.gYearMonth
            elif date_re.match(date_str):
                dt = XSD.date
            if dt:
                g.remove((s, p, o))
                g.add((s, p, Literal(str(o), datatype=dt)))
    return g


if __name__ == '__main__':
    g = Graph()
    g.add( (RDF.subject, RDF.predicate, Literal('2004', datatype=XSD.dateTime)))
    for t in post_process(g):
        print(str(t))
