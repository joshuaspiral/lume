import numpy as np
import threading
import config
import time
import os

class AudioProcessor:
    def __init__(self, state, callback):
        self.state = state
        self.callback = callback
        self._strobe_state = False

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        smooth_bass = 0
        smooth_mid = 0
        smooth_high = 0

        print(f"🎤 lume: listening to {config.FIFO_PATH}...")
        
        while True:
            if not os.path.exists(config.FIFO_PATH):
                print(f"[audio] waiting for {config.FIFO_PATH}...")
                time.sleep(2)
                continue

            try:
                with open(config.FIFO_PATH, "rb") as fifo:
                    # Read loop
                    while True:
                        if self.state.mode == "off":
                            self.callback(0, 0, 0)
                            time.sleep(0.5)
                            continue

                        # Assuming 16-bit Stereo PCM (4 bytes per sample)
                        raw = fifo.read(config.CHUNKS * 4)
                        if not raw:
                            break # FIFO closed?

                        data = np.frombuffer(raw, dtype=np.int16)
                        if len(data) == 0:
                            continue
                        
                        # Stereo to Mono
                        data = data.reshape(-1, 2).mean(axis=1)
                        
                        windowed = data * np.hanning(len(data))
                        fft = np.abs(np.fft.rfft(windowed))
                        freqs = np.fft.rfftfreq(config.CHUNKS, 1.0/config.RATE)

                        b_mask = (freqs >= config.BANDS["bass"][0]) & (freqs <= config.BANDS["bass"][1])
                        m_mask = (freqs > config.BANDS["mid"][0]) & (freqs <= config.BANDS["mid"][1])
                        h_mask = (freqs > config.BANDS["high"][0]) & (freqs <= config.BANDS["high"][1])

                        bv = np.mean(fft[b_mask]) if any(b_mask) else 0
                        mv = np.mean(fft[m_mask]) if any(m_mask) else 0
                        hv = np.mean(fft[h_mask]) if any(h_mask) else 0

                        smooth_bass = smooth_bass * 0.8 + (bv / 4000.0) * 0.2
                        smooth_mid = smooth_mid * 0.8 + (mv / 2000.0) * 0.2
                        smooth_high = smooth_high * 0.8 + (hv / 1000.0) * 0.2

                        intensity = min(1.0, smooth_bass * self.state.sensitivity)
                        r, g, b = 0, 0, 0

                        if self.state.mode == "visualize":
                            total = smooth_bass + smooth_mid + smooth_high + 0.001
                            r = int((smooth_bass / total) * 255 * self.state.brightness * intensity * 1.5)
                            g = int((smooth_mid / total) * 255 * self.state.brightness * intensity * 1.5)
                            b = int((smooth_high / total) * 255 * self.state.brightness * intensity * 1.5)
                        
                        elif self.state.mode == "strobe":
                            if smooth_bass > 0.4 / self.state.sensitivity:
                                self._strobe_state = not self._strobe_state
                            else:
                                self._strobe_state = False
                            val = 255 if self._strobe_state else 0
                            r = g = b = int(val * self.state.brightness)

                        elif self.state.mode == "pulse":
                            val = min(255, int(255 * intensity * self.state.brightness))
                            r = g = b = val

                        self.callback(min(255, r), min(255, g), min(255, b))
            except Exception as e:
                print(f"[audio] error: {e}")
                time.sleep(1)
