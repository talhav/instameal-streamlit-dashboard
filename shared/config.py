import os
from dotenv import load_dotenv

load_dotenv()

# Common DB Configs
DEFAULT_DB_NAME = os.getenv("DB_NAME")
DEFAULT_DB_USER = os.getenv("DB_USER")
DEFAULT_DB_PASSWORD = os.getenv("DB_PASSWORD")
DEFAULT_DB_HOST = os.getenv("DB_HOST", "localhost")
DEFAULT_DB_PORT = os.getenv("DB_PORT", "5432")

# Mongo Configs
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "instameals")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "first_recommendations")
MONGO_NTH_COLLECTION_NAME = os.getenv("MONGO_NTH_COLLECTION_NAME", "nth_recommendations")

# Endpoints
API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1/recommendations")
NTH_API_URL = os.getenv("NTH_API_URL", "http://localhost:8000/api/v1/nth-recommendations")
