BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE app_users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id bigint NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    delete_requested_at timestamptz
);

CREATE TABLE documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    original_filename varchar(255) NOT NULL,
    sha256 char(64) NOT NULL,
    parser_version varchar(32) NOT NULL,
    page_count integer NOT NULL CHECK (page_count BETWEEN 1 AND 40),
    estimated_tokens integer NOT NULL CHECK (estimated_tokens BETWEEN 1 AND 60000),
    status varchar(32) NOT NULL CHECK (status IN ('accepted', 'rejected', 'processed')),
    extracted_text text,
    page_map jsonb,
    text_expires_at timestamptz NOT NULL DEFAULT (now() + interval '24 hours'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, sha256)
);

CREATE TABLE card_sets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    title varchar(200) NOT NULL,
    model varchar(80) NOT NULL,
    prompt_version varchar(32) NOT NULL,
    schema_version varchar(16) NOT NULL,
    fallback_used boolean NOT NULL DEFAULT false,
    input_tokens integer NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
    output_tokens integer NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
    estimated_cost_usd numeric(12,6) NOT NULL DEFAULT 0 CHECK (estimated_cost_usd >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, prompt_version, schema_version)
);

CREATE TABLE cards (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    card_set_id uuid NOT NULL REFERENCES card_sets(id) ON DELETE CASCADE,
    position smallint NOT NULL CHECK (position BETWEEN 1 AND 10),
    question varchar(500) NOT NULL,
    reference_answer varchar(1200) NOT NULL,
    source_page integer NOT NULL CHECK (source_page >= 1),
    source_quote varchar(500) NOT NULL,
    difficulty varchar(16) NOT NULL CHECK (difficulty IN ('basic', 'intermediate', 'advanced')),
    tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    UNIQUE (card_set_id, position)
);

CREATE TABLE study_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    card_set_id uuid NOT NULL REFERENCES card_sets(id) ON DELETE CASCADE,
    status varchar(16) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'expired')),
    current_position smallint NOT NULL DEFAULT 1 CHECK (current_position BETWEEN 1 AND 10),
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '30 days')
);

CREATE TABLE answer_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES study_sessions(id) ON DELETE CASCADE,
    card_id uuid NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    student_answer varchar(2000),
    verdict varchar(24) NOT NULL CHECK (verdict IN ('correct', 'partially_correct', 'incorrect', 'skipped')),
    score smallint CHECK (score BETWEEN 0 AND 2),
    feedback varchar(600),
    missing_points jsonb NOT NULL DEFAULT '[]'::jsonb,
    model varchar(80),
    prompt_version varchar(32),
    fallback_used boolean NOT NULL DEFAULT false,
    latency_ms integer CHECK (latency_ms >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (session_id, card_id)
);

CREATE TABLE card_ratings (
    session_id uuid NOT NULL REFERENCES study_sessions(id) ON DELETE CASCADE,
    card_id uuid NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    useful boolean NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, card_id)
);

CREATE TABLE ai_call_metrics (
    trace_id varchar(128) PRIMARY KEY,
    operation varchar(32) NOT NULL CHECK (operation IN ('generate_cards', 'evaluate_answer')),
    model varchar(80) NOT NULL,
    prompt_version varchar(32) NOT NULL,
    schema_version varchar(16) NOT NULL,
    fallback_used boolean NOT NULL,
    status_code integer NOT NULL CHECK (status_code BETWEEN 100 AND 599),
    latency_ms integer NOT NULL CHECK (latency_ms >= 0),
    input_tokens integer NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
    output_tokens integer NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
    estimated_cost_usd numeric(12,6) NOT NULL DEFAULT 0 CHECK (estimated_cost_usd >= 0),
    violation_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_documents_text_expiry ON documents(text_expires_at)
    WHERE extracted_text IS NOT NULL;
CREATE INDEX idx_sessions_user_status ON study_sessions(user_id, status);
CREATE INDEX idx_answer_attempts_session ON answer_attempts(session_id);
CREATE INDEX idx_ai_call_metrics_created ON ai_call_metrics(created_at);

COMMENT ON COLUMN documents.extracted_text IS 'Temporary normalized text; purge after text_expires_at.';
COMMENT ON TABLE ai_call_metrics IS 'Telemetry only: no PDF text, prompts, secrets, or student answers.';

COMMIT;
