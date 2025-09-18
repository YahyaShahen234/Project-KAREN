import asyncio
from .audio_io import Mic, Speaker
from .wake import WakeWordService  # <-- wake word (openWakeWord/Porcupine-compatible)
from .stt import STT
from .llm import LLM
from .tts import TTS
from .ui import UI
from .netwatch import NetWatch
from .filler import Filler

async def run_turn(ui: UI, spk: Speaker, stt: STT, llm: LLM, tts: TTS):
    # We open Mic() only for the speech turn (so it doesn't fight the wake listener).
    ui.set_state("listening")
    async with Mic() as mic:
        audio = await mic.capture_until_silence(max_sec=12, silence_ms=700, thresh=0.01)
        rate = getattr(mic, "rate", 16000)

    ui.set_state("transcribing")
    # STT expects (audio, rate)
    text = await stt.transcribe((audio, rate))
    if not text:
        ui.toast("didn't catch that")
        return

    ui.show_user(text)

    # Start filler while waiting for LLM
    ui.set_state("thinking")
    filler = Filler(ui=ui, tts=tts, spk=spk)
    await filler.start()

    try:
        reply, actions = await llm.respond(text)
    finally:
        await filler.stop()

    ui.set_state("speaking")
    ui.show_karen(reply)

    async for chunk in tts.stream(reply):
        await spk.play_pcm(chunk)

async def main():
    ui = UI()
    net = NetWatch()

    # Keep Speaker/STT/LLM/TTS and the WakeWordService open across turns.
    async with Speaker() as spk, STT() as stt, LLM() as llm, TTS() as tts, WakeWordService() as wake:
        ui.set_state("idle")
        while True:
            ok = await net.ok()
            if hasattr(ui, "set_net_ok"):
                ui.set_net_ok(ok)
            if not ok:
                ui.toast("network down — waiting…")
                await asyncio.sleep(1.0)
                continue

            # Block here until the wake phrase is detected (e.g., "hey karen")
            await wake.wait()
            ui.ping()

            try:
                # Release the wake mic so our STT capture can take exclusive control
                await wake.pause()
                await run_turn(ui, spk, stt, llm, tts)
            except Exception as e:
                ui.error(str(e))
            finally:
                # Re-arm wake listening for the next turn
                await wake.resume()
                ui.set_state("idle")

if __name__ == "__main__":
    asyncio.run(main())
