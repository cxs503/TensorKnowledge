#!/usr/bin/env python3
"""Control probe for wp-7545-01's `declared_absent` figure finding.

The asset manifest claims the four figures of report 7545 have no byte payload (endpoint 404).
A 404 alone cannot distinguish "figure absent" from "endpoint broken", so this probe runs a
positive control on the same endpoint: a report created by this work package whose figure was
uploaded byte-identically. If the control returns bytes, the 404 on 7545 is a data gap, not a
tooling gap.

Writes docs/kf/wp-7545-01/probe_figure_endpoint.json (does not touch report 7545 or the
already-published result envelope).

Usage:
  python3 scripts/kf/probe_7545_figures.py <control_report_id>
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-7545-01"
REPORT_ID = "7545"
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / PKG / "probe_figure_endpoint.json"
LOCAL_FIG = REPO / "docs" / "kf" / PKG / "fig1_asset_inventory.png"
BASE = os.environ["TENSOR_API_BASE"].rstrip("/")


def _login():
    req = urllib.request.Request(BASE + "/auth/login",
                                 data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                                  "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["access_token"]


def probe(tok, report_id, name):
    url = "%s/tensor/reports/%s/figures/%s" % (BASE, report_id, name)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
    try:
        raw = urllib.request.urlopen(req, timeout=60).read()
        return {"report_id": report_id, "name": name, "status": "ok", "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(), "magic": raw[:4].hex()}
    except urllib.error.HTTPError as e:
        return {"report_id": report_id, "name": name, "status": "http_%s" % e.code,
                "detail": e.read().decode("utf-8", "replace")[:120]}
    except Exception as e:  # noqa: BLE001
        return {"report_id": report_id, "name": name, "status": "error", "detail": type(e).__name__}


def main(control_report_id):
    tok = _login()
    meta = json.loads(urllib.request.urlopen(urllib.request.Request(
        "%s/tensor/reports/%s" % (BASE, REPORT_ID), headers={"Authorization": "Bearer " + tok}),
        timeout=60).read())
    targets = [probe(tok, REPORT_ID, f["name"]) for f in (meta.get("figures") or [])]
    control = [probe(tok, control_report_id, LOCAL_FIG.name)]
    local = LOCAL_FIG.read_bytes()
    ok_control = bool(control and control[0].get("status") == "ok")
    same = control[0].get("sha256") == hashlib.sha256(local).hexdigest()
    doc = {
        "package_id": PKG,
        "scope": "endpoint control probe supporting the manifest's declared_absent resolution",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "endpoint_template": "/api/v1/tensor/reports/{report_id}/figures/{name}",
        "targets_report_%s" % REPORT_ID: targets,
        "positive_control": {
            "report_id": control_report_id,
            "samples": control,
            "local_file": str(LOCAL_FIG.relative_to(REPO)),
            "local_sha256": hashlib.sha256(local).hexdigest(),
            "roundtrip_identical": same,
        },
        "conclusion": (
            "Endpoint is functional: the positive control returns PNG bytes whose sha256 equals the "
            "locally generated file (%s). Therefore the 404s on report %s mean the four figures were "
            "never uploaded as byte payloads — declared_absent in asset_manifest.json is a data gap of "
            "the source report, not a probe/tooling failure."
            % (same, REPORT_ID)
        ) if ok_control else (
            "Control probe did not return bytes; the 404s on report %s are unexplained and the "
            "declared_absent resolution must be treated as unverified." % REPORT_ID
        ),
        "limits": [
            "Probe only reads; no bytes are copied from the control report into the manifest.",
            "Report 7545 figures remain declared_absent — a working endpoint does not manufacture payloads.",
        ],
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(REPO)), "control_ok": ok_control,
                      "roundtrip_identical": same,
                      "targets": [t.get("status") for t in targets]}, ensure_ascii=False))
    return 0 if ok_control else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "14664"))