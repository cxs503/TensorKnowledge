#!/bin/sh
# reproduce the m5054 source-guard probe (sha256 of source_guard.json is in the extract manifest)
python3 scripts/sediment_m5054_source_guard.py --source-repo /root/tensor-ecosystem/TensorSPH --sha 82b72a15c044259d1e7c8d638e9273705fa42e7b
