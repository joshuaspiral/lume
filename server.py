from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import subprocess
import config

def create_app(state):
    app = FastAPI()

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>joshua@arch:~/lume</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                :root {{ --bg: #000; --fg: #fff; --green: #00ff41; --dim: #666; --blue: #5dade2; }}
                body {{ font-family: 'Courier New', monospace; background: var(--bg); color: var(--fg); padding: 20px; line-height: 1.4; }}
                .terminal {{ max-width: 800px; margin: 0 auto; }}
                .prompt {{ color: var(--green); }}
                .path {{ color: var(--blue); }}
                .card {{ border: 1px solid #333; padding: 20px; margin-bottom: 25px; position: relative; }}
                .card::before {{ content: attr(data-label); position: absolute; top: -12px; left: 15px; background: var(--bg); padding: 0 10px; color: var(--dim); font-size: 14px; }}
                button {{ background: transparent; color: var(--fg); border: 1px solid var(--fg); padding: 10px 20px; margin: 5px; font-family: inherit; cursor: pointer; }}
                button:hover {{ background: var(--fg); color: var(--bg); }}
                button.active {{ border-color: var(--green); color: var(--green); }}
                .slider {{ width: 100%; height: 2px; background: #333; outline: none; -webkit-appearance: none; margin-top: 15px; }}
                .slider::-webkit-slider-thumb {{ -webkit-appearance: none; width: 15px; height: 15px; background: var(--green); cursor: pointer; }}
                a {{ color: var(--green); text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="terminal">
                <div style="margin-bottom:20px;">
                    <span class="prompt">joshua@arch</span>:<span class="path">~/lume</span>$ ./lume --status
                </div>

                <div class="card" data-label="spotify.sh">
                    <div id="now-playing" style="margin-bottom: 15px; color: var(--green); font-size: 14px;">
                        [ NO_TRACK_DETECTED ]
                    </div>
                    <button onclick="player('previous')">[ PREV ]</button>
                    <button onclick="player('play-pause')">[ PLAY/PAUSE ]</button>
                    <button onclick="player('next')">[ NEXT ]</button>
                </div>

                <div class="card" data-label="lume.conf">
                    <button class="m" id="b-visualize" onclick="setMode('visualize')">MODE_FFT</button>
                    <button class="m" id="b-strobe" onclick="setMode('strobe')">MODE_STROBE</button>
                    <button class="m" id="b-pulse" onclick="setMode('pulse')">MODE_PULSE</button>
                    <button class="m" id="b-off" onclick="setMode('off')">MODE_OFF</button>
                    
                    <div style="margin-top:20px;">
                        <span>SENSITIVITY</span>
                        <input type="range" class="slider" min="0.5" max="5.0" step="0.1" value="{state.sensitivity}" onchange="set('sensitivity', this.value)">
                    </div>
                    <div style="margin-top:20px;">
                        <span>BRIGHTNESS</span>
                        <input type="range" class="slider" min="0" max="1.0" step="0.1" value="{state.brightness}" onchange="set('brightness', this.value)">
                    </div>
                </div>
            </div>
            <script>
                async function updateMetadata() {{
                    try {{
                        const res = await fetch('/metadata');
                        const data = await res.json();
                        document.getElementById('now-playing').innerText = data.track ? `>> NOW_PLAYING: ${{data.track}} - ${{data.artist}}` : '[ IDLE ]';
                    }} catch (e) {{}}
                }}
                setInterval(updateMetadata, 3000);

                function setMode(m) {{ 
                    fetch('/mode?v=' + m);
                    document.querySelectorAll('.m').forEach(b => b.classList.remove('active'));
                    document.getElementById('b-' + m).classList.add('active');
                }}
                function set(k, v) {{ fetch('/set/' + k + '?v=' + v); }}
                function player(c) {{ fetch('/player?c=' + c); }}
                window.onload = () => {{
                    document.getElementById('b-{state.mode}').classList.add('active');
                    updateMetadata();
                }};
            </script>
        </body>
        </html>
        """

    @app.get("/metadata")
    async def get_metadata():
        try:
            track = subprocess.check_output(["playerctl", "metadata", "title"], text=True).strip()
            artist = subprocess.check_output(["playerctl", "metadata", "artist"], text=True).strip()
            return {{"track": track, "artist": artist}}
        except:
            return {{"track": None, "artist": None}}

    @app.get("/mode")
    async def set_mode(v: str):
        state.mode = v
        return {{"status": "ok"}}

    @app.get("/set/{{key}}")
    async def set_param(key: str, v: float):
        if hasattr(state, key):
            setattr(state, key, v)
        return {{"status": "ok"}}

    @app.get("/player")
    async def player_control(c: str):
        subprocess.run(["playerctl", c], check=False)
        return {{"status": "ok"}}

    return app
