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

- Select an active user directly from the PostgreSQL-backed dropdown.
- Enter a menu ID and configure meal quantities and delivery days.
- Send the minimal request contract; the recommendation service loads user history from its database using `user_id`.
- Shows a request payload inspector in the left panel and a response payload inspector in the right panel.
- Renders product cards from the flat `products[]` response, grouped by `assigned_meal_type`.
- Displays the backend `reason` text directly on each product card.
- Saves test runs to a **separate** MongoDB collection from the First Recommendation page.

---

## Project Structure

```
instameal-streamlit-dashboard/
├── app.py                          # Entry point — multi-page navigation router
├── pages/
│   ├── first_recommendation.py     # First Recommendation testing UI
│   └── nth_recommendation.py       # Nth Recommendation testing UI
├── shared/
│   ├── config.py                   # Environment variable definitions
│   ├── db.py                       # Read-only PostgreSQL fetches & MongoDB saves
│   ├── payloads.py                 # Minimal request payload builders
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
| `NTH_REC_API_URL`               | Nth Recommendation endpoint URL                       |
| `NTH_REC_API_TIMEOUT_SECONDS`   | Nth API timeout in seconds (default: `300`)            |
| `MONGO_URI`                 | MongoDB connection string                             |
| `MONGO_DB_NAME`             | Target MongoDB database name                          |
| `MONGO_FIRST_REC_FEEDBACK_COLLECTION`     | MongoDB collection for First Recommendation test runs |
| `MONGO_NTH_REC_FEEDBACK_COLLECTION` | MongoDB collection for Nth Recommendation test runs   |

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
6. Click **Save** — the run is saved to `MONGO_FIRST_REC_FEEDBACK_COLLECTION`.

### Nth Recommendation

1. Select the **Nth Recommendation** page from the sidebar.
2. Select an active user from the PostgreSQL-backed email dropdown.
3. Enter the menu ID, choose delivery days, and set the per-day meal quantities.
4. Click **Generate Nth Recommendations**.
5. Review product cards grouped by meal type, including the backend reason text.
6. Inspect the request payload in the left-panel JSON expander and the response payload in the right-panel JSON expander.
7. Enter feedback and click **Save Nth Test Run** — saved to `MONGO_NTH_REC_FEEDBACK_COLLECTION`.

### Current Nth UI Behavior

- The request controls stay hidden until the tester explicitly selects an active user.
- The user dropdown is populated directly from `public.users` where `deleted_at IS NULL`; no user-data GET endpoint is called.
- PostgreSQL reads reuse a bounded, read-only connection pool to avoid repeated remote connection handshakes.
- The request contains only `user_id`, `menu_id`, `number_of_days`, and `meals`.
- `number_of_days` is derived from the selected delivery-day pills.
- Meal types with a quantity of zero are omitted from the request.
- The request timeout defaults to 300 seconds to accommodate the LLM-backed Nth recommendation call.

### Pre-filled Default Values

Once a user is selected, the form loads with the following defaults — all of which the tester can freely adjust before hitting **Generate Nth Recommendations**:

| Field | Default Value |
| --------------------- | ------------------------------------ |
| **Menu ID** | `104` |
| **Breakfast Qty** | `1` |
| **Lunch Qty** | `1` |
| **Dinner Qty** | `1` |
| **Snack Qty** | `1` |
| **Drink Qty** | `1` |
| **Delivery Days** | `Monday`, `Tuesday`, `Wednesday` (3) |

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

- **First Recommendation** → `MONGO_FIRST_REC_FEEDBACK_COLLECTION`
- **Nth Recommendation** → `MONGO_NTH_REC_FEEDBACK_COLLECTION`

For the Nth page, the stored request payload reflects the current contract:

- `user_id` identifies the user whose history the recommendation service loads.
- `menu_id` identifies the active menu.
- `number_of_days` is the selected delivery-day count.
- `meals` contains only positive-quantity meal requests.

The response payload stored in MongoDB is the raw backend response, including the flat `products[]` array with `product_id`, `assigned_meal_type`, `quantity`, and `reason`.

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
NTH_REC_API_URL=http://host.docker.internal:8001/api/v1/nth-recommendations
```

---
