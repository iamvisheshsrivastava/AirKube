# AirKube dbt Project

This project builds the analytics layer for the AirKube news warehouse on BigQuery.

## What it includes
- A raw source definition for the news ingestion tables
- A staging model that normalizes text and derives common fields
- A mart for daily article counts by source
- Column-level tests for freshness and data quality

## How to use
1. Copy `profiles.yml.example` into your local dbt profiles directory and adjust the target if needed.
2. Ensure `GCP_PROJECT_ID`, `NEWS_BQ_DATASET`, and `NEWS_RAW_TABLE` are set in the environment.
3. Run `dbt build` from this directory.
