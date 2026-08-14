"""Run the SHACL gate over the built fund graph.

Layer 1 + 2 shapes (syntax, checksum policy, hierarchy integrity) run
through pyshacl over the full graph. Layer 3 rules are executed
set-based by governance_report.py; see shapes/ifo-rules.ttl for why.

Output:
  data/build/shacl_report.ttl   - full SHACL validation report graph
  data/build/shacl_summary.json - counts by severity and message
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter

from pyshacl import validate
from rdflib import Graph, Namespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "data", "build")
SH = Namespace("http://www.w3.org/ns/shacl#")


def main() -> None:
    t0 = time.time()
    data = Graph()
    data.parse(os.path.join(BUILD, "fund_graph.ttl"), format="turtle")
    data.parse(os.path.join(ROOT, "ontology", "ifo-core.ttl"), format="turtle")
    data.parse(os.path.join(ROOT, "skos", "identifier-schemes.ttl"),
               format="turtle")
    print(f"data graph loaded: {len(data):,} triples "
          f"({time.time()-t0:.1f}s)")

    shapes = Graph()
    shapes.parse(os.path.join(ROOT, "shapes", "ifo-shapes.ttl"),
                 format="turtle")

    t1 = time.time()
    conforms, report_graph, _ = validate(
        data_graph=data,
        shacl_graph=shapes,
        inference="none",
        abort_on_first=False,
        allow_warnings=True,
    )
    elapsed = time.time() - t1
    print(f"pyshacl finished in {elapsed:.1f}s, conforms={conforms}")

    report_graph.serialize(os.path.join(BUILD, "shacl_report.ttl"),
                           format="turtle")

    by_severity: Counter = Counter()
    by_message: Counter = Counter()
    for result in report_graph.subjects(
            predicate=None, object=SH.ValidationResult):
        pass
    for result, _, _ in report_graph.triples((None, SH.resultSeverity, None)):
        sev = report_graph.value(result, SH.resultSeverity)
        msg = report_graph.value(result, SH.resultMessage)
        by_severity[str(sev).split("#")[-1]] += 1
        by_message[str(msg)[:120]] += 1

    summary = {
        "conforms": bool(conforms),
        "validation_seconds": round(elapsed, 1),
        "data_triples": len(data),
        "results_by_severity": dict(by_severity),
        "results_by_message": dict(by_message.most_common()),
    }
    with open(os.path.join(BUILD, "shacl_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2)[:3000])


if __name__ == "__main__":
    main()
