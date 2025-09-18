import numpy as np
import openai
from .config import settings

def resample(audio: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    """Ugly resampling using numpy.interp. Good enough for this."""
    if from_rate == to_rate:
        return audio

    secs = len(audio) / from_rate
    samps = int(secs * to_rate)
    if samps == 0:
        return np.array([], dtype=np.float32)

    resampled_audio = np.interp(
        np.linspace(0, 1, samps, endpoint=False),      # New sample points
        np.linspace(0, 1, len(audio), endpoint=False), # Old sample points
        audio
    )
    return resampled_audio.astype(np.float32)


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

    async def stream(self, text: str):
        if settings.TTS_PROVIDER == "stub":
            sr = settings.SAMPLE_RATE
            t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
            tone = 0.1 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
            yield tone
            return

        if settings.TTS_PROVIDER == "openai":
            if not self.client:
                raise ConnectionError("OpenAI client not initialized")

            response = await self.client.audio.speech.with_streaming_response.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="pcm", # 24kHz, 16-bit, mono
            )

            async for chunk_bytes in response.iter_bytes(chunk_size=1024):
                if not chunk_bytes:
                    continue
                # Convert 16-bit PCM bytes to float32 numpy array
                audio_24k = np.frombuffer(chunk_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                # Resample to 16kHz
                audio_16k = resample(audio_24k, from_rate=24000, to_rate=settings.SAMPLE_RATE)

                yield audio_16k
            return

        raise NotImplementedError(f"TTS provider '{settings.TTS_PROVIDER}' not implemented")
