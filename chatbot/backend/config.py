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

    class Config:
        env_file = str(ENV_PATH)
        populate_by_name = True
        extra = "ignore"


settings = Settings()
