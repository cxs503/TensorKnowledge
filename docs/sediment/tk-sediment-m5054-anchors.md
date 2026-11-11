# External anchors for the m5054 sediment package

These are the primary references against which the claims in
`knowledge/sediment/tk-sediment-m5054/` are meant to be read. They are registered as
`external_anchors` in `knowledge/sediment/tk-sediment-m5054/spec.json` (mirrored to
`anchors.json` and `INDEX.md`), and they are *anchors*, not validations: no claim
in the package has been checked against them by an independent reviewer yet
(`assessment_status = unassessed`).

| Anchor | DOI | Which claim it bounds |
|---|---|---|
| Monaghan 1992, *Smoothed Particle Hydrodynamics*, Annu. Rev. Astron. Astrophys. 30:543–574 | 10.1146/annurev.aa.30.090192.002551 | `kernel-quadrature-exact`, `mass-calibration-lattice-constant` — kernel admissibility (unity + second-moment normalisation) |
| Morris, Fox & Zhu 1997, *Modeling low Reynolds number incompressible flows using SPH*, J. Comput. Phys. 136:214–263 | 10.1006/jcph.1997.5732 | `laplacian-renorm-scope` — the renormalised viscous-operator family |
| Randles & Libersky 1996, *Smoothed Particle Hydrodynamics: some recent improvements and applications*, CMAME 139:375–408 | 10.1016/S0045-7825(96)01090-0 | `laplacian-renorm-scope` — corrected-SPH / reproducing conditions behind the second-moment normalisation |
| Adami, Hu & Adams 2012, *A generalized wall boundary condition for smoothed particle hydrodynamics*, J. Comput. Phys. 231:7057–7075 | 10.1016/j.jcp.2012.06.034 | `hydrostatic-headline-is-a-single-point` — the wall model whose bottom load is the headline number |
| Colagrossi & Landrini 2003, *Numerical simulation of interfacial flows by smoothed particle hydrodynamics*, J. Comput. Phys. 191:448–475 | 10.1016/S0021-9991(03)00398-3 | `hydrostatic-headline-is-a-single-point` — free-surface spurious pressure / odd-even mode visible in the per-layer table |

## What the anchors do *not* cover

* They do not make the source's 2.7 % headline numbers general claims: the
  package's benchmark table shows the same operator at 12.6 % (n = 12) and 25.2 %
  (Tait wall). The anchor explains *why* a renormalised operator should converge;
  it says nothing about a single coarse-grid point.
* They are literature anchors, not experimental data. The source mission contains
  no experimental validation of the 3-D operators, so no claim here is graded
  against an experiment (that would require a separate, experimental benchmark).

## How to check an anchor

```bash
python3 -c "import json;print(json.load(open('knowledge/sediment/tk-sediment-m5054/anchors.json'))[0])"
# DOI resolution can be checked without the package:
curl -sI https://doi.org/10.1146/annurev.aa.30.090192.002551 | head -1
```