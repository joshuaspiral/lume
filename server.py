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
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Lume Control</title>
            <style>
                :root {{
                    --bg: #0f172a;
                    --card-bg: #1e293b;
                    --text: #f8fafc;
                    --text-dim: #94a3b8;
                    --primary: #38bdf8;
                    --accent: #22c55e;
                    --border: #334155;
                }}
                
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    background-color: var(--bg);
                    color: var(--text);
                    display: flex;
                    justify-content: center;
                    padding: 2rem 1rem;
                    line-height: 1.5;
                }}

                .container {{
                    width: 100%;
                    max-width: 500px;
                    display: flex;
                    flex-direction: column;
                    gap: 1.5rem;
                }}

                header {{
                    text-align: center;
                    margin-bottom: 0.5rem;
                }}

                h1 {{
                    font-size: 1.5rem;
                    font-weight: 700;
                    letter-spacing: -0.025em;
                }}

                .card {{
                    background: var(--card-bg);
                    border-radius: 1rem;
                    padding: 1.5rem;
                    border: 1px solid var(--border);
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                }}

                .card-title {{
                    font-size: 0.875rem;
                    font-weight: 600;
                    color: var(--text-dim);
                    margin-bottom: 1rem;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}

                #now-playing {{
                    background: rgba(0,0,0,0.2);
                    padding: 1rem;
                    border-radius: 0.5rem;
                    margin-bottom: 1.25rem;
                    font-size: 0.9375rem;
                    border-left: 3px solid var(--accent);
                }}

                .controls-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 0.75rem;
                }}

                .modes-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 0.75rem;
                    margin-bottom: 1.5rem;
                }}

                button {{
                    appearance: none;
                    background: #334155;
                    border: none;
                    color: var(--text);
                    padding: 0.75rem 1rem;
                    border-radius: 0.5rem;
                    font-weight: 600;
                    font-size: 0.875rem;
                    cursor: pointer;
                    transition: all 0.2s;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}

                button:hover {{ background: #475569; }}
                button:active {{ transform: scale(0.98); }}
                button.active {{ background: var(--primary); color: #0f172a; }}

                .slider-group {{ margin-top: 1.25rem; }}
                
                .label-row {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 0.5rem;
                    font-size: 0.875rem;
                    font-weight: 500;
                }}

                input[type="range"] {{
                    -webkit-appearance: none;
                    width: 100%;
                    height: 6px;
                    background: #334155;
                    border-radius: 3px;
                    outline: none;
                }}

                input[type="range"]::-webkit-slider-thumb {{
                    -webkit-appearance: none;
                    width: 18px;
                    height: 18px;
                    background: var(--primary);
                    border-radius: 50%;
                    cursor: pointer;
                    box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
                }}

                .icon {{ margin-right: 0.5rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Lume Control</h1>
                </header>

                <div class="card">
                    <div class="card-title">Now Playing</div>
                    <div id="now-playing">
                        [ NO_TRACK_DETECTED ]
                    </div>
                    <div class="controls-grid">
                        <button onclick="player('previous')">PREV</button>
                        <button onclick="player('play-pause')">PLAY</button>
                        <button onclick="player('next')">NEXT</button>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title">Lighting Mode</div>
                    <div class="modes-grid">
                        <button class="m" id="b-visualize" onclick="setMode('visualize')">Visualizer</button>
                        <button class="m" id="b-strobe" onclick="setMode('strobe')">Strobe</button>
                        <button class="m" id="b-pulse" onclick="setMode('pulse')">Pulse</button>
                        <button class="m" id="b-off" onclick="setMode('off')">Off</button>
                    </div>
                    
                    <div class="slider-group">
                        <div class="label-row">
                            <span>Sensitivity</span>
                            <span id="v-sensitivity">{state.sensitivity}</span>
                        </div>
                        <input type="range" min="0.5" max="5.0" step="0.1" value="{state.sensitivity}" 
                               oninput="document.getElementById('v-sensitivity').innerText=this.value"
                               onchange="set('sensitivity', this.value)">
                    </div>

                    <div class="slider-group">
                        <div class="label-row">
                            <span>Brightness</span>
                            <span id="v-brightness">{int(state.brightness * 100)}%</span>
                        </div>
                        <input type="range" min="0" max="1.0" step="0.05" value="{state.brightness}" 
                               oninput="document.getElementById('v-brightness').innerText=Math.round(this.value * 100) + '%'"
                               onchange="set('brightness', this.value)">
                    </div>
                </div>
            </div>
            <script>
                async function updateMetadata() {{
                    try {{
                        const res = await fetch('/metadata');
                        const data = await res.json();
                        const el = document.getElementById('now-playing');
                        if (data.track) {{
                            el.innerHTML = `<strong>${{data.track}}</strong><br><span style="color:var(--text-dim)">${{data.artist}}</span>`;
                        }} else {{
                            el.innerText = 'No music playing';
                        }}
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
