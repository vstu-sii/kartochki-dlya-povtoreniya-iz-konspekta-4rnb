CREATE TABLE IF NOT EXISTS documents (
  id varchar(64) PRIMARY KEY,
  original_filename varchar(255) NOT NULL DEFAULT 'pasted-text.txt',
  pages jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS card_sets (
  id varchar(64) PRIMARY KEY,
  document_id varchar(64) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  title varchar(200) NOT NULL,
  model varchar(100) NOT NULL,
  prompt_version varchar(32) NOT NULL,
  fallback_used boolean NOT NULL DEFAULT false,
  trace_id varchar(128) NOT NULL UNIQUE,
  latency_ms integer NOT NULL DEFAULT 0,
  input_tokens integer NOT NULL DEFAULT 0,
  output_tokens integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cards (
  id varchar(64) PRIMARY KEY,
  card_set_id varchar(64) NOT NULL REFERENCES card_sets(id) ON DELETE CASCADE,
  position integer NOT NULL CHECK (position BETWEEN 1 AND 10),
  question varchar(500) NOT NULL,
  reference_answer varchar(1200) NOT NULL,
  source_page integer NOT NULL CHECK (source_page > 0),
  source_quote varchar(500) NOT NULL,
  difficulty varchar(24) NOT NULL
);

CREATE TABLE IF NOT EXISTS answer_reviews (
  id varchar(64) PRIMARY KEY,
  card_id varchar(64) NOT NULL,
  student_answer text NOT NULL,
  verdict varchar(32) NOT NULL,
  feedback varchar(600) NOT NULL,
  missing_points jsonb NOT NULL DEFAULT '[]',
  model varchar(100) NOT NULL,
  trace_id varchar(128) NOT NULL UNIQUE,
  latency_ms integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS study_sessions (
  id varchar(64) PRIMARY KEY,
  card_set_id varchar(64) NOT NULL REFERENCES card_sets(id) ON DELETE CASCADE,
  user_id varchar(64) NOT NULL,
  current_position integer NOT NULL DEFAULT 0 CHECK (current_position >= 0),
  completed boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_study_sessions_card_set_id ON study_sessions(card_set_id);
CREATE INDEX IF NOT EXISTS ix_study_sessions_user_id ON study_sessions(user_id);

CREATE TABLE IF NOT EXISTS card_ratings (
  id varchar(64) PRIMARY KEY,
  session_id varchar(64) NOT NULL REFERENCES study_sessions(id) ON DELETE CASCADE,
  card_id varchar(64) NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  value varchar(16) NOT NULL CHECK (value IN ('useful', 'not_useful')),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_rating_session_card UNIQUE (session_id, card_id)
);

CREATE INDEX IF NOT EXISTS ix_card_ratings_session_id ON card_ratings(session_id);
CREATE INDEX IF NOT EXISTS ix_card_ratings_card_id ON card_ratings(card_id);
