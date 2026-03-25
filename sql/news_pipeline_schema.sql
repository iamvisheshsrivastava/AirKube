CREATE SCHEMA IF NOT EXISTS `{project_id}.{dataset_id}`;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.{raw_table}` (
  article_id STRING NOT NULL,
  title STRING NOT NULL,
  source_name STRING NOT NULL,
  source_id STRING,
  author STRING,
  description STRING,
  content STRING,
  url STRING NOT NULL,
  published_at TIMESTAMP NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  query STRING NOT NULL,
  batch_id STRING NOT NULL,
  language STRING NOT NULL,
  raw_payload JSON
)
PARTITION BY DATE(fetched_at)
CLUSTER BY source_name, language;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.{processed_table}` (
  article_id STRING NOT NULL,
  title STRING NOT NULL,
  source_name STRING NOT NULL,
  published_at TIMESTAMP NOT NULL,
  published_date DATE NOT NULL,
  content STRING,
  description STRING,
  content_length INT64 NOT NULL,
  url STRING NOT NULL,
  sentiment_placeholder STRING NOT NULL,
  ingestion_batch_id STRING NOT NULL,
  query STRING NOT NULL
)
PARTITION BY published_date
CLUSTER BY source_name, sentiment_placeholder;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.{daily_counts_table}` (
  published_date DATE NOT NULL,
  source_name STRING NOT NULL,
  article_count INT64 NOT NULL,
  sentiment_ready_count INT64 NOT NULL
)
PARTITION BY published_date
CLUSTER BY source_name;