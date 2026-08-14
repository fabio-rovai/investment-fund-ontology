# Changelog

## v0.2.0 (2026-08-14)

The open fund identifier map: closing the ISIN-to-share-class hop and
backfilling the open fabric, with open data only.

- **New: `pipeline/resolve_figi.py`.** Resolves fund-level ISINs to share
  classes via the OpenFIGI mapping API (ISIN to ticker + share-class FIGI,
  joined to the SEC register ticker within the same fund). FIGIs are an OMG
  open standard, free to store and redistribute; no CUSIP is requested,
  stored, or emitted. Keyless-tier paced (10-job batches, 25 requests/min,
  measured live); resumable JSONL cache.
- **New: `pipeline/harvest_nport.py`.** Harvests (issuer LEI, ISIN) pairs
  from SEC Form N-PORT structured filings (public record) and measures
  them against the GLEIF open mapping, globally and for the fund universe.
- **New findings** (2026q2 N-PORT quarter, GLEIF file of 2026-08-08):
  235,327 filing-attested pairs, of which 185,894 are absent from the
  GLEIF open mapping and 2,055 contradict it; 4 ISINs in filings fail
  their check digit; 937 ETFs gain their first open ISIN, lifting open
  ETF ISIN coverage from 12.3% to 35.4% from one quarter of filings.
- **New: open fund identifier map export** (`open-map/`): 5,176 (fund,
  ISIN) rows, 4,471 with FIGIs (86.4%), 2,186 resolved to an exact SEC
  share class (42.2%, zero ticker conflicts), 8.4x the v0.1
  licensed-data-free resolution rate.
- **Project scaffolding:** offline test suite (`tests/`), GitHub Actions
  CI on Python 3.11/3.12, CONTRIBUTING.md with the licensed-data policy,
  CITATION.cff, issue templates for finding disputes and registry
  additions.
- Registry: OpenFIGI and SEC N-PORT added as source-system concepts;
  `ifo:FIGI` identifier class added to the core ontology.

## v0.1.0 (2026-08-14)

First full-universe build. OWL 2 core ontology (Registrant > Fund >
ShareClass > Listing, reified identifiers), 20-scheme SKOS registry over
six markets, three-layer SHACL, three-source pipeline (SEC series/class,
Form N-CEN, GLEIF ISIN-LEI), 1.29M triples, automated governance report,
eight quantified findings, FIBO alignment with live-verified IRIs.
