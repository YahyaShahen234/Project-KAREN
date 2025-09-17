from .config import settings
SYSTEM_PROMPT = (
"You are Karen, a witty, mildly sarcastic assistant. Be concise. "
)
class LLM:
async def __aenter__(self):
return self
async def __aexit__(self, *a):
pass
async def respond(self, text: str):
if settings.LLM_PROVIDER == "stub":
reply = f"You said: {text}. Also, it's a lovely day to optimize
latency."
actions = []
return reply, actions
# --- Hook: call cloud LLM (stream or non-stream) ---
raise NotImplementedError("LLM provider not implemented")
