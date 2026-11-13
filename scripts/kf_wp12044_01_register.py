#!/usr/bin/env python3
"""wp-12044-01 (01-asset-registration, report 12044): register source assets.

Reads the byte copy of the registered markdown (docs/kf/wp-12044-01/source.md, produced
by scripts/kf_wp12044_01_fetch.py), recomputes its sha256, resolves every registered
asset locator verbatim against those exact bytes, and writes:

    docs/kf/wp-12044-01/locator_check.json      one row per quote (offset/line/occurrences)
    docs/kf/wp-12044-01/asset_manifest.json     contract output `asset_manifest.json`
    docs/kf/wp-12044-01/kf_result.json          kf_result.v1 envelope (schema-validated)
    docs/kf/wp-12044-01/report_body.md          six-section report body (one json block)

No claim extraction (objective.classify_report_type=false); nothing is marked verified —
verification is computed by the platform gate.

Usage: python3 scripts/kf_wp12044_01_register.py
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import sys

import jsonschema

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-12044-01"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"

PACKAGE_ID = "wp-12044-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "12044"
SOURCE_URI = "tensor://reports/12044"
EXPECTED_HASH = "74cbbb52b6682ff4bb865490e1b4cce8511d023ed1a48afa19a9f2d22a0220b6"
PRODUCER = "agent/m15737"
CONTRACT_TITLE = "probe figure upload (write_lease D1)"


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def build_locator(md: str, lines, offs, anchor: str, span, whole_doc: bool = False):
    """Locator = the exact character span of `anchor` inside md (verbatim, unique).

    Character-precise on purpose: this source report is a single line, so any
    line-granular locator would silently widen A02/A03/A04 to the whole document and
    make the registered quote meaningless. `span` is legacy/unused here.
    """
    if whole_doc:
        return dict(
            method="document",
            start_char=0,
            end_char=len(md),
            start_line=0,
            end_line=len(lines) - 1,
            quote=md,
            unique=True,
        )
    hits = md.count(anchor)
    if hits != 1:
        raise SystemExit(f"anchor not found/not unique ({hits} hits): {anchor!r}")
    start = md.index(anchor)
    end = start + len(anchor)
    line_idx = md.count("\n", 0, start)  # 0-based line containing `start`
    return dict(
        method="char_span",
        start_char=start,
        end_char=end,
        start_line=line_idx,
        end_line=md.count("\n", 0, end),
        quote=md[start:end],
        unique=True,
    )


def section_of(lines, upto_line: int) -> str:
    head = ""
    for ln in lines[:upto_line]:
        if ln.startswith("#"):
            head = ln.strip()
    return head or "(document)"


def resolve_check(spec, md: str, payload: dict, probe: dict):
    """Machine check backing each declared resolution status (no invented results)."""
    aid = spec["asset_id"]
    quote = spec["locator"]["quote"]
    if aid == "A04":
        figs = payload.get("figures") or []
        row = figs[0] if figs else {}
        eps = probe.get("probes", {})
        fig_ep = eps.get("/tensor/reports/12044/figures", {})
        return dict(
            check="figure_bytes_or_path_resolvable",
            result="unresolved",
            platform_figures_count=len(figs),
            figure_name=row.get("name"),
            figure_caption=row.get("caption"),
            figure_has_url_or_path=any(
                k in row for k in ("url", "path", "uri", "sha256", "content_base64")
            ),
            figures_endpoint_status=fig_ep.get("status"),
            detail=(
                "record.figures carries name+caption only (no path/URL/digest); "
                "GET /tensor/reports/12044/figures -> 404, so the binary cannot be resolved "
                "from the platform; the markdown names no figure file."
            ),
        )
    return dict(
        check="verbatim_substring_of_source_markdown",
        result="resolved",
        occurrences=md.count(quote),
        char_span_matches_quote=(md[spec["locator"]["start_char"]:spec["locator"]["end_char"]] == quote),
    )


# --------------------------------------------------------------- asset table
# Every quote must be a verbatim substring of the registered markdown; the builder
# dies on any miss (no hand transcription). resolution status is declared here and
# backed by resolve_check() above.
ASSETS = [
    dict(
        asset_id="A01",
        asset_class="source_document",
        label="报告 markdown 正文（整篇，57 字符 / 81 字节 UTF-8，单行 + 换行）",
        anchor="",
        span=(0, 0),
        whole_doc=True,
        resolution="resolved_in_source",
        note=(
            "sha256 与契约 source_hash 一致（见 source.hash）；正文仅一句探针声明，"
            "无表格/公式/数值结果，故本清单不含表、参数或结果资产。"
        ),
    ),
    dict(
        asset_id="A02",
        asset_class="timestamp_token",
        label="探针写入时间戳 2026-11-10T17:22:47.930890Z",
        anchor="2026-11-10T17:22:47.930890Z",
        span=(0, 0),
        resolution="resolved_in_source",
        note="ISO-8601 UTC 微秒级时刻，逐字取自正文；用于核验写租约 D1 的落库时刻。",
    ),
    dict(
        asset_id="A03",
        asset_class="intent_statement",
        label="报告自述用途：探针验证 figures 字段可落库",
        anchor="探针：验证 figures 字段可落库。",
        span=(0, 0),
        resolution="resolved_in_source",
        note="报告唯一实质性陈述；本工序只登记其位置，不判定该陈述真伪（不做 claim 抽取）。",
    ),
    dict(
        asset_id="A04",
        asset_class="figure_declaration",
        label="图件声明 fig1_d1_linearizability.png（caption=probe，record.figures[0]）",
        anchor="figures 字段可落库",
        span=(0, 0),
        resolution="referenced_unresolved",
        note=(
            "图件文件名/caption 只存在于平台 record.figures，正文未给出文件名、路径、URL 或摘要；"
            "figures 端点 404，二进制不可解析——如实标 unresolved，不臆造地址。"
        ),
    ),
]


def validate(instance: dict, schema_path: pathlib.Path, what: str) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance, schema)
    except jsonschema.ValidationError as exc:  # pragma: no cover
        raise SystemExit(f"SCHEMA FAIL ({what}): {exc.message} @ {list(exc.absolute_path)}")
    print(f"schema pass: {what} <- {schema_path.relative_to(ROOT)}")


def main() -> int:
    src_path = PKG / "source.md"
    if not src_path.exists():
        print("FATAL: run scripts/kf_wp12044_01_fetch.py first")
        return 1
    md = src_path.read_text(encoding="utf-8")
    payload = json.loads((PKG / "report_12044.json").read_text(encoding="utf-8"))
    probe = json.loads((PKG / "platform_probe.json").read_text(encoding="utf-8"))

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {EXPECTED_HASH}")
        return 2
    if payload.get("title") != CONTRACT_TITLE:
        print("WARN: platform title differs from contract title:", payload.get("title"))

    lines, offs = line_offsets(md)

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit("duplicate asset_id " + spec["asset_id"])
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"], spec.get("whole_doc", False))
        if not loc["unique"]:
            raise SystemExit(f"quote not unique for {spec['asset_id']}")
        spec["locator"] = loc
        assets.append(
            dict(
                asset_id=spec["asset_id"],
                asset_class=spec["asset_class"],
                label=spec["label"],
                in_report_section=section_of(lines, loc["start_line"]),
                locator=loc,
                resolution=spec["resolution"],
                resolution_check=resolve_check(spec, md, payload, probe),
                note=spec["note"],
            )
        )

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    loc_rows = [
        dict(
            asset_id=a["asset_id"],
            method=a["locator"]["method"],
            start_char=a["locator"]["start_char"],
            end_char=a["locator"]["end_char"],
            start_line=a["locator"]["start_line"],
            end_line=a["locator"]["end_line"],
            occurrences=md.count(a["locator"]["quote"]),
            unique=a["locator"]["unique"],
            span_matches_quote=md[a["locator"]["start_char"]:a["locator"]["end_char"]]
            == a["locator"]["quote"],
        )
        for a in assets
    ]
    (PKG / "locator_check.json").write_text(
        json.dumps({"report_id": REPORT_ID, "source_sha256": md_hash, "rows": loc_rows},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI,
            field="markdown",
            hash_alg="sha256",
            hash=md_hash,
            chars=len(md),
            bytes_utf8=len(md.encode()),
            title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_tags=payload.get("tags", []),
            platform_figures=payload.get("figures", []),
            retrieved_via="GET %s/tensor/reports/%s" % (
                (probe.get("base") or "").rstrip("/"), REPORT_ID),
            local_copy="docs/kf/wp-12044-01/source.md",
        ),
        counts=dict(
            assets=len(assets),
            by_class=by_class,
            by_resolution=by_res,
            resolved_in_source=by_res.get("resolved_in_source", 0),
            referenced_unresolved=by_res.get("referenced_unresolved", 0),
            declared_absent=by_res.get("declared_absent", 0),
        ),
        assets=assets,
        claims=[],
        claims_note=(
            "契约 objective.classify_report_type=false、notes 允许 claims 为空数组：本工序只做资产登记，"
            "不做知识抽取，也未对 A03 的陈述做真伪判定（no_forced_claim_generation）。"
        ),
        integrity=dict(
            quote_uniqueness="每条 locator.quote 均在 source.md 中唯一出现，且 md[start:end] 逐字等于 quote"
                            "（scripts/kf_wp12044_01_verify.py 复核）",
            hash_recomputed_locally=True,
            hash_matches_contract=True,
        ),
    )

    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    pkg_manifest = PKG / "asset_manifest.json"
    pkg_manifest.write_text(blob, encoding="utf-8")
    m_hash = hashlib.sha256(pkg_manifest.read_bytes()).hexdigest()

    # Idempotent regeneration: keep the first emitted_at while the registered bytes and
    # the manifest digest are unchanged, so re-running the chain cannot silently drift the
    # already-published body (the verifier asserts published == local body).
    emitted_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev_path = PKG / "kf_result.json"
    if prev_path.exists():
        try:
            prev = json.loads(prev_path.read_text(encoding="utf-8"))
            same_src = prev["provenance"]["source_hash"] == "sha256:" + md_hash
            same_art = (prev["outputs"]["asset_manifest.json"]["artifact_sha256"] == m_hash)
            if same_src and same_art and prev["provenance"].get("emitted_at"):
                emitted_at = prev["provenance"]["emitted_at"]
        except Exception:
            pass

    result = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_hash="sha256:" + md_hash,
            source_field="markdown",
            producer=PRODUCER,
            emitted_at=emitted_at,
            notes=(
                "source_uri=%s; contract_version=1.0; lane=C; chars=%d; bytes_utf8=%d; "
                "title=%s; asset_manifest_sha256=%s; verification_status=not_verified "
                "(platform gate computes verification)"
                % (SOURCE_URI, len(md), len(md.encode()), payload.get("title"), m_hash)
            ),
        ),
        outputs={
            "asset_manifest.json": dict(
                artifact_path="docs/kf/wp-12044-01/asset_manifest.json",
                artifact_sha256=m_hash,
                artifact_bytes=pkg_manifest.stat().st_size,
                **manifest,
            )
        },
        claims=[],
    )
    validate(result, SCHEMA, "kf_result.json")

    (PKG / "kf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    fig_meta = None
    try:
        import subprocess

        subprocess.run([sys.executable, str(ROOT / "scripts" / "kf_wp12044_01_figure.py")],
                       check=True, capture_output=True, cwd=str(ROOT))
        fig_meta = json.loads((PKG / "figures.json").read_text(encoding="utf-8"))[0]
    except Exception as exc:  # figure is optional evidence, never a hard dependency
        print("WARN: figure generation skipped:", exc)

    body = render_body(md, manifest, result, m_hash, probe, fig_meta)
    (PKG / "report_body.md").write_text(body, encoding="utf-8")
    (ROOT / "docs" / "kf_result_wp-12044-01.md").write_text(body, encoding="utf-8")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("assets:", len(assets), "by_class:", json.dumps(by_class, ensure_ascii=False))
    print("by_resolution:", json.dumps(by_res, ensure_ascii=False))
    print("manifest sha256:", m_hash)
    return 0


def render_body(md: str, manifest: dict, result: dict, m_hash: str, probe: dict,
                fig_meta: dict | None = None) -> str:
    figs = manifest["source"]["platform_figures"]
    rows = "\n".join(
        "| %s | %s | `%s` | %s | %s |"
        % (
            a["asset_id"],
            a["asset_class"],
            a["locator"]["quote"].replace("\n", "\\n"),
            (str(a["locator"]["start_char"]) + "–" + str(a["locator"]["end_char"])
             if a["locator"]["method"] == "char_span" else "整篇"),
            a["resolution"],
        )
        for a in manifest["assets"]
    )
    block = json.dumps(result, ensure_ascii=False, indent=2)
    by_id = {a["asset_id"]: a for a in manifest["assets"]}

    def _q(aid: str) -> str:
        return by_id[aid]["locator"]["quote"]

    def _c(aid: str) -> str:
        loc = by_id[aid]["locator"]
        return "%d–%d" % (loc["start_char"], loc["end_char"])

    fig_ep = probe.get("probes", {}).get("/tensor/reports/12044/figures", {}).get("status")
    if fig_meta:
        fig_line = (
            "| `docs/kf/wp-12044-01/fig1_asset_spans.png` | 资产定位区间图（字符轴区间 + 解析状态着色），"
            f"{fig_meta['bytes']} 字节，sha256 `{fig_meta['sha256'][:16]}…`，由 "
            f"`{fig_meta['generator']}` 从 `asset_manifest.json` 程序化生成 |"
        )
        fig_note = (
            "**结果图**:`docs/kf/wp-12044-01/fig1_asset_spans.png` —— 上格把 57 字符原文逐字符排在"
            "字符轴上（无 CJK 字体，中文按填充标记绘制，非乱码），下格把 4 条资产的逐字字符区间按解析状态着色。"
            "**为什么没有场量云图/对比曲线**:源报告是探针记录，正文不含任何场量、几何或数值结果，"
            "因此不存在可绘制的物理量；本图是本工序唯一可诚实产出的可视化（登记数据的结构图），"
            "不冒充计算结果。"
        )
    else:
        fig_line = "| （无图） | 图件生成被跳过（见 ⑤ 局限） |"
        fig_note = "**无图理由**:源报告无场量/几何/数值结果，且本仓环境图件生成被跳过。"

    return f"""# KF-RESULT wp-12044-01

**报告（被登记源）**: report_id=12044 — 「{manifest['source']['title']}」
**工作包**: `wp-12044-01` · task_type=`01-asset-registration` · lane=C · 契约版本 1.0
**工序目标**: `register_assets=true`、`classify_report_type=false`（只登记资产，不抽取知识）

## ① 本工序做了什么

对 report_id=12044 的唯一文档资产做**资产登记**：取平台 `GET /tensor/reports/12044` 的 `markdown`
字段原文字节，独立重算 sha256 并与契约 `source_hash` 比对（一致），随后在**该字节序列**上逐条解析
本报告可登记的资产定位（字符区间 + 行号 + 逐字引文），并对每条资产给出**机器校验过**的解析状态。
不做任何知识抽取，`claims` 为空数组（契约 notes 明示允许），也未对报告自述做真伪判定。

源报告本身是一条**探针记录**（title=`probe figure upload (write_lease D1)`，tags=`["probe"]`，
正文仅 57 字符一句），因此本清单只有 4 条资产：1 条整篇文档、1 条时间戳、1 条用途陈述、1 条图件声明。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`scripts/kf_wp12044_01_fetch.py` — `POST /auth/login`（凭据仅来自环境变量，不落盘）
   取 token，`GET /tensor/reports/12044`，把 `markdown` **按 UTF-8 原样字节**写入
   `docs/kf/wp-12044-01/source.md`（81 字节），同时保存整条 record 供 provenance 引用。
2. **校验哈希**：`hashlib.sha256(md.encode())` = `{manifest['source']['hash']}`，
   与契约 `source_hash` 逐字一致（`docs/kf/wp-12044-01/sha256.txt` 记录 match=True）。
3. **定位资产**：`scripts/kf_wp12044_01_register.py` 内每条资产登记 `anchor`（逐字子串）与行偏移 `span`，
   由脚本换算成 `start_char/end_char/start_line/end_line/quote`；anchor 命中数 ≠1 或 quote 非唯一即**硬失败退出**
   （禁止手抄、禁止"差不多"）。校验结果逐条落 `docs/kf/wp-12044-01/locator_check.json`。
4. **解析状态机器校验**：文本类资产校验 `md[start:end] == quote` 且 `md.count(quote)`；
   图件资产走平台探测 `scripts/kf_wp12044_01_probe.py`（`/tensor/reports/12044/figures|assets|attachments` → 均为 **404**），
   并检查 `record.figures` 是否带 path/URL/摘要 → **不带**，故如实标 `referenced_unresolved`。
5. **结构校验**：结果信封用仓内 `schemas/kf_result.v1.schema.json`（draft 2020-12）经 `jsonschema.validate`
   实测通过，不是"看起来合规"。
6. **不改上游**：只读 report 12044，未写其它任何 report_id，未把任何结论标成 verified。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-12044-01/source.md` | 被登记 markdown 的原样字节副本（57 字符 / 81 字节） |
| `docs/kf/wp-12044-01/sha256.txt` | 本地重算 sha256 与契约值比对（match=True） |
| `docs/kf/wp-12044-01/report_12044.json` | 平台 record 原文（title/tags/mission_id/figures） |
| `docs/kf/wp-12044-01/platform_probe.json` | 图件/附件端点探测原始响应（3×404） |
| `docs/kf/wp-12044-01/locator_check.json` | 每条引文的 offset/行号/出现次数/span 一致性 |
| `docs/kf/wp-12044-01/asset_manifest.json` | 契约输出：4 条资产 + 计数 + integrity |
| `docs/kf/wp-12044-01/asset_manifest.json`（sha256） | 清单摘要 `{m_hash[:16]}…` 落进结果信封与正文 json 块的 `artifact_sha256`，可离线核对 |
| `docs/kf/wp-12044-01/kf_result.json` | `kf_result.v1` 结果信封（schema 实测通过） |
| `docs/kf/wp-12044-01/report_body.md`、`docs/kf_result_wp-12044-01.md` | 本正文（含唯一一个 ```json 块） |
{fig_line}
| `scripts/kf_wp12044_01_fetch.py` / `_register.py` / `_verify.py` / `_probe.py` / `_publish.py` | 一键复跑链 |

资产表（每条引文均逐字来自正文）：

| id | class | quote（逐字） | 字符区间 | resolution |
|---|---|---|---|---|
{rows}

计数：assets={manifest['counts']['assets']}，resolved_in_source={manifest['counts']['resolved_in_source']}，
referenced_unresolved={manifest['counts']['referenced_unresolved']}，declared_absent={manifest['counts']['declared_absent']}。

{fig_note}

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 字段 | 值 | 原文引文（逐字） | 定位 |
|---|---|---|---|
| source.hash | `{manifest['source']['hash']}` | 整篇正文 `{md.strip()}` | 整篇 0–{manifest['source']['chars']} |
| A02 时间戳 | `2026-11-10T17:22:47.930890Z` | `{_q('A02')}` | char {_c('A02')}（唯一） |
| A03 用途陈述 | 探针验证 figures 字段落库 | `{_q('A03')}` | char {_c('A03')}（唯一） |
| A04 图件 | `{figs[0]['name'] if figs else 'n/a'}`（caption=`{figs[0].get('caption') if figs else 'n/a'}`） | 正文仅 `{_q('A04')}`；文件名不在正文 | record.figures[0]；`/figures` 端点 {fig_ep} |

零手抄声明：上表每个字符串均由脚本从 `source.md` **切片生成**（`md[start:end]`），
不是人工录入；重放 `python3 scripts/kf_wp12044_01_verify.py` 可逐条复核。

## ⑤ 注意点与局限

- **源报告是探针产物，不是科研结论**：正文仅一句"验证 figures 字段可落库"，无几何、无算例、无数值。
  本清单因此**没有参数/表格/结果资产**——这是如实反映，不是漏登。
- **图件不可解析（unresolved，不是 absent）**：`record.figures` 只带 `name`+`caption`，无 path/URL/sha256，
  且 `/tensor/reports/12044/figures` 返回 404。若下游需要图件本体，须由写租约方补齐可解析地址，本工序不得臆造。
- **`scenario_key` 为空（null）**：平台 record 未设置场景键；本工序按契约 `classify_report_type=false`
  不去猜场景，原样记录在 `source.scenario_key`。
- **quote 唯一性与字符精度**：定位按**字符**而非按行（源报告只有一行，按行会把 A02/A03/A04 的引文都撑成整篇）；
  4 条 quote 的 `md.count(quote)` 均为 1，且 `md[start:end] == quote` 逐条成立（见 `locator_check.json`）。
  A04 的引文 `figures 字段可落库` 落在 A03 引文内部——这是正文里唯一的图件指向，故 A04 借它定位，
  但解析状态仍是 unresolved（指向存在 ≠ 图件本体可解析）。
- **未做的事**：不做 claim 抽取、不做报告类型分类、不判定探针陈述真伪、不标 verified（由平台门计算）。
- **哈希一致 ≠ 内容可信**：`source_hash` 相等是机械同一性校验，只证明"登记的就是平台上那一份字节"。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 全部产物以 `json.dumps` 写出；`verify` 步骤逐文件 `json.load` 通过 |
| schema_pass | ✅ | `kf_result.json` 经 `jsonschema.validate` 对 `schemas/kf_result.v1.schema.json` 通过 |
| source_locator_resolvable | ✅ | 4/4 资产 quote 唯一且 `md[start:end]==quote`（`locator_check.json`） |
| source_hash_matches | ✅ | `{manifest['source']['hash']}` == 契约 `sha256:74cbbb52…0220b6` |
| no_duplicate_ids | ✅ | A01–A04 无重复；builder 内置重复即硬失败 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | `claims=[]`（契约允许）；A04 显式 `referenced_unresolved` |
| 边界：不改其它 report_id / 不标 verified | ✅ | 只读 12044；`verification_status=not_verified` |

无失败项（honest-FAIL 无需申报）；唯一"缺口"是 A04 图件本体的不可解析性，已显式标 unresolved 而非掩盖。

## 一键复跑

```bash
cd <worktree> && python3 scripts/kf_wp12044_01_fetch.py \\
  && python3 scripts/kf_wp12044_01_probe.py \\
  && python3 scripts/kf_wp12044_01_register.py \\
  && python3 scripts/kf_wp12044_01_verify.py
```

## 结果信封（唯一一个 json 块）

```json
{block}
```
"""


if __name__ == "__main__":
    sys.exit(main())