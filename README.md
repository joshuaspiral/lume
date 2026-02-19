# Lume

Light visualiser for Triones LED light strip.

## What it does

- **Music Mode** — Uses your phone's microphone to analyse audio in real time. The browser does the FFT, sends frequency data to the Pi over websockets.
- **Manual Mode** — Pick a colour, set an effect.
- **Source Handoff** — One phone acts as the audio source at a time. Tap "use my phone" to take over. Everyone else can see who's broadcasting.

## Setup

```bash
# Install dependencies
pip install websockets bleak

# Run
python server.py
```

The server binds to `0.0.0.0:8000`. Connect any device on the same network to `http://<pi-ip>:8000`.

## Hardware

- Raspberry Pi Zero 2w
- Triones Bluetooth LED strip
