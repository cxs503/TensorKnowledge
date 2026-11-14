"""KPI-KB-VERIFY-RATE 计量器（真代码：连库采集 -> 纯函数算核 -> result/报告/图件）。

用法（仓库根目录）::

    python -m tools.kpi_kb_verify_rate collect  --out runs/kpi_kb_verify_rate
    python -m tools.kpi_kb_verify_rate measure  --snapshot runs/kpi_kb_verify_rate/snapshot.json
    python -m tools.kpi_kb_verify_rate report   --snapshot runs/kpi_kb_verify_rate/snapshot.json \
                                               --out runs/kpi_kb_verify_rate
    python -m tools.kpi_kb_verify_rate verify   --snapshot runs/kpi_kb_verify_rate/snapshot.json
    python -m tools.kpi_kb_verify_rate bench    --out benchmarks/kpi_kb_verify_rate
    python -m tools.kpi_kb_verify_rate selftest

设计约束：
  * **只读**计量：SQL 全部 SELECT，且服务端以 ``default_transaction_read_only=on`` 连接；
  * **可复算**：``--from-snapshot`` 路径不连库，任意机器重算同一数值；
  * **不编造**：目标未定标 -> ``target=null``；0/0 -> ``current=null``（不写 0）。
"""
from __future__ import annotations

from .compute import (SemanticsError, build_result, result_fingerprint,
                      snapshot_fingerprint, verify_rate, wilson_interval)
from .spec import ANCHOR, SPEC_SHA256, SPEC_VERSION

__version__ = "1.0.0"

__all__ = [
    "ANCHOR", "SPEC_SHA256", "SPEC_VERSION", "__version__",
    "SemanticsError", "build_result", "result_fingerprint", "snapshot_fingerprint",
    "verify_rate", "wilson_interval",
]