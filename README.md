# instameal-streamlit-dashboard

Streamlit dashboard for testing the Instameals initial-recommendations API.

## What this app does

- Builds request payloads for the recommendation API from a tester-friendly form.
- Sends requests and renders recommendation output with product cards.
- Lets testers submit feedback for each generated run.
- Saves request payload, response payload, and feedback into MongoDB for tracking.

## Prerequisites

- Python 3.10 or newer
- uv installed
- Running API endpoint for initial recommendations
- Reachable PostgreSQL database (for menu/product rendering)
- Reachable MongoDB database (for save flow)

## Environment setup

1. Create a local env file:

```bash
cp .env.example .env
```

For Windows Command Prompt:

```cmd
copy .env.example .env
```

2. Fill all required keys in .env:

- DB_HOST: PostgreSQL host
- DB_PORT: PostgreSQL port
- DB_NAME: PostgreSQL database name
- DB_USER: PostgreSQL username
- DB_PASSWORD: PostgreSQL password
- API_URL: initial recommendations endpoint
- MONGO_URI: MongoDB connection string
- MONGO_DB_NAME: target MongoDB database name
- MONGO_COLLECTION_NAME: target MongoDB collection name

Example Mongo values:

- MONGO_DB_NAME=recommender
- MONGO_COLLECTION_NAME=test_runs

## Run locally

```bash
uv sync --locked
uv run streamlit run app.py
```

Open http://localhost:8501

## Tester workflow

1. Fill the request form on the left panel.
2. Click Generate Recommendations.
3. Review output in the right panel.
4. Enter tester feedback in the Feedback field.
5. Click Save.
6. Wait for the Saving test run... indicator to finish before starting the next test.

## Save behavior and validation

- Save is shown only after a generated run exists.
- Feedback is required.
- If feedback is missing, the app shows: please add the feedback to save
- Save requires generated request and response payloads.
- On validation error or Mongo save error, generated state remains visible in the UI.

## Mongo document schema

Each save writes one document containing:

- request_payload
- response_payload
- feedback
- created_at

## Docker

Build:

```bash
docker build -t instameals-ui .
```

Run:

```bash
docker run --rm -p 8501:8501 --env-file .env instameals-ui
```

If the API runs on your host machine, set API_URL in .env to:

http://host.docker.internal:8001/api/v1/initial-recommendations

## Troubleshooting

- Mongo save fails:
  Check MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME, and network access.
- Recommendation panel empty:
  Check API_URL and backend availability.
- Product cards missing:
  Check PostgreSQL credentials and data for selected menu_id.
