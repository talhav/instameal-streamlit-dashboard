MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack", "drink")


def build_nth_recommendation_payload(
    user_id, menu_id, selected_days, meal_quantities
):
    """Build the minimal request accepted by the nth-recommendation endpoint."""
    meals = []
    for meal_type in MEAL_TYPES:
        quantity = int(meal_quantities.get(meal_type, 0))
        if quantity > 0:
            meals.append({"meal_type": meal_type, "quantity": quantity})

    return {
        "user_id": int(user_id),
        "menu_id": int(menu_id),
        "number_of_days": len(selected_days or []),
        "meals": meals,
    }


def validate_nth_recommendation_payload(payload):
    """Return tester-facing validation messages for the minimal nth request."""
    errors = []
    if payload["number_of_days"] <= 0:
        errors.append("Select at least one delivery day.")
    if not payload["meals"]:
        errors.append("Add at least one meal with quantity greater than zero.")
    return errors
