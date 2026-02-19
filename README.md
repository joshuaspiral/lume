# lume

Light visualiser for the common room led strip.

## What it does

- **Music Mode** — your browser does FFT on mic input, streams frequency data to the Pi over websockets.
- **Manual Mode** — Pick a colour, set an effect.
- **Source Handoff** — One phone is the audio source at a time. Tap "use my phone" to take over.

## How it works

```
phone mic → web audio api (fft) → websocket → pi → triones ble
```

The pi receives `{ bass, mid, treble }` thirty times a second and translates that into bluetooth commands.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install websockets bleak aiohttp
.venv/bin/python server.py
```

or use the deploy script to set up the pi as a standalone access point:

```bash
sudo bash deploy.sh
```

## Hardware

- Raspberry Pi Zero 2W
- Triones Bluetooth LED strip
