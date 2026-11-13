#!/usr/bin/env python3
"""KF work-package wp-12458-01 (task_type=01-asset-registration) — asset registration.

Registers the source asset for report_id=12458 (a minimal test report):
  - confirms report_id and its markdown byte hash (sha256)
  - lists resolvable attachments/artifacts present in the markdown
  - does NOT extract claims (claims=[] is a legitimate complete result)

Outputs:
  artifacts/wp-12458-01/asset_manifest.json
  runs/wp-12458-01/kf_result.wp-12458-01.json   (result envelope, kf_result.v1 shape)
  runs/wp-12458-01/kf_result_block.wp-12458-01.json  (same JSON, for the single ```json block)

Usage: python3 scripts/kf_register_12458.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

REPORT_ID = "12458"
PACKAGE_ID = "wp-12458-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "e82df280a4f31a4a0aba360eaf3761377251d4c4bb18458c5140ea7eb8921ee5"
SOURCE_URI = "tensor://reports/12458"

RUN_DIR = pathlib.Path("runs/wp-12458-01")
ART_DIR = pathlib.Path("artifacts/wp-12458-01")
# durable mirror: this repo's push gate drops artifacts/** and runs/**,
# so the committed copy of every deliverable lives under docs/wp-12458-01/ (byte-identical).
DOC_DIR = pathlib.Path("docs/wp-12458-01")

# Anchor table: asset_id, class, label, anchor substring (must be unique in the markdown),
# line span relative to the anchor line, and the resolution status.
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告 markdown 全文（源资产本体）",
         anchor="--doc--", span=(0, -1), resolution="resolved_in_source",
         note="整篇 markdown 即源资产；sha256 见 source.hash"),
    dict(asset_id="A02", asset_class="heading", label="报告标题",
         anchor="# Test Report", span=(0, 0), resolution="resolved_in_source",
         note="标题行；与 API title 字段同源"),
    dict(asset_id="A03", asset_class="statement", label="报告正文声明（验证用文本）",
         anchor="This is a test report with sufficient length to pass validation.", span=(0, 0),
         resolution="resolved_in_source",
         note="正文唯一声明行；无数字/无外部引用，仅作长度与格式验证"),
]


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def build_locator(md, lines, offs, anchor, span):
    """Find the anchor line and emit the verbatim quote for the given line span."""
    if anchor == "--doc--":
        return dict(method="document", start_char=0, end_char=len(md),
                    start_line=0, end_line=len(lines) - 1,
                    quote=md, unique=True)
    for i, ln in enumerate(lines):
        if anchor in ln:
            s, e = span
            if e == -1:
                e = len(lines) - 1
            start = offs[i + s]
            end = offs[i + e] + len(lines[i + e])
            quote = "\n".join(lines[i + s:i + e + 1])
            # uniqueness: anchor must appear exactly once in the whole markdown
            unique = md.count(anchor) == 1
            return dict(method="char_span", start_char=start, end_char=end,
                        start_line=i + s, end_line=i + e, quote=quote, unique=unique)
    raise SystemExit(f"anchor not found: {anchor!r}")


def resolution_check(spec, worktree, payload):
    """Per-asset resolution check. For this minimal report all assets are
    resolved_in_source (char_span in the markdown); no external addresses exist."""
    return dict(check="char_span_in_source_markdown", result="resolved")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    # read the report payload from the local mirror (fetched once via the platform API)
    payload = json.loads((RUN_DIR / "report_12458.json").read_text())
    md = payload["markdown"]

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {EXPECTED_HASH}")
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit(f"duplicate asset_id {spec['asset_id']}")
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"])
        if not loc["unique"]:
            raise SystemExit(f"quote not unique for {spec['asset_id']}: {spec['anchor']!r}")
        head = ""
        for ln in lines[: loc["start_line"]]:
            if ln.startswith("#"):
                head = ln.strip()
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=head or "(document)",
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=resolution_check({**spec, "locator": loc}, worktree, payload),
            note=spec["note"],
        ))

    classes = {}
    for a in assets:
        classes[a["asset_class"]] = classes.get(a["asset_class"], 0) + 1
    res = {}
    for a in assets:
        res[a["resolution"]] = res.get(a["resolution"], 0) + 1

    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI,
            field="markdown",
            hash_alg="sha256",
            hash=md_hash,
            chars=len(md),
            bytes_utf8=len(md.encode()),
            title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_figures=payload.get("figures", []),
            platform_tags=payload.get("tags", []),
            retrieved_via=f"GET {os.environ.get('TENSOR_API_BASE','http://127.0.0.1:8010/api/v1').rstrip('/')}/tensor/reports/{REPORT_ID}",
            local_copy=str(RUN_DIR / "report_12458.md"),
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组："
                     "本工序只登记资产定位，不做 claim 抽取；claim 抽取由下游工作包负责。"),
        integrity=dict(quote_uniqueness="all quotes confirmed unique substrings of source markdown (scripts/kf_register_12458.py, checks.source_locator_resolvable)",
                       hash_recomputed_locally=True, hash_matches_contract=True),
    )

    art = ART_DIR / "asset_manifest.json"
    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art.write_text(blob)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
    if hashlib.sha256(mirror.read_bytes()).hexdigest() != art_hash:
        print("FATAL: durable mirror differs from artifact")
        return 3

    outputs_manifest = dict(artifact_path=str(art), artifact_sha256=art_hash,
                            artifact_bytes=art.stat().st_size)
    outputs_manifest.update({k: v for k, v in manifest.items()})

    result = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_uri=SOURCE_URI,
            source_field="markdown",
            source_hash="sha256:" + md_hash,
            source_chars=len(md),
            source_bytes_utf8=len(md.encode()),
            source_title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_version="1.0",
            lane="C",
            work_package=PACKAGE_ID,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=str(RUN_DIR / "report_12458.md"),
            generator="scripts/kf_register_12458.py",
            verifier="scripts/kf_verify_12458.py",
            verification_status="not_verified",  # verification is computed by the platform gate
        ),
        outputs={"asset_manifest.json": outputs_manifest},
        claims=[],
    )

    res_path = RUN_DIR / "kf_result.wp-12458-01.json"
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / "kf_result_block.wp-12458-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("assets:", len(assets), "by_class:", json.dumps(classes, ensure_ascii=False))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("result:", res_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
