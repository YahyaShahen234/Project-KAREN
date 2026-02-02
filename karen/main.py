import asyncio
from .audio_io import Mic, Speaker
from .wake import WakeWordService, record_wakeword_samples
from .stt import STT
from .llm import LLM
from .tts import TTS
from .ui import UI
from .netwatch import NetWatch
from .filler import Filler
import os

async def run_turn(ui: UI, spk: Speaker, stt: STT, llm: LLM, tts: TTS):
    ui.set_state("listening")
    async with Mic() as mic:
        audio = await mic.capture_until_silence(max_sec=12, silence_ms=700, thresh=0.01)
        rate = getattr(mic, "rate", 16000)

    ui.set_state("transcribing")
    text = await stt.transcribe((audio, rate))
    if not text:
        ui.toast("What, mumbling already? Speak up, genius!")
        return

    ui.show_user(text)

    ui.set_state("thinking")
    filler = Filler(ui=ui, tts=tts, spk=spk)
    await filler.start()

    try:
        reply, actions = await llm.respond(text)
        reply = f"Ugh, fine, here's your answer: {reply}"
    finally:
        await filler.stop()

    ui.set_state("speaking")
    ui.show_karen(reply)

    async for chunk in tts.stream(reply):
        await spk.play_pcm(chunk)

async def main():
    ui = UI()
    net = NetWatch()

    custom_model = "hey_karen.tflite"
    training_dir = "wake_training_data"
    model_paths = [custom_model] if os.path.exists(custom_model) else []

    if not model_paths and not (os.path.exists(training_dir) and os.listdir(training_dir)):
        print("\nNo 'Hey Karen' model or training data found.")
        print("Want to record 10 'Hey Karen' samples to train a model? (y/n): ", end="")
        choice = input().strip().lower()
        if choice in ["y", "yes"]:
            await record_wakeword_samples(num_samples=10)
            print("\nRecording complete. Train the model with:")
            print("python -c \"import openwakeword; openwakeword.train(wake_word='hey_karen', positive_path='wake_training_data/', save_path='hey_karen.tflite')\"")
            print("Re-run this script after training.")
            return
        else:
            print("No recording. Using dummy mode (wakes every 5s).")

    async with Speaker() as spk, STT() as stt, LLM() as llm, TTS() as tts, WakeWordService(model_paths=model_paths) as wake:
        ui.set_state("idle")
        ui.toast("KAREN online. Don't waste my circuits, what's up?")
        while True:
            ok = await net.ok()
            if hasattr(ui, "set_net_ok"):
                ui.set_net_ok(ok)
            if not ok:
                ui.toast("Network's down. What am I, a miracle worker? Waiting...")
                await asyncio.sleep(1.0)
                continue

            await wake.wait()
            ui.ping()
            ui.toast("Alright, you got my attention. What's the big idea?")

            try:
                await wake.pause()
                await run_turn(ui, spk, stt, llm, tts)
            except Exception as e:
                ui.error(f"Oh, great, something broke: {str(e)}. Typical.")
            finally:
                await wake.resume()
                ui.set_state("idle")
                ui.toast("Back to waiting. Don't make me sit here all day.")

if _name_ == "_main_":
    asyncio.run(main())
