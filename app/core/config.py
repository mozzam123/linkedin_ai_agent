from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    # OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL")


settings = Settings()