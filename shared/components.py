import html
import json
from textwrap import dedent

def parse_nutrition_data(raw_value):
    if not raw_value:
        return {}

    if isinstance(raw_value, dict):
        return raw_value

    if isinstance(raw_value, str):
        try:
            parsed_value = json.loads(raw_value)
            return parsed_value if isinstance(parsed_value, dict) else {}
        except json.JSONDecodeError:
            return {}

    return {}

def build_nutrition_html(nutrition):
    """Return a self-contained HTML string for the nutrition strip."""
    nutrition_fields = [
        ("calories", "Calories"),
        ("protein", "Protein"),
        ("carbs", "Carbs"),
        ("fat", "Fat"),
    ]
    items = [
        (label, nutrition.get(key))
        for key, label in nutrition_fields
        if nutrition.get(key) is not None
    ]

    if not items:
        return '<div class="reco-nut-empty">Nutrition data unavailable</div>'

    pills_html = "".join(
        f'''
        <div class="reco-nut-pill">
            <span class="reco-nut-val">{html.escape(str(value))}</span>
            <span class="reco-nut-lbl">{label}</span>
        </div>'''
        for label, value in items
    )

    return f'''
    <div class="reco-nut-section">
        <div class="reco-nut-heading">Nutrition per serving</div>
        <div class="reco-nut-row">{pills_html}</div>
    </div>'''

def build_card_html(title, description, image_url, nutrition, is_recommended=False, rank=None, rank_reasoning=None):
    """Return a complete card HTML block so Streamlit renders it as one unit."""
    badge_text = ""
    if rank is not None:
        badge_text = f"#{rank} Ranked"
    elif is_recommended:
        badge_text = "⭐ Recommended"

    badge_html = f'<div class="reco-badge">{badge_text}</div>' if badge_text else ''

    if image_url:
        image_html = f'<div class="reco-card-image-wrapper">{badge_html}<img src="{image_url}" alt="{title}" loading="lazy" /></div>'
    else:
        image_html = f'<div class="reco-card-no-image">{badge_html}No image available</div>'

    nutrition_html = build_nutrition_html(nutrition)

    reasoning_html = ""
    if rank_reasoning:
        # Display reason as italicized text in a dedicated box
        escaped_reason = html.escape(str(rank_reasoning))
        reasoning_html = f'<div class="reco-rank-reasoning"><em>{escaped_reason}</em></div>'

    return dedent(f'''
        <div class="reco-card">
            {image_html}
            <div class="reco-card-content">
                <div class="reco-card-body">
                    <div class="reco-card-title">{title}</div>
                    <p class="reco-card-description">{description}</p>
                </div>
                {reasoning_html}
                {nutrition_html}
            </div>
        </div>
    ''').strip()
