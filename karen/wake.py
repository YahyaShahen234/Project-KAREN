# wake.py — Offline wake-word (“Hey Karen”) using openWakeWord on Raspberry Pi
from __future__ import annotations
import asyncio, time
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

# Optional settings import; falls back to sane defaults for Pi
try:
    from .config import settings
except Exception:
    class _S:
        # Point to your custom .tflite model(s) once you train “hey karen”, otherwise leave empty to use built-ins
        WAKE_MODEL_PATHS: list[str] = []      # e.g. ["./models/hey_karen_en.tflite"]
        # TEMP for testing before you train “hey karen”, we can load all built-ins:
        USE_PRETRAINED = True                 # downloads once, then cached
        WAKE_THRESHOLD = 0.5                  # score to trigger (0..1)
        WAKE_TRIGGER_LEVEL = 3                # frames over threshold to confirm
        WAKE_COOLDOWN_MS = 1200               # ignore re-triggers for this long
        WAKE_DEVICE = None                    # ALSA index or None
        WAKE_VAD_THRESHOLD = 0.5              # gate by Silero VAD (reduces falses)
        WAKE_SPEEX_NS = False                 # enable Speex noise suppression (arm64)
        SAMPLE_RATE = 16000
        CHANNELS = 1
    settings = _S()  # type: ignore


FRAME_MS = 80                      # openWakeWord likes multiples of 80 ms
FRAME_SAMPLES = int(0.001 * FRAME_MS * settings.SAMPLE_RATE)  # 1280 @ 16k


class WakeWordService:
    """
    Usage:
        async with WakeWordService() as wake:
            while True:
                await wake.wait()   # blocks until wake word
                await wake.pause()  # release mic for STT
                # ... run STT/LLM/TTS ...
                await wake.resume() # re-arm
    """
    def __init__(
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

    async def __aenter__(self):
        # (One-time) download pre-trained models if user hasn’t provided custom model(s).
        # This lets you test quickly with a built-in like “jarvis”, then swap to your “hey_karen.tflite”.
        if not self.model_paths and getattr(settings, "USE_PRETRAINED", True):
            try:
                openwakeword.utils.download_models()
            except Exception:
                # If offline, we just proceed; Model() will raise if files missing
                pass

        self._model = Model(
            wakeword_models=self.model_paths if self.model_paths else None,
            vad_threshold=self.vad_threshold,                      # built-in VAD gate
            enable_speex_noise_suppression=self.use_speex_ns       # optional NS on arm64
        )
        self._open_stream()
        self._worker = asyncio.create_task(self._listen_loop())
        self._armed = True
        print("[wake] Armed. Say your wake phrase (e.g., 'hey karen').")
        return self

    async def __aexit__(self, *a):
        await self._teardown()

    async def wait(self):
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

    # ---------- internals ----------
    def _open_stream(self):
        def cb(indata, frames, time_info, status):
            if status:
                # Avoid prints in callback; occasional overruns are normal
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
            blocksize=0,                     # let ALSA choose; we reframe to 80 ms
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

    async def _listen_loop(self):
        assert self._model is not None
        buf = np.empty(0, dtype=np.float32)
        streak = 0

        while True:
            chunk = await self._queue.get()
            buf = chunk if buf.size == 0 else np.concatenate([buf, chunk])

            while buf.size >= FRAME_SAMPLES:
                frame_f32 = buf[:FRAME_SAMPLES]
                buf = buf[FRAME_SAMPLES:]

                # Convert float32 [-1,1] -> int16 PCM as expected by openWakeWord
                frame_i16 = (np.clip(frame_f32, -1.0, 1.0) * 32767.0).astype(np.int16)

                # Get prediction scores for all loaded wake-word models
                scores = self._model.predict(frame_i16)  # dict{name: score}
                max_score = max(scores.values()) if scores else 0.0

                if max_score >= self.threshold:
                    streak += 1
                else:
                    streak = max(0, streak - 1)  # gentle decay

                if streak >= self.trigger_level:
                    now = time.monotonic()
                    if now - self._last_trigger_ts >= self.cooldown_s:
                        self._last_trigger_ts = now
                        streak = 0
                        loop = asyncio.get_running_loop()
                        loop.call_soon_threadsafe(self._event.set)
