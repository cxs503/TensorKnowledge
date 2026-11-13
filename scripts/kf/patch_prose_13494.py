"""Cosmetic-only follow-up to patch_preset_13494.py: template prose layout for the wp-13494-01 report.

Idempotent; exits 0 when already applied.
"""
from __future__ import annotations

import pathlib

P = pathlib.Path("scripts/kf/kf01_register.py")
s = P.read_text(encoding="utf-8")

OLD1 = ('"   包配置声明的 `declared_absent` 工件（报告亲口说「未生成/未测量/不支持」）→ '
        '`resolution=declared_absent` + 逐字声明定位器，绝不伪装成缺失文件。",')
NEW1 = ('"",\n        "   包配置声明的 `declared_absent` 工件（报告亲口说「未生成/未测量/不支持」）→ '
        '`resolution=declared_absent` + 逐字声明定位器，绝不伪装成缺失文件。",')

OLD2 = '"内嵌图、源码/工件路径引用、表格、复现命令块、接口字段。**不做抽取、不生成 claim、不标注 verified**",'
NEW2 = ('"内嵌图、源码/工件路径引用、表格、复现命令块、接口字段，以及报告显式声明缺失（未生成/未测量/不支持）的工件。"\n'
        '        "**不做抽取、不生成 claim、不标注 verified**",')

applied = []
for old, new in ((OLD1, NEW1), (OLD2, NEW2)):
    if old in s:
        s = s.replace(old, new, 1)
        applied.append(old[:30])
    elif new not in s:
        raise SystemExit("anchor missing and not already applied: %r" % old[:50])

if applied:
    P.write_text(s, encoding="utf-8")
    print("applied:", applied)
else:
    print("already applied")