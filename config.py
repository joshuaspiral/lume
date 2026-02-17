LEDS = [
    {
        "name": "strip",
        "mac": "36:46:3F:B9:6B:C7",
        "uuid": "0000ffd9-0000-1000-8000-00805f9b34fb",
        "protocol": "triones"
    },
    {
        "name": "lamp",
        "mac": "BE:28:85:00:31:E8",
        "uuid": "0000fff3-0000-1000-8000-00805f9b34fb",
        "protocol": "happylighting"
    }
]

CHUNKS = 1024
RATE = 44100
BANDS = {
    "bass": (20, 250),
    "mid": (250, 4000),
    "high": (4000, 20000)
}

HOST = "0.0.0.0"
PORT = 8000
