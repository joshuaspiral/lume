import asyncio
from bleak import BleakClient
import config

class LEDDevice:
    def __init__(self, name, mac, uuid, protocol):
        self.name = name
        self.mac = mac
        self.uuid = uuid
        self.protocol = protocol
        self.client = None
        self.last_color = [0, 0, 0]

    async def connect(self, retries=3):
        for i in range(retries):
            try:
                self.client = BleakClient(self.mac)
                await self.client.connect()
                print(f"[led] connected to {self.name}")
                return True
            except Exception as e:
                if "InProgress" in str(e) and i < retries - 1:
                    print(f"[led] {self.name} busy, retrying in 2s...")
                    await asyncio.sleep(2)
                    continue
                print(f"[led] failed to connect to {self.name}: {e}")
                return False
        return False

    def _get_packet(self, r, g, b):
        if self.protocol == "triones":
            return bytes([0x56, r, g, b, 0x00, 0xF0, 0xAA])
        elif self.protocol == "happylighting":
            return bytes([0x7e, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xef])
        return None

    async def update(self, r, g, b):
        if not self.client or not self.client.is_connected:
            return
        
        if all(abs(c1 - c2) < 3 for c1, c2 in zip([r, g, b], self.last_color)):
            return

        packet = self._get_packet(r, g, b)
        if packet:
            try:
                await self.client.write_gatt_char(self.uuid, packet, response=False)
                self.last_color = [r, g, b]
            except Exception:
                pass

class LEDController:
    def __init__(self):
        self.devices = [LEDDevice(**cfg) for cfg in config.LEDS]

    async def connect_all(self):
        success = True
        for d in self.devices:
            if not await d.connect():
                success = False
        return success

    async def broadcast(self, r, g, b):
        await asyncio.gather(*(d.update(r, g, b) for d in self.devices))