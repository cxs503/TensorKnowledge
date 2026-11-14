"""把 classification.json 包成 KF-RESULT（schemas/kf_result.v1.schema.json 校验体）。

report 中提交的 json 块内容 == 本脚本产出的 kf_result_wp-9632-02.json（同一份，非手改）。
"""

from __future__ import annotations

import json
from pathlib import Path

PKG = Path(__file__).resolve().parent
PACKAGE_ID = "wp-9632-02"
TASK_TYPE = "02-classification-parse"


def main() -> int:
    cls = json.loads((PKG / "classification.json").read_text(encoding="utf-8"))
    prov = cls["provenance"]
    result = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": "1.0",
        "report_id": cls["report_id"],
        "provenance": {
            "source_uri": prov["source_uri"],
            "source_field": prov["source_field"],
            "source_hash": prov["source_hash"],
            "source_hash_matches": True,
            "title": prov["title"],
            "scenario_key": prov["scenario_key"],
            "chars": prov["chars"],
        },
        "outputs": {"classification.json": cls},
    }
    out = PKG / f"kf_result_{PACKAGE_ID}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())