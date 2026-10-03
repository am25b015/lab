import asyncio
from enum import Enum
from bleak import BleakScanner, BleakClient

#SERVICE_UUID = 
SENSOR_CHARACTERISTIC_UUID = ""

class ConnectionState(Enum):
    Disconnected = "Disconnected"
    Scanning = "Scanning"
    Connecting = "Connecting"
    Connected = "Connected"
    Reconnecting = "Reconnecting"

class BLEService:

    def __init__(self, device_name=None, address=None):

        self.device_name = device_name
        self.address = address

        self.client = None
        self.device = None

        self.state = ConnectionState.Disconnected

        self.reconnect_task = None
        self.manual_disconnect = False

        self.subscriptions = {}

    async def scan(self, timeout=5):

        self.state = ConnectionState.Scanning

        print("Scanning for BLE devices...")

        devices = await BleakScanner.discover(timeout=timeout)

        for device in devices:

            print(
                f"Found: {device.name} "
                f"({device.address})"
            )

            if self.address:

                if device.address.lower() == self.address.lower():

                    self.device = device

                    print(
                        f"Selected device: "
                        f"{device.name}"
                    )

                    return device

            if self.device_name:

                if device.name == self.device_name:

                    self.device = device

                    print(
                        f"Selected device: "
                        f"{device.name}"
                    )

                    return device

        self.state = ConnectionState.Disconnected

        print("Device not found.")

        return None

    async def connect(self):

        if self.device is None:

            await self.scan()

        if self.device is None:

            raise RuntimeError("No BLE device selected")

        self.state = ConnectionState.Connecting

        self.manual_disconnect = False

        print(
            f"Connecting to "
            f"{self.device.name}..."
        )

        self.client = BleakClient(
            self.device,
            disconnected_callback=self._on_disconnect
        )

        try:

            await asyncio.wait_for(self.client.connect(), timeout=10)

        except asyncio.TimeoutError as e:

            self.state = ConnectionState.Disconnected

            print("Connection timed out")

            raise

        except Exception as e:

            self.state = ConnectionState.Disconnected

            print(f"Connection failed: {e}")

            raise

        if self.client.is_connected:

            self.state = ConnectionState.Connected

            print("Connected!")

    async def disconnect(self):

        self.manual_disconnect = True

        if self.reconnect_task and not self.reconnect_task.done():

            self.reconnect_task.cancel()

            try:

                await self.reconnect_task

            except (asyncio.CancelledError, Exception):

                pass

            self.reconnect_task = None

        if self.client:

            if self.client.is_connected:

                print("Disconnecting...")

                await self.client.disconnect()

        self.state = ConnectionState.Disconnected

        print("Disconnected")

    async def subscribe(
        self,
        characteristic_uuid,
        callback
    ):

        if not self.client:

            raise RuntimeError("BLE client does not exist")

        if not self.client.is_connected:

            raise RuntimeError("BLE device is not connected")

        self.subscriptions[characteristic_uuid] = callback

        await self.client.start_notify(
            characteristic_uuid,
            callback
        )

        print(
            f"Subscribed to: "
            f"{characteristic_uuid}"
        )

    def _on_disconnect(self, client):

        print("\nESP32 disconnected!")

        self.state = ConnectionState.Disconnected

        if self.manual_disconnect:
            return

        if self.reconnect_task is None:

            try:

                loop = asyncio.get_running_loop()

                self.reconnect_task = loop.create_task(self.reconnect())

            except RuntimeError:

                print("Cannot start reconnect task")

    async def reconnect(
        self,
        retries=5,
        delay=3
    ):

        self.state = ConnectionState.Reconnecting

        for attempt in range(retries):

            if self.manual_disconnect:

                break

            print(
                f"Reconnect attempt "
                f"{attempt + 1}/{retries}"
            )

            try:

                if self.device is None:

                    await self.scan()

                    self.state = ConnectionState.Reconnecting

                if self.device is None:

                    await asyncio.sleep(delay)

                    continue

                self.client = BleakClient(
                    self.device,
                    disconnected_callback=self._on_disconnect
                )

                await self.client.connect()

                if self.client.is_connected:

                    self.state = ConnectionState.Connected

                    print("Reconnected!")

                    for uuid, callback in self.subscriptions.items():

                        try:

                            await self.client.start_notify(
                                uuid,
                                callback
                            )

                            print(
                                f"Resubscribed: "
                                f"{uuid}"
                            )

                        except Exception as e:

                            print(
                                f"Subscription failed: "
                                f"{e}"
                            )

                    self.reconnect_task = None

                    return True

            except Exception as e:

                print(f"Reconnect failed: {e}")

            await asyncio.sleep(delay)

        self.state = ConnectionState.Disconnected

        self.reconnect_task = None

        print("Unable to reconnect.")

        return False

    def get_state(self):

        return self.state.value


def sensor_callback(sender, data):

    try:

        message = data.decode("utf-8").strip()

        print(f"\nReceived: {message}")

        # Expected example:
        #
        # HR,SpO2,LoadG,LoadB

        values = message.split(",")

        if len(values) != 4:

            print(
                "Invalid packet:"
                f" expected 4 values, "
                f"received {len(values)}"
            )

            return

        heart_rate = float(values[0])
        spo2 = float(values[1])
        load_g = float(values[2])
        load_b = float(values[3])

        print(f"Heart Rate : {heart_rate:.1f} bpm")

        print(f"SpO2       : {spo2:.1f} %")

        print(f"LoadG      : {load_g:.2f} %")

        print(f"LoadB      : {load_b:.2f} %")

    except UnicodeDecodeError:

        print("Received non-text BLE data")

    except ValueError:

        print(f"Invalid sensor values: {data}")

    except Exception as e:

        print(f"Packet processing error: {e}")


async def main():

    ble = BLEService(
        device_name="Walkabit"
    )

    try:

        await ble.connect()

        await ble.subscribe(
            SENSOR_CHARACTERISTIC_UUID,
            sensor_callback
        )

        print("\n--------------------------------")
        print("Walkabit BLE is running")
        print("Waiting for sensor data...")
        print("Press Ctrl+C to stop")
        print("--------------------------------")

        while True:

            await asyncio.sleep(1)

    except KeyboardInterrupt:

        print("\nStopping Walkabit BLE...")

    except Exception as e:

        print(f"\nError: {e}")

    finally:

        await ble.disconnect()


if __name__ == "__main__":
    asyncio.run(main())