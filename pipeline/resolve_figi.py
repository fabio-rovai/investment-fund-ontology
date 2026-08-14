"""Resolve fund-level ISINs to share classes via OpenFIGI.

The v0.1 build left most ISINs honestly parked at fund level because
the ISIN-to-class hop traditionally runs through licensed CUSIP data.
This stage closes that hop with open data only:

    ISIN (GLEIF, open)
      -> OpenFIGI mapping API (free; FIGIs are an OMG open standard
         explicitly free to store and redistribute)
      -> ticker + share-class FIGI
      -> join to the SEC class whose register ticker matches, within
         the same fund

Behaviour:
  - Batches of 10 mapping jobs per request (the keyless maximum
    verified live), paced to the 25 requests/minute keyless limit
    using the server's ratelimit headers. Set OPENFIGI_API_KEY for
    the keyed tier (100 jobs per request) and the script uses it.
  - Results cached to data/build/figi_map.jsonl; reruns resume where
    they left off, so a killed run costs nothing.
  - Output: data/build/figi_graph.ttl (FIGI identifier assertions,
    ISIN promotions with ifo:resolutionMethod "figi-ticker-join")
    and data/build/figi_stats.json.

Every FIGI stored here is redistributable; no CUSIP, SEDOL or RIC is
requested, stored, or emitted.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "data", "build")

IFO = Namespace("https://gov.tesseract.academy/def/fund#")
SCH = Namespace("https://gov.tesseract.academy/def/fund/scheme#")
ID = "https://gov.tesseract.academy/id/fund/"

API = "https://api.openfigi.com/v3/mapping"
API_KEY = os.environ.get("OPENFIGI_API_KEY", "")
BATCH = 100 if API_KEY else 10
CACHE = os.path.join(BUILD, "figi_map.jsonl")


def load_graph() -> Graph:
    g = Graph()
    g.parse(os.path.join(BUILD, "fund_graph.ttl"), format="turtle")
    nport = os.path.join(BUILD, "nport_graph.ttl")
    if os.path.exists(nport):
        g.parse(nport, format="turtle")
    return g


def collect_targets(g: Graph):
    """ISINs asserted at fund level, with their fund's classes+tickers."""
    isin_to_fund = {}
    for isin_node in g.subjects(RDF.type, IFO.ISIN):
        val = str(g.value(isin_node, IFO.identifierValue))
        for fund in g.objects(isin_node, IFO.hasIssuedSecurityIdentifier):
            if (fund, RDF.type, IFO.Fund) in g:
                isin_to_fund[val] = (isin_node, fund)
    fund_classes = {}
    for val, (node, fund) in isin_to_fund.items():
        if fund not in fund_classes:
            pairs = []
            for c in g.objects(fund, IFO.hasShareClass):
                ticker = None
                for lst in g.objects(c, IFO.hasListing):
                    for tid in g.subjects(IFO.identifies, lst):
                        if (tid, RDF.type, IFO.TickerSymbol) in g:
                            ticker = str(g.value(tid, IFO.identifierValue))
                pairs.append((c, ticker))
            fund_classes[fund] = pairs
    return isin_to_fund, fund_classes


def fetch_mappings(isins):
    done = {}
    if os.path.exists(CACHE):
        with open(CACHE) as fh:
            for line in fh:
                rec = json.loads(line)
                done[rec["isin"]] = rec
    todo = [i for i in isins if i not in done]
    print(f"{len(done)} cached, {len(todo)} to fetch "
          f"(batch {BATCH}, {'keyed' if API_KEY else 'keyless'})",
          flush=True)
    out = open(CACHE, "a")
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        body = json.dumps(
            [{"idType": "ID_ISIN", "idValue": v} for v in chunk]).encode()
        req = urllib.request.Request(
            API, data=body, headers={"Content-Type": "application/json"})
        if API_KEY:
            req.add_header("X-OPENFIGI-APIKEY", API_KEY)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    results = json.loads(resp.read())
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = int(e.headers.get("ratelimit-reset", "60")) + 1
                    print(f"429; sleeping {wait}s", flush=True)
                    time.sleep(wait)
                else:
                    raise
        else:
            raise SystemExit("giving up after repeated 429s")
        for isin, res in zip(chunk, results):
            rec = {"isin": isin}
            data = (res or {}).get("data") or []
            if data:
                d = data[0]
                rec.update(ticker=d.get("ticker"),
                           figi=d.get("figi"),
                           shareClassFIGI=d.get("shareClassFIGI"),
                           securityType=d.get("securityType"),
                           exchCode=d.get("exchCode"))
            else:
                rec["error"] = (res or {}).get("error", "No identifier found.")
            done[isin] = rec
            out.write(json.dumps(rec) + "\n")
        out.flush()
        if (i // BATCH) % 20 == 0:
            print(f"  {i + len(chunk)}/{len(todo)} fetched", flush=True)
        time.sleep(0.3 if API_KEY else 2.7)
    out.close()
    return done


def main() -> None:
    g = load_graph()
    isin_to_fund, fund_classes = collect_targets(g)
    print(f"{len(isin_to_fund)} fund-level ISINs to resolve", flush=True)

    mappings = fetch_mappings(sorted(isin_to_fund))

    out = Graph()
    out.bind("ifo", IFO)
    out.bind("ifosch", SCH)
    stats = {"targets": len(isin_to_fund), "figi_found": 0,
             "ticker_returned": 0, "resolved_to_class": 0,
             "ticker_conflicts": 0, "no_figi": 0}
    for isin, (node, fund) in isin_to_fund.items():
        rec = mappings.get(isin) or {}
        if not rec.get("figi"):
            stats["no_figi"] += 1
            continue
        stats["figi_found"] += 1
        fnode = URIRef(ID + f"identifier/figi/{rec['figi']}")
        out.add((fnode, RDF.type, IFO.Identifier))
        out.add((fnode, RDF.type, IFO.FIGI))
        out.add((fnode, IFO.identifierValue, Literal(rec["figi"])))
        out.add((fnode, IFO.identifierScheme, SCH.FIGI))
        out.add((fnode, IFO.sourceSystem, SCH.OpenFIGI))
        ticker = rec.get("ticker")
        if not ticker:
            continue
        stats["ticker_returned"] += 1
        matches = [c for c, t in fund_classes.get(fund, []) if t == ticker]
        if len(matches) == 1:
            cls = matches[0]
            out.add((node, IFO.identifies, cls))
            out.add((node, IFO.resolutionMethod,
                     Literal("figi-ticker-join")))
            out.add((fnode, IFO.identifies, cls))
            out.add((cls, IFO.identifiedBy, fnode))
            out.add((cls, IFO.identifiedBy, node))
            stats["resolved_to_class"] += 1
        elif len(matches) > 1:
            stats["ticker_conflicts"] += 1

    out.serialize(os.path.join(BUILD, "figi_graph.ttl"), format="turtle")
    with open(os.path.join(BUILD, "figi_stats.json"), "w") as fh:
        json.dump(stats, fh, indent=2)
    print(json.dumps(stats, indent=2), flush=True)


if __name__ == "__main__":
    main()
