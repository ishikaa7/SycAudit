# SycAudit Backend — Quick Start

## 1. Set up environment
```bash
cp .env.example .env
# fill in GROQ_API_KEY, GEMINI_API_KEY, HUGGINGFACE_API_KEY
```

## 2. Start Postgres + the API
```bash
docker compose up --build
```
This starts Postgres on `5432` and FastAPI on `8000` with live-reload.

## 3. Run the migration (creates all seven tables)
In a second terminal, with the containers running:
```bash
docker compose exec backend alembic upgrade head
```

## 4. Seed the four LLM models
```bash
docker compose exec backend python -m app.seed_models
```

## 5. Verify
```bash
curl http://localhost:8000/health
```
Expect:
```json
{"status": "ok", "environment": "development", "database_connected": true, "database_error": null}
```

If `database_connected` is `false`, check `database_error` in the response — almost always a `.env` DB URL mismatch or the `db` container not being healthy yet.

## What's next (not in this slice)
- `LLMClient` interface + provider implementations (Groq/Gemini/HF)
- `ModelRegistry` reading from `llm_models`
- Framing generator, dispatcher, grader, aggregator
- `POST /submissions`, `GET /submissions/{id}`

## Notes for Ishika
- Schema lives in `app/models/tables.py` (SQLAlchemy) and `alembic/versions/0001_initial_schema.py` (migration) — these two must always move together. If you change one, change the other and regenerate a new revision rather than hand-editing `0001`.
- `llm_models.rate_limit_rpm` for Gemini is a placeholder (15) — verify the current free-tier number before we tune the dispatcher's semaphores against it.
