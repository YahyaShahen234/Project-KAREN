# wake.py — Offline wake-word (“Hey Karen”) using openWakeWord on Raspberry Pi
from _future_ import annotations
import asyncio
import time
import os
from typing import Optional, Sequence
import numpy as np
import sounddevice as sd

try:
    import openwakeword
    from openwakeword.model import Model
except Exception as e:
    raise RuntimeError(
        "openwakeword is required. pip install openwakeword sounddevice numpy"
    ) from e

try:
    import soundfile as sf
except Exception as e:
    raise RuntimeError(
        "soundfile is required for recording. pip install soundfile"
    ) from e

# Optional settings import; falls back to sane defaults for Pi
try:
    from .config import settings
except Exception:
    class _S:
        WAKE_MODEL_PATHS: list[str] = ["hey_karen.tflite"] if os.path.exists("hey_karen.tflite") else []
        USE_PRETRAINED = False
        WAKE_THRESHOLD = 0.5
        WAKE_TRIGGER_LEVEL = 3
        WAKE_COOLDOWN_MS = 1200
        WAKE_DEVICE = None
        WAKE_VAD_THRESHOLD = 0.5
        WAKE_SPEEX_NS = False
        SAMPLE_RATE = 16000
        CHANNELS = 1
    settings = _S()  # type: ignore

FRAME_MS = 80
FRAME_SAMPLES = int(0.001 * FRAME_MS * settings.SAMPLE_RATE)  # 1280 @ 16k

def record_wakeword_samples(num_samples: int = 10, sample_rate: int = 16000, channels: int = 1, duration_sec: float = 2.0):
    """
    Record wake word samples for training a custom model.
    Saves as .wav files in 'wake_training_data'.
    """
    os.makedirs('wake_training_data', exist_ok=True)
    
    print(f"\n=== Recording {num_samples} 'Hey Karen' samples ===")
    print("Instructions: Say 'Hey Karen' clearly after the beep. Press Enter to start.")
    input()
    
    for i in range(1, num_samples + 1):
        print(f"\nRecording sample {i}/{num_samples}...")
        time.sleep(1)
        print("Beep!")
        beep_freq = 800
        beep_duration = 0.2
        t = np.linspace(0, beep_duration, int(sample_rate * beep_duration), False)
        beep = np.sin(2 * np.pi * beep_freq * t)
        sd.play(beep, sample_rate)
        sd.wait()
        
        with sd.InputStream(samplerate=sample_rate, channels=channels, dtype='float32') as stream:
            audio = stream.read(int(sample_rate * duration_sec))[0]
        
        thresh = 0.01
        start_idx = 0
        end_idx = len(audio)
        for j, sample in enumerate(audio):
            if abs(sample) > thresh:
                start_idx = max(0, j - int(sample_rate * 0.1))
                break
        for j in range(len(audio) - 1, 0, -1):
            if abs(audio[j]) > thresh:
                end_idx = min(len(audio), j + int(sample_rate * 0.1))
                break
        
        audio_trimmed = audio[start_idx:end_idx]
        filename = os.path.join('wake_training_data', f'hey_karen_{i:02d}.wav')
        sf.write(filename, audio_trimmed, sample_rate)
        print(f"Saved {filename}")
    
    print(f"\nAll {num_samples} samples recorded in 'wake_training_data'.")
    print("Train the model with:")
    print("python -c \"import openwakeword; openwakeword.train(wake_word='hey_karen', positive_path='wake_training_data/', save_path='hey_karen.tflite')\"")

class WakeWordService:
    def _init_(
        self,
        model_paths: Optional[Sequence[str]] = None,
        threshold: Optional[float] = None,
        trigger_level: Optional[int] = None,
        vad_threshold: Optional[float] = None,
        use_speex_ns: Optional[bool] = None,
        device: Optional[int] = None,
        cooldown_ms: Optional[int] = None,
    ):
        self.model_paths = list(model_paths) if model_paths is not None else list(getattr(settings, "WAKE_MODEL_PATHS", []))
        self.threshold = float(threshold if threshold is not None else getattr(settings, "WAKE_THRESHOLD", 0.5))
        self.trigger_level = int(trigger_level if trigger_level is not None else getattr(settings, "WAKE_TRIGGER_LEVEL", 3))
        self.vad_threshold = float(vad_threshold if vad_threshold is not None else getattr(settings, "WAKE_VAD_THRESHOLD", 0.0))
        self.use_speex_ns = bool(use_speex_ns if use_speex_ns is not None else getattr(settings, "WAKE_SPEEX_NS", False))
        self.device = device if device is not None else getattr(settings, "WAKE_DEVICE", None)
        self.cooldown_s = (cooldown_ms if cooldown_ms is not None else getattr(settings, "WAKE_COOLDOWN_MS", 1200)) / 1000.0

        self._model: Model | None = None
        self._stream: sd.InputStream | None = None
        self._queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=32)
        self._worker: asyncio.Task | None = None
        self._event = asyncio.Event()
        self._armed = False
        self._last_trigger_ts = 0.0

    async def _aenter_(self):
        # Load custom or pretrained models
        if not self.model_paths and getattr(settings, "USE_PRETRAINED", False):
            try:
                openwakeword.utils.download_models()
                pretrained_models = [
                    "alexa_v0.1.tflite",
                    "hey_jarvis_v0.1.tflite",
                    "hey_mycroft_v0.1.tflite",
                    "hey_rhasspy_v0.1.tflite",
                ]
                self.model_paths = [m for m in pretrained_models if os.path.exists(m)]
                if not self.model_paths:
                    print("[wake] Warning: No pretrained models found.")
            except Exception as e:
                print(f"[wake] Warning: Failed to download pretrained models: {e}")

        if self.model_paths:
            print(f"[wake] Loading wake word models: {self.model_paths}")
            self._model = Model(
                wakeword_models=self.model_paths,
                vad_threshold=self.vad_threshold,
                enable_speex_noise_suppression=self.use_speex_ns
            )
        else:
            print("[wake] No wake word models available. Running in dummy mode (wakes every 5s).")
            self._model = None

        self._open_stream()
        self._worker = asyncio.create_task(self._listen_loop())
        self._armed = True
        print("[wake] Armed. Say 'Hey Karen' or wait for dummy trigger.")
        return self

    async def _aexit_(self, *a):
        await self._teardown()

    async def wait(self):
        if self._model is None:
            print("[wake] No model; waiting 5 seconds for demo...")
            await asyncio.sleep(5)
            self._event.set()
        else:
            await self._event.wait()
        self._event.clear()

    async def pause(self):
        if not self._armed:
            return
        self._armed = False
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None
        self._close_stream()
        print("[wake] Paused.")

    async def resume(self):
        if self._armed:
            return
        self._open_stream()
        self._worker = asyncio.create_task(self._listen_loop())
        self._armed = True
        print("[wake] Re-armed.")

    def _open_stream(self):
        def cb(indata, frames, time_info, status):
            if status:
                pass
            mono = indata[:, 0]
            try:
                self._queue.put_nowait(mono.copy())
            except asyncio.QueueFull:
                pass

        self._stream = sd.InputStream(
            samplerate=settings.SAMPLE_RATE,
            channels=settings.CHANNELS,
            dtype="float32",
            callback=cb,
            blocksize=0,
            device=self.device,
        )
        self._stream.start()

    def _close_stream(self):
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None

    async def _teardown(self):
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None
        self._close_stream()

    async def _listen_loop(self):
        if self._model is None:
            while True:
                await asyncio.sleep(1)
        else:
            buf = np.empty(0, dtype=np.float32)
            streak = 0
            while True:
                chunk = await self._queue.get()
                buf = chunk if buf.size == 0 else np.concatenate([buf, chunk])
                while buf.size >= FRAME_SAMPLES:
                    frame_f32 = buf[:FRAME_SAMPLES]
                    buf = buf[FRAME_SAMPLES:]
                    frame_i16 = (np.clip(frame_f32, -1.0, 1.0) * 32767.0).astype(np.int16)
                    scores = self._model.predict(frame_i16)
                    max_score = max(scores.values()) if scores else 0.0
                    if max_score >= self.threshold:
                        streak += 1
                    else:
                        streak = max(0, streak - 1)
                    if streak >= self.trigger_level:
                        now = time.monotonic()
                        if now - self._last_trigger_ts >= self.cooldown_s:
                            self._last_trigger_ts = now
                            streak = 0
                            loop = asyncio.get_running_loop()
                            loop.call_soon_threadsafe(self._event.set)
