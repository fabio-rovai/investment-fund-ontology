"""Backfill the open identifier fabric from SEC Form N-PORT filings.

Funds must file their portfolios monthly; every holding row names the
issuer's LEI and, in the identifier rows, the holding's ISIN. Fund-of-
funds and index funds hold other funds and ETFs, so public regulatory
filings are a lawful open source of exactly the (LEI, ISIN) pairs the
GLEIF open mapping is missing.

This stage:
  1. streams one quarter of FUND_REPORTED_HOLDING + IDENTIFIERS,
  2. extracts (issuer LEI, ISIN) pairs attested by filings,
  3. measures the backfill against GLEIF for OUR fund universe
     (which ETF funds gain their first open ISIN), and
  4. runs the global cross-check: where filings and GLEIF disagree
     about which LEI issued an ISIN.

No standalone CUSIP column is read, stored, or emitted anywhere in
this stage; identifier rows are used for their ISIN and ticker only.

Output: data/build/nport_graph.ttl, data/build/nport_stats.json.
"""

from __future__ import annotations

import csv
import glob
import json
import os
import sys

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

sys.path.insert(0, os.path.dirname(__file__))
from checksums import isin_valid, lei_valid  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BUILD = os.path.join(DATA, "build")
QUARTER = "2026q2"

IFO = Namespace("https://gov.tesseract.academy/def/fund#")
SCH = Namespace("https://gov.tesseract.academy/def/fund/scheme#")
ID = "https://gov.tesseract.academy/id/fund/"

csv.field_size_limit(10_000_000)


def stream_pairs():
    """Yield (lei, isin) pairs attested by holdings in the quarter."""
    base = os.path.join(DATA, "nport", QUARTER)
    lei_of = {}
    with open(os.path.join(base, "FUND_REPORTED_HOLDING.tsv"), newline="",
              encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            lei = (row.get("ISSUER_LEI") or "").strip().upper()
            if len(lei) == 20:
                lei_of[row["HOLDING_ID"]] = lei
    with open(os.path.join(base, "IDENTIFIERS.tsv"), newline="",
              encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            isin = (row.get("IDENTIFIER_ISIN") or "").strip().upper()
            lei = lei_of.get(row["HOLDING_ID"])
            if lei and len(isin) == 12:
                yield lei, isin


def main() -> None:
    stats = {"quarter": QUARTER}

    # Our universe: fund and registrant LEIs from the built graph.
    g = Graph()
    g.parse(os.path.join(BUILD, "fund_graph.ttl"), format="turtle")
    fund_leis = {}          # lei -> fund URI (series only)
    all_leis = set()
    etf_leis = set()
    etfs = set(g.subjects(IFO.hasFeature, SCH.ExchangeTradedFund))
    for node in g.subjects(RDF.type, IFO.LEI):
        val = str(g.value(node, IFO.identifierValue))
        all_leis.add(val)
        for ent in g.objects(node, IFO.identifies):
            if (ent, RDF.type, IFO.Fund) in g:
                fund_leis[val] = ent
                if ent in etfs:
                    etf_leis.add(val)
    funds_with_gleif_isin = set()
    for isin_node in g.subjects(RDF.type, IFO.ISIN):
        for f in g.objects(isin_node, IFO.hasIssuedSecurityIdentifier):
            funds_with_gleif_isin.add(f)

    # GLEIF baseline: isin -> lei for the global cross-check.
    gleif_file = glob.glob(os.path.join(DATA, "lei-isin-*.csv"))[0]
    gleif = {}
    with open(gleif_file, newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        for lei, isin in reader:
            gleif[isin] = lei

    # Stream the filings.
    pairs = set()
    for lei, isin in stream_pairs():
        pairs.add((lei, isin))
    stats["nport_holding_lei_isin_pairs"] = len(pairs)

    agree = disagree = novel = 0
    bad_isin = 0
    disagree_samples = []
    our_new = {}            # fund URI -> set of new ISINs
    for lei, isin in pairs:
        if not isin_valid(isin):
            bad_isin += 1
            continue
        mapped = gleif.get(isin)
        if mapped is None:
            novel += 1
        elif mapped == lei:
            agree += 1
        else:
            disagree += 1
            if len(disagree_samples) < 25:
                disagree_samples.append(
                    {"isin": isin, "filing_lei": lei, "gleif_lei": mapped})
        if lei in fund_leis and (mapped is None):
            our_new.setdefault(fund_leis[lei], set()).add(isin)

    stats["isin_checksum_failures_in_filings"] = bad_isin
    stats["pairs_agreeing_with_gleif"] = agree
    stats["pairs_absent_from_gleif"] = novel
    stats["pairs_contradicting_gleif"] = disagree
    stats["disagree_samples"] = disagree_samples

    etf_gaining = sum(
        1 for f in our_new
        if f in etfs and f not in funds_with_gleif_isin)
    stats["our_funds_gaining_first_open_isin"] = sum(
        1 for f in our_new if f not in funds_with_gleif_isin)
    stats["our_etfs_gaining_first_open_isin"] = etf_gaining
    stats["our_funds_with_new_pairs"] = len(our_new)

    out = Graph()
    out.bind("ifo", IFO)
    out.bind("ifosch", SCH)
    for fund, isins in our_new.items():
        for isin in isins:
            node = URIRef(ID + f"identifier/isin/{isin}")
            out.add((node, RDF.type, IFO.Identifier))
            out.add((node, RDF.type, IFO.ISIN))
            out.add((node, IFO.identifierValue, Literal(isin)))
            out.add((node, IFO.identifierScheme, SCH.ISIN))
            out.add((node, IFO.sourceSystem, SCH["SEC-NPORT"]))
            out.add((node, IFO.checksumValid,
                     Literal(True, datatype=XSD.boolean)))
            out.add((node, IFO.hasIssuedSecurityIdentifier, fund))
            out.add((fund, IFO.identifiedBy, node))
    out.serialize(os.path.join(BUILD, "nport_graph.ttl"), format="turtle")

    with open(os.path.join(BUILD, "nport_stats.json"), "w") as fh:
        json.dump(stats, fh, indent=2)
    print(json.dumps(stats, indent=2)[:4000], flush=True)


if __name__ == "__main__":
    main()
