#!/bin/sh
# one-shot reproduction of wp-10400-01 (run from the repo root)
set -e
python3 scripts/kf/build_asset_manifest_wp10400_01.py
python3 scripts/kf/validate_wp10400_01.py
python3 scripts/kf/render_and_publish_wp10400_01.py --no-publish
