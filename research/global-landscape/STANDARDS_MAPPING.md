# Standards and Interoperability Mapping

Research snapshot: 2026-11-09.

## Recommended posture

Adopt a standards-compatible core with explicit mappings. The TensorKnowledge Knowledge Object remains the application-level contract; adapters map it to established vocabularies and packages. Do not force the internal model wholesale into one standard.

## Mapping

| Standard | Scope | TensorKnowledge mapping | Recommendation |
|---|---|---|---|
| W3C PROV-O | Provenance of entities, activities, agents | Object/version = Entity; research/production/review = Activity; person/agent/tool/org = Agent | P0 mapping and export fixture |
| RO-Crate 1.3 | Research object package with JSON-LD | Package objects with source docs, data, code, models, workflows, people and environment | P0 export profile |
| FAIR | Findable, Accessible, Interoperable, Reusable | Persistent IDs, metadata, access policy, formats, rights | P0 stewardship checklist, not truth score |
| DataCite | DOI and research output metadata | Dataset/software/model/report references | P1 metadata normalization |
| Schema.org | Common web vocabulary | CreativeWork, Dataset, SoftwareSourceCode, Person, Organization | P1 JSON-LD crosswalk |
| JSON-LD 1.1 | Linked data serialization | Stable IDs/types and external contexts | P1 export representation |
| Dublin Core Terms | Generic resource metadata | creator, title, date, type, identifier, rights, source | P1 artifact crosswalk |
| SKOS | Concept schemes/taxonomies | Concept, broader/narrower, related, labels | P1 controlled vocabularies |
| OpenAlex | Scholarly entity metadata | External work/author/source/institution/topic identifiers | P0 scholarly discovery adapter |
| Semantic Scholar | Scholarly discovery/citation metadata | Discovery and citation links | P1 secondary provider |
| Crossref | DOI registration metadata | DOI resolution and bibliographic metadata | P0 DOI resolution |
| ORCID | Researcher identity | Optional human researcher identifiers | P1 |
| Wikidata | External entity graph | SameAs/external entity links | P2, contextual only |
| UNESCO AI competency | AI learning competency framework | Curriculum mapping | P1 |
| ESCO | EU skills/occupations taxonomy | External skill/occupation identifiers | P1 mapping only |
| O*NET | US occupational taxonomy | Occupational skill crosswalk | P2 regional extension |

## Semantic distinctions

### Provenance is not evidence quality
PROV-O records which entities, activities and agents were involved. It does not establish whether a claim is true.

### FAIR is not epistemic validation
FAIR improves data stewardship and reuse. A FAIR dataset can still contain erroneous or biased measurements. Never map FAIR compliance directly to evidence_status.

### RO-Crate is a package, not the canonical knowledge model
Use it to package research artifacts and contextual metadata. It complements Knowledge Objects; it does not replace claim-level structures and review decisions.

### Identifiers are not citations; citations are not entailment
A DOI/OpenAlex ID resolves a work. A citation identifies a source. A locator identifies a relevant passage, page, table or figure. A separate evidence relation must say whether that passage supports, refutes, qualifies or contextualizes a claim.

### Taxonomies are not theories
ESCO, O*NET and UNESCO are useful mapping targets. Preserve TensorKnowledge's own versioned competency framework and make mappings explicit: exact, broader, narrower, related or partial.

## Proposed schema evolution

The current v0.1 Knowledge Object is a sound first draft, but sources and provenance are too coarse for long-term evidence governance. Consider adding separately versioned contracts:

1. Claim Record: atomic statement, scope, modality, conditions and status.
2. Evidence Record: source entity, exact locator, quoted/extracted span, relation (supports/refutes/qualifies/contextualizes), extraction method and assessment.
3. Provenance Record: PROV-O-compatible entity/activity/agent, timestamps, software/model/tool versions and derivation links.
4. Review Event: append-only decision, reviewer role, policy version, rationale and timestamp.
5. Temporal Record: valid-time and observation/record-time for changing facts.
6. Rights Record: license, copyright status, access restrictions, attribution and permitted transformations.
7. External Identifiers: namespace/value pairs for DOI, ORCID, OpenAlex, Semantic Scholar and domain identifiers.
8. Typed Relations: source/target, relation, qualifiers, temporal scope and provenance.

Do not inflate one JSON object indefinitely. Keep evidence/provenance/review records modular and reference them from Knowledge Object.

## Interoperability deliverables

- Evidence and provenance schemas.
- RO-Crate export profile and fixtures.
- PROV-O property crosswalk and example.
- Schema.org/JSON-LD mapping.
- Academic identifier resolver for DOI, OpenAlex, Semantic Scholar and ORCID.
- Round-trip tests that report information loss.

## Primary references

- PROV-O: https://www.w3.org/TR/prov-o/
- RO-Crate 1.3: https://www.researchobject.org/ro-crate/specification/1.3/
- RO-Crate metadata: https://www.researchobject.org/ro-crate/specification/1.3/metadata
- FAIR: https://www.go-fair.org/fair-principles/
- DataCite: https://schema.datacite.org/
- Schema.org: https://schema.org/
- JSON-LD: https://www.w3.org/TR/json-ld11/
- SKOS: https://www.w3.org/TR/skos-reference/
- OpenAlex API: https://help.openalex.org/api/
- UNESCO: https://www.unesco.org/en/articles/ai-competency-framework-students
- ESCO: https://esco.ec.europa.eu/en
