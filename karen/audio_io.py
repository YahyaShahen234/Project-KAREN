import asyncio
import numpy as np
import sounddevice as sd
from .config import settings
class Mic:
def __init__(self, rate: int | None = None):
self.rate = rate or settings.SAMPLE_RATE
self.channels = settings.CHANNELS
self._queue = asyncio.Queue()
self._stream = None
async def __aenter__(self):
loop = asyncio.get_running_loop()
def cb(indata, frames, time, status):
if status: # print xruns, etc.
pass
# Copy to avoid reuse
loop.call_soon_threadsafe(self._queue.put_nowait, indata.copy())
self._stream = sd.InputStream(samplerate=self.rate,
channels=self.channels, callback=cb, blocksize=0)
self._stream.start()
return self
async def __aexit__(self, *args):
if self._stream:
self._stream.stop(); self._stream.close(); self._stream = None
async def capture_until_silence(self, max_sec: int | None = None,
silence_ms: int = 600):
max_sec = max_sec or settings.MAX_SEC
chunk_ms = 30
chunk_samples = int(self.rate * chunk_ms / 1000)
silence_chunks_needed = silence_ms // chunk_ms
buf = []
silent = 0
total_ms = 0
while total_ms < max_sec * 1000:
data = await self._queue.get()
mono = data[:,0] if data.ndim > 1 else data
buf.append(mono.copy())
# simple VAD based on RMS
rms = np.sqrt(np.mean(mono**2))
if rms < 0.01:
silent += 1
else:
silent = 0
total_ms += int(len(mono) / self.rate * 1000)
if silent >= silence_chunks_needed and total_ms > 500: # at least
0.5s
break
audio = np.concatenate(buf) if buf else np.zeros(1, dtype=np.float32)
return (audio.astype(np.float32), self.rate)
class Speaker:
def __init__(self, rate: int | None = None):
self.rate = rate or settings.SAMPLE_RATE
self._stream = None
async def __aenter__(self):
self._stream = sd.OutputStream(samplerate=self.rate, channels=1)
self._stream.start()
return self
async def __aexit__(self, *args):
if self._stream:
self._stream.stop(); self._stream.close(); self._stream = None
async def play_pcm(self, pcm: np.ndarray):
# pcm: float32 [-1,1]
self._stream.write(pcm.astype(np.float32))
async def play_chunks(self, gen):
async for chunk in gen:
await self.play_pcm(chunk)

