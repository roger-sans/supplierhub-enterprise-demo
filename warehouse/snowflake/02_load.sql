-- Full-refresh sandbox load using session-local landing tables and an atomic replace.
USE SCHEMA SUPPLIERHUB_DEMO;
CREATE OR REPLACE TEMPORARY TABLE LANDING_SUPPLIER LIKE DIM_QUALIFIED_SUPPLIER;
CREATE OR REPLACE TEMPORARY TABLE LANDING_MONTH LIKE FACT_SUPPLIER_MONTH;

COPY INTO LANDING_SUPPLIER
FROM @SUPPLIERHUB_STAGE
FILES = ('qualified_suppliers.csv.gz')
FILE_FORMAT = (FORMAT_NAME = 'SUPPLIERHUB_CSV')
ON_ERROR = ABORT_STATEMENT
FORCE = TRUE;

COPY INTO LANDING_MONTH
FROM @SUPPLIERHUB_STAGE
FILES = ('supplier_monthly_observations.csv.gz')
FILE_FORMAT = (FORMAT_NAME = 'SUPPLIERHUB_CSV')
ON_ERROR = ABORT_STATEMENT
FORCE = TRUE;

-- Snowflake standard-table key constraints are informational. Keep the last
-- published snapshot if the staging files fail grain or source-count checks.
EXECUTE IMMEDIATE $$
DECLARE
    invalid_snapshot EXCEPTION (-20001, 'Invalid SupplierHub snapshot grain or count bounds.');
    bad_rows NUMBER;
BEGIN
    SELECT
        (SELECT COUNT(*) FROM (
            SELECT supplier_id, as_of FROM LANDING_SUPPLIER GROUP BY 1, 2 HAVING COUNT(*) > 1
        )) +
        (SELECT IFF(COUNT(DISTINCT as_of) = 1, 0, 1) FROM LANDING_SUPPLIER) +
        (SELECT COUNT(*) FROM (
            SELECT supplier_id, period FROM LANDING_MONTH GROUP BY 1, 2 HAVING COUNT(*) > 1
        )) +
        (SELECT COUNT(*) FROM LANDING_MONTH
          WHERE period <> DATE_TRUNC('MONTH', period) OR
                deliveries < 0 OR on_time NOT BETWEEN 0 AND deliveries OR
                inspected < 0 OR accepted NOT BETWEEN 0 AND inspected OR
                checks < 0 OR compliant NOT BETWEEN 0 AND checks)
    INTO :bad_rows;
    IF (bad_rows > 0) THEN
        RAISE invalid_snapshot;
    END IF;

    BEGIN TRANSACTION;
    DELETE FROM DIM_QUALIFIED_SUPPLIER;
    INSERT INTO DIM_QUALIFIED_SUPPLIER SELECT * FROM LANDING_SUPPLIER;
    DELETE FROM FACT_SUPPLIER_MONTH;
    INSERT INTO FACT_SUPPLIER_MONTH SELECT * FROM LANDING_MONTH;
    COMMIT;
EXCEPTION
    WHEN invalid_snapshot THEN
        RAISE;
    WHEN OTHER THEN
        ROLLBACK;
        RAISE;
END;
$$;
