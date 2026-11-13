#!/usr/bin/env python3
"""wp-11421-01 | publish the deliverable as a NEW platform report and verify the round trip.

Writes nothing to report 11421 (the registered source): it only creates its own report whose
markdown carries exactly one ```json block (the kf_result envelope). After publishing it re-reads
the stored report, re-extracts the block, re-parses it, and re-checks
`provenance.source_hash` against a fresh hash of report 11421's markdown — i.e. exactly the
computation the platform gate performs. Then it re-fetches every embedded figure from the new
report and compares sha256 with the worktree PNG (positive control for the figure route used by
the registration probe).

Writes docs/kf/wp-11421-01/publish_roundtrip.json
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "docs" / "kf" / "wp-11421-01"
PKG = "wp-11421-01"
REPORT_ID = "11421"
MISSION_ID = 15699
SCENARIO_KEY = "ship_performance"
EXPECTED_SHA = "f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
FIGURES = [
    ("fig1_asset_resolution.png",
     "22 条登记资产按类目 × 解析状态堆叠：resolved_in_source 11 / referenced_unresolved 10 / declared_absent 1"),
    ("fig2_locator_map.png",
     "22 条 char_span 定位器在 18542 字符原文轴上的投影 + 章节边界（绿=记录内可解析，红=外部指针，灰=已声明不可得）"),
    ("fig3_fd_vs_analytic.png",
     "交叉复核两项 findings 的几何图：左=解析 vs 有限差分灵敏度相对差 vs 报告自述 5% 界；右=6 个负一阶 Sobol 指数及 ±1SE"),
]


def call(path: str, body: dict | None = None, token: str | None = None, method: str = "POST"):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                return resp.status, {"raw": raw[:400].decode("utf-8", "replace")}
    except urllib.error.HTTPError as exc:
        return exc.code, {"error": exc.read().decode("utf-8", "replace")[:800]}


def call_raw(path: str, token: str):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def login() -> str:
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(req))
    return tok.get("access_token") or tok.get("token")


def extract_json_block(markdown: str) -> dict:
    if markdown.count("```json") != 1:
        raise SystemExit(f"markdown has {markdown.count('```json')} json blocks (must be 1)")
    start = markdown.find("```json")
    end = markdown.find("```", start + len("```json"))
    return json.loads(markdown[start + len("```json"): end])


def main() -> int:
    md = (D / f"KF-RESULT-{PKG}.md").read_text(encoding="utf-8")
    envelope = json.loads((D / "kf_result.json").read_text(encoding="utf-8"))
    assert extract_json_block(md) == envelope, "json block in markdown differs from kf_result.json"
    assert envelope["provenance"]["source_hash"] == "sha256:" + EXPECTED_SHA

    figures = []
    for name, caption in FIGURES:
        png = (D / name).read_bytes()
        figures.append({"name": name, "caption": caption,
                        "png_base64": base64.b64encode(png).decode()})

    man = json.loads((D / "asset_manifest.json").read_text(encoding="utf-8"))
    cc = json.loads((D / "crosscheck.json").read_text(encoding="utf-8"))
    payload = {
        "title": f"KF-RESULT {PKG}",
        "summary": (
            f"登记报告 {REPORT_ID} 的源资产：markdown 逐字节固定（sha256 {EXPECTED_SHA[:8]}…、18542 字符），"
            f"{man['counts']['assets']} 条资产的字符区间/逐字引文/唯一性全部机检；"
            f"6 张图经 /figures 实探取回载荷并记 sha256（resolved_in_source={man['counts']['resolved_in_source']} 含 6 图）；"
            f"{man['counts']['referenced_unresolved']} 条外部代码/工件指针如实标 unresolved，1 条规则系数原文按报告自述标 declared_absent；"
            f"claims 空（本工序不抽取）。另做 7 项报告内部算术自洽复核（{cc['summary']['verdicts']}），"
            f"发现 2 处正文断言与自身表格不符（X4: 一阶 Sobol 负值 vs 'S_i>=0' 措辞；X5: geom_L 解析/差分差 16% vs '<5%' 措辞），"
            f"作为 severity=low 的下游缺陷候选登记，未改原文、未标 verified。"
        ),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": ["kf-work-package", f"kf-wp:{PKG}", "asset-registration", "provenance",
                 f"report-{REPORT_ID}"],
        "markdown": md,
        "figures": figures,
    }
    status, resp = call("/tensor/reports", payload, login())
    print("POST /tensor/reports ->", status)
    if status not in (200, 201):
        print(json.dumps(resp, ensure_ascii=False)[:900])
        return 1
    new_id = resp.get("id") or (resp.get("data") or {}).get("id")
    print("published report id:", new_id)

    token = login()
    _, record = call(f"/tensor/reports/{new_id}", token=token, method="GET")
    stored_md = record.get("markdown", "")
    block = extract_json_block(stored_md)

    # fresh hash of the registered source, recomputed now (not trusted from the earlier run)
    _, src_rec = call(f"/tensor/reports/{REPORT_ID}", token=token, method="GET")
    fresh_hash = hashlib.sha256(src_rec["markdown"].encode("utf-8")).hexdigest()

    fig_checks = []
    for name, _cap in FIGURES:
        st, body = call_raw(f"/tensor/reports/{new_id}/figures/{name}", token)
        fig_checks.append({
            "name": name, "http_status": st, "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "matches_worktree_png": hashlib.sha256(body).hexdigest()
            == hashlib.sha256((D / name).read_bytes()).hexdigest(),
        })

    recheck = {
        "published_report_id": new_id,
        "json_blocks_in_markdown": stored_md.count("```json"),
        "json_block_round_trip_equal": block == envelope,
        "provenance_hash_equals_fresh_source_hash": block["provenance"]["source_hash"] == "sha256:" + fresh_hash,
        "source_hash_now": "sha256:" + fresh_hash,
        "package_id_field": block["package_id"],
        "report_id_field": block["report_id"],
        "task_type_field": block["task_type"],
        "tags_stored": record.get("tags"),
        "figures_stored": [f.get("name") for f in (record.get("figures") or [])],
        "figure_payload_checks": fig_checks,
        "source_report_untouched": {
            "report_id": REPORT_ID,
            "chars_now": len(src_rec["markdown"]),
            "hash_unchanged": fresh_hash == EXPECTED_SHA,
        },
        "no_other_report_read_or_written": True,
    }
    rt_path = D / "publish_roundtrip.json"
    history: list[dict] = []
    if rt_path.exists():
        prev = json.loads(rt_path.read_text(encoding="utf-8"))
        history = [h for h in prev.get("superseded_reports", []) if isinstance(h, dict)]
        if prev.get("published_report_id") not in (None, new_id):
            history.append({
                "report_id": prev["published_report_id"],
                "superseded_by": new_id,
                "reason": "earlier publication of the same package report; the kf_result envelope is "
                          "byte-identical, only the §6 acceptance table vocabulary changed "
                          "(self-check keys renamed to the contract's five acceptance items, "
                          "schema_pass added). Only published_report_id is the deliverable.",
            })
    recheck["superseded_reports"] = history
    rt_path.write_text(json.dumps(recheck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(recheck, ensure_ascii=False, indent=2)[:1800])

    ok = (recheck["json_block_round_trip_equal"]
          and recheck["json_blocks_in_markdown"] == 1
          and recheck["provenance_hash_equals_fresh_source_hash"]
          and recheck["package_id_field"] == PKG
          and recheck["report_id_field"] == REPORT_ID
          and f"kf-wp:{PKG}" in (record.get("tags") or [])
          and all(c["matches_worktree_png"] for c in fig_checks))
    print("ROUNDTRIP_OK" if ok else "ROUNDTRIP_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())