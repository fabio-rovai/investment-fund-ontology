"""Export the open fund identifier map.

The deliverable the enclosure says you have to pay for: a class-level
identifier table for US registered funds assembled entirely from open
sources (SEC registers and filings, GLEIF, OpenFIGI). One row per
(fund, ISIN) with the share-class resolution where open data earns it.

Columns:
  series_id, fund_name, lei, isin, isin_source (GLEIF | SEC-NPORT),
  figi, share_class_figi, figi_ticker, class_id, class_name,
  resolution (figi-ticker-join | unique-pairing | unresolved)

Everything in this file is redistributable: LEIs and GLEIF-published
ISINs (GLEIF open publication), ISINs attested in public SEC filings,
FIGIs (OMG open standard), and SEC register identifiers (public
domain). No standalone CUSIP, SEDOL, or RIC appears.

Output: open-map/fund_identifier_map.csv + open-map/README.md counts.
"""

from __future__ import annotations

import csv
import json
import os

from rdflib import Graph, Namespace, RDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "data", "build")
OUT = os.path.join(ROOT, "open-map")
os.makedirs(OUT, exist_ok=True)

IFO = Namespace("https://gov.tesseract.academy/def/fund#")


def main() -> None:
    g = Graph()
    g.parse(os.path.join(BUILD, "fund_graph.ttl"), format="turtle")
    for extra in ("figi_graph.ttl", "nport_graph.ttl"):
        p = os.path.join(BUILD, extra)
        if os.path.exists(p):
            g.parse(p, format="turtle")

    figi_map = {}
    cache = os.path.join(BUILD, "figi_map.jsonl")
    if os.path.exists(cache):
        with open(cache) as fh:
            for line in fh:
                rec = json.loads(line)
                figi_map[rec["isin"]] = rec

    def value(node):
        return str(g.value(node, IFO.identifierValue))

    def name(node):
        v = g.value(node, IFO.legalName)
        return str(v) if v else ""

    def sid_of(fund):
        for n in g.objects(fund, IFO.identifiedBy):
            if (n, RDF.type, IFO.SECSeriesId) in g:
                return value(n)
        return ""

    def cid_of(cls):
        for n in g.objects(cls, IFO.identifiedBy):
            if (n, RDF.type, IFO.SECClassId) in g:
                return value(n)
        return ""

    def lei_of(fund):
        for n in g.objects(fund, IFO.identifiedBy):
            if (n, RDF.type, IFO.LEI) in g:
                return value(n)
        return ""

    src_label = {
        "GLEIF-ISIN-LEI": "GLEIF",
        "SEC-NPORT": "SEC-NPORT",
    }

    rows = []
    for isin_node in g.subjects(RDF.type, IFO.ISIN):
        isin = value(isin_node)
        sources = sorted({str(s).rsplit("#", 1)[-1]
                          for s in g.objects(isin_node, IFO.sourceSystem)})
        source = "|".join(src_label.get(s, s) for s in sources)
        for fund in g.objects(isin_node, IFO.hasIssuedSecurityIdentifier):
            if (fund, RDF.type, IFO.Fund) not in g:
                continue
            resolved_cls = None
            method = "unresolved"
            for target in g.objects(isin_node, IFO.identifies):
                if (target, RDF.type, IFO.ShareClass) in g:
                    resolved_cls = target
                    m = g.value(isin_node, IFO.resolutionMethod)
                    method = str(m) if m else "unique-pairing"
            rec = figi_map.get(isin, {})
            rows.append({
                "series_id": sid_of(fund),
                "fund_name": name(fund),
                "lei": lei_of(fund),
                "isin": isin,
                "isin_source": source,
                "figi": rec.get("figi") or "",
                "share_class_figi": rec.get("shareClassFIGI") or "",
                "figi_ticker": rec.get("ticker") or "",
                "class_id": cid_of(resolved_cls) if resolved_cls else "",
                "class_name": name(resolved_cls) if resolved_cls else "",
                "resolution": method,
            })

    rows.sort(key=lambda r: (r["series_id"], r["isin"]))
    path = os.path.join(OUT, "fund_identifier_map.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n_res = sum(1 for r in rows if r["resolution"] != "unresolved")
    counts = {
        "rows": len(rows),
        "resolved_to_class": n_res,
        "resolution_rate": round(n_res / len(rows), 4),
        "with_figi": sum(1 for r in rows if r["figi"]),
        "from_nport_only": sum(1 for r in rows
                               if r["isin_source"] == "SEC-NPORT"),
    }
    with open(os.path.join(OUT, "counts.json"), "w") as fh:
        json.dump(counts, fh, indent=2)
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
