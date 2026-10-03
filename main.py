from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

app = FastAPI()


# ============================================================
# SENSOR PACKET SCHEMA
# Temporary proxy schema until the actual binary packet format
# is finalized by the hardware team.
# ============================================================

class SensorPacket(BaseModel):
    device_id: str
    timestamp: int
    sequence: int
    data: dict


# ============================================================
# BASIC HTTP ENDPOINT
# ============================================================

@app.get("/")
async def root():
    return {
        "message": "Sensor backend is running"
    }


# ============================================================
# HTTP SENSOR ENDPOINT
# ============================================================

@app.post("/sensor")
async def receive_sensor_data(packet: SensorPacket):
    return {
        "status": "received",
        "packet": packet.model_dump()
    }


# ============================================================
# WEBSOCKET SENSOR ENDPOINT
# ============================================================

@app.websocket("/ws/device")
async def device_websocket(websocket: WebSocket):

    # Accept the WebSocket connection
    await websocket.accept()

    print("Device connected")

    try:
        while True:

            # Receive JSON data from the device/client
            data = await websocket.receive_json()

            # Validate the received data using Pydantic
            try:
                packet = SensorPacket.model_validate(data)

            except ValidationError as e:

                print("Invalid sensor packet:")
                print(e)

                # Tell the client that the packet was invalid
                await websocket.send_json({
                    "status": "error",
                    "message": "Invalid sensor packet",
                    "details": e.errors()
                })

                # Keep the WebSocket connection alive
                continue

            # Packet is valid
            print("Valid packet:")
            print(packet)

            # Optional acknowledgement
            await websocket.send_json({
                "status": "received",
                "sequence": packet.sequence
            })

    except WebSocketDisconnect:

        print("Device disconnected")