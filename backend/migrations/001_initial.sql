CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS auth_users (
  user_id TEXT PRIMARY KEY,
  google_sub TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  avatar_url TEXT,
  provider TEXT NOT NULL DEFAULT 'google',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_users_email
  ON auth_users (email);

CREATE TABLE IF NOT EXISTS auth_sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  token_hash TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'auth_sessions_user_id_fkey'
      AND conrelid = 'auth_sessions'::regclass
  ) THEN
    ALTER TABLE auth_sessions
      ADD CONSTRAINT auth_sessions_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES auth_users(user_id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_hash
  ON auth_sessions (token_hash);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_expires
  ON auth_sessions (user_id, expires_at);

CREATE TABLE IF NOT EXISTS style_tasks (
  task_id TEXT PRIMARY KEY,
  user_id TEXT,
  status TEXT NOT NULL,
  progress INTEGER NOT NULL DEFAULT 0,
  message TEXT NOT NULL DEFAULT '',
  request JSONB NOT NULL,
  result JSONB,
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'style_tasks_user_id_fkey'
      AND conrelid = 'style_tasks'::regclass
  ) THEN
    ALTER TABLE style_tasks
      ADD CONSTRAINT style_tasks_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES auth_users(user_id) ON DELETE SET NULL NOT VALID;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_style_tasks_user_created
  ON style_tasks (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS user_style_profiles (
  profile_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  source_task_id TEXT REFERENCES style_tasks(task_id) ON DELETE SET NULL,
  profile JSONB NOT NULL,
  embedding vector(1536),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_style_profiles_embedding
  ON user_style_profiles USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS wardrobe_items (
  item_id TEXT PRIMARY KEY,
  owner_id TEXT,
  category TEXT NOT NULL,
  title TEXT NOT NULL,
  image_url TEXT NOT NULL,
  colors TEXT[] NOT NULL DEFAULT '{}',
  style_tags TEXT[] NOT NULL DEFAULT '{}',
  fit_tags TEXT[] NOT NULL DEFAULT '{}',
  notes TEXT,
  embedding vector(1536),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wardrobe_items_owner_category
  ON wardrobe_items (owner_id, category);

CREATE INDEX IF NOT EXISTS idx_wardrobe_items_embedding
  ON wardrobe_items USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS product_snapshots (
  product_id TEXT PRIMARY KEY,
  marketplace TEXT NOT NULL,
  category TEXT NOT NULL,
  title TEXT NOT NULL,
  price NUMERIC NOT NULL DEFAULT 0,
  image_url TEXT NOT NULL,
  product_url TEXT NOT NULL,
  shop_name TEXT,
  sizes TEXT[] NOT NULL DEFAULT '{}',
  colors TEXT[] NOT NULL DEFAULT '{}',
  style_tags TEXT[] NOT NULL DEFAULT '{}',
  fit_tags TEXT[] NOT NULL DEFAULT '{}',
  source_reliability NUMERIC NOT NULL DEFAULT 0,
  score NUMERIC NOT NULL DEFAULT 0,
  risk_flags TEXT[] NOT NULL DEFAULT '{}',
  raw JSONB NOT NULL DEFAULT '{}',
  embedding vector(1536),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_snapshots_market_category
  ON product_snapshots (marketplace, category);

CREATE INDEX IF NOT EXISTS idx_product_snapshots_embedding
  ON product_snapshots USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS saved_looks (
  look_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  source_task_id TEXT REFERENCES style_tasks(task_id) ON DELETE SET NULL,
  outfit JSONB,
  recommendation_report JSONB NOT NULL,
  try_on_image_url TEXT,
  image_quality_report JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_saved_looks_user_created
  ON saved_looks (user_id, created_at DESC);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'saved_looks_user_id_fkey'
      AND conrelid = 'saved_looks'::regclass
  ) THEN
    ALTER TABLE saved_looks
      ADD CONSTRAINT saved_looks_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES auth_users(user_id) ON DELETE CASCADE NOT VALID;
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_looks_unique_user_task
  ON saved_looks (user_id, source_task_id)
  WHERE source_task_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS favorite_products (
  favorite_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
  product_id TEXT NOT NULL,
  marketplace TEXT NOT NULL,
  category TEXT NOT NULL,
  title TEXT NOT NULL,
  price NUMERIC NOT NULL DEFAULT 0,
  price_text TEXT,
  image_url TEXT NOT NULL,
  product_url TEXT NOT NULL,
  shop_name TEXT,
  sizes TEXT[] NOT NULL DEFAULT '{}',
  colors TEXT[] NOT NULL DEFAULT '{}',
  style_tags TEXT[] NOT NULL DEFAULT '{}',
  fit_tags TEXT[] NOT NULL DEFAULT '{}',
  source_reliability NUMERIC NOT NULL DEFAULT 0,
  score NUMERIC NOT NULL DEFAULT 0,
  risk_flags TEXT[] NOT NULL DEFAULT '{}',
  raw JSONB NOT NULL DEFAULT '{}',
  source_task_id TEXT REFERENCES style_tasks(task_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_favorite_products_user_created
  ON favorite_products (user_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_favorite_products_user_product_marketplace
  ON favorite_products (user_id, product_id, marketplace);

CREATE TABLE IF NOT EXISTS trace_events (
  event_id BIGSERIAL PRIMARY KEY,
  task_id TEXT NOT NULL,
  node TEXT NOT NULL,
  event TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trace_events_task_created
  ON trace_events (task_id, created_at);

CREATE TABLE IF NOT EXISTS eval_runs (
  eval_run_id TEXT PRIMARY KEY,
  suite_name TEXT NOT NULL,
  git_sha TEXT,
  aggregate JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eval_case_results (
  eval_run_id TEXT REFERENCES eval_runs(eval_run_id) ON DELETE CASCADE,
  case_id TEXT NOT NULL,
  status TEXT NOT NULL,
  metrics JSONB NOT NULL,
  failure_reason TEXT,
  PRIMARY KEY (eval_run_id, case_id)
);
