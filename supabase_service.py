import os

from dotenv import load_dotenv
from supabase import create_client, Client


# ------------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ------------------------------------------------------------

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is missing")

if not SUPABASE_SECRET_KEY:
    raise RuntimeError("SUPABASE_SECRET_KEY is missing")


# ------------------------------------------------------------
# SUPABASE CLIENT
# ------------------------------------------------------------

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


# ------------------------------------------------------------
# STORE SENSOR DATA
# ------------------------------------------------------------

def store_sensor_data(data: dict):

    response = (
        supabase
        .table("sensor_data")
        .insert(data)
        .execute()
    )

    return response.data

# ------------------------------------------------------------
# GET DATA
#
# This is our "outlet".
#
# It exists now, but we are NOT connecting it to the
# dashboard/enriched-data receiver yet.
# ------------------------------------------------------------

def get_session_data(session_id: str):

    response = (
        supabase
        .table("sensor_data")
        .select("*")
        .eq("session_id", session_id)
        .order("timestamp")
        .execute()
    )

    return response.data