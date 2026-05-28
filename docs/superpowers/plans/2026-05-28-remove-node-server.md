# Remove Node Demo Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the old Node.js demo backend and WeChat mini program while keeping Android plus the Python FastAPI backend, with the Web debug page served by Python.

**Architecture:** Python FastAPI remains the single backend and static Web debug host. The existing `backend/app/static` app is the source of truth because it already uses Python `/api/v1/*` routes; old Node-only search UI and browser-scraping helpers are removed instead of ported.

**Tech Stack:** Python 3.12, FastAPI, pytest, Kotlin/Android Gradle tests when Android files are touched, plain HTML/CSS/JS static assets.

---

## File Structure

- Create `backend/tests/test_repository_cleanup.py`: regression tests that fail while old Node runtime artifacts remain and pass once cleanup is complete.
- Keep `backend/app/static/index.html`, `backend/app/static/app.js`, and `backend/app/static/styles.css`: Python-hosted Web debug page.
- Modify `.env.example`: replace mixed Node/Python variables with Python `STYLE_BACKEND_*` variables only.
- Modify `README.md`: document only Python backend, Android app, Web debug page, and verification commands.
- Delete `server/`: old Node Express backend, Node model prompts, Node auth, Node tests, browser search adapters, and stored browser profiles.
- Delete `miniprogram/`: WeChat mini program tied to old Node backend.
- Delete `scripts/amazon-login.mjs` and `scripts/taobao-login.mjs`: old Playwright login helpers for removed browser-scraping search.
- Delete `package.json`, `package-lock.json`, and `tsconfig.json`: root Node backend build/test surface is no longer needed. `design/generate-clozai-ios-ui-kit.mjs` remains runnable directly with `node` because it uses only Node built-in modules.

Historical files under `docs/superpowers/**` may still mention Node or port `3000` because they record previous decisions. Cleanup searches should target live source/config/docs and explicitly exclude historical superpowers specs/plans.

---

### Task 1: Add Cleanup Regression Tests

**Files:**
- Create: `backend/tests/test_repository_cleanup.py`

- [ ] **Step 1: Create the failing cleanup tests**

Create `backend/tests/test_repository_cleanup.py` with:

```python
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


REMOVED_RUNTIME_PATHS = [
    "server",
    "miniprogram",
    "scripts/amazon-login.mjs",
    "scripts/taobao-login.mjs",
    "package.json",
    "package-lock.json",
    "tsconfig.json",
]


REMOVED_ENV_KEYS = [
    "PORT=",
    "PUBLIC_BASE_URL=",
    "SEARCH_PROVIDER=",
    "IMAGE_PROVIDER=",
    "OPENAI_API_KEY=",
    "OPENAI_IMAGE_MODEL=",
    "ARK_API_KEY=",
    "ARK_IMAGE_MODEL=",
    "ARK_VISION_MODEL=",
    "VISION_PROVIDER=",
    "AMAZON_BROWSER_ENABLED=",
    "TAOBAO_BROWSER_ENABLED=",
]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_old_node_runtime_paths_are_removed() -> None:
    existing = [relative for relative in REMOVED_RUNTIME_PATHS if (ROOT / relative).exists()]
    assert existing == []


def test_python_static_debug_app_has_no_node_internal_routes() -> None:
    html = read_text("backend/app/static/index.html")
    javascript = read_text("backend/app/static/app.js")
    combined = f"{html}\n{javascript}"

    assert "/api/v1/style-tasks" in combined
    assert "/static/app.js" in html
    assert "/internal/" not in combined
    assert "127.0.0.1:3000" not in combined
    assert "localhost:3000" not in combined


def test_env_example_is_python_backend_focused() -> None:
    env_example = read_text(".env.example")

    assert "STYLE_BACKEND_MODEL_PROVIDER=ark" in env_example
    assert "STYLE_BACKEND_ARK_VISION_MODEL=" in env_example
    assert "STYLE_BACKEND_ARK_IMAGE_MODEL=" in env_example

    remaining = [key for key in REMOVED_ENV_KEYS if key in env_example]
    assert remaining == []


def test_root_readme_documents_python_only_runtime() -> None:
    readme = read_text("README.md")

    assert "Python FastAPI" in readme
    assert "uvicorn app.main:app --reload --port 8000" in readme
    assert "server/src" not in readme
    assert "Node Demo" not in readme
    assert "miniprogram/" not in readme
    assert "127.0.0.1:3000" not in readme
```

- [ ] **Step 2: Run the new tests and verify they fail for the current repo**

Run:

```powershell
cd backend
python -m pytest tests/test_repository_cleanup.py -q
```

Expected: FAIL. The failure should mention existing old runtime paths such as `server`, `miniprogram`, `package.json`, or old env keys in `.env.example`.

- [ ] **Step 3: Commit the failing guard tests**

Run:

```powershell
git add backend/tests/test_repository_cleanup.py
git commit -m "test: guard python-only backend cleanup"
```

Expected: commit succeeds and only `backend/tests/test_repository_cleanup.py` is included.

---

### Task 2: Remove Old Node Runtime And Mini Program Files

**Files:**
- Delete: `server/`
- Delete: `miniprogram/`
- Delete: `scripts/amazon-login.mjs`
- Delete: `scripts/taobao-login.mjs`
- Delete: `package.json`
- Delete: `package-lock.json`
- Delete: `tsconfig.json`

- [ ] **Step 1: Verify deletion targets resolve inside the repository**

Run from repository root:

```powershell
$root = (Resolve-Path .).Path
$targets = @(
  "server",
  "miniprogram",
  "scripts/amazon-login.mjs",
  "scripts/taobao-login.mjs",
  "package.json",
  "package-lock.json",
  "tsconfig.json"
)
foreach ($target in $targets) {
  $resolved = Resolve-Path -LiteralPath $target -ErrorAction SilentlyContinue
  if ($resolved -and -not $resolved.Path.StartsWith($root)) {
    throw "Refusing to remove outside repo: $($resolved.Path)"
  }
  if ($resolved) {
    Write-Output $resolved.Path
  }
}
```

Expected: every printed path starts with `E:\work\clothes`.

- [ ] **Step 2: Remove the old runtime files**

Run from repository root:

```powershell
$targets = @(
  "server",
  "miniprogram",
  "scripts/amazon-login.mjs",
  "scripts/taobao-login.mjs",
  "package.json",
  "package-lock.json",
  "tsconfig.json"
)
foreach ($target in $targets) {
  if (Test-Path -LiteralPath $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
  }
}
```

Expected: the listed files/directories no longer exist. Do not remove `scripts/` itself because the directory may remain useful for future non-Node scripts.

- [ ] **Step 3: Run cleanup tests and verify remaining failures are docs/env only**

Run:

```powershell
cd backend
python -m pytest tests/test_repository_cleanup.py -q
```

Expected: failures should no longer list old runtime paths. Failures may still mention `.env.example` or `README.md` until Task 3 is complete.

- [ ] **Step 4: Commit removed runtime files**

Run:

```powershell
git add -A server miniprogram scripts/amazon-login.mjs scripts/taobao-login.mjs package.json package-lock.json tsconfig.json
git commit -m "chore: remove node demo runtime"
```

Expected: commit succeeds and includes only the old runtime removals.

---

### Task 3: Rewrite Root Runtime Configuration And README

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Replace `.env.example` with Python backend variables**

Set `.env.example` to:

```env
STYLE_BACKEND_PUBLIC_BASE_URL=http://127.0.0.1:8000
STYLE_BACKEND_STORAGE_DIR=backend/storage
STYLE_BACKEND_GENERATED_DIR=backend/storage/generated
STYLE_BACKEND_UPLOAD_DIR=backend/storage/uploads
STYLE_BACKEND_AUTH_STORE_PATH=backend/storage/auth-store.json
STYLE_BACKEND_PRODUCT_STORE_PATH=backend/storage/product-store.json
STYLE_BACKEND_AUTH_SESSION_MAX_AGE_DAYS=30

STYLE_BACKEND_SEARCH_PROVIDER=taobao_union
STYLE_BACKEND_IMAGE_PROVIDER=ark
STYLE_BACKEND_MODEL_PROVIDER=ark
STYLE_BACKEND_RECOMMENDATION_THRESHOLD=0.82
STYLE_BACKEND_IMAGE_THRESHOLD=0.84
STYLE_BACKEND_MAX_IMAGE_ATTEMPTS=2
STYLE_BACKEND_IMAGE_CANDIDATES_PER_ATTEMPT=3
STYLE_BACKEND_IMAGE_GENERATION_CONCURRENCY=3
STYLE_BACKEND_IMAGE_QUALITY_CONCURRENCY=3

STYLE_BACKEND_ARK_API_KEY=
STYLE_BACKEND_ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
STYLE_BACKEND_ARK_VISION_MODEL=doubao-seed-1-6-vision-250815
STYLE_BACKEND_ARK_IMAGE_MODEL=doubao-seedream-5-0-260128
STYLE_BACKEND_ARK_IMAGE_SIZE=2K
STYLE_BACKEND_ARK_WATERMARK=true

STYLE_BACKEND_TAOBAO_UNION_ENDPOINT=https://eco.taobao.com/router/rest
STYLE_BACKEND_TAOBAO_UNION_METHOD=taobao.tbk.dg.material.optional.upgrade
STYLE_BACKEND_TAOBAO_UNION_APP_KEY=
STYLE_BACKEND_TAOBAO_UNION_APP_SECRET=
STYLE_BACKEND_TAOBAO_UNION_ADZONE_ID=
STYLE_BACKEND_TAOBAO_UNION_SITE_ID=
STYLE_BACKEND_TAOBAO_UNION_MATERIAL_ID=80309
STYLE_BACKEND_TAOBAO_UNION_SIGN_METHOD=md5
STYLE_BACKEND_TAOBAO_UNION_TIMEOUT_SECONDS=15

STYLE_BACKEND_GOOGLE_CLIENT_ID=
STYLE_BACKEND_POSTGRES_DSN=
```

- [ ] **Step 2: Replace root `README.md` with Python-only runtime docs**

Set `README.md` to:

````markdown
# clothes

AI styling product targeting a native Android app and a Python FastAPI agent backend.

## Project Structure

```text
backend/    Python FastAPI backend, agent graph, model providers, storage, tracing, and Web debug page
android/    Kotlin Compose Android app
design/     Design references and generated UI kit assets
docs/       Specs and implementation plans
```

## Python Backend

Start the backend:

```bash
cd backend
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Useful local URLs:

- Web debug page: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/health`
- Uploaded/generated objects: `http://127.0.0.1:8000/objects/...`

Production-like provider configuration is controlled with `STYLE_BACKEND_*` environment variables. Copy `.env.example` to `.env` and set at least:

```env
STYLE_BACKEND_SEARCH_PROVIDER=taobao_union
STYLE_BACKEND_IMAGE_PROVIDER=ark
STYLE_BACKEND_MODEL_PROVIDER=ark
STYLE_BACKEND_ARK_API_KEY=...
STYLE_BACKEND_TAOBAO_UNION_APP_KEY=...
STYLE_BACKEND_TAOBAO_UNION_APP_SECRET=...
STYLE_BACKEND_TAOBAO_UNION_ADZONE_ID=...
```

Without an Ark key, local deterministic providers keep the backend runnable for development and tests.

## Android App

The Android app talks directly to the Python backend through `android/app/src/main/res/values/strings.xml`.

For an emulator, use:

```xml
<string name="api_base_url">http://10.0.2.2:8000</string>
```

For a local desktop browser or same-machine test, `http://127.0.0.1:8000` is fine. Real device testing needs a LAN IP or HTTPS backend URL.

Google login uses Android Credential Manager. Configure the same Web Client ID in:

- backend env: `STYLE_BACKEND_GOOGLE_CLIENT_ID`
- Android resource: `google_web_client_id`

## Web Debug Page

The debug page is served by FastAPI from `backend/app/static` at `/`. It uses Python backend routes only:

- `POST /api/v1/style-tasks`
- `GET /api/v1/style-tasks/{task_id}`
- `GET /api/v1/style-tasks/{task_id}/result`
- `GET /api/v1/style-tasks/{task_id}/trace`
- `GET/POST /api/v1/wardrobe-items`

## Verification

Backend tests:

```bash
cd backend
python -m pytest
```

Android tests:

```bash
cd android
./gradlew test
```

Design UI kit generation, if needed:

```bash
node design/generate-clozai-ios-ui-kit.mjs
```
````

- [ ] **Step 3: Run cleanup tests**

Run:

```powershell
cd backend
python -m pytest tests/test_repository_cleanup.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit config and README cleanup**

Run:

```powershell
git add .env.example README.md
git commit -m "docs: document python backend runtime"
```

Expected: commit succeeds and includes only `.env.example` and `README.md`.

---

### Task 4: Verify Python Web Debug Page And Backend Tests

**Files:**
- Test: `backend/tests/test_repository_cleanup.py`
- Test: all existing `backend/tests/*.py`

- [ ] **Step 1: Run full backend test suite**

Run:

```powershell
cd backend
python -m pytest
```

Expected: all non-skipped backend tests pass.

- [ ] **Step 2: Verify live source has no old Node runtime references**

Run from repository root:

```powershell
rg -n "server/src|localhost:3000|127\\.0\\.0\\.1:3000|/internal/search-products|npm run dev|ARK_VISION_MODEL" `
  . `
  --glob '!docs/superpowers/**' `
  --glob '!artifacts/**' `
  --glob '!storage/**' `
  --glob '!backend/storage/**' `
  --glob '!node_modules/**' `
  --glob '!dist/**'
```

Expected: no matches. If matches appear in live source, update or remove those references.

- [ ] **Step 3: Start FastAPI locally for browser verification**

Run:

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected: server starts and logs that Uvicorn is running on `http://127.0.0.1:8000`.

- [ ] **Step 4: Open and inspect the Web debug page**

Open `http://127.0.0.1:8000/` in the Codex Browser or a local browser.

Expected:

- Page loads without 404s for `/static/styles.css` or `/static/app.js`.
- Main tabs show `搭配`, `衣橱`, and `质检`.
- Browser console has no failed requests to `/internal/*` or port `3000`.

- [ ] **Step 5: Stop the FastAPI server**

Stop the Uvicorn process started in Step 3.

Expected: no long-running development server remains after verification.

---

### Task 5: Android Check Decision And Final Cleanup Review

**Files:**
- Test: `android/` only if Android files were touched during implementation
- Review: repository status and cleanup search output

- [ ] **Step 1: Confirm Android files were not changed**

Run:

```powershell
git status --short -- android
```

Expected: no output. This cleanup plan does not modify Android code or resources.

If this command prints Android files, stop and inspect those changes. They are outside this cleanup plan unless they are pre-existing user changes.

- [ ] **Step 2: Review git status for accidental unrelated changes**

Run:

```powershell
git status --short
```

Expected: only intended cleanup files are modified/deleted/untracked. Existing unrelated user changes may still appear and must not be reverted.

- [ ] **Step 3: Commit final verification fixes if the previous tasks required edits**

If Task 4 required follow-up edits to cleanup files, stage this fixed set:

```powershell
git add .env.example README.md backend/app/static/index.html backend/app/static/app.js backend/app/static/styles.css backend/tests/test_repository_cleanup.py
git commit -m "chore: finish python-only backend cleanup"
```

Expected: commit succeeds if any of those files changed. If none of those files changed, Git reports nothing to commit; skip the commit and report that no final fix commit was required.

---

## Self-Review Checklist

- Spec coverage: Tasks remove Node backend, mini program, browser-scraping helpers, root Node build files, stale env variables, and stale README runtime docs.
- Web debug page: Task 4 verifies Python-served static page and excludes Node-only `/internal/*` calls.
- Prompt cleanup: Deleting `server/` removes old Node prompt chain from live source.
- Historical docs: Search command excludes `docs/superpowers/**` so archived specs/plans can preserve historical context without failing live cleanup.
- No placeholders: every task names exact files and commands.
