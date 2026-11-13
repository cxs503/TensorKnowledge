"""Independent verifier for wp-12445-01 (asset registration).

Re-derives everything from the platform source of truth, i.e. it does NOT trust
the local markdown copy: it re-fetches /tensor/reports/12445, recomputes the
sha256 and re-resolves every locator (quote at its declared char span, exactly
one occurrence in the document).

Usage: python3 scripts/kf_wp12445_verify.py
Output: runs/wp-12445-01/verify_independent.json (machine log, exit code = gate)
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

PKG = "wp-12445-01"
REPORT_ID = "12445"
CONTRACT_HASH = "f86e8247d5dff43152a883b11207b09d96d5dd70892d7f62cab187746f85f23f"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MANIFEST = pathlib.Path("docs/kf") / PKG / "asset_manifest.json"
ENVELOPE = pathlib.Path("docs/kf") / PKG / "kf_result.json"
LOG = pathlib.Path("runs") / PKG / "verify_independent.json"


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not u or not p:
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _req(BASE + path, {"username": u, "password": p})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def fetch_markdown():
    payload = _req(BASE + "/tensor/reports/" + REPORT_ID, token=login())
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    return payload["markdown"], payload


def main():
    md, payload = fetch_markdown()
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    log = {"package_id": PKG, "source": "live API " + BASE + "/tensor/reports/" + REPORT_ID}

    log["hash_live"] = digest
    log["hash_contract_match"] = digest == CONTRACT_HASH
    log["hash_manifest_match"] = digest == man["source"]["hash"]
    log["hash_envelope_match"] = env["provenance"]["source_hash"] == "sha256:" + digest
    log["chars_match"] = len(md) == man["source"]["chars"]
    log["envelope_embeds_manifest"] = env["outputs"]["asset_manifest.json"] == man

    bad = []
    for a in man["assets"]:
        loc = a["locator"]
        span_ok = md[loc["start_char"]:loc["end_char"]] == loc["quote"]
        uniq_ok = md.count(loc["quote"]) == 1
        if not (span_ok and uniq_ok):
            bad.append({"asset_id": a["asset_id"], "span_ok": span_ok, "uniq_ok": uniq_ok})
    log["asset_locators"] = {"n": len(man["assets"]), "all_resolve": not bad, "failures": bad}

    bad_a = []
    for an in man.get("anchors", []):
        span_ok = md[an["start_char"]:an["end_char"]] == an["quote"]
        uniq_ok = md.count(an["quote"]) == 1
        if not (span_ok and uniq_ok):
            bad_a.append(an["anchor_id"])
    log["anchor_locators"] = {"n": len(man.get("anchors", [])), "all_resolve": not bad_a,
                              "failures": bad_a}

    # resolution census must be internally consistent
    counts = man["counts"]
    by_res = counts["by_resolution"]
    log["counts_consistent"] = (
        counts["assets"] == len(man["assets"]) == sum(by_res.values())
        and sum(counts["by_class"].values()) == counts["assets"])

    # declared figure count vs live record figures
    live_figs = payload.get("figures") or []
    log["figure_records"] = {
        "live": [f.get("name") for f in live_figs],
        "registered": [a["label"] for a in man["assets"] if a["asset_class"] == "figure"],
    }
    log["figure_records"]["consistent"] = (
        sorted(f.get("name") for f in live_figs)
        == sorted(a["label"] for a in man["assets"] if a["asset_class"] == "figure"))

    # schema
    from jsonschema import Draft202012Validator
    env_s = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    man_s = json.loads((pathlib.Path("docs/kf") / PKG / "asset_manifest.schema.json").read_text(encoding="utf-8"))
    log["envelope_schema_pass"] = not list(Draft202012Validator(env_s).iter_errors(env))
    log["manifest_schema_pass"] = not list(Draft202012Validator(man_s).iter_errors(man))

    # ---- round-trip: the published KF-RESULT report must carry exactly one JSON
    # fence and that block must parse back to the delivered envelope verbatim.
    pub_meta = LOG.parent / "published.json"
    if pub_meta.exists():
        pid = json.loads(pub_meta.read_text(encoding="utf-8"))["kf_result_report_id"]
        live = _req(BASE + "/tensor/reports/" + str(pid), token=login())
        if isinstance(live, dict) and isinstance(live.get("data"), dict):
            live = live["data"]
        rmd = live["markdown"]
        fences = rmd.count("```json")
        block = rmd.split("```json")[1].split("```")[0].strip() if fences == 1 else "{}"
        try:
            parsed = json.loads(block)
            ok = parsed == env
        except Exception:
            ok = False
        log["published_report"] = {"id": pid, "title": live.get("title"), "json_fences": fences,
                                   "block_equals_envelope": ok,
                                   "tags_ok": ("kf-wp:" + PKG) in (live.get("tags") or []),
                                   "title_ok": live.get("title") == "KF-RESULT " + PKG,
                                   "figures": [f.get("name") for f in (live.get("figures") or [])]}
        log["published_report"]["pass"] = (fences == 1 and ok
                                          and log["published_report"]["tags_ok"]
                                          and log["published_report"]["title_ok"])

    gates = [log["hash_contract_match"], log["hash_manifest_match"], log["hash_envelope_match"],
             log["chars_match"], log["envelope_embeds_manifest"], log["asset_locators"]["all_resolve"],
             log["anchor_locators"]["all_resolve"], log["counts_consistent"],
             log["figure_records"]["consistent"], log["envelope_schema_pass"],
             log["manifest_schema_pass"]] + ([log["published_report"]["pass"]]
                                            if "published_report" in log else [])
    log["all_gates_pass"] = all(gates)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in log.items() if k not in ("asset_locators",)}, ensure_ascii=False, indent=2)[:2500])
    if not log["all_gates_pass"]:
        sys.exit("FATAL: independent verification gates failed")


if __name__ == "__main__":
    main()