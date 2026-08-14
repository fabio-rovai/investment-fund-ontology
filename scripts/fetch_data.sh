#!/usr/bin/env bash
# Fetch the three public source datasets the pipeline builds from.
# Total download ~70 MB compressed; the GLEIF file expands to ~310 MB.
#
# Sources and licences:
#   SEC data: US government work, public domain.
#   GLEIF ISIN-LEI mapping: published by GLEIF free of charge for
#   public use; see gleif.org terms.
#
# SEC asks automated clients to identify themselves; set a real
# contact in UA before running.
set -euo pipefail
cd "$(dirname "$0")/../data"

UA="investment-fund-ontology research client (set-your-email-here)"

echo "1/3 SEC Investment Company Series and Class dataset"
curl -sL -A "$UA" -o sec_series_class_current.csv \
  "https://www.sec.gov/files/investment/data/other/investment-company-series-and-class-information/investment_company_series_class.csv"

echo "2/3 SEC Form N-CEN structured data, four quarters"
for q in 2025q3 2025q4 2026q1 2026q2; do
  curl -sL -A "$UA" -o "${q}_ncen.zip" \
    "https://www.sec.gov/files/dera/data/form-n-cen-data-sets/${q}_ncen.zip"
  mkdir -p "ncen/${q}"
  unzip -o -q "${q}_ncen.zip" -d "ncen/${q}"
  sleep 1
done

echo "3/3 GLEIF ISIN-to-LEI relationship file"
echo "GLEIF publishes a new file id per issue; take the newest link from"
echo "https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files"
echo "The build of 2026-08-14 used the 2026-08-08 file."
LATEST=$(curl -s -A "Mozilla/5.0" \
  "https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files" \
  | grep -oE 'https://mapping.gleif.org/api/v2/isin-lei/[a-f0-9-]+/download' | head -1)
curl -sL -A "$UA" -o isin_lei.zip "$LATEST"
unzip -o -q isin_lei.zip

echo "4/4 (v0.2) SEC Form N-PORT structured data, latest quarter (~440 MB)"
curl -sL -A "$UA" -o 2026q2_nport.zip \
  "https://www.sec.gov/files/dera/data/form-n-port-data-sets/2026q2_nport.zip"
mkdir -p nport/2026q2
unzip -o -q 2026q2_nport.zip -d nport/2026q2

echo "done:"
ls -la
