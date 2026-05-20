# AI Styling Agent Backend

This backend is a production-oriented replacement for the demo orchestration layer.
It uses an explicit workflow + expert-agent graph with quality gates so recommendation
and try-on image quality can be traced, evaluated, and improved.

## Architecture

- `api/`: FastAPI app and HTTP routes.
- `workflows/`: Temporal workflow entrypoints and compatibility shims.
- `agents/`: Explicit graph nodes: photo profiler, preference resolver, product scout,
  normalizer, stylist composer, critic, director, image prompt, try-on generator,
  image QC judge, and recovery agent.
- `schemas/`: Pydantic request, domain, result, and quality models.
- `providers/`: Search, image generation, object storage, persistence, and tracing adapters.
- `evals/`: Evaluation fixtures and regression utilities.

The local implementation ships with deterministic providers so the pipeline is runnable
without paid model/search integrations. Production providers should implement the same
interfaces and can be selected by configuration.

## Provider Configuration

The production path is selected through `STYLE_BACKEND_*` environment variables:

```env
STYLE_BACKEND_SEARCH_PROVIDER=browser
STYLE_BACKEND_IMAGE_PROVIDER=ark
STYLE_BACKEND_MODEL_PROVIDER=ark
STYLE_BACKEND_ARK_API_KEY=...
STYLE_BACKEND_MAX_IMAGE_ATTEMPTS=2
STYLE_BACKEND_IMAGE_CANDIDATES_PER_ATTEMPT=3
```

When Ark credentials are missing, the service falls back to deterministic local
photo/image providers so the Android app and backend tests can still run. Browser
search uses Playwright and only treats real marketplace detail pages with usable
product images as high-trust product data.

## Local Development

```bash
cd backend
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

PostgreSQL/pgvector bootstrap for production-like environments:

```bash
psql "$STYLE_BACKEND_POSTGRES_DSN" -f migrations/001_initial.sql
```

Create a task:

```bash
curl -F photo=@person.jpg \
  -F scene=daily \
  -F budget_min=300 \
  -F budget_max=800 \
  http://127.0.0.1:8000/api/v1/style-tasks
```

Then poll:

```bash
curl http://127.0.0.1:8000/api/v1/style-tasks/{task_id}
curl http://127.0.0.1:8000/api/v1/style-tasks/{task_id}/result
```

Retry only the try-on image for a task that already has an approved outfit:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/style-tasks/{task_id}/retry-image
```

## Quality Policy

The service is intentionally conservative:

- It will not output a final recommendation when product data or styling rationale is weak.
- It will not show a low-quality generated try-on image.
- If the outfit recommendation is strong but image QC fails after retries, the task returns
  a partial result with the recommendation report and no accepted try-on image.
