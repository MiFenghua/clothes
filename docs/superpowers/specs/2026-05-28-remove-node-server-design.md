# Remove Node Demo Server Design

## Goal

The product target is Android plus the Python FastAPI backend. The old Node.js demo backend and WeChat mini program are no longer product targets and should be cleanly removed.

After this change, the repository should have one business backend:

- Android app talks to `backend/` FastAPI.
- Web debugging page is served by `backend/` FastAPI.
- Node Express API, Node prompt chain, mini program, and browser-scraping search scripts are removed.

## Current State

- `backend/` is the production path. It exposes `/api/v1/*`, serves objects at `/objects`, and already serves a static debug app from `backend/app/static`.
- `android/` calls the Python backend through `api_base_url`, currently port `8000`.
- `server/` is a Node/TypeScript demo backend with its own `/api/v1/*`, auth, model prompts, image generation providers, search providers, and tests.
- `web/` is currently mounted by the Node server at `/web` and contains one Node-only route dependency: `/internal/search-products`.
- `miniprogram/` defaults to `http://127.0.0.1:3000` and is tied to the old Node backend.
- `scripts/amazon-login.mjs` and `scripts/taobao-login.mjs` only support the Node browser-scraping search path.

## Decisions

1. Use the Python backend as the only runtime backend.
2. Keep a Web debugging page, but serve it from `backend/app/static`.
3. Do not keep the WeChat mini program.
4. Do not keep Node browser-scraping search for Amazon or Taobao.
5. Remove stale Node model prompts so future prompt review only covers Python backend code.

## Architecture

The Python backend remains responsible for:

- API routes under `/api/v1/*`.
- Static debug UI at `/`.
- Static assets under `/static`.
- Uploaded/generated object files under `/objects`.
- Model providers, search providers, image generation, image QC, persistence, and tracing.

The Web debugging page should use relative Python backend routes only:

- `POST /api/v1/style-tasks`
- `GET /api/v1/style-tasks/{task_id}`
- `GET /api/v1/style-tasks/{task_id}/result`
- `GET /api/v1/style-tasks/{task_id}/trace`
- wardrobe endpoints if the debug page exposes wardrobe upload/listing

Node-only routes such as `/internal/search-products` are removed rather than ported.

## Removal Scope

Remove:

- `server/`
- `miniprogram/`
- `scripts/amazon-login.mjs`
- `scripts/taobao-login.mjs`
- root Node backend scripts and dependencies from `package.json`
- `package-lock.json` if no remaining npm dependency is required
- `tsconfig.json` if TypeScript is no longer used
- old Node-only environment variables from `.env.example`

Keep:

- `backend/`
- `android/`
- `backend/app/static`
- `design/`, including `design/generate-clozai-ios-ui-kit.mjs`, because it uses Node built-in modules only and is not part of the old server runtime
- root documentation, updated to describe the Python-only backend path

## Web Debug Page Migration

The current Python static app is the preferred base because it already targets Python backend routes. During implementation:

1. Compare root `web/` with `backend/app/static`.
2. Move only useful debugging features that are missing from `backend/app/static`.
3. Drop Node-only `/internal/search-products` UI.
4. Ensure all requests are relative to the Python backend origin.

## Configuration

`.env.example` should become Python-backend focused:

- `STYLE_BACKEND_PUBLIC_BASE_URL`
- `STYLE_BACKEND_STORAGE_DIR`
- `STYLE_BACKEND_SEARCH_PROVIDER`
- `STYLE_BACKEND_IMAGE_PROVIDER`
- `STYLE_BACKEND_MODEL_PROVIDER`
- `STYLE_BACKEND_ARK_API_KEY`
- `STYLE_BACKEND_ARK_BASE_URL`
- `STYLE_BACKEND_ARK_VISION_MODEL`
- `STYLE_BACKEND_ARK_IMAGE_MODEL`
- `STYLE_BACKEND_TAOBAO_UNION_*`
- `STYLE_BACKEND_GOOGLE_CLIENT_ID`
- `STYLE_BACKEND_POSTGRES_DSN`

Remove old Node variables such as `PORT`, `PUBLIC_BASE_URL`, `SEARCH_PROVIDER`, `IMAGE_PROVIDER`, `OPENAI_IMAGE_MODEL`, `ARK_IMAGE_MODEL`, `VISION_PROVIDER`, browser profile paths, and Google OAuth callback settings used only by Node.

## Tests And Verification

Required verification:

- Run Python backend tests from `backend/`.
- Run Android unit tests if the cleanup touches Android docs/config or shared assumptions.
- Start FastAPI locally and verify `/` serves the Web debug page.
- Inspect the Web debug page code for calls to `/internal/*` or `127.0.0.1:3000`; none should remain.
- Run repository searches for old Node entry points:
  - `server/src`
  - `localhost:3000`
  - `127.0.0.1:3000`
  - `/internal/search-products`
  - `npm run dev`
  - `ARK_VISION_MODEL` without `STYLE_BACKEND_`

## Risks

- Some docs may still mention Node demo startup or mini program usage. The implementation must clean README and any focused docs that describe current runtime.
- Removing `package.json` may also remove a convenient command surface for design generation. Since the design generator has no external dependencies, it can remain as a direct `node design/generate-clozai-ios-ui-kit.mjs` command documented only if still needed.
- Existing untracked/generated files in the worktree should not be reverted or deleted unless they are part of the old Node/mini program removal scope.

## Acceptance Criteria

- The repo no longer contains the old Node demo backend or mini program.
- The Python backend is the only documented backend.
- The Web debug page is available from Python FastAPI.
- Android continues to target Python backend routes.
- No old Node model prompts remain in live source.
- Test and search verification pass with concrete command output.
