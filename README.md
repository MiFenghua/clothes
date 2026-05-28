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

Create a backend-local env file from the root example before running FastAPI from `backend/`:

```powershell
Copy-Item .env.example backend/.env
```

Or on macOS/Linux:

```bash
cp .env.example backend/.env
```

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

Production-like provider configuration is controlled with `STYLE_BACKEND_*` environment variables in `backend/.env`. Set at least:

```env
STYLE_BACKEND_SEARCH_PROVIDER=taobao_union
STYLE_BACKEND_IMAGE_PROVIDER=ark
STYLE_BACKEND_MODEL_PROVIDER=ark
STYLE_BACKEND_ARK_API_KEY=...
STYLE_BACKEND_TAOBAO_UNION_APP_KEY=...
STYLE_BACKEND_TAOBAO_UNION_APP_SECRET=...
STYLE_BACKEND_TAOBAO_UNION_ADZONE_ID=...
```

The example env defaults to `STYLE_BACKEND_SEARCH_PROVIDER=local_demo`, so the backend starts without Taobao Union credentials. Without an Ark key, local deterministic providers keep the backend runnable for development and tests.

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
