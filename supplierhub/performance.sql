SELECT
    supplier_id,
    SUM(deliveries) AS delivery_base, SUM(on_time) AS on_time_count,
    SUM(inspected) AS quality_base, SUM(accepted) AS accepted_count,
    SUM(checks) AS compliance_base, SUM(compliant) AS compliant_count,
    CASE WHEN SUM(deliveries) >= 20 THEN 100.0 * SUM(on_time) / NULLIF(SUM(deliveries), 0) END AS delivery_pct,
    CASE WHEN SUM(inspected) >= 20 THEN 100.0 * SUM(accepted) / NULLIF(SUM(inspected), 0) END AS quality_pct,
    CASE WHEN SUM(checks) >= 3 THEN 100.0 * SUM(compliant) / NULLIF(SUM(checks), 0) END AS compliance_pct,
    MAX(observed_at) AS last_observed
FROM observations
WHERE period >= ? AND period < ?
GROUP BY supplier_id
