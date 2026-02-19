#!/usr/bin/env python3
"""
Triones LED WebSocket Server
Runs on Pi Zero 2W - receives audio FFT data from browser clients
and translates to BLE light commands.
"""

import asyncio
import json
import time
import colorsys
import math
import http.server
import threading
import os
from bleak import BleakClient
import websockets
from websockets.server import serve

# ── Config ──────────────────────────────────────────────────────────────────
LED_MAC = "36:46:3F:B9:6B:C7"
CHARACTERISTIC_UUID = "0000ffd9-0000-1000-8000-00805f9b34fb"
WS_PORT = 8765
HTTP_PORT = 8080
SEND_INTERVAL = 0.05   # 20 FPS max to LED strip

# ── LED Controller ───────────────────────────────────────────────────────────
class LEDController:
    def __init__(self):
        self.client = None
        self.current_color = [0, 0, 0]
        self.last_send_time = 0

    async def connect(self):
        try:
            print(f"🔌 Connecting to {LED_MAC}...")
            self.client = BleakClient(LED_MAC)
            await self.client.connect()
            print("✅ LED connected")
            return True
        except Exception as e:
            print(f"❌ LED connection failed: {e}")
            return False

    async def set_color(self, r, g, b):
        now = time.time()
        color_changed = any(
            abs(c - p) > 5
            for c, p in zip([r, g, b], self.current_color)
        )
        if not color_changed and (now - self.last_send_time) < SEND_INTERVAL:
            return
        if self.client and self.client.is_connected:
            try:
                packet = bytes([0x56, r, g, b, 0x00, 0xF0, 0xAA])
                await self.client.write_gatt_char(
                    CHARACTERISTIC_UUID, packet, response=False
                )
                self.current_color = [r, g, b]
                self.last_send_time = now
            except Exception as e:
                print(f"⚠️  LED write error: {e}")

    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print("👋 LED disconnected")


# ── Server State ─────────────────────────────────────────────────────────────
led = LEDController()
clients: dict[str, websockets.WebSocketServerProtocol] = {}
current_source: str | None = None   # client_id of audio source
client_counter = 0
smooth_r, smooth_g, smooth_b = 0.0, 0.0, 0.0
SMOOTHING = 0.35


def next_client_id() -> str:
    global client_counter
    client_counter += 1
    return f"client_{client_counter}"


async def broadcast(message: dict, exclude: str | None = None):
    """Send a message to all connected clients."""
    data = json.dumps(message)
    for cid, ws in list(clients.items()):
        if cid == exclude:
            continue
        try:
            await ws.send(data)
        except Exception:
            pass


def freq_to_color(bass: float, mid: float, treble: float) -> tuple[int, int, int]:
    """
    Map frequency bands to RGB.
    Bass → hue shift (warm reds/oranges), mid → saturation, treble → brightness.
    All values are 0.0–1.0.
    """
    # Bass drives hue: low bass = red (0°), high bass = blue (240°)
    hue = bass * 0.67          # 0.0 (red) → 0.67 (blue)
    saturation = 0.5 + mid * 0.5   # always at least 50% saturated
    value = 0.2 + treble * 0.8     # never fully off

    r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
    return int(r * 255), int(g * 255), int(b * 255)


# ── WebSocket Handler ─────────────────────────────────────────────────────────
async def handle_client(websocket):
    global current_source, smooth_r, smooth_g, smooth_b

    cid = next_client_id()
    clients[cid] = websocket
    print(f"🔗 {cid} connected  ({len(clients)} total)")

    # Send initial state to new client
    await websocket.send(json.dumps({
        "type": "init",
        "your_id": cid,
        "source": current_source,
        "client_count": len(clients),
    }))

    # Notify everyone of new connection count
    await broadcast({"type": "client_count", "count": len(clients)}, exclude=cid)

    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            # ── Claim source role ────────────────────────────────────────────
            if msg_type == "claim_source":
                current_source = cid
                label = msg.get("label", cid)
                print(f"🎵 {cid} claimed source ({label})")
                await broadcast({
                    "type": "source_changed",
                    "source_id": cid,
                    "label": label,
                })

            # ── Release source role ──────────────────────────────────────────
            elif msg_type == "release_source":
                if current_source == cid:
                    current_source = None
                    await broadcast({"type": "source_changed", "source_id": None, "label": None})
                    print(f"🔇 {cid} released source")

            # ── Audio frequency data ─────────────────────────────────────────
            elif msg_type == "freq" and cid == current_source:
                bass   = float(msg.get("bass",   0))
                mid    = float(msg.get("mid",    0))
                treble = float(msg.get("treble", 0))

                # Clamp
                bass   = max(0.0, min(1.0, bass))
                mid    = max(0.0, min(1.0, mid))
                treble = max(0.0, min(1.0, treble))

                target_r, target_g, target_b = freq_to_color(bass, mid, treble)

                # Exponential smoothing
                smooth_r = smooth_r * (1 - SMOOTHING) + target_r * SMOOTHING
                smooth_g = smooth_g * (1 - SMOOTHING) + target_g * SMOOTHING
                smooth_b = smooth_b * (1 - SMOOTHING) + target_b * SMOOTHING

                await led.set_color(int(smooth_r), int(smooth_g), int(smooth_b))

            # ── Manual colour ────────────────────────────────────────────────
            elif msg_type == "manual_color":
                r = int(msg.get("r", 255))
                g = int(msg.get("g", 255))
                b = int(msg.get("b", 0))
                # Manual overrides source temporarily
                if current_source == cid or current_source is None:
                    smooth_r, smooth_g, smooth_b = float(r), float(g), float(b)
                    await led.set_color(r, g, b)

            # ── Preset effects ───────────────────────────────────────────────
            elif msg_type == "preset":
                preset = msg.get("name")
                if preset == "off":
                    smooth_r = smooth_g = smooth_b = 0.0
                    await led.set_color(0, 0, 0)
                elif preset == "white":
                    smooth_r = smooth_g = smooth_b = 255.0
                    await led.set_color(255, 255, 255)
                elif preset == "warm":
                    await led.set_color(255, 120, 20)
                    smooth_r, smooth_g, smooth_b = 255.0, 120.0, 20.0

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        del clients[cid]
        if current_source == cid:
            current_source = None
            await broadcast({"type": "source_changed", "source_id": None, "label": None})
        await broadcast({"type": "client_count", "count": len(clients)})
        print(f"🔌 {cid} disconnected  ({len(clients)} remaining)")


# ── HTTP Server (serves index.html) ──────────────────────────────────────────
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress request logs

    def do_GET(self):
        # Always serve index.html for any path
        self.path = "/index.html"
        return super().do_GET()


def start_http_server():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(("0.0.0.0", HTTP_PORT), QuietHandler)
    print(f"🌐 HTTP server on port {HTTP_PORT}")
    server.serve_forever()


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    # Start HTTP server in background thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # Connect to LEDs
    await led.connect()

    # Start WebSocket server
    print(f"🔌 WebSocket server on port {WS_PORT}")
    async with serve(handle_client, "0.0.0.0", WS_PORT):
        print("✅ Ready. Open http://<pi-ip>:8080 on any phone.\n")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down")
