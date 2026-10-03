import asyncio
import json
import websockets


async def main():

    uri = "ws://127.0.0.1:8000/ws/device"

    async with websockets.connect(uri) as websocket:

        # Bad packet: sequence is missing
        bad_data = {
            "device_id": "ESP32_001",
            "timestamp": 123456789,
            "data": {
                "raw": "temporary"
            }
        }

        await websocket.send(json.dumps(bad_data))

        print("Bad packet sent")

        await asyncio.sleep(1)

        # Good packet
        good_data = {
            "device_id": "ESP32_001",
            "timestamp": 123456790,
            "sequence": 2,
            "data": {
                "raw": "temporary"
            }
        }

        await websocket.send(json.dumps(good_data))

        print("Good packet sent")

        await asyncio.sleep(1)


asyncio.run(main())