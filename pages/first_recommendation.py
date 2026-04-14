import html
import requests
import streamlit as st

from shared.config import API_URL, MONGO_COLLECTION_NAME
from shared.db import get_all_menu_products, save_test_run_to_mongo
from shared.styles import inject_styles
from shared.components import build_card_html

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
    menu_id = result.get("menu_id")

    st.success(f"Estimated calories per day: {response_data.get('est_calories_per_day', 'Unknown')}")

    recommendations = response_data.get("recommendations", [])
    if not recommendations:
        st.warning("The API returned no recommendations.")

    recommended_map = {}
    for rec in recommendations:
        meal_type_key = rec.get("meal_type", "unknown").lower()
        recommended_map[meal_type_key] = rec.get("products", [])

    all_products = get_all_menu_products(menu_id) if menu_id else []

    products_by_meal = {}
    for prod in all_products:
        for m in prod.get("meal_types", []):
            products_by_meal.setdefault(m, []).append(prod)

    for recommendation in recommendations:
        meal_type = recommendation.get("meal_type", "unknown")
        meal_key = meal_type.lower()
        st.markdown(f'<div class="meal-section"><h3>{meal_type.title()}</h3></div>', unsafe_allow_html=True)

        meal_products = products_by_meal.get(meal_key, [])
        if not meal_products:
            st.warning("No products found in the database for this meal type.")
            continue

        # Sort meal_products so that recommended items appear at the very top
        recommended_ids = recommended_map.get(meal_key, [])
        meal_products.sort(key=lambda p: p["id"] in recommended_ids, reverse=True)

        for start_index in range(0, len(meal_products), 3):
            row_cards = meal_products[start_index : start_index + 3]
            card_columns = st.columns(3, gap="medium")

            for column_index, detail in enumerate(row_cards):
                with card_columns[column_index]:
                    title = html.escape(detail.get("title", "Unknown product"))
                    raw_desc = detail.get("description", "")
                    description = html.escape(raw_desc).replace("\n", "<br>")
                    image_url = html.escape(detail.get("image", ""))
                    nutrition = detail.get("nutrition", {})

                    is_rec = detail["id"] in recommended_map.get(meal_key, [])

                    st.markdown(
                        build_card_html(title, description, image_url, nutrition, is_recommended=is_rec),
                        unsafe_allow_html=True,
                    )

    with st.expander("Raw API response", expanded=False):
        st.json(response_data)


inject_styles()

if "recommendation_result" not in st.session_state:
    st.session_state.recommendation_result = None
if "tester_feedback" not in st.session_state:
    st.session_state.tester_feedback = ""
if "save_status" not in st.session_state:
    st.session_state.save_status = None

st.title("First Recommendation Tester")
st.caption("Test the initial user recommendation endpoints.")

left_panel, right_panel = st.columns([1, 1.25], gap="large")

with left_panel:
    st.header("Request Form")

    with st.form("recommendation_form", clear_on_submit=False):
        profile_panel, meals_panel = st.columns(2, gap="large")

        with profile_panel:
            st.subheader("Profile")
            user_goal_label = st.selectbox(
                "User Goal", list(GOAL_OPTIONS.keys()),
                index=list(GOAL_OPTIONS.values()).index(DEFAULT_REQUEST["user_goal"]),
            )
            gender_label = st.selectbox(
                "Gender", list(GENDER_OPTIONS.keys()),
                index=list(GENDER_OPTIONS.values()).index(DEFAULT_REQUEST["gender"]),
            )
            activity_level_label = st.selectbox(
                "Activity Level", list(ACTIVITY_LEVEL_OPTIONS.keys()),
                index=list(ACTIVITY_LEVEL_OPTIONS.values()).index(DEFAULT_REQUEST["activity_level"]),
            )

            age = st.number_input("Age", min_value=1, max_value=120, value=DEFAULT_REQUEST["age"], step=1)
            height_cm = st.number_input("Height (cm)", min_value=0.0, value=DEFAULT_REQUEST["height_cm"], step=0.1)
            current_weight_kg = st.number_input("Current Weight (kg)", min_value=0.0, value=DEFAULT_REQUEST["current_weight_kg"], step=0.1)
            target_weight_kg = st.number_input("Target Weight (kg)", min_value=0.0, value=DEFAULT_REQUEST["target_weight_kg"], step=0.1)
            menu_id = st.number_input("Menu ID", min_value=1, value=DEFAULT_REQUEST["menu_id"], step=1)
            plan_duration_days = st.number_input("Plan Duration (days)", min_value=1, value=DEFAULT_REQUEST["plan_duration_days"], step=1)

            st.divider()
            st.subheader("Delivery Days")
            days_options = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            selected_days = st.pills("Select Days", options=days_options, default=["Monday", "Tuesday"], selection_mode="multi", label_visibility="collapsed")
            if selected_days is None:
                selected_days = []
            number_of_days = len(selected_days)

        with meals_panel:
            st.subheader("Meals")
            breakfast_qty = st.number_input("Breakfast Qty", min_value=0, value=DEFAULT_REQUEST["meals"]["breakfast"], step=1)
            lunch_qty = st.number_input("Lunch Qty", min_value=0, value=DEFAULT_REQUEST["meals"]["lunch"], step=1)
            dinner_qty = st.number_input("Dinner Qty", min_value=0, value=DEFAULT_REQUEST["meals"]["dinner"], step=1)
            snack_qty = st.number_input("Snack Qty", min_value=0, value=DEFAULT_REQUEST["meals"]["snack"], step=1)
            drink_qty = st.number_input("Drink Qty", min_value=0, value=DEFAULT_REQUEST["meals"]["drink"], step=1)

        def build_meals_request():
            meals_requested = []
            quantities = {"breakfast": breakfast_qty, "lunch": lunch_qty, "dinner": dinner_qty, "snack": snack_qty, "drink": drink_qty}
            for meal_type, quantity in quantities.items():
                if quantity > 0:
                    meals_requested.append({"meal_type": meal_type, "quantity": int(quantity)})
            return meals_requested

        meals_requested = build_meals_request()

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
            "number_of_days": int(number_of_days),
            "meals": meals_requested,
        }
        st.session_state.save_status = None

        if not meals_requested:
            st.session_state.recommendation_result = {
                "error": "Add at least one meal with quantity greater than zero.",
                "response": None,
                "request_payload": payload,
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
                            "menu_id": int(menu_id),
                            "request_payload": payload,
                        }
                    else:
                        st.session_state.recommendation_result = {
                            "error": None,
                            "response": response_data,
                            "menu_id": int(menu_id),
                            "request_payload": payload,
                        }
                except requests.RequestException as exc:
                    st.session_state.recommendation_result = {
                        "error": f"Could not reach the API: {exc}",
                        "response": None,
                        "request_payload": payload,
                    }

    generated_result = st.session_state.recommendation_result
    if bool(generated_result and generated_result.get("request_payload") is not None):
        st.divider()
        st.subheader("Tester Feedback")
        st.text_area("Feedback", key="tester_feedback", placeholder="Share tester feedback...", height=120)

        if st.button("Save", width='stretch'):
            r_payload = generated_result.get("request_payload")
            r_response = generated_result.get("response")
            f_value = st.session_state.tester_feedback.strip()

            if not f_value:
                st.session_state.save_status = {"type": "error", "message": "please add the feedback to save"}
            elif r_payload is None or r_response is None:
                st.session_state.save_status = {"type": "error", "message": "Generate recommendations first"}
            else:
                try:
                    with st.spinner("Saving test run..."):
                        inserted_id = save_test_run_to_mongo(MONGO_COLLECTION_NAME, r_payload, r_response, f_value)
                    st.session_state.save_status = {"type": "success", "message": f"Saved test run to MongoDB (id: {inserted_id})."}
                except Exception as exc:
                    st.session_state.save_status = {"type": "error", "message": f"Could not save: {exc}"}

        stat = st.session_state.save_status
        if stat:
            if stat.get("type") == "success":
                st.success(stat.get("message"))
            else:
                st.error(stat.get("message"))

with right_panel:
    render_recommendation_panel(st.session_state.recommendation_result)
