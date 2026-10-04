import os
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from supabase_service import create_client, Client


# ------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise RuntimeError("Supabase environment variables are missing")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


# ------------------------------------------------------------
# FastAPI
# ------------------------------------------------------------

app = FastAPI()


# ------------------------------------------------------------
# Temporary sensor schema
# ------------------------------------------------------------

class SensorData(BaseModel):
    device_id: str

    # Temporary validation ranges.
    # We can change these later when the actual sensor specs
    # are finalized.

    heart_rate: float = Field(ge=20, le=250)
    spo2: float = Field(ge=0, le=100)

    # The BLE file does not specify valid ranges for these,
    # so for now we only require numerical values.
    load_g: float
    load_b: float


# ------------------------------------------------------------
# Root endpoint
# ------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "message": "Walkabit sensor backend is running"
    }


# ------------------------------------------------------------
# Receive + validate + store sensor data
# ------------------------------------------------------------

@app.post("/sensor")
async def receive_sensor_data(sensor: SensorData):

    # Create timestamp on the server
    timestamp = datetime.now(timezone.utc).isoformat()

    # Data that will go into Supabase
    row = {
        "device_id": sensor.device_id,
        "timestamp": timestamp,
        "heart_rate": sensor.heart_rate,
        "spo2": sensor.spo2,
        "load_g": sensor.load_g,
        "load_b": sensor.load_b,
    }

    # Insert into Supabase
    response = (
        supabase
        .table("sensor_data")
        .insert(row)
        .execute()
    )

    return {
        "status": "stored",
        "data": row
    }