import asyncio
import uvicorn
import config
from led import LEDController
from audio import AudioProcessor
from server import create_app

class GlobalState:
    def __init__(self):
        self.mode = "visualize"
        self.brightness = 1.0
        self.sensitivity = 1.5

state = GlobalState()
leds = LEDController()

def audio_callback(r, g, b):
    asyncio.run_coroutine_threadsafe(leds.broadcast(r, g, b), loop)

async def start():
    global loop
    loop = asyncio.get_running_loop()
    
    print("[lume] initializing bluetooth...")
    await leds.connect_all()
    
    print("[lume] starting audio processor...")
    audio = AudioProcessor(state, audio_callback)
    audio.start()
    
    print(f"[lume] server starting on {config.HOST}:{config.PORT}")
    app = create_app(state)
    config_uvicorn = uvicorn.Config(app, host=config.HOST, port=config.PORT, log_level="error")
    server = uvicorn.Server(config_uvicorn)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass