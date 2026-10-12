import csv
from io import StringIO

from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel, Field

from supabase_service import store_sensor_data, get_session_data
app = FastAPI()


class SensorData(BaseModel):
    session_id: str
    device_id: str
    sequence: int

    heart_rate: float = Field(ge=20, le=250)
    spo2: float = Field(ge=0, le=100)

    load_g: float
    load_b: float


@app.get("/")
async def root():
    return {
        "message": "Walkabit sensor backend is running"
    }


@app.post("/sensor")
async def receive_sensor_data(sensor: SensorData):

    data = sensor.model_dump()

    stored_data = store_sensor_data(data)

    return {
        "status": "stored",
        "data": stored_data
    }

# ============================================================
# EXPORT SESSION SENSOR DATA AS CSV
# ============================================================

@app.get("/sessions/{session_id}/export/sensors")
async def export_sensor_data(session_id: str):

    # Retrieve the session's data from Supabase
    rows = get_session_data(session_id)

    # Define a consistent CSV column order
    columns = [
        "id",
        "session_id",
        "device_id",
        "timestamp",
        "sequence",
        "heart_rate",
        "spo2",
        "load_g",
        "load_b",
        "created_at"
    ]

    # Create CSV content in memory
    output = StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=columns,
        extrasaction="ignore"
    )

    # Write column headings
    writer.writeheader()

    # Write sensor records
    writer.writerows(rows)

    # Prepare a downloadable CSV response
    csv_content = output.getvalue()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition":
                f'attachment; filename="session_{session_id}_sensors.csv"'
        }
    )