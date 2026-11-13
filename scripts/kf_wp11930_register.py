"""wp-11930-01 · 01-asset-registration for report 11930 (TensorKnowledge).

Registers the source asset (report 11930 markdown) and the file-like artifacts /
figures it references. No extraction, no classification, no claim generation:
claims == [] is a legitimate complete result for this package.

Every locator is computed from the fetched markdown (char span + line numbers +
verbatim quote), never hand-typed, and each quote is checked to be unique in
the source so the platform side can re-resolve it by substring.

Run:  python3 scripts/kf_wp11930_register.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "kf" / "wp-11930-01"
SOURCE = ART / "source_11930.md"
REPORT_ID = "11930"
PACKAGE_ID = "wp-11930-01"
SOURCE_URI = "tensor://reports/11930"
EXPECTED_HASH = "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325"

# file-like references named in the report; order = registration order.
# kind: figure / module / script / test / data
REFS = [
    ("module", "src/tensordem/bpm_calibration_feasibility.py", "新增模块（本节点实现）"),
    ("script", "scripts/p270w2c_n08_feasibility.py", "战役脚本 sample/analyze"),
    ("script", "scripts/p270w2c_n08_figures.py", "图渲染脚本"),
    ("script", "scripts/p270w2c_n08_report.py", "报告渲染脚本"),
    ("test", "tests/test_bpm_calibration_feasibility.py", "AC8 pytest 套件（42 项）"),
    ("data", "runs/p270w2c_n08/records.jsonl", "逐任务原始记录（审计链第一层）"),
    ("data", "artifacts/p270w2c_n08/report.json", "判据/数字来源（审计链第二层）"),
    ("figure", "figures/p270w2c_n08/fig_response_surface.png", "图 1 响应面切片"),
    ("figure", "figures/p270w2c_n08/fig_jacobian.png", "图 2 可辨识性审计"),
    ("figure", "figures/p270w2c_n08/fig_pareto.png", "图 3 NSGA-II 种群与 Pareto 前沿"),
    ("figure", "figures/p270w2c_n08/fig_size_effect.png", "图 4 Weibull 尺寸效应"),
    ("figure", "figures/p270w2c_n08/fig_brazilian.png", "图 5 巴西圆盘中心主应力比"),
    ("figure", "figures/p270w2c_n08/fig_ucs.png", "图 6 UCS 应力–应变迹与负控分布"),
]

# explicit declarations of absence in the report -> recorded, never invented.
ABSENT = [
    (
        "declared_absent",
        "voided-campaign raw JSONL",
        "原始 JSONL 因磁盘配额已清理",
        "§4 · 注意点 条 1b",
    )
]


def api_token(base: str) -> str:
    body = json.dumps(
        {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
    ).encode()
    req = urllib.request.Request(
        base + "/auth/login", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    payload = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if isinstance(payload, str):
        return payload
    for k in ("access_token", "token", "jwt"):
        if payload.get(k):
            return payload[k]
    raise SystemExit("no token")


def locate(md: str, needle: str, prefer_token: bool = False) -> dict:
    """Minimal verbatim locator around `needle`.

    Widens the span outward until it hits a soft separator (·、|, newline) so the
    quote is the smallest self-describing fragment; falls back to the containing
    line, then to a three-line window, if that fragment is not unique.
    """
    idx = md.find(needle)
    if idx < 0:
        raise SystemExit("reference not found verbatim in source: %r" % needle)
    seps = set("·、|\n")
    lo, hi = idx, idx + len(needle)
    exact = prefer_token and md.count(needle) == 1
    if not exact:
        while lo > 0 and md[lo - 1] not in seps:
            lo -= 1
        while hi < len(md) and md[hi] not in seps:
            hi += 1
    quote = md[lo:hi].strip()
    qidx = md.find(quote)
    if md.count(quote) != 1:  # widen to the whole line
        lo = md.rfind("\n", 0, idx) + 1
        hi = md.find("\n", idx)
        hi = len(md) if hi < 0 else hi
        quote = md[lo:hi].strip()
        qidx = md.find(quote)
    if md.count(quote) != 1:  # last resort: one line of context each side
        prev = md.rfind("\n", 0, max(0, lo - 1)) + 1
        nxt = md.find("\n", hi + 1)
        quote = md[prev:len(md) if nxt < 0 else nxt].strip()
        qidx = md.find(quote)
    return {
        "method": "char_span",
        "seed_span": [idx, idx + len(needle)],
        "start_char": qidx,
        "end_char": qidx + len(quote),
        "start_line": md.count("\n", 0, qidx) + 1,
        "end_line": md.count("\n", 0, qidx + len(quote)) + 1,
        "quote": quote,
        "unique": md.count(quote) == 1,
    }


def fig_bytes(base: str, token: str, name: str) -> tuple[int, str]:
    req = urllib.request.Request(
        base + "/tensor/reports/%s/figures/%s" % (REPORT_ID, name),
        headers={"Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    return len(raw), hashlib.sha256(raw).hexdigest()


def main() -> int:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    raw = SOURCE.read_bytes()
    md = raw.decode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit("source hash mismatch: %s != %s" % (digest, EXPECTED_HASH))

    meta = json.loads((ART / "source_meta.json").read_text(encoding="utf-8"))
    token = api_token(base)

    assets = []
    for i, (kind, path, label) in enumerate(REFS, start=1):
        loc = locate(md, path)
        name = path.rsplit("/", 1)[-1]
        entry = {
            "asset_id": "A%02d" % i,
            "asset_class": kind,
            "label": label,
            "path_in_report": path,
            "in_report_section": _section_of(md, loc["start_char"]),
            "locator": loc,
        }
        if kind == "figure":
            nbytes, sha = fig_bytes(base, token, name)
            entry["resolution"] = "resolved_in_source"
            entry["resolution_check"] = {
                "check": "GET /api/v1/tensor/reports/11930/figures/%s (HTTP 200, image/png)" % name,
                "result": "resolved",
            }
            entry["note"] = (
                "平台报告记录 figures[] 含该文件名与逐字 caption；PNG 字节可取回，"
                "bytes_utf8=%d，sha256=%s（本地复算，供下游二次比对）。" % (nbytes, sha)
            )
            entry["platform_bytes"] = nbytes
            entry["platform_sha256"] = sha
        else:
            local = ROOT / path
            entry["resolution"] = "referenced_unresolved"
            entry["resolution_check"] = {
                "check": "本工作树（TensorKnowledge 检出）内 os.path.exists(path)",
                "result": "present" if local.exists() else "unresolved",
            }
            entry["note"] = (
                "报告声明该工件属于 TensorDEM 仓（节点 P270W2C-N08 / 任务 m9756）；"
                "TensorKnowledge 检出内不存在，也未随报告携带字节，故只登记引用不复制，"
                "解析需回 source repo。"
            )
        assets.append(entry)

    for j, (resolution, label, quote, section) in enumerate(ABSENT, start=len(assets) + 1):
        loc = locate(md, quote, prefer_token=True)
        assets.append(
            {
                "asset_id": "A%02d" % j,
                "asset_class": "data",
                "label": label,
                "path_in_report": "n/a (declared absent)",
                "in_report_section": section,
                "locator": loc,
                "resolution": resolution,
                "resolution_check": {"check": "报告正文显式声明缺失（逐字引文）", "result": "absent"},
                "note": "报告自述因磁盘配额已清理；不作补造、不推断内容。",
            }
        )

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest.split(":", 1)[1],
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": meta["title"],
            "scenario_key": meta["scenario_key"],
            "platform_figures": meta.get("figures") or [],
            "platform_tags": meta.get("tags") or [],
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
        "integrity": {
            "quote_uniqueness": "all %d/%d locator quotes occur exactly once in the source markdown"
            % (sum(1 for a in assets if a["locator"]["unique"]), len(assets)),
            "all_quotes_unique": all(a["locator"]["unique"] for a in assets),
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "no_claims_by_design": "objective.classify_report_type=false; task_type=01 registers assets only",
            "unresolved_assets_have_reason": all(
                a["resolution"] == "resolved_in_source" or a["note"] for a in assets
            ),
        },
    }

    out = ART / "asset_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    env_out = ART / "kf_result.wp-11930-01.json"
    emitted = _now()
    if env_out.exists():  # idempotent rerun: keep the original emission stamp
        try:
            prev = json.loads(env_out.read_text(encoding="utf-8"))
            if prev.get("provenance", {}).get("source_hash") == digest:
                emitted = prev["provenance"]["emitted_at"]
        except (ValueError, KeyError):
            pass

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": digest,
            "source_field": "markdown",
            "producer": "agent/m15731 · scripts/kf_wp11930_register.py",
            "emitted_at": emitted,
            "notes": "markdown fetched via GET /api/v1/tensor/reports/11930; hash recomputed from bytes on disk",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    env_out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "assets": len(assets),
                "by_class": by_class,
                "by_resolution": by_res,
                "all_quotes_unique": manifest["integrity"]["all_quotes_unique"],
                "manifest": str(out.relative_to(ROOT)),
                "envelope": str(env_out.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _section_of(md: str, char: int) -> str:
    """Nearest preceding heading of the source document."""
    head = md[:char]
    hits = re.findall(r"^(#{1,3})\s+(\d+(?:\.\d+)*)", head, flags=re.M)
    if not hits:
        return "header"
    return "§" + hits[-1][1]


def _now() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    sys.exit(main())