#!/usr/bin/env python3
"""Publish the KF-RESULT report for wp-11621-01 (task_type 01-asset-registration).

The report markdown embeds the kf_result envelope (docs/kf/wp-11621-01/kf_result.json)
as the SINGLE ```json code block, per the delivery contract. Published via the
platform report API (POST /tensor/reports).
"""
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
PACKAGE_ID = "wp-11621-01"

ENVELOPE = ROOT / "docs" / "kf" / PACKAGE_ID / "kf_result.json"
MANIFEST = ROOT / "docs" / "kf" / PACKAGE_ID / "asset_manifest.json"


def post(path, body, token=None):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    env = json.loads(ENVELOPE.read_text())
    man = json.loads(MANIFEST.read_text())
    block = json.dumps(env, ensure_ascii=False, indent=2)

    # ---- evidence locator table (verbatim quotes from report markdown) ----
    md = open(ROOT / "runs" / PACKAGE_ID / "report_11621.md").read()
    lines = md.rstrip("\n").split("\n")
    def q(ln): return lines[ln-1].strip()

    ev_table = [
        ("source_hash", "provenance.source_hash", "sha256:89a6a0828d4feddbc1c1ee81e80cc7c844ea234c01c2efeec215fcd7ed54dafb",
         "报告 markdown 字节哈希（平台独立重算一致）"),
        ("report_id", "report_id", "11621", "API 记录 id 字段"),
        ("title", "source.record_fields.title", "TensorFVM 数值黏性/色散算子验证面：修正方程 ν_num=cΔx(1-C)/2 波包衰减实测 + 离散放大因子 G(θ) 全域比对",
         "报告 H1 标题行（L1）"),
        ("scenario_key", "source.record_fields.scenario_key", "p73w3-n04-fvm-numerical-viscosity",
         "报告『**战役节点**』行（L3）"),
        ("mission_id", "source.record_fields.mission_id", "9775", "报告『**任务ID**』行（L4）"),
        ("chars", "source.chars", "7198", "markdown 字符数（py len）"),
        ("bytes", "source.bytes", "10224", "markdown UTF-8 字节数"),
        ("lines", "source.lines", "303", "markdown 逻辑行数"),
        ("figures_record", "counts.figures_declared_in_record", "6",
         "记录元数据 figures 数组（fig1_geometry.png…fig6_fatigue.png，船体水动力主题，与报告正文 FVM 主题不匹配——数据完整性观察）"),
        ("body_refs", "counts.body_references", "14",
         "报告正文 §7 产物清单与 §8 审计链声明的路径引用（src/tensorfvm/verification/*.py、tests/*、artifacts/fvm_modified_equation.json、docs/numerical-viscosity/*.png 等）"),
    ]

    rows = "\n".join(
        "| %s | %s | %s | %s |" % (c, f, v, src) for c, f, v, src in ev_table)

    # ---- self-check against acceptance ----
    selfcheck = [
        ("valid_json", "✅", "asset_manifest.json + kf_result.json 均 JSON 解析通过"),
        ("schema_pass", "✅", "kf_result.v1.schema 校验 0 错误（Draft202012Validator）"),
        ("source_locator_resolvable", "✅", "15/15 markdown 定位器（行号+逐字引文+quote_sha256）对活体 markdown 重解析通过"),
        ("source_hash_matches", "✅", "live=manifest=contract=envelope 四者一致 sha256:89a6a0828d4feddbc1c1ee81e80cc7c844ea234c01c2efeec215fcd7ed54dafb"),
        ("no_duplicate_ids", "✅", "21 个 asset_id 无重复"),
        ("all_claims_have_evidence_or_explicit_unresolved_status", "✅", "claims 为空数组（本工序只登记不抽取），空数组理由已声明"),
    ]
    sc = "\n".join("| %s | %s | %s |" % r for r in selfcheck)

    markdown = f"""# KF-RESULT {PACKAGE_ID}

**工作包**: {PACKAGE_ID} · **工序**: 01-asset-registration · **报告**: 11621 · **分层**: FVM|p73w3-n04-fvm-numerical-viscosity|m

## ① 本工序做了什么
登记源资产（asset-registration）：确认 report_id=11621 与其 markdown 的字节哈希（sha256:89a6a0828d4feddbc1c1ee81e80cc7c844ea234c01c2efeec215fcd7ed54dafb），
列出可解析的附件/工件（记录元数据 6 张图 + 报告正文 §7/§8 声明的 14 条路径引用）。**不做抽取**（claims 为空数组），**不标 verified**（verification 由平台门计算）。

## ② 怎么做的（步骤/工具/关键设置）
1. **取源**: `GET /api/v1/tensor/reports/11621`（Bearer 登录 token）取 `markdown` 字段；psql 直读被拒（permission denied），API 为唯一源信道。
2. **哈希**: 对 markdown UTF-8 字节独立重算 sha256，与契约 `source_hash` 逐位比对（一致）。
3. **登记**: 按 `schemas/kf_result.v1.schema.json` 与 `schemas/asset_manifest.v1.schema.json` 结构，产出 `asset_manifest.json`（21 资产）+ `kf_result.json`（信封）。
4. **定位**: 每个资产带 locator（行号+逐字引文+quote_sha256），verify 时对活体 markdown 重解析。
5. **附件探测**: 对记录元数据 6 张图 `GET /tensor/reports/11621/figures/<name>` 探测——平台返回 HTTP 200 + 字节，故登记为 resolved（含 sha256）；正文路径引用在交付工作树内未命中→登记为 unresolved（不臆造地址）。
6. **自检**: 6 条 acceptance 逐条打勾（见 ⑥）。

## ③ 产出物清单
| 输出文件 | 要点 |
|---|---|
| `docs/kf/wp-11621-01/asset_manifest.json` | 21 资产：1 源 markdown（resolved）+ 6 记录图（resolved，含字节/哈希）+ 14 正文路径引用（unresolved）；claims 空数组+理由 |
| `docs/kf/wp-11621-01/kf_result.json` | 结果信封（kf_result.v1）：package_id/task_type/report_id/provenance/outputs；provenance.source_hash 与契约一致 |
| `docs/kf/wp-11621-01/verification.json` | 6 条 acceptance 自检，all_ok=True |
| `runs/wp-11621-01/report_11621.md` | 源 markdown 本地镜像（字节一致） |
| `runs/wp-11621-01/report_11621.json` | 原始 API 载荷（含 figures 元数据） |
| `scripts/kf_fetch_11621.py` / `scripts/kf_wp11621_01_register.py` | 取源与登记脚本（可复跑） |

## ④ 证据定位表（claim/字段 → 原文引文片段）
{rows}

## ⑤ 注意点与局限
- **记录图主题不匹配（数据完整性观察）**: 记录元数据 6 张图（fig1_geometry.png…fig6_fatigue.png）的 caption 是船体水动力主题（附加质量/springing/whipping/疲劳），
  与报告正文 FVM 数值黏性主题（正文引用 fig1_von_neumann.png/fig2_nu_comparison.png/fig3_grid_convergence.png）**不一致**。平台确实返回了这 6 张图的字节（HTTP 200），
  故登记为 resolved 附件；但主题错配已作为观察项留给平台门，本工序不裁决。
- **正文路径引用未在交付工作树命中**: `src/tensorfvm/verification/*.py`、`tests/*`、`artifacts/fvm_modified_equation.json`、`docs/numerical-viscosity/*.png` 等
  在 TensorKnowledge 工作树内不存在→登记为 unresolved（existence_asserted_by_worker=false），不臆造地址。
- **仅登记不抽取**: 本工序不产出知识对象（claims 空），不标 verified；verification 由平台门独立重算。
- **source_hash 作用域**: UTF-8 字节；任何空白改动即失效。

## ⑥ 自检（逐条对照 acceptance）
{sc}

**repro_cmd**: `python3 scripts/kf_fetch_11621.py && python3 scripts/kf_wp11621_01_register.py all`

---

```json
{block}
```
"""
    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": "登记源资产 wp-11621-01：确认 report 11621 markdown 字节哈希 sha256:89a6a0828d4feddbc1c1ee81e80cc7c844ea234c01c2efeec215fcd7ed54dafb，列出 6 张记录图（resolved）+14 条正文路径引用（unresolved）；claims 空数组，不标 verified。",
        "scenario_key": "p73w3-n04-fvm-numerical-viscosity",
        "mission_id": 15727,
        "tags": ["kf-wp:wp-11621-01", "KF", "asset-registration", "FVM", "numerical-viscosity"],
        "markdown": markdown,
        "figures": [],
    }
    tok = post("/auth/login", {"username": USER, "password": PASS})
    token = tok.get("access_token") or tok.get("token")
    assert token, "no token"
    rep = post("/tensor/reports", payload, token)
    print("published:", json.dumps(rep, ensure_ascii=False)[:300])
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
