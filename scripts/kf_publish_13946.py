"""wp-13946-01: render the KF-RESULT markdown and publish it to the platform.

Markdown is rendered programmatically from the artifacts (manifest + verification JSON), so every
number in the six sections is injected, never typed. The single ```json block is the result
envelope byte-for-byte; the script asserts that before publishing.

Outputs:
  docs/wp-13946-01/KF-RESULT_wp-13946-01.md   (durable copy of the delivered markdown)
  runs/wp-13946-01/published.json             (platform response: id/title/status)
  docs/wp-13946-01/published.json             (mirror)

Usage: python3 scripts/kf_publish_13946.py [--dry-run]
Credentials: env TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE (never written to tree).
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

PACKAGE_ID = "wp-13946-01"
REPORT_ID = "13946"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
DOC = pathlib.Path("docs/wp-13946-01")
RUN = pathlib.Path("runs/wp-13946-01")
MAN = pathlib.Path("artifacts/wp-13946-01/asset_manifest.json")
VER = pathlib.Path("artifacts/wp-13946-01/verification.json")
ENV = RUN / "kf_result.wp-13946-01.json"
FIG = DOC / "fig1_asset_coverage.png"

REPRO = ("cd <worktree> && python3 scripts/kf_fetch_13946.py && python3 scripts/kf_register_13946.py"
         " && python3 scripts/kf_verify_13946.py && python3 scripts/kf_figures_13946.py"
         " && python3 -m pytest tests/test_kf_wp13946_01_asset_manifest.py -q")


def _cell(s: str) -> str:
    """Flatten a verbatim excerpt onto one display line: newlines -> ' / ', over-length tails cut.

    No escaping is applied (the ④ section renders quotes inside blockquotes, not table cells), so a
    reader can copy the visible text straight back into the source; truncation is marked so a prefix
    is never mistaken for the full quote.
    """
    t = s.replace("\n", " / ")
    if len(t) > 110:
        t = t[:110] + " …（截断）"
    return t


def render(m: dict, v: dict) -> str:
    c = m["counts"]
    br = c["by_resolution"]
    checks = v["checks"]
    ok = lambda k: "✔" if checks.get(k, {}).get("pass") else "✘"  # noqa: E731
    rows = "\n".join(
        "- **%s** · `%s` · `%s` · %s\n  > %s" % (a["asset_id"], a["asset_class"], a["resolution"],
                                              a["in_report_section"], _cell(a["locator"]["quote"]))
        for a in m["assets"])
    files = [
        ("artifacts/wp-13946-01/asset_manifest.json", "资产清单本体（schema=asset_manifest.v1）"),
        ("artifacts/wp-13946-01/verification.json", "独立复核逐项结果（8 项检查）"),
        ("artifacts/wp-13946-01/fig1_asset_coverage.png", "覆盖率图（数字全部来自清单 JSON）"),
        ("runs/wp-13946-01/report_13946.md", "取回的源 markdown（哈希门控通过）"),
        ("runs/wp-13946-01/kf_result.wp-13946-01.json", "结果信封（本报告唯一 json 块的原文）"),
        ("docs/wp-13946-01/asset_manifest.json", "耐久镜像（artifacts/ 被 .gitignore/push 门丢弃）"),
        ("schemas/asset_manifest.wp-13946-01.schema.json", "本包钉住的本地 schema（同名共享 schema 的 const 是别的包）"),
        ("scripts/kf_fetch_13946.py", "取源+哈希门控"),
        ("scripts/kf_register_13946.py", "登记器（逐条唯一性断言，不手抄）"),
        ("scripts/kf_verify_13946.py", "独立复核器（不 import 登记器）"),
        ("scripts/kf_figures_13946.py", "出图（断言与清单自洽）"),
        ("tests/test_kf_wp13946_01_asset_manifest.py", "pytest 包装：离线+在线双重复核"),
    ]
    ftab = "\n".join("| `%s` | %s |" % (f, d) for f, d in files)

    md = f"""# KF-RESULT {PACKAGE_ID}

**工序**：`{m['task_type']}`（lane C）｜**源**：`{m['source']['uri']}`（字段 `{m['source']['field']}`）
**源标题**：{m['source']['title']}
**scenario_key**：`{m['source']['scenario_key']}`｜**报告**：`{REPORT_ID}`

## ① 本工序做了什么

把 report `{REPORT_ID}` 的 markdown 作为**唯一源**登记成资产清单：确认 report_id 与 markdown 字节哈希、
逐条定位报告中可解析的结构（表格/参数/方法/结论/图注/复现命令）与**引用了但本工作树不可解析**的工件
（跨仓代码/脚本/结果集/测试），并显式登记报告自己声明缺失的入口（μ vs 实验的实验数据集）。

- 资产数 **{c['assets']}**：`resolved_in_source` **{br.get('resolved_in_source', 0)}** /
  `referenced_unresolved` **{br.get('referenced_unresolved', 0)}** /
  `declared_absent` **{br.get('declared_absent', 0)}**。
- **不抽知识**：`claims=[]`（契约 `objective.register_assets=true`、`classify_report_type=false`，
  「claims 允许为空数组」）——报告里的 F1/F2/F3 结论只作为资产 A04 原文登记，未被升级成 claim、未标 verified。
- 源哈希 `sha256:{m['source']['hash']}`，与契约一致；字符数 {m['source']['chars']}（= 契约值）。
- **未**做：附件字节校验（图件二进制）、跨仓代码解析、报告结论的独立复算（见 ⑤）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET $TENSOR_API_BASE/tensor/reports/{REPORT_ID}`（`/auth/login` 取 token）→ `markdown` 字段。
   直连库 `psql -d tensorplatform -c "select markdown from tensor_reports where id={REPORT_ID}"` **被拒**
   （`ERROR: permission denied for table tensor_reports`），故 API 是唯一取源信道；单信道限制已记在 ⑤。
2. **哈希门控**：`scripts/kf_fetch_13946.py` 落盘前重算 `sha256(markdown)` 并断言等于契约值
   （不匹配即 `exit 2`，不落盘）。
3. **定位**：`scripts/kf_register_13946.py` 用**行区间锚**（非手抄）切片，逐条断言
   `md.count(quote)==1`（全文唯一）且 `md[start_char:end_char]==quote`（char span 与 quote 不可能漂移）；
   一行的密集引用（A16–A23）改用**精确子串锚**，避免三条资产共用同一行定位。
4. **缺失不臆造**：跨仓路径/通配目录/未给 URL 或 commit 的引用一律 `referenced_unresolved`
   并写清原因；报告显式说没有的数据集记 `declared_absent`。**没有给出任何编造地址**。
5. **schema**：`schemas/asset_manifest.v1.schema.json` 的 `package_id`/`report_id` 是别的包（`wp-448-01`/`448`）
   的 `const`，直接复用无法校验本包；做法是新增**钉住本包身份**的同构 schema
   `schemas/asset_manifest.wp-13946-01.schema.json`，不改共享文件（否则会静默放宽其它包的检查）。
6. **独立复核**：`scripts/kf_verify_13946.py` **不 import 登记器**，重新从 API 取 markdown、重算哈希、
   重新解析每个 locator，逐条映射 acceptance；结果写 `verification.json`。
7. **测试**：`tests/test_kf_wp13946_01_asset_manifest.py` 双层——离线层（committed 清单 vs 运行副本）
   + 在线层（vs 服务端字节，API 不可达时 skip 而非 pass）。
8. **出图**：`scripts/kf_figures_13946.py` 只读清单 JSON，出图时断言「按类堆叠合计 == counts.assets」
   且「按 resolution 合计 == counts.by_resolution」——图与数字不可能各说各话。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
{ftab}

**复现（一键）**：
```
{REPRO}
```

## ④ 证据定位表（字段 → 原文引文片段）

引文均为报告 markdown 的**逐字切片**（完整 quote 与 `char_span` 见 `asset_manifest.json`；此处为显示副本，
换行画作 ` / `、超 110 字符处截断并标注 `…（截断）`，不做任何转义/改写）。

{rows}

源级定位：`{m['source']['uri']}#markdown`，`len={m['source']['chars']}`，`sha256={m['source']['hash']}`。

## ⑤ 注意点与局限

1. **单信道取源**：`psql` 无权限，哈希一致性只能对 API 返回的字节成立；若平台存有第二份 markdown 且与
   API 不同，本单无法发现这层差异（判据仍是契约给的 sha256，已逐字节相等）。
2. **图件只登记链接，不登记字节**：A08 是报告正文的 markdown 图片链接
   `../figures/shear_cell_m14840_servo.png`，本工作树无 `figures/` 目录；平台记录里该图只有
   name+caption（`figures[0]`）而无 png 字节，故 `referenced_unresolved`，不给哈希。
3. **跨仓引用不可解析**：A16–A22（`src/tensordem/shear_cell.py`、`scripts/m14840/*.py`、
   `artifacts/shear_cell_m14840/*.json`、`docs/SHEAR_CELL_..._tables.md`、
   `tests/test_shear_cell_servo_audit_m14840.py`）都是 TensorDEM 侧相对路径，报告未给 commit/URL；
   本单**未**去别的仓解析它们，也未复跑报告声称的「8 passed」。
4. **不判定报告结论**：F1/F2/F3 是源报告的作者结论，本工序只登记其原文位置；**没有任何一条被标 verified**，
   也没有替平台门做 verification。`μ vs 实验` 一项按原文登记为「无数据集 → 不能声称」的 honest-FAIL。
5. **占位符原样保留**：A14 复现命令含 `<tag>/<mode>/<strain>` 占位符，报告未给取值，本单不实例化。
6. **本包 schema 是本地钉住的**：若平台侧 canonical schema 与本仓不同，以平台门为准，本清单需重跑而非手改。

## ⑥ 自检（逐条对照 acceptance，honest）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | {ok('valid_json')} | manifest + envelope 均可 `json.loads` |
| schema_pass | {ok('schema_pass')} | 按 `schemas/asset_manifest.wp-13946-01.schema.json` + `schemas/kf_result.v1.schema.json` 校验，0 error |
| source_locator_resolvable | {ok('source_locator_resolvable')} | {c['assets']}/{c['assets']} 条 locator 在服务端字节上重新解析通过（span 相等 + 全文唯一 + start_line 相符） |
| source_hash_matches | {ok('source_hash_matches')} | 重算 `{m['source']['hash']}` == 契约；manifest/envelope 同值 |
| no_duplicate_ids | {ok('no_duplicate_ids')} | {c['assets']} 个 asset_id 全互异 |
| all_claims_have_evidence_or_explicit_unresolved_status | {ok('all_claims_have_evidence_or_explicit_unresolved_status')} | `claims=[]`（空数组=契约允许的完整结果，未造 claim） |

附加自查（非契约项，跑在本单自家复核器里）：
`no_asset_marked_verified` {ok('no_asset_marked_verified')}（无任何资产/claim 被标 verified）、
`scope_single_report` {ok('scope_single_report')}（manifest/envelope 的 report_id 均为 `{REPORT_ID}`，未触碰其它报告）。

**诚实说明（未完成/不可判定项，不粉饰）**：
- 图件 png 字节未校验（不可得，见 ⑤.2）；跨仓代码/结果集/测试未解析、未复跑（见 ⑤.3）。
- 本单**不**为「直剪盒伺服偏置已修」或「μ vs 实验 <10%」背书；这两条都是源报告的陈述，
  登记≠验证，verification 由平台门计算。

---

```json
{ENV.read_text().rstrip()}
```
"""
    return md


def check_single_json_block(md: str, env_text: str) -> None:
    assert md.count("```json") == 1, "markdown must contain exactly one json block"
    body = md.split("```json", 1)[1].split("```", 1)[0].strip()
    assert json.loads(body) == json.loads(env_text), "json block must be the result envelope verbatim"


def call(path: str, body: dict | None, tok: str | None = None, timeout: int = 120):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main() -> int:
    dry = "--dry-run" in sys.argv
    m = json.loads(MAN.read_text())
    v = json.loads(VER.read_text())
    env_text = (ENV).read_text()
    md = render(m, v)
    check_single_json_block(md, env_text)
    DOC.mkdir(parents=True, exist_ok=True)
    (DOC / "KF-RESULT_wp-13946-01.md").write_text(md)
    print("rendered", DOC / "KF-RESULT_wp-13946-01.md", len(md), "chars; single json block OK")
    if dry:
        return 0

    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    assert st == 200, (st, body[:400])
    tok = json.loads(body)["access_token"]
    fig_b64 = base64.b64encode(FIG.read_bytes()).decode() if FIG.exists() else ""
    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": (
            f"{PACKAGE_ID} (01-asset-registration, report {REPORT_ID}): source markdown sha256 "
            f"recomputed = contract ({m['source']['hash'][:16]}...); {m['counts']['assets']} assets "
            f"registered ({m['counts']['by_resolution'].get('resolved_in_source', 0)} resolved / "
            f"{m['counts']['by_resolution'].get('referenced_unresolved', 0)} unresolved / "
            f"{m['counts']['by_resolution'].get('declared_absent', 0)} declared absent); "
            "claims=[] (registration only, nothing marked verified)."
        ),
        "scenario_key": m["source"]["scenario_key"],
        "mission_id": 15769,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:" + REPORT_ID,
                 "lane:C", "draft", "knowledge-factory"],
        "markdown": md,
        "figures": [{
            "name": FIG.name,
            "caption": (f"{PACKAGE_ID} asset coverage: A = {m['counts']['assets']} assets by class "
                        f"stacked by resolution; B = locator char spans in the {m['source']['chars']}"
                        "-char source markdown. All numbers read from asset_manifest.json."),
            "png_base64": fig_b64,
        }] if fig_b64 else [],
    }
    st, resp = call("/tensor/reports", payload, tok)
    print(st, resp[:500])
    if st not in (200, 201):
        return 1
    try:
        rec = json.loads(resp)
    except Exception:  # noqa: BLE001
        rec = {"raw": resp}
    out = json.dumps({"http_status": st, "response": rec}, ensure_ascii=False, indent=2) + "\n"
    (RUN / "published.json").write_text(out)
    (DOC / "published.json").write_text(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())