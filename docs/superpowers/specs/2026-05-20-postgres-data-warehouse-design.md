# PostgreSQL Data Warehouse Persistence Design

## Context

The backend currently has production-shaped schema files but most runtime storage is still local:

- `AuthStore` persists users and sessions to a JSON file.
- `InMemoryTaskRepository` stores task requests and results in memory.
- `InMemoryWardrobeRepository` stores wardrobe items in memory.
- `InMemoryTraceRecorder` stores agent trace events in memory.
- `backend/migrations/001_initial.sql` already defines several Postgres tables, but `PostgresTaskRepository` is a stub that inherits the in-memory behavior.

The requested outcome is formal PostgreSQL persistence for user personal information, every user request log, wardrobe data, favorite products, and saved looks.

## Goals

- Use PostgreSQL when `STYLE_BACKEND_POSTGRES_DSN` is configured.
- Persist auth users and sessions in Postgres instead of the JSON auth file.
- Persist style task requests, status updates, results, and request ownership.
- Persist trace events for each task so request execution can be audited.
- Persist user wardrobe items.
- Add single-product favorites with user-scoped list, create, and delete behavior.
- Add saved looks for whole completed recommendation results.
- Preserve the current local development fallback when no Postgres DSN is configured.
- Fail clearly when a Postgres DSN is configured but the database cannot be used.

## Non-Goals

- No analytics ETL, aggregation jobs, dashboards, or scheduled warehouse transforms in this phase.
- No migration runner framework beyond maintaining SQL migration files.
- No vector search implementation beyond preserving existing vector-capable columns and indexes.
- No frontend UI changes are required for this spec.
- No anonymous favorites or anonymous saved looks. Favorites and saved looks require an authenticated user.

## Recommended Approach

Implement "Postgres repository plus favorites API" as the first production persistence layer.

The app keeps the existing interface-oriented shape but replaces local stores with concrete Postgres implementations when `STYLE_BACKEND_POSTGRES_DSN` is present:

- `PostgresAuthStore`
- `PostgresTaskRepository`
- `PostgresWardrobeRepository`
- `PostgresTraceRecorder`
- `PostgresFavoritesRepository`

`AppContainer` is responsible for selecting the implementation set. If no DSN is present, existing local implementations remain available for development and tests. If a DSN is present, connection or SQL setup failures must surface as errors rather than silently falling back to memory.

## Data Model

Extend `backend/migrations/001_initial.sql` while preserving existing tables.

### Auth Users

`auth_users`

- `user_id TEXT PRIMARY KEY`
- `google_sub TEXT UNIQUE NOT NULL`
- `email TEXT UNIQUE NOT NULL`
- `name TEXT NOT NULL`
- `avatar_url TEXT`
- `provider TEXT NOT NULL DEFAULT 'google'`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- unique index on lower-case `email` behavior is handled by normalizing email before write.
- unique index on `google_sub`.

### Auth Sessions

`auth_sessions`

- `session_id TEXT PRIMARY KEY`
- `user_id TEXT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE`
- `token_hash TEXT UNIQUE NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `expires_at TIMESTAMPTZ NOT NULL`

Indexes:

- `token_hash`
- `(user_id, expires_at DESC)`

Expired sessions are pruned during session creation and token lookup, matching existing JSON-store behavior.

### Style Tasks

Reuse `style_tasks`, with these runtime expectations:

- `user_id` is set from the authenticated user when present.
- `request JSONB` stores the validated `StyleTaskRequest`.
- `result JSONB` stores the validated `StyleTaskResult` once available.
- `error` stores the user-facing failure message when a task fails.
- `created_at` and `updated_at` are maintained on every write.

Existing index `(user_id, created_at DESC)` supports user task history.

### Trace Events

Reuse `trace_events` for request execution logs:

- `task_id`
- `node`
- `event`
- `payload JSONB`
- `created_at`

The tracer should append one row per agent or service event. The existing `GET /api/v1/style-tasks/{task_id}/trace` route reads from this table in Postgres mode.

### Wardrobe Items

Reuse `wardrobe_items`:

- `owner_id` stores the authenticated user id.
- `owner_id NULL` remains supported for existing anonymous wardrobe behavior.
- list behavior must remain scoped: logged-in users see their own items; anonymous users see only anonymous items.

### Favorite Products

Add `favorite_products`.

- `favorite_id TEXT PRIMARY KEY`
- `user_id TEXT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE`
- `product_id TEXT NOT NULL`
- `marketplace TEXT NOT NULL`
- `category TEXT NOT NULL`
- `title TEXT NOT NULL`
- `price NUMERIC NOT NULL DEFAULT 0`
- `price_text TEXT`
- `image_url TEXT NOT NULL`
- `product_url TEXT NOT NULL`
- `shop_name TEXT`
- `sizes TEXT[] NOT NULL DEFAULT '{}'`
- `colors TEXT[] NOT NULL DEFAULT '{}'`
- `style_tags TEXT[] NOT NULL DEFAULT '{}'`
- `fit_tags TEXT[] NOT NULL DEFAULT '{}'`
- `source_reliability NUMERIC NOT NULL DEFAULT 0`
- `score NUMERIC NOT NULL DEFAULT 0`
- `risk_flags TEXT[] NOT NULL DEFAULT '{}'`
- `raw JSONB NOT NULL DEFAULT '{}'`
- `source_task_id TEXT REFERENCES style_tasks(task_id) ON DELETE SET NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:

- `(user_id, created_at DESC)`
- unique `(user_id, product_id, marketplace)` to make repeated favorite requests idempotent.

The table stores a product snapshot rather than only a foreign key because recommendation products may come from live search results and may not exist in `product_snapshots`.

### Saved Looks

Reuse `saved_looks`:

- `user_id` must reference the authenticated user.
- `source_task_id` links to the completed style task.
- `outfit`, `recommendation_report`, `try_on_image_url`, and `image_quality_report` copy the task result snapshot at save time.

Add a unique index on `(user_id, source_task_id)` when `source_task_id` is not null so saving the same completed task twice is idempotent.

## API Design

### Favorite Products

`GET /api/v1/favorite-products`

- Requires auth.
- Returns favorites for the current user, newest first.

`POST /api/v1/favorite-products`

- Requires auth.
- Accepts a product snapshot payload compatible with `ProductCandidate`, plus optional `source_task_id`.
- Creates a favorite or returns the existing favorite for the same `(user_id, product_id, marketplace)`.
- If `source_task_id` is provided, the task must belong to the current user.

`DELETE /api/v1/favorite-products/{favorite_id}`

- Requires auth.
- Deletes only if the favorite belongs to the current user.
- Returns `{ "ok": true }` for a deleted record.
- Returns `404` when the favorite does not exist for the current user.

### Saved Looks

`GET /api/v1/saved-looks`

- Requires auth.
- Returns saved looks for the current user, newest first.

`POST /api/v1/style-tasks/{task_id}/save-look`

- Requires auth.
- The task must exist, belong to the current user, and have a result with an outfit and recommendation report.
- Creates or returns the existing saved look for `(user_id, task_id)`.
- Accepts both `succeeded` and `partial_succeeded` results if an outfit exists.
- Rejects failed or incomplete tasks with `409`.

## Data Flow

### Login

1. Verify Google ID token.
2. Normalize email to lower case.
3. Upsert `auth_users` by Google subject or email.
4. Create `auth_sessions` with hashed token only.
5. Return public user and raw session token.

### Style Task Request

1. Resolve current user from bearer token.
2. Validate uploaded photo and wardrobe item access.
3. Save uploaded object through the existing object storage provider.
4. Create a `style_tasks` row with `user_id`, request JSON, status `created`, and initial progress.
5. Run the graph in the background.
6. Each status callback updates the same task row.
7. Agent trace events append rows to `trace_events`.
8. Completion writes result JSON; failure writes status, error, and updated timestamp.

### Favorite Product

1. Require authenticated user.
2. Validate product snapshot.
3. Insert favorite row.
4. On unique conflict, return the existing favorite.

### Save Look

1. Require authenticated user.
2. Load task by id.
3. Require task ownership.
4. Require a completed result with outfit and recommendation report.
5. Insert saved look snapshot.
6. On unique conflict, return the existing saved look.

## Error Handling

- Configured DSN with missing tables, failed connection, or SQL errors should produce explicit startup or request errors.
- No configured DSN keeps current local fallback behavior.
- Auth token lookup prunes expired sessions before matching.
- Favorites and saved looks return `401` when unauthenticated.
- Cross-user favorite delete, favorite source task lookup, and save-look task lookup return `404` to avoid leaking ids.
- Saving an incomplete or failed task returns `409`.

## Security and Privacy

- Raw session tokens are never stored. Only SHA-256 token hashes are persisted.
- User email is normalized before persistence.
- Favorites and saved looks are always scoped by current `user_id`.
- Task ownership is stored on `style_tasks.user_id` so saved looks and future task history can enforce access control.
- Trace payloads may include operational details and should stay behind existing task trace routes rather than being exposed as global logs.

## Testing Strategy

Use test-first implementation for behavior changes.

Repository tests should cover:

- Auth user upsert by Google subject and email.
- Session creation, lookup, expiration pruning, and logout.
- Task create, status update, completion, failure, and reload from Postgres.
- Trace append and task-scoped read.
- Wardrobe save, list by owner, anonymous list, and product conversion.
- Favorite create, idempotent duplicate create, list ordering, and scoped delete.
- Saved look create, duplicate save, list ordering, and incomplete task rejection.

API tests should cover:

- Logged-in favorite create/list/delete.
- Unauthenticated favorite requests return `401`.
- User A cannot see or delete User B favorites.
- Saving a completed owned task works.
- Saving a failed or unfinished task returns `409`.
- User A cannot save User B task.
- Existing style task and wardrobe API behavior remains unchanged.

Integration tests can use a real Postgres DSN when available and skip otherwise. Local unit tests should continue to run without Postgres.

## Rollout

1. Add SQL migration changes.
2. Add repository interfaces for wardrobe, auth, trace, and favorites where current code is concrete.
3. Implement Postgres repositories with psycopg row mapping and JSONB serialization through Pydantic models.
4. Wire `AppContainer` to choose the Postgres implementation set when `STYLE_BACKEND_POSTGRES_DSN` is configured.
5. Add favorites and saved looks schemas and routes.
6. Update README environment documentation.
7. Run backend tests and a focused Postgres integration check when a test DSN is available.

## Acceptance Criteria

- With `STYLE_BACKEND_POSTGRES_DSN` configured, users, sessions, style tasks, wardrobe items, trace events, favorite products, and saved looks persist across process restarts.
- With no DSN configured, existing local development flow still works.
- Configured Postgres failures do not silently fall back to memory.
- Favorite products support create, list, delete, and duplicate-safe behavior.
- Saved looks support saving completed or partial completed recommendations with an outfit.
- User data is scoped by `user_id` in API and repository behavior.
- Existing tests pass, and new persistence/API tests cover the added behavior.
