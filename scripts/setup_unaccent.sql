-- =============================================================================
-- Diacritic-insensitive search support for the bilingual reader.
-- =============================================================================
-- Run as the DB owner (e.g. `admin`) — installs the `unaccent` extension and
-- builds functional GIN trigram indexes on the diacritic-stripped, lowercased
-- text columns. After this runs, queries like
--
--     WHERE f_unaccent(text_pali) ILIKE f_unaccent(%(query)s)
--
-- can match "kosambi" against the canonical "kosambī" (and similar — typists
-- without a Pāli keyboard otherwise hit zero results).
--
-- Idempotent: safe to re-run. Indexes only build the first time; subsequent
-- runs are no-ops via IF NOT EXISTS / OR REPLACE.
--
-- Usage:
--   docker exec -i tripitaka-db psql -U admin -d tripitaka_db < scripts/setup_unaccent.sql

-- 1. Extension itself (provides the `unaccent(dict, text)` function)
CREATE EXTENSION IF NOT EXISTS unaccent;

-- 2. Read-only role needs USAGE on the schema to call our wrapper.
GRANT USAGE ON SCHEMA public TO tripitaka_ro;

-- 3. IMMUTABLE wrapper. The bare unaccent() is STABLE (it reads dict files)
--    and Postgres refuses STABLE expressions in indexes. Pinning the dict
--    name + wrapping in a SQL function makes it indexable. Using lower()
--    inside means callers don't have to remember to lowercase too.
CREATE OR REPLACE FUNCTION public.f_unaccent(text)
RETURNS text AS $$
  SELECT unaccent('public.unaccent', lower($1))
$$ LANGUAGE sql IMMUTABLE PARALLEL SAFE;

-- 4. Functional GIN trigram indexes — same shape as the existing raw-text
--    indexes (idx_segment_text_pali_trgm / idx_segment_text_english_trgm),
--    just on the normalized form. Trigram index gives ILIKE substring search
--    speed proportional to result-set size, not table size.
CREATE INDEX IF NOT EXISTS idx_segment_pali_unaccent_trgm
  ON segment USING gin (f_unaccent(text_pali) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_segment_english_unaccent_trgm
  ON segment USING gin (f_unaccent(text_english) gin_trgm_ops);

-- 5. Make sure the runtime read-only role can call the wrapper. (Default
--    EXECUTE on functions goes to PUBLIC, but `setup_readonly_user.sql`
--    revokes ALL ON SCHEMA from PUBLIC before re-granting USAGE to
--    tripitaka_ro — that does not affect function-EXECUTE, but being
--    explicit here means a cold-rebuild can't get into a state where
--    the reader 500s on every query.)
GRANT EXECUTE ON FUNCTION public.f_unaccent(text) TO tripitaka_ro;
