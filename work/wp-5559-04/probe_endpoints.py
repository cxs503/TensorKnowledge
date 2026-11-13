#!/usr/bin/env python3
"""wp-5559-04 · replay the attachment probes the upstream package reports as HTTP 404."""
import json, os, urllib.request, urllib.error, sys

tok = open("/tmp/tok.txt").read().strip()
base = os.environ["TENSOR_API_BASE"]
paths = [
    "/tensor/reports/5559/figures",
    "/tensor/reports/5559/artifacts",
    "/tensor/reports/5559/attachments",
    "/tensor/artifacts/field_synth_demo.json",
    "/tensor/reports/5559/figures/fig1_level_ice.png",
    "/tensor/reports/5559/figures/fig2_broken_ice.png",
    "/tensor/reports/5559/figures/fig3_ridges.png",
    "/tensor/reports/5559/figures/fig4_frazil.png",
    "/tensor/reports/5559/figures/fig5_scene.png",
]
out = []
for p in paths:
    try:
        r = urllib.request.urlopen(urllib.request.Request(base + p, headers={"Authorization": "Bearer " + tok}), timeout=20)
        out.append({"path": p, "status": r.status, "bytes": len(r.read())})
    except urllib.error.HTTPError as e:
        out.append({"path": p, "status": e.code, "bytes": 0})
    except Exception as e:  # noqa: BLE001
        out.append({"path": p, "status": None, "error": str(e)})
print(json.dumps(out, indent=1))
json.dump({"probes": out, "n": len(out), "http_404": sum(1 for o in out if o["status"] == 404)},
          open("work/wp-5559-04/endpoint_probes.json", "w"), indent=1)
