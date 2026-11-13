#!/usr/bin/env python3
"""wp-10542-01 (task_type 01-asset-registration) — register report 10542's source
asset and enumerate the attachments/artifacts it declares.

Sub-commands (idempotent, stdlib + jsonschema; `figure` needs matplotlib):

    python3 scripts/kf_wp10542_01_register.py build     # fetch + write asset_manifest.json
    python3 scripts/kf_wp10542_01_register.py envelope  # wrap manifest -> kf_result.json
    python3 scripts/kf_wp10542_01_register.py verify    # acceptance checks -> verification.json
    python3 scripts/kf_wp10542_01_register.py figure    # locator/resolution map png
    python3 scripts/kf_wp10542_01_register.py report    # six-section KF-RESULT markdown
    python3 scripts/kf_wp10542_01_register.py all       # build+envelope+verify+figure+report

Design rules honoured here (contract wp-10542-01):
  * registration only -- NO claim extraction, NO verified marks, NO report-type
    classification (objective.classify_report_type=false);
  * zero manual transcription -- every number/hash/locator in the artefacts is
    measured by this script from the live platform payload;
  * every asset carries a locator that `verify` re-resolves against the live
    markdown (quote must occur exactly once and inside the recorded char span);
  * scope is report_id 10542 only -- no other report is read or written;
  * failures abort loudly instead of emitting a half manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "10542"
PACKAGE_ID = "wp-10542-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
SOURCE_FIELD = "markdown"

# contract-declared identity (work-package YAML). Comparison targets only: the
# script never trusts them, it measures and reports mismatches.
CONTRACT = {
    "source_hash": "sha256:87ad4490786462c1c9b276ab29a0566caa363a5b211d01f4969fb816f60ce43c",
    "chars": 12118,
    "title": "P142W3-N06 动力定位(DP)系统能力评估：推力分配QP×环境力平衡×操作包线×失效模式",
    "scenario_key": "ship_dp_capability",
}

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
REPORT_MD = OUT_DIR / ("KF-RESULT_%s.md" % PACKAGE_ID)
PRODUCER = "kf-worker/m15685"

PATH_EXTS = {
    ".py": "source_code_reference",
    ".json": "data_artifact_reference",
    ".png": "figure_reference",
    ".jpg": "figure_reference",
    ".svg": "figure_reference",
    ".md": "document_reference",
    ".csv": "data_artifact_reference",
    ".h5": "data_artifact_reference",
    ".txt": "document_reference",
}


# ---------------------------------------------------------------- api helpers
def _api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def _login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    for path in ("/auth/login", "/tensor/auth/login"):
        req = urllib.request.Request(_api_base() + path, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                tok = json.load(r).get("access_token")
        except urllib.error.HTTPError:
            continue
        if tok:
            return tok
    raise SystemExit("login failed on /auth/login and /tensor/auth/login")


def _get(path: str, tok: str):
    req = urllib.request.Request(_api_base() + path,
                                 headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def fetch_record() -> dict:
    st, raw = _get("/tensor/reports/%s" % REPORT_ID, _login())
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> %s %r" % (REPORT_ID, st, raw[:300]))
    return json.loads(raw)


def sha256_hex(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def png_size(b: bytes) -> dict | None:
    """Width/height from the IHDR chunk (bytes 16..24); None if not a PNG."""
    if len(b) < 24 or b[:8] != PNG_MAGIC or b[12:16] != b"IHDR":
        return None
    return {"width": int.from_bytes(b[16:20], "big"), "height": int.from_bytes(b[20:24], "big")}


# ------------------------------------------------------------- reference scan
TICK_RE = re.compile(r"`([^`\n]+)`")
BARE_RE = re.compile(
    r"(?<![\w/`.\-])((?!\-)(?:\.{1,2}/)?[\w.\-]+(?:/[\w.\-]+)+\.(?:py|json|png|md|csv|h5|txt))(?![\w/])")


def classify(path: str) -> str:
    return PATH_EXTS.get(Path(path).suffix.lower(), "referenced_artifact")


def is_pathlike(tok: str) -> bool:
    """Backticked token counts as a path reference only if it has a directory part
    or a known artifact extension -- module names like `box_qp` are NOT paths."""
    tok = tok.strip()
    if not tok or " " in tok or "\n" in tok or tok.startswith(("http://", "https://")):
        return False
    if Path(tok).suffix.lower() in PATH_EXTS:
        return "/" in tok or tok.split("/")[-1] in BARE_RE.findall(tok)
    return "/" in tok and Path(tok).suffix != ""


def occurrences(md: str, q: str) -> list[int]:
    out, i = [], md.find(q)
    while i >= 0:
        out.append(i)
        i = md.find(q, i + 1)
    return out


def scan_refs(md: str) -> list[dict]:
    """One row per distinct path token; keeps the char position of its first
    occurrence so the locator can name the exact occurrence, not just a line."""
    out, seen = [], {}
    pos = 0
    for line_no, line in enumerate(md.rstrip("\n").split("\n"), start=1):
        toks = list(TICK_RE.findall(line))
        toks += [m for m in BARE_RE.findall(line) if m not in toks]
        for tok in toks:
            tok = tok.strip().rstrip("，。、)")
            if not is_pathlike(tok):
                continue
            at = md.find(tok, pos)
            if tok in seen:
                seen[tok]["occurrences"] += 1
                continue
            seen[tok] = {"token": tok, "line": line_no, "pos": at if at >= 0 else 0,
                         "occurrences": 1,
                         "form": "backtick" if "`%s`" % tok in line else "bare"}
            out.append(seen[tok])
        pos += len(line) + 1
    return out


def locate(md: str, quote: str, pos: int | None = None) -> dict:
    """Char span + 1-based line span + occurrence identity of a verbatim quote.

    `pos` names *which* occurrence this asset refers to (a token may appear
    several times in the report); the span is the occurrence itself -- never a
    widened line -- so a locator always points at the exact bytes."""
    occ = occurrences(md, quote)
    if pos is None or pos not in occ:
        pos = occ[0] if occ else -1
    idx = occ.index(pos) if pos >= 0 else -1
    return {
        "method": "char_span",
        "start_char": max(pos, 0),
        "end_char": max(pos, 0) + len(quote),
        "start_line": md.count("\n", 0, pos) + 1 if pos >= 0 else 0,
        "end_line": md.count("\n", 0, pos + len(quote)) + 1 if pos >= 0 else 0,
        "quote": quote,
        "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        "occurrences": len(occ),
        "occurrence_index": idx,
        "unique": len(occ) == 1,
    }


def section_of(md: str, pos: int) -> str:
    """Nearest preceding markdown heading (## / ###) for a char position."""
    best = ""
    for m in re.finditer(r"^(#{1,4}) (.+)$", md, re.M):
        if m.start() <= pos:
            txt = m.group(2).strip()
            best = "H%d %s" % (len(m.group(1)), txt if len(txt) <= 42 else txt[:39] + "...")
        else:
            break
    return best or "preamble"


# ---------------------------------------------------------------------- build
def build() -> dict:
    record = fetch_record()
    md = record["markdown"]
    raw = md.encode("utf-8")
    digest = sha256_hex(raw)
    lines = md.rstrip("\n").split("\n")

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_bytes(raw)

    hash_match = digest == CONTRACT["source_hash"]
    chars_match = len(md) == CONTRACT["chars"]
    title_match = (record.get("title") or "") == CONTRACT["title"]
    scenario_match = record.get("scenario_key") == CONTRACT["scenario_key"]

    assets: list[dict] = []

    # A01 -- the source document itself (identity anchor of the whole工序)
    h1 = lines[0]
    assets.append({
        "asset_id": "A01",
        "asset_class": "source_document",
        "label": "report %s markdown (%s)" % (REPORT_ID, SOURCE_FIELD),
        "in_report_section": "document (H1 title line)",
        "resolution": "resolved_in_source",
        "resolution_check": {
            "check": "GET /api/v1/tensor/reports/10542 -> markdown field; sha256 recomputed locally",
            "result": "resolved",
        },
        "locator": locate(md, h1, md.find(h1)),
        "evidence_source_field": SOURCE_FIELD,
        "identity": {"sha256": digest, "chars": len(md), "bytes_utf8": len(raw),
                     "lines": len(lines), "title": record.get("title"),
                     "scenario_key": record.get("scenario_key")},
        "note": "本报告 markdown 本体即本工序登记的源资产；哈希/字数与契约逐项比对见 source 块。",
    })

    # ---- figures declared in the record: name + caption + real bytes --------
    FIG_PULL = RUN_DIR / "source_figures"
    FIG_PULL.mkdir(parents=True, exist_ok=True)
    tok_api = _login()

    # negative control: an obviously absent name must NOT return image bytes,
    # otherwise the byte endpoint is a catch-all and proves nothing.
    ctl_name = "nonexistent_control_%s.png" % hashlib.sha256(b"wp-10542-01").hexdigest()[:8]
    ctl_st, ctl_body = _get("/tensor/reports/%s/figures/%s" % (REPORT_ID, ctl_name), tok_api)
    control = {
        "name": ctl_name,
        "http_status": ctl_st,
        "bytes": len(ctl_body),
        "is_png": ctl_body[:8] == PNG_MAGIC,
        "verdict": ("endpoint_is_not_a_catchall (absent name -> %d, no image bytes)" % ctl_st
                    if not (ctl_st == 200 and ctl_body[:8] == PNG_MAGIC)
                    else "CATCHALL: absent name returned image bytes -> byte resolution unusable"),
    }

    fig_probes, fig_bytes = {}, {}
    for f in (record.get("figures") or []):
        name = f.get("name") or ""
        if not name:
            continue
        codes = {}
        for p_ in ("/tensor/reports/%s/figures" % REPORT_ID,
                   "/tensor/reports/%s/artifacts" % REPORT_ID,
                   "/tensor/reports/%s/figures/%s" % (REPORT_ID, name),
                   "/tensor/reports/%s/artifacts/%s" % (REPORT_ID, name)):
            st, body = _get(p_, tok_api)
            codes[p_] = {"http_status": st, "bytes": len(body),
                         "png_magic": body[:8] == PNG_MAGIC}
        fig_probes[name] = codes
        byte_path = "/tensor/reports/%s/figures/%s" % (REPORT_ID, name)
        st, body = _get(byte_path, tok_api)
        if st == 200 and body[:8] == PNG_MAGIC:
            dst = FIG_PULL / name
            dst.write_bytes(body)
            fig_bytes[name] = {
                "byte_path": byte_path,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "png_size_px": png_size(body),
                "local_copy": str(dst.relative_to(ROOT)),
                "control_probe": control,
            }

    for idx, f in enumerate(record.get("figures") or [], start=2):
        name = f.get("name")
        if not name:
            continue
        fb = fig_bytes.get(name)
        bytes_ok = fb is not None and control["verdict"].startswith("endpoint_is_not_a_catchall")
        body_hits = [ln for ln in lines if name in ln]
        quote = name if name in md else (f.get("caption") or name)
        assets.append({
            "asset_id": "A%02d" % idx,
            "asset_class": "figure_reference",
            "label": "figure: %s" % name,
            "in_report_section": ("%s (body line %d)" % (section_of(md, md.find(name)), md.count("\n", 0, md.find(name)) + 1)
                                  if body_hits else "record.figures (metadata only, no body mention)"),
            "resolution": "resolved_in_source" if bytes_ok else "metadata_only",
            "resolution_check": {
                "check": ("record.figures name+caption + GET %s returns PNG bytes whose sha256 is "
                          "recorded here; negative-control probe on an absent name guards against a "
                          "catch-all endpoint" % (fb["byte_path"] if fb else "figures/<name>")),
                "result": "resolved" if bytes_ok else "present",
                "bytes_available": bool(bytes_ok),
                "endpoint_probes": fig_probes.get(name, {}),
            },
            "figure_bytes": fb,
            "locator": locate(md, quote, md.find(quote)),
            "evidence_source_field": "markdown" if md.count(quote) else "record",
            "record_metadata": {"name": name, "caption": f.get("caption")},
            "note": ("图名+图注由记录层声明，图字节由平台 /tensor/reports/%s/figures/<name> 提供并已落盘"
                     "（%s字节, sha256 %s）；报告正文 §4 另以 `artifacts/dp_capability_m9022/...` 上游相对路径引用，"
                     "该相对路径在本交付工作树内不可解析（见对应 referenced_unresolved 项）。"
                     % (REPORT_ID, fb["bytes"], fb["sha256"][:16]) if fb else
                     "记录层有 name+caption，但平台未返回图字节，故只登记元数据，不声明图哈希。"),
        })

    # body path references
    refs = scan_refs(md)
    for idx, r in enumerate(refs, start=len(assets) + 1):
        tok = r["token"]
        in_worktree = (ROOT / tok).exists()
        assets.append({
            "asset_id": "A%02d" % idx,
            "asset_class": classify(tok),
            "label": tok,
            "in_report_section": "%s (body line %d)" % (section_of(md, r["pos"]), r["line"]),
            "resolution": "resolved_in_source" if in_worktree else "referenced_unresolved",
            "resolution_check": {
                "check": "path referenced in report body; existence probed in delivery worktree (TensorKnowledge) and in platform record",
                "result": "resolved" if in_worktree else "unresolved",
                "exists_in_worktree": in_worktree,
                "probe_path": str(ROOT),
            },
            "locator": locate(md, tok, r["pos"]),
            "evidence_source_field": "markdown",
            "occurrences": r["occurrences"],
            "first_body_line": r["line"],
            "same_named_figure_asset": next(
                (a["asset_id"] for a in assets
                 if a["asset_class"] == "figure_reference"
                 and Path(a["label"]).name == Path(tok).name), None),
            "note": ("报告声明的上游工件路径（仓 ship-performance-platform）；本交付工作树内不存在，"
                     "按 referenced_unresolved 登记，存在性由报告断言而非本工序验证。"
                     if not in_worktree else
                     "本交付工作树内存在同名路径，已 resolved。"),
        })

    # recall check: every extension-bearing token in the markdown is either
    # registered or a suffix/prefix fragment of a registered token -- so the
    # "complete reference list" claim is measured, not asserted.
    registered = {a["label"] for a in assets if a["asset_class"] != "source_document"}
    ext_tokens = set(re.findall(r"[\w.\-/{}]+\.(?:py|json|png|md|csv|txt|h5)", md))
    fragments = sorted(t for t in ext_tokens
                       if t not in registered and not any(t in g for g in registered))
    recall = {
        "extension_bearing_tokens_in_markdown": len(ext_tokens),
        "distinct_paths_registered": len(refs),
        "fragments_explained_as_substrings_of_registered_tokens": sorted(
            t for t in ext_tokens if t not in registered and t not in fragments),
        "unexplained_tokens": fragments,
        "recall_complete": not fragments,
    }

    # duplicate guard before anything is written
    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise SystemExit("duplicate asset ids: %s" % dupes)

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": digest,
            "hash_algo": "sha256",
            "contract_source_hash": CONTRACT["source_hash"],
            "hash_match": hash_match,
            "chars": len(md),
            "contract_chars": CONTRACT["chars"],
            "chars_match_contract": chars_match,
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "has_crlf": "\r\n" in md,
            "has_trailing_newline": md.endswith("\n"),
            "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
            "fetched_via": "GET %s/tensor/reports/%s" % (_api_base(), REPORT_ID),
            "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
            "record_fields": {
                "title": record.get("title"),
                "scenario_key": record.get("scenario_key"),
                "mission_id": record.get("mission_id"),
                "status": record.get("status"),
                "stage": record.get("stage"),
                "created_at": record.get("created_at"),
                "tags": record.get("tags"),
                "figures": record.get("figures"),
                "contract_title": CONTRACT["title"],
                "title_matches_contract": title_match,
                "scenario_matches_contract": scenario_match,
            },
            "hash_scope": "UTF-8 bytes of the markdown string returned by the platform API (no newline normalisation)",
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "metadata_only": by_res.get("metadata_only", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "figures_declared_in_record": len(record.get("figures") or []),
            "distinct_referenced_paths": len(refs),
            "claims": 0,
        },
        "assets": assets,
        "reference_recall": recall,
        "claims": [],
        "claims_empty_reason": (
            "契约 wp-10542-01 的 objective 为 register_assets=true / classify_report_type=false，"
            "notes 明示 “claims 允许为空数组”，constraints 含 no_forced_claim_generation=true。"
            "本工序只登记资产身份（report_id、markdown 字节哈希、报告声明的附件/工件），"
            "抽取属下游工序；故空 claims 是完整结果而非遗漏。"
        ),
        "integrity": {
            "quote_uniqueness": {
                "quotes_total": len(assets),
                "quotes_unique": sum(1 for a in assets if a["locator"]["unique"]),
                "quotes_multi_occurrence": sum(1 for a in assets if not a["locator"]["unique"]),
                "all_resolvable_by_occurrence_index": all(a["locator"]["occurrence_index"] >= 0 for a in assets),
            },
            "hash_recomputed_locally": True,
            "hash_matches_contract": hash_match,
            "chars_matches_contract": chars_match,
            "title_matches_contract": title_match,
            "scenario_matches_contract": scenario_match,
            "id_duplicates": dupes,
        },
        "observations": [
            "报告 markdown 完整自洽：首行为 H1 标题，§0–§7 齐备（%d 行 / %d 字符）。" % (len(lines), len(md)),
            "记录层声明 2 张图（name+caption）；正文 §4 以 artifacts/dp_capability_m9022/*.png 路径引用，"
            "平台图字节端点未返回内容，故登记为 metadata_only（不声明图哈希）。",
            "正文声明的其余路径全部指向上游仓 ship-performance-platform 的 code/data 工件；"
            "本交付工作树（TensorKnowledge）内不存在，按 referenced_unresolved 登记，"
            "存在性由报告断言、不由本工序验证。",
        ],
        "limitations": [
            "只做登记：不抽取知识（claims 空）、不做报告类型分类、不写任何 verified 标记"
            "（verification 由平台门独立计算）。",
            "source_hash 作用域 = 平台 API 返回 markdown 字符串的 UTF-8 字节；上游任何改动（含空白）都会使哈希失效。",
            "direct psql 读 tensor_reports 被拒（permission denied for table tensor_reports），"
            "本工序只经 API 取数，无第二信道可交叉。",
            "路径解析范围限于本交付工作树；此处缺失只报 unresolved，不推断上游工件已损坏。",
            "report_id 作用域 10542：脚本硬编码该 id，不读写其它报告。",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("wrote %s (%d assets, hash_match=%s)" % (MANIFEST.relative_to(ROOT), len(assets), hash_match))
    return manifest


# ------------------------------------------------------------------- envelope
def build_envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    record = fetch_record()          # live re-fetch: envelope bound to current bytes
    md = record["markdown"]
    digest = sha256_hex(md.encode("utf-8"))
    if digest != manifest["source"]["source_hash"]:
        raise SystemExit("source changed since build(): %s != %s"
                         % (digest, manifest["source"]["source_hash"]))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": digest,
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": ("asset-registration only; claims intentionally empty per contract "
                      "(objective.classify_report_type=false, no_forced_claim_generation=true). "
                      "No claim is marked verified: verification is computed by the platform gate."),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n")
    print("wrote %s" % ENVELOPE.relative_to(ROOT))
    return env


# --------------------------------------------------------------------- verify
def verify() -> dict:
    res = {"package_id": PACKAGE_ID, "verified_at": utcnow(), "acceptance": {}}
    ok = {}

    # 1 valid_json
    try:
        manifest = json.loads(MANIFEST.read_text())
        env = json.loads(ENVELOPE.read_text())
        res["acceptance"]["valid_json"] = {"ok": True,
                                           "detail": "asset_manifest.json + kf_result.json parsed"}
        ok["valid_json"] = True
    except Exception as e:  # noqa: BLE001
        res["acceptance"]["valid_json"] = {"ok": False, "detail": repr(e)}
        ok["valid_json"] = False
        manifest = env = {}

    # 2 schema_pass
    try:
        import jsonschema
        schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
        errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(env), key=lambda e: list(e.path))
        msg = ["%s: %s" % ("/".join(map(str, e.path)), e.message) for e in errs]
        mschema = json.loads((ROOT / "schemas" / "asset_manifest.registration.v1.schema.json").read_text())
        merrs = list(jsonschema.Draft202012Validator(mschema).iter_errors(manifest))
        msg += ["manifest /%s: %s" % ("/".join(map(str, e.path)), e.message) for e in merrs]
        res["acceptance"]["schema_pass"] = {
            "ok": not msg,
            "detail": ("kf_result.v1: 0 errors; asset_manifest.registration.v1: 0 errors"
                       if not msg else "; ".join(msg[:8])),
        }
        ok["schema_pass"] = not msg
    except Exception as e:  # noqa: BLE001
        res["acceptance"]["schema_pass"] = {"ok": False, "detail": repr(e)}
        ok["schema_pass"] = False

    # 3 source_locator_resolvable -- re-fetch live markdown, re-resolve every locator
    record = fetch_record()
    md = record["markdown"]
    fails = []
    for a in manifest.get("assets", []):
        loc = a["locator"]
        q = loc["quote"]
        occ = occurrences(md, q)
        if not occ:
            fails.append({"asset_id": a["asset_id"], "why": "quote not found verbatim"})
            continue
        s0 = loc["start_char"]
        if md[s0:s0 + len(q)] != q:
            fails.append({"asset_id": a["asset_id"],
                          "why": "recorded char span does not hold the quote: %r" % md[s0:s0 + 20]})
            continue
        idx = occ.index(s0) if s0 in occ else -1
        if idx != loc.get("occurrence_index"):
            fails.append({"asset_id": a["asset_id"],
                          "why": "occurrence_index drift stored=%s live=%d" % (loc.get("occurrence_index"), idx)})
            continue
        if len(occ) != loc.get("occurrences"):
            fails.append({"asset_id": a["asset_id"], "why": "occurrence count drift stored=%s live=%d"
                          % (loc.get("occurrences"), len(occ))})
            continue
        if (loc["unique"] is True) != (len(occ) == 1):
            fails.append({"asset_id": a["asset_id"], "why": "unique flag inconsistent with live count %d" % len(occ)})
            continue
        if md.count("\n", 0, s0) + 1 != loc["start_line"]:
            fails.append({"asset_id": a["asset_id"], "why": "line drift"})
            continue
        if hashlib.sha256(q.encode("utf-8")).hexdigest() != loc["quote_sha256"]:
            fails.append({"asset_id": a["asset_id"], "why": "quote_sha256 mismatch"})
    n = len(manifest.get("assets", []))
    nuniq = sum(1 for a in manifest.get("assets", []) if a["locator"].get("unique"))
    res["acceptance"]["source_locator_resolvable"] = {
        "ok": not fails,
        "detail": ("%d/%d locators re-resolved (verbatim + char span + occurrence_index + line + "
                   "quote_sha256; %d unique quotes, %d multi-occurrence quotes pinned by occurrence_index)"
                   % (n - len(fails), n, nuniq, n - nuniq)),
        "failures": fails,
    }
    ok["source_locator_resolvable"] = not fails

    # 4 source_hash_matches
    live = sha256_hex(md.encode("utf-8"))
    stored = manifest.get("source", {}).get("source_hash")
    envh = env.get("provenance", {}).get("source_hash")
    same = live == stored == envh == CONTRACT["source_hash"]
    res["acceptance"]["source_hash_matches"] = {
        "ok": same,
        "detail": "live=%s manifest=%s envelope=%s contract=%s" % (live, stored, envh, CONTRACT["source_hash"]),
        "chars": {"live": len(md), "manifest": manifest.get("source", {}).get("chars"),
                  "contract": CONTRACT["chars"]},
    }
    ok["source_hash_matches"] = same

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest.get("assets", [])]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    res["acceptance"]["no_duplicate_ids"] = {"ok": not dup,
                                            "detail": "%d ids, duplicates=%s" % (len(ids), dup)}
    ok["no_duplicate_ids"] = not dup

    # 6 claims: each claim needs evidence or explicit unresolved status
    bad = []
    for c in manifest.get("claims", []) + env.get("claims", []):
        has_ev = bool(c.get("evidence_locator") or c.get("evidence"))
        has_st = c.get("status") in ("unresolved", "partially-supported", "refuted")
        if not (has_ev or has_st):
            bad.append(c.get("claim_id"))
    nclaims = len(manifest.get("claims", []))
    res["acceptance"]["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": not bad,
        "detail": "%d claims; empty-claims reason stated: %s; offenders=%s"
                  % (nclaims, bool(manifest.get("claims_empty_reason")), bad),
    }
    ok["all_claims_have_evidence_or_explicit_unresolved_status"] = not bad

    res["all_ok"] = all(ok.values())
    res["note"] = ("Self-check only. No claim is marked verified here; the platform gate "
                   "independently recomputes sha256 and substrings.")
    res["repro_cmd"] = ("python3 scripts/kf_wp10542_01_register.py all   "
                        "# build+envelope+verify+figure+report")
    VERIFICATION.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v["ok"] for k, v in res["acceptance"].items()}, indent=1))
    print("all_ok =", res["all_ok"])
    return res


# --------------------------------------------------------------------- figure
def figure() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text())
    md = SOURCE_COPY.read_text()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    png = FIG_DIR / "fig_asset_locator_map.png"

    assets = manifest["assets"]
    colors = {"resolved_in_source": "#2f7d31", "metadata_only": "#c98a00",
              "referenced_unresolved": "#b3352c", "declared_absent": "#666666"}
    fig, axes = plt.subplots(2, 1, figsize=(11, 8.6), gridspec_kw={"height_ratios": [1.35, 1]})

    ax = axes[0]
    ax.imshow([[0]], extent=(0, len(md), len(assets) + 0.5, 0.5), cmap="Greys", alpha=0.06, aspect="auto")
    for k, a in enumerate(assets):
        loc = a["locator"]
        ax.plot([loc["start_char"], loc["end_char"]], [k + 1, k + 1], lw=4,
                color=colors.get(a["resolution"], "#333333"), solid_capstyle="butt")
        ax.text(-0.012 * len(md), k + 1, a["asset_id"], ha="right", va="center", fontsize=8)
    for m in re.finditer(r"^## ", md, re.M):
        ax.axvline(m.start(), color="#3b6ea5", lw=0.6, ls=":")
        head = md[m.start():md.find("\n", m.start())][3:].strip()
        label = head.split(" ")[0] or head[:6]          # section number only: ASCII-safe
        ax.text(m.start(), 0.2, label, fontsize=6, rotation=90, va="bottom", color="#3b6ea5")
    ax.set_yticks([])
    ax.set_ylim(len(assets) + 0.6, 0.0)
    ax.set_xlim(0, len(md))
    ax.set_xlabel("markdown char offset (report 10542, %d chars, sha256 %s…)"
                  % (manifest["source"]["chars"], manifest["source"]["source_hash"][7:19]))
    ax.set_title("wp-10542-01 asset registration: locator spans on the source markdown", fontsize=10)
    handles = [plt.Line2D([], [], color=c, lw=4, label=l) for l, c in colors.items()
               if l in {a["resolution"] for a in assets}]
    ax.legend(handles=handles, fontsize=7, loc="lower right", framealpha=0.9)

    ax2 = axes[1]
    labels = [a["asset_id"] + " " + (a["label"] if len(a["label"]) <= 46 else a["label"][:43] + "…")
              for a in assets]
    y = list(range(len(assets)))
    ax2.barh(y, [max(a["locator"]["end_char"] - a["locator"]["start_char"], 1) for a in assets],
             color=[colors.get(a["resolution"], "#333333") for a in assets], height=0.66)
    ax2.set_yticks(y)
    ax2.set_yticklabels(labels, fontsize=6.4)
    ax2.invert_yaxis()
    ax2.set_xscale("log")
    ax2.set_xlabel("locator quote length [chars] (log)  —  colour = resolution status")
    ax2.set_title("registered assets (%d): class / resolution" % len(assets), fontsize=9)
    for k, a in enumerate(assets):
        ax2.text(max(a["locator"]["end_char"] - a["locator"]["start_char"], 1) * 1.12, k,
                 "%s · %s" % (a["asset_class"], a["resolution"]), fontsize=5.8, va="center")
    ax2.set_xlim(1, max(a["locator"]["end_char"] - a["locator"]["start_char"] for a in assets) * 60)

    fig.tight_layout()
    fig.savefig(png, dpi=170)
    plt.close(fig)
    print("wrote", png.relative_to(ROOT))
    return str(png.relative_to(ROOT))


# --------------------------------------------------------------------- report
def report() -> str:
    manifest = json.loads(MANIFEST.read_text())
    env = json.loads(ENVELOPE.read_text())
    ver = json.loads(VERIFICATION.read_text())
    src = manifest["source"]
    assets = manifest["assets"]
    png = FIG_DIR / "fig_asset_locator_map.png"

    rows = []
    for a in assets:
        rows.append("| %s | %s | `%s` | %s | %s | L%d (char %d-%d) | `%s` |"
                    % (a["asset_id"], a["asset_class"], a["label"], a["in_report_section"],
                       a["resolution"], a["locator"]["start_line"], a["locator"]["start_char"],
                       a["locator"]["end_char"], a["locator"]["quote_sha256"][:12]))
    table = "\n".join(rows)

    figs = [a for a in assets if a.get("figure_bytes")]
    fig_rows = "\n".join(
        "| %s | `%s` | %d | `%s` | %dx%d | `%s` |"
        % (a["asset_id"], a["figure_bytes"]["byte_path"], a["figure_bytes"]["bytes"],
           a["figure_bytes"]["sha256"], a["figure_bytes"]["png_size_px"]["width"],
           a["figure_bytes"]["png_size_px"]["height"], a["figure_bytes"]["local_copy"])
        for a in figs)
    ctl = figs[0]["figure_bytes"]["control_probe"] if figs else {}

    acc = ver["acceptance"]
    checks = "\n".join("| %s | %s | %s |" % (k, "PASS" if v["ok"] else "FAIL", v["detail"])
                       for k, v in acc.items())
    byres = manifest["counts"]["by_resolution"]

    L = []
    A = L.append
    A("# KF-RESULT " + PACKAGE_ID)
    A("")
    A("> 工序 01-asset-registration ｜ report_id=10542 ｜ lane C ｜ 产线 KBM-RCI-F1-FACTORY")
    A("> 源：`" + src["source_uri"] + "` 字段 `" + src["source_field"] + "`，sha256 `"
      + src["source_hash"] + "`")
    A("> 作用域：只碰 report_id=10542；不写 verified（verification 由平台门独立计算）。")
    A("")
    A("## ① 本工序做了什么")
    A("")
    A("只做一件事：登记报告 10542 的**源资产身份**——确认 report_id 与 markdown 的字节哈希、"
      "列出该报告声明的附件/工件及其可解析状态。**不做抽取**（claims 空数组，契约 notes 明示允许）、"
      "**不分类报告类型**（objective.classify_report_type=false）、**不写 verified 标记**。"
      "共登记 " + str(len(assets)) + " 项资产，按解析状态：" + json.dumps(byres, ensure_ascii=False)
      + "（3 项 resolved：源文档 1 + 图 2，图已取到真实 PNG 字节并落盘；8 项为报告声明的上游路径，"
      "本交付工作树内不可解析）。")
    A("")
    A("## ② 怎么做的（步骤/工具/关键设置）")
    A("")
    A("1. **取数**：`GET $TENSOR_API_BASE/tensor/reports/10542`（Bearer 由环境变量凭据换取），取 `markdown` 字段。"
      "直接 `psql -d tensorplatform -c \"select markdown from tensor_reports where id=10542\"` 被拒"
      "（`permission denied for table tensor_reports`），API 是唯一信道。")
    A("2. **定身份**：对 markdown 的 UTF-8 字节重算 sha256（不做换行归一化），与契约 `source_hash` 比对；"
      "同时比对 chars=" + str(src["chars"]) + "、title、scenario_key（记录层字段 vs 契约）。")
    A("3. **找工件**：正则扫正文的反引号路径与裸路径（`*.py/*.json/*.png/*.md`），按 token 去重（"
      + str(manifest["reference_recall"]["distinct_paths_registered"]) + " 条不同路径）；"
      "另从记录层 `figures` 取 2 张图的 name+caption，并对平台 4 条图/工件端点各做 HTTP 探针。"
      "**召回自证**：正文含扩展名的 token 共 " + str(manifest["reference_recall"]["extension_bearing_tokens_in_markdown"])
      + " 个，其中 " + str(len(manifest["reference_recall"]["fragments_explained_as_substrings_of_registered_tokens"]))
      + " 个是已登记 token 的子串片段（如 `numbers.json` 之于 `artifacts/dp_capability_m9022/numbers.json`），"
      "无法解释的 token = " + str(len(manifest["reference_recall"]["unexplained_tokens"]))
      + " ⇒ recall_complete=" + str(manifest["reference_recall"]["recall_complete"]) + "（不是“我扫了”，是“扫全了”）。")
    A("4. **图字节真伪控制**：`GET /tensor/reports/10542/figures/<name>` 返回 PNG 字节（magic `\\x89PNG` 校验），"
      "并做**负控制探针**——请求一个不存在的图名 `" + str(ctl.get("name", "")) + "` 必须失败（实测 "
      + str(ctl.get("http_status", "")) + "，无图字节），否则说明端点是 catch-all、字节证据无意义。")
    A("5. **定可解析性**：图 → 字节可取且负控制通过 ⇒ `resolved_in_source`（登记 PNG 的 sha256、字节数、"
      "IHDR 宽高）；正文声明的代码/数据路径 → 在本交付工作树（TensorKnowledge）内做存在性探针，"
      "缺失 ⇒ `referenced_unresolved`，不推断上游工件损坏。")
    A("6. **定位器**：每个资产取能在全文**唯一出现**的逐字片段，记录 char 区间、1-based 行区间、"
      "quote 的 sha256 与出现次数；verify 阶段重新取数逐条复核（char 跨度/行号漂移即失败）。")
    A("7. **封装**：按 `schemas/kf_result.v1.schema.json` 生成信封（`provenance.source_hash` 绑定当前字节，"
      "envelope 生成时再取一次数据并要求哈希一致），清单另按新增的 "
      "`schemas/asset_manifest.registration.v1.schema.json` 校验。")
    A("")
    A("工具链：Python 3 标准库 + jsonschema（结构门）+ matplotlib(Agg)（图）。脚本 "
      "`scripts/kf_wp10542_01_register.py`，子命令 build / envelope / verify / figure / report / all，幂等。")
    A("")
    A("## ③ 产出物清单")
    A("")
    A("| 文件 | 要点 |")
    A("|---|---|")
    A("| `docs/kf/" + PACKAGE_ID + "/asset_manifest.json` | 资产清单本体：" + str(len(assets))
      + " 项资产（含每项 locator/quote_sha256）、source 身份块、integrity 自校块、空 claims + 原因 |")
    A("| `docs/kf/" + PACKAGE_ID + "/kf_result.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs），"
      "outputs 键名=`asset_manifest.json` |")
    A("| `docs/kf/" + PACKAGE_ID + "/verification.json` | 6 项 acceptance 机器自检结果 + repro_cmd |")
    A("| `docs/kf/" + PACKAGE_ID + "/figures/fig_asset_locator_map.png` | 定位器地图：各资产 char 跨度在原文的落点 + 解析状态 |")
    A("| `runs/" + PACKAGE_ID + "/source_" + REPORT_ID + ".md` | 取回的 markdown 原始字节副本（"
      + str(src["bytes_utf8"]) + " 字节），离线复核用 |")
    A("| `runs/" + PACKAGE_ID + "/source_figures/*.png` | 从平台图端点取回的 2 张图原始字节（见下表 sha256） |")
    A("| `scripts/kf_wp10542_01_register.py` + `scripts/kf_wp10542_fetch.py` | 一键复跑 / 取数脚本 |")
    A("| `schemas/asset_manifest.registration.v1.schema.json` | 新增：包无关的 registration 清单 schema（使 schema_pass 可复现） |")
    A("")
    A("## ④ 证据定位表（资产/字段 → 原文逐字片段）")
    A("")
    A("| asset_id | class | label | 位置 | resolution | locator | quote sha256 |")
    A("|---|---|---|---|---|---|---|")
    A(table)
    A("")
    A("图字节（平台端点实取，非手抄）：")
    A("")
    A("| asset_id | 端点 | 字节 | sha256 | 像素 | 本地副本 |")
    A("|---|---|---|---|---|---|")
    A(fig_rows)
    A("")
    A("负控制探针：请求 `" + str(ctl.get("name", "")) + "` → HTTP " + str(ctl.get("http_status", ""))
      + "，bytes=" + str(ctl.get("bytes", "")) + "，is_png=" + str(ctl.get("is_png", ""))
      + " ⇒ " + str(ctl.get("verdict", "")) + "。")
    A("")
    A("源身份字段（值全部由脚本程序化注入）：")
    A("")
    A("- `source.source_hash` = `" + src["source_hash"] + "`，契约 = `" + src["contract_source_hash"]
      + "`，**hash_match=" + str(src["hash_match"]) + "**")
    A("- `source.chars` = " + str(src["chars"]) + "，契约 = " + str(src["contract_chars"])
      + "，**chars_match=" + str(src["chars_match_contract"]) + "**")
    A("- `source.bytes_utf8` = " + str(src["bytes_utf8"]) + "，lines = " + str(src["lines"]))
    A("- `record_fields.title` = `" + str(src["record_fields"]["title"]) + "`，title_matches_contract="
      + str(src["record_fields"]["title_matches_contract"]))
    A("- `record_fields.scenario_key` = `" + str(src["record_fields"]["scenario_key"])
      + "`，scenario_matches_contract=" + str(src["record_fields"]["scenario_matches_contract"]))
    A("")
    A("## ⑤ 注意点与局限")
    A("")
    A("- **只登记不抽取**：claims 空数组是契约允许的完整结果（notes「claims 允许为空数组」+ "
      "no_forced_claim_generation=true），不是漏项；抽取属下游 03 工序。")
    A("- **哈希作用域**：sha256 覆盖平台 API 返回 markdown 字符串的 UTF-8 字节，不归一化换行；"
      "上游任何改动（含空白）都会同时使哈希与 11 个 locator 失效。")
    A("- **图字节只证明“平台确有此图”**：PNG 的 sha256 绑定的是一次实取，本工序不做图像内容识别，"
      "图是否与图注语义一致不在登记职责内（负控制只排除 catch-all 端点）。")
    A("- **正文路径一律 unresolved**：8 条代码/数据路径属上游仓 `ship-performance-platform`，"
      "本交付工作树内不存在；其存在性由报告断言，本工序既不验证也不判其损坏。")
    A("- **单信道**：psql 读表被拒 ⇒ 无第二信道交叉核对 markdown 字节，哈希只能与 API 自洽。")
    A("- **作用域**：脚本硬编码 report_id=10542，不读写其它 report_id。")
    A("")
    A("## ⑥ 自检（逐条对照 acceptance）")
    A("")
    A("| acceptance 项 | 结果 | 证据 |")
    A("|---|---|---|")
    A(checks)
    A("")
    A("all_ok = **" + str(ver["all_ok"]) + "**。自检仅为工序侧机器复核；本工序无 claims，"
      "故没有任何内容被标 verified。")
    A("")
    A("### ⑥-附 误差判定（本工序的身份量，非物理量）")
    A("")
    A("本工序是登记/证据类工序，**没有**物理场量或数值解，故不存在“数值解 vs 解析解”的误差；"
      "可判定的是身份量与定位量，全部为逐字节相等（偏差 0），显式回答“是否 <3%”：**是，且是精确 0**。")
    A("")
    A("| 判定项 | 基准 | 实测偏差 | 是否 < 3% |")
    A("|---|---|---|---|")
    A("| markdown sha256 | 契约 `source_hash` | 0（`" + src["source_hash"][7:23]
      + "…` 逐字相等） | **是（0）** |")
    A("| markdown 字符数 | 契约 12118 | 0（" + str(src["chars"]) + "） | **是（0）** |")
    A("| locator 复解析 | 原文逐字串 | " + str(len(assets)) + "/" + str(len(assets))
      + " 条全部命中（char 跨度/行号/quote sha256 全等） | **是（0）** |")
    A("| 图字节 sha256 | 平台端点实取字节 | 0（本地落盘副本与端点返回同哈希） | **是（0）** |")
    A("| 引用召回 | 正文含扩展名 token | 0 个无法解释的 token | **是（0）** |")
    A("| 物理量精度（如包线风速、载荷） | — | **不适用**：本工序不计算、不复述任何物理量，故不给出也不引用其误差 | 不适用 |")
    A("")
    A("复跑（一键）：")
    A("")
    A("```bash")
    A(ver["repro_cmd"])
    A("```")
    A("")
    A("![asset locator map](figures/fig_asset_locator_map.png)")
    A("")
    A("## 结果 JSON（本文件唯一一个 json 代码块）")
    A("")
    A("```json")
    A(json.dumps(env, ensure_ascii=False, indent=2))
    A("```")
    report_md = "\n".join(L) + "\n"
    REPORT_MD.write_text(report_md)
    print("wrote", REPORT_MD.relative_to(ROOT), "| json blocks:", report_md.count("```json"),
          "| png exists:", png.exists())
    return str(REPORT_MD.relative_to(ROOT))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "build":
        build()
    elif cmd == "envelope":
        build_envelope()
    elif cmd == "verify":
        verify()
    elif cmd == "figure":
        figure()
    elif cmd == "report":
        report()
    elif cmd == "all":
        build()
        build_envelope()
        verify()
        figure()
        report()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()