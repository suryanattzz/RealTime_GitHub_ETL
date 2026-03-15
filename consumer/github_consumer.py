from kafka import KafkaConsumer
import json
import os
from datetime import datetime

from config.config import (
    KAFKA_BROKER,
    KAFKA_TOPIC,
    OUTPUT_DIR,
    BATCH_SIZE
)


def _build_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )


def _write_batch(batch):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = os.path.join(
        OUTPUT_DIR,
        f"github_events_{timestamp}.json",
    )

    with open(filename, "w", encoding="utf-8") as output_file:
        json.dump(batch, output_file, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(batch)} events to {filename}\n")


def run_consumer():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    consumer = _build_consumer()
    batch = []

    print("Consumer started. Listening for events...\n")

    try:
        for message in consumer:
            event = message.value

            if not isinstance(event, dict):
                print("Invalid event skipped:", event)
                continue

            batch.append(event)

            event_type = event.get("type", "unknown")
            repo = event.get("repo", {}).get("name", "unknown")
            actor = event.get("actor", {}).get("login", "unknown")

            print(f"Received -> {event_type} | {repo} | {actor}")

            if len(batch) >= BATCH_SIZE:
                _write_batch(batch)
                batch = []

    except KeyboardInterrupt:
        print("\nConsumer stopped manually.")

    finally:
        if batch:
            _write_batch(batch)
            print(f"Saved remaining {len(batch)} events")

        consumer.close()
        print("Consumer closed.")


if __name__ == "__main__":
    run_consumer()