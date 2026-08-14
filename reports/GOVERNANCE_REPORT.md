# Automated governance report: US registered fund universe

Generated 2026-08-14 by pipeline/governance_report.py, against the SEC series/class register and N-CEN quarters fetched that day and the GLEIF file dated 2026-08-08. Every figure below is computed from the graph built out of the three public source systems; nothing is hand-typed. The SEC register and the GLEIF file are fetched as "current"/"latest" and are not pinned to this date, so rerunning the pipeline today will produce different totals; the four N-CEN quarters and the N-PORT quarter used in v0.2 are pinned and reproduce exactly. See README.md "Data currency."

## 1. Universe

| Object | Count |
|---|---|
| Fund registrants | 3,304 |
| Funds (series) | 19,803 |
| Share classes | 43,344 |
| Listings (quotations) | 30,238 |
| Trading venues (MIC-resolved) | 7 |
| Identifier assertions | 126,425 |
| Graph triples | 1,292,541 |

## 2. Full-file identifier validation (GLEIF ISIN-LEI)

| Check | Result |
|---|---|
| ISIN-LEI pairs validated | 9,119,948 |
| ISIN check-digit failures | 0 |
| LEI check-digit failures | 0 |

The zero failure rates are a validated null result, not a vacuous one: the validators reject corrupted vectors in their embedded self-tests. GLEIF's published mapping file is checksum-clean at full scale, as of the 8 August 2026 file. This is a narrow claim: only ISO 6166 (ISIN) and ISO 17442/ISO 7064 MOD 97-10 (LEI) check-digit validity was tested, on every one of the 9,119,948 pairs, not a sample. Deduplication, staleness of LEI registrations, and correctness of the entity-to-ISIN mapping itself were not tested.

## 3. Checksum failures inside regulatory filings

19 distinct LEI values fail their check digit, out of 14,960 LEI values checked across four N-CEN quarters (2,743 registrant-level + 12,217 fund-level): a rate of 0.127% (~0.13%). 2 of the 19 are additionally malformed (a subset of the 19, not additional to it).

| Identifier class | Failures | Of checked | Rate | Examples (value, subject) |
|---|---|---|---|---|
| LEI | 19 | 14,960 | 0.13% | `00000000000000238096` ((not in current series/class register)); `549300QWZ7KAP3JLSX45` (GUARDIAN SEPARATE ACCT N OF THE GUARDIAN INS & ANNUITY CO); `549300GCAGWIKTPSSD37` (Teucrium Agricultural Strategy No K-1 ETF) |

## 4. Layer-3 business rules (set-based execution)

| Rule | Severity | Findings |
|---|---|---|
| R1 ETF fund with unlisted share class | Violation | 73 |
| R2 Conflicting LEI values on one fund | Violation | 0 |
| R3 Fund reports its registrant's LEI as its own | Warning | 214 |
| R3b One LEI shared by multiple sibling funds | Warning | 13 LEIs |
| R4 Identifier attached at wrong scope level | Violation | 0 |
| R5 Observed classes exceed N-CEN reported count | Warning | 2,148 |

R1 is the only Violation-severity finding in this table: an ETF's share class must, by definition, be listed somewhere, so an unlisted ETF class is a genuine defect, not a coverage gap. R3b's 13 shared LEIs include one LEI asserted by 27 distinct fund series (see `reports/findings_detail.json`, `r3b_shared_leis`); this is very likely a legitimate series-trust structure (one legal entity, one LEI, many SEC series that are not separately incorporated), which is exactly why R3 and R3b are graded Warning rather than Violation. Treat R3/R3b as a prompt to check the entity structure, not as a proven error.

## 5. Cross-system coverage and reconciliation

| Measure | Count | Share |
|---|---|---|
| Funds with no LEI from any source | 7,586 | 38.3% of funds |
| N-CEN fund reports matching the current series/class register | 7,255 of 12,217 | 59.4% |
| Fund/registrant LEIs with at least one ISIN in GLEIF | 2,109 of 14,467 | see section 6 |
| ETF funds (self-reported IS_ETF flag) whose LEI has an ISIN in GLEIF | 497 of 4,053 | 12.3% |
| Quotations with no resolvable venue in public data | 29,258 of 30,238 | 96.8% |
| Tickers quoted for more than one share class | 163 | |
| Fund-level ISINs resolved to a class by unique pairing | 259 | |

The venue row is a scope limit of the public schema, not a data-quality failure: the SEC series/class register carries no venue field at all, the only venue source is Form N-CEN's ETF-only Item E.1 table, and most of the 30,238 listings are ordinary mutual fund share classes with no trading venue concept by design. Section 7's SHACL result for this same measure is graded Warning with the message "not an error in the record," and this section should be read consistently with that.

## 6. Where US fund ISINs point

ISIN country prefixes among GLEIF-mapped ISINs issued by LEIs of US-registered funds and their registrants:

| Prefix | ISINs |
|---|---|
| US | 6,985 |
| DE | 74 |
| PR | 23 |
| CH | 15 |
| GB | 11 |
| KY | 3 |
| NL | 1 |

## 7. SHACL gate (layers 1 and 2, full graph)

pyshacl over 1,293,042 triples in 27.3s. Results by severity: Warning: 37,904, Violation: 4,986.

| Result message | Count |
|---|---|
| Quotation with no resolvable trading venue: the SEC series/class register publishes tickers venue-free, and venue resolu | 29,258 |
| Fund has no LEI assertion from any source system. Not an error in the record; a coverage gap in the identifier fabric wo | 7,586 |
| Fund must belong to exactly one registrant. | 4,962 |
| Registrant with no fund series attached: either a shell registration or a join failure between source systems. | 988 |
| Ticker symbol deviates from conventional venue symbology (letters, digits, dots; leading letter). Not fatal: ticker conv | 58 |
| LEI check digits fail ISO 7064 MOD 97-10. | 19 |
| Investment company file number outside the 811-/814- convention. | 14 |
| Listing must not name more than one trading venue. | 3 |
| LEI must be 20 characters ending in 2 check digits (ISO 17442). | 2 |

