CREATE OR REPLACE VIEW QUALIFIED_SUPPLIER_SCORECARD AS
WITH rolling AS (
    SELECT
        d.as_of, d.supplier_id, d.name, d.category, d.segment, d.risk,
        SUM(f.deliveries) AS delivery_base, SUM(f.on_time) AS on_time_count,
        SUM(f.inspected) AS quality_base, SUM(f.accepted) AS accepted_count,
        SUM(f.checks) AS compliance_base, SUM(f.compliant) AS compliant_count,
        MAX(f.observed_at) AS last_observed
    FROM DIM_QUALIFIED_SUPPLIER d
    LEFT JOIN FACT_SUPPLIER_MONTH f
        ON f.supplier_id = d.supplier_id
        AND f.period >= DATEADD('MONTH', -3, DATE_TRUNC('MONTH', d.as_of))
        AND f.period < DATE_TRUNC('MONTH', d.as_of)
    GROUP BY d.as_of, d.supplier_id, d.name, d.category, d.segment, d.risk
), rates AS (
    SELECT rolling.*,
        CASE WHEN delivery_base >= 20 THEN 100.0 * on_time_count / NULLIF(delivery_base, 0) END AS delivery_pct,
        CASE WHEN quality_base >= 20 THEN 100.0 * accepted_count / NULLIF(quality_base, 0) END AS quality_pct,
        CASE WHEN compliance_base >= 3 THEN 100.0 * compliant_count / NULLIF(compliance_base, 0) END AS compliance_pct
    FROM rolling
)
SELECT
    as_of, supplier_id, name, category, segment, risk,
    delivery_base, quality_base, compliance_base, last_observed,
    ROUND(delivery_pct, 1) AS delivery_rate,
    ROUND(quality_pct, 1) AS quality_rate,
    ROUND(compliance_pct, 1) AS compliance_rate,
    ROUND(0.50 * delivery_pct + 0.30 * quality_pct + 0.20 * compliance_pct, 1) AS composite
FROM rates;
