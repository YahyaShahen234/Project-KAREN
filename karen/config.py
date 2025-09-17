from pydantic import BaseSettings

class Settings(BaseSettings):
    # Swap these to real providers when ready
    STT_PROVIDER: str = "stub"      # "openai" | "deepgram" | etc
    LLM_PROVIDER: str = "stub"      # "openai" | "anthropic" | etc
    TTS_PROVIDER: str = "stub"      # "openai" | "azure" | "elevenlabs"

    # API keys (only used when provider != stub)
    OPENAI_API_KEY: str | None = None
    DEEPGRAM_API_KEY: str | None = None
    AZURE_SPEECH_KEY: str | None = None
    AZURE_SPEECH_REGION: str | None = None
    ELEVENLABS_API_KEY: str | None = None

    # Audio
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    MAX_SEC: int = 12

    # Wake word
    WAKEWORD: str = "karen"

    # Thinking fillers
    FILLERS: list[str] = [
        "mhmm…",
        "mmmmmm",
        "uhhhh",
        "hold on…",
        "one moment…",
    ]
    FILLER_MIN_S: float = 2.5
    FILLER_MAX_S: float = 4.0

    class Config:
        env_file = "/etc/karen.env"
        env_file_encoding = "utf-8"

settings = Settings()
