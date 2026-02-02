import io, wave
import openai
import numpy as np
from .config import settings

class STT:
    client: openai.AsyncOpenAI | None = None

    async def __aenter__(self):
        if settings.STT_PROVIDER == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not set in environment")
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self

    async def __aexit__(self, *a):
        if self.client:
            await self.client.close()

    async def transcribe(self, audio: np.ndarray, rate: int) -> str:
        if settings.STT_PROVIDER == "openai":
            assert self.client is not None
            audio16 = np.clip(audio, -1.0, 1.0)
            audio16 = (audio16 * 32767.0).astype(np.int16)
            wav_bytes = io.BytesIO()
            with wave.open(wav_bytes, "wb") as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
                wf.writeframes(audio16.tobytes())
            wav_bytes.seek(0)
            file_tuple = ("audio.wav", wav_bytes)
            tr = await self.client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=file_tuple,
            )
            return tr.text or ""
        raise NotImplementedError(f"STT provider '{settings.STT_PROVIDER}' not implemented")
