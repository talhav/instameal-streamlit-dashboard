import html
from collections import defaultdict
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

MEAL_TYPE_ALIASES = {
    "snacks": "snack",
    "drinks": "drink",
    "beverages": "drink",
}


def normalize_meal_type(raw_meal_type):
    meal_type = str(raw_meal_type or "").strip().lower()
    meal_type = meal_type.strip("{}[]()\"'")
    meal_type = " ".join(meal_type.split())
    return MEAL_TYPE_ALIASES.get(meal_type, meal_type)

DEFAULT_REQUEST = {
    "user_goal": "weight_loss",
    "gender": "male",
    "age": 25,
    "height_cm": 180.0,
    "current_weight_kg": 80.0,
    "target_weight_kg": 75.0,
    "plan_duration_days": 30,
    "number_of_days": 5,
    "activity_level": "regular_walking",
    "menu_id": 104,
    "meals": [
        {"meal_type": "breakfast", "quantity": 1},
        {"meal_type": "lunch", "quantity": 1},
        {"meal_type": "dinner", "quantity": 1},
        {"meal_type": "snack", "quantity": 1},
        {"meal_type": "drink", "quantity": 1}
    ]
}

def get_default_meal_quantity(meal_type):
    """Get the default quantity for a meal type from DEFAULT_REQUEST."""
    for meal in DEFAULT_REQUEST.get("meals", []):
        if meal.get("meal_type") == meal_type:
            return meal.get("quantity", 0)
    return 0


def assign_products_to_meal_types(all_products, recommended_counts_by_meal):
    """
    Assign each product to exactly ONE meal_type.

    Priority order:
    1. If product is API-recommended, assign to that meal_type
    2. If product has multiple meal_types and is NOT recommended, intelligently
       balance between lunch and dinner to achieve equal counts
    3. If product has single meal_type, assign to that type

    Returns:
        dict: {meal_type: [products]} where each product appears exactly once
    """
    products_by_meal = defaultdict(list)
    assigned_product_ids = set()

    # Step 1: Assign API-recommended products to their specified meal_type
    for meal_type, product_counts in recommended_counts_by_meal.items():
        for product_id in product_counts.keys():
            # Find the product in all_products
            product = next((p for p in all_products if p.get("id") == product_id), None)
            if product:
                products_by_meal[meal_type].append(product)
                assigned_product_ids.add(product_id)

    # Step 2: Process remaining non-recommended products
    non_recommended_products = [p for p in all_products if p.get("id") not in assigned_product_ids]

    # Separate products with multiple meal_types vs. single meal_type vs. no meal_type
    multi_meal_products = []
    single_meal_products = defaultdict(list)
    no_meal_type_products = []

    for product in non_recommended_products:
        meal_types = [normalize_meal_type(mt) for mt in (product.get("meal_types", []) or [])]
        meal_types = [mt for mt in meal_types if mt]  # Remove empty strings

        if len(meal_types) > 1:
            multi_meal_products.append((product, meal_types))
        elif len(meal_types) == 1:
            single_meal_products[meal_types[0]].append(product)
        else:
            # Product has no meal_type defined
            no_meal_type_products.append(product)

    # Step 3: Balance multi-meal-type products between lunch and dinner
    # Goal: achieve roughly equal counts in lunch and dinner sections
    if multi_meal_products:
        lunch_count = len(products_by_meal.get("lunch", []))
        dinner_count = len(products_by_meal.get("dinner", []))

        for idx, (product, meal_types) in enumerate(multi_meal_products):
            # Check if both lunch and dinner are in the meal_types
            has_lunch = "lunch" in meal_types
            has_dinner = "dinner" in meal_types

            if has_lunch and has_dinner:
                # Assign to the meal_type with fewer products to balance
                if lunch_count <= dinner_count:
                    products_by_meal["lunch"].append(product)
                    lunch_count += 1
                else:
                    products_by_meal["dinner"].append(product)
                    dinner_count += 1
            elif has_lunch:
                products_by_meal["lunch"].append(product)
                lunch_count += 1
            elif has_dinner:
                products_by_meal["dinner"].append(product)
                dinner_count += 1
            else:
                # Neither lunch nor dinner, assign to first available meal_type
                first_meal = meal_types[0] if meal_types else None
                if first_meal:
                    products_by_meal[first_meal].append(product)

    # Step 4: Assign single-meal-type products
    for meal_type, products in single_meal_products.items():
        products_by_meal[meal_type].extend(products)

    # Step 5: Assign products with no meal_type defined
    if no_meal_type_products:
        products_by_meal["not_defined"].extend(no_meal_type_products)

    return products_by_meal


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

    # New response contract: recommendations is a flat list of
    # {"product_id": int, "quantity": int, "meal_type": str}.
    recommended_counts_by_meal = defaultdict(lambda: defaultdict(int))
    invalid_recommendation_rows = 0
    for row in recommendations:
        meal_type = normalize_meal_type(row.get("meal_type", ""))
        product_id = row.get("product_id")
        quantity = row.get("quantity", 0)

        if not meal_type:
            invalid_recommendation_rows += 1
            continue

        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            invalid_recommendation_rows += 1
            continue

        if quantity <= 0:
            continue

        recommended_counts_by_meal[meal_type][product_id] += quantity

    if invalid_recommendation_rows:
        st.warning(f"Skipped {invalid_recommendation_rows} invalid recommendation rows from API response.")

    all_products = get_all_menu_products(menu_id) if menu_id else []

    # Use new deduplication logic that assigns each product to exactly one meal_type
    products_by_meal = assign_products_to_meal_types(all_products, recommended_counts_by_meal)

    meal_order = ["breakfast", "lunch", "dinner", "snack", "drink", "not_defined"]
    response_meal_types = [meal for meal in recommended_counts_by_meal.keys() if meal not in meal_order]
    meal_types_to_render = meal_order + sorted(response_meal_types)

    for meal_type in meal_types_to_render:
        meal_products = products_by_meal.get(meal_type, [])
        recommended_counts = recommended_counts_by_meal.get(meal_type, {})

        # Format the section title
        if meal_type == "not_defined":
            section_title = "Meal Type Not Defined In the Database"
        else:
            section_title = meal_type.title()

        st.markdown(f'<div class="meal-section"><h3>{section_title}</h3></div>', unsafe_allow_html=True)

        if not meal_products:
            if not recommended_counts:
                st.info(
                    "No recommendations were returned for this meal type, and no foods were found in the database for this meal type and menu ID."
                )
            else:
                st.info(
                    "Recommendations were returned for this meal type, but no foods were found in the database for this meal type and menu ID."
                )
            continue

        recommended_cards = []
        non_recommended_cards = []
        for product in meal_products:
            product_id = product.get("id")
            qty = int(recommended_counts.get(product_id, 0))
            if qty > 0:
                recommended_cards.extend([(product, True)] * qty)
            else:
                non_recommended_cards.append((product, False))

        meal_cards = recommended_cards + non_recommended_cards

        for product, is_recommended in meal_cards:
            product_id = product.get("id")
            title = html.escape(product.get("title", f"Unknown Product #{product_id}"))
            raw_desc = product.get("description", "")
            description = html.escape(raw_desc).replace("\n", "<br>")
            image_url = html.escape(product.get("image", ""))
            nutrition = product.get("nutrition", {})

            st.markdown(
                build_card_html(title, description, image_url, nutrition, is_recommended=is_recommended),
                unsafe_allow_html=True,
            )

    with st.expander("Raw API response", expanded=False):
        st.json(response_data)


inject_styles()

if "recommendation_result" not in st.session_state:
    st.session_state.recommendation_result = None
if "tester_feedback_rating" not in st.session_state:
    st.session_state.tester_feedback_rating = None
if "tester_feedback_comment" not in st.session_state:
    st.session_state.tester_feedback_comment = ""
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
            breakfast_qty = st.number_input("Breakfast Qty", min_value=0, value=get_default_meal_quantity("breakfast"), step=1)
            lunch_qty = st.number_input("Lunch Qty", min_value=0, value=get_default_meal_quantity("lunch"), step=1)
            dinner_qty = st.number_input("Dinner Qty", min_value=0, value=get_default_meal_quantity("dinner"), step=1)
            snack_qty = st.number_input("Snack Qty", min_value=0, value=get_default_meal_quantity("snack"), step=1)
            drink_qty = st.number_input("Drink Qty", min_value=0, value=get_default_meal_quantity("drink"), step=1)

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

        # Thumbs rating buttons with visual selection state
        rating_options = ["👍 Like", "👎 Dislike"]

        # Determine current selection index
        current_index = None
        if st.session_state.tester_feedback_rating == "like":
            current_index = 0
        elif st.session_state.tester_feedback_rating == "dislike":
            current_index = 1

        rating_value = st.radio(
            "How was the recommendation?",
            options=rating_options,
            index=current_index,
            horizontal=True,
            key="rating_selector",
            label_visibility="collapsed"
        )

        # Update session state based on selection
        if rating_value == "👍 Like":
            st.session_state.tester_feedback_rating = "like"
        elif rating_value == "👎 Dislike":
            st.session_state.tester_feedback_rating = "dislike"

        # Optional comment field
        st.text_area(
            "Comments (Optional)",
            key="tester_feedback_comment",
            placeholder="Share additional feedback...",
            height=100
        )

        if st.button("Save", width='stretch', type="primary"):
            r_payload = generated_result.get("request_payload")
            r_response = generated_result.get("response")
            rating = st.session_state.tester_feedback_rating
            comment = st.session_state.tester_feedback_comment.strip()

            # Validation: require either rating or comment
            if rating is None and not comment:
                st.session_state.save_status = {
                    "type": "error",
                    "message": "Please select a rating (👍/👎) or add a comment to save."
                }
            elif r_payload is None or r_response is None:
                st.session_state.save_status = {
                    "type": "error",
                    "message": "Generate recommendations first."
                }
            else:
                try:
                    with st.spinner("Saving test run..."):
                        # Build structured feedback dict
                        feedback_dict = {
                            "rating": rating,
                            "comment": comment
                        }
                        inserted_id = save_test_run_to_mongo(
                            MONGO_COLLECTION_NAME,
                            r_payload,
                            r_response,
                            feedback_dict
                        )
                    st.session_state.save_status = {
                        "type": "success",
                        "message": f"Saved test run to MongoDB (id: {inserted_id})."
                    }
                except Exception as exc:
                    st.session_state.save_status = {
                        "type": "error",
                        "message": f"Could not save: {exc}"
                    }

        stat = st.session_state.save_status
        if stat:
            if stat.get("type") == "success":
                st.success(stat.get("message"))
            else:
                st.error(stat.get("message"))

        with st.expander("Request payload", expanded=False):
            st.json(generated_result.get("request_payload"))

with right_panel:
    render_recommendation_panel(st.session_state.recommendation_result)
