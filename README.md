# instameal-streamlit-dashboard

A multi-page Streamlit testing dashboard for the Instameals Recommendation Engine. Provides a tester-friendly UI to validate both the **First Recommendation** and **Nth Recommendation** endpoints, render product cards, and persist test runs with feedback to MongoDB.

---

## Pages

### 1. First Recommendation (`/`)

Tests the initial `POST /api/v1/initial-recommendations` endpoint.

- Build a full request payload via a structured form (user profile, goal, meals, delivery days).
- View rendered product cards grouped by meal type with nutrition data.
- Submit tester feedback and save the complete run to MongoDB.

### 2. Nth Recommendation (`/Nth_Recommendation`)

Tests the continuity `POST /api/v1/nth-recommendations` endpoint — used for week 2, 3, etc. of a user's diet plan.

- Set user stats (menu ID, current weight, target weight, goal, step count, plan dates).
- Build a **Weekly Weights History** with individually add/remove-able entries.
- Track **Internal Meals** (ordered via Instameals) and **External Meals** (off-platform), each with optional granular nutrition fields.
- Configure **Previous Recommendations** for up to 3 historical weeks, with their own per-meal lists.
- Shows a request payload inspector in the left panel and a response payload inspector in the right panel.
- Renders product cards from the flat `products[]` response, grouping them by `meal_types[]` and showing a ⭐ badge for `recommended=true` items.
- Displays the backend `reason` text directly on each product card.
- Saves test runs to a **separate** MongoDB collection from the First Recommendation page.

---

## Project Structure

```
instameal-streamlit-dashboard/
├── app.py                          # Entry point — multi-page navigation router
├── pages/
│   ├── 01_first_recommendation.py  # First Recommendation testing UI
│   └── 02_nth_recommendation.py    # Nth Recommendation testing UI
├── shared/
│   ├── config.py                   # Environment variable definitions
│   ├── db.py                       # PostgreSQL (product fetch) & MongoDB (save) queries
│   ├── styles.py                   # Injected CSS — card styles, form entry cards
│   └── components.py               # Shared HTML card builders (build_card_html, etc.)
├── .env                            # Local environment variables (never committed)
├── .env.example                    # Template for required environment variables
├── pyproject.toml                  # Project metadata and dependencies
└── Dockerfile                      # Container build definition
```

---

## Prerequisites

- Python 3.10 or newer
- `uv` installed ([docs](https://docs.astral.sh/uv/))
- Reachable backend API for both endpoints
- Reachable PostgreSQL database (for menu/product rendering)
- Reachable MongoDB database (for test run persistence)

---

## Environment Setup

1. Copy the example env file:

```bash
# macOS / Linux
cp .env.example .env

# Windows
copy .env.example .env
```

2. Fill in all required keys in `.env`:

| Variable                    | Description                                           |
| --------------------------- | ----------------------------------------------------- |
| `DB_HOST`                   | PostgreSQL host                                       |
| `DB_PORT`                   | PostgreSQL port (default: `5432`)                     |
| `DB_NAME`                   | PostgreSQL database name                              |
| `DB_USER`                   | PostgreSQL username                                   |
| `DB_PASSWORD`               | PostgreSQL password                                   |
| `API_URL`                   | First Recommendation endpoint URL                     |
| `NTH_API_URL`               | Nth Recommendation endpoint URL                       |
| `MONGO_URI`                 | MongoDB connection string                             |
| `MONGO_DB_NAME`             | Target MongoDB database name                          |
| `MONGO_COLLECTION_NAME`     | MongoDB collection for First Recommendation test runs |
| `MONGO_NTH_COLLECTION_NAME` | MongoDB collection for Nth Recommendation test runs   |

> **Note**: The two endpoints write to entirely separate MongoDB collections so first-recommendation and nth-recommendation test telemetry never mix.

---

## Run Locally

```bash
uv sync --locked
uv run streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501)

---

## Tester Workflow

### First Recommendation

1. Select the **First Recommendation** page from the sidebar.
2. Fill out the user profile (goal, gender, age, weight, activity level, etc.) and meal quantities.
3. Click **Generate Recommendations**.
4. Review the rendered product cards in the right panel.
5. Enter feedback in the **Tester Feedback** field.
6. Click **Save** — the run is saved to `MONGO_COLLECTION_NAME`.

### Nth Recommendation

1. Select the **Nth Recommendation** page from the sidebar.
2. Fill in the user stats section (menu ID, weights, goal, step count, dates).
3. Add/remove **Weekly Weight** history entries using the `＋ Add` / `− Remove` buttons.
4. Add **Internal Meals** (Instameals orders) and **External Meals** (off-platform) with optional nutrition fields.
5. Enable previous week recommendation blocks and fill in their meal data.
6. Click **Generate Nth Recommendations**.
7. Review product cards grouped by meal type — cards show the recommendation flag, meal-type membership, and the backend reason text.
8. Inspect the request payload in the left-panel JSON expander and the response payload in the right-panel JSON expander.
9. Enter feedback and click **Save Nth Test Run** — saved to `MONGO_NTH_COLLECTION_NAME`.

### Current Nth UI Behavior

- The Nth request form no longer exposes a recommended calorie count input.
- Nutrition inputs for internal, external, and previous-week meals are expanded by default for easier editing.
- Previous recommendations are entered as week-based blocks with add/remove controls for both weeks and meals.
- Products that belong to multiple meal types are shown in each applicable meal section.
- The request timeout is set to 120 seconds to accommodate slower Nth recommendations.

---

## MongoDB Document Schema

Both pages save an identical document structure:

```json
{
  "request_payload": { ... },
  "response_payload": { ... },
  "feedback": "Tester notes here",
  "created_at": "2026-04-14T00:00:00Z"
}
```

The collection used depends on the page:

- **First Recommendation** → `MONGO_COLLECTION_NAME`
- **Nth Recommendation** → `MONGO_NTH_COLLECTION_NAME`

For the Nth page, the stored request payload reflects the current contract:

- `stats` includes `current_weight_kg`, `target_weight_kg`, `goal`, `step_count`, `weekly_weights`, and date fields
- `meal_data.consumed_meal_internal` is an array of meals with optional `nutrition_per_serving`
- `meal_data.consumed_meal_external` is grouped by ordinal week keys such as `1st_week` and `2nd_week`
- `previous_recommendations` is grouped by ordinal week keys and stores meal lists for each enabled week

The response payload stored in MongoDB is the raw backend response, including the flat `products[]` array with `product_id`, `meal_types[]`, `recommended`, and `reason`.

---

## Docker

**Build:**

```bash
docker build -t instameals-ui .
```

**Run:**

```bash
docker run --rm -p 8501:8501 --env-file .env instameals-ui
```

If the API runs on your local machine, update the URLs in `.env` to use `host.docker.internal`:

```env
API_URL=http://host.docker.internal:8001/api/v1/initial-recommendations
NTH_API_URL=http://host.docker.internal:8001/api/v1/nth-recommendations
```

---
