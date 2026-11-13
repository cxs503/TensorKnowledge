#!/usr/bin/env python3
"""wp-9582-01: publish the KF-RESULT report to the platform (the only result channel).

Posts docs/kf/wp-9582-01/KF-RESULT-wp-9582-01.md verbatim, with tags carrying
`kf-wp:wp-9582-01` and the two measurement-derived figures inlined as png_base64.
After posting it re-reads the created report and re-reads source report 9582 to prove
(a) the envelope survives the round trip and (b) report 9582 itself was not mutated.

    python3 scripts/kf_wp9582_01_publish.py            # post + round-trip verify
    python3 scripts/kf_wp9582_01_publish.py --dry-run  # payload summary only
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "docs" / "kf" / "wp-9582-01"
REPORT_MD = PKG_DIR / "KF-RESULT-wp-9582-01.md"
MANIFEST = PKG_DIR / "asset_manifest.json"
FIG_DIR = PKG_DIR / "figures"
TITLE = "KF-RESULT wp-9582-01"
TAGS = ["kf-wp:wp-9582-01", "KF-RESULT", "asset-registration", "report-9582",
        "ice_rubble_rheology_dem", "DEM", "mu(I)"]
MISSION_ID = 15661
SOURCE_REPORT = "9582"


def base() -> str:
    return os.environ["TENSOR_API_BASE"].rstrip("/")


def login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["access_token"]


def get(path: str, tok: str) -> dict:
    req = urllib.request.Request(base() + path, headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def post(path: str, payload: dict, tok: str) -> dict:
    req = urllib.request.Request(base() + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def put(path: str, payload: dict, tok: str) -> dict:
    req = urllib.request.Request(base() + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok}, method="PUT")
    with urllib.request.urlopen(req, timeout=180) as r:
        body = r.read().decode()
    return json.loads(body) if body.strip() else {}


def figures() -> list[dict]:
    from importlib.machinery import SourceFileLoader

    mod = SourceFileLoader("kf9582fig", str(ROOT / "scripts" / "kf_wp9582_01_figures.py")).load_module()
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out = []
    for cap in mod.captions(man):
        png = FIG_DIR / cap["name"]
        out.append({"name": cap["name"], "caption": cap["caption"],
                    "png_base64": base64.b64encode(png.read_bytes()).decode()})
    return out


def main() -> int:
    md = REPORT_MD.read_text(encoding="utf-8")
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    if len(blocks) != 1:
        raise SystemExit("result markdown must hold exactly one json block, found %d" % len(blocks))
    env = json.loads(blocks[0])
    if env["provenance"]["source_hash"] != "sha256:" + man["source"]["hash"]:
        raise SystemExit("envelope provenance hash disagrees with manifest")
    payload = {
        "title": TITLE,
        "summary": ("report %s 资产登记：%d 个资产（resolved_in_source %d / referenced_unresolved %d / "
                    "declared_absent %d），markdown sha256 与契约逐字节相同（chars=%d），locator %d/%d 可复现且唯一，"
                    "acceptance 6/6 本地自检 PASS；claims=[]（未做抽取，不标 verified）。"
                    % (SOURCE_REPORT, man["counts"]["assets"], man["counts"]["resolved_in_source"],
                       man["counts"]["referenced_unresolved"], man["counts"]["declared_absent"],
                       man["source"]["chars"], man["integrity"]["quote_uniqueness"]["unique"],
                       man["counts"]["assets"])),
        "scenario_key": man["source"]["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": TAGS,
        "markdown": md,
        "figures": figures(),
    }
    if "--reconcile" in sys.argv:
        log_path = PKG_DIR / "publish.json"
        log = json.loads(log_path.read_text(encoding="utf-8"))
        tok = login()
        for a in log["attempts"]:
            back = get("/tensor/reports/%s" % a["report_id"], tok)
            a["holds_current_bytes"] = back["markdown"] == md
            a["superseded"] = not a["holds_current_bytes"]
        log["current_report_id"] = next((a["report_id"] for a in log["attempts"]
                                         if a["holds_current_bytes"]), None)
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: log[k] for k in ("current_report_id",)}, indent=2))
        print(json.dumps([{"report_id": a["report_id"], "holds_current_bytes": a["holds_current_bytes"]}
                          for a in log["attempts"]], indent=2))
        return 0 if log["current_report_id"] else 3

    if "--dry-run" in sys.argv:
        print(json.dumps({k: (v if k != "markdown" else "<%d chars>" % len(v)) for k, v in payload.items()
                          if k != "figures"}, ensure_ascii=False, indent=2))
        print("figures:", [(f["name"], len(f["png_base64"])) for f in payload["figures"]])
        return 0

    tok = login()
    upd = None
    if "--update" in sys.argv:
        upd = sys.argv[sys.argv.index("--update") + 1]
        try:
            created = put("/tensor/reports/%s" % upd, payload, tok)
            print("PUT /tensor/reports/%s ->" % upd, str(created)[:200])
        except Exception as exc:  # noqa: BLE001 - fall back to a fresh post, reported
            print("in-place update unavailable (%s); posting a new report instead" % exc)
            created = post("/tensor/reports", payload, tok)
    else:
        created = post("/tensor/reports", payload, tok)
    rid = created.get("id") or (created.get("data") or {}).get("id")
    if isinstance(rid, dict):
        rid = rid.get("id")
    if rid is None:
        rid = upd
    print("created report id:", rid, "status:", created.get("status"), "tags:", created.get("tags"))
    back = get("/tensor/reports/%s" % rid, tok)
    rb = re.findall(r"```json\n(.*?)\n```", back["markdown"], re.S)
    rt = {
        "id": rid,
        "title_matches": back.get("title") == TITLE,
        "tag_present": "kf-wp:wp-9582-01" in (back.get("tags") or []),
        "json_blocks": len(rb),
        "envelope_roundtrip_equal": len(rb) == 1 and json.loads(rb[0]) == env,
        "markdown_roundtrip_equal": back["markdown"] == md,
    }
    src = get("/tensor/reports/%s" % SOURCE_REPORT, tok)
    rt["source_9582_unchanged"] = (
        hashlib.sha256(src["markdown"].encode("utf-8")).hexdigest() == man["source"]["hash"])
    print(json.dumps(rt, ensure_ascii=False, indent=2))
    log_path = PKG_DIR / "publish.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {"attempts": []}
    log.setdefault("attempts", []).append({
        "report_id": rid, "title": TITLE, "tags": TAGS,
        "in_place_update": bool(upd) and str(rid) == str(upd),
        "roundtrip": rt})
    log["current_report_id"] = rid
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(v for k, v in rt.items() if k != "id") else 3


if __name__ == "__main__":
    raise SystemExit(main())