-- Knowledge Object Schema v1 — DDL (PostgreSQL 14+)
-- 锚点: KBM-RCI-S2-SCHEMA | 配套: schemas/knowledge-object-v1.schema.json, docs/rci/schema-v1.md
--
-- 纪律（写进约束，不靠自觉）:
--   1. verification_status 三态状态机: unverified -> report_claimed -> platform_verified
--      （reopen 时 platform_verified -> report_claimed）。越级跳转由触发器拒绝。
--   2. L3（=platform_verified）唯一通道 = ko_verification 里 gate_state='confirmed' 且
--      gate_level>=2 的平台验证单（maturity/benchmark/xval/repro gate）。Agent 侧写入被拒。
--   3. L3 晋级还要求该对象至少一条“三闸全绿”证据（report_resolved+section_resolved+
--      artifact_resolved），即证据可追溯率对单对象必须触达 1.0。
--   4. 已 L3 的对象的 claim/doc 不可原地改写（防漂移）；纠正 = 新版本对象 + supersedes 边。
--   5. ko_evidence / ko_verification / ko_state_event 追加不覆盖（L0/L1 只增）。
--   6. L0 原件（原始数据、场文件）不在本库：归 TensorData data_artifacts（内容寻址 sha256），
--      本库只存引用。故本 DDL 无二进制列。
--
-- 应用: psql "$KO_DSN" -v ON_ERROR_STOP=1 -f schemas/sql/knowledge_object_v1.sql

BEGIN;

-- ---------------------------------------------------------------- ko_object
CREATE TABLE IF NOT EXISTS ko_object (
    knowledge_id        TEXT PRIMARY KEY
        CHECK (knowledge_id ~ '^ko:[a-z0-9][a-z0-9._-]*:[a-z0-9][a-z0-9._-]*$'),
    schema_version      TEXT NOT NULL DEFAULT 'ko/v1' CHECK (schema_version = 'ko/v1'),
    version             INTEGER NOT NULL CHECK (version >= 1),
    type                TEXT NOT NULL CHECK (type IN (
                            'method_card','parameter_card','failure_card',
                            'benchmark_card','code_pointer_card',
                            'capability_claim','negative_result','measurement',
                            'definition','procedure','reference')),
    domain              TEXT NOT NULL CHECK (length(btrim(domain)) > 0),
    subject             TEXT NOT NULL CHECK (length(btrim(subject)) > 0),
    claim               TEXT NOT NULL CHECK (length(btrim(claim)) > 0),
    conditions          JSONB NOT NULL CHECK (conditions ? 'description'),
    confidence          JSONB NOT NULL CHECK (confidence ? 'level'),
    verification_status TEXT NOT NULL DEFAULT 'unverified'
        CHECK (verification_status IN ('unverified','report_claimed','platform_verified')),
    storage_level       TEXT NOT NULL DEFAULT 'L1' CHECK (storage_level IN ('L1','L2','L3')),
    limitations         JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(limitations) = 'array'),
    relations           JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(relations) = 'array'),
    next_actions        JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(next_actions) = 'array'),
    provenance          JSONB NOT NULL CHECK (provenance ? 'producer' AND provenance ? 'created_at'),
    payload             JSONB,
    doc                 JSONB NOT NULL,
    content_sha256      CHAR(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    producer            TEXT NOT NULL CHECK (length(btrim(producer)) > 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ko_l3_iff_verified CHECK ((verification_status = 'platform_verified') = (storage_level = 'L3')),
    CONSTRAINT ko_l2_needs_relations CHECK (storage_level <> 'L2' OR jsonb_array_length(relations) > 0)
);

CREATE INDEX IF NOT EXISTS ko_object_type_idx      ON ko_object (type);
CREATE INDEX IF NOT EXISTS ko_object_domain_idx    ON ko_object (domain);
CREATE INDEX IF NOT EXISTS ko_object_status_idx    ON ko_object (verification_status);
CREATE INDEX IF NOT EXISTS ko_object_level_idx     ON ko_object (storage_level);
CREATE UNIQUE INDEX IF NOT EXISTS ko_object_claim_uniq
    ON ko_object (domain, subject, md5(claim));  -- 同域同主体同断言=同一对象（防手抄多份）

-- -------------------------------------------------------------- ko_evidence
CREATE TABLE IF NOT EXISTS ko_evidence (
    evidence_id      TEXT PRIMARY KEY CHECK (evidence_id ~ '^ev:[0-9a-f]{16}$'),
    knowledge_id     TEXT NOT NULL REFERENCES ko_object(knowledge_id) ON DELETE RESTRICT,
    ordinal          INTEGER NOT NULL CHECK (ordinal >= 0),
    report_id        BIGINT NOT NULL CHECK (report_id > 0),      -- TensorPlatform tensor_reports.id
    report_kind      TEXT NOT NULL DEFAULT 'tensor_report'
        CHECK (report_kind IN ('tensor_report','external')),
    section_heading  TEXT NOT NULL CHECK (length(btrim(section_heading)) > 0),
    section_anchor   TEXT NOT NULL CHECK (section_anchor ~ '^[a-z0-9\u4e00-\u9fff][a-z0-9\u4e00-\u9fff-]*$'),
    section_start    INTEGER CHECK (section_start >= 0),
    section_end      INTEGER,
    section_sha256   CHAR(64) CHECK (section_sha256 IS NULL OR section_sha256 ~ '^[0-9a-f]{64}$'),
    excerpt          TEXT,
    evidence_type    TEXT NOT NULL CHECK (evidence_type IN (
                        'measurement','simulation','analytic','literature',
                        'code','test','dataset','documentation')),
    relation         TEXT NOT NULL DEFAULT 'supports'
        CHECK (relation IN ('supports','refutes','quantifies','limits','reproduces')),
    artifact_kind    TEXT NOT NULL CHECK (artifact_kind IN (
                        'tensor_data_artifact','repo_path','report_figure',
                        'report_section','url','none')),
    artifact_ref     TEXT NOT NULL CHECK (length(btrim(artifact_ref)) > 0),
    artifact_sha256  CHAR(64) CHECK (artifact_sha256 IS NULL OR artifact_sha256 ~ '^[0-9a-f]{64}$'),
    report_resolved  BOOLEAN NOT NULL DEFAULT FALSE,
    section_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    artifact_resolved BOOLEAN,
    resolver_version TEXT,
    resolved_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ko_ev_span CHECK (section_start IS NULL OR section_end IS NULL OR section_end > section_start),
    CONSTRAINT ko_ev_artifact_addr CHECK (artifact_kind <> 'tensor_data_artifact' OR artifact_sha256 IS NOT NULL),
    CONSTRAINT ko_ev_none_shape CHECK (artifact_kind <> 'none'
        OR evidence_type = 'documentation'),  -- 'none' 只用于纯文档证据
    UNIQUE (knowledge_id, ordinal)
);

CREATE INDEX IF NOT EXISTS ko_evidence_report_idx ON ko_evidence (report_id);

-- -------------------------------------------------------------- ko_relation
CREATE TABLE IF NOT EXISTS ko_relation (
    src_id     TEXT NOT NULL REFERENCES ko_object(knowledge_id) ON DELETE CASCADE,
    dst_id     TEXT NOT NULL CHECK (length(btrim(dst_id)) > 0),
    relation   TEXT NOT NULL CHECK (relation IN (
                  'supports','refines','contradicts','supersedes','depends_on',
                  'derived_from','instance_of','measured_by','fails_on','replicated_by')),
    note       TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (src_id, dst_id, relation),
    CONSTRAINT ko_rel_no_self CHECK (src_id <> dst_id)
);
CREATE INDEX IF NOT EXISTS ko_relation_dst_idx ON ko_relation (dst_id);

-- ---------------------------------------------------------- ko_verification
-- 平台验证单（只由平台侧/裁决席写入；TK 只读消费）。这是 L3 的唯一合法凭据。
CREATE TABLE IF NOT EXISTS ko_verification (
    ticket_id           TEXT PRIMARY KEY CHECK (length(btrim(ticket_id)) > 0),
    knowledge_id        TEXT NOT NULL REFERENCES ko_object(knowledge_id) ON DELETE RESTRICT,
    source              TEXT NOT NULL CHECK (source IN
                            ('maturity_gate','benchmark_gate','xval_gate','repro_gate')),
    gate_state          TEXT NOT NULL CHECK (gate_state IN ('confirmed','reopened')),
    gate_level          INTEGER NOT NULL CHECK (gate_level BETWEEN 0 AND 4),
    verdict_by          TEXT NOT NULL CHECK (length(btrim(verdict_by)) > 0),
    verdict_at          TIMESTAMPTZ NOT NULL,
    maturity_verdict_id BIGINT,                       -- TensorPlatform tensor_maturity_verdicts.id
    mission_id          BIGINT,
    evidence_ref        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- confirmed 才可能是 L3 凭据；confirmed 的 gate_level 必须 >=2（L0/L1 级不算验证）
    CONSTRAINT ko_ver_confirmed_shape CHECK (gate_state <> 'confirmed' OR gate_level >= 2)
);
CREATE INDEX IF NOT EXISTS ko_verification_ko_idx ON ko_verification (knowledge_id);

-- ---------------------------------------------------------- ko_state_event
CREATE TABLE IF NOT EXISTS ko_state_event (
    event_id     BIGSERIAL PRIMARY KEY,
    knowledge_id TEXT NOT NULL REFERENCES ko_object(knowledge_id) ON DELETE RESTRICT,
    from_status  TEXT CHECK (from_status IS NULL OR from_status IN
                     ('unverified','report_claimed','platform_verified')),
    to_status    TEXT NOT NULL CHECK (to_status IN
                     ('unverified','report_claimed','platform_verified')),
    actor        TEXT NOT NULL,
    actor_role   TEXT NOT NULL CHECK (actor_role IN ('agent','human','platform')),
    ticket_id    TEXT REFERENCES ko_verification(ticket_id),
    reason       TEXT,
    at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- owner 铁则：L3 只能由平台角色凭票据写入
    CONSTRAINT ko_state_l3_channel CHECK (to_status <> 'platform_verified'
        OR (actor_role = 'platform' AND ticket_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ko_state_event_ko_idx ON ko_state_event (knowledge_id, at);

-- ------------------------------------------------------- guards & triggers
-- 全绿证据：三闸全绿的证据行（artifact_kind='none' 视为不设址，按锚点/正文核验）
CREATE OR REPLACE FUNCTION ko_evidence_is_traceable(
    p_report BOOLEAN, p_section BOOLEAN, p_artifact BOOLEAN, p_kind TEXT)
RETURNS BOOLEAN LANGUAGE sql IMMUTABLE AS $$
    SELECT p_report AND p_section AND COALESCE(p_artifact, p_kind = 'none');
$$;

CREATE OR REPLACE FUNCTION ko_object_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    t_ticket ko_verification;
    traceable_n INTEGER;
    v_ok BOOLEAN := FALSE;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- 状态机合法边
        -- 合法边以数据表表达（与 docs/rci/schema-v1.md §1 的状态机表逐行对应）
        SELECT EXISTS (
            SELECT 1 FROM (VALUES
                ('unverified','report_claimed'),
                ('report_claimed','platform_verified'),
                ('platform_verified','report_claimed')
            ) AS t(f, s)
            WHERE t.f = OLD.verification_status AND t.s = NEW.verification_status
        ) INTO v_ok;
        IF NEW.verification_status <> OLD.verification_status AND NOT COALESCE(v_ok, FALSE) THEN
            RAISE EXCEPTION 'illegal verification transition %.% -> %.% for %',
                OLD.verification_status, OLD.storage_level,
                NEW.verification_status, NEW.storage_level, NEW.knowledge_id;
        END IF;
        -- 已 L3 对象不可原地改写断言/正文（防“验证后改内容”漂移）
        IF OLD.storage_level = 'L3' AND (NEW.claim IS DISTINCT FROM OLD.claim
                                         OR NEW.doc IS DISTINCT FROM OLD.doc) THEN
            RAISE EXCEPTION 'L3 object % is immutable: publish a new version + supersedes edge',
                OLD.knowledge_id;
        END IF;
        IF NEW.verification_status = 'report_claimed' AND OLD.verification_status = 'unverified' THEN
            IF NOT EXISTS (SELECT 1 FROM ko_evidence e WHERE e.knowledge_id = NEW.knowledge_id) THEN
                RAISE EXCEPTION 'report_claimed requires >=1 evidence row (report_id+section) for %',
                    NEW.knowledge_id;
            END IF;
        END IF;
    END IF;

    IF NEW.verification_status = 'platform_verified' THEN
        SELECT * INTO t_ticket FROM ko_verification v
         WHERE v.knowledge_id = NEW.knowledge_id
           AND v.gate_state = 'confirmed' AND v.gate_level >= 2
         ORDER BY v.verdict_at DESC LIMIT 1;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'L3 promotion for % requires a confirmed platform ticket (gate_level>=2); agents cannot self-declare',
                NEW.knowledge_id;
        END IF;
        -- 且必须已有三闸全绿证据（单对象证据可追溯率=1.0）
        SELECT count(*) INTO traceable_n FROM ko_evidence e
         WHERE e.knowledge_id = NEW.knowledge_id
           AND ko_evidence_is_traceable(e.report_resolved, e.section_resolved,
                                        e.artifact_resolved, e.artifact_kind);
        IF traceable_n = 0 THEN
            RAISE EXCEPTION 'L3 promotion for % requires >=1 fully traceable evidence row', NEW.knowledge_id;
        END IF;
    END IF;

    NEW.updated_at := now();
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS ko_object_guard_trg ON ko_object;
CREATE TRIGGER ko_object_guard_trg BEFORE INSERT OR UPDATE ON ko_object
    FOR EACH ROW EXECUTE FUNCTION ko_object_guard();

-- 自动状态审计：任何状态变更自动落 ko_state_event（含平台晋级）
CREATE OR REPLACE FUNCTION ko_object_audit() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    t_ticket TEXT;
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.verification_status = OLD.verification_status THEN
        RETURN NULL;
    END IF;
    IF NEW.verification_status = 'platform_verified' THEN
        SELECT v.ticket_id INTO t_ticket FROM ko_verification v
         WHERE v.knowledge_id = NEW.knowledge_id AND v.gate_state = 'confirmed' AND v.gate_level >= 2
         ORDER BY v.verdict_at DESC LIMIT 1;
    END IF;
    INSERT INTO ko_state_event (knowledge_id, from_status, to_status, actor, actor_role, ticket_id)
    VALUES (NEW.knowledge_id,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.verification_status END,
            NEW.verification_status,
            COALESCE(NEW.provenance ->> 'producer', 'unknown'),
            CASE WHEN NEW.verification_status = 'platform_verified' THEN 'platform' ELSE 'agent' END,
            t_ticket);
    RETURN NULL;
END $$;

DROP TRIGGER IF EXISTS ko_object_audit_trg ON ko_object;
CREATE TRIGGER ko_object_audit_trg AFTER INSERT OR UPDATE ON ko_object
    FOR EACH ROW EXECUTE FUNCTION ko_object_audit();

-- ko_evidence 追加不覆盖：只允许解析三闸/解析器版本这五个列被更新
CREATE OR REPLACE FUNCTION ko_evidence_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'ko_evidence is append-only (delete refused for %)', OLD.evidence_id;
    END IF;
    IF NEW.evidence_id <> OLD.evidence_id OR NEW.knowledge_id <> OLD.knowledge_id
       OR NEW.report_id <> OLD.report_id OR NEW.section_heading <> OLD.section_heading
       OR NEW.section_anchor <> OLD.section_anchor OR NEW.artifact_kind <> OLD.artifact_kind
       OR NEW.artifact_ref <> OLD.artifact_ref OR NEW.evidence_type <> OLD.evidence_type THEN
        RAISE EXCEPTION 'ko_evidence identity columns are immutable; add a new row instead';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS ko_evidence_guard_trg ON ko_evidence;
CREATE TRIGGER ko_evidence_guard_trg BEFORE UPDATE OR DELETE ON ko_evidence
    FOR EACH ROW EXECUTE FUNCTION ko_evidence_guard();

-- ko_verification / ko_state_event 只增不改
CREATE OR REPLACE FUNCTION ko_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END $$;

DROP TRIGGER IF EXISTS ko_verification_append_only_trg ON ko_verification;
CREATE TRIGGER ko_verification_append_only_trg BEFORE UPDATE OR DELETE ON ko_verification
    FOR EACH ROW EXECUTE FUNCTION ko_append_only();

DROP TRIGGER IF EXISTS ko_state_event_append_only_trg ON ko_state_event;
CREATE TRIGGER ko_state_event_append_only_trg BEFORE UPDATE OR DELETE ON ko_state_event
    FOR EACH ROW EXECUTE FUNCTION ko_append_only();

-- ------------------------------------------------------------- 可追溯率视图
-- 口径（docs/rci/schema-v1.md §3）：单条证据可追溯 = 报告闸 ∧ 小节闸 ∧ 工件闸；
-- artifact_kind='none' 视为不设址（该闸以“锚点+正文哈希”代替地址）。
CREATE OR REPLACE VIEW ko_evidence_traceability AS
SELECT knowledge_id,
       count(*) AS evidence_total,
       count(*) FILTER (WHERE report_resolved)  AS report_resolved_n,
       count(*) FILTER (WHERE section_resolved) AS section_resolved_n,
       count(*) FILTER (WHERE ko_evidence_is_traceable(report_resolved, section_resolved,
                                                       artifact_resolved, artifact_kind)) AS traceable_n,
       round(count(*) FILTER (WHERE ko_evidence_is_traceable(report_resolved, section_resolved,
                                                             artifact_resolved, artifact_kind))::numeric
             / NULLIF(count(*), 0), 4) AS e_tr
FROM ko_evidence
GROUP BY knowledge_id;

CREATE OR REPLACE VIEW ko_evidence_traceability_global AS
WITH e AS (
    SELECT count(*) AS total,
           count(*) FILTER (WHERE report_resolved)  AS report_n,
           count(*) FILTER (WHERE section_resolved) AS section_n,
           count(*) FILTER (WHERE ko_evidence_is_traceable(report_resolved, section_resolved,
                                                           artifact_resolved, artifact_kind)) AS traceable_n
    FROM ko_evidence
)
SELECT total AS evidence_total,
       round(report_n::numeric  / NULLIF(total, 0), 4) AS r1_report_resolvable,
       round(section_n::numeric / NULLIF(total, 0), 4) AS r2_section_resolvable,
       round(traceable_n::numeric / NULLIF(total, 0), 4) AS e_tr_full,
       report_n AS report_resolved_n,
       section_n AS section_resolved_n,
       traceable_n AS fully_traceable_n
FROM e;

-- L3 审计：任何 L3 行必须有 confirmed 票据（触发器已保证，视图用于对账/巡检）
CREATE OR REPLACE VIEW ko_l3_audit AS
SELECT o.knowledge_id, o.version, o.type, o.domain, o.verification_status, o.storage_level,
       v.ticket_id, v.source, v.gate_state, v.gate_level, v.verdict_by, v.verdict_at,
       (v.ticket_id IS NULL) AS missing_ticket
FROM ko_object o
LEFT JOIN LATERAL (
    SELECT * FROM ko_verification v2
     WHERE v2.knowledge_id = o.knowledge_id AND v2.gate_state = 'confirmed' AND v2.gate_level >= 2
     ORDER BY v2.verdict_at DESC LIMIT 1
) v ON TRUE
WHERE o.storage_level = 'L3';

CREATE OR REPLACE VIEW ko_state_distribution AS
SELECT type, verification_status, storage_level, count(*) AS n
FROM ko_object GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

COMMIT;