#!/usr/bin/env python3
"""Wrap review_report.json in the kf_result.v1 envelope (the only result channel)."""
import hashlib
import json
from pathlib import Path

W = Path("work/wp-5559-04")
src = (W / "source_5559.md").read_bytes()
review = json.loads((W / "review_report.json").read_text(encoding="utf-8"))
contract_hash = "sha256:3b04e96a056a9d8ba1b7861452dd5c2b3ce74777654154c7cc91e41f4e0b74ed"
h = "sha256:" + hashlib.sha256(src).hexdigest()
assert h == contract_hash, (h, contract_hash)

result = {
    "package_id": "wp-5559-04",
    "task_type": "04-independent-review",
    "report_id": "5559",
    "provenance": {
        "source_uri": "tensor://reports/5559",
        "source_field": "markdown",
        "source_hash": h,
        "producer": "kf-worker/m15833",
        "notes": "hash recomputed by the reviewer from GET /api/v1/tensor/reports/5559 field `markdown`; "
                 "independent GET, not copied from the upstream package. Review context = report markdown + "
                 "upstream wp-5559-01 structured artifacts; producer narrative and producer scripts excluded.",
    },
    "outputs": {"review_report.json": review},
}
(W / "kf_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"source_hash": h, "outputs": list(result["outputs"]), "verdict": review["verdict"]}, ensure_ascii=False))
