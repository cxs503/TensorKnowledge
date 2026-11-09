"""Self-built thin layer ("Option C") for the TensorKnowledge engine selection.

A deliberately small (~single file) layer that stores the four TensorKnowledge
contracts in PostgreSQL and serves the four retrieval primitives the pilot
requires, plus PROV-O export and a lossless round-trip back to the contract
JSON. It exists to give the Cognee/Graphiti comparison an honest baseline:
what does one engineer lose by *not* adopting a framework, and what does the
framework buy that this does not do?

Design decisions that matter for the evaluation
  * PostgreSQL 15 as the only backend (the deployment target); no vector
    extension available -> cosine similarity is implemented as a SQL function
    over float8[], and lexical retrieval uses core `tsvector`.
  * Embeddings are a deterministic hashed character-ngram TF vector
    (no external embedding service needed; the container has no embedding
    endpoint - see report). Swappable: `Embedder` is an interface.
  * The four contracts are stored as *columns for the fields that are queried*
    (status, domain, relation, timestamps) and as `jsonb` for the rest, so the
    round-trip is lossless by construction while the query surface stays
    indexed. This is the key structural difference to framework graph models,
    which normalise into nodes/edges and therefore lose contract fields.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import time
from dataclasses import dataclass

DDL = """
DROP SCHEMA IF EXISTS ke CASCADE;
CREATE SCHEMA ke;

CREATE TABLE ke.claim (
  id            text NOT NULL,
  version       text NOT NULL,
  statement     text NOT NULL,
  claim_type    text NOT NULL,
  epistemic_status text NOT NULL,
  domain        text NOT NULL,
  modality      text,
  created_by    text,
  created_at    timestamptz,
  valid_start   timestamptz,
  valid_end     timestamptz,
  evidence_refs text[] DEFAULT '{}',
  supersedes    text[] DEFAULT '{}',
  payload       jsonb NOT NULL,          -- full contract record, lossless
  fts           tsvector,
  PRIMARY KEY (id, version)
);
CREATE INDEX ON ke.claim (epistemic_status);
CREATE INDEX ON ke.claim (domain);
CREATE INDEX ON ke.claim USING gin (fts);

CREATE TABLE ke.evidence (
  id           text NOT NULL,
  version      text NOT NULL,
  relation     text NOT NULL,            -- supports|refutes|qualifies|contextualizes|mentions
  assessment_status text NOT NULL,
  locator_type text,
  locator      text,
  citation     text,
  captured_at  timestamptz,
  captured_by  text,
  payload      jsonb NOT NULL,
  PRIMARY KEY (id, version)
);
CREATE INDEX ON ke.evidence (relation);

CREATE TABLE ke.evidence_claim (                 -- the evidence relation graph
  evidence_id text NOT NULL,
  claim_id    text NOT NULL,
  relation    text NOT NULL,
  PRIMARY KEY (evidence_id, claim_id)
);
CREATE INDEX ON ke.evidence_claim (claim_id);

CREATE TABLE ke.provenance (
  id          text NOT NULL,
  version     text NOT NULL,
  entity_id   text NOT NULL,
  entity_type text NOT NULL,
  activity_id text NOT NULL,
  activity_type text NOT NULL,
  agents      jsonb NOT NULL,
  derived_from text[] DEFAULT '{}',
  recorded_at timestamptz,
  payload     jsonb NOT NULL,
  PRIMARY KEY (id, version)
);
CREATE INDEX ON ke.provenance (entity_id);
CREATE INDEX ON ke.provenance USING gin (derived_from);

CREATE TABLE ke.kobject (
  id            text NOT NULL,
  version       text NOT NULL,
  title         text NOT NULL,
  object_type   text NOT NULL,
  domains       text[] NOT NULL,
  evidence_status text NOT NULL,
  review_status text NOT NULL,
  claim_refs    text[] DEFAULT '{}',
  evidence_refs text[] DEFAULT '{}',
  provenance_refs text[] DEFAULT '{}',
  payload       jsonb NOT NULL,
  PRIMARY KEY (id, version)
);
CREATE INDEX ON ke.kobject USING gin (domains);

CREATE TABLE ke.review_event (
  id           text NOT NULL,
  object_ref   text NOT NULL,
  object_version text NOT NULL,
  decision     text NOT NULL,
  reviewer_id  text NOT NULL,
  reviewed_at  timestamptz,
  policy_version text NOT NULL,
  payload      jsonb NOT NULL,
  PRIMARY KEY (id)
);

CREATE TABLE ke.embedding (
  claim_id text NOT NULL,
  dim      int  NOT NULL,
  vec      float8[] NOT NULL,
  model    text NOT NULL,
  PRIMARY KEY (claim_id)
);

-- cosine similarity inside the database (no pgvector available)
CREATE OR REPLACE FUNCTION ke.cosine(a float8[], b float8[]) RETURNS float8 AS $$
DECLARE i int; dot float8 := 0; na float8 := 0; nb float8 := 0;
BEGIN
  IF array_length(a,1) IS DISTINCT FROM array_length(b,1) THEN RETURN 0; END IF;
  FOR i IN 1..array_length(a,1) LOOP
    dot := dot + a[i]*b[i]; na := na + a[i]*a[i]; nb := nb + b[i]*b[i];
  END LOOP;
  IF na = 0 OR nb = 0 THEN RETURN 0; END IF;
  RETURN dot / (sqrt(na)*sqrt(nb));
END; $$ LANGUAGE plpgsql IMMUTABLE;

-- governance invariant: the producer of a claim may not review it
CREATE OR REPLACE FUNCTION ke.reject_self_approval() RETURNS trigger AS $$
DECLARE producer text;
BEGIN
  SELECT created_by INTO producer FROM ke.claim WHERE id = NEW.object_ref LIMIT 1;
  IF producer IS NOT NULL AND producer = NEW.reviewer_id THEN
    RAISE EXCEPTION 'self-approval rejected: % reviewed own claim %', NEW.reviewer_id, NEW.object_ref;
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_no_self_approval BEFORE INSERT ON ke.review_event
FOR EACH ROW EXECUTE FUNCTION ke.reject_self_approval();
"""


def hashed_ngram_vec(text: str, dim: int = 256) -> list[float]:
    """Deterministic local embedding: hashed char 3-gram term frequency, L2 normed.

    Used because the container exposes a chat LLM gateway but no embedding
    model (see report). Any real embedder can replace it: same interface.
    """
    vec = [0.0] * dim
    toks = re.findall(r"[a-z0-9]+", text.lower())
    grams = toks + [t[i:i + 3] for t in toks for i in range(max(1, len(t) - 2))]
    for g in grams:
        h = int.from_bytes(hashlib.blake2b(g.encode(), digest_size=8).digest(), "big")
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


@dataclass
class Metrics:
    ingest_s: float
    queries: dict

    def as_dict(self) -> dict:
        return {"ingest_s": round(self.ingest_s, 3),
                "queries": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                                for kk, vv in v.items()} for k, v in self.queries.items()}}


class ThinLayer:
    def __init__(self, dsn: str):
        import psycopg
        self.psycopg = psycopg
        self.conn = psycopg.connect(dsn, autocommit=True)

    def init_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(DDL)
            # trigram index above needs pg_trgm; fall back to plain btree-if-absent
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                cur.execute("CREATE INDEX ON ke.claim USING gin (domain gin_trgm_ops)")
            except Exception:
                self.conn.rollback() if not self.conn.autocommit else None

    # ------------------------------------------------------------------ ingest
    def ingest(self, corpus: dict) -> dict:
        t0 = time.perf_counter()
        counts = {}
        with self.conn.cursor() as cur:
            n = 0
            for c in corpus["claims"]:
                scope = c.get("scope") or {}
                vt = c.get("valid_time") or {}
                cur.execute(
                    """INSERT INTO ke.claim (id,version,statement,claim_type,epistemic_status,domain,
                          modality,created_by,created_at,valid_start,valid_end,evidence_refs,supersedes,payload,fts)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,to_tsvector('simple',%s))
                       ON CONFLICT (id,version) DO UPDATE SET statement=EXCLUDED.statement,
                          epistemic_status=EXCLUDED.epistemic_status, payload=EXCLUDED.payload,
                          fts=EXCLUDED.fts""",
                    (c["id"], c["version"], c["statement"], c["claim_type"], c["epistemic_status"],
                     scope.get("domain", "unspecified"), c.get("modality"), c.get("created_by"),
                     c.get("created_at"), vt.get("start"), vt.get("end"),
                     c.get("evidence_refs") or [], c.get("supersedes") or [],
                     json.dumps(c), c["statement"]))
                cur.execute("""INSERT INTO ke.embedding (claim_id,dim,vec,model) VALUES (%s,%s,%s,%s)
                               ON CONFLICT (claim_id) DO UPDATE SET vec=EXCLUDED.vec""",
                            (c["id"], 256, hashed_ngram_vec(c["statement"]), "hashed-char3gram-256"))
                n += 1
            counts["claims"] = n

            n = 0
            for e in corpus["evidence"]:
                src = e.get("source") or {}
                loc = e.get("locator") or {}
                cur.execute(
                    """INSERT INTO ke.evidence (id,version,relation,assessment_status,locator_type,locator,
                          citation,captured_at,captured_by,payload)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (id,version) DO UPDATE SET relation=EXCLUDED.relation, payload=EXCLUDED.payload""",
                    (e["id"], e["version"], e["relation"], e["assessment_status"],
                     loc.get("locator_type"), loc.get("value"), src.get("citation"),
                     e.get("captured_at"), e.get("captured_by"), json.dumps(e)))
                for cid in e.get("claim_refs") or []:
                    cur.execute("""INSERT INTO ke.evidence_claim (evidence_id,claim_id,relation)
                                   VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                                (e["id"], cid, e["relation"]))
                n += 1
            counts["evidence"] = n

            n = 0
            for p in corpus["provenance"]:
                ge = p["generated_entity"]; ac = p["activity"]
                cur.execute(
                    """INSERT INTO ke.provenance (id,version,entity_id,entity_type,activity_id,activity_type,
                          agents,derived_from,recorded_at,payload)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (id,version) DO UPDATE SET payload=EXCLUDED.payload""",
                    (p["id"], p["version"], ge["id"], ge["entity_type"], ac["id"], ac["activity_type"],
                     json.dumps(p.get("agents") or []), p.get("derived_from") or [],
                     p.get("recorded_at"), json.dumps(p)))
                n += 1
            counts["provenance"] = n

            n = 0
            for o in corpus["objects"]:
                cur.execute(
                    """INSERT INTO ke.kobject (id,version,title,object_type,domains,evidence_status,
                          review_status,claim_refs,evidence_refs,provenance_refs,payload)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (id,version) DO UPDATE SET payload=EXCLUDED.payload""",
                    (o["id"], o["version"], o["title"], o["object_type"], o["domains"],
                     o["evidence_status"], o["review_status"], o.get("claim_refs") or [],
                     o.get("evidence_refs") or [], o.get("provenance_refs") or [], json.dumps(o)))
                n += 1
            counts["objects"] = n

            n = 0
            for r in corpus["review_events"]:
                cur.execute(
                    """INSERT INTO ke.review_event (id,object_ref,object_version,decision,reviewer_id,
                          reviewed_at,policy_version,payload)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (r["id"], r["object_ref"], r["object_version"], r["decision"],
                     r["reviewer"]["id"], r["reviewed_at"], r["policy_version"], json.dumps(r)))
                n += 1
            counts["review_events"] = n
        counts["ingest_s"] = time.perf_counter() - t0
        return counts

    # ----------------------------------------------------------- retrieval x4
    def q1_claim_status(self, status: str) -> list[dict]:
        """P1: claims by epistemic status (+ the review decision attached to them)."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.statement, c.epistemic_status, c.domain, c.version,
                       COALESCE(json_agg(DISTINCT r.decision) FILTER (WHERE r.id IS NOT NULL), '[]') AS reviews
                FROM ke.claim c
                LEFT JOIN ke.review_event r ON r.object_ref = c.id
                WHERE c.epistemic_status = %s
                GROUP BY c.id, c.statement, c.epistemic_status, c.domain, c.version
                ORDER BY c.id""", (status,))
            return [{"id": r[0], "statement": r[1], "epistemic_status": r[2],
                     "domain": r[3], "version": r[4], "reviews": r[5]} for r in cur.fetchall()]

    def q2_evidence_relations(self, claim_id: str | None = None) -> dict:
        """P2: evidence relation graph (supports/refutes/qualifies/contextualizes)."""
        with self.conn.cursor() as cur:
            if claim_id:
                cur.execute("""SELECT ec.claim_id, ec.relation, e.id, e.citation, e.locator,
                                      e.assessment_status
                               FROM ke.evidence_claim ec JOIN ke.evidence e ON e.id = ec.evidence_id
                               WHERE ec.claim_id = %s ORDER BY ec.relation, e.id""", (claim_id,))
            else:
                cur.execute("""SELECT ec.claim_id, ec.relation, e.id, e.citation, e.locator,
                                      e.assessment_status
                               FROM ke.evidence_claim ec JOIN ke.evidence e ON e.id = ec.evidence_id
                               ORDER BY ec.claim_id, ec.relation""")
            out: dict = {}
            for cid, rel, eid, cit, loc, st in cur.fetchall():
                out.setdefault(cid, {}).setdefault(rel, []).append(
                    {"evidence": eid, "citation": cit, "locator": loc, "assessment": st})
            return out

    def q3_provenance_chain(self, entity_id: str, max_depth: int = 4) -> list[dict]:
        """P3: PROV provenance chain via recursive CTE over derived_from."""
        with self.conn.cursor() as cur:
            cur.execute("""
                WITH RECURSIVE chain(entity_id, prov_id, activity_type, agents, own_derived, depth, path) AS (
                  SELECT p.entity_id, p.id, p.activity_type, p.agents, p.derived_from, 0, ARRAY[p.entity_id]
                  FROM ke.provenance p WHERE p.entity_id = %s
                  UNION ALL
                  SELECT q.entity_id, q.id, q.activity_type, q.agents, q.derived_from, c.depth + 1,
                         c.path || q.entity_id
                  FROM chain c
                  JOIN ke.provenance q ON q.entity_id = ANY(c.own_derived)
                  WHERE c.depth < %s AND NOT (q.entity_id = ANY(c.path))
                )
                SELECT entity_id, prov_id, activity_type, agents, depth, path
                FROM chain ORDER BY depth, entity_id""", (entity_id, max_depth))
            return [{"entity": r[0], "provenance": r[1], "activity_type": r[2],
                     "agents": r[3], "depth": r[4], "path": r[5]} for r in cur.fetchall()]

    def q4_domain(self, domain: str) -> list[dict]:
        """P4: domain-scoped retrieval (claims + objects carrying the domain)."""
        with self.conn.cursor() as cur:
            cur.execute("""SELECT id, statement, epistemic_status FROM ke.claim
                           WHERE domain = %s ORDER BY id""", (domain,))
            claims = [{"id": r[0], "statement": r[1], "status": r[2]} for r in cur.fetchall()]
            cur.execute("""SELECT id, title, evidence_status FROM ke.kobject
                           WHERE %s = ANY(domains) ORDER BY id""", (domain,))
            objs = [{"id": r[0], "title": r[1], "evidence_status": r[2]} for r in cur.fetchall()]
            return {"claims": claims, "objects": objs}

    # ------------------------------------------------------- hybrid retrieval
    def q5_hybrid(self, query: str, k: int = 5, rrf_k: int = 60,
                  domain: str | None = None) -> dict:
        """Lexical (ts_rank) + vector (in-DB cosine) fused with Reciprocal Rank Fusion."""
        qvec = hashed_ngram_vec(query)
        # OR-semantics tsquery so a multi-term query does not collapse to 0 hits
        terms = [t for t in re.findall(r"[A-Za-z0-9]+", query.lower()) if len(t) > 1]
        tsq = " | ".join(terms) if terms else query
        with self.conn.cursor() as cur:
            dom_clause = "AND c.domain = %s" if domain else ""
            params = [tsq] + ([domain] if domain else [])
            cur.execute(f"""
                SELECT c.id, ts_rank(c.fts, to_tsquery('simple', %s)) AS rank
                FROM ke.claim c WHERE c.fts @@ to_tsquery('simple', %s) {dom_clause}
                ORDER BY rank DESC LIMIT 50""", [tsq] + params)
            lex = cur.fetchall()
            cur.execute(f"""
                SELECT c.id, ke.cosine(e.vec, %s::float8[]) AS sim
                FROM ke.claim c JOIN ke.embedding e ON e.claim_id = c.id
                WHERE true {dom_clause} ORDER BY sim DESC LIMIT 50""",
                        [qvec] + ([domain] if domain else []))
            vec = cur.fetchall()
        fused: dict[str, float] = {}
        for rank, (cid, _s) in enumerate(lex):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
        for rank, (cid, _s) in enumerate(vec):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
        ranked = sorted(fused.items(), key=lambda kv: -kv[1])[:k]
        return {"query": query, "domain": domain,
                "lexical_hits": len(lex), "vector_hits": len(vec),
                "fused": [{"claim_id": cid, "rrf": round(score, 6)} for cid, score in ranked]}

    # ---------------------------------------------------------------- export
    def prov_o_export(self, claim_id: str) -> dict:
        """PROV-O JSON-LD projection of one claim's provenance record."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT payload FROM ke.provenance WHERE entity_id = %s", (claim_id,))
            row = cur.fetchone()
        if not row:
            return {"@context": "https://www.w3.org/ns/prov.jsonld", "@graph": []}
        p = row[0]
        graph = [{
            "@id": p["generated_entity"]["id"], "@type": "prov:Entity",
            "prov:wasGeneratedBy": {"@id": p["activity"]["id"]},
            "prov:wasAttributedTo": [{"@id": a["id"]} for a in p.get("agents", [])],
            "prov:wasDerivedFrom": [{"@id": d} for d in p.get("derived_from", [])],
        }, {
            "@id": p["activity"]["id"], "@type": "prov:Activity",
            "prov:startedAtTime": p["activity"].get("started_at"),
            "prov:endedAtTime": p["activity"].get("ended_at"),
            "prov:used": [{"@id": u} for u in p["activity"].get("used_entities", [])],
            "prov:wasAssociatedWith": [{"@id": a["id"]} for a in p.get("agents", [])],
            "tk:activityType": p["activity"].get("activity_type"),
            "tk:software": p["activity"].get("software", []),
        }]
        for a in p.get("agents", []):
            graph.append({"@id": a["id"], "@type": "prov:Agent",
                          "tk:agentType": a.get("agent_type"), "tk:name": a.get("name"),
                          "tk:role": a.get("role")})
        return {"@context": {"prov": "https://www.w3.org/ns/prov#",
                             "tk": "https://tensorknowledge.example/ns#"},
                "@graph": graph}

    def roundtrip(self, schema_dir: str) -> dict:
        """Re-export every stored record from the DB and validate against the schemas."""
        import jsonschema
        from pathlib import Path
        schema_dir = Path(schema_dir)
        pairs = [("ke.claim", "claim-record"), ("ke.evidence", "evidence-record"),
                 ("ke.provenance", "provenance-record"), ("ke.kobject", "knowledge-object"),
                 ("ke.review_event", "review-event")]
        out = {}
        for table, schema_name in pairs:
            schema = json.loads((schema_dir / f"{schema_name}.schema.json").read_text())
            with self.conn.cursor() as cur:
                cur.execute(f"SELECT payload FROM {table}")
                rows = [r[0] for r in cur.fetchall()]
            ok, errs = 0, []
            for rec in rows:
                try:
                    jsonschema.validate(rec, schema)
                    ok += 1
                except jsonschema.ValidationError as exc:
                    errs.append(str(exc)[:200])
            out[schema_name] = {"exported": len(rows), "valid": ok, "errors": errs[:3]}
        return out

    # ------------------------------------------------------------- measuring
    @staticmethod
    def timeit(fn, repeats: int = 5):
        lat = []
        res = None
        for _ in range(repeats):
            t = time.perf_counter()
            res = fn()
            lat.append((time.perf_counter() - t) * 1000)
        return res, {"median_ms": statistics.median(lat), "min_ms": min(lat), "n": repeats}

    def close(self) -> None:
        self.conn.close()