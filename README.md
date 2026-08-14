# Investment Fund Ontology (IFO)

An open OWL 2 ontology, SKOS identifier-scheme registry, and SHACL governance layer for registered investment fund data, built and validated against the full public US fund universe:

- **2,316 registrants, 14,841 funds, 43,344 share classes** from the SEC Investment Company Series and Class dataset,
- **12,217 fund N-CEN reports with self-reported LEIs** across four quarters of SEC Form N-CEN structured data,
- **9,119,948 ISIN-to-LEI pairs** from the GLEIF open mapping file, every one check-digit validated,
- joined into a **1.29 million triple knowledge graph** with per-source named-graph provenance, gated by SHACL, and reported on automatically.

This is not a toy schema with three sample funds. It is the fund product hierarchy (`FundRegistrant > Fund > ShareClass > Listing`) populated at national scale from three authoritative sources that disagree with each other in measurable ways, which is the actual problem fund data teams live with.

## Findings from the first full build (14 August 2026)

All figures below are as of the 14 August 2026 build, run against the GLEIF file dated 8 August 2026 and four quarters of pinned SEC Form N-CEN data (2025q3-2026q2). The SEC series/class register and the GLEIF file are fetched as "current"/"latest" by `scripts/fetch_data.sh`, not pinned to a snapshot, so a rerun today will not reproduce these exact totals. See "Data currency" below.

| # | Finding | Number |
|---|---|---|
| 1 | GLEIF's open ISIN-to-LEI mapping file, checksum-validated in full, not sampled: every one of 9,119,948 pairs | **0 ISIN or LEI check-digit failures**, out of 9,119,948 (as of the 8 Aug 2026 file). This covers check-digit arithmetic only, not deduplication, staleness of the LEI registrations, or correctness of the entity-to-ISIN mapping itself |
| 2 | LEI values inside hand-keyed SEC N-CEN filings that fail the same ISO 7064 check digits GLEIF passes in full, including `00000000000000238096` filed as an LEI | **19 of 14,960 LEI values checked (0.127%, ~0.13%)**. 2 of the 19 are also malformed (a subset of the 19, not additional to it) |
| 3 | ETF funds whose share class has no listing anywhere in public data: the single Violation-severity rule in the ontology's own SHACL layer (every other finding here is Warning-severity) | **73 of 4,053 ETF funds (1.8%)** |
| 4 | ETF funds (self-reported `IS_ETF=Y` flag on Form N-CEN, not a curated exchange list) whose LEI has at least one ISIN in the GLEIF open mapping file. The Vanguard 500 Index Fund (VOO) is among those missing the link: VOO has a real, valid ISIN in commercial data, GLEIF's open file simply does not carry the LEI-to-ISIN pair for it | **497 of 4,053 (12.3%)** |
| 5 | Listings in the SEC series/class register with no trading venue resolvable from public SEC data. This is a scope limit of the public schema, not a data-quality failure: the venue field exists only in Form N-CEN's ETF-only exchange table (Item E.1), and most of the 30,238 listings are ordinary open-end mutual fund share classes that have no trading venue at all by design. The ontology's own SHACL shape grades this Warning and states in its message that it is "not an error in the record" | **29,258 of 30,238 (96.8%)** carry no venue; only 1,130 (3.7%) resolve one |
| 6 | One LEI shared across 27 distinct SEC fund series (the largest of 13 LEIs shared by multiple sibling funds); separately, 214 funds report their registrant's LEI as their own | Very likely a legitimate series-trust structure: one legal entity (one LEI) hosting many SEC series that are not separately incorporated. Graded **Warning**, not Violation, by the ontology's own rules; worth asking about identifier granularity, not evidence of a broken ID |
| 7 | Funds whose registered share classes exceed the class count they reported on their own N-CEN annual report (Warning-severity; timing between an annual filing and a register snapshot explains part of the gap) | **2,148** |
| 8 | US-registered funds issue ISINs under DE, PR, CH, GB, KY and NL prefixes, not only US | **127 non-US ISINs**, out of 7,112 GLEIF-mapped ISINs traced to US-registered fund/registrant LEIs |
| 9 | Fund-level ISINs resolvable to an exact share class by unique pairing alone (v0.1): one class, one ISIN, no ambiguity | **259** of 19,803 funds in the graph (1.3%), drawn from the 2,109 LEIs GLEIF-matched to at least one ISIN; v0.2 closes the hop further, see below |
| 10 | v0.2: (LEI, ISIN) pairs attested in public N-PORT filings (2026q2 only) that are absent from the GLEIF open mapping | **185,894** absent, **2,055 contradicting**, 47,374 agreeing, of 235,327 filing-attested pairs |
| 11 | v0.2: ETFs gaining their first open ISIN from the 2026q2 N-PORT harvest; open ETF ISIN coverage after one quarter | **937 gained; 12.3% to 35.4%** |
| 12 | v0.2: fund-ISIN rows resolved to an exact share class via OpenFIGI ticker join, zero conflicts | **2,186 of 5,176 (42.2%)**. On that same 5,176-row denominator v0.1 resolved 259 (5.0%), so v0.2 is 8.4x the licensed-data-free rate. Note row 9 quotes 259 against a different population, the 19,803 funds in the graph, which is why the two percentages differ |

The strongest result here is #1: 9.1 million machine-maintained GLEIF records, checked in full against the same arithmetic, with zero check-digit failures, set against hand-keyed regulatory filings that have some. The check is pure arithmetic, so 0.13% is still a real defect rate, not a rounding artefact, even though it is small.

The full numbers, method, and caveats: [BUILD_REPORT.md](BUILD_REPORT.md) and [reports/GOVERNANCE_REPORT.md](reports/GOVERNANCE_REPORT.md).

### Data currency

Two of the three v0.1 source feeds are fetched as "current"/"latest," not pinned to the 14 August 2026 build:

- **Pinned, reproducible exactly:** the four SEC Form N-CEN quarters (2025q3-2026q2) and the 2026q2 N-PORT quarter, all fetched by fixed URL.
- **Not pinned, will drift:** the SEC Investment Company Series and Class register (fetched from SEC's always-current snapshot URL) and the GLEIF ISIN-to-LEI file (`scripts/fetch_data.sh` scrapes GLEIF's site for the newest file link, not the 8 Aug 2026 file this build used).

Running `bash scripts/fetch_data.sh` today will pull a different SEC register snapshot and a newer, larger GLEIF file, so fund/class counts, GLEIF pair counts, and downstream percentages will not reproduce exactly. The pipeline and methodology are fully reproducible; the specific headline numbers are timestamped to these two snapshots and are not evergreen constants.

## The open fund identifier map (v0.2)

The enclosure says the fund-to-class identifier join requires licensed CUSIP data. v0.2 rebuilds it from open sources only:

```
ISIN (GLEIF open file + SEC N-PORT public filings)
  -> OpenFIGI (free API over the OMG FIGI open standard)
  -> ticker + share-class FIGI
  -> SEC register class, joined by ticker within the fund
```

The result is [`open-map/fund_identifier_map.csv`](open-map/fund_identifier_map.csv): 5,176 (fund, ISIN) rows, 4,471 carrying FIGIs (86.4%), 2,186 resolved to an exact SEC share class (42.2%) with zero ticker conflicts. Every column is redistributable: LEIs, GLEIF-published and filing-attested ISINs, FIGIs, and public-domain SEC identifiers. No standalone CUSIP, SEDOL, or RIC appears anywhere in the repo, and CONTRIBUTING.md makes that a policy, not an accident. The residual 57.8% is the honest, measured price of refusing licensed data, and three more N-PORT quarters remain to harvest.

## Why this exists

Fund data governance is an identifier problem before it is anything else. A fund complex managing thousands of funds across the US, UK, Ireland, Australia, Canada and Mexico handles dozens of identifier schemes (ISIN, CUSIP, SEDOL, LEI, FIGI, tickers, APIR, FundSERV, regulator registry ids) asserted by many internal source-of-record systems that drift apart silently. The industry answer is manual reconciliation spreadsheets. The better answer is:

1. **Identifiers as first-class nodes**, each carrying its scheme, its source system, and its computed validation state, so cross-system disagreement is a query, not an audit project.
2. **Scope as data**: the SKOS registry declares each scheme entity-scoped, issue-scoped, or venue-scoped, and SHACL enforces that identifiers sit at the right level of the hierarchy (an ISIN on a share class, a ticker on a listing, an LEI on a legal entity).
3. **Policy as executable constraints**: "an exchange-traded fund's share classes must each be listed" is a SHACL shape that runs at fund launch and every day after, not a paragraph in a procedures manual.
4. **Arithmetic in code, policy in shapes**: check digits (ISO 7064 MOD 97-10, the ISIN Luhn variant, CUSIP double-add-double, SEDOL weights) are computed by the pipeline and asserted into the graph; shapes require the recorded result. Encoding MOD 97 in SPARQL is possible and unwise.

## Repository layout

```
ontology/ifo-core.ttl             Core OWL: hierarchy + reified identifier model
ontology/ifo-fibo-alignment.ttl   Graded SKOS alignment to FIBO (every IRI verified live)
skos/identifier-schemes.ttl       Identifier-scheme registry: 20 schemes, 6 markets,
                                  syntax patterns, check algorithms, scope levels
shapes/ifo-shapes.ttl             Layer 1+2 SHACL: syntax, checksum policy, hierarchy
shapes/ifo-rules.ttl              Layer 3 SHACL-SPARQL: cross-source business rules
pipeline/checksums.py             Check-digit algorithms with embedded test vectors
pipeline/build_graph.py           Three-source join -> Turtle + N-Quads
pipeline/validate.py              pyshacl gate over the full graph
pipeline/governance_report.py     Set-based rules + automated governance report
pipeline/resolve_figi.py          v0.2: ISIN -> FIGI/ticker -> share class (open data)
pipeline/harvest_nport.py         v0.2: N-PORT filings -> (LEI, ISIN) backfill + cross-check
pipeline/export_open_map.py       v0.2: emits open-map/fund_identifier_map.csv
open-map/                         The open fund identifier map (committed artifact)
tests/                            Offline test suite (runs in CI, no downloads)
queries/*.rq                      SPARQL 1.1 library (01,02,04,05 tested on the full
                                  1.29M-triple graph; 03 on the example subgraph, its
                                  universe numbers computed by the report pipeline)
examples/                         Committed example subgraph (one fund family)
reports/GOVERNANCE_REPORT.md      The automated report from the latest build
BUILD_REPORT.md                   What was fetched, computed, and NOT obtainable
scripts/fetch_data.sh             Reproduce the source downloads
```

## Reproduce the build

```bash
python3 -m venv .venv && .venv/bin/pip install rdflib pyshacl
bash scripts/fetch_data.sh          # ~70 MB download; set your contact in UA
.venv/bin/python pipeline/checksums.py          # self-test the validators
.venv/bin/python pipeline/build_graph.py        # ~80s: build 1.29M triples
.venv/bin/python pipeline/validate.py           # ~30s: SHACL gate
.venv/bin/python pipeline/governance_report.py  # ~25s: findings report
.venv/bin/python pipeline/harvest_nport.py      # v0.2: N-PORT backfill + cross-check
.venv/bin/python pipeline/resolve_figi.py       # v0.2: ~35 min keyless (resumable cache)
.venv/bin/python pipeline/export_open_map.py    # v0.2: the open identifier map
```

The source data is not committed (310 MB GLEIF file; SEC files are regenerated annually); the committed `examples/` subgraph lets you try the queries without any download.

## Design positions you may disagree with

- **A ShareClass is a Security.** The issued instrument is the share class; a separate `Security` leaf under `Listing` (as some enterprise models have it) conflates the issue with its venue admission. Venue-scoped identifiers live on the Listing.
- **No owl:sameAs across source systems.** Two systems asserting "the same" identifier yield two assertion nodes bridged by `ifo:sameIdentifierAs`. Collapsing them destroys exactly the information governance needs.
- **Warnings are findings, not noise.** A fund with no LEI is not a broken record; it is a governance decision waiting to happen. The severity split encodes that.
- **Layer-3 rules ship as SHACL-SPARQL but run set-based.** Per-focus-node execution of SPARQL constraints over 1.3M triples multiplies query invocations for zero semantic gain. Platforms with native optimisation (TopBraid EDG, GraphDB) can run the shapes as shipped.

## Scope and honesty

v0.1 instance data is US-only by declared scope; the scheme registry models all six target markets (US, UK, IE, AU, CA, MX) so ingestion of the FCA, CBI, APIR, CSA and CNBV registers extends the same graph without remodelling. Licensed identifier fabrics (CUSIP, SEDOL, RIC) are modelled but never asserted as instance data. Every "0 failures" claim is guarded by negative test vectors, and every one of them means 0 check-digit failures specifically: ISO 6166 for ISIN, ISO 17442/ISO 7064 MOD 97-10 for LEI. None of them mean the underlying records are deduplicated, current, or otherwise correct beyond that arithmetic; deduplication, staleness and mapping correctness were not tested. See [BUILD_REPORT.md](BUILD_REPORT.md) for the full list of what public data cannot give you; those gaps are findings, and pretending otherwise is how fund data projects fail.

## Roadmap

- v0.2 (delivered): OpenFIGI resolution, N-PORT backfill and cross-check, the open identifier map, CI and contribution scaffolding.
- v0.3: remaining N-PORT quarters; FCA and CBI register ingestion (UK/IE market instance data); KGCL-based changelog between annual SEC dataset editions.
- v0.3: R2RML mappings as an alternative to the Python pipeline for warehouse-resident source systems; named-graph-per-quarter N-CEN history.

## Licence

Ontology, registry, shapes: CC BY 4.0. Pipeline code: MIT. Source data: SEC (public domain), GLEIF (open publication).

## Author and contact

Built by [Fabio Rovai](https://fabiorovai.com) (The Tesseract Academy). Related work: [open-ontologies](https://github.com/fabio-rovai/open-ontologies) (Rust semantic platform + MCP server), the [FinanceBench verification study](https://gov.tesseract.academy/research/financial-answer-verification), and the deep-dive article on this repository at [gov.tesseract.academy](https://gov.tesseract.academy).

Working on fund data, identifier governance, or semantic data foundations in financial services? I take on proof-of-concept and advisory engagements: **fabio@thetesseractacademy.com**.
