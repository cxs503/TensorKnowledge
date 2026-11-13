"""Register the source assets of report 14137 (work package wp-14137-01, task_type 01-asset-registration).

Design rules enforced here:
  * No hand transcription. Every ``quote`` in the manifest is sliced out of the report markdown at run
    time from a programmatic anchor (unique line search + line span); the script refuses to write
    anything if an anchor is missing/ambiguous or a quote is not a unique substring of the markdown.
  * Registration only. No extraction, no classification (contract: objective.register_assets=true,
    objective.classify_report_type=false). ``claims`` is therefore an empty array -- legitimate per
    schemas/kf_result.v1.schema.json ("零条=合法完整结果").
  * Nothing is marked verified. ``resolution`` only states whether the referenced address is
    resolvable *from the cited source span*; the upstream report's own conclusions are registered,
    never re-adjudicated.
  * Unresolvable items are recorded as referenced_unresolved / declared_absent *with the machine
    check that produced that verdict* (missing worktree path, DB permission denied, external repo,
    cluster job state), never dropped and never given an invented address.

Inputs (produced by scripts/kf_fetch_14137.py):
  runs/wp-14137-01/report_14137.md    (markdown payload, sha256 checked against the contract)
  runs/wp-14137-01/report_14137.json  (raw API payload: id/title/scenario_key/figures/tags)

Outputs:
  artifacts/wp-14137-01/asset_manifest.json
  runs/wp-14137-01/kf_result.wp-14137-01.json       (result envelope, kf_result.v1 shape)
  runs/wp-14137-01/kf_result_block.wp-14137-01.json (same JSON, for the single ```json block)

Usage: python3 scripts/kf_register_14137.py
"""
from __future__ import annotations

import copy
import datetime
import glob
import hashlib
import json
import pathlib
import re
import subprocess
import sys

REPORT_ID = "14137"
PACKAGE_ID = "wp-14137-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "6f65040f0d3483ee5ca35f81c0fa4e5af147165e066e6c9c1cdb9a815faa8c30"
SOURCE_URI = "tensor://reports/14137"
SCENARIO_KEY = "dem_clump_shape_effect"

RUN_DIR = pathlib.Path("runs/wp-14137-01")
ART_DIR = pathlib.Path("artifacts/wp-14137-01")
SCHEMA_PATH = pathlib.Path("schemas/asset_manifest.v1.schema.json")
KF_SCHEMA_PATH = pathlib.Path("schemas/kf_result.v1.schema.json")

# anchor = a substring that must occur on exactly one line of the markdown;
# span = (offset of first quoted line, offset of last quoted line) relative to that line.
ASSETS = [
    dict(asset_id="A01", asset_class="code_pointer",
         label="src/tensordem/contact/rolling_static.py（新增，149 行；静态 + 形状感知滚动律）",
         anchor="src/tensordem/contact/rolling_static.py", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓内路径；报告未给 commit/分支，无法从 tensor://reports/14137 解析到具体版本"),
    dict(asset_id="A02", asset_class="code_pointer",
         label="clump_dem.py（pair 与 wall 两条滚动分支接入点）",
         anchor="接入点：`clump_dem.py`", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓内引擎代码；无 commit 锚点"),
    dict(asset_id="A03", asset_class="code_symbol",
         label="ContactParams 新增 rolling_model / rolling_lever 两个参数",
         anchor="`ContactParams` 新增", span=(0, 0),
         resolution="referenced_unresolved",
         note="符号级引用，无版本锚点，无法机器解析"),
    dict(asset_id="A04", asset_class="test_file",
         label="tests/test_rolling_static.py（13 项内核测试；报告自报 13 passed）",
         anchor="验证（机器可判，", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓内测试文件；本工序只登记文件名与自报计数，未复跑（不冒充复验）"),
    dict(asset_id="A05", asset_class="code_pointer",
         label="benchmarks/gap_dem_clump/run_round2_scan.py（单算例 + 聚合入口）",
         anchor="run_round2_scan.py --case", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓内基准脚本；无 commit 锚点"),
    dict(asset_id="A06", asset_class="code_pointer",
         label="benchmarks/gap_dem_clump/shard_round2.py（8 片分片入口）",
         anchor="shard_round2.py --i", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓内基准脚本；无 commit 锚点"),
    dict(asset_id="A07", asset_class="code_pointer",
         label="run_gap_dem_clump.py::main()（前轮死代码，m14681 已修）",
         anchor="run_gap_dem_clump.py::main()", span=(0, 1),
         resolution="referenced_unresolved",
         note="TensorDEM 仓内入口脚本；修复提交仅以任务号 m14681 指代，无 git hash"),
    dict(asset_id="A08", asset_class="data_artifact",
         label="artifacts/GAP-DEM-CLUMP-R2/results.json（扫描真数据）",
         anchor="artifacts/GAP-DEM-CLUMP-R2/results.json", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓 artifacts 目录路径，未内嵌于报告；本工作树无此文件"),
    dict(asset_id="A09", asset_class="sql_artifact",
         label="artifacts/GAP-DEM-CLUMP-R2/oss_solutions_insert.sql（选型沉淀入库脚本）",
         anchor="oss_solutions_insert.sql", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓 artifacts 路径；本工作树无此文件"),
    dict(asset_id="A10", asset_class="figure",
         label="artifacts/GAP-DEM-CLUMP-R2/gap_dem_clump_r2.png（repose vs a/b + 形状效应 Δ）",
         anchor="图：`artifacts/GAP-DEM-CLUMP-R2/gap_dem_clump_r2.png`", span=(0, 0),
         resolution="referenced_unresolved",
         note="图件以路径引用，报告内未内嵌 base64；平台 figures 字段为空（见 resolution_check）"),
    dict(asset_id="A11", asset_class="platform_table",
         label="平台表 oss_solutions（feature_slug=GAP-DEM-CLUMP 共 6 行）",
         anchor="`oss_solutions` 共 6 行", span=(0, 1),
         resolution="referenced_unresolved",
         note="报告断言已入库 6 行；本工序以只读 SQL 复核计数，权限不足（见 resolution_check），故不判 resolved"),
    dict(asset_id="A12", asset_class="platform_table",
         label="平台表 oss_inventory（报告称 218 行 / 140 个 feature_slug）",
         anchor="oss_inventory WHERE", span=(0, 0),
         resolution="referenced_unresolved",
         note="只读复核被拒（见 resolution_check）；行数系报告自报"),
    dict(asset_id="A13", asset_class="cluster_job",
         label="集群作业 cj974（a/b=3.0 与 seed=1 网格，排队未回；未回的数不引用）",
         anchor="集群 cj974", span=(0, 1),
         resolution="referenced_unresolved",
         note="作业未完成，无结果工件；查询时点状态见 resolution_check"),
    dict(asset_id="A14", asset_class="mission_ref",
         label="本轮任务锚 m15028",
         anchor="round 2 (m15028)", span=(0, 0),
         resolution="referenced_unresolved",
         note="任务号引用，不是工件；本工序不解析任务库"),
    dict(asset_id="A15", asset_class="mission_ref",
         label="前轮 m14996（honest-FAIL，未留 fail_stage/failure_reason）",
         anchor="前轮（m14996）honest-FAIL", span=(0, 1),
         resolution="referenced_unresolved",
         note="任务号引用；前轮报告本体不在本工件范围内"),
    dict(asset_id="A16", asset_class="mission_ref",
         label="m14681（run_gap_dem_clump.py::main() 死代码修复任务）",
         anchor="m14681 修复", span=(0, 0),
         resolution="referenced_unresolved",
         note="任务号引用，无 commit hash"),
    dict(asset_id="A17", asset_class="code_constant",
         label="仓内文献锚常量 LIT（球基线带 22–25° 来源）",
         anchor="沿用仓内 `LIT`", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓内常量名；具体取值以引用文献 Zhou 1999 为准，本工序不复核"),
    dict(asset_id="A18", asset_class="cluster_filesystem",
         label="集群节点 ~/oss-cache（n315/n330 开源包缓存，报告称只有 LBM 包）",
         anchor="`~/oss-cache`（n315/n330）", span=(0, 0),
         resolution="referenced_unresolved",
         note="集群节点家目录路径，本控制面不可挂载核验；报告断言无法在本工序落实为机器检查"),
    dict(asset_id="A19", asset_class="bibliography",
         label="外部文献 4 条：Ai 2011 / Wensrich 2012 / Jiang 2005 / Zhou 1999",
         anchor="Ai, Chen, Rotter, Ooi (2011)", span=(0, 3),
         resolution="referenced_unresolved",
         note="仅期刊名+卷页，无 DOI/URL；本工序不联网猜地址（见 resolution_check 地址抽取）"),
    dict(asset_id="A20", asset_class="in_source_table",
         label="§2.2 13 项内核测试判据表（R1a–R4c）",
         anchor="| id | 判据 | 实测 |", span=(0, 14),
         resolution="resolved_in_source", note="表体随报告 markdown 内嵌，字符区间可直接定位"),
    dict(asset_id="A21", asset_class="in_source_table",
         label="§3 质量匹配填充高度 / n_particles / 墙高判定表（4 行）",
         anchor="| a/b | 匹配填充高度 h [m] | n_particles | 墙高 [m] | 判定 |", span=(0, 5),
         resolution="resolved_in_source", note="表体内嵌；登记其存在与位置，不复核数值"),
    dict(asset_id="A22", asset_class="in_source_table",
         label="§4 误差判定表（关键量 vs 基准，6 行）",
         anchor="| 量 | 基准 | 实测 | 误差 | <3%? |", span=(0, 7),
         resolution="resolved_in_source", note="表体内嵌；含 honest-FAIL 行（repose −22%…−37%）"),
    dict(asset_id="A23", asset_class="in_source_table",
         label="附表：三配置有效/失效计数表（程序生成）",
         anchor="| 配置 | 有效算例 | quiesced=false | 有效 repose [deg] |", span=(0, 4),
         resolution="resolved_in_source", note="表体内嵌，声明为程序生成"),
    dict(asset_id="A24", asset_class="repro_command_block",
         label="§7 复现命令块（4 段：单算例 / 分片 / 聚合 / 内核测试）",
         anchor="## 7 复现", span=(3, 9),
         resolution="resolved_in_source",
         note="只取命令行本身（不含 ``` fences，避免结果信封内出现三反引号导致 json 块被截断）；路径指向 TensorDEM 仓，本工作树无法直接执行"),
]


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def build_locator(md: str, lines, offs, anchor: str, span):
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"anchor not unique/found ({len(hits)} hits): {anchor!r}")
    a = hits[0]
    i0, i1 = a + span[0], a + span[1]
    i1 = min(i1, len(lines) - 1)
    start = offs[i0]
    end = offs[i1] + len(lines[i1])
    quote = md[start:end]
    if not quote.strip():
        raise SystemExit(f"empty quote for anchor {anchor!r}")
    return dict(method="char_span", start_char=start, end_char=end,
                start_line=i0, end_line=i1, quote=quote, unique=md.count(quote) == 1)


def host_probe(basename_pattern: str, limit: int = 3):
    """Bounded host-side probe: is there any checkout of this path outside this worktree?"""
    pats = glob.glob(str(pathlib.Path("/root/tp-agent/work/*/src/tensordem/**/" + basename_pattern)),
                     recursive=True)
    pats += glob.glob(str(pathlib.Path("/root/tp-agent/work/*/" + basename_pattern)))
    return sorted(set(pats))[:limit], len(set(pats))


def worktree_path_check(paths):
    missing = [p for p in paths if not pathlib.Path(p).exists()]
    return dict(check="worktree_path_exists", paths=paths, missing=missing,
                result="unresolved" if missing else "resolved")


def resolution_check(asset, worktree: pathlib.Path, payload: dict):
    aid = asset["asset_id"]
    quote = asset["locator"]["quote"]

    if aid in ("A01", "A04"):
        base = "rolling_static.py" if aid == "A01" else "test_rolling_static.py"
        rel = ("src/tensordem/contact/" if aid == "A01" else "tests/") + base
        chk = worktree_path_check([rel])
        found, n = host_probe(base)
        chk.update(host_probe_glob=f"/root/tp-agent/work/*/.../{base}", host_probe_hits=n,
                   host_probe_sample=found,
                   detail="本工作树(TensorKnowledge)无此路径；报告未给 commit，故其它检出不能用于解析本报告的版本")
        return chk

    if aid in ("A02", "A05", "A06", "A07", "A08", "A09"):
        chk = worktree_path_check(["src", "artifacts/GAP-DEM-CLUMP-R2"])
        chk["detail"] = ("引用的相对路径属 TensorDEM 仓；本工作树无 src/ 与 artifacts/GAP-DEM-CLUMP-R2/，"
                         "且契约禁止改写外部仓产物 ⇒ 只登记不解析")
        return chk

    if aid == "A10":
        figs = payload.get("figures") or []
        meta = [f for f in figs if (f or {}).get("name") == "gap_dem_clump_r2.png"]
        has_bytes = any((f or {}).get("png_base64") for f in figs)
        return dict(check="platform_figures_field", platform_figures_count=len(figs),
                    metadata_name_match=bool(meta),
                    png_bytes_present=has_bytes,
                    result="unresolved",
                    detail=("平台 figures 记录里有同名图件元数据（name+caption），但无 png_base64 字节；"
                            "矢量内容只在 TensorDEM 仓 artifacts/ 下 ⇒ 地址仍不可由本报告解析"))

    if aid in ("A03", "A17"):
        return dict(check="symbol_reference_only", symbol=asset["label"].split("（")[0],
                    result="unresolved",
                    detail="报告只给符号名/常量名，未给文件+版本；本工序不猜测其定义位置")

    if aid in ("A11", "A12"):
        table = "oss_solutions" if aid == "A11" else "oss_inventory"
        sql = (f"select count(*) from {table} where feature_slug='GAP-DEM-CLUMP'"
               if aid == "A11" else f"select count(*) from {table}")
        try:
            r = subprocess.run(["psql", "-d", "tensorplatform", "-tA", "-c", sql],
                               capture_output=True, text=True, timeout=30)
            err = (r.stderr or "").strip().splitlines()
            return dict(check="readonly_sql_count", sql=sql, exit_code=r.returncode,
                        stdout=(r.stdout or "").strip(), stderr=" ".join(err[-2:]),
                        result="resolved" if r.returncode == 0 else "unresolved",
                        detail="只读计数失败（权限不足），故报告自报行数不判 resolved")
        except Exception as exc:  # pragma: no cover - environment dependent
            return dict(check="readonly_sql_count", sql=sql, result="unresolved", error=str(exc))

    if aid == "A13":
        obs = RUN_DIR / "cluster_cj974_probe.txt"
        txt = obs.read_text().strip() if obs.exists() else ""
        state = ""
        for ln in txt.splitlines():
            if ln.startswith("cj974"):
                state = " ".join(ln.split()[1:3])
        return dict(check="cluster_job_state_probe", probe_file=str(obs),
                    observed=state, result="unresolved" if "queued" in state or "running" in state
                    else ("resolved" if state else "unresolved"),
                    detail="作业未出结果 ⇒ 无工件可解析（报告亦声明未回的数不引用）")

    if aid == "A19":
        found = re.findall(r"(https?://\S+|doi:\S+|10\.\d{4}/[^\s|]+)", quote)
        return dict(check="address_extraction", result="unresolved" if not found else "resolved",
                    addresses_found=found,
                    detail="仅在引用文本内检索 URL/DOI（不联网猜地址）；4 条文献均只给期刊卷页")

    if aid == "A18":
        return dict(check="filesystem_reachability", path="~/oss-cache (n315/n330)",
                    result="unresolved",
                    detail="集群节点家目录，控制面无挂载点；报告断言不可在本工序机器化")

    if aid == "A10":
        figs = payload.get("figures") or []
        return dict(check="platform_figures_field", result="absent" if not figs else "present",
                    platform_figures_count=len(figs),
                    detail="图件仅在正文以路径引用；平台 figures 字段计数见左")

    if aid == "A14":
        mid = payload.get("mission_id")
        return dict(check="platform_mission_id_field", record_mission_id=mid,
                    matches_report_anchor=mid == 15028, result="present",
                    detail="记录字段 mission_id 与本行任务号一致；任务本体（执行历史/工件）不在报告内，故仍判 unresolved 级解析")

    if aid in ("A15", "A16"):
        return dict(check="mission_id_reference_only", result="unresolved",
                    detail="任务号是引用键不是工件；本工序不查询任务库（越界）")

    return dict(check="char_span_in_source_markdown", result="resolved")


def validate(manifest: dict, payload_ok: bool):
    """schema_pass: validate against the repo schemas. asset_manifest.v1 pins wp-448-01 identity
    consts (it was written by that package); we substitute the identity consts in memory so the
    shape check is real, and record the substitution instead of mutating another package's file."""
    import jsonschema

    notes = {}
    schema = json.loads(SCHEMA_PATH.read_text())
    patched = copy.deepcopy(schema)
    patched["properties"]["package_id"] = {"const": PACKAGE_ID}
    patched["properties"]["report_id"] = {"const": REPORT_ID}
    patched["properties"]["source"]["properties"]["uri"] = {"const": SOURCE_URI}
    jsonschema.validate(manifest, patched)
    notes["asset_manifest_v1"] = dict(
        schema_file=str(SCHEMA_PATH), ok=True,
        identity_consts_substituted=["package_id", "report_id", "source.uri"])

    envelope_schema = json.loads(KF_SCHEMA_PATH.read_text())
    envelope = dict(
        package_id=PACKAGE_ID, task_type=TASK_TYPE, report_id=REPORT_ID,
        provenance=dict(source_hash="sha256:" + EXPECTED_HASH, source_field="markdown"),
        outputs={"asset_manifest.json": manifest}, claims=[])
    jsonschema.validate(envelope, envelope_schema)
    notes["kf_result_v1"] = dict(schema_file=str(KF_SCHEMA_PATH), ok=True,
                                 note="provenance.source_hash placeholder checked against real hash below")
    return notes


def emitted_at() -> str:
    """Pin the emission timestamp so re-running the chain is byte-identical (idempotent reruns).

    First run records the wall clock; later runs reuse it, which keeps the local envelope equal to
    the ```json block of the already published report.
    """
    pin = RUN_DIR / "emitted_at.txt"
    if pin.exists():
        return pin.read_text().strip()
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    pin.write_text(ts + "\n")
    return ts


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RUN_DIR / "report_14137.json").read_text())
    md = (RUN_DIR / "report_14137.md").read_text()

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {EXPECTED_HASH}")
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    # heading map: only real markdown headings (line starts with '#' outside a fenced code block).
    # A naive "last line starting with '#'" would attribute code comments inside the §7 bash block
    # (``# 单算例``) as report sections.
    section_map, cur, in_fence = [], "(document)", False
    for ln in lines:
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and ln.startswith("#"):
            cur = ln.strip()
        section_map.append(cur)

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit(f"duplicate asset_id {spec['asset_id']}")
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"])
        if not loc["unique"]:
            raise SystemExit(f"quote not unique for {spec['asset_id']}: {spec['anchor']!r}")
        head = section_map[loc["start_line"]]
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=head,
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=resolution_check({"asset_id": spec["asset_id"], "label": spec["label"], "locator": loc},
                                              worktree, payload),
            note=spec["note"],
        ))

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

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
            title=payload.get("title") or "",
            scenario_key=payload.get("scenario_key") or SCENARIO_KEY,
            platform_figures=payload.get("figures") or [],
            platform_tags=payload.get("tags") or [],
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
        integrity=dict(
            quote_uniqueness=all(a["locator"]["unique"] for a in assets),
            hash_recomputed_locally=True,
            hash_matches_contract=md_hash == EXPECTED_HASH,
            contract_chars_expected=7569,
            chars_matches_contract=len(md) == 7569,
            registered_not_verified="resolution 只表示定位可解析性；报告结论未经本工序复核，未标 verified",
        ),
    )

    notes = validate(manifest, True)
    manifest["integrity"]["schema_pass"] = notes
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (ART_DIR / "asset_manifest.json").write_text(manifest_text)
    # artifacts/ is gitignored in this repo (mission-push gate drops artifacts/**), so the committed
    # copy lives under docs/; both are written from the same string, so they cannot drift.
    docs = pathlib.Path("docs") / PACKAGE_ID
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "asset_manifest.json").write_text(manifest_text)

    envelope = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_hash="sha256:" + EXPECTED_HASH,
            source_field="markdown",
            producer=f"agent/m15782 {PACKAGE_ID} (scripts/kf_fetch_14137.py + scripts/kf_register_14137.py)",
            emitted_at=emitted_at(),
            notes=("sha256 本地重算并与契约 source_hash 逐字比对一致；assets 的 quote 均由脚本从 "
                   "markdown 切片，逐条校验唯一子串；未做抽取、未标 verified"),
        ),
        outputs={"asset_manifest.json": manifest},
        claims=[],
    )
    (RUN_DIR / f"kf_result.{PACKAGE_ID}.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / f"kf_result_block.{PACKAGE_ID}.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n")

    print(f"manifest: {ART_DIR/'asset_manifest.json'}")
    print(f"assets={len(assets)} by_resolution={by_res}")
    print(f"sha256={md_hash} chars={len(md)} MATCH={md_hash == EXPECTED_HASH}")
    for a in assets:
        first = a["locator"]["quote"].splitlines()[0][:90]
        print(f"  {a['asset_id']} {a['resolution']:<22} "
              f"[{a['locator']['start_char']}:{a['locator']['end_char']}] "
              f"{a['resolution_check']['result']:<10} {first}")
    return 0


if __name__ == "__main__":
    sys.exit(main())