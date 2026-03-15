import argparse

from consumer.github_consumer import run_consumer
from producer.github_producer import start_github_stream

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Kafka ETL runner")
    parser.add_argument(
        "--mode",
        choices=["producer", "consumer"],
        default="producer",
        help="Choose which pipeline component to run.",
    )
    args = parser.parse_args()

    if args.mode == "producer":
        start_github_stream()
    else:
        run_consumer()