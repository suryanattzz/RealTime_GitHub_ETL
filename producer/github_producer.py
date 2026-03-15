import time
import json
from collections import deque

import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.config import (
    GITHUB_API_URL,
    GITHUB_TOKEN,
    KAFKA_BROKER,
    KAFKA_TOPIC,
    STREAM_DURATION,
    REQUEST_INTERVAL,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    BACKOFF_FACTOR,
    DEDUPE_CACHE_SIZE,
    KAFKA_SEND_TIMEOUT,
)


def _build_http_session():
    retry = Retry(
        total=MAX_RETRIES,
        connect=MAX_RETRIES,
        read=MAX_RETRIES,
        status=MAX_RETRIES,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        backoff_factor=BACKOFF_FACTOR,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)

    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "User-Agent": "social-media-streaming-etl",
        }
    )

    if GITHUB_TOKEN:
        session.headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return session


def _is_rate_limited(response):
    remaining = response.headers.get("X-RateLimit-Remaining")
    return response.status_code in (403, 429) and remaining == "0"


def _sleep_until_rate_limit_reset(response):
    reset_epoch = int(response.headers.get("X-RateLimit-Reset", "0"))
    wait_seconds = max(reset_epoch - int(time.time()), REQUEST_INTERVAL)
    print(f"Rate limit reached. Sleeping {wait_seconds}s before retrying...")
    time.sleep(wait_seconds)


def _remember_event_id(event_id, seen_ids, event_window):
    if not event_id:
        return False

    if event_id in seen_ids:
        return True

    if len(event_window) >= DEDUPE_CACHE_SIZE:
        oldest = event_window.popleft()
        seen_ids.discard(oldest)

    event_window.append(event_id)
    seen_ids.add(event_id)
    return False


def start_github_stream():

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    session = _build_http_session()

    start_time = time.time()
    seen_ids = set()
    event_window = deque()
    sent_count = 0
    skipped_duplicates = 0

    print("Starting GitHub streaming...\n")

    try:
        while (time.time() - start_time) < STREAM_DURATION:

            try:
                response = session.get(GITHUB_API_URL, timeout=REQUEST_TIMEOUT)

                if _is_rate_limited(response):
                    _sleep_until_rate_limit_reset(response)
                    continue

                if response.status_code != 200:
                    print("GitHub API error:", response.status_code)
                    time.sleep(REQUEST_INTERVAL)
                    continue

                events = response.json()

                if not isinstance(events, list):
                    print("Invalid response from GitHub:", events)
                    time.sleep(REQUEST_INTERVAL)
                    continue

                print(f"Fetched {len(events)} events")

                for event in events:
                    event_id = event.get("id")
                    if _remember_event_id(event_id, seen_ids, event_window):
                        skipped_duplicates += 1
                        continue

                    try:
                        future = producer.send(KAFKA_TOPIC, event)
                        future.get(timeout=KAFKA_SEND_TIMEOUT)
                        sent_count += 1
                    except KafkaError as send_error:
                        print("Kafka send error:", send_error)
                        continue

                    event_type = event.get("type", "unknown")
                    repo = event.get("repo", {}).get("name", "unknown")
                    actor = event.get("actor", {}).get("login", "unknown")
                    print(f"Sent -> {event_type} | {repo} | {actor}")

            except requests.RequestException as request_error:
                print("Request error:", request_error)
            except json.JSONDecodeError as parse_error:
                print("JSON parse error:", parse_error)
            except Exception as error:
                print("Unexpected producer error:", error)

            time.sleep(REQUEST_INTERVAL)

    finally:
        print("\nStreaming finished.")
        print(f"Total sent events: {sent_count}")
        print(f"Skipped duplicate events: {skipped_duplicates}")

        producer.flush()
        producer.close()
        session.close()