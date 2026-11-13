#!/usr/bin/env python3
"""Post-publish self-check: the published markdown must carry EXACTLY ONE ```json block and
that block must equal the delivered envelope byte-for-byte in structure (dict equality).
Re-fetches the published report from the platform (id taken from publish_receipt.json).
"""
import json
import os
import pathlib
import re
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")
RUN = pathlib.Path("runs/wp-9840-01")


def api(path, data=None, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, body, timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> int:
    if len(sys.argv) > 1:
        raw = '{"id": %s}' % sys.argv[1]
    else:
        raw = (RUN / "publish_receipt.json").read_text()
    try:
        rid = json.loads(raw)["id"]
    except json.JSONDecodeError:
        # the POST response echoes the embedded figures (large); the receipt may be truncated
        rid = int(re.search(r'"id"\s*:\s*(\d+)', raw).group(1))
    tok = api("/auth/login", {"username": USER, "password": PASS})["access_token"]
    rep = api("/tensor/reports/%d" % rid, token=tok)
    md = rep["markdown"]
    blocks = re.findall(r"```(\w*)\n(.*?)```", md, re.S)
    js = [b for b in blocks if b[0] == "json"]
    env = json.loads((RUN / "kf_result.wp-9840-01.json").read_text())
    fences = md.count("```")
    ok = len(js) == 1 and fences == 2          # exactly one fence pair in the whole document
    same = ok and json.loads(js[0][1]) == env
    tags = rep.get("tags") or []
    secs = [l for l in md.split("\n") if l.startswith("## ")]
    out = dict(report_id=rid, title=rep.get("title"), fenced_blocks=[b[0] for b in blocks],
               fence_markers=fences, json_blocks=len(js), json_block_equals_envelope=same,
               tags=tags, tag_ok="kf-wp:wp-9840-01" in tags,
               sections=secs, section_count=len(secs), markdown_chars=len(md),
               figures=len(rep.get("figures") or []),
               verdict="PASS" if (ok and same and "kf-wp:wp-9840-01" in tags and len(secs) >= 6) else "FAIL")
    (RUN / "postcheck_publish.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    pathlib.Path("docs/wp-9840-01/postcheck_publish.json").write_text(
        (RUN / "postcheck_publish.json").read_text())
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())