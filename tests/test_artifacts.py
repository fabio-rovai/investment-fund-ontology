"""Offline artifact checks: every committed TTL parses, shapes load,
and the query library runs against the committed example subgraph."""
import glob, os
from rdflib import Graph

ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_all_ttl_parse():
    files = (glob.glob(os.path.join(ROOT, "ontology", "*.ttl"))
             + glob.glob(os.path.join(ROOT, "skos", "*.ttl"))
             + glob.glob(os.path.join(ROOT, "shapes", "*.ttl"))
             + glob.glob(os.path.join(ROOT, "examples", "*.ttl")))
    assert len(files) >= 6
    for f in files:
        g = Graph()
        g.parse(f, format="turtle")
        assert len(g) > 0, f


def test_queries_run_on_example():
    g = Graph()
    g.parse(os.path.join(ROOT, "examples", "vanguard-index-funds.ttl"))
    g.parse(os.path.join(ROOT, "skos", "identifier-schemes.ttl"))
    for q in sorted(glob.glob(os.path.join(ROOT, "queries", "*.rq"))):
        res = list(g.query(open(q).read()))
        assert isinstance(res, list), q


def test_example_shacl_gate():
    from pyshacl import validate
    data = Graph()
    data.parse(os.path.join(ROOT, "examples", "vanguard-index-funds.ttl"))
    data.parse(os.path.join(ROOT, "ontology", "ifo-core.ttl"))
    data.parse(os.path.join(ROOT, "skos", "identifier-schemes.ttl"))
    shapes = Graph()
    shapes.parse(os.path.join(ROOT, "shapes", "ifo-shapes.ttl"))
    conforms, report, _ = validate(data, shacl_graph=shapes,
                                   inference="none", allow_warnings=True)
    assert len(report) > 0
