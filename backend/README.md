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
STYLE_BACKEND_SEARCH_PROVIDER=taobao_union
STYLE_BACKEND_IMAGE_PROVIDER=ark
STYLE_BACKEND_MODEL_PROVIDER=ark
STYLE_BACKEND_ARK_API_KEY=...
STYLE_BACKEND_TAOBAO_UNION_APP_KEY=...
STYLE_BACKEND_TAOBAO_UNION_APP_SECRET=...
STYLE_BACKEND_TAOBAO_UNION_ADZONE_ID=...
STYLE_BACKEND_MAX_IMAGE_ATTEMPTS=2
STYLE_BACKEND_IMAGE_CANDIDATES_PER_ATTEMPT=3
```

When Ark credentials are missing, the service falls back to deterministic local
photo/image providers so the Android app and backend tests can still run. Product
search is provider-based; the production provider is Taobao Union, and future
sources should implement `ProductSearchProvider` and be registered in the container.

## PostgreSQL Persistence

Set `STYLE_BACKEND_POSTGRES_DSN` to switch the backend from local JSON/in-memory
stores to PostgreSQL-backed auth, style task, wardrobe, favorite product, saved
look, and trace repositories:

```env
STYLE_BACKEND_POSTGRES_DSN=postgresql://style:password@localhost:5432/style
```

Run the migration before starting the API. The migration enables `pgvector` and
creates tables for user profiles and sessions, style task request/result history,
task trace events, wardrobe items, product snapshots, favorite products, and saved
looks:

```bash
psql "$STYLE_BACKEND_POSTGRES_DSN" -f migrations/001_initial.sql
```

PostgreSQL integration tests are opt-in. Set `STYLE_BACKEND_TEST_POSTGRES_DSN`
to a disposable database and run `python -m pytest tests/test_postgres_persistence.py`.
Those tests are skipped when the variable is not set.

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
