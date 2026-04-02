import os

import psycopg2
import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


API_URL = os.getenv("API_URL")
DEFAULT_DB_NAME = os.getenv("DB_NAME")
DEFAULT_DB_USER = os.getenv("DB_USER")
DEFAULT_DB_PASSWORD = os.getenv("DB_PASSWORD")
DEFAULT_DB_HOST = os.getenv("DB_HOST")
DEFAULT_DB_PORT = os.getenv("DB_PORT")

GOAL_OPTIONS = {
    "Weight loss": "weight_loss",
    "Weight gain": "weight_gain",
    "Maintenance": "maintenance",
}
GENDER_OPTIONS = {
    "Male": "male",
    "Female": "female",
}
ACTIVITY_LEVEL_OPTIONS = {
    "Mostly sitting": "mostly_sitting",
    "Often standing": "often_standing",
    "Regular walking": "regular_walking",
    "Physical intense work": "physical_intense_work",
}


def get_product_details(product_ids):
    if not product_ids:
        return []

    try:
        connection = psycopg2.connect(
            dbname=DEFAULT_DB_NAME,
            user=DEFAULT_DB_USER,
            password=DEFAULT_DB_PASSWORD,
            host=DEFAULT_DB_HOST,
            port=DEFAULT_DB_PORT,
        )
        cursor = connection.cursor()

        placeholders = ",".join(["%s"] * len(product_ids))
        cursor.execute(
            f"SELECT id, title, kcal FROM products WHERE id IN ({placeholders})",
            tuple(product_ids),
        )

        db_results = {row[0]: f"{row[1]} ({row[2]} Kcal)" for row in cursor.fetchall()}
        ordered_results = [
            f"ID: {product_id} | {db_results.get(product_id, 'Unknown')}"
            for product_id in product_ids
        ]

        cursor.close()
        connection.close()
        return ordered_results
    except Exception:
        return [f"ID {product_id} (DB Connection Error)" for product_id in product_ids]


def build_meals_request():
    meals_requested = []

    quantities = {
        "breakfast": breakfast_qty,
        "lunch": lunch_qty,
        "dinner": dinner_qty,
        "snack": snack_qty,
        "drink": drink_qty,
    }

    for meal_type, quantity in quantities.items():
        if quantity > 0:
            meals_requested.append({"meal_type": meal_type, "quantity": int(quantity)})

    return meals_requested


def render_recommendation_panel(result):
    st.header("Recommendations")

    if not result:
        st.info("Run the form on the left to generate recommendations.")
        return

    if result.get("error"):
        st.error(result["error"])
        if result.get("response") is not None:
            st.json(result["response"])
        return

    response_data = result.get("response", {})
    st.success(
        f"Estimated calories per day: {response_data.get('est_calories_per_day', 'Unknown')}"
    )

    recommendations = response_data.get("recommendations", [])
    if not recommendations:
        st.warning("The API returned no recommendations.")

    for recommendation in recommendations:
        meal_type = recommendation.get("meal_type", "unknown")
        product_ids = recommendation.get("products", [])

        st.subheader(f"{meal_type.title()}")
        if not product_ids:
            st.warning("Empty result set for this meal.")
            continue

        for detail in get_product_details(product_ids):
            st.write(f"- {detail}")

    with st.expander("Raw API response", expanded=False):
        st.json(response_data)


st.set_page_config(page_title="Instameals RecSys UI", layout="wide")

if "recommendation_result" not in st.session_state:
    st.session_state.recommendation_result = None


st.title("Instameals Recommendation Engine Tester")
st.caption("Left panel collects exact enum values; right panel renders the response and product details.")

left_panel, right_panel = st.columns([1, 1.25], gap="large")

with left_panel:
    st.header("Request Form")

    with st.form("recommendation_form", clear_on_submit=False):
        user_goal_label = st.selectbox("User Goal", list(GOAL_OPTIONS.keys()))
        gender_label = st.selectbox("Gender", list(GENDER_OPTIONS.keys()))
        activity_level_label = st.selectbox("Activity Level", list(ACTIVITY_LEVEL_OPTIONS.keys()))

        age = st.number_input("Age", min_value=1, max_value=120, value=30, step=1)
        height_cm = st.number_input("Height (cm)", min_value=0.0, value=180.0, step=0.1)
        current_weight_kg = st.number_input("Current Weight (kg)", min_value=0.0, value=80.0, step=0.1)
        target_weight_kg = st.number_input("Target Weight (kg)", min_value=0.0, value=90.0, step=0.1)
        menu_id = st.number_input("Menu ID", min_value=1, value=91, step=1)

        st.subheader("Meals")
        meal_cols = st.columns(5)
        with meal_cols[0]:
            breakfast_qty = st.number_input("Breakfast Qty", min_value=0, value=1, step=1)
        with meal_cols[1]:
            lunch_qty = st.number_input("Lunch Qty", min_value=0, value=1, step=1)
        with meal_cols[2]:
            dinner_qty = st.number_input("Dinner Qty", min_value=0, value=2, step=1)
        with meal_cols[3]:
            snack_qty = st.number_input("Snack Qty", min_value=0, value=0, step=1)
        with meal_cols[4]:
            drink_qty = st.number_input("Drink Qty", min_value=0, value=2, step=1)

        meals_requested = build_meals_request()

        with st.expander("Payload preview", expanded=False):
            st.json(
                {
                    "user_goal": GOAL_OPTIONS[user_goal_label],
                    "gender": GENDER_OPTIONS[gender_label],
                    "age": int(age),
                    "height_cm": float(height_cm),
                    "current_weight_kg": float(current_weight_kg),
                    "target_weight_kg": float(target_weight_kg),
                    "activity_level": ACTIVITY_LEVEL_OPTIONS[activity_level_label],
                    "menu_id": int(menu_id),
                    "meals": meals_requested,
                }
            )

        submitted = st.form_submit_button("Generate Recommendations", type="primary")

    if submitted:
        payload = {
            "user_goal": GOAL_OPTIONS[user_goal_label],
            "gender": GENDER_OPTIONS[gender_label],
            "age": int(age),
            "height_cm": float(height_cm),
            "current_weight_kg": float(current_weight_kg),
            "target_weight_kg": float(target_weight_kg),
            "activity_level": ACTIVITY_LEVEL_OPTIONS[activity_level_label],
            "menu_id": int(menu_id),
            "meals": meals_requested,
        }

        if not meals_requested:
            st.session_state.recommendation_result = {
                "error": "Add at least one meal with quantity greater than zero.",
                "response": None,
            }
        else:
            with st.spinner("Calculating recommendations..."):
                try:
                    response = requests.post(API_URL, json=payload, timeout=60)
                    try:
                        response_data = response.json()
                    except ValueError:
                        response_data = {"detail": response.text}

                    if response.status_code != 200:
                        st.session_state.recommendation_result = {
                            "error": f"API request failed with HTTP {response.status_code}.",
                            "response": response_data,
                        }
                    else:
                        st.session_state.recommendation_result = {
                            "error": None,
                            "response": response_data,
                        }
                except requests.RequestException as exc:
                    st.session_state.recommendation_result = {
                        "error": f"Could not reach the API: {exc}",
                        "response": None,
                    }

with right_panel:
    render_recommendation_panel(st.session_state.recommendation_result)