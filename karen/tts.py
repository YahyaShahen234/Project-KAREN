import numpy as np
from .config import settings
class TTS:
async def __aenter__(self):
return self
async def __aexit__(self, *a):
pass
async def stream(self, text: str):
if settings.TTS_PROVIDER == "stub":
# Generate a short placeholder tone so the audio path is tested
sr = 16000
t = np.linspace(0, 0.5, int(sr*0.5), endpoint=False)
tone = 0.1*np.sin(2*np.pi*440*t).astype(np.float32)
yield tone
return
# --- Hook: stream PCM from cloud TTS ---
raise NotImplementedError("TTS provider not implemented")
