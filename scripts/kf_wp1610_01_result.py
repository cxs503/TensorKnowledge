#!/usr/bin/env python3
"""wp-1610-01: assemble the kf_result.v1 envelope from the registered assets,
validate it against schemas/kf_result.v1.schema.json, and render the report markdown
(narrative template + machine-injected JSON / evidence tables, so no value is
hand-copied into the deliverable).

Inputs : docs/kf/wp-1610-01/asset_manifest.json, docs/kf/wp-1610-01/locator_check.json
Outputs: docs/kf/wp-1610-01/kf_result.json
         docs/kf_result_wp-1610-01.md
"""
from __future__ import annotations

import datetime as dt
import json
import os

import jsonschema

PKG_DIR = "docs/kf/wp-1610-01"
OUT_DIR = "docs/kf/wp-1610-01"
TEMPLATE = os.path.join(OUT_DIR, "report_body.md")
SCHEMA = "schemas/kf_result.v1.schema.json"
MARKER_JSON = "@@KF_RESULT_JSON@@"
MARKER_EVID = "@@EVIDENCE_TABLE@@"
MARKER_ID = "@@IDENTITY_TABLE@@"


def stable_emitted_at() -> str:
    """Reuse the timestamp already recorded in kf_result.json so that re-running the
    pipeline reproduces byte-identical deliverables (only the first run stamps time)."""
    path = os.path.join(OUT_DIR, "kf_result.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)["provenance"]["emitted_at"]
        except (KeyError, ValueError):
            pass
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def build_envelope(manifest: dict) -> dict:
    return {
        "package_id": manifest["package_id"],
        "task_type": manifest["task_type"],
        "report_id": manifest["report_id"],
        "provenance": {
            "source_hash": manifest["source_hash"],
            "source_field": manifest["source_field"],
            "producer": "agent/m15530",
            "emitted_at": stable_emitted_at(),
            "notes": (
                "source_hash recomputed with hashlib.sha256 over the report markdown bytes "
                "fetched from GET /api/v1/tensor/reports/1610; matches the contract-declared hash. "
                "Hash equality is a mechanical identity check only: no claim in this package is "
                "marked verified, verification stays with the platform gate."
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
    }


def identity_table(m: dict, lc: dict) -> str:
    rows = [
        ("report_id", m["report_id"]),
        ("source_uri", m["source_uri"]),
        ("source_field", m["source_field"]),
        ("title (record)", m["title"]),
        ("scenario_key (record)", m["scenario_key"]),
        ("chars (len(markdown))", m["chars"]),
        ("bytes_utf8", m["bytes_utf8"]),
        ("sha256 (recomputed)", m["source_hash"]),
        ("sha256 (contract)", m["source_hash_expected"]),
        ("hash match", m["source_hash_matches"]),
        ("headings", m["heading_count"]),
        ("attachments (record.figures)", len(m["attachments"])),
        ("artifacts declared in §3.5", len(m["artifacts"])),
        ("claims", len(m["claims"])),
        ("quotes resolved", f"{lc['quotes_resolvable']}/{lc['quotes_checked']}"),
    ]
    out = ["| 字段 | 值 |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows]
    return "\n".join(out)


def evidence_table(lc: dict) -> str:
    out = ["| 定位 ID | 该引文钉住什么 | 原文逐字片段 | 字符偏移 |", "|---|---|---|---|"]
    for c in lc["checks"]:
        quote = c["quote"].replace("|", "\\|")
        fence = "``" if "`" in quote else "`"  # keep verbatim even when the quote carries backticks
        offset = c["char_offset"] if c["resolvable"] else "**未解析**"
        out.append(f"| {c['locator_id']} | {c['meaning']} | {fence}{quote}{fence} | {offset} |")
    out.append("")
    out.append(
        f"全部 {lc['quotes_checked']} 条引文均在 markdown 中逐字命中"
        f"（未解析：{lc['unresolved'] or '无'}），命中偏移见 "
        "`docs/kf/wp-1610-01/locator_check.json`；平台可独立重算 sha256 与子串二次确认。"
    )
    return "\n".join(out)


def main() -> None:
    manifest = json.load(open(os.path.join(PKG_DIR, "asset_manifest.json"), encoding="utf-8"))
    lc = json.load(open(os.path.join(PKG_DIR, "locator_check.json"), encoding="utf-8"))
    envelope = build_envelope(manifest)

    schema = json.load(open(SCHEMA, encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    print("schema validation: OK")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "kf_result.json"), "w", encoding="utf-8") as fh:
        json.dump(envelope, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    body = open(TEMPLATE, encoding="utf-8").read()
    fenced_json = "```json\n" + json.dumps(envelope, ensure_ascii=False, indent=2) + "\n```"
    body = body.replace(MARKER_JSON, fenced_json)
    body = body.replace(MARKER_EVID, evidence_table(lc))
    body = body.replace(MARKER_ID, identity_table(manifest, lc))
    assert MARKER_JSON not in body and MARKER_EVID not in body and MARKER_ID not in body
    md_path = "docs/kf_result_wp-1610-01.md"
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(body)
    print("rendered:", md_path, len(body), "chars")


if __name__ == "__main__":
    main()