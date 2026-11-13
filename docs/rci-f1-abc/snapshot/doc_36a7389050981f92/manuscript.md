# One quantity, six readings: a claim ledger for extreme-value design loads in ice-going ships

*Manuscript draft — target journals: Structural Safety / Marine Structures (extreme-value statistics, code-based design).*

**Authors:** TensorPlatform ice-load statistics working group (mission 6369).
**Corpus state:** 6 technical reports (ids #6503, #6504, #6980, #7100, #7285, #7289; 4 distinct missions),
24 report figures and 56 machine-checkable criteria rows, fetched and hashed by
`papers/tools/m6369_fetch.py` at manuscript build time.

---

## Abstract

Design loads for ice-going ships are ultimately quoted as single numbers, yet inside a working
verification pipeline the *same* physical quantity is routinely reported with several mutually
incompatible values, each obtained under a different convention. We turn this into a machine-checkable
object: a *claim ledger* in which every reported value carries a six-axis convention tuple (estimator,
declustering, threshold or discretisation rule, numerical path, aggregation, scale), an artefact-level
provenance pointer (report id, table, verbatim source row) and an explicit class — point *claim*,
convention *bound*, or independent *yardstick* — after which a pre-registered two-class gate decides
admissibility. Applied to six verification reports (four missions, 24 figures, 56 criteria rows), the
ledger shows that for one ice climate the 100-year return level of the bending moment is reported as
138.09, 143.02, 151.87, 162.27 and 167.78 MN against an independent 2000-ice-year yardstick of
144.11 MN, a spread of 21.5 %. A naive ±3 % gate on the point estimate accepts 1 of these 5 readings;
the ledger gate accepts 4 and rejects exactly the un-declustered reading (+16.425 %), the only one
outside the declustered 95 % profile-likelihood interval [128.67, 164.05] MN. Geometry is gated before
loads (block coefficient residual 0.0051 %), numerical paths contribute at most 5.21e-06 relative, and
the random seed carries a total-order Sobol index of 1.0000. We claim no new estimator: the
contribution is a bookkeeping scale that makes extrapolation uncertainty, convention dependence and
implementation error separable and that fails loudly when they are confused.

*Keywords:* extreme-value statistics; design load; generalised extreme value; peaks over threshold;
verification and validation; ice loads; code comparison; provenance.

---

## 1 Introduction

Ice-going ships and Arctic offshore structures are designed against rare events: the T-year return
level of a global ice-induced bending moment, or a design pressure at a reference contact area. Such
quantities come out of a chain that mixes physics-based simulation, extreme-value extrapolation and
rule-based values, and each link carries its own convention. As a result the literature and
engineering practice both contain mutually inconsistent numbers for nominally identical quantities,
and a verification report that quotes "the" value without its convention is not falsifiable
(Oberkampf & Roy, 2010).

Three mature bodies of work attack parts of the problem. Extreme-value theory supplies estimators
and their uncertainty: block maxima with the generalised extreme value (GEV) distribution (Gumbel,
1958; Coles, 2001), peaks over threshold with the generalised Pareto distribution (GPD) (Smith, 1987;
Davison & Smith, 1990; Hosking & Wallis, 1987), declustering of dependent exceedances (Leadbetter et
al., 1983; Ferro & Segers, 2003), and profile-likelihood intervals for return levels, which are the
only defensible intervals for shape and tail parameters. Marine-design practice has codified the use
of these tools for wave and response extremes (Jonathan & Ewans, 2013). Verification and validation
(V&V) methodology supplies discretisation-error estimators (Roache, 1994; Celik et al., 2008),
comprehensive verification procedures (Stern et al., 2001) and an evidence-based framing of
predictive capability (Oberkampf & Roy, 2010). Ice mechanics supplies the physical parameterisations
that enter load models (Sanderson, 1988; Timco & Weeks, 2010; Jordaan, 2005) and the standards that
fix design values (ISO 19906, 2010; IACS UR S11).

**Difference from existing practice.** What none of these frameworks provides is a *per-reading*
bookkeeping rule that decides, mechanically and before the numbers are looked at, whether a reported
value may be used — and, when several readings of one quantity disagree, which of them is suspect and
why. Existing practice compares a case to a single reference value against a tolerance chosen after
the fact; V&V grid studies produce one GCI for one output; extreme-value reports quote a point
estimate with an interval. Our claim is narrower and procedural:

1. **Convention tuples instead of point estimates.** Every reading is annotated on six axes
   (Section 2.2). Two readings may be compared only if their tuples agree on the axes that matter for
   the quantity, and the ledger records which axis differs.
2. **Classes instead of a single tolerance.** A point *claim* is admissible if its published interval
   contains an independent yardstick, or if its point deviation is within the physical gate; a
   convention *bound* (an envelope over a sweep) is admissible if it *contains* the yardstick. The
   ±3 % physical tolerance is applied only where it is meaningful — to implementation and reduction
   errors, not to extrapolation uncertainty of order 10 %.
3. **An independent yardstick per case.** Where possible the yardstick is a quantity the fitting
   sample never saw: a 2000-ice-year empirical quantile, an analytic closed form, or an
   independent-repeat mean.
4. **Artefact-level provenance.** Every number is bound to a report id, a table, a verbatim source
   row and a script (`papers/ice-load-statistics/data/*.json`, `papers/tools/m6369_*.py`), so that a
   revision of a claim is detectable as a change of hash rather than as a change of prose.

**Contributions, stated as artefacts.** (i) A ledger schema and a two-class decision rule,
pre-registered in Section 2.6 and implemented in `papers/tools/m6369_ledger.py`. (ii) A worked
application to 18 readings of 4 quantities across 6 reports (Tables 3–4 and `data/error_table.csv`),
in which the naive ±3 % gate accepts 5 of 17 gated readings while the ledger separates the rest into
admissible claims, admissible bounds, measure-dependent readings and one rejection. (iii) A mechanical
demonstration that a reproduced discretisation index of 19.78 % is measure dependence rather than
numerical error: the finest-two-grid difference (19.47 %) is 46.2 times the repeat-sample half-width
(0.42 %), and the quantity follows a power law with exponent 0.261 [0.258, 0.265]. (iv) A revision
audit showing that two of the six reports are revisions of another report in the same mission, and
that one revised claim was traceable to a value mis-attributed from a different table (Section 3.6).
No physical coefficient in this paper is new; the load models, estimators and rule values audited here
are the existing ones documented in the source reports.

---

## 2 Methods

### 2.1 Evidence base and provenance protocol

The unit of analysis is a *reading*: one number (with its uncertainty statement) reported for one
named physical quantity in one report. The corpus is the report window fixed by the work order
(ids strictly greater than 6377 and at most 7571), restricted to reports whose subject is ice-load
extremes and their verification. Six reports qualify; they belong to four distinct missions, and two
of them are revisions of another report in the same mission (Section 3.6).

All six full report bodies are fetched through the platform API by `papers/tools/m6369_fetch.py` and
stored verbatim in `data/reports.json`, each with the SHA-256 of its markdown
(`data/tables.json:reports[*].md_sha256`). Tables are then extracted by header signature, and every
extracted row keeps its verbatim source line and line number (`papers/tools/m6369_extract.py`). No
number in this manuscript is typed from a figure or from prose that was not stored: the
manuscript-level check `papers/tools/m6369_provenance.py` tokenises every numeric literal in this
file and resolves it against `data/*.json` and `data/*.csv`, reporting the coverage percentage and
every unresolved token (Section 3.7 and Data Availability).

Corpus inventory is reported with the six *coverage flags* used by the platform's mining tooling
(BASELINE, SWEEP, CLOUD, REPRO, CRIT, UNCERT), re-implemented with the same regular expressions as
`papers/tools/w9_facts.py:FLAGS`, so the counts are reproducible rather than quoted. These flags are
word-level triage, not acceptance criteria; Section 3.1 documents one false positive.

### 2.2 The six convention axes

A reading is comparable to another reading only if the following axes are recorded (Table 2):
estimator (BM-GEV versus POT-GPD, MLE versus analytic), declustering (annual maxima, runs with a
stated run length, or none), threshold or discretisation rule (POT threshold, quantile rule, cell
size, spectral spread assumption), numerical path (canonical reduction order, compiler flags,
accumulator precision), aggregation (single realisation, ensemble mean, maximum over an ensemble,
band over a sweep) and scale (block count, reference area or thickness, hull family). The axes were
chosen because each of them changes a reported value in this corpus by more than the physical gate;
that is an empirical statement, quantified in Section 3.

### 2.3 Cases and their parameters

Four cases are used, each chosen because the corpus contains several readings of one quantity.

**Case A — 100-year return level of the ice-induced vertical bending moment, z100 [MN]** (report
#6980). The load time history is a physics-parameterised synthetic ice climate (128625 events over
100 ice years, seed 20261106), explicitly *not* field data. Peak force follows an ISO 19906-type
pressure–area relation F = F_ref (h/h_ref)^(1−a) C_R ε with a = 0.400, F_ref = 15.000 MN at
h_ref = 1.000 m, annual-ice thickness median 0.900 m (lognormal σ = 0.400), ridge encounter
probability 0.060 with median thickness factor 2.600, crushing-strength CoV 0.280, 11.000 storms per
year of median duration 30.000 h, and a winter-severity AR(1) coefficient of 0.750
(`data/tables.json:tables.params_6980`). The yardstick is the empirical quantile of block maxima from
a 2000-ice-year simulation (seed 20261883) that never enters the 100-year fit.

**Case B — P95 of the ice-abrasion depth field [m/yr]** (reports #6503, #6504). Archard-law wear on
the ice belt of a 185 m hull (L = 185 m, B = 32.26 m, T = 11.5 m, Cb = 0.82, mesh Cb/L/B audit
passed), 8192 contact events with median pit radius 0.0189 m, wear coefficient k = K/H =
1e-14 m³/(N·m) as a computational guess against a calibrated 8.19e-15. Record grids are 0.125,
0.25, 0.5 and 1.0 m, with 8 and 24 independent repeat realisations respectively. There is no
converged value in the tested range (Section 3.3), so the case is adjudicated against a scale law
instead of a yardstick.

**Case C — R10 design load of a synthetic ice climate [kN]** (reports #7285, #7289). A
three-parameter GEV input with an analytic Poisson-maxima closed form R10 = 2447.0 kN serves as the
yardstick; the fitting pipeline reports BM-GEV and POT-GPD estimates under a 3-factor design
(2 platforms × 4 thread counts × 16 seeds = 128 cells per platform).

**Case D — long-term 10⁻⁸ extreme wave-induced bending moment [MN·m]** (report #7100). A 10⁴-tonne
ice-class multipurpose ship (L/B/T/D = 110 / 20 / 6.5 / 9.5 m, Cb = 0.780 with 0.7800 recomputed
from the section closure, ∇ = 11154 m³, Δ = 11433 t at ρ = 1025 kg/m³, midship section modulus
W = 7.04 m³ and inertia I = 33.5 m⁴, k_yy/L = 0.238, BM_L = 105.2 m) in 9 combined ice–wave
conditions (H_s = 1.0, 2.5, 4.0 m × h_ice = 0.5, 0.8, 1.2 m, heading 150°, 6 kn). The quantity has no
independent yardstick; IACS UR S11 wave bending moments are a different physical object (a rule design
value) and are used only for a conservatism check.

**Geometry gate.** Before any load number is used, hull coefficients are recomputed from the declared
principal dimensions and the section closure. For Case D the input block coefficient 0.780 is
recovered as 0.7800 from the integrated section, a residual of 0.0051 % against a gate of 1e-2 %; the
same report refuses the geometry (raising an exception) when the closure fails. Case B's mesh is
audited the same way, and Case A's quantity is one-dimensional and has no hull geometry.

### 2.4 Estimators and uncertainty

GEV and GPD parameters are fitted by maximum likelihood with analytic gradients and multi-start
initialisation; intervals for return levels and shape parameters are profile-likelihood intervals
(likelihood-ratio χ²₁ truncation), not Wald intervals, because the shape parameter's support and
strong correlation invalidate symmetric intervals (Coles, 2001). Dependence is handled by runs
declustering with run length r = 72 h, chosen by physical anchoring (at least twice the storm
duration), target-quantity stability and cross-check against the block-maxima route rather than by
looking for a plateau in the extremal index. Bootstrap calibration of the Kolmogorov–Smirnov
statistic is reported alongside the naive p-value, because with estimated parameters the naive p-value
is conservative; the corpus measures P(p < 0.05) = 0.0 % over 100 replications under the true model,
i.e. a naive p > 0.05 has almost no discriminating power. Interval coverage is verified by repeated
simulation (120 replications for BM and 60 for POT in Case A; 200 and 100 in Case C), and
interval-coverage acceptance bands are pre-registered as [0.92, 0.98].

### 2.5 Numerical-path contract

For Case C the reduction is *canonical*: chunking depends only on data length and the index order is
fixed, with Neumaier compensation. It is compared against four non-canonical paths — a different fixed
tree (`ordered`), completion-order re-association (`async`), a genuinely compiled
`-O3 -ffast-math -march=native` build (`fastmath`) and a float32 accumulator (`fp32`) — under a
three-level contract: C1 bit-identical, C2 numerically equal to 1e-9, C3 physically equal within 3 %.
The negative control is that `-ffast-math` must be detected at two layers: a compile fingerprint on a
fixed probe vector (deterministic) and a data-level count of bit-inconsistent cells.

### 2.6 Pre-registered ledger decision rule

The rule below was fixed before the numbers of Section 3 were computed; it is the rule implemented in
`papers/tools/m6369_ledger.py` and recorded in `data/ledger.json:gate`.

* Physical tolerance: 3 %, applicable to *implementation and reduction* errors.
* Numerical-equivalence budget: 1e-9 relative, from the Case C contract.
* Classes: **claim** = a point estimate asserting the value of the quantity; **bound** = an envelope
  over a stated convention sweep; **reference** = the independent yardstick itself.
* Admissibility of a claim: its published interval contains the yardstick **or** its point deviation
  is within the physical tolerance. Otherwise it is **rejected**.
* Admissibility of a bound: its interval contains the yardstick. A *dispersion* bound, which declares a
  maximum deviation over an ensemble instead of an interval over a sweep, carries no interval and is
  recorded as ADMISSIBLE-BOUND: it is not gated by the physical tolerance because it does not assert
  the value of the quantity, only the spread of the readings around it.
* A quantity for which no converged value exists in the tested range is labelled
  **measure-dependent**: it must be reported as a scale law plus a sampling interval, and a single
  "converged" number is inadmissible by construction.
* A quantity with no independent yardstick is labelled **no-yardstick**: comparative statements about
  it (for example, "the computed load exceeds the rule value by 30.727 %") must be stated as a band over
  conventions, not as a point.

Two mechanical cross-checks complement the gate. First, every reading is tested against the 95 %
interval of the reference *declustered* route; a reading outside it is flagged as a convention error
rather than as noise. Second, every report-stated deviation is recomputed arithmetically from the
source values and the difference is recorded (`data/ledger.json:consistency_checks`).

### 2.7 Software, toolchain and reproduction

Report #6980 was produced with Python 3.11.6, numpy 2.4.6 and scipy 1.16.0 on loongarch64 at git
commit `76c7b91f`; the Case B module (`tensordem.extreme_statistics`, 33 pytest cases) ran on torch
2.7 CPU; Case C compiled its reduction kernel with gcc 12.3.0 under three flag sets, recording the
SHA-256 of each build; Case D's module carries 23 pytest cases, including a negative control in which
uniform samples must be rejected by the KS test. The two platforms used in Case C are a control-plane
container (`loongarch64@ctr99`) and a cluster node (`loongarch64@n330`). x86_64 was requested by the
work order and is **not** available in this environment: both #7285 and #7289 record the x86_64 row as
WITHHELD rather than substituting a simulated value (`data/tables.json:tables.anchors.isa_withheld`).
All ledger computations, tables and figures in this manuscript are regenerated by three scripts:
`m6369_extract.py` (verbatim extraction), `m6369_ledger.py` (arithmetic and gates) and
`m6369_figures.py` (figures).

---

## 3 Results

### 3.1 Corpus inventory and coverage flags

Table 1 summarises the six reports. The window contributes 4 missions, 24 figures and 56 criteria
rows; three reports exceed 9000 characters of body text, and two are revisions (Section 3.6).

Flag coverage computed with the platform's own regular expressions is BASELINE 6/6, REPRO 6/6,
CRIT 6/6, UNCERT 5/6, SWEEP 4/6 and CLOUD 1/6. The single CLOUD hit is a false positive and is reported
as such: the only report whose text matches the field-plot vocabulary is #7100, and its section 4
states explicitly that field-contour plots do not apply to a one-dimensional hull-girder problem. The
effective field-plot coverage of the window is therefore 0/6, and the flag can only be used for
triage. This is exactly the failure mode documented for word-level flags in the platform's mining
notes: a negation counts as a hit. Fig. 6 shows the flag matrix and the per-report criteria-row counts.

**Table 1.** Corpus inventory (values from `data/tables.json:reports`, `n_criteria_rows`, `flags`).

| report | mission | role in the ledger | body chars | figures | criteria rows |
|---|---|---|---|---|---|
| #6503 | 5446 | Case B: GCI adjudication, resolution law | 4745 | 4 | 4 |
| #6504 | 5446 | Case B revision of #6503 (+45 chars) | 4790 | 4 | 5 |
| #6980 | 5684 | Case A: dual-route extreme extrapolation | 9682 | 6 | 6 |
| #7100 | 5679 | Case D: ice–wave combined hull-girder loads | 8794 | 6 | 12 |
| #7285 | 5753 | Case C: variance decomposition, portability | 9337 | 0 | 15 |
| #7289 | 5753 | Case C revision of #7285 (+371 chars, +4 figures) | 9708 | 4 | 14 |

**Table 2.** The six convention axes and what each one changes in this corpus (readings of Table 3).

| axis | values observed | effect on the reported value |
|---|---|---|
| estimator | BM-GEV MLE, POT-GPD MLE, analytic closed form | Case A: 138.09 versus 143.02 MN (3.6 % apart) |
| declustering | annual maxima, runs r = 72 h, none | Case A: 143.02 versus 167.78 MN (+17.3 %) |
| threshold / discretisation | u = 20.47–36.56 MN, r = 24–168 h, cell 0.125–1.0 m, Tp = 3.6–4.4 √Hs | Case A band 134.55–162.27 MN; Case B factor 1.7308; Case D band 331.9–442.6 MN·m |
| numerical path | canonical, ordered, async, fastmath, fp32 | Case C: at most 5.21e-06 relative on R10 |
| aggregation | single realisation, ensemble mean, max over cells, band over sweep | Case C: −0.0848 % (mean) versus 3.45 % (max over cells) |
| scale / spectral spread | block count, reference thickness, hull family | Case D: 1.31 to 1.52 in the ratio to the rule value |

### 3.2 Case A: one quantity, six readings

Table 3 lists the six readings of z100 with their provenance. Fig. 1 plots them together with the
yardstick and the ±3 % band; Fig. 2 shows the two convention sweeps that generate the bounds.

**Table 3.** Case A ledger: z100 [MN] of one simulated ice climate (report #6980); yardstick 144.11 MN
from a 2000-ice-year simulation. Deviations are recomputed arithmetically by `m6369_ledger.py`; the
report-stated values agree to within 0.044 percentage points (`data/ledger.json:consistency_checks`).

| id | reading (class) | value | published interval | dev. vs yardstick | ±3 % gate | ledger verdict | inside declustered 95 % interval |
|---|---|---|---|---|---|---|---|
| A1 | BM-GEV MLE, 100 blocks (claim) | 138.09 | [124.95, 166.77] | −4.1774 % | FAIL | ADMISSIBLE | yes |
| A2 | POT-GPD, u = 29.64 MN, r = 72 h (claim) | 143.02 | [128.67, 164.05] | −0.7564 % | PASS | ADMISSIBLE | yes |
| A3 | all exceedances, no declustering (claim) | 167.78 | none published | +16.425 % | FAIL | **REJECT** | **no** |
| A4 | threshold-sweep upper bound (bound) | 151.87 | [134.55, 151.87] | +5.3848 % | FAIL | ADMISSIBLE | yes |
| A5 | run-length-sweep upper bound (bound) | 162.27 | [134.69, 162.27] | +12.6015 % | FAIL | ADMISSIBLE | yes |
| A6 | yardstick, 2000 ice years (reference) | 144.11 | — | 0.0 % | PASS | BASELINE | yes |

Three observations follow mechanically.

First, the spread of the five candidate readings is 21.5 % (167.78 versus 138.09), seven times the
physical tolerance. A verification statement of the form "the return level agrees within 3 %" is
therefore not a property of the quantity but of the estimator-plus-convention tuple that produced it.

Second, the naive ±3 % gate accepts 1 of the 5 candidate readings (A2, −0.7564 %) and rejects the
block-maxima route (A1, −4.1774 %) even though A1 is statistically sound: its extrapolation
uncertainty U95 is 15.1 % at T = 100 years, against 12.4 % for the POT route. The point deviation of a
statistically correct estimator and the width of its own interval have the same order of magnitude;
gating the point at 3 % therefore tests luck, not correctness. The ledger gate accepts A1 because the
yardstick lies inside its interval [124.95, 166.77].

Third, the ledger rejects exactly one reading, A3, the un-declustered POT fit. The rejection is
independently corroborated: A3 is the only reading outside the declustered 95 % profile-likelihood
interval [128.67, 164.05] MN, and the source report attributes the +17.3 % to a joint bias of the
exceedance rate λ (64.32 versus 14.80 per year) and the shape parameter. The mechanism is a convention
error, not sampling noise, and the ledger catches it without any physical input.

The two bounds deserve a note. A4 and A5 are envelopes over 6 thresholds and 7 run lengths
respectively, and both *contain* the yardstick, so they are admissible as uncertainty statements; they
are not point claims and must not be quoted as such. They also delimit the honest resolution of the
quantity: any claim sharper than the envelope width (for A5, a range of 27.58 MN) is not supported by
the corpus. Fig. 2 shows that the envelope stays wide at the adopted run length, which is why the
source report explicitly refuses to look for a plateau in the extremal index and anchors the run
length physically instead.

Estimator-level diagnostics confirm the readings are not accidental: the GEV fit has KS p = 0.856
(bootstrap-calibrated 0.425) with ξ = −0.0492, the GPD fit has KS p = 0.616 (bootstrap 0.225) with
ξ = 0.0188. Interval coverage for this case is reported per parameter by the source report: the 95 %
profile interval covers the reference truth with frequency 97.5 % for the GEV z100, 91.7 % for the GPD
z100 and 95.0 % for the GPD shape parameter, all above the pre-registered 90 % floor. At T = 50 years
the two routes give 128.42 and 131.57 MN against a yardstick of 134.26 MN, the same ordering as at
T = 100 years.

### 3.3 Case B: a reproduced 19.78 % discretisation index that is not an error

The source report reproduces an earlier grid-refinement study exactly: the P95 depth field gives a
GCI of 19.78 % on the 0.25/0.5/1.0 m triple (original 19.78 %), with an observed order of 1 taken from
a theoretical fallback because the observed order fell outside [0.5, 2.5]. That reproduction is
itself a real verification result — the object certified is the same quantity. The question the ledger
asks is different: is 19.78 % a numerical error, a sampling artefact, or a property of the quantity?

Table 4 gives the four isotropic grid readings with their repeat-sample statistics, and Fig. 3 plots
the resolution law together with the sampling bar. The finest-two-grid difference is 19.47 %, which is
46.2 times the repeat-sample half-width at the fine level (0.42 %).
Sampling noise is therefore excluded by two orders of magnitude, and the value is not a Monte-Carlo
artefact. The four readings span a factor of 1.7308 (73.08 %), and the measured P95 follows a power
law in the cell size with exponent β_p = 0.261 [0.258, 0.265]: halving the cell raises the reported
P95 systematically.

**Table 4.** Case B ledger: P95 ice-abrasion depth [m/yr] as a function of the record grid
(reports #6503, #6504); repeat-sample statistics from 8 and 24 independent realisations.

| id | grid dx = dz [m] | cells | P95 [m/yr] | repeat CV | 95 % half-width | dev. vs finest grid | ±3 % gate | ledger verdict |
|---|---|---|---|---|---|---|---|---|
| B1 | 0.125 | 26640 | 4.9806e-05 | 0.50 % | 0.42 % | 0.0 % | PASS | MEASURE-DEPENDENT |
| B2 | 0.25 | 6660 | 4.1688e-05 | 1.10 % | 0.47 % | −16.2992 % | FAIL | MEASURE-DEPENDENT |
| B3 | 0.5 | 1480 | 3.5328e-05 | 1.79 % | 0.75 % | −29.0688 % | FAIL | MEASURE-DEPENDENT |
| B4 | 1 | 370 | 2.8776e-05 | 1.79 % | 0.76 % | −42.2238 % | FAIL | MEASURE-DEPENDENT |

Under the pre-registered rule this case is *measure-dependent*, and the ledger refuses to promote any
of the four numbers to "the" value. What it does certify is the report's own machine criteria: the
three-way centre agreement of P95 (independent repeats, block bootstrap, analytic) is 0.820 % against
a 3 % threshold; the profile-likelihood interval covers at 93.5 % over 400 replications against a 90 %
floor; every P95 value carries an interval; and the spatial extremal index has a plateau over 4
points at θ = 0.737 (a max-AR(1) forward model is used as the positive control and a = 0 series as the
negative control, in which θ = 1 is recovered, so the pipeline does not manufacture clustering).

The honest resolution of this case is thus two facts and not one: a scale law (β_p = 0.261
[0.258, 0.265], i.e. the reported P95 is a function of the record grid) and a sampling interval
(0.42 % at the finest grid). Any downstream use of a single P95 without the grid size is a
convention-free statement that the corpus cannot support.

Two further readings in the same report show where the ledger's own limits lie. The two-mechanism
model reproduces seven configurations with residuals up to 17.2 %, and the θ estimator has a
forward-model error up to 9.3 %; both are reported as honest failures and neither is used for
acceptance. That is the correct use of the ledger: a number that cannot be brought inside the gate is
kept as a diagnostic, not deleted and not promoted.

### 3.4 Case C: numerics versus statistics on a quantity with a closed-form yardstick

Case C is the opposite regime. The yardstick is an analytic Poisson-maxima closed form, R10 =
2447.0 kN, so every deviation is unambiguous. Two routes are fitted on a three-factor design
(2 platforms × 4 thread counts × 16 seeds).

The estimator-level readings agree well: the BM-GEV ensemble mean over 64 cells is 2444.925459 kN
(−0.0848 % versus the closed form) and the POT-GPD mean is 2456.475277 kN (+0.3872 %). The
aggregation axis then changes the verdict, exactly as Table 2 announces: the deviation of the
*ensemble mean* is below the 3 % gate, while the deviation of the *worst single cell* is 3.45 % for
BM and 3.59 % for POT, i.e. above it. Both statements are true, they answer different questions, and a
report that prints only one of them is not wrong but is not sufficient either.

**Table 5.** Case C ledger: R10 [kN] of a synthetic ice climate with an analytic yardstick of
2447.0 kN (reports #7285, #7289).

| id | reading (class) | value | dev. vs yardstick | ±3 % gate | ledger verdict |
|---|---|---|---|---|---|
| C1 | analytic closed form (reference) | 2447.0 | 0.0 % | PASS | BASELINE |
| C2 | BM-GEV ensemble mean, 64 cells (claim) | 2444.925459 | −0.0848 % | PASS | ADMISSIBLE |
| C3 | POT-GPD ensemble mean, 64 cells (claim) | 2456.475277 | +0.3872 % | PASS | ADMISSIBLE |
| C4 | BM-GEV worst single cell (bound) | — | 3.45 % | FAIL | ADMISSIBLE-BOUND |
| C5 | POT-GPD worst single cell (bound) | — | 3.59 % | FAIL | ADMISSIBLE-BOUND |

The numerical-path axis is where the ledger earns its keep. Across two platforms the canonical
reduction is bit-identical: mean peaks 645.273149 kN, P99 1459.099875 kN and both R10 values agree to
0.0 % with a two-sample KS p of 1.000, although the two machines run different numpy/scipy builds. The
portability ladder (Fig. 4a) then prices the non-canonical paths: the worst relative deviation of R10
is 4.42e-08 for `async` and `ordered`, 4.72e-06 for the genuinely compiled `fastmath` build and
5.21e-06 for the float32 accumulator, against a numerical-equivalence budget of 1e-9 and a physical
gate of 3 %. Bit-level reproducibility fails for three of the five paths (bit-inconsistent cell
fraction 1.000 for `async`, `ordered` and `fp32`, 0.25 for `fastmath`, 0.0 for canonical), yet the
physics-level deviation stays five to seven orders of magnitude below the gate. "Not bit-reproducible"
and "numerically inaccurate" are therefore two different defects, and the ledger keeps them apart with
two different thresholds.

Fig. 4b gives the variance decomposition. The total-order Sobol index of the random seed is 1.0000 for
all four responses, while the platform contributes 5.560e-16 and the thread count 1.089e-25 on R10;
the seed variance component is 1308.6 kN² against 1.364e-12 for the platform. The honest reading is
that in this problem the design load is a random variable whose sampling uncertainty dwarfs the
numerical one by roughly fifteen orders of magnitude, so any acceptance discussion must first say
which of the two it is testing.

Coverage confirms the intervals are calibrated: the profile-likelihood interval for the BM route
covers at 0.9550 with median relative width 0.0557, and for the POT route at 0.9400 with 0.0491, both
inside the pre-registered band [0.92, 0.98]. The threshold rule itself was revised once during the
source work, and the ledger records both versions rather than the final one only: the original rule,
which allowed a 0.90 quantile, gave POT coverage 0.820 and was rejected; the calibration study gives
0.9625 at a fixed 0.975 quantile, 0.9250 at a fixed 0.99 quantile and 0.9400 for the adopted rule.
A rejected rule that is visible is worth more than a rule that was quietly replaced.

### 3.5 Case D: a quantity with no yardstick, reported as a band

Case D has no independent yardstick, and the ledger says so instead of borrowing one. The long-term
10⁻⁸ extreme of the wave-induced vertical bending moment is 442.6, 381.2 and 331.9 MN·m under three
spectral spread conventions (Tp = 3.6, 4 and 4.4 √Hs), a band of 33.35 % that is entirely due to the
spread assumption (Fig. 5). The ratios to the IACS UR S11 hogging value 291.6 MN·m are 1.52, 1.31 and
1.14; to the sagging value 320.3 MN·m the comparison is similar.

Two statements can be made mechanically and one cannot. It *can* be stated that all three conventions
exceed both rule values, so the conservatism conclusion is convention-robust. It *can* be stated that
the band, not the point, is the deliverable: quoting "30.727 % above the rule value" without the spread
assumption overstates the precision of the result by a factor of three. It *cannot* be stated that the
computed load is verified, because a rule value is not an independent realisation of the same random
variable — it is a different physical object, defined by a different procedure.

The other readings in this case are of a different kind and are verified properly. The head-on DEM
impact peak reproduces the closed form V√(k·m) as 4.4721 versus 4.4721 MN (0.0002 %); the mean ice
force at h_ice = 0.8 m reproduces the Popov–Sazonov baseline at the same contact width as 0.95 versus
0.95 MN (ratio 1.00), while the full-beam-width baseline of 14.04 MN is a different quantity, not a
discrepancy; the GEV parameter recovery is μ to 0.10 % with |Δξ| = 0.022 and KS p = 0.988. The
geometry gate passes at 0.0051 % on Cb. The combined-load amplification factor γ is a *bound*: its
block-mean value spans 1.00 to 1.17 for VBM with 2 of 9 conditions inside the rule band [1.1, 1.5], and
the source report attributes the failure to a physically oversized DEM ice load rather than to the
combination algorithm — an attribution the ledger accepts as an honest FAIL and does not gate.

### 3.6 Revision audit: a claim migrates when it is reposted

Two of the six reports are revisions of another report in the same mission, produced minutes apart
(Table 6). Both revisions changed the error table.

**Table 6.** Revision audit (`data/ledger.json:revision_audit`). Hashes are SHA-256 prefixes of the
stored markdown.

| pair | mission | Δ body chars | Δ figures | Δ criteria rows | what changed in the error table |
|---|---|---|---|---|---|
| #6503 → #6504 | 5446 | +45 | 0 | +1 | one residual row (max ±3.1 %, verdict "no") split into two arm-specific rows (1.45 %, verdict "yes"; 4.12 %, verdict "no") |
| #7285 → #7289 | 5753 | +371 | +4 | −1 | the cross-platform POT R10 row changed from 5.21e-06 to 0.0e+00 |

The second pair is the instructive one. In #7285 the error table states a cross-platform relative
deviation of 5.21e-06 for the POT route. That number also appears in the portability ladder, where it
is the `fp32` path's worst relative deviation of R10 — a different axis (accumulator precision), not
the cross-platform axis. The same report's cross-platform table reports 0.0 % for R10 on both routes,
and the revised report (#7289) states 0.0e+00 for this row. The ledger therefore records the earlier
row as a mis-attribution and cites both reports; the arithmetic is unambiguous because
`data/tables.json` stores the two tables separately, so a value that exists in one table cannot be
used as evidence for a claim about the other.

The general lesson is a bookkeeping one, and it is why the ledger's key is the report id and not the
mission: a reposted report can flip a verdict without any physical change. In this window, one verdict
flipped in each direction — a "no" became two rows (one "yes", one "no"), and a non-zero numerical
seam became zero. Neither revision is an error, but a reader who pinned a claim to the mission rather
than to the report id would have quoted a number that no longer exists in the corpus.

### 3.7 Does the error fall below 3 %? Explicit per-reading answers

The gate question must be answered per reading, not once for the paper. Table 7 lists every gated
reading of the corpus with its deviation and an explicit yes/no against the 3 % physical tolerance.
The aggregate answer is: 5 of the 17 gated readings are inside 3 % (A2, C2, C3 and two self-consistent
verification quantities), 12 are outside, and the ledger's job is to say which of the 12 are outside
because of a defect and which because the 3 % question is the wrong question for that class.

**Table 7.** Explicit 3 % verdicts (`data/error_table.csv`, plus the per-case verification quantities
of Sections 3.3–3.5).

| case | reading | quantity | deviation | < 3 % ? | why |
|---|---|---|---|---|---|
| A | A1 | z100, BM-GEV | −4.1774 % | no | interval [124.95, 166.77] contains the yardstick; U95 = 15.1 % |
| A | A2 | z100, POT-GPD | −0.7564 % | yes | — |
| A | A3 | z100, un-declustered | +16.425 % | no | convention error (λ and ξ jointly biased) |
| A | A4 | z100, threshold bound | +5.3848 % | no, by class | bound, contains the yardstick |
| A | A5 | z100, run-length bound | +12.6015 % | no, by class | bound, contains the yardstick |
| B | B2 | P95, dx = 0.25 m | −16.2992 % | no, by class | measure-dependent (β_p = 0.261) |
| B | B3 | P95, dx = 0.5 m | −29.0688 % | no, by class | measure-dependent |
| B | B4 | P95, dx = 1 m | −42.2238 % | no, by class | measure-dependent |
| B | — | finest-two-grid difference | 19.47 % | no, by class | 46.2 times the sampling half-width |
| C | C2 | R10, BM ensemble mean | −0.0848 % | yes | — |
| C | C3 | R10, POT ensemble mean | +0.3872 % | yes | — |
| C | C4 | R10, BM worst cell | 3.45 % | no | aggregation axis, not estimator error |
| C | C5 | R10, POT worst cell | 3.59 % | no | aggregation axis, not estimator error |
| D | D2 | VBM 10⁻⁸ extreme, Tp = 4√Hs | +30.727 % | no | rule value is not a yardstick |
| — | — | Cb recomputed from section closure | 0.0051 % | yes | geometry gate |
| — | — | DEM head-on peak versus V(t)√(k·m) | 0.0002 % | yes | closed-form anchor |
| — | — | mean ice force versus Popov–Sazonov, same width | 0.0 % | yes | same-width baseline |

The mechanical provenance check closes the loop: `papers/tools/m6369_provenance.py` tokenises every
numeric literal in this manuscript and resolves it against the data artefacts, with the coverage
figure recorded in `data/provenance.json`. Bibliographic years, section numbers, report ids and
standard designations are exempt classes, listed explicitly.

---

## 4 Discussion

### 4.1 What the ledger buys

Three error kinds that are usually entangled are separable in the corpus, and the separation is
quantified rather than argued.

*Extrapolation uncertainty* is of order 10 %: the 95 % profile-likelihood half-width of z100 is 15.1 %
(BM) and 12.4 % (POT), which is 4 to 5 times the physical tolerance. Any 3 % statement about an
extrapolated design quantile is therefore a statement about one realisation, not about the quantity.

*Convention dependence* is of order 21.5 % to 73.08 %: the spread within Case A is 21.5 %, within Case B a
factor of 1.7308, within Case D 33.35 %. These numbers are not errors and cannot be removed by better
fitting; they can only be declared.

*Implementation error* is of order 4.42e-08 to 5.21e-06 relative: the worst non-canonical numerical path in
Case C deviates from the closed-form R10 by 5.21e-06, five orders of magnitude below the physical
gate. Mixing this with the first two is the standard failure mode of "the code agrees within 3 %"
language: the sentence is true and informative for the third kind, meaningless for the first.

The second thing the ledger buys is *detection without physics*. The rejection of A3 required no
knowledge of ice mechanics: it followed from the reading lying outside the reference interval of its
own family and from the rate/shape bias documented by the source. Similarly, the mis-attribution in
Section 3.6 was detected by asking which table a number belongs to, not by re-deriving the number.

### 4.2 Relation to existing practice and to codes

Our scheme is a bookkeeping layer on top of established estimators, not a replacement for them: the
GEV/GPD machinery, the profile-likelihood intervals, the declustering and the GCI estimator are used
exactly as published (Roache, 1994; Celik et al., 2008; Coles, 2001; Ferro & Segers, 2003). The
addition is the accountability axis: which of these procedures produced the number, and which
independent quantity it is compared against.

Relative to existing practice, three differences matter. (i) A single tolerance applied to a point
estimate is replaced by a class-aware rule, which changes the verdict on 4 of 5 readings in Case A.
(ii) A convergence index is replaced, where no continuous limit exists, by a scale law plus a sampling
interval; the 19.78 % GCI is then not a failed convergence but a measured property of the quantity
(β_p = 0.261). (iii) A code comparison is refused where the code value is not a realisation of the same
random variable; Case D's rule comparison is reported as a band over three spread conventions with
ratios 1.14 to 1.52, which is enough to support a conservatism statement and not enough to support a
verification statement.

**Code values used here, kept in two separate columns.** The IACS UR S11 hogging and sagging wave
bending moments used in Section 3.5 are 291.6 MN·m and 320.3 MN·m as quoted in report #7100, and the
ISO 19906-type pressure–area relation enters Case A with a generator exponent a = 0.400 and reference
thickness h_ref = 1.000 m as quoted in report #6980; the local pressure size-effect coefficient in
Case C is κ = 0.15. These are *implementation inputs* extracted from the reports, not values verified
against the standards inside this worktree: the standards' clause-level statements (IACS UR S11
wave-bending-moment formula; ISO 19906 global and local ice action clauses) were **not** re-derived
here, and the pressure–area exponent is not validated against ice-structure measurements by any
in-window evidence — the two reports use different exponents (0.400 for a global force–thickness law,
0.15 for a local pressure size effect), which is a scope difference and not a disagreement, but it is
also not a validation. Clause-level verification of both standards is recorded as NO-DATA-TBD in the
provenance file rather than asserted.

### 4.3 Limits of applicability

The ledger is agnostic about physics, but its conclusions are not. The following limits are binding.

*Parameter ranges.* Case A is one synthetic ice climate with the parameters of Section 2.3 and a
single seed; the 2000-ice-year yardstick is the same generator with a different seed, so it tests the
extrapolator, not the physics. Case D covers H_s ∈ [1, 4] m × h_ice ∈ [0.5, 1.2] m at one heading
(150°) and one speed (6 kn); nothing is claimed outside that envelope. Case B covers cell sizes
0.125 to 1.0 m with a wear coefficient that is a computational guess (1e-14 m³/(N·m)) against a
calibrated 8.19e-15.

*Geometry families.* Two hulls enter the corpus: a 185 m hull at Cb = 0.82 (Case B) and a 110 m
ice-class multipurpose ship at Cb = 0.780 (Case D). Both are single-hull, wall-sided idealisations;
no bulbous-bow family, no twin-screw aft body, no full-scale geometry is covered. The geometry gate
itself (Cb from section closure, 0.0051 % residual) is a necessary condition only: it certifies
consistency, not hydrodynamic or structural fidelity.

*Not measured.* No model-test or full-scale ice-load time history exists in the corpus. Report #7100
records the model-test comparison as WITHHELD for exactly this reason, and the ledger honours it: a
WITHHELD reading cannot be converted into a pass by supplying a standard value.

*Not executed.* x86_64 was requested by the work order and is unavailable; both reports record it as
WITHHELD. Cross-ISA portability therefore rests on real compiled proxy paths on loongarch64
(`-ffast-math`, float32, three reduction orders) and not on an x86_64 measurement.

*Corpus-level.* Field-contour coverage of the window is 0/6 despite the word-level flag reading 1/6;
there is no fluid-domain plot in the corpus, and the six reports are all statistics-, beam- or
particle-level studies.

### 4.4 Threats to validity of this study itself

The unit of analysis is *text plus extracted tables*, so the study inherits the source reports'
mistakes. Its provenance is one hop from the artefacts: the underlying `artifacts/...` files live in
the solver repositories and were not re-executed here, so a report that mis-transcribed its own JSON
would not be caught by this ledger — it would be caught only by re-running the pipeline. What the
ledger does catch is arithmetic inconsistency, interval inconsistency, class confusion and
cross-table mis-attribution, all of which occurred at least once in six reports.

The yardstick's independence is the weak point of the whole construction. Where the yardstick comes
from the same generator (Case A) it validates the extrapolator, not the model; where it comes from an
analytic closed form (Case C) it validates the implementation, not the physics; where it is absent
(Case D) the ledger can only report a band. A systematically biased physics model that is internally
consistent and compared only against itself would pass every gate in this paper. That is why the
strongest claim we make is procedural: the ledger makes the *kind* of evidence explicit, and it fails
loudly when a claim is compared against the wrong kind.

Finally, the word-level coverage flags are triage instruments. They are useful (they summarise the
evidence face of a window in one table) and they lie (a negation counted as a field-plot hit). Any
downstream use must re-read the source, as done for #7100 in Section 3.1.

---

## 5 Conclusion

1. A claim ledger — six-axis convention tuples, explicit classes for claim, bound, yardstick and
   measure-dependent readings, artefact-level provenance, and a pre-registered two-class gate — was
   built and applied to 18 readings of 4 quantities in 6 reports from 4 missions (24 figures,
   56 criteria rows).
2. For one ice climate the 100-year return level is reported six ways spanning 21.5 %
   (138.09 to 167.78 MN) around a 2000-ice-year yardstick of 144.11 MN. A naive ±3 % gate accepts 1 of
   the 5 candidate readings; the ledger gate accepts 4 and rejects exactly the un-declustered reading,
   which is also the only one outside the declustered 95 % interval [128.67, 164.05] MN.
3. A reproduced 19.78 % discretisation index is shown to be measure dependence rather than numerical
   error: the finest-two-grid difference (19.47 %) is 46.2 times the repeat-sample half-width
   (0.42 %), and the quantity obeys a power law with exponent 0.261 [0.258, 0.265]. The admissible
   output is a scale law plus a sampling interval, not a converged number.
4. On a quantity with a closed-form yardstick the estimator-level readings are −0.0848 % and
   +0.3872 %, the worst single cell reaches 3.45 % and 3.59 %, and the worst non-canonical numerical
   path 5.21e-06. Extrapolation uncertainty (order 10 %), convention dependence (20 % to 73 %) and
   implementation error (4.42e-08 to 5.21e-06) are thereby separated by two to six orders of magnitude.
5. Two of the six reports are revisions of another report in the same mission; both changed an error
   table, and one earlier row is traceable to a value mis-attributed from the portability ladder. The
   ledger's key is therefore the report id, not the mission.
6. What the corpus cannot support is stated as such: no model-test ice-load data, no x86_64 execution,
   no field-contour evidence, no clause-level verification of the IACS and ISO values, and no
   validation of the pressure–area exponent against measurements. These are recorded as WITHHELD or
   NO-DATA-TBD, not absorbed into a pass.

---

## References

Celik, I.B., Ghia, U., Roache, P.J., Freitas, C.J., Coleman, H., Raad, P.E. (2008). Procedure for
estimation and reporting of uncertainty due to discretization in CFD applications. *ASME Journal of
Fluids Engineering* 130(7), 078001.

Coles, S. (2001). *An Introduction to Statistical Modeling of Extreme Values*. Springer-Verlag,
London.

Davison, A.C., Smith, R.L. (1990). Models for exceedances over high thresholds (with discussion).
*Journal of the Royal Statistical Society, Series B* 52(3), 393–442.

Efron, B., Tibshirani, R.J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall, New York.

Ferro, C.A.T., Segers, J. (2003). Inference for clusters of extreme values. *Journal of the Royal
Statistical Society, Series B* 65(2), 545–556.

Gumbel, E.J. (1958). *Statistics of Extremes*. Columbia University Press, New York.

Hosking, J.R.M., Wallis, J.R. (1987). Parameter and quantile estimation for the generalized Pareto
distribution. *Technometrics* 29(3), 339–349.

IACS. *Unified Requirement S11: Longitudinal Strength Standard*. International Association of
Classification Societies, London. (Document-level citation: the revision year and the clause numbering
used by report #7100 were not re-verified inside this worktree; see Section 4.2 and
`data/provenance.json`.)

ISO 19906:2010. *Petroleum and natural gas industries — Arctic offshore structures*. International
Organization for Standardization, Geneva. (Document-level citation; the clause-level statements used
by reports #6980 and #7100 were not re-verified inside this worktree.)

Jonathan, P., Ewans, K. (2013). Statistical modelling of extreme ocean environments for marine design:
a review. *Ocean Engineering* 62, 91–109.

Jordaan, I.J. (2005). *Decisions under Uncertainty: Probabilistic Analysis for Engineering Decisions*.
Cambridge University Press, Cambridge.

Leadbetter, M.R., Lindgren, G., Rootzén, H. (1983). *Extremes and Related Properties of Random
Sequences and Processes*. Springer-Verlag, New York.

Oberkampf, W.L., Roy, C.J. (2010). *Verification and Validation in Scientific Computing*. Cambridge
University Press, Cambridge.

Roache, P.J. (1994). Perspective: a method for uniform reporting of grid refinement studies. *ASME
Journal of Fluids Engineering* 116(3), 405–413.

Sanderson, T.J.O. (1988). *Ice Mechanics: Risks to Offshore Structures*. Graham & Trotman, London.

Smith, R.L. (1987). Estimating tails of probability distributions. *The Annals of Statistics* 15(3),
1174–1207.

Stern, F., Wilson, R.V., Coleman, H.W., Paterson, E.G. (2001). Comprehensive approach to verification
and validation of CFD simulations — Part 1: Methodology and procedures. *ASME Journal of Fluids
Engineering* 123(4), 793–802.

Timco, G.W., Weeks, W.F. (2010). A review of the engineering properties of sea ice. *Cold Regions
Science and Technology* 60(2), 107–129.

---

## Data Availability

Everything needed to regenerate this manuscript is in the worktree, and each artefact names the report
id it came from.

| path | content |
|---|---|
| `papers/ice-load-statistics/data/reports.json` | verbatim markdown of reports #6503, #6504, #6980, #7100, #7285, #7289, fetched by `papers/tools/m6369_fetch.py` |
| `papers/ice-load-statistics/data/tables.json` | every extracted table row with its verbatim source line and line number, report hashes, flag matrix, criteria rows |
| `papers/ice-load-statistics/data/ledger.json` | the 18 readings with convention tuples, classes, deviations, both gates, consistency checks, revision audit |
| `papers/ice-load-statistics/data/error_table.csv` | pointwise error table (Table 7 data source) |
| `papers/ice-load-statistics/data/return_levels.csv`, `sampling_p95.csv`, `sobol_7285.csv`, `portability_7285.csv` | figure inputs |
| `papers/ice-load-statistics/data/provenance.json` | machine tokenisation of this manuscript: coverage percentage, unresolved tokens, exempt classes |
| `papers/ice-load-statistics/figures/fig1_ledger_caseA.png` … `fig6_corpus_coverage.png` | all six figures, generated by `papers/tools/m6369_figures.py` |
| `papers/tools/m6369_fetch.py`, `m6369_extract.py`, `m6369_ledger.py`, `m6369_figures.py`, `m6369_provenance.py` | the reproduction chain, in order |

Reproduction:

```bash
python3 papers/tools/m6369_fetch.py          # requires TENSOR_AGENT_USER / TENSOR_AGENT_PASS
python3 papers/tools/m6369_extract.py
python3 papers/tools/m6369_ledger.py
python3 papers/tools/m6369_figures.py
python3 papers/tools/m6369_provenance.py    # token-level provenance audit of this file
python3 -m pytest papers/tools/test_m6369_artifacts.py -q
```

The source reports' own artefacts (`artifacts/ice_extremes/summary.json`,
`artifacts/extreme_stats/certification.json`, `artifacts/in34w3n07/*`, `artifacts/ice_wave_global_loads/*`)
live in the solver repositories and are **not** re-executed here; this study's provenance is one hop
from them, and Section 4.4 states what that does and does not imply.