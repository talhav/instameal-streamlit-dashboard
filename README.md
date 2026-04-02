# instameal-streamlit-dashboard

Streamlit dashboard for testing the Instameals `initial-recommendations` API.

## Prerequisites

- Python 3.10
- `uv` installed
- Backend API running

## Environment setup

Copy the example env file and fill your real values:

```bash
copy .env.example .env
```

Required keys:

- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `API_URL`

## Run locally

```bash
uv sync --locked
uv run streamlit run app.py
```

Open: `http://localhost:8501`

## Run with Docker

Build:

```bash
docker build -t instameals-ui .
```

Run:

```bash
docker run --rm -p 8501:8501 --env-file .env instameals-ui
```

If backend runs on host machine, set `API_URL` in `.env` to:

`http://host.docker.internal:8001/api/v1/initial-recommendations`
