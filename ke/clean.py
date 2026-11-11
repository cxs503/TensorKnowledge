#!/usr/bin/env python3
"""KBM-CLEAN-W1 —— 知识语料清洗层（确定性 / 全量覆盖 / 剔除分类账可复算）.

三个受管面（同一规则引擎，两个适配器）：

  1. ``--scope files``  ：仓内知识语料（默认 ``knowledge/``）——逐文件判定
  2. ``--scope reports``：KBM 抽取的源语料（tensor_reports 已发布报告）——逐报告判定

产出（每面一套）::

    <out>/ledger.jsonl   每一条 = 一个语料单元（含 kept），含 sha256/bytes/decision/reasons
    <out>/summary.json   汇总数字（全部由 ledger 派生，无手抄）
    <out>/report.md      人类可读报告

核心不变量（``ke.clean verify`` 机器复核）：

  A. 覆盖率  : len(ledger) == 语料单元总数（逐条枚举，无抽样、无遗漏）
  B. 字节账  : sum(ledger.bytes) == 语料总字节数
  C. 判定账  : kept + repaired + excluded == len(ledger)，且 reason 分项之和 == excluded
  D. 输出账  : sum(ledger.bytes for decision != excluded) == 保留语料字节
  E. 复算账  : summary.json 中每个数字 == 由 ledger.jsonl 重新聚合的值
  F. 快照账  : snapshot_digest == sha256(sorted "key:sha256" 行) —— 账本与语料快照互相锚定

设计依据（方法谱系，见 docs/kbm-clean-w1.md §1）：
  - ISO/IEC 25012:2008 数据质量维度（完整性/一致性/可追溯性）
  - Unicode UAX #15 (NFC) 与 RFC 3629 (UTF-8) 文本规范化
  - gitleaks/trufflehog 家族的「正则+熵」秘密扫描（此处仅正则族，避免高熵假阳性）
  - OpenRefine 的 key-collision/去重范式（此处用内容 sha256 精确去重，不做模糊聚类）

规则表见 RULES；每条规则规则号稳定，改动需改版本号 LEDGER_VERSION。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

LEDGER_VERSION = "clean-w1/v1"

# 判定词表（闭合集，写入 ledger 校验）
DEC_KEPT = "kept"
DEC_REPAIRED = "repaired"
DEC_EXCLUDED = "excluded"
DECISIONS = (DEC_KEPT, DEC_REPAIRED, DEC_EXCLUDED)

# 剔除理由码（闭合集）：X01..X08
REASON_CODES = {
    "X01_non_utf8": "文本不可按 UTF-8 解码（非文本二进制资产或损坏编码）",
    "X02_empty_or_stub": "去壳后有效正文 < 阈值（空壳/占位文件）",
    "X03_duplicate": "内容 sha256 与更早的规范条目相同（冗余副本）",
    "X04_secret_leak": "命中凭据/密钥正则族（明细仅留 span 与 token 摘要，不留原文）",
    "X05_boilerplate_only": "扣除跨文档模板行后残余 < 阈值（纯模板无实质内容）",
    "X06_process_log": "运营/流程日志型文本：流程词命中且知识标记族 < 阈值",
    "X07_invalid_json": "声明为 JSON 但无法解析（结构损坏）",
}

# 主因码优先级（固定顺序；一条剔除记录只有一个主因，账本按主因加总==剔除总数）
REASON_PRIORITY = ("X04_secret_leak", "X01_non_utf8", "X02_empty_or_stub",
                   "X07_invalid_json", "X03_duplicate", "X06_process_log",
                   "X05_boilerplate_only")

# 修复动作码（闭合集）：R01..R05
REPAIR_CODES = {
    "R01_strip_bom": "去除 UTF-8 BOM",
    "R02_crlf_to_lf": "CRLF -> LF 行尾统一",
    "R03_trailing_ws": "逐行去除行尾空白",
    "R04_unicode_nfc": "Unicode NFC 规范化",
    "R05_blank_collapse": "≥3 连续空行折叠为 1 空行",
}

# ---------------------------------------------------------------------------
# 阈值（预注册；改阈值=改判据，需在 docs 记 Delta）
# ---------------------------------------------------------------------------
TH = {
    "file_min_bytes": 40,        # 文件面：空壳阈值
    "file_text_ext": {".md", ".json", ".txt", ".py", ".sh", ".input", ".yaml", ".yml", ".csv"},
    "report_min_chars": 120,     # 报告面：空壳阈值
    "boilerplate_line_frac": 0.20,
    "boilerplate_min_docs": 20,   # 模板扣除的语料规模下限（预注册）  # 跨文档出现率 >= 20% 的行视为模板行
    "boilerplate_min_len": 8,
    "boilerplate_residual_chars": 200,
    "process_knowledge_min": 2,  # 知识标记族命中数下限（低于则判流程日志；v2 由 3 收紧到 2 并加结构护栏）
    "boilerplate_cov_min": 0.80,  # v2：模板行必须占去壳字符 >= 80% 才可判纯模板
    "report_max_scan": 200000,   # 单条报告正则扫描窗口（字符）
}

PROCESS_TOKENS = (
    # 只保留"编排/治理语义"专指词；v1 曾含 report/qa/audit/ledger/board 等泛词，
    # 抽检证明它们零区分度（技术报告标题同样含"报告/审计/账本"）→ v2 剔除。
    "仲裁", "播种", "提案", "战役", "自主续航", "派单", "派发", "巡检",
    "值守", "舰队", "plan ", "campaign", "governance", "autonomy", "arbit",
    "handoff", "proposal", "wave ", "board", "watchdog", "pull request",
    "merge #", "pr #", "返工", "补报", "接棒", "欠账清理",
)

UNITS_RE = re.compile(r"(N·m|kN|m/s|Pa|kg/m³|Hz|°C|m²|kg|mm|rad|MPa|kW|knot|rpm)\b")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.M)
EQ_RE = re.compile(r"\\frac|\\partial|\\sum|\$\$")

KNOWLEDGE_MARKERS = {
    "math": re.compile(r"\\frac|\\partial|\\sum|\$\$|\$[^$\n]{3,}\$"),
    "table": re.compile(r"^\s*\|.*\|\s*$", re.M),
    "error": re.compile(r"误差|相对偏差|relative error|deviation|order of accuracy"),
    "quantity": re.compile(r"(N·m|kN|m/s|Pa|kg/m³|Hz|°C|m²|kg|mm|rad)\b"),
    "citation": re.compile(r"https?://|doi:|arXiv:|参考文献|reference", re.I),
    "code": re.compile(r"```(python|bash|sh)?", re.I),
    # v2 新增：论文式小节与校验面（技术报告几乎必然出现，编排日志几乎不出现）
    "section": re.compile(r"案例介绍|物理背景|算例|工况|边界条件|解析解|收敛|benchmark|"
                          r"validation|verification|对标|相对误差", re.I),
}


def _entropy(s: str) -> float:
    """Shannon 熵（bits/char）——仅用于记录命中 token 的可疑度，不单独作判据。"""
    if not s:
        return 0.0
    c = Counter(s)
    n = len(s)
    import math
    return -sum((v / n) * math.log2(v / n) for v in c.values())


SECRET_PATTERNS = {
    "pg_password": re.compile(r"PGPASSWORD\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    "api_key": re.compile(r"(?i)(api[_-]?key|secret[_-]?key)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    "bearer": re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]{20,}"),
    "aws_ak": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(t: str) -> str:
    return sha256_bytes(t.encode("utf-8"))


# ---------------------------------------------------------------------------
# 规范化（R01..R05）
# ---------------------------------------------------------------------------
def normalize(text: str) -> tuple[str, list[str]]:
    """返回 (规范化文本, 修复动作码列表)。纯函数、幂等。"""
    repairs: list[str] = []
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
        repairs.append("R01_strip_bom")
    if "\r\n" in text:
        text = text.replace("\r\n", "\n")
        repairs.append("R02_crlf_to_lf")
    if "\r" in text:
        text = text.replace("\r", "\n")
    lines = text.split("\n")
    stripped = [ln.rstrip() for ln in lines]
    if stripped != lines:
        repairs.append("R03_trailing_ws")
        text = "\n".join(stripped)
    nfc = unicodedata.normalize("NFC", text)
    if nfc != text:
        repairs.append("R04_unicode_nfc")
        text = nfc
    if re.search(r"\n{3,}", text):
        text = re.sub(r"\n{3,}", "\n\n", text)
        repairs.append("R05_blank_collapse")
    return text, repairs


def secret_hits(text: str) -> list[dict]:
    """返回命中明细：规则名 + 起止 span + token 摘要（绝不回写原文）。"""
    out = []
    for name, pat in SECRET_PATTERNS.items():
        for m in pat.finditer(text):
            tok = m.group(0)
            # 只保留「键名」部分与长度/熵，避免把秘密写进账本
            head = tok.split("=")[0].split(":")[0][:24]
            out.append({
                "rule": name,
                "span": [m.start(), m.end()],
                "len": len(tok),
                "token_sha256_12": sha256_text(tok)[:12],
                "entropy": round(_entropy(tok), 3),
                "shape": head,
            })
    return out


def knowledge_score(text: str) -> int:
    return sum(1 for pat in KNOWLEDGE_MARKERS.values() if pat.search(text))


# ---------------------------------------------------------------------------
# 规则引擎：单个语料单元
# ---------------------------------------------------------------------------
def classify_item(item: dict, canonical: dict[str, str], boiler_lines: set[str]) -> dict:
    """item: {key, kind, bytes, text|None}。返回 ledger 行（不含 snapshot_digest）。"""
    key = item["key"]
    raw: bytes = item["bytes"]
    row = {
        "key": key,
        "kind": item.get("kind", "text"),
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "decision": DEC_KEPT,
        "reasons": [],
        "repairs": [],
        "warnings": [],
        "bytes_out": len(raw),
        "sha256_out": sha256_bytes(raw),
    }
    text = item.get("text")
    if text is None:
        # 二进制/不可解码
        row["reasons"].append("X01_non_utf8")
        row["reason"] = "X01_non_utf8"
        row["reason_all"] = ["X01_non_utf8"]
        row["decision"] = DEC_EXCLUDED
        row["bytes_out"] = 0
        row["sha256_out"] = None
        return row

    norm, repairs = normalize(text)
    row["repairs"] = repairs
    row["sha256_out"] = sha256_text(norm)
    row["bytes_out"] = len(norm.encode("utf-8"))

    # ---- 剔除类规则：全部命中都记账，但主因码按固定优先级取一条（保证账本可加总）----
    hits = secret_hits(text)
    if hits:
        row["reasons"].append("X04_secret_leak")
        row["secret_hits"] = hits

    min_len = (TH["file_min_bytes"]
               if item.get("kind") in ("text_file", "json_file") else TH["report_min_chars"])
    if len(norm.strip()) < min_len:
        row["reasons"].append("X02_empty_or_stub")

    if item.get("kind") == "json_file":
        try:
            json.loads(norm)
        except Exception:
            row["reasons"].append("X07_invalid_json")

    if canonical.get(row["sha256"]) and canonical[row["sha256"]] != key:
        row["reasons"].append("X03_duplicate")
        row["duplicate_of"] = canonical[row["sha256"]]

    if item.get("kind") == "report":
        win = norm[:TH["report_max_scan"]]
        head = (item.get("title", "") + " " + item.get("scenario_key", "")).lower()
        proc_hits = [t for t in PROCESS_TOKENS if t in head]
        ks = knowledge_score(win)
        # 结构信号入账：剔除判定必须能被账本自检（有量纲/公式证据 = 疑似误剔）
        row["knowledge_markers"] = ks
        row["struct_signals"] = {
            "unit_hits": len(UNITS_RE.findall(win)),
            "eq_hits": len(EQ_RE.findall(win)),
            "table_rows": len(TABLE_ROW_RE.findall(win)),
            "proc_tokens": proc_hits[:4],
        }
        # v2 判据：编排词命中 + 知识标记 <=1 + 零量纲 + 零公式（任一结构证据即不剔）
        if (proc_hits and ks < TH["process_knowledge_min"]
                and not row["struct_signals"]["unit_hits"]
                and not row["struct_signals"]["eq_hits"]):
            row["reasons"].append("X06_process_log")

    # 模板行扣除（跨文档；v2：仅散文，且要求模板行占去壳字符 >= 80%——短技术报告不再被误剔）
    prose = item.get("kind") == "report" or item.get("key", "").endswith(".md")
    if boiler_lines and prose:
        residual = 0
        for ln in norm.split("\n"):
            s = ln.strip()
            if s and s in boiler_lines:
                continue
            residual += len(s)
        total_stripped = sum(len(ln.strip()) for ln in norm.split("\n") if ln.strip())
        cov = 1.0 - (residual / total_stripped) if total_stripped else 0.0
        row["residual_chars"] = residual
        row["boilerplate_coverage"] = round(cov, 4)
        if residual < TH["boilerplate_residual_chars"] and cov >= TH["boilerplate_cov_min"]:
            row["reasons"].append("X05_boilerplate_only")

    # ---- 非剔除类警示 ----
    if not any(r.startswith("X") for r in row["reasons"]):
        if item.get("kind") == "report":
            has_claim = re.search(r"达标|通过|完成|验收|PASS|S[1-5]\b", norm) is not None
            has_artifact = re.search(r"(docs/|artifacts/|runs/|scripts/|\.py\b|\.json\b|\.csv\b|\.png\b)", norm) is not None
            if has_claim and not has_artifact:
                row["warnings"].append("W01_claims_without_artifact_refs")

    if row["reasons"]:
        row["decision"] = DEC_EXCLUDED
        row["reason_all"] = sorted(row["reasons"])
        row["reason"] = next(rc for rc in REASON_PRIORITY if rc in row["reasons"])
        row["bytes_out"] = 0
        row["sha256_out"] = None
    else:
        row["reason"] = None
        if repairs:
            row["decision"] = DEC_REPAIRED
    return row


def _canonical_map(items: list[dict]) -> dict[str, str]:
    """同 sha256 的规范条目 = key 字典序最小者（确定性）。"""
    canon: dict[str, str] = {}
    for it in sorted(items, key=lambda x: x["key"]):
        h = sha256_bytes(it["bytes"])
        canon.setdefault(h, it["key"])
    return canon


def _boilerplate_lines(texts: list[str], n_docs: int) -> set[str]:
    """跨文档高频短行集合（阈值预注册：出现率 >= 20%）。"""
    if n_docs < TH["boilerplate_min_docs"]:
        return set()  # 小语料退化保护：样本太少时"模板行"与"实质内容"不可分
    df = Counter()
    for t in texts:
        seen = set()
        for ln in t.split("\n"):
            s = ln.strip()
            if len(s) >= TH["boilerplate_min_len"] and s not in seen:
                seen.add(s)
                df[s] += 1
    cutoff = max(2, int(TH["boilerplate_line_frac"] * n_docs))
    return {s for s, c in df.items() if c >= cutoff}


def snapshot_digest(rows: list[dict]) -> str:
    """语料快照摘要：sha256( 逐行 "key:sha256" 排序拼接 )。"""
    h = hashlib.sha256()
    for r in sorted(rows, key=lambda x: x["key"]):
        h.update(f'{r["key"]}:{r["sha256"]}\n'.encode("utf-8"))
    return h.hexdigest()


# ---------------------------------------------------------------------------
# 汇总（全部由 ledger 派生）
# ---------------------------------------------------------------------------
CONTENT_REASONS = ("X02_empty_or_stub", "X05_boilerplate_only", "X06_process_log")


def _contradiction(rows: list[dict]) -> dict:
    """内容质量类剔除项中，带量纲/公式结构证据（= 疑似误剔）的条数与比例。"""
    sub = [r for r in rows if r["decision"] == DEC_EXCLUDED and r.get("reason") in CONTENT_REASONS]
    bad = [r for r in sub if r.get("struct_signals", {}).get("unit_hits")
           or r.get("struct_signals", {}).get("eq_hits")]
    return {
        "excluded_content_reasons": len(sub),
        "with_struct_evidence": len(bad),
        "rate": round(len(bad) / len(sub), 6) if sub else 0.0,
        "gate_le_0.05": (len(bad) / len(sub) if sub else 0.0) <= 0.05,
    }


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    dec = Counter(r["decision"] for r in rows)
    reasons = Counter(r["reason"] for r in rows if r.get("reason"))
    repairs = Counter(rc for r in rows for rc in r["repairs"])
    warnings = Counter(w for r in rows for w in r["warnings"])
    bytes_in = sum(r["bytes"] for r in rows)
    bytes_out = sum(r["bytes_out"] for r in rows if r["decision"] != DEC_EXCLUDED)
    bytes_repair_delta = sum(r["bytes"] - r["bytes_out"] for r in rows if r["decision"] == DEC_REPAIRED)
    return {
        "ledger_version": LEDGER_VERSION,
        "items_scanned": n,
        "decision_counts": {d: dec.get(d, 0) for d in DECISIONS},
        "excluded_total": dec.get(DEC_EXCLUDED, 0),
        "exclusion_reasons": dict(sorted(reasons.items())),
        "repair_actions": dict(sorted(repairs.items())),
        "warnings": dict(sorted(warnings.items())),
        "bytes_in": bytes_in,
        "bytes_out": bytes_out,
        "bytes_excluded": sum(r["bytes"] for r in rows if r["decision"] == DEC_EXCLUDED),
        "bytes_repair_delta": bytes_repair_delta,
        "coverage_ratio": 1.0 if n else 0.0,  # 全量枚举：每条语料单元都有一行
        "keep_ratio_by_count": round((dec.get(DEC_KEPT, 0) + dec.get(DEC_REPAIRED, 0)) / n, 6) if n else 0.0,
        "keep_ratio_by_bytes": round(bytes_out / bytes_in, 6) if bytes_in else 0.0,
        # 矛盾率：仅对"内容质量类"理由计（X03 副本即使含量纲也应当剔除，不计矛盾）
        "contradiction_content_reasons": _contradiction(rows),
        "excluded_with_unit_evidence": sum(
            1 for r in rows if r["decision"] == DEC_EXCLUDED
            and r.get("struct_signals", {}).get("unit_hits")),
        "excluded_with_eq_evidence": sum(
            1 for r in rows if r["decision"] == DEC_EXCLUDED
            and r.get("struct_signals", {}).get("eq_hits")),
        "ledger_sha256": sha256_bytes(
            ("\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows)).encode("utf-8")
        ),
        "snapshot_digest": snapshot_digest(rows),
    }


# ---------------------------------------------------------------------------
# 适配器 1：仓内文件语料
# ---------------------------------------------------------------------------
def iter_file_items(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        raw = p.read_bytes()
        key = str(p.relative_to(root.parent))
        ext = p.suffix.lower()
        if ext not in TH["file_text_ext"]:
            yield {"key": key, "kind": "binary_asset", "bytes": raw, "text": None}
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            yield {"key": key, "kind": "text_file", "bytes": raw, "text": None}
            continue
        kind = "json_file" if ext == ".json" else "text_file"
        yield {"key": key, "kind": kind, "bytes": raw, "text": text}


def run_files(root: Path, out: Path) -> dict:
    items = list(iter_file_items(root))
    rows = _run_engine(items, out)
    return rows


# ---------------------------------------------------------------------------
# 适配器 2：tensor_reports 已发布报告（DB）
# ---------------------------------------------------------------------------
def fetch_reports(pg: list[str], env: dict) -> list[dict]:
    """从平台库导出已发布报告（id/title/scenario_key/markdown）。"""
    sql = (
        "COPY (SELECT id, coalesce(title,''), coalesce(scenario_key,''), "
        "coalesce(markdown,'') FROM tensor_reports WHERE status='published' ORDER BY id) "
        "TO STDOUT WITH (FORMAT csv)"
    )
    proc = subprocess.run(pg + ["-c", sql], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"psql failed: {proc.stderr[:400]}")
    import csv
    import io
    csv.field_size_limit(sys.maxsize)
    items = []
    for row in csv.reader(io.StringIO(proc.stdout)):
        if len(row) < 4:
            continue
        items.append({
            "key": f"report:{int(row[0])}",
            "kind": "report",
            "bytes": row[3].encode("utf-8"),
            "text": row[3],
            "title": row[1],
            "scenario_key": row[2],
        })
    return items


def run_reports(out: Path, pg: list[str], env: dict) -> dict:
    items = fetch_reports(pg, env)
    return _run_engine(items, out)


# ---------------------------------------------------------------------------
# 引擎执行 + 落盘
# ---------------------------------------------------------------------------
def _run_engine(items: list[dict], out: Path) -> list[dict]:
    canon = _canonical_map(items)
    texts = [it["text"] for it in items if it.get("text")]
    boiler = _boilerplate_lines(texts, len(texts))
    rows = [classify_item(it, canon, boiler) for it in sorted(items, key=lambda x: x["key"])]
    out.mkdir(parents=True, exist_ok=True)
    with (out / "ledger.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    summ = summarize(rows)
    summ["boilerplate_lines"] = len(boiler)
    (out / "summary.json").write_text(
        json.dumps(summ, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "report.md").write_text(render_report(summ, rows, out.name), encoding="utf-8")
    return rows


def render_report(s: dict, rows: list[dict], scope: str) -> str:
    lines = [
        f"# KBM-CLEAN-W1 · 清洗分类账（scope={scope}）",
        "",
        f"- 账本版本：`{s['ledger_version']}`",
        f"- 语料单元数：**{s['items_scanned']}**（全量枚举，无抽样）",
        f"- 判定：kept {s['decision_counts']['kept']} / repaired {s['decision_counts']['repaired']}"
        f" / excluded {s['excluded_total']}",
        f"- 字节：in {s['bytes_in']} → out {s['bytes_out']}"
        f"（剔除 {s['bytes_excluded']}，规范化缩水 {s['bytes_repair_delta']}）",
        f"- 保留率：按条数 {s['keep_ratio_by_count']:.4f}，按字节 {s['keep_ratio_by_bytes']:.4f}",
        f"- ledger_sha256：`{s['ledger_sha256']}`",
        f"- snapshot_digest：`{s['snapshot_digest']}`",
        "",
        "## 剔除分类账（按理由码）",
        "",
        "| reason_code | 条数 | 说明 |",
        "|---|---|---|",
    ]
    for code, cnt in s["exclusion_reasons"].items():
        lines.append(f"| {code} | {cnt} | {REASON_CODES.get(code, '')} |")
    lines += ["", "## 修复动作", "", "| repair_code | 条数 | 说明 |", "|---|---|---|"]
    if s["repair_actions"]:
        for code, cnt in s["repair_actions"].items():
            lines.append(f"| {code} | {cnt} | {REPAIR_CODES.get(code, '')} |")
    else:
        lines.append("| - | 0 | 本语料无需修复 |")
    lines += ["", "## 警示（不剔除）", ""]
    if s["warnings"]:
        for code, cnt in s["warnings"].items():
            lines.append(f"- `{code}`：{cnt}")
    else:
        lines.append("- 无")
    lines += ["", "## 复算方式", "", "```bash",
              "python -m ke.clean verify --out <本目录> --scope {scope} [--root knowledge]",
              "```", "",
              "`verify` 从 ledger.jsonl 重新聚合全部数字并与 summary.json 逐项比对；"
              "任一不等即非零退出。", ""]
    return "\n".join(lines).format(scope=scope)


# ---------------------------------------------------------------------------
# 复核器
# ---------------------------------------------------------------------------
def load_ledger(out: Path) -> list[dict]:
    p = out / "ledger.jsonl"
    if not p.exists():
        raise SystemExit(f"缺少账本: {p}")
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def verify(out: Path, scope: str, root: Path | None = None, pg_expected: int | None = None) -> int:
    rows = load_ledger(out)
    summ = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    recalc = summarize(rows)
    errs = []
    # E. 复算账：summary 的每个派生字段必须等于重算值
    for k in ("items_scanned", "decision_counts", "excluded_total", "exclusion_reasons",
              "repair_actions", "warnings", "bytes_in", "bytes_out", "bytes_excluded",
              "keep_ratio_by_count", "keep_ratio_by_bytes", "bytes_repair_delta",
              "excluded_with_unit_evidence", "excluded_with_eq_evidence",
              "contradiction_content_reasons",
              "ledger_sha256", "snapshot_digest"):
        if summ.get(k) != recalc.get(k):
            errs.append(f"{k}: summary={summ.get(k)!r} recalc={recalc.get(k)!r}")
    # C. 判定账
    if sum(recalc["decision_counts"].values()) != recalc["items_scanned"]:
        errs.append("decision_counts 之和 != items_scanned")
    if sum(recalc["exclusion_reasons"].values()) != recalc["excluded_total"]:
        errs.append("exclusion_reasons 之和 != excluded_total")
    # B/D. 字节账
    if recalc["bytes_in"] != recalc["bytes_out"] + recalc["bytes_excluded"] + recalc["bytes_repair_delta"]:
        errs.append("bytes_in != bytes_out + bytes_excluded + bytes_repair_delta")
    # A. 覆盖率：账本条数 == 语料实际单元数
    if scope == "files":
        if root is None:
            errs.append("files 面需要 --root 才能复核覆盖率")
        else:
            actual = sum(1 for p in root.rglob("*") if p.is_file() and ".git" not in p.parts)
            if actual != recalc["items_scanned"]:
                errs.append(f"覆盖率不闭合：磁盘 {actual} 个文件 vs 账本 {recalc['items_scanned']} 条")
    elif scope == "reports":
        if pg_expected is not None and pg_expected != recalc["items_scanned"]:
            errs.append(f"覆盖率不闭合：DB {pg_expected} 条 vs 账本 {recalc['items_scanned']} 条")
    # 闭合集校验
    for r in rows:
        if r["decision"] not in DECISIONS:
            errs.append(f"{r['key']}: 非法 decision {r['decision']}")
        for rc in r["reasons"]:
            if rc not in REASON_CODES:
                errs.append(f"{r['key']}: 非法 reason {rc}")
        for rp in r["repairs"]:
            if rp not in REPAIR_CODES:
                errs.append(f"{r['key']}: 非法 repair {rp}")
    if errs:
        for e in errs[:20]:
            print(f"[FAIL] {e}")
        print(f"verify FAILED ({len(errs)} 项)")
        return 1
    print(f"[OK] ledger={recalc['items_scanned']} items, "
          f"excluded={recalc['excluded_total']}, bytes_in={recalc['bytes_in']}, "
          f"ledger_sha256={recalc['ledger_sha256'][:16]}… 复算一致")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _pg():
    env = dict(os.environ)
    env.setdefault("PGPASSWORD", os.environ.get("TP_PG_PASSWORD", ""))
    pg = ["psql", "-h", os.environ.get("TP_PG_HOST", "127.0.0.1"),
          "-U", os.environ.get("TP_PG_USER", "postgres"),
          "-d", os.environ.get("TP_PG_DB", "tensorplatform"), "-tA"]
    return pg, env


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="KBM-CLEAN-W1 知识语料清洗层")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="跑清洗并落账本")
    p_run.add_argument("--scope", choices=["files", "reports"], required=True)
    p_run.add_argument("--root", default="knowledge")
    p_run.add_argument("--out", required=True)

    p_re = sub.add_parser("resummarize", help="从 ledger.jsonl 重算 summary.json + report.md（不改账本）")
    p_re.add_argument("--scope", required=True)
    p_re.add_argument("--out", required=True)

    p_ver = sub.add_parser("verify", help="从 ledger 重新聚合复核 summary")
    p_ver.add_argument("--scope", choices=["files", "reports"], required=True)
    p_ver.add_argument("--root", default=None)
    p_ver.add_argument("--out", required=True)
    p_ver.add_argument("--pg-expected", type=int, default=None)

    a = ap.parse_args(argv)
    out = Path(a.out)
    if a.cmd == "run":
        if a.scope == "files":
            rows = run_files(Path(a.root), out)
        else:
            pg, env = _pg()
            rows = run_reports(out, pg, env)
        s = summarize(rows)
        print(json.dumps({k: s[k] for k in ("items_scanned", "excluded_total", "bytes_in",
                                           "bytes_out", "keep_ratio_by_count")}, ensure_ascii=False))
        return 0
    if a.cmd == "resummarize":
        rows = load_ledger(out)
        summ = summarize(rows)
        (out / "summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n",
                                         encoding="utf-8")
        (out / "report.md").write_text(render_report(summ, rows, out.name), encoding="utf-8")
        print(json.dumps({k: summ[k] for k in ("items_scanned", "excluded_total",
                                              "contradiction_content_reasons")}, ensure_ascii=False))
        return 0
    if a.cmd == "verify":
        return verify(out, a.scope, Path(a.root) if a.root else None, a.pg_expected)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())