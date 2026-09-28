-- Initial migration. Run from this directory with psql:
-- psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f 001_initial.sql
\ir ../schema.sql
