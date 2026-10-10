-- RIDE360 read-only dashboard role.
-- Run using a PostgreSQL administrator account.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'ride360_dashboard'
    ) THEN
        CREATE ROLE ride360_dashboard LOGIN;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE ride360
TO ride360_dashboard;

GRANT USAGE ON SCHEMA
    ride360_analytics,
    ride360_audit,
    ride360_cache
TO ride360_dashboard;

GRANT SELECT ON ALL TABLES
IN SCHEMA ride360_analytics
TO ride360_dashboard;

GRANT SELECT ON ALL TABLES
IN SCHEMA ride360_audit
TO ride360_dashboard;

GRANT SELECT ON ALL TABLES
IN SCHEMA ride360_cache
TO ride360_dashboard;

ALTER DEFAULT PRIVILEGES
IN SCHEMA ride360_cache
GRANT SELECT ON TABLES
TO ride360_dashboard;