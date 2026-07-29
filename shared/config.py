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
MONGO_FIRST_REC_FEEDBACK_COLLECTION = os.getenv("MONGO_FIRST_REC_FEEDBACK_COLLECTION", "first_recommendations")
MONGO_NTH_REC_FEEDBACK_COLLECTION = os.getenv("MONGO_NTH_REC_FEEDBACK_COLLECTION", "nth_recommendations")

# Endpoints
# New specific env vars take priority; fall back to the old API_URL / NTH_API_URL
# names that existing Railway deployments already have set.
_api_base = os.getenv("API_URL", "http://127.0.0.1:8001")
NTH_REC_API_URL = (os.getenv("NTH_REC_API_URL")
                   or os.getenv("NTH_API_URL")
                   or "http://localhost:8000/api/v1/nth-recommendations")
NTH_REC_API_TIMEOUT_SECONDS = int(os.getenv("NTH_REC_API_TIMEOUT_SECONDS", "300"))
DIET_PLAN_API_URL = (os.getenv("DIET_PLAN_API_URL")
                     or f"{_api_base}/api/v1/diet-plan")
INITIAL_REC_API_URL = (os.getenv("INITIAL_REC_API_URL")
                       or f"{_api_base}/api/v1/initial-recommendations")
