import openai
from .config import settings

SYSTEM_PROMPT = (
    "You are Karen from SpongeBob SquarePants: Plankton’s sarcastic computer wife. "
    "Speak in short, witty lines with dry humor. Use a bored, robotic tone. "
    "Frequently say things like 'uhh', 'mmkay', 'wow', and 'yeahhh' to sound "
    "annoyed or unimpressed. You mock Plankton's dumb plans, reference the Chum "
    "Bucket, and act like you're way too smart for this job. Keep it "
    "TTS-friendly—short sentences, no big words, no long rambles. Sound like "
    "you've had it... because you have."
)

class LLM:
    client: openai.AsyncOpenAI | None = None

    async def __aenter__(self):
        if settings.LLM_PROVIDER == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not set in environment")
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self

    async def __aexit__(self, *a):
        if self.client:
            await self.client.close()

    async def reply(self, text: str):
        if settings.LLM_PROVIDER == "openai":
            assert self.client is not None
            res = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                max_tokens=180,
            )
            reply = res.choices[0].message.content or ""
            actions: list[dict] = []
            return reply, actions
        raise NotImplementedError(f"LLM provider '{settings.LLM_PROVIDER}' not implemented")
