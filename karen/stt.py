import io
import wave
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

    async def transcribe(self, audio_tuple):
        audio, rate = audio_tuple
        if settings.STT_PROVIDER == "stub":
            return "what time is it"

        if settings.STT_PROVIDER == "openai":
            if not self.client:
                raise ConnectionError("OpenAI client not initialized")

            # Convert float32 numpy array to 16-bit WAV bytes
            wav_bytes = io.BytesIO()
            with wave.open(wav_bytes, "wb") as wav_file:
                wav_file.setnchannels(settings.CHANNELS)
                wav_file.setsampwidth(2)  # 16-bit PCM
                wav_file.setframerate(rate)
                wav_file.writeframes((audio * 32767).astype(np.int16).tobytes())
            wav_bytes.seek(0)

            # The OpenAI client needs a file-like object with a name
            # so we create a tuple for the file argument.
            # (filename, file-like-object)
            wav_file_tuple = ("audio.wav", wav_bytes)

            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=wav_file_tuple,
            )
            return transcript.text

        raise NotImplementedError(f"STT provider '{settings.STT_PROVIDER}' not implemented")
