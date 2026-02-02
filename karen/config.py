from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Runtime configuration for Karen assistant.
    Values can be overridden via environment variables or karen.env file.
    """
    # Providers
    STT_PROVIDER: str = "openai"      # "openai" | "deepgram" | "stub"
    LLM_PROVIDER: str = "openai"      # "openai" | "anthropic" | "stub"
    TTS_PROVIDER: str = "openai"      # "openai" | "azure" | "elevenlabs" | "stub"

    # API keys
    OPENAI_API_KEY: str | None = None
    DEEPGRAM_API_KEY: str | None = None
    AZURE_SPEECH_KEY: str | None = None
    AZURE_SPEECH_REGION: str | None = None
    ELEVENLABS_API_KEY: str | None = None

    # Audio
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1

    # Wake word
    WAKE_THRESHOLD: float = 0.5
    WAKE_TRIGGER_LEVEL: int = 3
    WAKE_COOLDOWN_S: float = 2.0

    # Filler speech
    FILLERS: list[str] = [
        "mhmm…",
        "hmmmmmm",
        "uuuuuuh",
        "hold on…",
        "one moment…",
    ]
    FILLER_MIN_S: float = 2.5
    FILLER_MAX_S: float = 4.0

    class Config:
        env_file = "karen.env"
        env_file_encoding = "utf-8"

settings = Settings()
