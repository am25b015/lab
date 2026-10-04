import asyncio
from enum import Enum

from bleak import BleakScanner, BleakClient


# ============================================================
# BLE CONFIGURATION
# ============================================================

SENSOR_CHARACTERISTIC_UUID = ""


# ============================================================
# CONNECTION STATES
# ============================================================

class ConnectionState(Enum):
    DISCONNECTED = "Disconnected"
    SCANNING = "Scanning"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"


# ============================================================
# BLE SERVICE
# Handles ONLY:
# - scanning
# - connecting
# - disconnecting
# - subscribing to notifications
# - reconnecting
# - forwarding raw BLE data
# ============================================================

class BLEService:

    def __init__(self, device_name=None, address=None):

        self.device_name = device_name
        self.address = address

        self.client = None
        self.device = None

        self.state = ConnectionState.DISCONNECTED

        self.reconnect_task = None
        self.manual_disconnect = False

        # Stores:
        # characteristic UUID -> callback
        #
        # This allows us to restore subscriptions after reconnecting.
        self.subscriptions = {}

    # ========================================================
    # SCAN
    # ========================================================

    async def scan(self, timeout=5):

        self.state = ConnectionState.SCANNING

        print("Scanning for BLE devices...")

        devices = await BleakScanner.discover(timeout=timeout)

        for device in devices:

            print(f"Found: {device.name} ({device.address})")

            # Match by address if provided
            if self.address:

                if device.address.lower() == self.address.lower():

                    self.device = device

                    print(f"Selected device: {device.name}")

                    return device

            # Otherwise match by device name
            if self.device_name:

                if device.name == self.device_name:

                    self.device = device

                    print(f"Selected device: {device.name}")

                    return device

        self.state = ConnectionState.DISCONNECTED

        print("Device not found.")

        return None

    # ========================================================
    # CONNECT
    # ========================================================

    async def connect(self):

        # Find device if we don't already have one
        if self.device is None:

            await self.scan()

        if self.device is None:

            raise RuntimeError("No BLE device selected")

        self.state = ConnectionState.CONNECTING
        self.manual_disconnect = False

        print(f"Connecting to {self.device.name}...")

        self.client = BleakClient(
            self.device,
            disconnected_callback=self._on_disconnect
        )

        try:

            await asyncio.wait_for(
                self.client.connect(),
                timeout=10
            )

        except asyncio.TimeoutError:

            self.state = ConnectionState.DISCONNECTED

            print("Connection timed out")

            raise

        except Exception as e:

            self.state = ConnectionState.DISCONNECTED

            print(f"Connection failed: {e}")

            raise

        if self.client.is_connected:

            self.state = ConnectionState.CONNECTED

            print("Connected!")

    # ========================================================
    # SUBSCRIBE TO BLE NOTIFICATIONS
    #
    # This does NOT interpret the data.
    #
    # The callback receives:
    #
    #     sender
    #     raw bytes
    #
    # What those bytes mean is handled somewhere else.
    # ========================================================

    async def subscribe(self, characteristic_uuid, callback):

        if self.client is None:

            raise RuntimeError("BLE client does not exist")

        if not self.client.is_connected:

            raise RuntimeError("BLE device is not connected")

        # Remember subscription so it can be restored
        # after reconnecting.
        self.subscriptions[characteristic_uuid] = callback

        await self.client.start_notify(
            characteristic_uuid,
            callback
        )

        print(f"Subscribed to: {characteristic_uuid}")

    # ========================================================
    # DISCONNECT
    # ========================================================

    async def disconnect(self):

        self.manual_disconnect = True

        # Stop any reconnect task
        if self.reconnect_task:

            if not self.reconnect_task.done():

                self.reconnect_task.cancel()

                try:
                    await self.reconnect_task
                except asyncio.CancelledError:
                    pass

            self.reconnect_task = None

        # Disconnect BLE client
        if self.client:

            if self.client.is_connected:

                print("Disconnecting...")

                await self.client.disconnect()

        self.state = ConnectionState.DISCONNECTED

        print("Disconnected")

    # ========================================================
    # HANDLE UNEXPECTED DISCONNECT
    # ========================================================

    def _on_disconnect(self, client):

        print("\nESP32 disconnected!")

        self.state = ConnectionState.DISCONNECTED

        # If we intentionally disconnected, do nothing.
        if self.manual_disconnect:

            return

        # Start reconnection in the background.
        if self.reconnect_task is None:

            try:

                loop = asyncio.get_running_loop()

                self.reconnect_task = loop.create_task(
                    self.reconnect()
                )

            except RuntimeError:

                print("Cannot start reconnect task")

    # ========================================================
    # RECONNECT
    # ========================================================

    async def reconnect(self, retries=5, delay=3):

        self.state = ConnectionState.RECONNECTING

        for attempt in range(retries):

            if self.manual_disconnect:

                break

            print(
                f"Reconnect attempt "
                f"{attempt + 1}/{retries}"
            )

            try:

                # Rediscover device if necessary
                if self.device is None:

                    await self.scan()

                    self.state = ConnectionState.RECONNECTING

                if self.device is None:

                    await asyncio.sleep(delay)

                    continue

                # Create a new BLE client
                self.client = BleakClient(
                    self.device,
                    disconnected_callback=self._on_disconnect
                )

                await self.client.connect()

                if self.client.is_connected:

                    self.state = ConnectionState.CONNECTED

                    print("Reconnected!")

                    # Restore all previous subscriptions
                    for uuid, callback in self.subscriptions.items():

                        try:

                            await self.client.start_notify(
                                uuid,
                                callback
                            )

                            print(f"Resubscribed: {uuid}")

                        except Exception as e:

                            print(
                                f"Failed to resubscribe "
                                f"{uuid}: {e}"
                            )

                    self.reconnect_task = None

                    return True

            except Exception as e:

                print(f"Reconnect failed: {e}")

            await asyncio.sleep(delay)

        self.state = ConnectionState.DISCONNECTED

        self.reconnect_task = None

        print("Unable to reconnect.")

        return False

    # ========================================================
    # GET CURRENT CONNECTION STATE
    # ========================================================

    def get_state(self):

        return self.state.value


# ============================================================
# EXAMPLE RAW DATA CALLBACK
#
# This deliberately does NOTHING with the data.
# It only demonstrates that BLE data arrived.
#
# Later, main.py can replace this with:
#
#     raw bytes -> decoder -> Pydantic -> Supabase
# ============================================================

def handle_ble_data(sender, data):

    print(
        f"Received {len(data)} bytes "
        f"from {sender}"
    )

    print(f"Raw data: {data}")


# ============================================================
# TEST / STANDALONE RUNNER
# ============================================================

async def main():

    ble = BLEService(
        device_name="Walkabit"
    )

    try:

        await ble.connect()

        await ble.subscribe(
            SENSOR_CHARACTERISTIC_UUID,
            handle_ble_data
        )

        print("\n--------------------------------")
        print("Walkabit BLE service is running")
        print("Waiting for BLE data...")
        print("Press Ctrl+C to stop")
        print("--------------------------------")

        while True:

            await asyncio.sleep(1)

    except KeyboardInterrupt:

        print("\nStopping BLE service...")

    except Exception as e:

        print(f"\nError: {e}")

    finally:

        await ble.disconnect()


if __name__ == "__main__":
    asyncio.run(main())