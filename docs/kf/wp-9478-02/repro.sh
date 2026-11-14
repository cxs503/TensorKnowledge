#!/usr/bin/env bash
# wp-9478-02 一键复跑：取源 → 分类解析 → 独立复核 → 出报告载荷
#
#   bash docs/kf/wp-9478-02/repro.sh            # 用已缓存源（仍是逐字节哈希校验后的源）
#   bash docs/kf/wp-9478-02/repro.sh --refresh  # 重新从平台取源（需 TENSOR_API_BASE / TENSOR_AGENT_*）
#   bash docs/kf/wp-9478-02/repro.sh --post     # 额外发布平台报告（mission 19793）
#
# 依赖：python3 + matplotlib + jsonschema；平台凭证只从环境变量读取，不落盘。
set -euo pipefail

PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$PKG_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

PY="${PYTHON:-python3}"
REFRESH=0
POST=""

for arg in "$@"; do
  case "$arg" in
    --refresh) REFRESH=1 ;;
    --post)    POST="--post" ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

if [ "$REFRESH" = "1" ]; then
  echo "== 1/3 取源并校验哈希（平台 API 重新拉取） =="
  KF_REFRESH=1 "$PY" "$PKG_DIR/scripts/generate_classification.py"
else
  echo "== 1/3 分类解析（缓存源，仍逐字节校验 sha256） =="
  "$PY" "$PKG_DIR/scripts/generate_classification.py"
fi

echo "== 2/3 独立复核（重新登录+重取源、重解每个 locator、schema 校验） =="
"$PY" "$PKG_DIR/scripts/verify_result.py"

echo "== 3/3 出图与报告载荷 =="
"$PY" "$PKG_DIR/scripts/build_report.py" $POST

echo "完成：classification.json / checks.json / verify.json / kf_result.json / 图 2 张"