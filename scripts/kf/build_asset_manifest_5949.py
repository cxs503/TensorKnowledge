#!/usr/bin/env python3
"""Work package wp-5949-01 (01-asset-registration) — asset manifest builder + verifier.

Scope guard: touches ONLY report_id=5949. No extraction, no claim generation, no verified marks.

Every locator quote is taken verbatim from the fetched markdown bytes (never retyped), so
`quote` is guaranteed to be a substring of the source and the char span is recomputed, not stored
by hand. Identity: one asset per (kind, occurrence); repeated references keep separate evidence.

Usage:
  python3 scripts/kf/build_asset_manifest_5949.py build
  python3 scripts/kf/build_asset_manifest_5949.py result
  python3 scripts/kf/build_asset_manifest_5949.py verify
  python3 scripts/kf/build_asset_manifest_5949.py build result verify   # one-shot repro

Credentials: TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS (no secrets are stored here).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-5949-01"
REPORT_ID = "5949"
SOURCE_URI = "tensor://reports/5949"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002"
EXPECTED_CHARS = 12605

REPO = Path(__file__).resolve().parents[2]
# .gitignore drops artifacts/ at the push gate, so registered assets live under docs/kf/<pkg>/.
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
RESULT = OUT_DIR / "kf_result.json"
VERDICT = OUT_DIR / "verification.json"

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]

FILE_RE = re.compile(r"^(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|png|py|md|txt|csv|ya?ml))$")
DIR_RE = re.compile(r"^(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*/)$")
BRACE_RE = re.compile(r"^(?P<dir>[A-Za-z0-9_./-]*)\{(?P<names>[A-Za-z0-9_,.-]+)\}(?P<ext>\.[A-Za-z0-9]+)$")
SYM_RE = re.compile(r"^(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|png|py|md|txt|csv|ya?ml))::(?P<sym>\S+)$")
MODULE_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*\.){2,}[A-Za-z_][A-Za-z0-9_]*$")
TICK_RE = re.compile(r"`([^`\n]+)`")
FENCE_RE = re.compile(r"^```")


# ---------------------------------------------------------------- platform I/O


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def login():
    try:
        d = _req(BASE + "/auth/login", data=json.dumps({"username": USER, "password": PASS}).encode())
    except urllib.error.HTTPError:
        d = _req(
            BASE + "/auth/login",
            data=urllib.parse.urlencode({"username": USER, "password": PASS}).encode(),
            ctype="application/x-www-form-urlencoded",
        )
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %r" % sorted(d))
    return tok


def fetch_report(token):
    d = _req(BASE + "/tensor/reports/%s" % REPORT_ID, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    return d, md


# ---------------------------------------------------------------- parsing


def char_spans(lines):
    """1-based line -> (start_char, end_char) offsets into the full markdown string."""
    spans, pos = {}, 0
    for i, line in enumerate(lines, start=1):
        spans[i] = (pos, pos + len(line))
        pos += len(line) + 1  # '\n'
    return spans


def classify_path(path):
    p = path.lower()
    if p.endswith(".png"):
        return "figure_reference"
    if p.endswith(".py"):
        return "source_code_reference"
    if p.endswith(".md"):
        return "document_reference"
    if p.endswith((".json", ".csv", ".txt", ".yaml", ".yml")):
        return "data_artifact_reference"
    if path.endswith("/"):
        return "directory_reference"
    return "reference"


def scan_references(md):
    """Ordered, de-duplicated (token, line) references found inside inline code spans.

    Only backticked spans are parsed: prose in this report contains mathematics and
    prose parentheses, so a bare-text path regex would manufacture assets that the
    author never claimed to be artifacts.
    """
    refs, seen = [], set()
    for i, line in enumerate(md.split("\n"), start=1):
        for m in TICK_RE.finditer(line):
            tok = m.group(1).strip()
            token_forms = []
            if SYM_RE.match(tok):
                token_forms.append((tok, "symbol_reference"))
            elif FILE_RE.match(tok) or DIR_RE.match(tok):
                token_forms.append((tok, None))
            elif BRACE_RE.match(tok):
                token_forms.append((tok, "brace_expansion"))
            elif MODULE_RE.match(tok):
                token_forms.append((tok, "dotted_module"))
            for form, form_kind in token_forms:
                key = (form, i)
                if key in seen:
                    continue
                seen.add(key)
                refs.append({"line": i, "token": form, "form": form_kind})
    return refs


def expand_brace(tok):
    m = BRACE_RE.match(tok)
    if not m:
        return []
    d, names, ext = m.group("dir"), m.group("names"), m.group("ext")
    return [(d + n.strip() + ext) for n in names.split(",")]


def resolve_local(path):
    """Resolve inside the delivery worktree only (no cross-repo guessing)."""
    for cand in (REPO / path, REPO / path.lstrip("./")):
        try:
            cand = cand.resolve()
        except OSError:
            continue
        if not str(cand).startswith(str(REPO)):
            continue
        if cand.is_file():
            raw = cand.read_bytes()
            return {
                "status": "resolved",
                "scope": "delivery_worktree",
                "resolved_path": str(cand.relative_to(REPO)),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        if cand.is_dir():
            return {"status": "resolved", "scope": "delivery_worktree",
                    "resolved_path": str(cand.relative_to(REPO)), "kind": "directory"}
    return {
        "status": "unresolved",
        "scope": "delivery_worktree",
        "reason": "path is not present in the TensorKnowledge delivery worktree "
                  "(report 5949 describes TensorPlatform/report-side artifacts outside this package's boundary)",
    }


def fence_blocks(md):
    """Character spans of fenced code blocks (``` ... ```)."""
    blocks, lines, pos = [], md.split("\n"), 0
    start = None
    offs, p = [], 0
    for line in lines:
        offs.append(p)
        p += len(line) + 1
    for idx, line in enumerate(lines):
        if FENCE_RE.match(line):
            if start is None:
                start = idx
            else:
                blocks.append({
                    "start_line": start + 1,
                    "end_line": idx + 1,
                    "start_char": offs[start],
                    "end_char": offs[idx] + len(line),
                    "text": md[offs[start]:offs[idx] + len(line)],
                })
                start = None
    return blocks


DIGEST_TICK_RE = re.compile(r"`(?P<tok>[0-9a-f]{8,64})(?P<ell>…|\.\.\.)?`")
LABEL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,40}")


def _label_before(prefix, lines, lineno, back=3):
    """Nearest author-written label token before an inline-code digest (survives line wrapping)."""
    cand = prefix.rstrip()
    hit = re.search(r"([A-Za-z_][A-Za-z0-9_]{1,40})$", cand)
    if hit:
        return hit.group(1)
    for k in range(lineno - 2, max(-1, lineno - 2 - back), -1):
        prev = lines[k].rstrip()
        if not prev:
            continue
        hit = re.search(r"([A-Za-z_][A-Za-z0-9_]{1,40})$", prev)
        return hit.group(1) if hit else None
    return None


def scan_declared_digests(md):
    """Hex digests the report *declares* in inline code (e.g. artifact snapshot sha256 prefixes).

    They are registered as declared-only: a 16-hex prefix is not a sha256 and cannot be
    verified, so no `resolved` status is claimed for them.
    """
    out = []
    lines = md.split("\n")
    for i, line in enumerate(lines, start=1):
        for m in DIGEST_TICK_RE.finditer(line):
            tok, ell = m.group("tok"), m.group("ell")
            label = _label_before(line[:m.start()], lines, i)
            out.append({
                "label": label,
                "digest_prefix": tok,
                "declared_hex_chars": len(tok),
                "truncated": bool(ell) or len(tok) < 64,
                "line": i,
                "quote": line,
                "start_char": m.start(),
                "end_char": m.end(),
                "verifiable": (not ell) and len(tok) == 64,
            })
    return out


# ---------------------------------------------------------------- build


def build():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit("SOURCE HASH MISMATCH: contract=%s actual=%s" % (EXPECTED_HASH, digest))
    if len(md) != EXPECTED_CHARS:
        raise SystemExit("SOURCE CHAR COUNT MISMATCH: contract=%d actual=%d" % (EXPECTED_CHARS, len(md)))

    lines = md.split("\n")
    spans = char_spans(lines)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assets = []

    def add(asset_class, label, section, resolver, locator, note, extra=None):
        n = len(assets) + 1
        loc = dict(locator)
        if loc.get("method") == "char_span":
            sc, ec = loc["start_char"], loc["end_char"]
            loc["quote_exact"] = md[sc:ec] == loc["quote"]
            loc["unique"] = md.count(loc["quote"]) == 1
        asset = {
            "asset_id": "A%02d" % n,
            "asset_class": asset_class,
            "label": label,
            "in_report_section": section,
            "locator": loc,
            "resolution": resolver["status_mapped"],
            "resolution_check": resolver["check"],
            "note": note,
        }
        asset.update(extra or {})
        asset["resolution_detail"] = resolver["detail"]
        assets.append(asset)
        return asset

    # A01 — the source asset itself (whole document)
    add(
        "report_markdown", "报告 5949 的 markdown 源本体", "全文",
        {
            "status_mapped": "resolved_in_source",
            "check": {"check": "sha256(markdown.encode('utf-8')) == contract source_hash", "result": "resolved"},
            "detail": {"uri": SOURCE_URI, "field": SOURCE_FIELD, "chars": len(md),
                       "bytes_utf8": len(raw), "sha256": digest},
        },
        {"method": "document", "start_char": 0, "end_char": len(md), "start_line": 1,
         "end_line": len(lines), "quote": lines[0], "unique": md.count(lines[0]) == 1},
        "全文字节哈希与契约 source_hash 一致；字符数 %d 与契约 chars 一致。" % len(md),
        {"uri": SOURCE_URI, "source_field": SOURCE_FIELD, "chars": len(md),
         "bytes_utf8": len(raw), "sha256": digest, "title": meta.get("title")},
    )

    # A02.. — figures held by the platform report record
    for n, fig in enumerate(meta.get("figures") or [], start=1):
        b64 = fig.get("png_base64") or ""
        try:
            blob = base64.b64decode(b64) if b64 else b""
        except Exception:  # noqa: BLE001
            blob = b""
        add(
            "embedded_figure", "报告内嵌图 %d：%s" % (n, (fig.get("caption") or "")[:48]), "④ 图",
            {
                "status_mapped": "resolved_in_source",
                "check": {"check": "figures[%d] exists in report record; png_base64 decodes" % (n - 1),
                          "result": "resolved" if blob else "present"},
                "detail": {"index": n - 1, "name": fig.get("name"), "caption": fig.get("caption"),
                           "bytes": len(blob) or None,
                           "sha256": hashlib.sha256(blob).hexdigest() if blob else None},
            },
            {"method": "document", "start_char": 0, "end_char": len(md), "start_line": 0, "end_line": 0,
             "quote": lines[0], "unique": True},
            "图字节随报告记录提供（figures[%d]）；未抽取、未改写。" % (n - 1),
            {"uri": "%s#figures[%d]" % (SOURCE_URI, n - 1)},
        )

    # fenced code blocks: the audit-chain diagram and the one-line repro command
    for blk in fence_blocks(md):
        add(
            "code_block", "围栏代码块（审计链/复算命令，行 %d-%d）" % (blk["start_line"], blk["end_line"]),
            "审计链",
            {
                "status_mapped": "resolved_in_source",
                "check": {"check": "fenced block bytes located at recorded char span", "result": "resolved"},
                "detail": {"start_line": blk["start_line"], "end_line": blk["end_line"],
                           "chars": len(blk["text"]),
                           "sha256": hashlib.sha256(blk["text"].encode("utf-8")).hexdigest()},
            },
            {"method": "char_span", "start_char": blk["start_char"], "end_char": blk["end_char"],
             "start_line": blk["start_line"], "end_line": blk["end_line"], "quote": blk["text"],
             "unique": md.count(blk["text"]) == 1},
            "代码块按原文整块定位；块内命令原样登记，未执行（不属于本工作包职责）。",
        )

    # path-like / module-like references written inside inline code
    for ref in scan_references(md):
        ln = ref["line"]
        quote = lines[ln - 1]
        sc, ec = spans[ln]
        base = SYM_RE.match(ref["token"]).group("path") if ref["form"] == "symbol_reference" else ref["token"]
        targets = expand_brace(base) or [base]
        results = {t: resolve_local(t) for t in targets}
        n_res = sum(1 for r in results.values() if r["status"] == "resolved")
        if n_res == len(targets):
            mapped, result = "resolved_in_source", "resolved"
        else:
            mapped, result = "referenced_unresolved", "unresolved"
        add(
            classify_path(base) if ref["form"] in (None, "symbol_reference") else "module_reference",
            ref["token"], "正文/误引处（行 %d）" % ln,
            {
                "status_mapped": mapped,
                "check": {"check": "resolve each expanded target inside the delivery worktree",
                          "result": result},
                "detail": {"targets": targets, "form": ref["form"], "resolved": results},
            },
            {"method": "char_span", "start_char": sc, "end_char": ec, "start_line": ln, "end_line": ln,
             "quote": quote, "unique": md.count(quote) == 1},
            ("按原文内联代码逐字登记；%d/%d 个目标在 TensorKnowledge 工作树内命中。" % (n_res, len(targets))),
            {"path_reference": ref["token"], "uri": "%s#line=%d" % (SOURCE_URI, ln)},
        )

    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate asset_id produced")
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    digests = scan_declared_digests(md)
    inline_tokens = {r["token"] for r in scan_references(md)}
    block_names = sorted({n for blk in fence_blocks(md) for n in re.findall(
        r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|png|py|md|txt|csv|ya?ml)", blk["text"])}
        - inline_tokens)
    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
            "platform_tags": meta.get("tags"),
            "platform_figures": [
                {"index": i - 1, "name": f.get("name"), "caption": f.get("caption"),
                 "has_payload": bool(f.get("png_base64"))}
                for i, f in enumerate(meta.get("figures") or [], start=1)
            ],
        },
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + digest,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(raw),
            "fetched_via": "GET /api/v1/tensor/reports/5949",
            "generator": "scripts/kf/build_asset_manifest_5949.py",
            "contract_version": "1.0",
            "report_title": meta.get("title"),
            "report_scenario_key": meta.get("scenario_key"),
            "report_tags": meta.get("tags"),
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "claims_note": "合同 output 允许 claims 为空数组；本工序只登记资产，不做抽取、不生成 claim、不标 verified。",
        "integrity": {
            "quote_uniqueness": {
                "checked": sum(1 for a in assets if a["locator"].get("method") == "char_span"),
                "non_unique": [a["asset_id"] for a in assets
                               if a["locator"].get("method") == "char_span" and not a["locator"]["unique"]],
                "note": "document 级 locator 不参与唯一性判定（quote 取首行，仅作锚点）。",
            },
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "chars_match_contract": len(md) == EXPECTED_CHARS,
            "quotes_are_verbatim_substrings": all(
                a["locator"]["quote"] in md for a in assets if a["locator"].get("method") == "char_span"
            ),
        },
        "block_internal_names": {
            "note": "只出现在围栏代码块内部、未被正文内联引用的文件名：由整块代码块资产（A04）覆盖，"
                    "不单独登记为资产（同一字节不应产生两条身份）；此处列出以免读者以为漏登记。",
            "names": block_names,
        },
        "declared_digests": {
            "note": "报告正文声明的工件快照哈希（内联代码中的十六进制前缀）。仅登记声明值，"
                    "前缀不足 64 位或带省略号者标注 truncated=true 且 verifiable=false——不据此宣称任何币级一致。",
            "count": len(digests),
            "verifiable": sum(1 for d in digests if d["verifiable"]),
            "items": digests,
        },
        "limitations": [
            "仅登记资产：不抽取正文、不生成 claim、不写 verified（verification 由平台门计算）。",
            "登记边界=report_id 5949；未读写任何其它 report_id。",
            "报告所述 TensorPlatform 侧工件（tools/diversity/*、artifacts/in25_t2/*、tests/test_diversity_engine.py）不在本仓工作树内，一律登记为 referenced_unresolved，未凭记忆补内容。",
            "内联代码之外的裸文本不解析为路径，避免把数学/散文误登记成资产。",
            "平台 figures[] 只登记名称/说明与是否存在字节负载，不把图字节复制进 manifest。",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # verbatim local copy of the registered source bytes (hash-checked above), so the offline
    # tests can re-verify every char span without hitting the platform
    (OUT_DIR / "source_5949.md").write_bytes(raw)
    print("wrote %s (%d assets: %s)" % (MANIFEST.relative_to(REPO), len(assets), by_res))
    return manifest


# ---------------------------------------------------------------- result envelope


def emit_result():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mraw = MANIFEST.read_bytes()
    token = login()
    _meta, live_md = fetch_report(token)
    live_digest = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    if live_digest != declared:
        raise SystemExit("live source drifted from manifest: %s != %s" % (live_digest, declared))
    result = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + live_digest,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(live_md),
            "source_bytes_utf8": len(live_md.encode("utf-8")),
            "fetched_via": "GET /api/v1/tensor/reports/5949",
            "generator": "scripts/kf/build_asset_manifest_5949.py",
            "contract_version": "1.0",
        },
        "outputs": {
            "asset_manifest.json": {
                "path": str(MANIFEST.relative_to(REPO)),
                "sha256": hashlib.sha256(mraw).hexdigest(),
                "bytes": len(mraw),
                "asset_count": manifest["counts"]["assets"],
                "claims": len(manifest["claims"]),
            }
        },
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % RESULT.relative_to(REPO))
    return result


# ---------------------------------------------------------------- verify


def verify():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    lines = md.split("\n")
    checks = {}

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "json.loads OK"}
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"valid_json": {"pass": False, "detail": str(e)}}, ensure_ascii=False))
        return 1

    # schema_pass: validate against the package-local schema pinned in this repo
    schema_path = REPO / "schemas" / "asset_manifest.v1.wp-5949-01.schema.json"
    try:
        import jsonschema
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errs = sorted(jsonschema.Draft7Validator(schema).iter_errors(manifest), key=lambda e: list(e.path))
        checks["schema_pass"] = {
            "pass": not errs,
            "detail": "jsonschema against %s; errors=%s" % (schema_path.relative_to(REPO),
                                                           [e.message for e in errs[:5]]),
        }
    except ImportError:
        req = {"schema", "package_id", "task_type", "report_id", "source", "counts", "assets", "claims", "integrity"}
        missing = sorted(req - set(manifest))
        checks["schema_pass"] = {
            "pass": not missing and manifest["package_id"] == PKG and manifest["report_id"] == REPORT_ID,
            "detail": "jsonschema not installed -> structural key check; missing=%s" % missing,
        }

    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "char_span":
            q = loc["quote"]
            if md[loc["start_char"]:loc["end_char"]] != q or q not in md:
                bad.append(a["asset_id"])
            elif lines[loc["start_line"] - 1] != q and "\n" not in q:
                bad.append(a["asset_id"])
        elif not (0 <= loc["start_char"] <= len(md) and loc["end_char"] <= len(md)):
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "pass": not bad,
        "detail": "checked %d locators against live markdown bytes; failing=%s" % (len(manifest["assets"]), bad),
    }

    actual = hashlib.sha256(raw).hexdigest()
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    checks["source_hash_matches"] = {
        "pass": actual == declared == EXPECTED_HASH,
        "detail": "recomputed=%s declared=%s contract=%s" % (actual, declared, EXPECTED_HASH),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)) and all(ids),
        "detail": "assets=%d unique=%d" % (len(ids), len(set(ids))),
    }

    claims = manifest.get("claims", [])
    bad_claims = [c for c in claims if not c.get("evidence_locator") and not c.get("status")]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not bad_claims,
        "detail": "claims=%d violating=%d (empty array: vacuously satisfied per contract output.asset_manifest notes)"
                  % (len(claims), len(bad_claims)),
    }
    checks["do_not_mark_claims_as_verified"] = {
        "pass": all(c.get("status") != "verified" for c in claims),
        "detail": "claims carry no 'verified' status (claims=%d)" % len(claims),
    }

    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
    }
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["all_pass"] else 1


if __name__ == "__main__":
    acts = sys.argv[1:] or ["build", "result", "verify"]
    if "build" in acts:
        build()
    if "result" in acts:
        emit_result()
    if "verify" in acts:
        sys.exit(verify())