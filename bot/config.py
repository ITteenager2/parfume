import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "parfum_bot.db")  # Provide a default value
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

# Validate required environment variables
required_vars = ["TELEGRAM_TOKEN", "OPENAI_API_KEY", "ENCRYPTION_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
