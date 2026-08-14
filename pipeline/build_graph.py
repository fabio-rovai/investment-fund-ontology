"""Build the investment-fund knowledge graph from three public sources.

Sources (all snapshots in data/, all fetched 14 Aug 2026):
  1. SEC Investment Company Series and Class dataset (CSV)
     - registrant (CIK, name, 811- file number) > series (S id) >
       class (C id, ticker).
  2. SEC Form N-CEN structured data, 4 quarters 2025q3..2026q2
     - registrant LEI, per-series LEI, fund classification flags,
       authorised class counts, ETF listing exchanges (MIC + ticker).
  3. GLEIF ISIN-to-LEI relationship file
     - ISINs issued by each fund/registrant LEI.

Output:
  data/build/fund_graph.ttl       - single-graph Turtle
  data/build/fund_graph.nq        - N-Quads, one named graph per source
  data/build/gleif_stats.json     - full-file GLEIF validation stats
  data/build/build_stats.json     - build-side counts for the report

Every identifier value is asserted exactly as the source spelled it;
checksums are computed here and recorded as ifo:checksumValid for the
SHACL layer to police. Provenance is carried twice, deliberately:
ifo:sourceSystem on every identifier node (queryable inside any
single graph) and the N-Quads named graph (wholesale provenance).
"""

from __future__ import annotations

import csv
import glob
import json
import os
import sys
import time
from collections import Counter, defaultdict

from rdflib import ConjunctiveGraph, Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

sys.path.insert(0, os.path.dirname(__file__))
from checksums import cusip_valid, isin_valid, lei_valid  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BUILD = os.path.join(DATA, "build")
os.makedirs(BUILD, exist_ok=True)

IFO = Namespace("https://gov.tesseract.academy/def/fund#")
SCH = Namespace("https://gov.tesseract.academy/def/fund/scheme#")
ID = "https://gov.tesseract.academy/id/fund/"

G_SCI = URIRef("https://gov.tesseract.academy/graph/sec-series-class")
G_NCEN = URIRef("https://gov.tesseract.academy/graph/sec-ncen")
G_GLEIF = URIRef("https://gov.tesseract.academy/graph/gleif-isin-lei")

NCEN_QUARTERS = ["2025q3", "2025q4", "2026q1", "2026q2"]

stats: dict = {"built": time.strftime("%Y-%m-%d")}


def uri(*parts: str) -> URIRef:
    return URIRef(ID + "/".join(p.replace(" ", "_") for p in parts))


def add_identifier(g: Graph, subject: URIRef, kind: str, cls, scheme,
                   value: str, source, checksum=None, scope_prop=None):
    """Mint a reified identifier node and link it to its subject."""
    node = uri("identifier", kind, value)
    g.add((node, RDF.type, IFO.Identifier))
    g.add((node, RDF.type, cls))
    g.add((node, IFO.identifierValue, Literal(value)))
    g.add((node, IFO.identifierScheme, scheme))
    g.add((node, IFO.sourceSystem, source))
    if checksum is not None:
        g.add((node, IFO.checksumValid,
               Literal(checksum, datatype=XSD.boolean)))
    prop = scope_prop or IFO.identifies
    g.add((node, prop, subject))
    g.add((subject, IFO.identifiedBy, node))
    return node


def main() -> None:
    cg = ConjunctiveGraph()
    sci = cg.get_context(G_SCI)
    ncen = cg.get_context(G_NCEN)
    gleif = cg.get_context(G_GLEIF)

    # ------------------------------------------------------------------
    # 1. SEC series/class register: the structural spine.
    # ------------------------------------------------------------------
    registrants: dict[str, str] = {}
    series_of: dict[str, str] = {}
    classes_of: dict[str, list] = defaultdict(list)
    tickers: dict[str, str] = {}

    path = os.path.join(DATA, "sec_series_class_current.csv")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            cik = row["CIK"].lstrip("0") or "0"
            sid, cid = row["series_id"], row["class_id"]
            if not sid.startswith("S") or not cid.startswith("C"):
                continue
            registrants.setdefault(cik, row["entity_name"])
            series_of.setdefault(sid, cik)
            classes_of[sid].append((cid, row["class_name"]))
            tick = row["class_ticker_symbol"].strip()
            if tick and tick != "[NULL]":
                tickers[cid] = tick

            r, s, c = uri("registrant", cik), uri("series", sid), uri("class", cid)
            if (r, RDF.type, IFO.FundRegistrant) not in sci:
                sci.add((r, RDF.type, IFO.FundRegistrant))
                sci.add((r, IFO.legalName, Literal(row["entity_name"])))
                sci.add((r, IFO.domicileCountry, Literal("US")))
                add_identifier(sci, r, "cik", IFO.CIK, SCH.CIK, cik, SCH["SEC-SCI"])
                fn = row["rep_file_num"].strip()
                if fn:
                    add_identifier(sci, r, "filenum", IFO.SECFileNumber,
                                   SCH.SECFileNumber, fn, SCH["SEC-SCI"])
            if (s, RDF.type, IFO.Fund) not in sci:
                sci.add((s, RDF.type, IFO.Fund))
                sci.add((s, IFO.legalName, Literal(row["series_name"])))
                sci.add((s, IFO.fundOf, r))
                sci.add((r, IFO.hasFund, s))
                add_identifier(sci, s, "series", IFO.SECSeriesId,
                               SCH.SECSeriesId, sid, SCH["SEC-SCI"])
            sci.add((c, RDF.type, IFO.ShareClass))
            sci.add((c, IFO.legalName, Literal(row["class_name"])))
            sci.add((c, IFO.shareClassOf, s))
            sci.add((s, IFO.hasShareClass, c))
            add_identifier(sci, c, "class", IFO.SECClassId,
                           SCH.SECClassId, cid, SCH["SEC-SCI"])
            if cid in tickers:
                lst = uri("listing", cid)
                sci.add((lst, RDF.type, IFO.Listing))
                sci.add((lst, IFO.listingOf, c))
                sci.add((c, IFO.hasListing, lst))
                add_identifier(sci, lst, "ticker", IFO.TickerSymbol,
                               SCH.TickerSymbol, tickers[cid], SCH["SEC-SCI"])

    stats["sci_registrants"] = len(registrants)
    stats["sci_series"] = len(series_of)
    stats["sci_classes"] = sum(len(v) for v in classes_of.values())
    stats["sci_tickers"] = len(tickers)

    # ------------------------------------------------------------------
    # 2. N-CEN: LEIs, classification flags, ETF exchanges.
    #    Latest accession per series wins across the 4 quarters.
    # ------------------------------------------------------------------
    reg_lei: dict[str, tuple] = {}        # cik -> (accession, lei)
    fund_rows: dict[str, tuple] = {}      # series id -> (accession, row)
    exchange_rows: list[tuple] = []       # (accession, cik, sid, mic, ticker)

    for q in NCEN_QUARTERS:
        base = os.path.join(DATA, "ncen", q)
        with open(os.path.join(base, "REGISTRANT.tsv"), newline="",
                  encoding="utf-8", errors="replace") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                cik = row["CIK"].lstrip("0") or "0"
                acc = row["ACCESSION_NUMBER"]
                lei = (row.get("LEI") or "").strip()
                if lei and (cik not in reg_lei or acc > reg_lei[cik][0]):
                    reg_lei[cik] = (acc, lei)
        with open(os.path.join(base, "FUND_REPORTED_INFO.tsv"), newline="",
                  encoding="utf-8", errors="replace") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                sid = (row.get("SERIES_ID") or "").strip()
                acc = row["ACCESSION_NUMBER"]
                if sid.startswith("S") and (
                        sid not in fund_rows or acc > fund_rows[sid][0]):
                    fund_rows[sid] = (acc, row)
        sx = os.path.join(base, "SECURITY_EXCHANGE.tsv")
        if os.path.exists(sx):
            with open(sx, newline="", encoding="utf-8",
                      errors="replace") as fh:
                for row in csv.DictReader(fh, delimiter="\t"):
                    fid = row.get("FUND_ID") or ""
                    parts = fid.split("_")
                    if len(parts) == 3 and parts[2].startswith("S"):
                        exchange_rows.append(
                            (parts[0], parts[1].lstrip("0"), parts[2],
                             (row.get("FUND_EXCHANGE") or "").strip(),
                             (row.get("FUND_TICKER_SYMBOL") or "").strip()))

    feature_flags = {
        "IS_ETF": SCH.ExchangeTradedFund,
        "IS_INDEX": SCH.IndexFund,
        "IS_MONEY_MARKET": SCH.MoneyMarketFund,
        "IS_TARGET_DATE": SCH.TargetDateFund,
        "IS_FUND_OF_FUND": SCH.FundOfFunds,
        "IS_MASTER_FEEDER": SCH.MasterFeeder,
        "IS_INTERVAL": SCH.IntervalFund,
    }

    fund_lei: dict[str, str] = {}
    for cik, (acc, lei) in reg_lei.items():
        r = uri("registrant", cik)
        if cik not in registrants:
            # Registrant filed N-CEN but is absent from the current
            # series/class register (deregistered or BDC): keep it,
            # typed, so the join gap is measurable.
            ncen.add((r, RDF.type, IFO.FundRegistrant))
            ncen.add((r, IFO.legalName, Literal("(not in current series/class register)")))
        add_identifier(ncen, r, "lei", IFO.LEI, SCH.LEI, lei,
                       SCH["SEC-NCEN"], checksum=lei_valid(lei))

    ncen_series_in_sci = 0
    for sid, (acc, row) in fund_rows.items():
        s = uri("series", sid)
        if sid in series_of:
            ncen_series_in_sci += 1
        else:
            ncen.add((s, RDF.type, IFO.Fund))
            ncen.add((s, IFO.legalName, Literal(row.get("FUND_NAME") or sid)))
            add_identifier(ncen, s, "series", IFO.SECSeriesId,
                           SCH.SECSeriesId, sid, SCH["SEC-NCEN"])
        lei = (row.get("LEI") or "").strip()
        if lei:
            fund_lei[sid] = lei
            add_identifier(ncen, s, "lei", IFO.LEI, SCH.LEI, lei,
                           SCH["SEC-NCEN"], checksum=lei_valid(lei))
        for flag, concept in feature_flags.items():
            if (row.get(flag) or "").strip().upper() == "Y":
                ncen.add((s, IFO.hasFeature, concept))
        cnt = (row.get("AUTHORIZED_SHARES_CNT") or "").strip()
        if cnt.isdigit():
            ncen.add((s, IFO.reportedShareClassCount,
                      Literal(int(cnt), datatype=XSD.integer)))

    # ETF listing exchanges: venue-resolved listings. The exchange rows
    # are series-level; attach the venue to the class whose SCI ticker
    # matches the N-CEN ticker, the only public join key available.
    venues_seen = set()
    etf_listings = 0
    ticker_to_class = defaultdict(list)
    for cid, t in tickers.items():
        ticker_to_class[t].append(cid)
    for acc, cik, sid, mic, tick in exchange_rows:
        if not mic or not tick:
            continue
        matches = [cid for cid in ticker_to_class.get(tick, [])
                   if series_of.get(sid) is not None and
                   any(cid == c for c, _ in classes_of.get(sid, []))]
        if len(matches) != 1:
            continue
        cid = matches[0]
        lst = uri("listing", cid)
        venue = uri("venue", mic)
        if mic not in venues_seen:
            venues_seen.add(mic)
            ncen.add((venue, RDF.type, IFO.TradingVenue))
            add_identifier(ncen, venue, "mic", IFO.MICIdentifier,
                           SCH.MIC, mic, SCH["SEC-NCEN"])
        ncen.add((lst, RDF.type, IFO.Listing))
        ncen.add((lst, IFO.listedOn, venue))
        etf_listings += 1

    stats["ncen_registrant_leis"] = len(reg_lei)
    stats["ncen_fund_reports"] = len(fund_rows)
    stats["ncen_fund_leis"] = len(fund_lei)
    stats["ncen_series_in_sci"] = ncen_series_in_sci
    stats["ncen_etf_listings_venue_resolved"] = etf_listings
    stats["ncen_venues"] = len(venues_seen)

    # ------------------------------------------------------------------
    # 3. GLEIF ISIN-LEI: full-file validation + fund-scoped join.
    # ------------------------------------------------------------------
    wanted = {}
    for sid, lei in fund_lei.items():
        wanted.setdefault(lei, []).append(("series", sid))
    for cik, (acc, lei) in reg_lei.items():
        wanted.setdefault(lei, []).append(("registrant", cik))

    gleif_file = glob.glob(os.path.join(DATA, "lei-isin-*.csv"))[0]
    total = bad_isin = bad_lei = 0
    prefix_counter: Counter = Counter()
    fund_isins: dict[str, list] = defaultdict(list)
    matched_pairs = 0
    with open(gleif_file, newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        for lei, isin in reader:
            total += 1
            if not isin_valid(isin):
                bad_isin += 1
            if not lei_valid(lei):
                bad_lei += 1
            if lei in wanted:
                matched_pairs += 1
                fund_isins[lei].append(isin)
                prefix_counter[isin[:2]] += 1

    stats["gleif_file"] = os.path.basename(gleif_file)
    stats["gleif_total_pairs"] = total
    stats["gleif_isin_checksum_failures"] = bad_isin
    stats["gleif_lei_checksum_failures"] = bad_lei
    stats["gleif_matched_pairs"] = matched_pairs
    stats["gleif_matched_leis"] = len(fund_isins)
    stats["fund_isin_prefixes"] = dict(prefix_counter.most_common())

    resolved = 0
    for lei, isins in fund_isins.items():
        for kind, key in wanted[lei]:
            subject = uri(kind, key)
            for isin in isins:
                node = add_identifier(
                    gleif, subject, "isin", IFO.ISIN, SCH.ISIN, isin,
                    SCH["GLEIF-ISIN-LEI"], checksum=isin_valid(isin),
                    scope_prop=IFO.hasIssuedSecurityIdentifier)
                # A US ISIN embeds a CUSIP in positions 3..11 with its
                # own independent check digit: mint the derived CUSIP
                # as a first-class identifier and validate it too.
                if isin.startswith("US") and isin_valid(isin):
                    cusip = isin[2:11]
                    cnode = add_identifier(
                        gleif, subject, "cusip", IFO.CUSIP, SCH.CUSIP,
                        cusip, SCH["GLEIF-ISIN-LEI"],
                        checksum=cusip_valid(cusip),
                        scope_prop=IFO.hasIssuedSecurityIdentifier)
                    gleif.add((cnode, IFO.resolutionMethod,
                               Literal("derived-from-isin")))
                # Unique-pairing promotion: one class, one ISIN.
                if (kind == "series" and len(isins) == 1
                        and len(classes_of.get(key, [])) == 1):
                    cid = classes_of[key][0][0]
                    gleif.add((node, IFO.identifies, uri("class", cid)))
                    gleif.add((node, IFO.resolutionMethod,
                               Literal("unique-pairing")))
                    resolved += 1

    stats["isin_unique_pairing_resolved"] = resolved

    # ------------------------------------------------------------------
    # Serialise.
    # ------------------------------------------------------------------
    cg.serialize(os.path.join(BUILD, "fund_graph.nq"), format="nquads")
    merged = Graph()
    for ctx in (sci, ncen, gleif):
        for t in ctx:
            merged.add(t)
    merged.serialize(os.path.join(BUILD, "fund_graph.ttl"), format="turtle")
    stats["graph_triples"] = len(merged)

    with open(os.path.join(BUILD, "build_stats.json"), "w") as fh:
        json.dump(stats, fh, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
