#!/usr/bin/env bash
# Regenerate knowledge/sediment/m7485/VALIDATION.md from *real* command output.
# Nothing in VALIDATION.md is typed by hand: every block is the captured stdout
# of the command shown above it.
set -o pipefail
cd "$(dirname "$0")/.."
export M7485_SRC_REPO="${M7485_SRC_REPO:-/root/tp-agent/work/m7485}"
SHA=80ad52a8236030e2343d5a88131bea3190088c09
OUT=knowledge/sediment/m7485/VALIDATION.md

halt() { echo "FAILED: $1" >&2; exit 1; }

{
  echo "# VALIDATION — knowledge/sediment/m7485"
  echo
  echo "由 \`scripts/sediment_m7485_validation.sh\` 生成（每段都是紧随命令的真实 stdout，非手抄）。"
  echo
  echo "- source_mission_id: 7485 / task_key: tk-sediment-m7485"
  echo "- source_repo: TensorBEM / source_head_sha: \`$SHA\`"
  echo "- 校验环境: $(python3 -V 2>&1) / jsonschema $(python3 -c 'import jsonschema;print(jsonschema.__version__)' 2>/dev/null)"
  echo
  echo "## 1. 写包 + jsonschema 校验"
  echo
  echo '```'
  echo "\$ python3 scripts/sediment_m7485_extract.py"
  python3 scripts/sediment_m7485_extract.py || halt "extract"
  echo '```'
  echo
  echo "## 2. 独立复核（引句按 sha 重取 / 数值由 points.csv 复算 / INDEX↔JSON 一致性）"
  echo
  echo '```'
  echo "\$ M7485_SRC_REPO=\$M7485_SRC_REPO python3 scripts/verify_sediment_m7485.py"
  python3 scripts/verify_sediment_m7485.py || halt "verify"
  echo '```'
  echo
  echo "## 3. 逐条引句的 grep 复现（按 sha 取 blob，再 grep -nF）"
  echo
  echo '```'
  for spec in \
    "docs/m7485_kp505_openwater_bem.md|**结论先行（honest FAIL）**" \
    "docs/m7485_kp505_openwater_bem.md|读法：径向一阶（p ≈ 1）" \
    "docs/m7485_kp505_openwater_bem.md|4. **近零载荷段不可信**" \
    "benchmarks/kp505_openwater_bem/points.csv|0.8,0.0999328035758505" \
    "benchmarks/kp505_openwater_bem/verdict.json|\"measured_pct\": -29.125671222801053" \
    "tests/test_propeller_open_water.py|assert velocity[1] == pytest.approx" \
    "tests/test_propeller_open_water.py|formula itself at AR = 4" ; do
    path="${spec%%|*}"; needle="${spec#*|}"
    echo "\$ git -C \$M7485_SRC_REPO show $SHA:$path | grep -nF '$needle'"
    git -C "$M7485_SRC_REPO" show "$SHA:$path" | grep -nF "$needle" || halt "grep $needle"
    echo
  done
  echo '```'
  echo
  echo "## 4. 守卫测试（包被改动时必须红）"
  echo
  echo '```'
  echo "\$ python3 -m pytest tests/test_sediment_m7485.py -q"
  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_sediment_m7485.py -q -p no:cacheprovider 2>&1 | tail -3
  echo '```'
  echo
  echo "## 5. 源 mission 的自证测试重跑（可复现性下限）"
  echo
  echo '```'
  echo "\$ cd \$M7485_SRC_REPO && PYTHONPATH=src python3 -m pytest tests/test_propeller_open_water.py -q"
  (cd "$M7485_SRC_REPO" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_propeller_open_water.py -q -p no:cacheprovider 2>&1 | tail -2)
  echo '```'
  echo
  echo "## 6. 未做 / 局限"
  echo
  echo "- 未重跑 \`tensorbem.benchmarks.kp505_openwater_bem\` 扫掠：数值取自该 sha 已提交的工件，"
  echo "  并用 \`points.csv\` 逐项复算（见复核输出 num:/data: 行），属工件溯源 + 复算，不是独立重算。"
  echo "- \`epistemic_status\` 取 \`provisional\`：\`schemas/claim-record.schema.json\` 的 enum 无 \`draft\`"
  echo "  （draft 是 review-event 账本 fold 的结果，见 \`docs/ke/mapping-spec.md\` MUST-4.5 / D-09）；"
  echo "  \`review_status=draft\` 落在 \`review-status.json\` 与 claim.notes。"
  echo "- 本包不含 review-event，未 promoted：评审由独立席位另派。"
} > "$OUT"

[ -s "$OUT" ] || halt "empty VALIDATION.md"
echo "wrote $OUT ($(wc -l < "$OUT") lines)"