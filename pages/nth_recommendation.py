import html
import requests
import streamlit as st

from shared.config import NTH_API_URL, MONGO_NTH_COLLECTION_NAME
from shared.db import get_all_menu_products, save_test_run_to_mongo
from shared.styles import inject_styles
from shared.components import build_card_html


# ── Helpers ──────────────────────────────────────────────────────────────────

def _default(key, value):
    """Set key in session_state only if it has not been set yet."""
    if key not in st.session_state:
        st.session_state[key] = value


def _ordinal_week_key(week_number):
    if 10 <= (week_number % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(week_number % 10, "th")
    return f"{week_number}{suffix}_week"


def _week_display_label(week_number):
    if 10 <= (week_number % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(week_number % 10, "th")
    return f"{week_number}{suffix} Week"


def _parse_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _nutrition_payload(calories, carbs, fat, protein):
    nutrition = {
        "calories_kcal": _parse_float(calories),
        "carbs_g": _parse_float(carbs),
        "fat_g": _parse_float(fat),
        "protein_g": _parse_float(protein),
    }
    if any(value is not None for value in nutrition.values()):
        return nutrition
    return None


def init_state():
    # ── Stats ──
    _default("nth_menu_id", 1)
    _default("nth_current_weight", 76.4)
    _default("nth_target_weight", 70.0)
    _default("nth_goal", "weight_loss")
    _default("nth_step_count", 9250)
    _default("nth_plan_start", "2024-03-01")
    _default("nth_plan_end", "2024-06-01")
    _default("nth_current_date", "2024-04-05")

    # ── Weekly Weights ──
    _default("nth_ww_count", 5)
    _default("nth_ww_date_0", "2024-03-01")
    _default("nth_ww_weight_0", 80.0)
    _default("nth_ww_date_1", "2024-03-08")
    _default("nth_ww_weight_1", 79.1)
    _default("nth_ww_date_2", "2024-03-15")
    _default("nth_ww_weight_2", 78.3)
    _default("nth_ww_date_3", "2024-03-22")
    _default("nth_ww_weight_3", 77.5)
    _default("nth_ww_date_4", "2024-03-29")
    _default("nth_ww_weight_4", 76.4)

    # ── Internal Meals ──
    internal_meals = [
        {
            "title": "Grilled Lemon Herb Chicken Bowl",
            "calories": 480.0,
            "description": "Lunch on Monday, feeling full.",
            "nutrition": {"calories": 480.0, "carbs": 45.0, "fat": 12.0, "protein": 42.0},
        },
        {
            "title": "Teriyaki Salmon with Quinoa",
            "calories": 610.0,
            "description": "Dinner on Monday.",
            "nutrition": {"calories": 610.0, "carbs": 50.5, "fat": 22.0, "protein": 38.0},
        },
        {
            "title": "Classic Whey Protein Shake",
            "calories": 250.0,
            "description": "Post-workout drink on Tuesday.",
            "nutrition": {"calories": 250.0, "carbs": 8.0, "fat": 3.5, "protein": 30.0},
        },
        {
            "title": "Vegan Lentil Stew",
            "calories": 380.0,
            "description": "Lunch on Tuesday.",
            "nutrition": {"calories": 380.0, "carbs": 55.0, "fat": 6.0, "protein": 18.0},
        },
        {
            "title": "Spicy Turkey Meatballs",
            "calories": 450.0,
            "description": "Dinner on Wednesday, highly rated.",
            "nutrition": {"calories": 450.0, "carbs": 30.0, "fat": 16.0, "protein": 35.0},
        },
    ]
    _default("nth_int_count", len(internal_meals))
    for idx, meal in enumerate(internal_meals):
        _default(f"nth_int_title_{idx}", meal["title"])
        _default(f"nth_int_cal_{idx}", meal["calories"])
        _default(f"nth_int_desc_{idx}", meal["description"])
        _default(f"nth_int_ncal_{idx}", meal["nutrition"]["calories"])
        _default(f"nth_int_ncarbs_{idx}", meal["nutrition"]["carbs"])
        _default(f"nth_int_nfat_{idx}", meal["nutrition"]["fat"])
        _default(f"nth_int_nprot_{idx}", meal["nutrition"]["protein"])

    # ── External Meals ──
    external_weeks = [
        [
            {
                "title": "Starbucks Black Coffee",
                "calories": 5.0,
                "description": "Morning coffee.",
                "nutrition": {"calories": 5.0, "carbs": 1.0, "fat": 0.0, "protein": 0.0},
            },
            {
                "title": "Homemade Oats with Banana",
                "calories": 390.0,
                "description": "Breakfast at home, week 1.",
                "nutrition": {"calories": 390.0, "carbs": 68.0, "fat": 5.0, "protein": 10.0},
            },
        ],
        [
            {
                "title": "Office Birthday Cake Slice",
                "calories": 350.0,
                "description": "Couldn't resist at Dave's birthday.",
                "nutrition": {"calories": 350.0, "carbs": 40.0, "fat": 18.0, "protein": 4.0},
            },
            {
                "title": "Restaurant Grilled Sea Bass",
                "calories": 520.0,
                "description": "Dinner out at a restaurant, week 2.",
                "nutrition": {"calories": 520.0, "carbs": 10.0, "fat": 20.0, "protein": 48.0},
            },
        ],
        [
            {
                "title": "Large Green Apple",
                "calories": 116.0,
                "description": "Snack during Wednesday commute.",
                "nutrition": {"calories": 116.0, "carbs": 30.8, "fat": 0.4, "protein": 0.6},
            },
            {
                "title": "Takeaway Chicken Shawarma",
                "calories": 670.0,
                "description": "Dinner takeaway, week 3. Slightly over budget.",
                "nutrition": {"calories": 670.0, "carbs": 58.0, "fat": 28.0, "protein": 38.0},
            },
        ],
    ]
    _default("nth_ext_week_count", len(external_weeks))
    for week_idx, meals in enumerate(external_weeks):
        _default(f"nth_ext_meal_count_{week_idx}", len(meals))
        for meal_idx, meal in enumerate(meals):
            _default(f"nth_ext_title_{week_idx}_{meal_idx}", meal["title"])
            _default(f"nth_ext_cal_{week_idx}_{meal_idx}", meal["calories"])
            _default(f"nth_ext_desc_{week_idx}_{meal_idx}", meal["description"])
            _default(f"nth_ext_ncal_{week_idx}_{meal_idx}", meal["nutrition"]["calories"])
            _default(f"nth_ext_ncarbs_{week_idx}_{meal_idx}", meal["nutrition"]["carbs"])
            _default(f"nth_ext_nfat_{week_idx}_{meal_idx}", meal["nutrition"]["fat"])
            _default(f"nth_ext_nprot_{week_idx}_{meal_idx}", meal["nutrition"]["protein"])

    # ── Previous Recommendations ──
    previous_weeks = [
        {
            "enabled": True,
            "calories": 1950,
            "meals": [
                {
                    "title": "Oatmeal with Blueberries",
                    "calories": 320.0,
                    "nutrition": {"calories": 320.0, "carbs": 54.0, "fat": 5.0, "protein": 10.0},
                },
                {
                    "title": "Grilled Lemon Herb Chicken Bowl",
                    "calories": 480.0,
                    "nutrition": {"calories": 480.0, "carbs": 45.0, "fat": 12.0, "protein": 42.0},
                },
                {
                    "title": "Sirloin Steak with Asparagus",
                    "calories": 650.0,
                    "nutrition": {"calories": 650.0, "carbs": 15.0, "fat": 30.0, "protein": 55.0},
                },
            ],
        },
        {
            "enabled": True,
            "calories": 1900,
            "meals": [
                {
                    "title": "Scrambled Egg Whites with Spinach",
                    "calories": 280.0,
                    "nutrition": {"calories": 280.0, "carbs": 10.0, "fat": 2.0, "protein": 35.0},
                },
                {
                    "title": "Turkey Wrap with Hummus",
                    "calories": 520.0,
                    "nutrition": {"calories": 520.0, "carbs": 55.0, "fat": 18.0, "protein": 32.0},
                },
                {
                    "title": "Teriyaki Salmon with Quinoa",
                    "calories": 610.0,
                    "nutrition": {"calories": 610.0, "carbs": 50.5, "fat": 22.0, "protein": 38.0},
                },
            ],
        },
        {
            "enabled": True,
            "calories": 1850,
            "meals": [
                {
                    "title": "Greek Yogurt with Almonds",
                    "calories": 300.0,
                    "nutrition": {"calories": 300.0, "carbs": 20.0, "fat": 14.0, "protein": 25.0},
                },
                {
                    "title": "Vegan Lentil Stew",
                    "calories": 380.0,
                    "nutrition": {"calories": 380.0, "carbs": 55.0, "fat": 6.0, "protein": 18.0},
                },
                {
                    "title": "Roasted Chicken Breasts with Sweet Potato",
                    "calories": 580.0,
                    "nutrition": {"calories": 580.0, "carbs": 60.0, "fat": 10.0, "protein": 45.0},
                },
            ],
        },
    ]
    _default("nth_prev_week_count", len(previous_weeks))
    for idx, week in enumerate(previous_weeks):
        _default(f"nth_prev_enabled_{idx}", week["enabled"])
        _default(f"nth_prev_cal_{idx}", week["calories"])
        _default(f"nth_prev_meal_count_{idx}", len(week["meals"]))
        for meal_idx, meal in enumerate(week["meals"]):
            _default(f"nth_prev_meal_title_{idx}_{meal_idx}", meal["title"])
            _default(f"nth_prev_meal_cal_{idx}_{meal_idx}", meal["calories"])
            _default(f"nth_prev_meal_ncal_{idx}_{meal_idx}", meal["nutrition"]["calories"])
            _default(f"nth_prev_meal_ncarbs_{idx}_{meal_idx}", meal["nutrition"]["carbs"])
            _default(f"nth_prev_meal_nfat_{idx}_{meal_idx}", meal["nutrition"]["fat"])
            _default(f"nth_prev_meal_nprot_{idx}_{meal_idx}", meal["nutrition"]["protein"])

    # Migrate legacy fixed week keys (1st_week/2nd_week/3rd_week) if present.
    legacy_weeks = ["1st_week", "2nd_week", "3rd_week"]
    for idx, week in enumerate(legacy_weeks):
        legacy_enabled = f"nth_prev_enabled_{week}"
        legacy_cal = f"nth_prev_cal_{week}"
        legacy_meal_count = f"nth_prev_meal_count_{week}"

        if legacy_enabled in st.session_state:
            st.session_state[f"nth_prev_enabled_{idx}"] = st.session_state[legacy_enabled]
        if legacy_cal in st.session_state:
            st.session_state[f"nth_prev_cal_{idx}"] = st.session_state[legacy_cal]
        if legacy_meal_count in st.session_state:
            st.session_state[f"nth_prev_meal_count_{idx}"] = st.session_state[legacy_meal_count]

        meal_count = int(st.session_state.get(f"nth_prev_meal_count_{idx}", 0))
        for meal_idx in range(meal_count):
            legacy_title = f"nth_prev_meal_title_{week}_{meal_idx}"
            legacy_calorie = f"nth_prev_meal_cal_{week}_{meal_idx}"
            if legacy_title in st.session_state:
                st.session_state[f"nth_prev_meal_title_{idx}_{meal_idx}"] = st.session_state[legacy_title]
            if legacy_calorie in st.session_state:
                st.session_state[f"nth_prev_meal_cal_{idx}_{meal_idx}"] = st.session_state[legacy_calorie]

    # ── Results ──
    _default("nth_result", None)
    _default("nth_save_status", None)
    _default("nth_feedback_rating", None)
    _default("nth_feedback_comment", "")


# ── Add / Remove callbacks (must be outside render so buttons work instantly) ─

def add_ww():
    i = st.session_state.nth_ww_count
    st.session_state[f"nth_ww_date_{i}"] = ""
    st.session_state[f"nth_ww_weight_{i}"] = 0.0
    st.session_state.nth_ww_count += 1

def remove_ww():
    n = st.session_state.nth_ww_count
    if n > 1:
        n -= 1
        st.session_state.pop(f"nth_ww_date_{n}", None)
        st.session_state.pop(f"nth_ww_weight_{n}", None)
        st.session_state.nth_ww_count = n

def add_int_meal():
    i = st.session_state.nth_int_count
    for k, v in [("title",""), ("cal",0.0), ("desc",""), ("ncal",""), ("ncarbs",""), ("nfat",""), ("nprot","")]:
        st.session_state[f"nth_int_{k}_{i}"] = v
    st.session_state.nth_int_count += 1

def remove_int_meal():
    n = st.session_state.nth_int_count
    if n > 1:
        n -= 1
        for k in ["title","cal","desc","ncal","ncarbs","nfat","nprot"]:
            st.session_state.pop(f"nth_int_{k}_{n}", None)
        st.session_state.nth_int_count = n

def add_ext_week():
    week_index = st.session_state.nth_ext_week_count
    st.session_state[f"nth_ext_meal_count_{week_index}"] = 1
    st.session_state[f"nth_ext_title_{week_index}_0"] = ""
    st.session_state[f"nth_ext_cal_{week_index}_0"] = 0.0
    st.session_state[f"nth_ext_desc_{week_index}_0"] = ""
    st.session_state[f"nth_ext_ncal_{week_index}_0"] = 0.0
    st.session_state[f"nth_ext_ncarbs_{week_index}_0"] = 0.0
    st.session_state[f"nth_ext_nfat_{week_index}_0"] = 0.0
    st.session_state[f"nth_ext_nprot_{week_index}_0"] = 0.0
    st.session_state.nth_ext_week_count += 1


def remove_ext_week():
    n = st.session_state.nth_ext_week_count
    if n > 0:
        n -= 1
        meal_count = int(st.session_state.get(f"nth_ext_meal_count_{n}", 0))
        for meal_idx in range(meal_count):
            for field in ["title", "cal", "desc", "ncal", "ncarbs", "nfat", "nprot"]:
                st.session_state.pop(f"nth_ext_{field}_{n}_{meal_idx}", None)
        st.session_state.pop(f"nth_ext_meal_count_{n}", None)
        st.session_state.nth_ext_week_count = n


def add_ext_meal(week_index):
    ck = f"nth_ext_meal_count_{week_index}"
    i = st.session_state[ck]
    st.session_state[f"nth_ext_title_{week_index}_{i}"] = ""
    st.session_state[f"nth_ext_cal_{week_index}_{i}"] = 0.0
    st.session_state[f"nth_ext_desc_{week_index}_{i}"] = ""
    st.session_state[f"nth_ext_ncal_{week_index}_{i}"] = 0.0
    st.session_state[f"nth_ext_ncarbs_{week_index}_{i}"] = 0.0
    st.session_state[f"nth_ext_nfat_{week_index}_{i}"] = 0.0
    st.session_state[f"nth_ext_nprot_{week_index}_{i}"] = 0.0
    st.session_state[ck] += 1


def remove_ext_meal(week_index):
    ck = f"nth_ext_meal_count_{week_index}"
    n = st.session_state[ck]
    if n > 1:
        n -= 1
        for field in ["title", "cal", "desc", "ncal", "ncarbs", "nfat", "nprot"]:
            st.session_state.pop(f"nth_ext_{field}_{week_index}_{n}", None)
        st.session_state[ck] = n

def add_prev_meal(week_index):
    ck = f"nth_prev_meal_count_{week_index}"
    i = st.session_state[ck]
    st.session_state[f"nth_prev_meal_title_{week_index}_{i}"] = ""
    st.session_state[f"nth_prev_meal_cal_{week_index}_{i}"] = 0.0
    st.session_state[f"nth_prev_meal_ncal_{week_index}_{i}"] = 0.0
    st.session_state[f"nth_prev_meal_ncarbs_{week_index}_{i}"] = 0.0
    st.session_state[f"nth_prev_meal_nfat_{week_index}_{i}"] = 0.0
    st.session_state[f"nth_prev_meal_nprot_{week_index}_{i}"] = 0.0
    st.session_state[ck] += 1

def remove_prev_meal(week_index):
    ck = f"nth_prev_meal_count_{week_index}"
    n = st.session_state[ck]
    if n > 1:
        n -= 1
        st.session_state.pop(f"nth_prev_meal_title_{week_index}_{n}", None)
        st.session_state.pop(f"nth_prev_meal_cal_{week_index}_{n}", None)
        st.session_state.pop(f"nth_prev_meal_ncal_{week_index}_{n}", None)
        st.session_state.pop(f"nth_prev_meal_ncarbs_{week_index}_{n}", None)
        st.session_state.pop(f"nth_prev_meal_nfat_{week_index}_{n}", None)
        st.session_state.pop(f"nth_prev_meal_nprot_{week_index}_{n}", None)
        st.session_state[ck] = n


def add_prev_week():
    idx = st.session_state.nth_prev_week_count
    st.session_state[f"nth_prev_enabled_{idx}"] = True
    st.session_state[f"nth_prev_cal_{idx}"] = 1900
    st.session_state[f"nth_prev_meal_count_{idx}"] = 1
    st.session_state[f"nth_prev_meal_title_{idx}_0"] = ""
    st.session_state[f"nth_prev_meal_cal_{idx}_0"] = 0.0
    st.session_state[f"nth_prev_meal_ncal_{idx}_0"] = 0.0
    st.session_state[f"nth_prev_meal_ncarbs_{idx}_0"] = 0.0
    st.session_state[f"nth_prev_meal_nfat_{idx}_0"] = 0.0
    st.session_state[f"nth_prev_meal_nprot_{idx}_0"] = 0.0
    st.session_state.nth_prev_week_count += 1


def remove_prev_week():
    n = st.session_state.nth_prev_week_count
    if n > 0:
        n -= 1
        meal_count = int(st.session_state.get(f"nth_prev_meal_count_{n}", 0))
        for meal_idx in range(meal_count):
            for field in ["title", "cal", "ncal", "ncarbs", "nfat", "nprot"]:
                st.session_state.pop(f"nth_prev_meal_{field}_{n}_{meal_idx}", None)
        st.session_state.pop(f"nth_prev_enabled_{n}", None)
        st.session_state.pop(f"nth_prev_cal_{n}", None)
        st.session_state.pop(f"nth_prev_meal_count_{n}", None)
        st.session_state.nth_prev_week_count = n


# ── Payload builder ───────────────────────────────────────────────────────────

def collect_payload():
    ss = st.session_state

    weekly_weights = []
    for i in range(ss.nth_ww_count):
        d = ss.get(f"nth_ww_date_{i}", "")
        w = ss.get(f"nth_ww_weight_{i}", 0.0)
        if d:
            weekly_weights.append({"recorded_date": d, "weight_kg": float(w)})

    consumed_internal = []
    for i in range(ss.nth_int_count):
        title = ss.get(f"nth_int_title_{i}", "")
        if not title:
            continue
        meal = {
            "title": title,
            "calories_kcal": _parse_float(ss.get(f"nth_int_cal_{i}", 0.0)),
            "description": ss.get(f"nth_int_desc_{i}", "") or None,
        }
        nutrition = _nutrition_payload(
            ss.get(f"nth_int_ncal_{i}", 0.0),
            ss.get(f"nth_int_ncarbs_{i}", 0.0),
            ss.get(f"nth_int_nfat_{i}", 0.0),
            ss.get(f"nth_int_nprot_{i}", 0.0),
        )
        if nutrition is not None:
            meal["nutrition_per_serving"] = nutrition
        consumed_internal.append(meal)

    consumed_external = {}
    for week_index in range(ss.get("nth_ext_week_count", 0)):
        meals = []
        for i in range(ss.get(f"nth_ext_meal_count_{week_index}", 0)):
            title = ss.get(f"nth_ext_title_{week_index}_{i}", "")
            if not title:
                continue
            meal = {
                "title": title,
                "calories_kcal": _parse_float(ss.get(f"nth_ext_cal_{week_index}_{i}", 0.0)),
                "description": ss.get(f"nth_ext_desc_{week_index}_{i}", "") or None,
            }
            nutrition = _nutrition_payload(
                ss.get(f"nth_ext_ncal_{week_index}_{i}", 0.0),
                ss.get(f"nth_ext_ncarbs_{week_index}_{i}", 0.0),
                ss.get(f"nth_ext_nfat_{week_index}_{i}", 0.0),
                ss.get(f"nth_ext_nprot_{week_index}_{i}", 0.0),
            )
            if nutrition is not None:
                meal["nutrition_per_serving"] = nutrition
            meals.append(meal)
        if meals:
            consumed_external[_ordinal_week_key(week_index + 1)] = meals

    prev_recs = {}
    for week_index in range(ss.get("nth_prev_week_count", 0)):
        if not ss.get(f"nth_prev_enabled_{week_index}", False):
            continue
        meals = []
        for i in range(ss.get(f"nth_prev_meal_count_{week_index}", 0)):
            title = ss.get(f"nth_prev_meal_title_{week_index}_{i}", "")
            if title:
                meal = {
                    "title": title,
                    "calories_kcal": _parse_float(ss.get(f"nth_prev_meal_cal_{week_index}_{i}", 0.0)),
                }
                nutrition = _nutrition_payload(
                    ss.get(f"nth_prev_meal_ncal_{week_index}_{i}", 0.0),
                    ss.get(f"nth_prev_meal_ncarbs_{week_index}_{i}", 0.0),
                    ss.get(f"nth_prev_meal_nfat_{week_index}_{i}", 0.0),
                    ss.get(f"nth_prev_meal_nprot_{week_index}_{i}", 0.0),
                )
                if nutrition is not None:
                    meal["nutrition_per_serving"] = nutrition
                meals.append(meal)
        prev_recs[_ordinal_week_key(week_index + 1)] = {
            "meals": meals,
        }

    return {
        "menu_id": int(ss.nth_menu_id),
        "stats": {
            "current_weight_kg": float(ss.nth_current_weight),
            "target_weight_kg": float(ss.nth_target_weight),
            "goal": ss.nth_goal,
            "step_count": int(ss.nth_step_count),
            "weekly_weights": weekly_weights,
            "plan_start_date": ss.nth_plan_start,
            "plan_end_date": ss.nth_plan_end,
            "current_date": ss.nth_current_date,
        },
        "meal_data": {
            "consumed_meal_internal": consumed_internal,
            "consumed_meal_external": consumed_external or None,
        },
        "previous_recommendations": prev_recs or None,
    }


# ── Response panel ────────────────────────────────────────────────────────────

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

    all_products = get_all_menu_products(menu_id) if menu_id else []
    product_map = {p["id"]: p for p in all_products}
    rendered_any = False

    # Parse flat products array and group by meal_types
    products = response_data.get("products", [])
    meal_type_groups = {}
    for product in products:
        for meal_type in product.get("meal_types", []):
            if meal_type not in meal_type_groups:
                meal_type_groups[meal_type] = []
            meal_type_groups[meal_type].append(product)

    # Sort products within each meal type: recommended first, then others
    for meal_type in meal_type_groups:
        meal_type_groups[meal_type].sort(key=lambda p: (not p.get("recommended", False), p.get("product_id")))

    # Define meal type order for display
    category_order = ["breakfast", "lunch", "dinner", "snack", "drink"]
    for category in category_order:
        if category not in meal_type_groups:
            continue

        rendered_any = True
        st.markdown(f'<div class="meal-section"><h3>{category.title()}</h3></div>', unsafe_allow_html=True)
        products_in_category = meal_type_groups[category]

        for start_index in range(0, len(products_in_category), 3):
            row_items = products_in_category[start_index: start_index + 3]
            card_columns = st.columns(3, gap="medium")
            for col_idx, product_item in enumerate(row_items):
                with card_columns[col_idx]:
                    prod_id   = product_item.get("product_id")
                    is_recommended = product_item.get("recommended", False)
                    reason = product_item.get("reason")
                    detail    = product_map.get(prod_id, {})
                    title     = html.escape(detail.get("title", f"Unknown Product #{prod_id}"))
                    desc      = html.escape(detail.get("description", "")).replace("\n", "<br>")
                    image_url = html.escape(detail.get("image", ""))
                    nutrition = detail.get("nutrition", {})
                    st.markdown(
                        build_card_html(title, desc, image_url, nutrition, is_recommended=is_recommended, rank_reasoning=reason),
                        unsafe_allow_html=True,
                    )

    if not rendered_any:
        st.warning("The API returned no products.")

    with st.expander("Raw API response", expanded=False):
        st.json(response_data)


def render_request_payload_panel(result):
    st.subheader("Request Payload")

    if not result:
        st.info("Generate recommendations to inspect the request payload.")
        return

    request_payload = result.get("request_payload")
    with st.expander("Request Payload JSON", expanded=False):
        if request_payload is None:
            st.info("Request payload is not available.")
        else:
            st.json(request_payload)


def render_response_payload_panel(result):
    st.header("Response Payload")

    if not result:
        st.info("Generate recommendations to inspect the response payload.")
        return

    response_payload = result.get("response")
    with st.expander("Response Payload JSON", expanded=False):
        if response_payload is None:
            st.info("Response payload is not available.")
        else:
            st.json(response_payload)


# ── Page setup ────────────────────────────────────────────────────────────────

inject_styles()
init_state()

st.title("Nth-Recommendation Tester")
st.caption("Continuity Testing — simulates week-over-week user states, meals, and goal progress.")

left_panel, right_panel = st.columns([1, 1.25], gap="large")

# ═══════════════════════════════════════════════════════════════════════════════
with left_panel:
    st.header("Request Form")

    # ── Stats ──────────────────────────────────────────────────────────────────
    st.subheader("Stats")

    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Menu ID", min_value=1, step=1, key="nth_menu_id")
        st.number_input("Current Weight (kg)", min_value=0.0, step=0.1, key="nth_current_weight")
        st.number_input("Target Weight (kg)", min_value=0.0, step=0.1, key="nth_target_weight")
        st.text_input("Plan Start Date (YYYY-MM-DD)", key="nth_plan_start")
    with c2:
        st.selectbox("Goal", ["weight_loss", "weight_gain", "maintenance"], key="nth_goal")
        st.number_input("Step Count", min_value=0, step=100, key="nth_step_count")
        st.text_input("Current Date (YYYY-MM-DD)", key="nth_current_date")
        st.text_input("Plan End Date (YYYY-MM-DD)", key="nth_plan_end")

    st.divider()

    # ── Weekly Weights ─────────────────────────────────────────────────────────
    hc, bc = st.columns([2, 1])
    with hc:
        st.subheader("Weekly Weights")
    with bc:
        b1, b2 = st.columns(2)
        with b1:
            st.button("＋ Add", on_click=add_ww, width='stretch', key="btn_add_ww")
        with b2:
            st.button("− Remove", on_click=remove_ww, width='stretch', key="btn_rem_ww",
                      disabled=(st.session_state.nth_ww_count <= 1))
    st.caption("Historic weight trajectory for the LLM.")

    for i in range(st.session_state.nth_ww_count):
        with st.container(border=True):
            st.markdown(f'<div class="entry-card-label">📅 Weight Entry {i + 1}</div>', unsafe_allow_html=True)
            dc, wc = st.columns(2)
            with dc:
                st.text_input("Date (YYYY-MM-DD)", key=f"nth_ww_date_{i}", label_visibility="visible")
            with wc:
                st.number_input("Weight (kg)", min_value=0.0, step=0.1, key=f"nth_ww_weight_{i}")

    st.divider()

    # ── Meal Data ──────────────────────────────────────────────────────────────
    st.subheader("Meal Data")

    # Internal meals ─────────────────────────────────────────────────────────
    hc, bc = st.columns([2, 1])
    with hc:
        st.markdown("**Internal Meals** *(ordered via Instameals)*")
    with bc:
        b1, b2 = st.columns(2)
        with b1:
            st.button("＋ Add", on_click=add_int_meal, width='stretch', key="btn_add_int")
        with b2:
            st.button("− Remove", on_click=remove_int_meal, width='stretch', key="btn_rem_int",
                      disabled=(st.session_state.nth_int_count <= 1))

    for i in range(st.session_state.nth_int_count):
        with st.container(border=True):
            st.markdown(f'<div class="entry-card-label">🍽 Internal Meal {i + 1}</div>', unsafe_allow_html=True)
            tc, cc = st.columns([2, 1])
            with tc:
                st.text_input("Title", key=f"nth_int_title_{i}", placeholder="e.g. Avocado Toast")
            with cc:
                st.number_input("Calories (kcal)", min_value=0.0, step=1.0, key=f"nth_int_cal_{i}")
            st.text_input("Description", key=f"nth_int_desc_{i}", placeholder="Optional notes...")

            with st.expander("Nutrition per Serving (optional)", expanded=True):
                n1, n2, n3, n4 = st.columns(4)
                with n1:
                    st.number_input("Calories (kcal)", min_value=0.0, step=1.0, key=f"nth_int_ncal_{i}")
                with n2:
                    st.number_input("Carbs (g)", min_value=0.0, step=0.1, key=f"nth_int_ncarbs_{i}")
                with n3:
                    st.number_input("Fat (g)", min_value=0.0, step=0.1, key=f"nth_int_nfat_{i}")
                with n4:
                    st.number_input("Protein (g)", min_value=0.0, step=0.1, key=f"nth_int_nprot_{i}")

    # External meals ─────────────────────────────────────────────────────────
    st.markdown("&nbsp;", unsafe_allow_html=True)
    hc, bc = st.columns([2, 1])
    with hc:
        st.subheader("External Meals")
    with bc:
        b1, b2 = st.columns(2)
        with b1:
            st.button("＋ Add", on_click=add_ext_week, width='stretch', key="btn_add_ext_week")
        with b2:
            st.button("− Remove", on_click=remove_ext_week, width='stretch', key="btn_rem_ext_week",
                      disabled=(st.session_state.nth_ext_week_count <= 0))
    st.caption("Off-platform meals grouped by week to match the backend request schema.")

    for week_index in range(st.session_state.nth_ext_week_count):
        week_label = _week_display_label(week_index + 1)
        meal_count_key = f"nth_ext_meal_count_{week_index}"

        with st.container(border=True):
            st.markdown(f'<div class="entry-card-label">🌍 {week_label}</div>', unsafe_allow_html=True)

            mhc, mbc = st.columns([2, 1])
            with mhc:
                st.markdown("**Meals that week**")
            with mbc:
                mb1, mb2 = st.columns(2)
                with mb1:
                    st.button("＋ Add", on_click=add_ext_meal, args=(week_index,), width='stretch', key=f"btn_add_ext_{week_index}")
                with mb2:
                    st.button("− Remove", on_click=remove_ext_meal, args=(week_index,), width='stretch', key=f"btn_rem_ext_{week_index}",
                              disabled=(st.session_state[meal_count_key] <= 1))

            for meal_index in range(st.session_state[meal_count_key]):
                with st.container(border=True):
                    st.markdown(f'<div class="entry-card-label">🍽 External Meal {meal_index + 1}</div>', unsafe_allow_html=True)
                    tc, cc = st.columns([2, 1])
                    with tc:
                        st.text_input("Title", key=f"nth_ext_title_{week_index}_{meal_index}", placeholder="e.g. McDonalds Big Mac")
                    with cc:
                        st.number_input("Calories (kcal)", min_value=0.0, step=1.0, key=f"nth_ext_cal_{week_index}_{meal_index}")
                    st.text_input("Description", key=f"nth_ext_desc_{week_index}_{meal_index}", placeholder="Optional notes...")

                    with st.expander("Nutrition per Serving (optional)", expanded=True):
                        n1, n2, n3, n4 = st.columns(4)
                        with n1:
                            st.number_input("Calories (kcal)", min_value=0.0, step=1.0, key=f"nth_ext_ncal_{week_index}_{meal_index}")
                        with n2:
                            st.number_input("Carbs (g)", min_value=0.0, step=0.1, key=f"nth_ext_ncarbs_{week_index}_{meal_index}")
                        with n3:
                            st.number_input("Fat (g)", min_value=0.0, step=0.1, key=f"nth_ext_nfat_{week_index}_{meal_index}")
                        with n4:
                            st.number_input("Protein (g)", min_value=0.0, step=0.1, key=f"nth_ext_nprot_{week_index}_{meal_index}")

    st.divider()

    # ── Previous Recommendations ───────────────────────────────────────────────
    hc, bc = st.columns([2, 1])
    with hc:
        st.subheader("Previous Recommendations")
    with bc:
        b1, b2 = st.columns(2)
        with b1:
            st.button("＋ Add", on_click=add_prev_week, width='stretch', key="btn_add_prev_week")
        with b2:
            st.button("− Remove", on_click=remove_prev_week, width='stretch', key="btn_rem_prev_week",
                      disabled=(st.session_state.nth_prev_week_count <= 0))
    st.caption("Include historical week data to give the LLM continuity context.")

    for week_index in range(st.session_state.nth_prev_week_count):
        week_label = _week_display_label(week_index + 1)
        enabled_key = f"nth_prev_enabled_{week_index}"

        with st.container(border=True):
            st.markdown(f'<div class="entry-card-label">📆 {week_label}</div>', unsafe_allow_html=True)
            st.checkbox(f"Include {week_label}", key=enabled_key)

            if st.session_state[enabled_key]:
                meal_count_key = f"nth_prev_meal_count_{week_index}"

                mhc, mbc = st.columns([2, 1])
                with mhc:
                    st.markdown("**Meals that week**")
                with mbc:
                    mb1, mb2 = st.columns(2)
                    with mb1:
                        st.button("＋ Add", on_click=add_prev_meal, args=(week_index,),
                                  width='stretch', key=f"btn_add_pm_{week_index}")
                    with mb2:
                        st.button("− Remove", on_click=remove_prev_meal, args=(week_index,),
                                  width='stretch', key=f"btn_rem_pm_{week_index}",
                                  disabled=(st.session_state[meal_count_key] <= 1))

                for i in range(st.session_state[meal_count_key]):
                    with st.container(border=True):
                        st.markdown(f'<div class="entry-card-label">🍽 Meal {i + 1}</div>', unsafe_allow_html=True)
                        mc1, mc2 = st.columns([2, 1])
                        with mc1:
                            st.text_input("Meal Title", key=f"nth_prev_meal_title_{week_index}_{i}",
                                          placeholder="e.g. Chicken Salad")
                        with mc2:
                            st.number_input("Calories (kcal)", min_value=0.0, step=1.0,
                                            key=f"nth_prev_meal_cal_{week_index}_{i}")

                        with st.expander("Nutrition per Serving (optional)", expanded=True):
                            n1, n2, n3, n4 = st.columns(4)
                            with n1:
                                st.number_input("Calories (kcal)", min_value=0.0, step=1.0,
                                                key=f"nth_prev_meal_ncal_{week_index}_{i}")
                            with n2:
                                st.number_input("Carbs (g)", min_value=0.0, step=0.1,
                                                key=f"nth_prev_meal_ncarbs_{week_index}_{i}")
                            with n3:
                                st.number_input("Fat (g)", min_value=0.0, step=0.1,
                                                key=f"nth_prev_meal_nfat_{week_index}_{i}")
                            with n4:
                                st.number_input("Protein (g)", min_value=0.0, step=0.1,
                                                key=f"nth_prev_meal_nprot_{week_index}_{i}")

    st.divider()

    # ── Submit ────────────────────────────────────────────────────────────────
    if st.button("Generate Nth Recommendations", type="primary", width='stretch'):
        st.session_state.nth_save_status = None
        payload = collect_payload()

        with st.spinner("Calling Nth Endpoint..."):
            try:
                response = requests.post(NTH_API_URL, json=payload, timeout=120)
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {"detail": response.text}

                if response.status_code != 200:
                    st.session_state.nth_result = {
                        "error": f"API request failed with HTTP {response.status_code}.",
                        "response": response_data,
                        "menu_id": payload["menu_id"],
                        "request_payload": payload,
                    }
                else:
                    st.session_state.nth_result = {
                        "error": None,
                        "response": response_data,
                        "menu_id": payload["menu_id"],
                        "request_payload": payload,
                    }
            except requests.RequestException as exc:
                st.session_state.nth_result = {
                    "error": f"Could not reach the Nth API: {exc}",
                    "response": None,
                    "request_payload": payload,
                }

    st.divider()
    render_request_payload_panel(st.session_state.nth_result)

    # ── Feedback & Save ───────────────────────────────────────────────────────
    generated_result = st.session_state.nth_result
    if generated_result and generated_result.get("request_payload") is not None:
        st.subheader("Tester Feedback")

        # Thumbs rating buttons with visual selection state
        rating_options = ["👍 Like", "👎 Dislike"]

        # Determine current selection index
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
            label_visibility="collapsed"
        )

        # Update session state based on selection
        if rating_value == "👍 Like":
            st.session_state.nth_feedback_rating = "like"
        elif rating_value == "👎 Dislike":
            st.session_state.nth_feedback_rating = "dislike"

        # Optional comment field
        st.text_area(
            "Comments (Optional)",
            key="nth_feedback_comment",
            placeholder="Share additional feedback...",
            height=100
        )

        if st.button("Save Nth Test Run", width='stretch', type="primary"):
            r_payload = generated_result.get("request_payload")
            r_response = generated_result.get("response")
            rating = st.session_state.nth_feedback_rating
            comment = st.session_state.nth_feedback_comment.strip()

            # Validation: require either rating or comment
            if rating is None and not comment:
                st.session_state.nth_save_status = {
                    "type": "error",
                    "message": "Please select a rating (👍/👎) or add a comment to save."
                }
            elif r_payload is None or r_response is None:
                st.session_state.nth_save_status = {
                    "type": "error",
                    "message": "Generate recommendations first."
                }
            else:
                try:
                    with st.spinner("Saving to MongoDB..."):
                        # Build structured feedback dict
                        feedback_dict = {
                            "rating": rating,
                            "comment": comment
                        }
                        inserted_id = save_test_run_to_mongo(
                            MONGO_NTH_COLLECTION_NAME,
                            r_payload,
                            r_response,
                            feedback_dict
                        )
                    st.session_state.nth_save_status = {
                        "type": "success",
                        "message": f"Saved Nth test run (id: {inserted_id}).",
                    }
                except Exception as exc:
                    st.session_state.nth_save_status = {
                        "type": "error",
                        "message": f"Could not save: {exc}"
                    }

        stat = st.session_state.nth_save_status
        if stat:
            if stat.get("type") == "success":
                st.success(stat["message"])
            else:
                st.error(stat["message"])


# ═══════════════════════════════════════════════════════════════════════════════
with right_panel:
    render_nth_recommendation_panel(st.session_state.nth_result)
    st.divider()
    render_response_payload_panel(st.session_state.nth_result)
