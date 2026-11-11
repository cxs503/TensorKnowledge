"""Spec data for the sediment extraction of platform mission 7485.

Separated from ``sediment_m7485_extract.py`` so that the writer and the
independent verifier share the *identity* constants (repo / sha / paths) while
the verifier re-reads everything else from the written JSON, never from this
module.
"""

REPO_NAME = "TensorBEM"
SHA = "80ad52a8236030e2343d5a88131bea3190088c09"
SOURCE_MISSION = 7485
SOURCE_TASK_KEY = "tk-sediment-m7485"
SOURCE_BRANCH = "agent/m7485"
SOURCE_FINISHED_AT = "2026-11-08T15:52:03.438574+00:00"

DOC = "docs/m7485_kp505_openwater_bem.md"
DRIVER = "src/tensorbem/benchmarks/kp505_openwater_bem.py"
SOLVER = "src/tensorbem/propeller.py"
TESTS = "tests/test_propeller_open_water.py"
VERDICT = "benchmarks/kp505_openwater_bem/verdict.json"
POINTS = "benchmarks/kp505_openwater_bem/points.csv"
CONVERGENCE = "benchmarks/kp505_openwater_bem/convergence.csv"

RECORDED_AT = "2026-11-10T00:00:00+00:00"
CREATED_AT = "2026-11-10T00:00:00+00:00"
CREATED_BY = "agent/m8823"
SOURCE_MODEL = "deepseek-v4-flash"
VERSION = "0.1.0"