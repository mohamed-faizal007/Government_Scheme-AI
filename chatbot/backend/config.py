"""Central configuration for the chatbot backend. Import `settings` everywhere."""
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


class Settings(BaseSettings):
    mongodb_uri: str = Field(default="", alias="MONGODB_URI")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="", alias="GROQ_MODEL")
    ollama_model: str = Field(default="qwen2.5:3b", alias="OLLAMA_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    chroma_persist_path: str = Field(default="chatbot/data/chroma_db", alias="CHROMA_PERSIST_PATH")
    myscheme_base_url: str = Field(default="https://api.myscheme.gov.in", alias="MYSCHEME_BASE_URL")
    myscheme_site_url: str = Field(default="https://www.myscheme.gov.in", alias="MYSCHEME_SITE_URL")
    myscheme_api_key: str = Field(default="", alias="MYSCHEME_API_KEY")
    sync_api_key: str = Field(default="", alias="SYNC_API_KEY")
    sync_scheduler_enabled: bool = Field(default=True, alias="SYNC_SCHEDULER_ENABLED")

    class Config:
        env_file = str(ENV_PATH)
        populate_by_name = True
        extra = "ignore"


settings = Settings()
