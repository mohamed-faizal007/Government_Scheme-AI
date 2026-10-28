"""Central configuration for the chatbot backend. Import `settings` everywhere."""
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


class Settings(BaseSettings):
    mongodb_uri: str = Field(default="", alias="MONGODB_URI")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="", alias="GROQ_MODEL")
    groq_fallback_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_FALLBACK_MODEL")
    ollama_model: str = Field(default="qwen2.5:3b", alias="OLLAMA_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    chroma_persist_path: str = Field(default="chatbot/data/chroma_db", alias="CHROMA_PERSIST_PATH")
    myscheme_base_url: str = Field(default="https://api.myscheme.gov.in", alias="MYSCHEME_BASE_URL")
    myscheme_site_url: str = Field(default="https://www.myscheme.gov.in", alias="MYSCHEME_SITE_URL")
    myscheme_api_key: str = Field(default="", alias="MYSCHEME_API_KEY")
    sync_api_key: str = Field(default="", alias="SYNC_API_KEY")
    sync_scheduler_enabled: bool = Field(default=True, alias="SYNC_SCHEDULER_ENABLED")
    # Gemini "understanding" layer (see backend/nlu). Blank key disables it.
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="", alias="GEMINI_MODEL")
    gemini_model_fallback: str = Field(default="", alias="GEMINI_MODEL_FALLBACK")
    gemini_model_extra: str = Field(default="gemini-3.5-flash", alias="GEMINI_MODEL_EXTRA")
    gemini_model_order: str = Field(default="", alias="GEMINI_MODEL_ORDER")
    gemini_session_cap: int = Field(default=20, alias="GEMINI_SESSION_CAP")
    gemini_daily_cap: int = Field(default=200, alias="GEMINI_DAILY_CAP")
    # Answer generation: GENERATION_PRIMARY=gemini (default) tries Gemini first, "groq" keeps Groq first.
    generation_primary: str = Field(default="gemini", alias="GENERATION_PRIMARY")
    gemini_gen_timeout: float = Field(default=6.0, alias="GEMINI_GEN_TIMEOUT")  # seconds per generation request
    # Candidate schemes retrieved (and all rule-checked) for profile-based eligibility answers; 5 are shown.
    eligibility_candidates: int = Field(default=30, alias="ELIGIBILITY_CANDIDATES")
    # ANSWER_CACHE=on/off: reuse guard-passed answers to repeated questions (see backend/cache).
    answer_cache: bool = Field(default=True, alias="ANSWER_CACHE")

    @field_validator("groq_fallback_model", mode="before")
    @classmethod
    def _blank_fallback_model(cls, v):
        # A blank GROQ_FALLBACK_MODEL= line in .env must not disable the fallback.
        return v.strip() if isinstance(v, str) and v.strip() else "openai/gpt-oss-120b"

    @field_validator("generation_primary", mode="before")
    @classmethod
    def _known_primary(cls, v):
        return "groq" if isinstance(v, str) and v.strip().lower() == "groq" else "gemini"

    class Config:
        env_file = str(ENV_PATH)
        populate_by_name = True
        extra = "ignore"


settings = Settings()
