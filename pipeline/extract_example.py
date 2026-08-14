"""Extract a committed example subgraph: one fund family, full depth.

Picks the Vanguard Index Funds registrant (the largest index fund
family in the register) and emits every triple reachable from it:
registrant, funds, share classes, listings, venues, and all reified
identifier assertions, so the SPARQL query library works out of the
box without downloading anything.
"""

from __future__ import annotations

import os

from rdflib import Graph, Namespace, RDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "data", "build")
OUT = os.path.join(ROOT, "examples")
os.makedirs(OUT, exist_ok=True)

IFO = Namespace("https://gov.tesseract.academy/def/fund#")


def main() -> None:
    g = Graph()
    g.parse(os.path.join(BUILD, "fund_graph.ttl"), format="turtle")

    target = None
    for reg in g.subjects(RDF.type, IFO.FundRegistrant):
        name = str(g.value(reg, IFO.legalName) or "")
        if name.strip().lower() == "vanguard index funds":
            target = reg
            break
    if target is None:
        raise SystemExit("Vanguard Index Funds not found in graph")

    keep = {target}
    for f in g.objects(target, IFO.hasFund):
        keep.add(f)
        for c in g.objects(f, IFO.hasShareClass):
            keep.add(c)
            for l in g.objects(c, IFO.hasListing):
                keep.add(l)
                for v in g.objects(l, IFO.listedOn):
                    keep.add(v)

    out = Graph()
    out.bind("ifo", IFO)
    out.bind("ifosch", "https://gov.tesseract.academy/def/fund/scheme#")
    grown = True
    while grown:
        grown = False
        for s, p, o in g:
            if s in keep and (s, p, o) not in out:
                out.add((s, p, o))
                if p in (IFO.identifiedBy,) and o not in keep:
                    keep.add(o)
                    grown = True
    # identifier nodes' outbound triples
    for s, p, o in g:
        if s in keep:
            out.add((s, p, o))

    path = os.path.join(OUT, "vanguard-index-funds.ttl")
    out.serialize(path, format="turtle")
    print(f"{path}: {len(out):,} triples, {len(keep):,} nodes")


if __name__ == "__main__":
    main()
