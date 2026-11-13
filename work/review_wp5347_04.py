#!/usr/bin/env python3
"""wp-5347-04 independent re-verification of upstream wp-5347-01 asset_manifest.json.

Reviewer-side checks are recomputed from the source bytes fetched fresh from the
platform API (never from the producer's cached copy):

  R1 source_hash  : sha256(markdown bytes) == contract hash == manifest hash
  R2 char count   : len(markdown) == contract chars == manifest chars
  R3 locator span : markdown[start:end] == quote (byte exact) when offsets given
  R4 quote hash   : sha256(quote) == locator.quote_sha256
  R5 quote find   : quote is findable verbatim when no offsets are given
  R6 path literal : the registered `path` token actually occurs inside its quote (char_span only)
  R7 counts       : declared counts == recomputed counts (assets / by_kind / by_reachability)
  R8 coverage     : path-like tokens in the report that the manifest missed (recall probe)
  R9 record_field : figures[].name locator value_sha256 + declared_caption byte-exact vs record

Usage: python3 work/review_wp5347_04.py [--manifest PATH] [--json OUT]
"""
import argparse
import collections
import hashlib
import json
import os
import re
import sys
import urllib.request

BASE = os.environ["TENSOR_API_BASE"]
REPORT_ID = "5347"
CONTRACT_HASH = "sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1"
CONTRACT_CHARS = 4206
DEFAULT_MANIFEST = "/root/tp-agent/work/m15817/docs/production/wp-5347-01/asset_manifest.json"


def api_token():
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        method="POST")
    req.add_header("Content-Type", "application/json")
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    return d.get("access_token") or d.get("token") or d["data"]["access_token"]


def fetch_record():
    tok = api_token()
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID)
    req.add_header("Authorization", "Bearer " + tok)
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())


def sha(text_or_bytes):
    if isinstance(text_or_bytes, str):
        text_or_bytes = text_or_bytes.encode("utf-8")
    return "sha256:" + hashlib.sha256(text_or_bytes).hexdigest()


PATH_RE = re.compile(
    r"(?:~|/)?(?:[A-Za-z0-9_.@<>${}-]+/)+[A-Za-z0-9_.@<>-]*(?:\.[A-Za-z0-9]{1,6})?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    rec = fetch_record()
    raw = rec["markdown"].encode("utf-8")
    md = raw.decode("utf-8")
    man = json.load(open(args.manifest, encoding="utf-8"))
    figures = rec.get("figures") or []

    checks = []

    def add(check, ok, detail, blocking=True):
        checks.append({"check": check, "ok": bool(ok), "blocking": blocking,
                       "detail": detail})

    add("R1.source_hash", sha(raw) == CONTRACT_HASH
        and man["source"]["source_hash"] == CONTRACT_HASH,
        {"recomputed": sha(raw), "contract": CONTRACT_HASH,
         "manifest": man["source"]["source_hash"]})
    add("R2.char_count", len(md) == CONTRACT_CHARS
        and man["source"]["chars"] == CONTRACT_CHARS,
        {"recomputed_chars": len(md), "bytes": len(raw),
         "contract_chars": CONTRACT_CHARS, "manifest_chars": man["source"]["chars"]})

    span_bad, hash_bad, find_bad, path_bad, field_bad, caption_bad = [], [], [], [], [], []
    for a in man["assets"]:
        loc = a.get("locator", {})
        ltype = loc.get("locator_type")
        if ltype == "char_span":
            q = loc.get("quote", "")
            if "start_offset" in loc and "end_offset" in loc:
                s, e = loc["start_offset"], loc["end_offset"]
                if md[s:e] != q:
                    span_bad.append({"asset_id": a["asset_id"], "declared": [s, e],
                                     "source_slice": md[s:e], "shipped_quote": q,
                                     "byte_equal": False})
            else:
                if q not in md:
                    find_bad.append({"asset_id": a["asset_id"], "shipped_quote": q,
                                 "found_in_source": False})
            if loc.get("quote_sha256") and sha(q) != loc["quote_sha256"]:
                hash_bad.append({"asset_id": a["asset_id"], "recomputed": sha(q),
                                 "declared": loc["quote_sha256"]})
            if a["path"] not in q:
                path_bad.append({"asset_id": a["asset_id"], "path": a["path"],
                                 "source_slice": q})
        elif ltype == "record_field":
            sv, dv = loc.get("value_sha256"), None
            fname = loc.get("field", "name").split(".")[-1]
            vals = [f.get(fname) for f in figures]
            vals = [v for v in vals if isinstance(v, str)]
            if a["path"] not in vals:
                field_bad.append({"asset_id": a["asset_id"], "path": a["path"],
                                  "record_values": vals})
            dv = sha(a["path"])
            if sv and dv != sv:
                field_bad.append({"asset_id": a["asset_id"], "path": a["path"],
                                  "recomputed_value_sha256": dv,
                                  "declared_value_sha256": sv})
            cap = a.get("declared_caption")
            src_caps = [f.get("caption", "") for f in figures if f.get("name") == a["path"]]
            if cap is not None and (not src_caps or src_caps[0] != cap):
                caption_bad.append({"asset_id": a["asset_id"], "path": a["path"],
                                    "declared_caption": cap,
                                    "record_caption": src_caps[0] if src_caps else None})
        else:
            field_bad.append({"asset_id": a["asset_id"],
                              "unexpected_locator_type": ltype})

    add("R3.quote_at_declared_offsets", not span_bad,
        {"violations": span_bad, "assets_checked": len(man["assets"])})
    add("R4.quote_sha256_matches", not hash_bad, {"violations": hash_bad})
    add("R5.quote_searchable_when_no_offsets", not find_bad, {"violations": find_bad})
    add("R6.registered_path_occurs_in_quote", not path_bad, {"violations": path_bad})
    add("R9.record_field_locator_resolvable", not field_bad and not caption_bad,
        {"violations": field_bad, "caption_violations": caption_bad,
         "record_figure_names": [f.get("name") for f in figures]})

    kinds = collections.Counter(a["kind"] for a in man["assets"])
    reach = collections.Counter(a["reachability"] for a in man["assets"])
    add("R7.counts_consistent",
        man["counts"]["assets"] == len(man["assets"])
        and dict(kinds) == man["counts"]["by_kind"]
        and dict(reach) == man["counts"]["by_reachability"]
        and man["counts"]["unresolved"] == len(man.get("unresolved", [])),
        {"assets": len(man["assets"]), "declared_assets": man["counts"]["assets"],
         "by_kind_recomputed": dict(kinds), "by_kind_declared": man["counts"]["by_kind"],
         "by_reach_recomputed": dict(reach),
         "by_reach_declared": man["counts"]["by_reachability"],
         "unresolved_recomputed": len(man.get("unresolved", [])),
         "unresolved_declared": man["counts"]["unresolved"]})

    registered = {a["path"] for a in man["assets"]}
    registered |= {a["path"].lstrip("./") for a in man["assets"]}
    ordered, seen = [], set()
    for m in PATH_RE.finditer(md):
        t = m.group(0)
        if len(t) < 4 or t in seen:
            continue
        seen.add(t)
        ordered.append(t)
    missing = [t for t in ordered if t not in registered
               and t.rstrip("`").lstrip("./") not in registered]
    add("R8.coverage_probe_recall", True,
        {"tokens_found": len(ordered), "registered_paths": len(registered),
         "not_registered_count": len(missing), "not_registered": missing,
         "note": "advisory probe: manifest declares its own token grammar; misses matter "
                 "only if they are real repo paths named in the report"},
        blocking=False)

    # R10 source identity fields must match the platform record byte-exact (S14 spirit)
    ident = {}
    for k in ("title", "scenario_key", "status"):
        ident[k] = {"manifest": man["source"].get(k), "record": rec.get(k),
                    "equal": man["source"].get(k) == rec.get(k)}
    ident["tags"] = {"manifest": man["source"].get("tags"), "record": rec.get("tags"),
                     "equal": man["source"].get("tags") == rec.get("tags")}
    ident["created_at_prefix"] = {
        "manifest": man["source"].get("created_at"),
        "record_starts_with_it": (rec.get("created_at") or "").startswith(
            str(man["source"].get("created_at"))[:19])}
    add("R10.record_identity_fields_match",
        all(v.get("equal") for v in ident.values() if "equal" in v)
        and ident["created_at_prefix"]["record_starts_with_it"],
        ident)

    # R11 open-account (unresolved) closure: every unresolved path is a registered asset and
    # every registered asset appears exactly once in the open account
    ureg = [u["path"] for u in man.get("unresolved", [])]
    areg = [a["path"] for a in man["assets"]]
    add("R11.unresolved_account_closed",
        sorted(ureg) == sorted(areg) and len(set(ureg)) == len(ureg),
        {"unresolved_paths": len(ureg), "asset_paths": len(areg),
         "only_in_unresolved": sorted(set(ureg) - set(areg)),
         "only_in_assets": sorted(set(areg) - set(ureg)),
         "dup_unresolved": [p for p in set(ureg) if ureg.count(p) > 1]})

    # R12 source-report arithmetic probe: is the printed TRACKED ratio reproducible from
    # the printed count rows? (adversarial check on the upstream report, advisory for 03)
    def row_int(label):
        m = re.search(r"^\|\s*`?" + re.escape(label) + r"`?\s*\|\s*([0-9]+)\s*\|\s*([0-9]+)\s*\|",
                      md, re.M)
        return (int(m.group(1)), int(m.group(2))) if m else None

    code_r = row_int("code:TRACKED")
    test_r = row_int("test:TRACKED")
    ptr_r = row_int("指针数")
    rat_r = re.search(r"^\|\s*判\s*`?TRACKED`?\s*占比\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|",
                      md, re.M)
    arith = {"rows_found": {"code:TRACKED": code_r, "test:TRACKED": test_r,
                            "指针数": ptr_r,
                            "TRACKED占比": rat_r.groups() if rat_r else None}}
    if code_r and test_r and ptr_r and rat_r:
        printed = [float(rat_r.group(1)), float(rat_r.group(2))]
        visible = [(code_r[i] + test_r[i]) / ptr_r[i] for i in (0, 1)]
        implied_doc = [round(printed[i] * ptr_r[i]) - (code_r[i] + test_r[i]) for i in (0, 1)]
        arith.update({
            "printed_ratio": printed,
            "ratio_from_visible_rows": [round(v, 4) for v in visible],
            "reproducible_from_visible_rows": all(
                abs(printed[i] - visible[i]) < 5e-5 for i in (0, 1)),
            "implied_doc_tracked_not_shown": implied_doc,
            "conclusion": ("printed ratio needs an unshown doc:TRACKED row (%d -> %d); "
                           "not recomputable from the printed table alone, but arithmetically "
                           "consistent with such a row" % (implied_doc[0], implied_doc[1]))
            if not all(abs(printed[i] - visible[i]) < 5e-5 for i in (0, 1)) else
            "printed ratio reproducible from visible rows"})
    add("R12.report_ratio_reproducible", True, arith, blocking=False)

    result = {
        "report_id": REPORT_ID,
        "upstream_manifest": args.manifest,
        "manifest_sha256": sha(open(args.manifest, "rb").read()),
        "source_hash": sha(raw),
        "checks": checks,
        "ok": all(c["ok"] for c in checks if c["blocking"]),
    }
    txt = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json:
        open(args.json, "w", encoding="utf-8").write(txt + "\n")
    print(txt)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())