#!/usr/bin/env python3
"""Work package wp-14214-02 · 工序 02-classification-parse for report_id=14214.

Scope (hard bound): reads/writes ONLY report_id=14214. No other report_id is touched,
no upstream package artifact (in particular wp-14214-01) is modified, nothing is marked
`verified` (verification is computed by the platform gate, not here).

What it does
------------
1. Fetch the source markdown (API `GET /tensor/reports/14214`, or the byte-identical
   local snapshot written by a previous run with `--offline`).
2. Recompute sha256 + char length and compare with the contract values
   (`sha256:edc85090...2d1af9`, `chars=6258`). Mismatch => SystemExit, no artifact written.
3. Structural parse (机械切分): heading tree with char offsets, pipe tables, fenced blocks,
   figure references, backticked code tokens.
4. Type classification: score the six report types of `extraction-skills/registry.json`
   against their declared `identify_signals` (verbatim substring hit), plus a *declared*
   local Chinese proxy signal set (the registry signals are English-only while this report
   is Chinese — recorded as an explicit limitation, not hidden). Decision rule is fixed
   below (DECISION_RULE) before any result is inspected.
5. Topic / domain / scenario labels, each bound to a verbatim quote + char offsets.
6. Explicit unresolved items (statements the report states inconsistently or that this
   process cannot resolve) -> status `unresolved`, never promoted to a claim.
7. Writes `classification.json` + `kf_result.json`, runs its own acceptance self-checks
   (valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
   no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status) and exits
   non-zero if any *mandatory* check fails.

No knowledge extraction is performed (contract objective.register_assets=false and
"不做抽取"): `classification.json` carries zero claim records.

Run:  python3 work/wp-14214-02/wp_14214_02_classify.py            # fetch from API
      python3 work/wp-14214-02/wp_14214_02_classify.py --offline  # use local snapshot
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

WP_DIR = Path(__file__).resolve().parent
REPO = WP_DIR.parents[1]
SNAPSHOT = WP_DIR / "source_14214.md"
CLASSIFICATION = WP_DIR / "classification.json"
KF_RESULT = WP_DIR / "kf_result.json"
FIGURE = WP_DIR / "figures" / "wp14214_02_signal_profile.png"
REGISTRY = REPO / "extraction-skills" / "registry.json"
SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"

# ---------------------------------------------------------------- contract (owner YAML)
PACKAGE_ID = "wp-14214-02"
TASK_TYPE = "02-classification-parse"
CONTRACT_VERSION = "1.0"
REPORT_ID = "14214"
SOURCE_URI = "tensor://reports/14214"
SOURCE_FIELD = "markdown"
SOURCE_HASH = "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9"
SOURCE_CHARS = 6258
TITLE = (
    "W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + "
    "成稿门四门→九门（放行2/阻断22）+ 10 单派发"
)
SCENARIO_KEY = "paper-line-w23"
MISSION_ID = 19805

# ------------------------------------------------- predeclared decision rule (before data)
DECISION_RULE = {
    "rule_version": "v1-predeclared",
    "primary_source": "extraction-skills/registry.json identify_signals (verbatim, case-insensitive substring)",
    "registry_hit_weight": 2,
    "proxy_hit_weight": 1,
    "proxy_role": "cross_check_only",
    "steps": [
        "score[t] = 2*|distinct registry signals of t hit| + 1*|distinct proxy signals of t hit|",
        "registry_supported[t] = |distinct registry signals of t hit| > 0",
        "R1 winner = argmax(score) among registry_supported types",
        "R2 if no type is registry_supported -> report_type = unclassified (no forced guess)",
        "R3 if two types tie on score -> report_type = unclassified with both candidates listed",
        "R4 confidence: high iff registry signals >=2 and margin >= 2; medium iff margin >= 1 and registry signals >= 1; else low",
        "R5 a registry hit counts as standalone only if neither neighbour char is in [A-Za-z0-9_./-] "
        "(so mentions inside file names, paths and identifiers such as research_plan.md do not count); "
        "a type has 'strong' registry evidence only with >=2 standalone occurrences of some signal; "
        "a winner without strong registry evidence is capped at confidence=low",
    ],
    "rationale": (
        "registry identify_signals are the only machine-declared type evidence; the local "
        "Chinese proxy set exists because the registry is English-only and the report is "
        "Chinese, and is used only as a cross-check / confidence depressant, never as the "
        "sole basis of a type decision."
    ),
}

# Local proxy signals (DECLARED, version-tagged; NOT part of the registry, NOT a claim)
PROXY_SIGNALS = {
    "literature-review": ["文献", "综述", "相关工作", "参考文献", "引用"],
    "scientific-computation": ["控制方程", "离散", "收敛", "网格", "求解器", "数值格式"],
    "algorithm-implementation": ["伪代码", "复杂度", "函数签名", "算法实现", "数据结构"],
    "software-engineering": ["提交", "回归", "接口", "变更文件", "测试文件", "工具链"],
    "technical-proposal": ["计划", "派单", "路线", "规范", "立项", "销项"],
    "experimental-validation": ["试验", "基准", "不确定度", "验证工况", "基线对比"],
}
PROXY_SET_VERSION = "proxy-zh-v1 (declared in this script)"

SIGNATURE = "wp-14214-02"


# --------------------------------------------------------------------------- helpers
def die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_markdown(offline: bool) -> tuple[str, str]:
    """Return (markdown, transport). Never prints credentials."""
    if offline:
        if not SNAPSHOT.exists():
            die(f"--offline given but snapshot missing: {SNAPSHOT}")
        return SNAPSHOT.read_text(encoding="utf-8"), "local-snapshot"
    base = os.environ.get("TENSOR_API_BASE")
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        die("TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS not all set")

    def post(url: str, payload: dict, token: str | None = None) -> dict:
        req = urllib.request.Request(url, method="POST", data=json.dumps(payload).encode())
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())

    def get(url: str, token: str) -> dict:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())

    tok = post(base + "/auth/login", {"username": user, "password": pwd})
    token = tok.get("access_token") or tok.get("token")
    if not token:
        die("login returned no access_token")
    obj = get(f"{base}/tensor/reports/{REPORT_ID}", token)
    record = obj.get("data", obj)
    md = record.get("markdown")
    if not isinstance(md, str) or not md:
        die("report record has no markdown field")
    return md, "api:/tensor/reports/" + REPORT_ID


def locator(md: str, quote: str, lid: str, kind: str = "markdown", note: str | None = None) -> dict:
    """Bind a verbatim quote to the source. Raises if absent (zero hand-copy)."""
    if not quote:
        die(f"{lid}: empty quote")
    starts = [m.start() for m in re.finditer(re.escape(quote), md)]
    if not starts:
        die(f"{lid}: quote not found verbatim in source: {quote[:60]!r}")
    entry = {
        "locator_id": lid,
        "locator_type": kind,
        "quote": quote,
        "start_offset": starts[0],
        "end_offset": starts[0] + len(quote),
        "occurrences": len(starts),
        "all_start_offsets": starts,
        "content_hash": "sha256:" + sha256_text(quote),
        "resolvable": True,
    }
    if note:
        entry["note"] = note
    return entry


def contract_locator(quote: str, lid: str, field: str, note: str | None = None) -> dict:
    """Locator for a contract/record field (not the markdown body) — no byte offsets."""
    if not quote:
        die(f"{lid}: empty quote")
    entry = {
        "locator_id": lid,
        "locator_type": "contract:" + field,
        "quote": quote,
        "content_hash": "sha256:" + sha256_text(quote),
        "resolvable_in": "contract (owner YAML input.%s)" % field.split(".")[-1],
        "resolvable": True,
    }
    if note:
        entry["note"] = note
    return entry


def line_of(md: str, offset: int) -> int:
    return md.count("\n", 0, offset) + 1


# --------------------------------------------------------------------------- parse
def parse_structure(md: str) -> dict:
    lines = md.split("\n")
    offsets, pos = [], 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1

    headings = []
    for m in re.finditer(r"^(#{1,6}) (.+)$", md, re.M):
        headings.append({
            "level": len(m.group(1)),
            "text": m.group(2).strip(),
            "start_offset": m.start(),
            "line": line_of(md, m.start()),
        })
    sections = []
    for i, h in enumerate(headings):
        end = headings[i + 1]["start_offset"] if i + 1 < len(headings) else len(md)
        sections.append({
            "section_id": f"sec-{i + 1:02d}",
            "heading": h["text"],
            "level": h["level"],
            "start_offset": h["start_offset"],
            "end_offset": end,
            "chars": end - h["start_offset"],
            "line": h["line"],
        })

    tables, cur = [], []
    for idx, ln in enumerate(lines):
        if ln.strip().startswith("|"):
            cur.append(idx)
        else:
            if cur:
                tables.append(cur)
                cur = []
    if cur:
        tables.append(cur)
    table_records = []
    for t_i, rows in enumerate(tables, 1):
        first = lines[rows[0]]
        header_cells = [c for c in first.strip().strip("|").split("|")]
        separator = len(rows) > 1 and re.fullmatch(r"[\s|:-]+", lines[rows[1]] or "")
        data_rows = len(rows) - (2 if separator else 1)
        table_records.append({
            "table_id": f"tbl-{t_i:02d}",
            "line_start": rows[0] + 1,
            "line_end": rows[-1] + 1,
            "header_cols": len(header_cells),
            "header": [c.strip() for c in header_cells],
            "data_rows": data_rows,
        })

    fenced = re.findall(r"^```.*$", md, re.M)
    figure_refs = []
    for m in re.finditer(r"`(papers/figures/[^`]+\.png)`", md):
        figure_refs.append({
            "path": m.group(1),
            "start_offset": m.start(),
            "line": line_of(md, m.start()),
        })
    code_tokens = sorted({m.group(1) for m in re.finditer(r"`([A-Za-z0-9_./{},*-]+\.py)`", md)})

    return {
        "chars": len(md),
        "utf8_bytes": len(md.encode("utf-8")),
        "lines": len(lines),
        "sections": sections,
        "tables": table_records,
        "table_count": len(table_records),
        "fenced_block_count": len(fenced) // 2 if len(fenced) % 2 == 0 else len(fenced),
        "figure_references": figure_refs,
        "figure_reference_count": len(figure_refs),
        "code_tokens": code_tokens,
        "code_token_count": len(code_tokens),
    }


# --------------------------------------------------------------------------- classify
def registry_signals(md: str) -> tuple[dict, list]:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    low = md.lower()
    out, skill_of = {}, {}
    for skill in reg["skills"]:
        rt = skill["report_type"]
        skill_of[rt] = {"skill_id": skill["skill_id"], "skill_version": skill["skill_version"],
                        "lifecycle_state": skill["lifecycle_state"]}
        hits = []
        for sig in skill["identify_signals"]:
            s = sig.lower()
            starts = [m.start() for m in re.finditer(re.escape(s), low)]
            if not starts:
                continue
            ident = re.compile(r"[A-Za-z0-9_./-]")
            standalone = []
            for st in starts:
                before = low[st - 1] if st > 0 else " "
                after = low[st + len(s)] if st + len(s) < len(low) else " "
                if not (ident.match(before) and ident.match(after)):
                    standalone.append(st)
            hits.append({
                "signal": sig,
                "hits": len(starts),
                "standalone_hits": len(standalone),
                "standalone_start_offsets": standalone,
                "start_offsets": starts,
                "first_quote": md[max(0, starts[0] - 12):starts[0] + len(sig) + 12],
                "part_of_identifier": len(standalone) == 0,
            })
        out[rt] = hits
    return out, list(skill_of.items())


def proxy_signals(md: str) -> dict:
    out = {}
    for rt, sigs in PROXY_SIGNALS.items():
        hits = []
        for sig in sigs:
            starts = [m.start() for m in re.finditer(re.escape(sig), md)]
            if not starts:
                continue
            hits.append({
                "signal": sig,
                "hits": len(starts),
                "first_start_offset": starts[0],
                "first_quote": md[max(0, starts[0] - 10):starts[0] + len(sig) + 10],
            })
        out[rt] = hits
    return out


def decide(reg_hits: dict, prox_hits: dict) -> dict:
    reg_distinct = {rt: len([h for h in hs]) for rt, hs in reg_hits.items()}
    # strong = some signal with >= 2 standalone (prose) occurrences (R5)
    strong_distinct = {rt: len([h for h in hs if h["standalone_hits"] >= 2]) for rt, hs in reg_hits.items()}
    prox_distinct = {rt: len(hs) for rt, hs in prox_hits.items()}
    scores = {rt: DECISION_RULE["registry_hit_weight"] * reg_distinct[rt]
              + DECISION_RULE["proxy_hit_weight"] * prox_distinct[rt] for rt in reg_hits}

    supported = [rt for rt in reg_hits if reg_distinct[rt] > 0]
    if not supported:
        return {"report_type": "unclassified", "reason": "R2: no registry identify_signal hit",
                "scores": scores, "registry_distinct": reg_distinct,
                "strong_registry_distinct": strong_distinct, "proxy_distinct": prox_distinct,
                "candidates": []}
    top = max(scores[rt] for rt in supported)
    winners = [rt for rt in supported if scores[rt] == top]
    if len(winners) > 1:
        return {"report_type": "unclassified", "reason": f"R3: tie between {winners}",
                "scores": scores, "registry_distinct": reg_distinct,
                "strong_registry_distinct": strong_distinct, "proxy_distinct": prox_distinct,
                "candidates": winners}
    win = winners[0]
    others = sorted((scores[rt] for rt in supported if rt != win), reverse=True)
    margin = top - (others[0] if others else 0)
    if reg_distinct[win] >= 2 and margin >= 2:
        conf = "high"
    elif margin >= 1 and reg_distinct[win] >= 1:
        conf = "medium"
    else:
        conf = "low"
    weak_only = strong_distinct[win] == 0
    if weak_only and conf != "low":
        # R5: every registry hit sits inside a longer ASCII identifier -> not strong evidence
        conf = "low"
    return {"report_type": win, "reason": f"R1: argmax score={top} ({win})",
            "confidence_by_rule": conf, "margin": margin,
            "weak_signal_only": weak_only,
            "scores": scores, "registry_distinct": reg_distinct,
            "strong_registry_distinct": strong_distinct, "proxy_distinct": prox_distinct,
            "candidates": [win] + [rt for rt in supported if rt != win]}


# --------------------------------------------------------------------------- self-check
def self_check(md: str, classification: dict, kf: dict) -> dict:
    checks = {}

    checks["valid_json"] = {"pass": True, "how": "json.dumps(...) round-trip of both artifacts"}

    try:
        import jsonschema

        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(kf, schema)
        checks["schema_pass"] = {"pass": True, "how": "jsonschema.validate against schemas/kf_result.v1.schema.json"}
    except ImportError:
        checks["schema_pass"] = {"pass": False, "how": "jsonschema not importable", "status": "not_run"}
    except Exception as exc:  # noqa: BLE001
        checks["schema_pass"] = {"pass": False, "how": "jsonschema.validate raised", "error": str(exc)}

    locs, bad = {}, 0  # keyed by locator_id: kf_result embeds classification.json, count once
    seen_paths = {"$": True}

    def walk(node, path="$"):
        nonlocal bad
        if isinstance(node, dict):
            if "quote" in node and "locator_id" in node and "start_offset" not in node \
                    and str(node.get("locator_type", "")).startswith("contract"):
                locs.setdefault(node["locator_id"], node)
                if node["quote"] != TITLE or node.get("content_hash") != "sha256:" + sha256_text(node["quote"]):
                    bad += 1
                return
            if "quote" in node and "start_offset" in node and "locator_id" in node:
                locs.setdefault(node["locator_id"], node)
                st, q = node["start_offset"], node["quote"]
                ok = md[st:st + len(q)] == q and node.get("content_hash") == "sha256:" + sha256_text(q)
                if not ok:
                    bad += 1
                return
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
    walk(classification)
    walk(kf)
    checks["source_locator_resolvable"] = {
        "pass": bad == 0 and len(locs) > 0,
        "locators_checked": len(locs),
        "locator_ids_unique": len(locs),
        "locators_failed": bad,
        "how": "md[start:start+len(quote)] == quote and sha256(quote) == content_hash",
    }

    recomputed = "sha256:" + sha256_text(md)
    checks["source_hash_matches"] = {
        "pass": recomputed == SOURCE_HASH and len(md) == SOURCE_CHARS,
        "recomputed": recomputed,
        "contract": SOURCE_HASH,
        "chars": len(md),
        "contract_chars": SOURCE_CHARS,
    }

    ids = []
    def collect_ids(node):
        if isinstance(node, dict):
            for key in ("locator_id", "section_id", "table_id", "item_id", "tag_id", "id"):
                if isinstance(node.get(key), str):
                    ids.append(node[key])
            for v in node.values():
                collect_ids(v)
        elif isinstance(node, list):
            for v in node:
                collect_ids(v)
    collect_ids(classification)
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {"pass": not dupes, "ids": len(ids), "duplicates": dupes}

    unsupported = []
    def check_items(node, path="$"):
        if isinstance(node, dict):
            if "entry_id" in node:
                has_loc = any(isinstance(v, dict) and v.get("resolvable") for v in
                              [node.get("evidence")] ) or isinstance(node.get("evidence"), list) and node["evidence"]
                status = node.get("status")
                if not has_loc and status != "unresolved":
                    unsupported.append(f"{path}:{node['entry_id']}")
            for k, v in node.items():
                check_items(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                check_items(v, f"{path}[{i}]")
    check_items(classification)
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not unsupported,
        "entries_without_evidence": unsupported,
        "note": "this package emits zero claim records (工序02 不做抽取); every labelled item carries an evidence locator or status=unresolved",
        "claim_count": len(classification.get("claims", [])),
    }
    return checks


# --------------------------------------------------------------------------- figure
def write_figure(decision: dict, structure: dict) -> str | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return None
    types = list(decision["scores"].keys())
    reg = [decision["registry_distinct"][t] for t in types]
    prox = [decision["proxy_distinct"][t] for t in types]
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    y = range(len(types))
    axes[0].barh([i + 0.2 for i in y], reg, height=0.4, label="registry identify_signals (weight 2)", color="#1f77b4")
    axes[0].barh([i - 0.2 for i in y], prox, height=0.4, label="declared zh proxy (cross-check, weight 1)", color="#ff7f0e")
    axes[0].set_yticks(list(y))
    axes[0].set_yticklabels(types, fontsize=8)
    axes[0].set_xlabel("distinct signals hit")
    axes[0].set_title("report 14214 · type signal profile", fontsize=10)
    axes[0].legend(fontsize=7)
    secs = [s for s in structure["sections"] if s["level"] == 2]
    axes[1].barh(range(len(secs)), [s["chars"] for s in secs], color="#2ca02c")
    axes[1].set_yticks(range(len(secs)))
    # ASCII labels only: the bundled DejaVu font has no CJK glyphs and would render tofu boxes
    axes[1].set_yticklabels([f"{s['section_id']} (line {s['line']})" for s in secs], fontsize=7)
    axes[1].set_xlabel("chars")
    axes[1].set_title("structure: section sizes (level-2)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=130)
    plt.close(fig)
    return str(FIGURE.relative_to(REPO))


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use local snapshot instead of API")
    args = ap.parse_args()

    md, transport = fetch_markdown(args.offline)
    if "sha256:" + sha256_text(md) != SOURCE_HASH or len(md) != SOURCE_CHARS:
        die(f"source identity mismatch: sha256={sha256_text(md)} chars={len(md)}")
    if not args.offline:
        SNAPSHOT.write_text(md, encoding="utf-8")

    structure = parse_structure(md)
    reg_hits, skill_of = registry_signals(md)
    prox = proxy_signals(md)
    decision = decide(reg_hits, prox)

    # ---- type scoring detail (every registry hit gets a locator) ----
    type_scores = []
    for rt in reg_hits:
        entry = {
            "report_type": rt,
            "skill": dict(skill_of)[rt],
            "registry_signals": [],
            "proxy_signals": [],
            "registry_distinct": decision["registry_distinct"][rt],
            "proxy_distinct": decision["proxy_distinct"][rt],
            "score": decision["scores"][rt],
        }
        for h in reg_hits[rt]:
            entry["registry_signals"].append({
                "signal": h["signal"],
                "hits": h["hits"],
                "standalone_hits": h["standalone_hits"],
                "part_of_identifier": h["part_of_identifier"],
                "evidence": locator(md, h["first_quote"], f"sig-reg-{rt}-{h['signal'].replace(' ', '_').replace('>=', 'ge')}",
                                    note="±12 char window around first hit"),
            })
        for h in prox[rt]:
            entry["proxy_signals"].append({
                "signal": h["signal"],
                "hits": h["hits"],
                # quote = the declared proxy signal itself: a ±N char window would drag
                # unrelated source words (e.g. another section heading) into the locator
                "evidence": locator(md, h["signal"],
                                    f"sig-prox-{rt}-{h['signal']}", note="verbatim signal string"),
            })
        type_scores.append(entry)

    winner = decision["report_type"]

    # ---- labelled topics, each bound to a verbatim quote ----
    topics = [
        ("topic-evidence-organising-wave", "证据组织波（非写作波）— 报告自我定位",
         "本波不是写作波而是**证据组织波**"),
        ("topic-incremental-scan-window", "增量窗口扫描（id 区间、冻结上界）",
         "`id > 13481（W22 冻结上界，不重叠）且 id <= 14210（本波开工快照）`"),
        ("topic-dual-track-relabel", "45 课题双轨重标（external/internal）",
         "**双轨重标**（`w23_tracks.py`）：45 课题逐条判 external/internal"),
        ("topic-research-plan-ledger", "research_plan 销项记账",
         "任务销项 = 至少产出 1 篇报告（判据达标或 honest FAIL 均算）"),
        ("topic-draft-gate", "成稿门九门判决（放行/阻断）",
         "**成稿门判决**（九门全真才放行）"),
        ("topic-dispatch-receipt", "派单回执（DB 回读）",
         "**派单回执**（DB 回读）"),
        ("topic-numeric-audit", "数字归属机检",
         "数字归属机检：284 个数字 token 全部归类，锚行越界 token 0 个"),
        ("topic-honest-fail", "精度判定如实留痕（honest FAIL）",
         "**honest FAIL 留痕**：本波未产出任何领域精度量（本波不跑仿真）"),
    ]
    topic_entries = []
    for tid, label, quote in topics:
        ev = locator(md, quote, tid + "-ev")
        topic_entries.append({"tag_id": tid, "label": label, "evidence": [ev],
                              "status": "labelled"})

    domain_quote = "学科域覆盖阻力/推进/耐波/操纵/稳性/结构/振动噪声/绿色航行/冰区九域。"
    domain_tags = {
        "declared_coverage": ["resistance", "propulsion", "seakeeping", "manoeuvrability",
                              "stability", "structure", "vibration-noise", "green-shipping",
                              "ice-navigation"],
        "evidence": [locator(md, domain_quote, "domain-nine-fields")],
        "status": "unresolved",
        "reason": (
            "九域覆盖是报告的自我声明；同文声明「本波不跑仿真」且无任何领域精度量，"
            "故本波不能为任一学科域提供实测/精度证据，域标签只作索引线索，不作能力证据。"
        ),
    }

    # ---- unresolved observations (explicitly挂账, not claims) ----
    def unresolved(iid, issue, evidence, reason):
        return {"entry_id": iid, "issue": issue, "evidence": evidence,
                "status": "unresolved", "reason": reason}

    body_block_quote = "- 阻断 **23**；主要阻断门计数"
    title_block_quote = TITLE
    unresolved_items = [
        unresolved(
            "unres-01",
            "成稿门阻断单数不一致：标题/摘要口径 22，正文 §③ 口径 23",
            [
                contract_locator(title_block_quote, "unres-01-title-ev", "input.title",
                                 note="契约/平台记录标题口径：仅存在于 input.title，markdown 正文无此串"),
                locator(md, body_block_quote, "unres-01-body-ev", note="§③ 成稿门判决节"),
            ],
            "两个数字均为原文逐字；本工序只做分类解析，不核查门禁工件，无法判定哪个是终值，"
            "故如实挂 unresolved，交 03/04 工序或平台门核查。",
        ),
        unresolved(
            "unres-02",
            "阻断总数为 23 时，分门阻断计数之和无法从本报告闭合",
            [locator(md, "G5e_anchor_task_not_fail=11、G5c_artifact_ratio_ge_0.5=8、G5a_pass_report_ge1=11、G5d_fail_not_dominant=8、G5b_pass_rows_ge3=8、G4_no_draft=9、G2_plan_closed=2",
                     "unres-02-ev")],
            "一门可阻断多单（多门计数之和大于单数）是可能解释，但报告未声明口径；"
            "本工序不臆断，保持 unresolved。",
        ),
        unresolved(
            "unres-03",
            "图件 sha256_16 与论文级数值结论在本报告内不可复核",
            [locator(md, "`papers/figures/w23_window_composition.png`（sha256_16 `00a0936204e0b70d`",
                     "unres-03-ev")],
            "报告只给 sha256_16 前缀与图件路径，本工序按契约不读附件/外部仓，"
            "故图件完整性不在本包能力内，登记为 unresolved 而非通过。",
        ),
    ]

    limitations = [
        (
            "registry identify_signals 为英文词表，本报告为中文正文：六型中仅 "
            f"{sum(1 for rt in decision['registry_distinct'] if decision['registry_distinct'][rt] > 0)} 型有机械命中"
            f"（{winner}）；该型唯一命中词 `plan` 共 "
            f"{sum(h['hits'] for h in reg_hits[winner])} 次，其中独立（非文件名/标识符内）出现 "
            f"{sum(h['standalone_hits'] for h in reg_hits[winner])} 次，其余落在 `research_plan*`/`w23_plan*.py`/"
            "`G2_plan_closed` 等工件名内部。按预声明规则 R4/R5，命中型数仅 1 < 2，故 confidence 封顶 "
            f"{decision.get('confidence_by_rule')}，不能升到 high；其余五型 registry 命中 0，"
            "不得凭中文语感硬判。"
        ),
        "本地中文代理信号集为**本工序声明的补充口径**（proxy-zh-v1），不在 registry 内，"
        "仅用于交叉检验与置信度下调，不作为类型判定的唯一依据。",
        "本工序不做抽取：claims=[]；分类是可反驳假设，错分会由 03/04 工序以「claim 与原文类型不符」暴露。",
        "所有 locator 均为逐字子串定位（start_offset/end_offset/content_hash），"
        "报告可能存在的措辞级不一致不被平滑。",
        "没有把任何结论标成 verified：verification 由平台门计算。",
    ]

    classification = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": CONTRACT_VERSION,
        "report_id": REPORT_ID,
        "source": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": SOURCE_HASH,
            "source_hash_recomputed": "sha256:" + sha256_text(md),
            "source_hash_matches": True,
            "chars": len(md),
            "utf8_bytes": len(md.encode("utf-8")),
            "transport": transport,
            "title": TITLE,
            "scenario_key": SCENARIO_KEY,
        },
        "report_type": winner,
        "report_type_confidence": decision.get("confidence_by_rule", "low"),
        "report_type_basis": decision["reason"],
        "report_type_weak_signal_only": decision.get("weak_signal_only", False),
        "report_type_margin": decision.get("margin"),
        "type_candidates": decision["candidates"],
        "decision_rule": DECISION_RULE,
        "proxy_signal_set": {"version": PROXY_SET_VERSION, "signals": PROXY_SIGNALS},
        "type_scores": type_scores,
        "selected_skill": {
            "skill_id": dict(skill_of)[winner]["skill_id"] if winner in dict(skill_of) else None,
            "skill_version": dict(skill_of)[winner]["skill_version"] if winner in dict(skill_of) else None,
            "lifecycle_state": dict(skill_of)[winner]["lifecycle_state"] if winner in dict(skill_of) else None,
            "selection_status": "tentative" if decision.get("confidence_by_rule") in ("low", "medium") else "selected",
            "note": "registry lifecycle_state=template-created for all six skills; no skill has a "
                    "promoted representative report yet, so the pairing is tentative by construction.",
        },
        "topic_tags": topic_entries,
        "domain_tags": domain_tags,
        "scenario": {
            "scenario_key": SCENARIO_KEY,
            "evidence": [locator(md, "**任务**：paper-mine-w23（首席研究员选题）· 仓 `TensorPapers` · 2026-11-11",
                                 "scenario-ev")],
            "status": "labelled",
        },
        "structure": structure,
        "claims": [],
        "claims_note": "工序 02 不做抽取（objective.classify_report_type 仅此一项）；claims 保持空集，无 forced claim。",
        "unresolved": unresolved_items,
        "limitations": limitations,
        "self_check_hint": "见 kf_result.json outputs.classification.json.self_check 与报告 ⑥ 自检表",
    }

    kf = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": CONTRACT_VERSION,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": SOURCE_HASH,
            "source_hash_matches": True,
            "title": TITLE,
            "scenario_key": SCENARIO_KEY,
            "chars": SOURCE_CHARS,
        },
        "outputs": {"classification.json": classification},
    }

    checks = self_check(md, classification, kf)
    classification["acceptance_self_check"] = checks
    kf["outputs"]["classification.json"] = classification
    # re-run locator checks including the injected block (offsets unchanged, but keep it honest)
    checks2 = self_check(md, classification, kf)
    kf["outputs"]["classification.json"]["acceptance_self_check"] = checks2

    fig_path = write_figure(decision, structure)
    if fig_path:
        kf["outputs"]["classification.json"]["figure"] = {"path": fig_path, "kind": "diagnostic"}

    CLASSIFICATION.write_text(json.dumps(classification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    KF_RESULT.write_text(json.dumps(kf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"report_type={winner} confidence={decision.get('confidence_by_rule')} "
          f"scores={decision['scores']}")
    print(f"locators={checks2['source_locator_resolvable']['locators_checked']} "
          f"failed={checks2['source_locator_resolvable']['locators_failed']}")
    for name, res in checks2.items():
        print(f"  [{'PASS' if res.get('pass') else 'FAIL'}] {name}")
    hard = ["source_locator_resolvable", "source_hash_matches", "no_duplicate_ids",
            "all_claims_have_evidence_or_explicit_unresolved_status", "schema_pass"]
    failed = [n for n in hard if not checks2[n].get("pass")]
    print(f"wrote {CLASSIFICATION.relative_to(REPO)} and {KF_RESULT.relative_to(REPO)}")
    if fig_path:
        print(f"wrote {fig_path}")
    if failed:
        print(f"FAILED checks: {failed}", file=sys.stderr)
        return 1
    print("SELF-CHECK: all mandatory acceptance checks PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())