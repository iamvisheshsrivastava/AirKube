from datetime import datetime, timezone
import logging
import os
from typing import Any, Dict, List

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from ml.env import load_env

load_env()

from ml.news_integration import build_ml_trigger_conf
from ml.news_pipeline import (
    BQ_DATASET,
    DAILY_COUNTS_TABLE,
    GCP_PROJECT_ID,
    GCS_BUCKET_NAME,
    NEWS_API_KEY,
    PROCESSED_TABLE,
    RAW_TABLE,
    build_daily_counts_table_id,
    build_pipeline_summary,
    build_audit_event,
    build_data_quality_summary,
    build_processed_table_id,
    build_raw_table_id,
    clean_and_transform_articles,
    fetch_incremental_articles,
    get_incremental_watermark,
    load_jsonl_from_gcs_to_bigquery,
    load_rows_to_bigquery,
    persist_incremental_watermark,
    raw_article_schema,
    render_sql_template,
    run_bigquery_sql,
    record_audit_event,
    write_jsonl_to_gcs,
)
from ml.news_schemas import NewsPipelineConfig

logger = logging.getLogger("airflow.task")

NEWS_PIPELINE_DAG_ID = "news_data_pipeline"

default_args = {
    "owner": "data_engineering_team",
    "retries": 2,
}


def prepare_run_context(**context):
    dag_run_conf = (context.get("dag_run").conf if context.get("dag_run") else {}) or {}
    sources = dag_run_conf.get("sources")
    if isinstance(sources, str):
        sources = [item.strip() for item in sources.split(",") if item.strip()]

    project_id = GCP_PROJECT_ID
    config = NewsPipelineConfig(
        query=dag_run_conf.get("query", os.getenv("NEWS_QUERY", "technology OR artificial intelligence OR machine learning")),
        language=dag_run_conf.get("language", os.getenv("NEWS_LANGUAGE", "en")),
        page_size=int(dag_run_conf.get("page_size", os.getenv("NEWS_PAGE_SIZE", "100"))),
        lookback_hours=int(dag_run_conf.get("lookback_hours", os.getenv("NEWS_LOOKBACK_HOURS", "24"))),
        sources=sources,
    )

    since = get_incremental_watermark(default_hours=config.lookback_hours)
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "config": config.model_dump(),
        "since": since.isoformat(),
        "run_ts": run_ts,
        "project_id": project_id,
        "raw_table": build_raw_table_id(project_id),
        "processed_table": build_processed_table_id(project_id),
        "daily_counts_table": build_daily_counts_table_id(project_id),
        "gcs_object": f"news/raw/news_{run_ts}.jsonl",
    }
    logger.info("Prepared news pipeline context for query=%s since=%s", config.query, since.isoformat())
    record_audit_event(
        build_audit_event(
            "prepare_run_context",
            "success",
            {
                "query": config.query,
                "since": since.isoformat(),
                "raw_table": payload["raw_table"],
                "processed_table": payload["processed_table"],
                "daily_counts_table": payload["daily_counts_table"],
            },
        )
    )
    return payload


def fetch_news(**context):
    run_context = context["ti"].xcom_pull(task_ids="prepare_run_context")
    config = NewsPipelineConfig(**run_context["config"])
    since = datetime.fromisoformat(run_context["since"].replace("Z", "+00:00"))
    api_key = NEWS_API_KEY or os.getenv("NEWS_API_KEY", "")
    articles = fetch_incremental_articles(config=config, api_key=api_key, since=since)
    logger.info("Fetched %s incremental articles", len(articles))
    record_audit_event(
        build_audit_event(
            "fetch_news",
            "success",
            {
                "article_count": len(articles),
                "since": since.isoformat(),
            },
        )
    )
    return [article.model_dump(mode="json") for article in articles]


def transform_news(**context):
    raw_articles = context["ti"].xcom_pull(task_ids="fetch_news") or []
    from ml.news_schemas import RawNewsArticle

    articles = [RawNewsArticle(**article) for article in raw_articles]
    cleaned_raw, processed_articles, daily_counts = clean_and_transform_articles(articles)
    summary = build_pipeline_summary(processed_articles)
    quality = build_data_quality_summary(articles, cleaned_raw)
    payload = {
        "cleaned_raw": [article.model_dump(mode="json") for article in cleaned_raw],
        "processed_articles": [article.model_dump(mode="json") for article in processed_articles],
        "daily_counts": [item.model_dump(mode="json") for item in daily_counts],
        "summary": summary,
        "quality": quality,
        "latest_published_at": summary.get("latest_published_at"),
    }
    logger.info("Transformation produced %s processed articles", summary["article_count"])
    record_audit_event(
        build_audit_event(
            "transform_news",
            "success",
            {
                **summary,
                **quality,
            },
        )
    )
    return payload


def branch_on_article_count(**context):
    transformed = context["ti"].xcom_pull(task_ids="transform_news") or {}
    article_count = transformed.get("summary", {}).get("article_count", 0)
    if article_count > 0:
        if GCS_BUCKET_NAME:
            return "upload_raw_to_gcs"
        return "load_raw_direct_to_bigquery"
    return "no_new_articles"


def upload_raw_to_gcs(**context):
    transformed = context["ti"].xcom_pull(task_ids="transform_news") or {}
    run_context = context["ti"].xcom_pull(task_ids="prepare_run_context")
    cleaned_raw = transformed.get("cleaned_raw", [])
    gcs_object = run_context["gcs_object"]
    gcs_uri = write_jsonl_to_gcs(GCS_BUCKET_NAME, gcs_object, cleaned_raw)
    logger.info("Uploaded raw articles to %s", gcs_uri)
    record_audit_event(
        build_audit_event(
            "upload_raw_to_gcs",
            "success",
            {
                "gcs_uri": gcs_uri,
                "row_count": len(cleaned_raw),
            },
        )
    )
    return gcs_uri


def load_raw_direct_to_bigquery(**context):
    transformed = context["ti"].xcom_pull(task_ids="transform_news") or {}
    run_context = context["ti"].xcom_pull(task_ids="prepare_run_context")
    cleaned_raw = transformed.get("cleaned_raw", [])
    load_rows_to_bigquery(
        rows=cleaned_raw,
        table_id=run_context["raw_table"],
        schema=raw_article_schema(),
        write_disposition="WRITE_APPEND",
    )
    logger.info("Loaded raw articles directly to BigQuery table %s", run_context["raw_table"])
    record_audit_event(
        build_audit_event(
            "load_raw_direct_to_bigquery",
            "success",
            {
                "table_id": run_context["raw_table"],
                "row_count": len(cleaned_raw),
            },
        )
    )


def load_raw_to_bigquery(**context):
    run_context = context["ti"].xcom_pull(task_ids="prepare_run_context")
    gcs_uri = context["ti"].xcom_pull(task_ids="upload_raw_to_gcs")
    load_jsonl_from_gcs_to_bigquery(
        gcs_uri=gcs_uri,
        table_id=run_context["raw_table"],
        schema=raw_article_schema(),
        write_disposition="WRITE_APPEND",
    )
    record_audit_event(
        build_audit_event(
            "load_raw_to_bigquery",
            "success",
            {
                "gcs_uri": gcs_uri,
                "table_id": run_context["raw_table"],
            },
        )
    )


def run_elt_processing(**context):
    run_context = context["ti"].xcom_pull(task_ids="prepare_run_context")
    sql = render_sql_template(
        "news_pipeline_elt.sql",
        project_id=run_context["project_id"],
        dataset_id=BQ_DATASET,
        raw_table=RAW_TABLE,
        processed_table=PROCESSED_TABLE,
        daily_counts_table=DAILY_COUNTS_TABLE,
    )
    run_bigquery_sql(sql)
    logger.info(
        "Materialized processed table %s and daily counts table %s",
        run_context["processed_table"],
        run_context["daily_counts_table"],
    )
    record_audit_event(
        build_audit_event(
            "run_elt_processing",
            "success",
            {
                "processed_table": run_context["processed_table"],
                "daily_counts_table": run_context["daily_counts_table"],
            },
        )
    )


def persist_watermark(**context):
    transformed = context["ti"].xcom_pull(task_ids="transform_news") or {}
    latest = transformed.get("latest_published_at")
    if latest:
        watermark = datetime.fromisoformat(latest.replace("Z", "+00:00"))
        persist_incremental_watermark(watermark)
        record_audit_event(
            build_audit_event(
                "persist_watermark",
                "success",
                {
                    "watermark": watermark.isoformat(),
                },
            )
        )


with DAG(
    dag_id=NEWS_PIPELINE_DAG_ID,
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    default_args=default_args,
    tags=["news", "gcp", "bigquery", "gcs", "etl"],
    doc_md="""
    # News Data Pipeline

    Incrementally ingests public news articles, stores raw payloads in GCS, and materializes
    BigQuery raw, processed, and daily-count tables for downstream ML usage.
    """,
) as dag:
    start = EmptyOperator(task_id="start_news_pipeline")

    prepare = PythonOperator(task_id="prepare_run_context", python_callable=prepare_run_context)
    extract = PythonOperator(task_id="fetch_news", python_callable=fetch_news)
    transform = PythonOperator(task_id="transform_news", python_callable=transform_news)
    branch = BranchPythonOperator(task_id="branch_on_article_count", python_callable=branch_on_article_count)
    no_new_articles = EmptyOperator(task_id="no_new_articles")
    upload_raw = PythonOperator(task_id="upload_raw_to_gcs", python_callable=upload_raw_to_gcs)
    load_raw_direct = PythonOperator(task_id="load_raw_direct_to_bigquery", python_callable=load_raw_direct_to_bigquery)
    load_raw = PythonOperator(task_id="load_raw_to_bigquery", python_callable=load_raw_to_bigquery)
    elt = PythonOperator(task_id="run_elt_processing", python_callable=run_elt_processing)
    persist = PythonOperator(task_id="persist_watermark", python_callable=persist_watermark)

    trigger_ml = TriggerDagRunOperator(
        task_id="trigger_enhanced_ml_pipeline",
        trigger_dag_id="enhanced_ml_pipeline",
        conf=build_ml_trigger_conf(
            project_id=GCP_PROJECT_ID,
            dataset_id=BQ_DATASET,
            processed_table=build_processed_table_id(GCP_PROJECT_ID),
            daily_counts_table=build_daily_counts_table_id(GCP_PROJECT_ID),
        ),
    )

    end = EmptyOperator(task_id="news_pipeline_complete")

    start >> prepare >> extract >> transform >> branch
    branch >> no_new_articles >> end
    branch >> upload_raw >> load_raw >> elt >> trigger_ml >> persist >> end
    branch >> load_raw_direct >> elt >> trigger_ml >> persist >> end
