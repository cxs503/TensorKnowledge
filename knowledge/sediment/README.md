# Sediment packages (`knowledge/sediment/`)

Machine-checkable knowledge extracted from platform missions: four-contract
records (claim / evidence / provenance) with **verbatim, hashed quotes** and
**re-derived numbers**, plus the run artefacts that prove they were executed.

| package | source | claims | re-derived numbers | status |
|---|---|---|---|---|
| [`sloshing-impact-lbm/`](sloshing-impact-lbm/) | `TensorLBM@aecabea25cc7` (mission 7437) | 5 | 15 / 19 checks | 104/104 checks pass, worst \|rel err\| 1.6e-3 |

## Layout of a package

```
knowledge/sediment/<capability-slug>/
    claim/*.json           schemas/claim-record.schema.json      (epistemic_status = draft)
    evidence/*.json        schemas/evidence-record.schema.json   (assessment_status = unassessed)
    provenance/*.json      schemas/provenance-record.schema.json
    INDEX.md               one row per claim: id / digest / locator / quote sha256
    number_checks.json     declarative plan: claim number -> source regex + recipe + tolerance
    manifest.json          source identity (repo / sha / root env) + entry points
    run/build.json         build artefact: slice audit + per-file sha256 (deterministic rebuild)
    run/verification.json  every check with PASS/FAIL + environment
    run/benchmark.json     ref (source-recorded) vs got (re-derived) + relative error
```

Naming note: the directory is named after the **capability**, never after the
source mission id. A path segment `m<other-mission>/` is stripped by the push
gate, which is exactly what silently removed the first attempt at this package.

## Adding a package

1. Write a builder that reads the source repository **as a git object store**
   (`scripts/sediment_lib.py:GitSource`) and slices every quote by line range;
   abort if a number in a claim statement is not a canonical rendering of a value
   read from the source or re-derived by a recipe.
2. Write an **independent** verifier (no shared numeric code path) that re-slices
   quotes, re-hashes them, re-locates them with `grep -F`, validates schemas,
   checks cross-reference/index closure, and executes `number_checks.json`.
3. Declare the verifier in `manifest.json:entry.verifier`; it is then picked up by
   `scripts/validate_sediment_packages.py`, which `scripts/validate_knowledge_assets.py`
   calls as part of the repository integrity gate.
4. Commit the run artefacts. When the source repository is absent (CI), the
   verifier reports `source:available = FAIL` and the runner classifies the
   package as *skipped*, never as passed.

## Reference implementation

`sloshing-impact-lbm` is the worked example: `scripts/sediment_sloshing_extract.py`
(writer), `scripts/verify_sediment_sloshing.py` (verifier + benchmark),
`scripts/sloshing_reference.py` (recipes: dispersion / shock / spectral peak /
trailing average), `tests/test_sediment_sloshing.py` (16 tests), and
`docs/ke/sloshing-impact-lbm-sediment.md` (generated report).