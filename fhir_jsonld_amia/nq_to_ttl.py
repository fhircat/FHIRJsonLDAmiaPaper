import argparse

from rdflib import Graph


def main():
    parser = argparse.ArgumentParser(description="Convert nq to ttl")
    parser.add_argument("infile", help="Input nq file")
    parser.add_argument("prefixes", help="Additional RDF prefixes to bind", nargs='?')
    opts = parser.parse_args()
    g = Graph()
    if opts.prefixes:
        g.load(opts.prefixes, format="turtle")
    g.parse(opts.infile, format="nquads")
    turtle = g.serialize(format="turtle").decode()
    print(turtle)


if __name__ == '__main__':
    main()
