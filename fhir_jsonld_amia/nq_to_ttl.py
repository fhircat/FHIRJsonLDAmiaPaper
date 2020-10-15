import argparse

from rdflib import Graph


def main():
    parser = argparse.ArgumentParser(description="Convert nq to ttl")
    parser.add_argument("infile", help="Input nq file")
    opts = parser.parse_args()
    g = Graph()
    g.parse(opts.infile, format="nquads")
    turtle = g.serialize(format="turtle").decode()
    print(turtle)


if __name__ == '__main__':
    main()
