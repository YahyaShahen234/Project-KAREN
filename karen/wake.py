# MVP: Use keyboard hotkey as a stand-in for wake word
from pynput import keyboard
import asyncio
class WakeService:
def __init__(self, key='space'):
  self.key = getattr(keyboard.Key, key) if hasattr(keyboard.Key, key) else
key
self._event = asyncio.Event()
self._listener = None
async def __aenter__(self):
def on_press(k):
if k == self.key:
try:
loop = asyncio.get_running_loop()
loop.call_soon_threadsafe(self._event.set)
except RuntimeError:
pass
self._listener = keyboard.Listener(on_press=on_press)
self._listener.start()
return self
async def __aexit__(self, *a):
if self._listener:
self._listener.stop()
async def wait(self):
print("[wake] Press SPACE to talk…")
await self._event.wait()
self._event.clear()
