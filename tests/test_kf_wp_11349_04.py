"""wp-11349-04 审核产物的回归测试：断言不变量，而不是只跑一遍脚本。

覆盖：
1) 已交付 review_report.json 的判据矩阵形状（18 项，唯一 fail = C09 schema 漂移，裁决 needs-fix）；
2) 本包 kf_result.json / review_events 对仓内 schema 严格通过（无超集字段）；
3) 采样篡改测试：把上游 manifest 某条 locator 的 start_char 篡改 1 个字符，
   审核脚本必须把 C04b 判 fail（证明切片判据真的在断言，不是装饰）；
4) 源哈希判据：篡改源 markdown 一个字符必须让 C01/C02 fail。
"""
import json
import os
import shutil
import subprocess
import sys

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "docs/kf/wp-11349-01")
OUTDIR = os.path.join(ROOT, "docs/kf/wp-11349-04")
SNAP = os.path.join(ROOT, "runs/wp-11349-04/report_11349_api.json")


def run_verify(pkg, out, snapshot=SNAP, probe=None):
    cmd = [sys.executable, os.path.join(ROOT, "scripts/kf/verify_wp_11349_04.py"),
           "--pkg", pkg, "--out", out, "--snapshot", snapshot]
    if probe:
        cmd += ["--probe-json", probe]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.load(open(out))


def checks_by_id(rr):
    return {c["id"]: c["result"] for c in rr["checks"]}


def test_delivered_review_matrix():
    rr = json.load(open(os.path.join(OUTDIR, "review_report.json")))
    res = checks_by_id(rr)
    assert len(res) == 18
    failed = sorted(k for k, v in res.items() if v != "pass")
    assert failed == ["C09"], failed
    assert rr["verdict"] == "needs-fix"
    assert rr["reviewed_package"] == "wp-11349-01"
    # 每条 locator 的 slice 判据必须真的被断言过
    assert res["C04b"] == "pass" and res["C04a"] == "pass"


def test_envelope_and_event_schema_strict():
    env = json.load(open(os.path.join(OUTDIR, "kf_result.json")))
    sch = json.load(open(os.path.join(ROOT, "schemas/kf_result.v1.schema.json")))
    assert list(jsonschema.Draft202012Validator(sch).iter_errors(env)) == []
    ev = json.load(open(os.path.join(ROOT, "schemas/review-event.schema.json")))
    assert list(jsonschema.Draft202012Validator(ev).iter_errors(env["outputs"]["review_events.json"][0])) == []
    assert env["provenance"]["source_hash"] == \
        "sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80"


def test_tampered_locator_is_detected(tmp_path):
    pkg = tmp_path / "pkg"
    shutil.copytree(PKG, pkg)
    m = json.load(open(pkg / "asset_manifest.json"))
    a = next(a for a in m["assets"] if a["asset_id"] == "A03")
    a["locator"]["start_char"] += 1  # 切片错 1 字符：quote 仍唯一，但 md[s:e] != quote
    json.dump(m, open(pkg / "asset_manifest.json", "w"), ensure_ascii=False)
    rr = run_verify(str(pkg), str(tmp_path / "rr.json"))
    res = checks_by_id(rr)
    assert res["C04b"] == "fail", res
    assert rr["verdict"] == "needs-fix"


def test_tampered_source_hash_is_detected(tmp_path):
    snap = tmp_path / "snap.json"
    d = json.load(open(SNAP))
    d["markdown"] = d["markdown"].replace("补记：", "补记:")  # 1 字符级改动
    json.dump(d, open(snap, "w"), ensure_ascii=False)
    rr = run_verify(PKG, str(tmp_path / "rr.json"), snapshot=str(snap))
    res = checks_by_id(rr)
    assert res["C01"] == "fail" and res["C02"] == "fail", res
    assert rr["verdict"] == "needs-fix"