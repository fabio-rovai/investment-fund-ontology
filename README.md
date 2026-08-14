# Investment Fund Ontology (IFO)

An open OWL 2 ontology, SKOS identifier-scheme registry, and SHACL governance layer for registered investment fund data, built and validated against the full public US fund universe:

- **2,316 registrants, 14,841 funds, 43,344 share classes** from the SEC Investment Company Series and Class dataset,
- **12,217 fund N-CEN reports with self-reported LEIs** across four quarters of SEC Form N-CEN structured data,
- **9,119,948 ISIN-to-LEI pairs** from the GLEIF open mapping file, every one check-digit validated,
- joined into a **1.29 million triple knowledge graph** with per-source named-graph provenance, gated by SHACL, and reported on automatically.

This is not a toy schema with three sample funds. It is the fund product hierarchy (`FundRegistrant > Fund > ShareClass > Listing`) populated at national scale from three authoritative sources that disagree with each other in measurable ways, which is the actual problem fund data teams live with.

## Findings from the first full build (14 August 2026)

| # | Finding | Number |
|---|---|---|
| 1 | LEI values inside SEC N-CEN filings that fail the ISO 7064 check digits, including `00000000000000238096` filed as an LEI | **19 failures + 2 malformed** |
| 2 | GLEIF's published ISIN-LEI file, by contrast, is checksum-clean at full scale (validators self-test against corrupted vectors) | **0 failures in 9,119,948 pairs** |
| 3 | ETF funds (all exchange-traded by definition) whose LEI has at least one ISIN in the GLEIF open mapping (the Vanguard 500 Index Fund is among the missing) | **only 497 of 4,053 (12.3%)** |
| 4 | Quotations in the SEC register with no resolvable trading venue in any public SEC dataset | **29,258 of 30,238 (96.8%)** |
| 5 | Funds reporting their registrant's LEI as their own (umbrella/series identifier collapse) | **214**, plus 13 LEIs shared across sibling funds |
| 6 | Funds whose registered share classes exceed the class count they reported on their own N-CEN annual report | **2,148** |
| 7 | US-registered funds issue ISINs under DE, PR, CH, GB, KY and NL prefixes, not only US | **127 non-US ISINs** |
| 8 | Fund-level ISINs resolvable to an exact share class from public data alone (unique pairing) | **259**; the rest require licensed CUSIP-to-class data |

The full numbers, method, and caveats: [BUILD_REPORT.md](BUILD_REPORT.md) and [reports/GOVERNANCE_REPORT.md](reports/GOVERNANCE_REPORT.md).

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
```

The source data is not committed (310 MB GLEIF file; SEC files are regenerated annually); the committed `examples/` subgraph lets you try the queries without any download.

## Design positions you may disagree with

- **A ShareClass is a Security.** The issued instrument is the share class; a separate `Security` leaf under `Listing` (as some enterprise models have it) conflates the issue with its venue admission. Venue-scoped identifiers live on the Listing.
- **No owl:sameAs across source systems.** Two systems asserting "the same" identifier yield two assertion nodes bridged by `ifo:sameIdentifierAs`. Collapsing them destroys exactly the information governance needs.
- **Warnings are findings, not noise.** A fund with no LEI is not a broken record; it is a governance decision waiting to happen. The severity split encodes that.
- **Layer-3 rules ship as SHACL-SPARQL but run set-based.** Per-focus-node execution of SPARQL constraints over 1.3M triples multiplies query invocations for zero semantic gain. Platforms with native optimisation (TopBraid EDG, GraphDB) can run the shapes as shipped.

## Scope and honesty

v0.1 instance data is US-only by declared scope; the scheme registry models all six target markets (US, UK, IE, AU, CA, MX) so ingestion of the FCA, CBI, APIR, CSA and CNBV registers extends the same graph without remodelling. Licensed identifier fabrics (CUSIP, SEDOL, RIC) are modelled but never asserted as instance data. Every "0 failures" claim is guarded by negative test vectors. See [BUILD_REPORT.md](BUILD_REPORT.md) for the full list of what public data cannot give you; those gaps are findings, and pretending otherwise is how fund data projects fail.

## Roadmap

- v0.2: FIGI ingestion via the OpenFIGI API; FCA and CBI register ingestion (UK/IE market instance data); KGCL-based changelog between annual SEC dataset editions.
- v0.3: R2RML mappings as an alternative to the Python pipeline for warehouse-resident source systems; named-graph-per-quarter N-CEN history.

## Licence

Ontology, registry, shapes: CC BY 4.0. Pipeline code: MIT. Source data: SEC (public domain), GLEIF (open publication).

## Author and contact

Built by [Fabio Rovai](https://fabiorovai.com) (The Tesseract Academy). Related work: [open-ontologies](https://github.com/fabio-rovai/open-ontologies) (Rust semantic platform + MCP server), the [FinanceBench verification study](https://gov.tesseract.academy/research/financial-answer-verification), and the deep-dive article on this repository at [gov.tesseract.academy](https://gov.tesseract.academy).

Working on fund data, identifier governance, or semantic data foundations in financial services? I take on proof-of-concept and advisory engagements: **fabio@thetesseractacademy.com**.
