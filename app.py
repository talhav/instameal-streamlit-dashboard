import html
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

DEFAULT_REQUEST = {
    "user_goal": "weight_gain",
    "gender": "male",
    "age": 30,
    "height_cm": 180.0,
    "current_weight_kg": 80.0,
    "target_weight_kg": 90.0,
    "activity_level": "physical_intense_work",
    "menu_id": 91,
    "plan_duration_days": 28,
    "meals": {
        "breakfast": 1,
        "lunch": 1,
        "dinner": 3,
        "snack": 0,
        "drink": 1,
    },
}


def inject_styles():
    st.markdown(
        """
        <style>
        .reco-card {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 18px;
            overflow: hidden;
            background: linear-gradient(180deg, rgba(20, 24, 33, 0.98), rgba(14, 18, 24, 0.98));
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.18);
            margin-bottom: 16px;
        }

        .reco-card-image img {
            width: 100%;
            height: 150px;
            object-fit: cover;
            display: block;
        }

        .reco-card-body {
            padding: 16px 16px 18px 16px;
        }

        .reco-card-title {
            font-size: 1.1rem;
            font-weight: 700;
            line-height: 1.35;
            margin: 0 0 8px 0;
            color: #f3f5f7;
        }

        .reco-card-description {
            font-size: 0.92rem;
            line-height: 1.5;
            color: rgba(243, 245, 247, 0.78);
            margin: 0;
        }

        .meal-section {
            margin-top: 20px;
            margin-bottom: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        }

        .meal-section h3 {
            margin-bottom: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
            f"SELECT id, title, description, image FROM products WHERE id IN ({placeholders})",
            tuple(product_ids),
        )

        db_results = {
            row[0]: {
                "title": row[1] or "Unknown title",
                "description": row[2] or "",
                "image": row[3] or "",
            }
            for row in cursor.fetchall()
        }
        ordered_results = [
            {"id": product_id, **db_results.get(product_id, {})}
            for product_id in product_ids
        ]

        cursor.close()
        connection.close()
        return ordered_results
    except Exception:
        return [
            {"id": product_id, "title": "DB Connection Error", "description": "", "image": ""}
            for product_id in product_ids
        ]


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

        st.markdown(f'<div class="meal-section"><h3>{meal_type.title()}</h3></div>', unsafe_allow_html=True)
        if not product_ids:
            st.warning("Empty result set for this meal.")
            continue

        product_details = get_product_details(product_ids)
        for start_index in range(0, len(product_details), 3):
            row_cards = product_details[start_index : start_index + 3]
            card_columns = st.columns(3, gap="medium")

            for column_index, detail in enumerate(row_cards):
                with card_columns[column_index]:
                    title = html.escape(detail.get("title", "Unknown product"))
                    description = html.escape(detail.get("description", "")).replace("\n", "<br>")
                    image_url = html.escape(detail.get("image", ""))

                    st.markdown('<div class="reco-card">', unsafe_allow_html=True)
                    if image_url:
                        st.markdown(
                            f'<div class="reco-card-image"><img src="{image_url}" alt="{title}" /></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            '<div class="reco-card-image"><div style="height:150px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.04);color:rgba(255,255,255,0.45);font-weight:600;">No image available</div></div>',
                            unsafe_allow_html=True,
                        )

                    st.markdown(
                        f'''
                        <div class="reco-card-body">
                            <div class="reco-card-title">{title}</div>
                            <p class="reco-card-description">{description}</p>
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Raw API response", expanded=False):
        st.json(response_data)


st.set_page_config(page_title="Instameals RecSys UI", layout="wide")
inject_styles()

if "recommendation_result" not in st.session_state:
    st.session_state.recommendation_result = None


st.title("Instameals Recommendation Engine Tester")
st.caption("Left panel collects exact enum values; right panel renders the response and product details.")

left_panel, right_panel = st.columns([1, 1.25], gap="large")

with left_panel:
    st.header("Request Form")

    with st.form("recommendation_form", clear_on_submit=False):
        profile_panel, meals_panel = st.columns(2, gap="large")

        with profile_panel:
            st.subheader("Profile")
            user_goal_label = st.selectbox(
                "User Goal",
                list(GOAL_OPTIONS.keys()),
                index=list(GOAL_OPTIONS.values()).index(DEFAULT_REQUEST["user_goal"]),
            )
            gender_label = st.selectbox(
                "Gender",
                list(GENDER_OPTIONS.keys()),
                index=list(GENDER_OPTIONS.values()).index(DEFAULT_REQUEST["gender"]),
            )
            activity_level_label = st.selectbox(
                "Activity Level",
                list(ACTIVITY_LEVEL_OPTIONS.keys()),
                index=list(ACTIVITY_LEVEL_OPTIONS.values()).index(DEFAULT_REQUEST["activity_level"]),
            )

            age = st.number_input("Age", min_value=1, max_value=120, value=DEFAULT_REQUEST["age"], step=1)
            height_cm = st.number_input("Height (cm)", min_value=0.0, value=DEFAULT_REQUEST["height_cm"], step=0.1)
            current_weight_kg = st.number_input(
                "Current Weight (kg)",
                min_value=0.0,
                value=DEFAULT_REQUEST["current_weight_kg"],
                step=0.1,
            )
            target_weight_kg = st.number_input(
                "Target Weight (kg)",
                min_value=0.0,
                value=DEFAULT_REQUEST["target_weight_kg"],
                step=0.1,
            )
            menu_id = st.number_input("Menu ID", min_value=1, value=DEFAULT_REQUEST["menu_id"], step=1)
            plan_duration_days = st.number_input(
                "Plan Duration (days)",
                min_value=1,
                value=DEFAULT_REQUEST["plan_duration_days"],
                step=1,
            )

        with meals_panel:
            st.subheader("Meals")
            st.caption("Enter quantities for each meal type.")
            breakfast_qty = st.number_input(
                "Breakfast Qty", min_value=0, value=DEFAULT_REQUEST["meals"]["breakfast"], step=1
            )
            lunch_qty = st.number_input(
                "Lunch Qty", min_value=0, value=DEFAULT_REQUEST["meals"]["lunch"], step=1
            )
            dinner_qty = st.number_input(
                "Dinner Qty", min_value=0, value=DEFAULT_REQUEST["meals"]["dinner"], step=1
            )
            snack_qty = st.number_input(
                "Snack Qty", min_value=0, value=DEFAULT_REQUEST["meals"]["snack"], step=1
            )
            drink_qty = st.number_input(
                "Drink Qty", min_value=0, value=DEFAULT_REQUEST["meals"]["drink"], step=1
            )

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
                    "plan_duration_days": int(plan_duration_days),
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
            "plan_duration_days": int(plan_duration_days),
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
