import asyncio
from .audio_io import Mic, Speaker
from .wake import WakeService
from .stt import STT
from .llm import LLM
from .tts import TTS
from .ui import UI
from .netwatch import NetWatch
from .filler import Filler

async def run_turn(ui, mic, spk, stt, llm, tts):
    ui.set_state("listening")
    audio = await mic.capture_until_silence(max_sec=12)
    ui.set_state("transcribing")
    text = await stt.transcribe(audio)
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
    async with Mic() as mic, Speaker() as spk, STT() as stt, LLM() as llm, TTS() as tts, WakeService() as wake:
        ui.set_state("idle")
        while True:
            ok = await net.ok()
            ui.set_net_ok(ok) if hasattr(ui, 'set_net_ok') else None
            if not ok:
                ui.toast("network down — waiting…")
                await asyncio.sleep(1.0)
                continue
            await wake.wait()
            ui.ping()
            try:
                await run_turn(ui, mic, spk, stt, llm, tts)
            except Exception as e:
                ui.error(str(e))
            finally:
                ui.set_state("idle")

if __name__ == "__main__":
    asyncio.run(main())
