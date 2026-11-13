-- Independent DB-side cross-check of m15810 rci_asset_registry (board audit m15886)
\pset pager off
\echo == 1. registry row count / distinct ids
SELECT count(*) AS rows, count(DISTINCT report_id) AS ids,
       min(report_id) AS min_id, max(report_id) AS max_id
FROM rci_asset_registry;

\echo == 2. by_type from DB vs shipped summary (info 1149 / research 2981 / analysis 892 / creative 4424)
SELECT asset_type, count(*) FROM rci_asset_registry GROUP BY 1 ORDER BY 1;

\echo == 3. real_exec / clean distributions from DB
SELECT real_exec_flag, count(*) FROM rci_asset_registry GROUP BY 1 ORDER BY 1;
SELECT clean_decision, count(*) FROM rci_asset_registry GROUP BY 1 ORDER BY 1;

\echo == 4. every registry row must be published and created_at <= pin (expect 0 / 0)
SELECT
  (SELECT count(*) FROM rci_asset_registry r LEFT JOIN tensor_reports t ON t.id=r.report_id WHERE t.id IS NULL) AS not_in_reports,
  (SELECT count(*) FROM rci_asset_registry r JOIN tensor_reports t ON t.id=r.report_id
     WHERE t.status <> 'published') AS not_published,
  (SELECT count(*) FROM rci_asset_registry r JOIN tensor_reports t ON t.id=r.report_id
     WHERE t.created_at > TIMESTAMPTZ '2026-11-11 20:00:31.841339+00') AS after_pin;

\echo == 5. coverage: published<=pin not present in registry (expect 0)
SELECT count(*) AS missing_from_registry
FROM tensor_reports t
LEFT JOIN rci_asset_registry r ON r.report_id=t.id
WHERE t.status='published'
  AND t.created_at <= TIMESTAMPTZ '2026-11-11 20:00:31.841339+00'
  AND r.report_id IS NULL;

\echo == 6. mission chain: dangling mission_ids (report §4 A5 claims 10)
SELECT count(*) AS dangling_rows, count(DISTINCT r.mission_id) AS dangling_missions
FROM rci_asset_registry r
LEFT JOIN tensor_dev_missions m ON m.id=r.mission_id
WHERE r.mission_id IS NOT NULL AND m.id IS NULL;

\echo == 7. declared FK to tensor_reports? (report claims FK; expect 0 constraints)
SELECT count(*) AS fk_constraints
FROM information_schema.table_constraints
WHERE table_name='rci_asset_registry' AND constraint_type='FOREIGN KEY';

\echo == 8. duplicate/excess recomputed in SQL (expect 763 / 2174 / 1411)
SELECT count(*) AS clusters, sum(n) AS reports_in_clusters, sum(n)-count(*) AS excess
FROM (SELECT dup_cluster_id, count(*) n FROM rci_asset_registry
      WHERE dup_cluster_id IS NOT NULL GROUP BY 1) s;

\echo == 9. snapshot id uniformity
SELECT snapshot_id, count(*) FROM rci_asset_registry GROUP BY 1;

\echo == 10. report row six-section check
SELECT id, mission_id, length(markdown) AS md_len,
       (markdown LIKE '%① 问题设定%') AS s1, (markdown LIKE '%② 方法与实现%') AS s2,
       (markdown LIKE '%③ 参数表%') AS s3, (markdown LIKE '%④ 对照表%') AS s4,
       (markdown LIKE '%⑤ 敏感性%') AS s5, (markdown LIKE '%⑥ 失败模式%') AS s6
FROM tensor_reports WHERE mission_id=15810 ORDER BY id DESC LIMIT 3;