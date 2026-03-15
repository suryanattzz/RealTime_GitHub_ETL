from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# GitHub API configuration
GITHUB_API_URL = "https://api.github.com/events"
GITHUB_TOKEN = ""

# Kafka configuration
KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "github-events"

# Streaming configuration
STREAM_DURATION = 600
REQUEST_INTERVAL = 5
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.0
DEDUPE_CACHE_SIZE = 10000
KAFKA_SEND_TIMEOUT = 10

# Data storage
OUTPUT_DIR = str(BASE_DIR / "data")

# Consumer batch settings
BATCH_SIZE = 50