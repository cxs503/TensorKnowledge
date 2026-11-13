#!/usr/bin/env python3
"""wp-4129-04 independent re-derivation of every assertion in wp-4129-01.

Inputs (nothing else):
  work/wp-4129-04/source/report_4129.md   markdown fetched independently (sha256 pinned)
  work/wp-4129-04/source/report_4129.json raw API record
  knowledge/kf/wp-4129-01/kf_result.json  the artefact under review (upstream KO)

Emits work/wp-4129-04/review_findings.json: machine-checked table of
assertion -> recomputed value -> pass/fail, plus defect list.
No producer script or producer narrative is read.
"""
import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.request

WT = pathlib.Path(".")
SRC_MD = WT / "work/wp-4129-04/source/report_4129.md"
SRC_JSON = WT / "work/wp-4129-04/source/report_4129.json"
UP = WT / "knowledge/kf/wp-4129-01/kf_result.json"
OUT = WT / "work/wp-4129-04/review_findings.json"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")

raw = SRC_MD.read_bytes()
md = raw.decode("utf-8")
lines = md.rstrip("\n").split("\n")
rec = json.loads(SRC_JSON.read_text(encoding="utf-8"))
rec = rec.get("data", rec)
up = json.loads(UP.read_text(encoding="utf-8"))
man = up["outputs"]["asset_manifest.json"]

checks = []


def rec_chk(cid, ok, upstream_value, recomputed, note=""):
    checks.append({"check_id": cid, "pass": bool(ok), "upstream_value": upstream_value,
                   "recomputed": recomputed, "note": note})


def pointer(obj, ptr):
    cur = obj
    for part in ptr.lstrip("/").split("/"):
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur[part]
        else:
            raise KeyError(ptr)
    return cur


# ---- 1. provenance / hash identity -----------------------------------------
recomputed_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
rec_chk("source_hash", recomputed_hash == man["source"]["source_hash"],
        man["source"]["source_hash"], recomputed_hash)
rec_chk("source_bytes", len(raw) == man["source"]["bytes"], man["source"]["bytes"], len(raw))
rec_chk("source_chars", len(md) == man["source"]["chars"], man["source"]["chars"], len(md))
rec_chk("source_lines", len(lines) == man["source"]["lines"], man["source"]["lines"], len(lines))
rec_chk("source_crlf", man["source"]["has_crlf"] == ("\r\n" in md), man["source"]["has_crlf"], "\r\n" in md)
rec_chk("provenance_hash_eq_contract", up["provenance"]["source_hash"] == man["source"]["source_hash"],
        up["provenance"]["source_hash"], man["source"]["source_hash"])
for field in ("title", "scenario_key", "mission_id", "status", "created_at", "tags"):
    u = man["source"]["record_fields"].get(field)
    r = rec.get(field)
    rec_chk("record_" + field, u == r, u, r)

# ---- 2. every locator: verbatim in source / resolvable pointer -------------
def collect():
    items = []
    for f in man["identity_facts"]:
        items.append(("identity_facts/" + f["fact_id"], f.get("locator") or {}, f.get("quote")))
    for a in man["assets"]:
        items.append(("assets/" + a["asset_id"], a.get("locator") or {}, a.get("quote")))
    for v in man["vcs_references"]:
        items.append(("vcs/" + v["ref_id"], v.get("locator") or {}, v.get("quote")))
    for s in man["symbol_references"]:
        items.append(("sym/" + s["symbol_id"], s.get("locator") or {}, s.get("quote")))
    for l in man["locators"]:
        items.append(("locators/" + l["id"], l.get("locator") or {}, l.get("quote")))
    return items


items = collect()
bad_quote, bad_line, bad_ptr = [], [], []
n_md = n_md_line = n_rec = 0
for name, loc, quote in items:
    if quote is None:
        continue
    sf = loc.get("source_field")
    if sf == "markdown":
        n_md += 1
        if quote not in md:
            bad_quote.append({"locator": name, "quote": quote})
            continue
        ln = loc.get("line")
        if ln is None:
            continue
        if 1 <= ln <= len(lines) and quote in lines[ln - 1]:
            n_md_line += 1
        else:
            bad_line.append({"locator": name, "declared_line": ln,
                             "actual_lines": [i + 1 for i, l in enumerate(lines) if quote in l]})
    elif sf == "record":
        n_rec += 1
        try:
            val = pointer(rec, loc["pointer"])
        except Exception as e:
            bad_ptr.append({"locator": name, "pointer": loc.get("pointer"), "error": repr(e), "quote": quote})
            continue
        if val != quote:
            bad_ptr.append({"locator": name, "pointer": loc.get("pointer"), "value": val, "quote": quote})

rec_chk("markdown_quotes_verbatim", not bad_quote, f"{n_md} markdown quotes", f"{n_md - len(bad_quote)} verbatim")
rec_chk("markdown_quotes_on_declared_line", not bad_line, f"{n_md} markdown quotes",
        f"{n_md_line} verified on declared line")
rec_chk("record_pointers_resolve_to_quote", not bad_ptr, f"{n_rec} record locators", f"{n_rec - len(bad_ptr)} resolve+equal")

# ---- 3. each vcs/symbol token occurs inside its own locator quote ----------
tok_miss = []
for coll, idk in ((man["vcs_references"], "ref_id"), (man["symbol_references"], "symbol_id")):
    for it in coll:
        q = (it.get("locator") or {}).get("quote", "")
        t = it.get("token")
        if t and t not in q:
            tok_miss.append({"id": it[idk], "token": t, "quote": q,
                             "token_lines": [i + 1 for i, l in enumerate(lines) if t in l]})
rec_chk("token_inside_locator_quote", not tok_miss, "every vcs/symbol token inside its quote",
        f"{len(tok_miss)} outside")

# ---- 4. counts / id integrity ---------------------------------------------
hist = {}
for a in man["assets"]:
    k = f"{a['kind']}/{a['resolution']['status']}"
    hist[k] = hist.get(k, 0) + 1
rec_chk("kind_status_histogram", hist == man["counts"]["kind_status_histogram"],
        man["counts"]["kind_status_histogram"], hist)
rec_chk("assets_total", man["counts"]["assets_total"] == len(man["assets"]),
        man["counts"]["assets_total"], len(man["assets"]))
namespaces = {
    "assets": [x["asset_id"] for x in man["assets"]],
    "locators": [x["id"] for x in man["locators"]],
    "vcs_references": [x["ref_id"] for x in man["vcs_references"]],
    "symbol_references": [x["symbol_id"] for x in man["symbol_references"]],
    "identity_facts": [x["fact_id"] for x in man["identity_facts"]],
}
dup = {ns: (len(v) - len(set(v))) for ns, v in namespaces.items() if len(v) != len(set(v))}
rec_chk("id_uniqueness_per_namespace", not dup, "id_integrity.unique = true (27 ids)",
        f"no intra-namespace duplicates; sizes={ {k: len(v) for k, v in namespaces.items()} }")
flat = [i for v in namespaces.values() for i in v]
cross = sorted({i for i in flat if flat.count(i) > 1})
rec_chk("id_integrity_scope_matches_claim",
        man["id_integrity"]["ids_checked"] == len(namespaces["locators"]) and man["id_integrity"]["unique"] is True,
        {"ids_checked": man["id_integrity"]["ids_checked"], "unique": man["id_integrity"]["unique"]},
        {"locators": len(namespaces["locators"]), "intra_namespace_duplicates": dup,
         "cross_namespace_overlap": len(set(namespaces["assets"]) & set(namespaces["locators"])),
         "flat_distinct": len(set(flat))},
        "upstream uniqueness claim is namespace-local (locators only); cross-namespace id reuse is an observation, "
        "not a contradiction")
rec_chk("locators_count", man["counts"]["locators"] == len(man["locators"]),
        man["counts"]["locators"], len(man["locators"]))
resolved = sum(1 for l in man["locators"] if l.get("resolved") is True)
rec_chk("locators_resolved_count", man["counts"]["locators_resolved"] == resolved,
        man["counts"]["locators_resolved"], resolved)

# ---- 5. no verified marks / claims empty / single report scope -------------
def all_strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from all_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from all_strings(v)

verified_marks = [s for s in all_strings(man) if s.strip().lower() == "verified"]
rec_chk("no_verified_status", not verified_marks, "none", verified_marks)
rec_chk("claims_empty", man["claims"] == [] and up.get("claims", []) == [],
        "empty claims (permitted by contract)", f"{len(man['claims'])}/{len(up.get('claims', []))}")
other_reports = sorted({s for s in all_strings(up) if "reports/" in s and "reports/4129" not in s})
rec_chk("single_report_scope", not other_reports, "report 4129 only", other_reports)

# ---- 6. cross-reference prefix arithmetic re-derived -----------------------
ref = man["ref_consistency_checks"]
rec_chk("merge_short_is_prefix_of_full", "b7bbe3707838".startswith("b7bbe37078")
        == ref["merge_commit_short_is_prefix_of_full"], ref["merge_commit_short_is_prefix_of_full"],
        "b7bbe3707838".startswith("b7bbe37078"))
rec_chk("main_head_7hex_is_prefix_of_9hex", "7accc4b9c".startswith("7accc4b")
        == ref["main_head_7hex_is_prefix_of_9hex"], ref["main_head_7hex_is_prefix_of_9hex"],
        "7accc4b9c".startswith("7accc4b"))
rec_chk("branch_head_is_not_prefix_of_merge", "b7bbe3707838".startswith("c441d91")
        == ref["branch_head_prefix_of_merge_commit"], ref["branch_head_prefix_of_merge_commit"],
        "b7bbe3707838".startswith("c441d91"))
rec_chk("all_four_sha_forms_present_in_source",
        all(t in md for t in ("b7bbe3707838", "b7bbe3707", "c441d91", "7accc4b9c", "7accc4b")),
        "5 git tokens registered", [t for t in ("b7bbe3707838", "b7bbe3707", "c441d91", "7accc4b9c", "7accc4b") if t not in md])

# ---- 7. findings anchors present verbatim ---------------------------------
anchor_miss = [{"finding": f["finding_id"], "anchor": a}
               for f in man["findings"] for a in f["anchors_in_source"] if a not in md]
rec_chk("finding_anchors_verbatim", not anchor_miss, "all anchors verbatim", anchor_miss)

# ---- 7b. path-reference census vs counts.body_path_references ------------
import re as _re
SPAN = _re.compile(r"`([^`\n]+)`")
KINDS = {"file_reference", "data_artifact_reference", "source_code_reference",
         "test_reference", "directory_reference", "worktree_path_reference"}
reg_pairs = {((a.get("locator") or {}).get("line"), a["name"]) for a in man["assets"] if a["kind"] in KINDS}
site_pairs, distinct = [], set()
for i, line in enumerate(lines, 1):
    if i == 1:
        continue                      # title line: registered as identity fact, not a body reference
    for raw_tok in SPAN.findall(line):
        if raw_tok.startswith("PYTHONPATH="):
            continue                  # placeholder, not a concrete path
        if raw_tok.startswith("git ") and " src/" in raw_tok:
            site_pairs.append((i, "src/"))
            distinct.add("src/")
            continue
        if raw_tok.startswith("git ") or raw_tok.startswith("setsid") or " " in raw_tok:
            continue                  # command snippets: no path identity asserted
        if raw_tok.startswith("agent/"):
            continue                  # branch token -> vcs_references
        if not (("/" in raw_tok) or raw_tok.endswith((".md", ".py", ".json", ".png"))):
            continue                  # not path-shaped
        site_pairs.append((i, raw_tok))
        distinct.add(raw_tok)
unreg = [p for p in site_pairs if p not in reg_pairs]
rec_chk("body_path_reference_census",
        len(site_pairs) == man["counts"]["body_path_references"] and len(distinct) == man["counts"]["distinct_referenced_paths"],
        {"body_path_references": man["counts"]["body_path_references"],
         "distinct_referenced_paths": man["counts"]["distinct_referenced_paths"]},
        {"body_path_references": len(site_pairs), "distinct_referenced_paths": len(distinct),
         "unregistered_sites": unreg},
        "rule: backticked concrete path token in the body; placeholders, git/setsid spans and the branch token "
        "excluded; 'src/' of the git pathspec counted as one directory reference")

# ---- 7c. contract fields vs live record ----------------------------------
CONTRACT = {"title": "PR #77 三方合并：CHANGELOG 语义并集 + 「行保全≠文档正确」可复现审计（TensorFEM）",
            "scenario_key": "benchmark-closure", "chars": 3969,
            "source_hash": "sha256:8670fa44138a8835fac88bbc2722e7b0b8f11c9f87ce8fa728ac0971c2a0f155"}
rec_chk("contract_fields_match_record",
        rec.get("title") == CONTRACT["title"] and rec.get("scenario_key") == CONTRACT["scenario_key"]
        and len(md) == CONTRACT["chars"] and recomputed_hash == CONTRACT["source_hash"],
        CONTRACT, {"title": rec.get("title"), "scenario_key": rec.get("scenario_key"),
                   "chars": len(md), "source_hash": recomputed_hash})

# ---- 7d. every "path not present" reason is true in this worktree --------
absent_ok, absent_bad = 0, []
for u in man["unresolved"]:
    name, reason = u["name"], u["reason"]
    if not name.startswith("/") and name.startswith("r4129"):
        continue
    is_abs = name.startswith("/")
    probe = pathlib.Path(name) if is_abs else WT / name
    if "path not present in delivery worktree" in reason:
        if probe.exists():
            absent_bad.append({"asset_id": u["asset_id"], "name": name, "problem": "path exists but marked absent"})
        else:
            absent_ok += 1
    elif "same-named path exists" in reason:
        if not probe.exists():
            absent_bad.append({"asset_id": u["asset_id"], "name": name, "problem": "same-named path missing"})
        else:
            absent_ok += 1
rec_chk("unresolved_reasons_true_in_worktree", not absent_bad,
        f"{len(man['unresolved'])} unresolved entries", f"{absent_ok} re-checked, {len(absent_bad)} contradicted")

# ---- 8. independent probe of the endpoints declared 404 -------------------
probes = {}
tok = None
try:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    rq = urllib.request.Request(BASE + "/auth/login", data=body,
                                headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(rq, timeout=30) as r:
        tok = (json.loads(r.read().decode()) or {}).get("access_token")
except Exception as e:  # pragma: no cover - network optional
    probes["login_error"] = repr(e)

paths = ["/tensor/reports/4129/artifacts",
         "/tensor/reports/4129/figures/merge_audit.png",
         "/tensor/reports/4129/figures/plate_gate.png"]
for path in paths:
    try:
        rq = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + str(tok)})
        with urllib.request.urlopen(rq, timeout=30) as r:
            probes[path] = {"status": r.status, "bytes": len(r.read())}
    except urllib.error.HTTPError as e:
        probes[path] = {"status": e.code, "bytes": len(e.read())}
    except Exception as e:  # pragma: no cover
        probes[path] = {"error": repr(e)}
rec_chk("artifacts_probe_404",
        probes.get("/tensor/reports/4129/artifacts", {}).get("status")
        == man["source"]["platform_attachment_probes"]["GET /tensor/reports/4129/artifacts"]["http_status"],
        man["source"]["platform_attachment_probes"]["GET /tensor/reports/4129/artifacts"]["http_status"],
        probes.get("/tensor/reports/4129/artifacts"))

out = {
    "reviewed_artifact": "knowledge/kf/wp-4129-01/kf_result.json (wp-4129-01 / asset_manifest.json)",
    "source_sha256": recomputed_hash,
    "source_bytes": len(raw),
    "source_chars": len(md),
    "checks_total": len(checks),
    "checks_passed": sum(1 for c in checks if c["pass"]),
    "checks": checks,
    "quotation_surface": {"markdown_quotes": n_md, "markdown_quotes_on_declared_line": n_md_line,
                          "record_locators": n_rec},
    "defects": {"quote_not_verbatim": bad_quote, "quote_not_on_declared_line": bad_line,
                "record_pointer_mismatch": bad_ptr, "token_outside_quote": tok_miss,
                "finding_anchor_missing": anchor_miss},
    "probes": probes,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: out[k] for k in ("checks_total", "checks_passed")}, ensure_ascii=False))
for c in checks:
    print("PASS " if c["pass"] else "FAIL ", c["check_id"], "|", c["upstream_value"], "|", c["recomputed"])
print("defects:", json.dumps(out["defects"], ensure_ascii=False)[:3000])
print("probes:", json.dumps(probes, ensure_ascii=False))