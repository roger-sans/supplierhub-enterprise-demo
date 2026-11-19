-- Run after loading. Investigate any row where violations is greater than zero.
SELECT 'duplicate_dimension_grain' AS rule, COUNT(*) AS violations FROM (
    SELECT supplier_id, as_of FROM DIM_QUALIFIED_SUPPLIER GROUP BY 1, 2 HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'duplicate_fact_grain', COUNT(*) FROM (
    SELECT supplier_id, period FROM FACT_SUPPLIER_MONTH GROUP BY 1, 2 HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'invalid_denominators', COUNT(*) FROM FACT_SUPPLIER_MONTH
WHERE deliveries < 0 OR on_time NOT BETWEEN 0 AND deliveries
   OR inspected < 0 OR accepted NOT BETWEEN 0 AND inspected
   OR checks < 0 OR compliant NOT BETWEEN 0 AND checks
UNION ALL
SELECT 'invalid_reporting_period', COUNT(*) FROM FACT_SUPPLIER_MONTH
WHERE period <> DATE_TRUNC('MONTH', period)
UNION ALL
SELECT 'score_outside_range', COUNT(*) FROM QUALIFIED_SUPPLIER_SCORECARD
WHERE composite NOT BETWEEN 0 AND 100;
