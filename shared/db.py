import psycopg2
import streamlit as st
from datetime import datetime, timezone
from pymongo import MongoClient

from shared.config import (
    DEFAULT_DB_NAME,
    DEFAULT_DB_USER,
    DEFAULT_DB_PASSWORD,
    DEFAULT_DB_HOST,
    DEFAULT_DB_PORT,
    MONGO_URI,
    MONGO_DB_NAME
)
from shared.components import parse_nutrition_data

@st.cache_data(ttl=600)
def get_all_menu_products(menu_id):
    if not menu_id:
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

        cursor.execute(
            """
            SELECT p.id, p.title, p.description, p.image, p.nutrition_per_serving, p.meal_type
            FROM products p
            JOIN menu_products mp ON p.id = mp.product_id
            WHERE mp.menu_id = %s
            """,
            (menu_id,)
        )

        db_results = []
        for row in cursor.fetchall():
            nutrition_data = parse_nutrition_data(row[4])
            meal_types = [m.lower() for m in (row[5] or [])]
            db_results.append({
                "id": row[0],
                "title": row[1] or "Unknown title",
                "description": row[2] or "",
                "image": row[3] or "",
                "nutrition": nutrition_data,
                "meal_types": meal_types
            })

        cursor.close()
        connection.close()
        return db_results
    except Exception as e:
        st.error(f"DB Connection Error: {e}")
        return []

def save_test_run_to_mongo(collection_name, request_payload, response_payload, feedback):
    """
    Save test run data to MongoDB.

    Args:
        collection_name: MongoDB collection name
        request_payload: Original API request dict
        response_payload: API response dict
        feedback: Can be either:
                 - string: Legacy format (e.g., "Great recommendations!")
                 - dict: New format (e.g., {"rating": "like", "comment": "..."})

    Returns:
        str: MongoDB document ID

    Example:
        # New format with thumbs rating
        feedback_dict = {
            "rating": "like",  # "like" | "dislike" | null
            "comment": "Excellent options!"  # optional text
        }
        save_test_run_to_mongo(collection, request, response, feedback_dict)
    """
    if not MONGO_URI:
        raise ValueError("Mongo connection is not configured. Please set MONGO_URI.")

    # Validate feedback format if dict
    if isinstance(feedback, dict):
        # New structured format
        if "rating" in feedback:
            rating = feedback.get("rating")
            if rating is not None and rating not in ("like", "dislike"):
                raise ValueError(f"Invalid rating value: {rating}. Must be 'like', 'dislike', or null.")
        feedback_to_save = feedback
    else:
        # Legacy string format - convert to new format for consistency
        feedback_to_save = {
            "rating": None,
            "comment": feedback if isinstance(feedback, str) else str(feedback)
        }

    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) as client:
        database = client[MONGO_DB_NAME]
        insert_result = database[collection_name].insert_one(
            {
                "request_payload": request_payload,
                "response_payload": response_payload,
                "feedback": feedback_to_save,
                "created_at": datetime.now(timezone.utc),
            }
        )

    return str(insert_result.inserted_id)
