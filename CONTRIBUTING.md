# Contributing

Contributions are welcome, with the same evidence bar the repo holds itself to.

## Ground rules

1. **Real data, verified claims.** Every asserted mapping, IRI, or format
   claim must be verifiable: external IRIs fetched and confirmed before
   assertion, identifier formats traced to a standard or explicitly marked
   as convention. PRs that add unverified assertions will be asked for
   evidence, not merged on plausibility.
2. **No licensed identifier data.** Do not contribute bulk CUSIP, SEDOL,
   RIC, or other licensed identifier instances, including scraped ones.
   FIGIs, LEIs, GLEIF-published ISINs, and identifiers from public SEC
   filings are fine. If in doubt, open an issue first.
3. **Honesty over coverage.** A gap stated plainly beats a guessed value.
   The scheme registry marks conventions as conventions; keep that
   discipline.
4. **Tests must pass offline.** `pytest tests/` runs without network or
   the large source downloads; anything you add to ontology/, skos/,
   shapes/, queries/ or examples/ is covered by the artifact tests.

## Useful contributions

- Market extensions: FCA (UK), CBI (IE), ASIC/APIR (AU), CSA (CA), CNBV
  (MX) register ingestion, following the pipeline pattern (one module,
  one named graph, one source-system concept).
- Additional identifier schemes for the registry, with sources.
- SHACL business rules with a stated governance rationale.
- Corrections: if a finding number does not reproduce, that is a bug of
  the first order; please open an issue with your run's stats JSON.

## Workflow

Fork, branch, `pytest tests/`, PR with a description that states what
was verified and how. CI runs the offline suite on 3.11 and 3.12.
