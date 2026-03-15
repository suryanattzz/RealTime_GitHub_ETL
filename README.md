# Social Media Streaming ETL (GitHub Events)

This project streams GitHub events with local Kafka, stores raw events as JSON files, then processes them in Databricks using a medallion architecture (Bronze, Silver, Gold).

## What I Implemented

1. Streamed GitHub events locally with Kafka producer and consumer.
2. Persisted ingested events as JSON snapshots in `data/`.
3. Manually uploaded raw JSON files to a Databricks Volume (Community Edition workflow).
4. Processed data through Bronze -> Silver -> Gold notebooks in Databricks.
5. Built a dashboard in Databricks from Gold-layer tables.

## Why Manual Databricks Ingestion

I am using Databricks Community Edition. Because of CE limits for production-style, direct Kafka streaming setup, I used local Kafka ingestion + JSON landing, then uploaded files to Databricks Volume for processing.

## Architecture

GitHub Events API -> Local Kafka Producer -> Kafka Topic -> Local Kafka Consumer -> JSON files (`data/`) -> Databricks Volume -> Bronze -> Silver -> Gold -> Databricks Dashboard

## End-to-End Data Flow

1. GitHub public events are fetched from the GitHub Events API by the local producer.
2. Producer publishes each event to Kafka topic `github-events`.
3. Local consumer reads Kafka events in batches and saves JSON files in `data/`.
4. JSON files are uploaded to Databricks Volume (Community Edition compatible path).
5. Bronze notebook ingests raw JSON into table:
	`github_stream_event_catalog.bronze_layer.github_events_raw`
6. Silver notebook cleans and standardizes data into table:
	`github_stream_event_catalog.silver_layer.silver_github_events`
7. Gold notebook creates analytics-ready tables in:
	`github_stream_event_catalog.gold_layer.*`
8. Databricks dashboard reads Gold tables for KPI cards and charts.

Flow summary:

GitHub API -> Kafka -> Local JSON Landing -> Databricks Volume -> Bronze Table -> Silver Table -> Gold Tables -> Dashboard / External DB Exports

## Project Highlights

- Retry and rate-limit aware producer
- Batch consumer and raw JSON landing
- Medallion transformation pipeline in Databricks
- Curated notebook copies for GitHub sharing

## Repository Map

- `producer/` GitHub streaming producer
- `consumer/` Kafka consumer and data sink
- `config/` runtime configuration
- `kafka-docker/` local Kafka setup
- `notebooks/` working notebooks
- `notebooks_clean/` curated notebooks for portfolio/repo
- `dashboard/` screenshots and dashboard prompt templates

## Setup

1. Create/activate virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start Kafka (from `kafka-docker/`):

```bash
docker compose up -d
```

## Run Pipeline

Producer mode:

```bash
python main.py --mode producer
```

Consumer mode:

```bash
python main.py --mode consumer
```

## Databricks Output Tables

Core serving table:

- `github_stream_event_catalog.gold_layer.gold_github_events`

Dashboard aggregate tables:

- `github_stream_event_catalog.gold_layer.repo_activity`
- `github_stream_event_catalog.gold_layer.actor_activity`
- `github_stream_event_catalog.gold_layer.event_type_distribution`
- `github_stream_event_catalog.gold_layer.activity_over_time`
- `github_stream_event_catalog.gold_layer.branch_activity`
- `github_stream_event_catalog.gold_layer.unique_developers`
- `github_stream_event_catalog.gold_layer.org_activity`

## Export Gold Tables to MySQL / PostgreSQL

You can export any Gold table from Databricks using Spark JDBC writes.

Example for MySQL:

```python
df = spark.table("github_stream_event_catalog.gold_layer.gold_github_events")

(df.write
	.format("jdbc")
	.option("url", "jdbc:mysql://<host>:3306/<database>")
	.option("dbtable", "gold_github_events")
	.option("user", "<username>")
	.option("password", "<password>")
	.option("driver", "com.mysql.cj.jdbc.Driver")
	.mode("overwrite")
	.save())
```

Example for PostgreSQL:

```python
df = spark.table("github_stream_event_catalog.gold_layer.gold_github_events")

(df.write
	.format("jdbc")
	.option("url", "jdbc:postgresql://<host>:5432/<database>")
	.option("dbtable", "gold_github_events")
	.option("user", "<username>")
	.option("password", "<password>")
	.option("driver", "org.postgresql.Driver")
	.mode("overwrite")
	.save())
```

Notes:

- Use Databricks secret scopes for credentials instead of hardcoding.
- For incremental loads, use `append` mode and add a watermark/key-based upsert strategy.
- Ensure your Databricks cluster has the JDBC driver package for MySQL/PostgreSQL.

## Notebook Workflow

- `notebooks/`: original working notebooks.
- `notebooks_clean/`: curated notebooks with only important cells.
- Empty cells and comment-only cells are removed in curated notebooks.
- Relevant markdown titles are added before code steps.
- Important retained cells keep their available outputs.

### Why outputs were removed earlier

Outputs are often removed in clean notebooks to reduce git noise and avoid huge diffs. In this repo, curated notebooks now keep useful outputs for key steps so reviewers can see both logic and results.

## Dashboard

- For now, dashboard evidence is kept as screenshot(s) in `dashboard/screenshots/`.
- Genie prompt template: `dashboard/genie_dashboard_template.md`

![Databricks Dashboard Screenshot](dashboard/screenshots/Dashboard%20screenshot.jpeg)

## Notes

- Generated JSON payloads in `data/` are ignored by git.
- Keep secrets out of source control. Use `.env.example` as reference.
