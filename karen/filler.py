import asyncio, random
from .config import settings

class Filler:
    """Speaks short interjections while in thinking state to mask latency."""
    def __init__(self, ui, tts, spk):
        self.ui = ui
        self.tts = tts
        self.spk = spk
        self._task = None
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self):
        while self._running:
            delay = random.uniform(settings.FILLER_MIN_S, settings.FILLER_MAX_S)
            await asyncio.sleep(delay)
            if not self._running:
                break
            phrase = random.choice(settings.FILLERS)
            # Show on screen to reinforce "alive" feeling
            self.ui.show_karen(f"[thinking] {phrase}")
            # Speak with current TTS (stub or real)
            async for chunk in self.tts.stream(phrase):
                await self.spk.play_pcm(chunk)
