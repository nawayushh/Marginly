import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings(BaseModel):
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    RESTAURANT_NAME: str = os.getenv("RESTAURANT_NAME", "The Rustic Ladle Café")
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "INR")
    DEFAULT_CURRENCY_SYMBOL: str = os.getenv("DEFAULT_CURRENCY_SYMBOL", "₹")

    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(Path(__file__).parent / "marginly.db"))

    # Local AI (Qwen in LM Studio via OpenAI-compatible API)
    LM_STUDIO_BASE_URL: str = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    LM_STUDIO_API_KEY: str = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
    LM_STUDIO_MODEL: str = os.getenv("LM_STUDIO_MODEL", "qwen2.5-7b-instruct")
    LM_STUDIO_TIMEOUT_SECONDS: float = float(os.getenv("LM_STUDIO_TIMEOUT_SECONDS", "45.0"))

    # Gemini API Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Calculation thresholds
    POPULARITY_FACTOR: float = float(os.getenv("POPULARITY_FACTOR", "1.0"))
    PRICE_ALERT_THRESHOLD_PERCENT: float = float(os.getenv("PRICE_ALERT_THRESHOLD_PERCENT", "5.0"))

settings = Settings()