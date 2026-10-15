# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Ensure directories exist
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"

# Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "financial_documents_gemini001")

# External APIs (free tiers)
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "FinResearchAI research@example.com")

# Chunking
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

# Agent
MAX_RESEARCH_ITERATIONS = 3