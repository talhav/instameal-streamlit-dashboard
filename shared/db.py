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
    if not MONGO_URI:
        raise ValueError("Mongo connection is not configured. Please set MONGO_URI.")

    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) as client:
        database = client[MONGO_DB_NAME]
        insert_result = database[collection_name].insert_one(
            {
                "request_payload": request_payload,
                "response_payload": response_payload,
                "feedback": feedback,
                "created_at": datetime.now(timezone.utc),
            }
        )

    return str(insert_result.inserted_id)
