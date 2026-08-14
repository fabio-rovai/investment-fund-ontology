# Build report

Build date: 14 August 2026. Machine: Apple silicon laptop, Python 3.11, rdflib 7.6.0, pyshacl 0.40.1. Everything below states exactly what was fetched, what was computed, and what could not be obtained. Nothing is estimated.

## What was fetched

| Source | File | Fetched | Contents |
|---|---|---|---|
| SEC Investment Company Series and Class dataset | `investment_company_series_class.csv` (7.8 MB) | 2026-08-14 | 43,344 class rows across 14,841 series and 2,316 registrants, with CIK, 811- file number, series id, class id, ticker |
| SEC Form N-CEN structured data | `2025q3` `2025q4` `2026q1` `2026q2` zips (38 MB total) | 2026-08-14 | 3,369 registrant filings and 14,283 fund report rows; deduplicated to 12,217 funds by latest accession, all carrying self-reported LEIs, classification flags and, for ETFs, listing exchange MICs |
| GLEIF ISIN-to-LEI relationship file | `lei-isin-20260808T071509.csv` (310 MB, zip 32 MB) | 2026-08-14, file dated 2026-08-08 | 9,119,948 ISIN-LEI pairs |
| FIBO modules (for alignment verification only) | SEC/Funds/Funds, SEC/Securities/SecuritiesIdentification, SEC/Securities/SecuritiesListings, BE/LegalEntities/LEIEntities, FBC/FinancialInstruments/FinancialInstruments, FBC/FunctionalEntities/Markets | 2026-08-14 | Turtle serialisations from spec.edmcouncil.org; every IRI asserted in `ontology/ifo-fibo-alignment.ttl` was confirmed present in these files before assertion |

**Pinning.** The four N-CEN quarters and the 2026q2 N-PORT quarter are fetched by fixed URL and are reproducible exactly. The SEC series/class register is fetched from SEC's always-current snapshot URL, and the GLEIF file is fetched by scraping GLEIF's site for the newest available link (`scripts/fetch_data.sh`); neither is pinned to this build's date. A rerun of `fetch_data.sh` today will pull a different register snapshot and a newer, larger GLEIF file, so the counts in this report will not reproduce exactly. Treat every headline figure below as dated to 14 August 2026 (register) and 8 August 2026 (GLEIF), not as an evergreen constant.

## What was built

- `data/build/fund_graph.ttl`: 1,292,541 triples (96 MB), merged graph.
- `data/build/fund_graph.nq`: the same assertions as N-Quads in three named graphs, one per source system (291 MB).
- 126,425 reified identifier assertions across 10 schemes, each carrying scheme, source system, and (for ISIN, LEI, CUSIP) computed check-digit state.
- Build time 82 seconds, including full-file validation of all 9,119,948 GLEIF pairs.
- SHACL gate (layers 1 and 2, 15 shapes) over the full 1.29M-triple graph: 27.3 seconds in pyshacl, 42,890 results (4,986 violations, 37,904 warnings).
- Layer-3 business rules executed set-based (see `shapes/ifo-rules.ttl` for why): all six rules over the full graph in under 24 seconds.

## Validation guard

The zero checksum-failure results on the GLEIF file are guarded against a vacuous validator: `pipeline/checksums.py` embeds negative test vectors (corrupted Apple ISIN, LEI, CUSIP; corrupted HSBC SEDOL) and the self-test runs them on every invocation. Scope: "zero checksum failures" means zero ISO 6166 (ISIN) and ISO 17442/ISO 7064 MOD 97-10 (LEI) check-digit failures across all 9,119,948 pairs, full-file, not sampled. It does not mean the file is free of duplicate entries, stale or lapsed LEI registrations, or incorrect entity-to-ISIN mappings; none of that was tested. The 19 distinct LEI values (of 14,960 checked, 0.13%) that fail their check digit inside N-CEN filings come from the same code paths that pass 9.1 million GLEIF LEIs, which is what makes them credible; 2 of those 19 are additionally malformed (a subset of the 19, not additional to it).

## What could NOT be obtained from public data

Stated plainly, because each gap is itself a finding:

1. **Venue for 96.8 percent of quotations (29,258 of 30,238), as of 14 August 2026.** This is a scope limit of the public schema, not a failure: the SEC series/class register carries no venue/exchange field at all for any listing, and the only venue source is Form N-CEN's ETF-only exchange table (Item E.1), which non-ETF funds never complete because it does not apply to them. Most of the 30,238 listings are ordinary open-end mutual fund share classes, which transact at NAV and have no trading venue concept by design; only the 4,053 self-flagged ETF series could plausibly have one. Only the 1,130 ETF listings joinable to N-CEN exchange rows resolve to a MIC (3.7% of all listings). The ontology's own SHACL shape grades this Warning and its message states explicitly that it is "not an error in the record."
2. **Class-level ISIN resolution.** GLEIF maps LEI to ISIN set; the LEI sits at fund level. Resolving which ISIN belongs to which share class requires CUSIP-to-class data, which is licensed (CUSIP Global Services). 259 of 19,803 funds resolve exactly by unique pairing (one class, one ISIN); the rest stay honestly at fund level via `ifo:hasIssuedSecurityIdentifier`.
3. **ISINs for 87.7 percent of ETFs (3,556 of 4,053), as of the 8 Aug 2026 GLEIF file.** Only 497 of 4,053 ETF funds have any ISIN against their LEI in GLEIF's open ISIN-to-LEI mapping file, although every one of them is exchange-traded and therefore has an ISIN in commercial datasets. This is a gap in GLEIF's open file, which relies on voluntary/optional ISIN reporting by the legal entity (LEI-CDF Level 2 is not mandatory), not evidence that these funds lack an ISIN.
4. **SEDOL, FIGI, APIR, FundSERV instance data.** SEDOL and RIC are licensed; FIGI requires an API key (feasible, not done in v0.1); APIR and FundSERV have no open bulk files. The schemes are modelled in the registry; no instances are asserted.
5. **Non-US regulator registers.** The FCA, CBI, ASIC/APIR, CSA and CNBV registers are not ingested in v0.1; the registry models their schemes so the model is 6-market-ready, but instance data is US-only. This is the declared scope of v0.1, not an oversight.

## Interpretation caveats

- The 59.4 percent N-CEN-to-register match rate is a universe difference, not pure error: the current series/class file lists active series at its publication date, while four quarters of N-CEN include since-terminated series and BDCs. The graph keeps unmatched entities typed so the mismatch stays measurable rather than silently dropped.
- The 2,148 funds whose observed class count exceeds their N-CEN reported count compare an annual-report-time figure with a register snapshot; timing explains part of the divergence. It is reported as a Warning, not a Violation, for exactly that reason.
- `AUTHORIZED_SHARES_CNT` in the N-CEN extracts was empirically verified to hold small integers (0 to about 30) consistent with class counts, not share counts, before being used as `ifo:reportedShareClassCount`.

---

# Build report addendum: v0.2 (14 August 2026)

## What was fetched

| Source | Volume | Notes |
|---|---|---|
| SEC Form N-PORT structured data, 2026q2 | 440 MB zip; 5,347,869 holding rows; 6,749,116 identifier rows | Public regulatory filings |
| OpenFIGI mapping API | 5,126 ISIN lookups in 10-job keyless batches at 25 requests/minute (measured live from the server's ratelimit headers), resumable JSONL cache | FIGIs are an OMG open standard, free to store and redistribute |

## What was built

- `pipeline/harvest_nport.py`: 235,327 filing-attested (issuer LEI, ISIN) pairs from one quarter. Against the GLEIF open mapping: 47,374 agree, **185,894 are absent, 2,055 contradict** (filing and GLEIF name different LEIs for the same ISIN). 4 ISINs in filings fail their check digit. For our universe: 1,841 funds gain their first open ISIN, 937 of them ETFs, lifting open ETF ISIN coverage from 12.3% to 35.4%.
- `pipeline/resolve_figi.py`: of 5,126 fund-level ISINs, 4,423 returned a FIGI and ticker (86.3%); 2,069 joined to exactly one SEC register class by ticker within the fund, with zero ambiguous joins.
- `open-map/fund_identifier_map.csv`: 5,176 (fund, ISIN) rows, 2,186 resolved to an exact share class (42.2%), 4,471 with FIGIs. Combined resolution methods: figi-ticker-join and v0.1 unique pairing.

## What could NOT be obtained, v0.2 edition

1. **703 ISINs return no FIGI** from OpenFIGI (13.7%). A word-frequency pass over the affected fund names shows no dominant category: they are ordinary equity, bond and portfolio funds, 45 of them with ETF in the name, with only about 5 percent looking money-market or insurance-linked. Why FIGI coverage misses them is an open question this build records rather than answers.
2. **The unresolved 57.8 percent of map rows** split into: ISINs whose OpenFIGI ticker matches no register ticker in the fund (ticker drift between vendor symbology and the SEC register), funds whose classes carry no register ticker at all, and the no-FIGI set above. Each is measurable from the map file.
3. **Three further N-PORT quarters** were not harvested in this build; the backfill numbers are a floor, not a ceiling.
4. **Interpretation caveat on the 2,055 contradictions:** a filing attributing an ISIN to a different LEI than GLEIF is not automatically an error by either side; guarantor versus issuer attribution and umbrella versus series reporting both produce legitimate-looking disagreement. What the number establishes is that the two open sources cannot both be treated as ground truth simultaneously, which is precisely the kind of fact a governance layer must represent rather than resolve by fiat.

## Redistribution policy, restated

No standalone CUSIP, SEDOL, or RIC is read into the graph, stored, or emitted at any stage. ISINs come only from GLEIF's open publication and from public SEC filings; FIGIs from OpenFIGI under the open FIGI standard; everything else is US public record.
