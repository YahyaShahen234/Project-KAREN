from .config import settings
class STT:
async def __aenter__(self):
return self
async def __aexit__(self, *a):
pass
async def transcribe(self, audio_tuple):
audio, rate = audio_tuple
if settings.STT_PROVIDER == "stub":
return "what time is it"
# --- Hook: implement cloud STT here (OpenAI/Deepgram) ---
# return text
raise NotImplementedError("STT provider not implemented")
