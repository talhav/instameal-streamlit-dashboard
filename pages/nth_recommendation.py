import html
from collections import defaultdict

import requests
import streamlit as st

from shared.components import build_card_html
from shared.config import (
    MONGO_NTH_REC_FEEDBACK_COLLECTION,
    NTH_REC_API_TIMEOUT_SECONDS,
    NTH_REC_API_URL,
)
from shared.db import get_all_menu_products, get_all_users, save_test_run_to_mongo
from shared.payloads import (
    build_nth_recommendation_payload,
    validate_nth_recommendation_payload,
)
from shared.styles import inject_styles


MEAL_TYPE_ALIASES = {
    "snacks": "snack",
    "drinks": "drink",
    "beverages": "drink",
}
MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack", "drink")
DELIVERY_DAYS = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)
DEFAULT_MENU_ID = 104
DEFAULT_SELECTED_DAYS = ["Monday", "Tuesday", "Wednesday"]


def normalize_meal_type(raw_meal_type):
    meal_type = str(raw_meal_type or "").strip().lower()
    meal_type = meal_type.strip("{}[]()\"'")
    meal_type = " ".join(meal_type.split())
    return MEAL_TYPE_ALIASES.get(meal_type, meal_type)


def assign_products_to_meal_types(all_products, recommended_counts_by_meal):
    """Assign every menu product to one meal section, prioritising API assignments."""
    products_by_meal = defaultdict(list)
    assigned_product_ids = set()

    for meal_type, product_counts in recommended_counts_by_meal.items():
        for product_id in product_counts:
            product = next((p for p in all_products if p.get("id") == product_id), None)
            if product:
                products_by_meal[meal_type].append(product)
                assigned_product_ids.add(product_id)

    non_recommended = [
        product for product in all_products if product.get("id") not in assigned_product_ids
    ]
    multi_meal = []
    single_meal = defaultdict(list)
    no_meal = []

    for product in non_recommended:
        meal_types = [
            normalize_meal_type(meal_type)
            for meal_type in (product.get("meal_types", []) or [])
        ]
        meal_types = [meal_type for meal_type in meal_types if meal_type]
        if len(meal_types) > 1:
            multi_meal.append((product, meal_types))
        elif len(meal_types) == 1:
            single_meal[meal_types[0]].append(product)
        else:
            no_meal.append(product)

    lunch_count = len(products_by_meal.get("lunch", []))
    dinner_count = len(products_by_meal.get("dinner", []))
    for product, meal_types in multi_meal:
        has_lunch = "lunch" in meal_types
        has_dinner = "dinner" in meal_types
        if has_lunch and has_dinner:
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
            products_by_meal[meal_types[0]].append(product)

    for meal_type, products in single_meal.items():
        products_by_meal[meal_type].extend(products)
    if no_meal:
        products_by_meal["not_defined"].extend(no_meal)

    return products_by_meal


def _set_default(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def init_state():
    _set_default("nth_selected_user_id", None)
    _set_default("nth_menu_id", DEFAULT_MENU_ID)
    _set_default("nth_selected_days", DEFAULT_SELECTED_DAYS)
    for meal_type in MEAL_TYPES:
        _set_default(f"nth_meal_qty_{meal_type}", 1)

    _set_default("nth_result", None)
    _set_default("nth_save_status", None)
    _set_default("nth_feedback_rating", None)
    _set_default("nth_feedback_comment", "")


def reset_nth_run_for_user_change():
    """Clear output that belongs to the previously selected user."""
    st.session_state.nth_result = None
    st.session_state.nth_save_status = None
    st.session_state.nth_feedback_rating = None
    st.session_state.nth_feedback_comment = ""
    st.session_state.pop("nth_rating_selector", None)


def render_nth_recommendation_panel(result):
    st.header("Recommendations")

    if not result:
        st.info("Run the Nth Recommendation form on the left.")
        return

    if result.get("error"):
        st.error(result["error"])
        if result.get("response") is not None:
            st.json(result["response"])
        return

    response_data = result.get("response", {})
    menu_id = result.get("menu_id")
    products_from_api = response_data.get("products", [])
    recommended_counts_by_meal = defaultdict(lambda: defaultdict(int))
    recommended_reasons = {}

    invalid_rows = 0
    for item in products_from_api:
        meal_type = normalize_meal_type(item.get("assigned_meal_type", ""))
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        reason = item.get("reason")

        if not meal_type:
            invalid_rows += 1
            continue

        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            invalid_rows += 1
            continue

        if quantity <= 0:
            continue

        recommended_counts_by_meal[meal_type][product_id] += quantity
        if reason:
            recommended_reasons[(meal_type, product_id)] = reason

    if invalid_rows:
        st.warning(f"Skipped {invalid_rows} invalid product rows from API response.")
    if not products_from_api:
        st.warning("The API returned no products.")

    all_products = get_all_menu_products(menu_id) if menu_id else []
    products_by_meal = assign_products_to_meal_types(
        all_products, recommended_counts_by_meal
    )

    meal_order = ["breakfast", "lunch", "dinner", "snack", "drink", "not_defined"]
    extra_meal_types = [
        meal_type
        for meal_type in recommended_counts_by_meal
        if meal_type not in meal_order
    ]

    for meal_type in meal_order + sorted(extra_meal_types):
        meal_products = products_by_meal.get(meal_type, [])
        recommended_counts = recommended_counts_by_meal.get(meal_type, {})
        section_title = (
            "Meal Type Not Defined In the Database"
            if meal_type == "not_defined"
            else meal_type.title()
        )

        st.markdown(
            f'<div class="meal-section"><h3>{section_title}</h3></div>',
            unsafe_allow_html=True,
        )

        if not meal_products:
            if recommended_counts:
                st.info(
                    "Recommendations were returned for this meal type, but no foods "
                    "were found in the database for this meal type and menu ID."
                )
            else:
                st.info(
                    "No recommendations were returned for this meal type, and no "
                    "foods were found in the database for this meal type and menu ID."
                )
            continue

        recommended_cards = []
        non_recommended_cards = []
        for product in meal_products:
            product_id = product.get("id")
            quantity = int(recommended_counts.get(product_id, 0))
            reason = recommended_reasons.get((meal_type, product_id))
            if quantity > 0:
                recommended_cards.extend([(product, True, reason)] * quantity)
            else:
                non_recommended_cards.append((product, False, None))

        for product, is_recommended, reason in (
            recommended_cards + non_recommended_cards
        ):
            product_id = product.get("id")
            title = html.escape(product.get("title", f"Unknown Product #{product_id}"))
            description = html.escape(product.get("description", "")).replace(
                "\n", "<br>"
            )
            image_url = html.escape(product.get("image", ""))
            nutrition = product.get("nutrition", {})
            st.markdown(
                build_card_html(
                    title,
                    description,
                    image_url,
                    nutrition,
                    is_recommended=is_recommended,
                    rank_reasoning=reason,
                ),
                unsafe_allow_html=True,
            )

    with st.expander("Raw API response", expanded=False):
        st.json(response_data)


def render_request_payload_panel(result):
    st.subheader("Request Payload")

    if not result:
        st.info("Generate recommendations to inspect the request payload.")
        return

    with st.expander("Request Payload JSON", expanded=False):
        request_payload = result.get("request_payload")
        if request_payload is None:
            st.info("Request payload is not available.")
        else:
            st.json(request_payload)


def render_response_payload_panel(result):
    st.header("Response Payload")

    if not result:
        st.info("Generate recommendations to inspect the response payload.")
        return

    with st.expander("Response Payload JSON", expanded=False):
        response_payload = result.get("response")
        if response_payload is None:
            st.info("Response payload is not available.")
        else:
            st.json(response_payload)


def render_feedback_panel(result):
    if not result or result.get("request_payload") is None:
        return

    st.subheader("Tester Feedback")
    rating_options = ["Like", "Dislike"]
    current_index = None
    if st.session_state.nth_feedback_rating == "like":
        current_index = 0
    elif st.session_state.nth_feedback_rating == "dislike":
        current_index = 1

    rating_value = st.radio(
        "How was the recommendation?",
        options=rating_options,
        index=current_index,
        horizontal=True,
        key="nth_rating_selector",
        label_visibility="collapsed",
    )
    if rating_value == "Like":
        st.session_state.nth_feedback_rating = "like"
    elif rating_value == "Dislike":
        st.session_state.nth_feedback_rating = "dislike"

    st.text_area(
        "Comments (Optional)",
        key="nth_feedback_comment",
        placeholder="Share additional feedback...",
        height=100,
    )

    if st.button("Save Nth Test Run", use_container_width=True, type="primary"):
        request_payload = result.get("request_payload")
        response_payload = result.get("response")
        rating = st.session_state.nth_feedback_rating
        comment = st.session_state.nth_feedback_comment.strip()

        if rating is None and not comment:
            st.session_state.nth_save_status = {
                "type": "error",
                "message": (
                    "Please select a rating (Like/Dislike) or add a comment to save."
                ),
            }
        elif request_payload is None or response_payload is None:
            st.session_state.nth_save_status = {
                "type": "error",
                "message": "Generate recommendations successfully before saving.",
            }
        else:
            try:
                with st.spinner("Saving to MongoDB..."):
                    inserted_id = save_test_run_to_mongo(
                        MONGO_NTH_REC_FEEDBACK_COLLECTION,
                        request_payload,
                        response_payload,
                        {"rating": rating, "comment": comment},
                    )
                st.session_state.nth_save_status = {
                    "type": "success",
                    "message": f"Saved Nth test run (id: {inserted_id}).",
                }
            except Exception as exc:
                st.session_state.nth_save_status = {
                    "type": "error",
                    "message": f"Could not save: {exc}",
                }

    save_status = st.session_state.nth_save_status
    if save_status:
        if save_status.get("type") == "success":
            st.success(save_status["message"])
        else:
            st.error(save_status["message"])


def call_nth_recommendation_api(payload):
    try:
        response = requests.post(
            NTH_REC_API_URL,
            json=payload,
            timeout=NTH_REC_API_TIMEOUT_SECONDS,
        )
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"detail": response.text}

        if response.status_code != 200:
            return {
                "error": f"API request failed with HTTP {response.status_code}.",
                "response": response_data,
                "menu_id": payload["menu_id"],
                "request_payload": payload,
            }

        return {
            "error": None,
            "response": response_data,
            "menu_id": payload["menu_id"],
            "request_payload": payload,
        }
    except requests.RequestException as exc:
        return {
            "error": f"Could not reach the Nth API: {exc}",
            "response": None,
            "menu_id": payload["menu_id"],
            "request_payload": payload,
        }


inject_styles()
init_state()

st.title("Nth-Recommendation Tester")
st.caption(
    "Test adaptive recommendations using a selected database user and a minimal request."
)

left_panel, right_panel = st.columns([1, 1.25], gap="large")

with left_panel:
    st.header("Request Form")
    st.subheader("Active User")

    users = get_all_users()

    selected_user_id = None
    if not users:
        st.warning("No active users were found in the database.")
    else:
        users_by_id = {int(user["id"]): user for user in users}
        selected_user_id = st.selectbox(
            "Select User by Email",
            options=list(users_by_id),
            format_func=lambda user_id: (
                f"{users_by_id[user_id]['email']} (ID: {user_id})"
            ),
            index=None,
            placeholder="Select an active user",
            key="nth_selected_user_id",
            on_change=reset_nth_run_for_user_change,
        )

        if selected_user_id is not None:
            selected_user = users_by_id[selected_user_id]
            st.caption(
                f"Selected user: {selected_user['name']} · ID {selected_user_id}"
            )

    st.divider()

    menu_meals_column, delivery_column = st.columns(2)
    with menu_meals_column:
        st.subheader("Menu ID")
        st.number_input(
            "Menu ID",
            min_value=1,
            step=1,
            key="nth_menu_id",
            label_visibility="collapsed",
        )
        st.subheader("Meals")
        for meal_type in MEAL_TYPES:
            st.number_input(
                f"{meal_type.title()} Qty",
                min_value=0,
                step=1,
                key=f"nth_meal_qty_{meal_type}",
            )

    with delivery_column:
        st.subheader("Delivery Days")
        selected_days = st.pills(
            "Select Days",
            options=DELIVERY_DAYS,
            selection_mode="multi",
            label_visibility="collapsed",
            key="nth_selected_days",
        )
        selected_days = selected_days or []

    if st.button(
        "Generate Nth Recommendations",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.nth_save_status = None

        if selected_user_id is None:
            st.session_state.nth_result = {
                "error": "Please select an active user before generating recommendations.",
                "response": None,
                "menu_id": st.session_state.nth_menu_id,
                "request_payload": None,
            }
        else:
            meal_quantities = {
                meal_type: st.session_state[f"nth_meal_qty_{meal_type}"]
                for meal_type in MEAL_TYPES
            }
            payload = build_nth_recommendation_payload(
                user_id=selected_user_id,
                menu_id=st.session_state.nth_menu_id,
                selected_days=selected_days,
                meal_quantities=meal_quantities,
            )

            validation_errors = validate_nth_recommendation_payload(payload)

            if validation_errors:
                st.session_state.nth_result = {
                    "error": " ".join(validation_errors),
                    "response": None,
                    "menu_id": payload["menu_id"],
                    "request_payload": payload,
                }
            else:
                with st.spinner("Calling Nth Endpoint..."):
                    st.session_state.nth_result = call_nth_recommendation_api(
                        payload
                    )

    st.divider()
    render_request_payload_panel(st.session_state.nth_result)
    render_feedback_panel(st.session_state.nth_result)

with right_panel:
    render_nth_recommendation_panel(st.session_state.nth_result)
    st.divider()
    render_response_payload_panel(st.session_state.nth_result)
