# lume

light visualiser for triones led light strip.

## what it does

- **music mode** — uses your phone's microphone to analyse audio in real time. the browser does the fft, sends frequency data to the pi over websockets. no app install, no account, no spotify api. just sound.
- **manual mode** — pick a colour, set an effect, hand off control to someone else.
- **source handoff** — one phone acts as the audio source at a time. tap "use my phone" to take over. everyone else sees who's broadcasting.

## setup

```bash
# install dependencies
pip install websockets bleak

# run
python server.py
```

the server binds to `0.0.0.0:8000`. connect any device on the same network to `http://<pi-ip>:8000`.

## hardware

- raspberry pi zero 2w
- triones bluetooth led strip
