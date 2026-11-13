#!/usr/bin/env python3
"""Make the wp-9840-01 evidence durable inside docs/ (the repo push gate drops runs/** and
artifacts/**, so anything only there would vanish on push).

Copies (byte-identical, hash-verified) the frozen source markdown and the result envelope into
docs/wp-9840-01/ so that tests/test_kf_9840_asset_manifest.py can re-slice every locator and
recompute the contract hash offline, with no API access.
"""
import hashlib
import json
import pathlib
import sys

PACKAGE_ID = "wp-9840-01"
EXPECTED_HASH = "159d4a1419890fe82d46b49037d00273376244d1f24a6503e386c6243d882524"
RUN = pathlib.Path("runs/wp-9840-01")
DOC = pathlib.Path("docs/wp-9840-01")


def main() -> int:
    DOC.mkdir(parents=True, exist_ok=True)
    pairs = [(RUN / "report_9840.md", DOC / "source_report_9840.md"),
             (RUN / ("kf_result.%s.json" % PACKAGE_ID), DOC / ("kf_result.%s.json" % PACKAGE_ID))]
    for src, dst in pairs:
        blob = src.read_bytes()
        dst.write_bytes(blob)
        h1, h2 = hashlib.sha256(blob).hexdigest(), hashlib.sha256(dst.read_bytes()).hexdigest()
        if h1 != h2:
            print("FATAL: copy mismatch", src, dst)
            return 2
        print("mirrored %-40s %s" % (dst.name, h1[:16]))
    md = (DOC / "source_report_9840.md").read_text()
    h = hashlib.sha256(md.encode()).hexdigest()
    env = json.loads((DOC / ("kf_result.%s.json" % PACKAGE_ID)).read_text())
    ok = h == EXPECTED_HASH and env["provenance"]["source_hash"] == "sha256:" + EXPECTED_HASH
    print("durable source sha256:", h, "MATCH" if ok else "MISMATCH")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())