import os
from dotenv import load_dotenv

load_dotenv()

PHONE_ID     = os.getenv("PHONE_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
APP_SECRET   = os.getenv("APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_API_KEY")
APP_ID = os.getenv("APP_ID")