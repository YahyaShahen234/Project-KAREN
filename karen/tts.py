import numpy as np
from typing import AsyncGenerator
import openai
from .config import settings

def resample(audio: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    """Simple linear resampler using numpy.interp."""
    if from_rate == to_rate or len(audio) == 0:
        return audio.astype(np.float32, copy=False)
    secs = len(audio) / from_rate
    samps = max(int(secs * to_rate), 0)
    if samps == 0:
        return np.array([], dtype=np.float32)
    x_old = np.linspace(0.0, 1.0, len(audio), endpoint=False, dtype=np.float64)
    x_new = np.linspace(0.0, 1.0, samps, endpoint=False, dtype=np.float64)
    y = np.interp(x_new, x_old, audio.astype(np.float32))
    return y.astype(np.float32)

class TTS:
    client: openai.AsyncOpenAI | None = None

    async def __aenter__(self):
        if settings.TTS_PROVIDER == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not set in environment")
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self

    async def __aexit__(self, *a):
        if self.client:
            await self.client.close()

    async def stream(self, text: str) -> AsyncGenerator[np.ndarray, None]:
        """Yield PCM chunks (float32, mono, [-1,1]) at settings.SAMPLE_RATE."""
        if settings.TTS_PROVIDER == "openai":
            assert self.client is not None
            # Request raw PCM (24kHz, 16-bit mono). We'll chunk and resample.
            resp = await self.client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="sage",
                input=text,
                response_format="pcm",
            )
            pcm_bytes: bytes = resp.read() if hasattr(resp, "read") else bytes(resp)  # type: ignore
            # Slice into frames of ~50 ms at 24kHz
            frame_samples = int(0.05 * 24000)
            sample_width = 2  # int16
            step = frame_samples * sample_width
            for i in range(0, len(pcm_bytes), step):
                frame = pcm_bytes[i:i+step]
                if not frame:
                    continue
                audio_24k = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
                audio_out = resample(audio_24k, from_rate=24000, to_rate=settings.SAMPLE_RATE)
                yield audio_out
            return
        raise NotImplementedError(f"TTS provider '{settings.TTS_PROVIDER}' not implemented")
