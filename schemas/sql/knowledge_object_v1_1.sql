-- Knowledge Object Schema v1.1 —— L3 验证单「作用域绑定」硬化迁移
-- 锚点: KBM-RCI-S2-SCHEMA（第 2 轮）| 配套: schemas/sql/knowledge_object_v1.sql
-- 依据: docs/rci/methods-survey-v2.md §3（VC credentialSubject / in-toto subject digest /
--       SLSA provenance subject 三处成熟做法）+ docs/rci/l3-gate-scope-audit.md（现网缺陷实测）
--
-- 为什么要有这次迁移（实测缺陷，不是推测）:
--   v1 的 L3 通道只校验「该对象名下存在一张 gate_state='confirmed' 且 gate_level>=2 的票」。
--   票本身没有任何约束把它绑定到**这张对象的内容**或**平台真实裁定的范围**：
--   `verdict_by` 是自由文本、`maturity_verdict_id` 无外键、票的写入者无人核验。
--   现网 ko_v1 库内 6 条 L3 对象全部引用同一张 maturity_verdict_id=286、同一 verdict_at，
--   即「一张任务级 maturity 裁定」被复用去背书 6 条它从未审阅过的断言。
--
-- v1.1 增加三条约束（都写进数据库，不写进倡议书）:
--   G1 主体摘要绑定: confirmed 票必须带 subject_sha256（= 被裁定对象的 content_sha256）。
--   G2 作用域: source='maturity_gate' 的票必须带 maturity_verdict_id + mission_id；
--      晋级时要么摘要相等（对象级裁定），要么 mission_id 相同**且**票显式枚举该
--      knowledge_id（evidence_ref.knowledge_ids，任务级裁定只覆盖被点名的对象）。
--   G3 降级对价: platform_verified -> report_claimed 必须持该对象的 reopened 票。
--
-- 兼容性: 既有 6 条 L3 行保持原状（历史票 subject_sha256 IS NULL），但会出现在视图
--   ko_l3_unbound 中，标记 needs_reverification；平台侧重新出票（带 subject_sha256）即消除。
--
-- 应用: psql "$KO_DSN" -v ON_ERROR_STOP=1 -f schemas/sql/knowledge_object_v1_1.sql
-- 幂等: 可重复执行（IF NOT EXISTS / CREATE OR REPLACE / NOT VALID 约束）。

BEGIN;

-- ------------------------------------------------------------------ 列
ALTER TABLE ko_verification ADD COLUMN IF NOT EXISTS subject_sha256 CHAR(64);
ALTER TABLE ko_verification ADD COLUMN IF NOT EXISTS subject_scope  TEXT;

COMMENT ON COLUMN ko_verification.subject_sha256 IS
    '被裁定对象内容摘要（= ko_object.content_sha256）；confirmed 票必填（v1.1 G1）';
COMMENT ON COLUMN ko_verification.subject_scope IS
    'ticket 作用域：object（单对象裁定）| mission（任务级裁定，须在 evidence_ref.knowledge_ids 枚举）';

-- ------------------------------------------------------------- 约束（G1/G2）
-- NOT VALID: 不对历史行做校验（历史票保持原样并在 ko_l3_unbound 中暴露），
-- 但新写入/更新必须满足 —— 这正是「不回填即不能新增」的硬化语义。
DO $$
BEGIN
    BEGIN
        ALTER TABLE ko_verification
            ADD CONSTRAINT ko_ver_confirmed_binds_subject
            CHECK (gate_state <> 'confirmed' OR subject_sha256 ~ '^[0-9a-f]{64}$') NOT VALID;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
    BEGIN
        ALTER TABLE ko_verification
            ADD CONSTRAINT ko_ver_maturity_scope
            CHECK (source <> 'maturity_gate'
                   OR (maturity_verdict_id IS NOT NULL AND mission_id IS NOT NULL)) NOT VALID;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
    BEGIN
        ALTER TABLE ko_verification
            ADD CONSTRAINT ko_ver_subject_scope_vocab
            CHECK (subject_scope IS NULL OR subject_scope IN ('object', 'mission')) NOT VALID;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
END $$;

CREATE INDEX IF NOT EXISTS ko_verification_sha_idx ON ko_verification (subject_sha256);

-- ------------------------------------------------------- 晋级/降级守卫（G1/G2/G3）
CREATE OR REPLACE FUNCTION ko_object_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    t_ticket   ko_verification;
    traceable_n INTEGER;
    v_ok       BOOLEAN := FALSE;
    v_digest_ok BOOLEAN := FALSE;
    v_mission_ok BOOLEAN := FALSE;
    v_enumerated BOOLEAN := FALSE;
    v_obj_mission BIGINT;
    v_reopen RECORD;
BEGIN
    IF TG_OP = 'UPDATE' THEN
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

        -- G1 主体摘要绑定
        v_digest_ok := (t_ticket.subject_sha256 IS NOT NULL
                        AND t_ticket.subject_sha256 = NEW.content_sha256);

        -- G2 作用域：mission 级裁定必须显式枚举本对象
        v_obj_mission := NULLIF(NEW.provenance->>'mission_id', '')::BIGINT;
        v_mission_ok := (t_ticket.mission_id IS NOT NULL
                         AND v_obj_mission IS NOT NULL
                         AND t_ticket.mission_id = v_obj_mission);
        v_enumerated := COALESCE(
            (t_ticket.evidence_ref->'knowledge_ids') ? NEW.knowledge_id, FALSE);
        IF NOT v_enumerated AND NEW.knowledge_id = ANY (
                ARRAY(SELECT jsonb_array_elements_text(
                        COALESCE(t_ticket.evidence_ref->'knowledge_ids', '[]'::jsonb)))) THEN
            v_enumerated := TRUE;
        END IF;

        IF NOT (v_digest_ok OR (v_mission_ok AND v_enumerated)) THEN
            RAISE EXCEPTION
                'L3 promotion for % rejected by ticket %: subject unbound (ticket.subject_sha256=%, object.content_sha256=%, mission_match=%, enumerated=%)',
                NEW.knowledge_id, t_ticket.ticket_id,
                COALESCE(t_ticket.subject_sha256,'NULL'), NEW.content_sha256,
                v_mission_ok, v_enumerated;
        END IF;

        -- 证据必须至少一条三闸全绿（v1 原有要求，保留）
        SELECT count(*) INTO traceable_n FROM ko_evidence e
         WHERE e.knowledge_id = NEW.knowledge_id
           AND ko_evidence_is_traceable(e.report_resolved, e.section_resolved,
                                        e.artifact_resolved, e.artifact_kind);
        IF traceable_n = 0 THEN
            RAISE EXCEPTION 'L3 promotion for % requires >=1 fully traceable evidence row', NEW.knowledge_id;
        END IF;
    END IF;

    -- G3 降级对价：reopen 必须持该对象的 reopened 票
    IF TG_OP = 'UPDATE' AND OLD.verification_status = 'platform_verified'
       AND NEW.verification_status = 'report_claimed' THEN
        SELECT * INTO v_reopen FROM ko_verification v
         WHERE v.knowledge_id = NEW.knowledge_id AND v.gate_state = 'reopened'
         ORDER BY v.verdict_at DESC LIMIT 1;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'demotion of % requires a reopened platform ticket for this object',
                NEW.knowledge_id;
        END IF;
    END IF;

    NEW.updated_at := now();
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS ko_object_guard_trg ON ko_object;
CREATE TRIGGER ko_object_guard_trg BEFORE INSERT OR UPDATE ON ko_object
    FOR EACH ROW EXECUTE FUNCTION ko_object_guard();

-- ------------------------------------------------------------ 对账视图
DROP VIEW IF EXISTS ko_l3_unbound;
CREATE VIEW ko_l3_unbound AS
SELECT o.knowledge_id,
       o.verification_status,
       o.storage_level,
       v.ticket_id,
       v.source,
       v.maturity_verdict_id,
       v.mission_id              AS ticket_mission_id,
       NULLIF(o.provenance->>'mission_id','')::BIGINT AS object_mission_id,
       v.subject_sha256,
       o.content_sha256,
       CASE
         WHEN v.ticket_id IS NULL THEN 'no_confirmed_ticket'
         WHEN v.subject_sha256 IS NULL THEN 'legacy_ticket_without_subject_digest'
         WHEN v.subject_sha256 <> o.content_sha256 THEN 'subject_digest_mismatch'
         ELSE 'bound'
       END AS binding,
       'needs_reverification'    AS next_action
  FROM ko_object o
  LEFT JOIN LATERAL (
      SELECT * FROM ko_verification v
       WHERE v.knowledge_id = o.knowledge_id
         AND v.gate_state = 'confirmed' AND v.gate_level >= 2
       ORDER BY v.verdict_at DESC LIMIT 1
  ) v ON TRUE
 WHERE o.verification_status = 'platform_verified'
   AND (v.ticket_id IS NULL
        OR v.subject_sha256 IS NULL
        OR v.subject_sha256 <> o.content_sha256);

COMMENT ON VIEW ko_l3_unbound IS
    'L3 但凭据未绑定对象内容（历史票）——下一动作=平台按 ko_object.content_sha256 重出票；不自动降级';

COMMIT;