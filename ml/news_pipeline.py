import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

from ml.env import load_env

load_env()

from ml.news_schemas import DailyArticleCount, NewsPipelineConfig, ProcessedNewsArticle, RawNewsArticle

logger = logging.getLogger("news_pipeline")

NEWS_API_URL = os.getenv("NEWS_API_URL", "https://newsapi.org/v2/everything")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCS_BUCKET_NAME = os.getenv("NEWS_GCS_BUCKET", "")
BQ_DATASET = os.getenv("NEWS_BQ_DATASET", "news_pipeline")
RAW_TABLE = os.getenv("NEWS_RAW_TABLE", "news_articles_raw")
PROCESSED_TABLE = os.getenv("NEWS_PROCESSED_TABLE", "news_articles_processed")
DAILY_COUNTS_TABLE = os.getenv("NEWS_DAILY_COUNTS_TABLE", "news_article_daily_counts")
LAST_WATERMARK_VARIABLE = os.getenv("NEWS_LAST_WATERMARK_VARIABLE", "news_pipeline_last_published_at")

try:
    from airflow.models import Variable
except Exception:  # pragma: no cover - Airflow is not available in unit-test environments.
    Variable = None

try:
    from google.cloud import bigquery, storage
except Exception:  # pragma: no cover - Optional runtime dependency for local testing.
    bigquery = None
    storage = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _article_id(source_name: str, title: str, url: str, published_at: datetime) -> str:
    fingerprint = f"{source_name}|{title}|{url}|{published_at.isoformat()}"
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.split()).strip()


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def get_incremental_watermark(default_hours: int = 24) -> datetime:
    fallback = _utc_now() - timedelta(hours=default_hours)

    if Variable is None:
        return fallback

    stored = Variable.get(LAST_WATERMARK_VARIABLE, default_var=None)
    if not stored:
        return fallback

    try:
        return _parse_datetime(stored) or fallback
    except Exception:
        logger.warning("Invalid watermark stored in Airflow Variable %s: %s", LAST_WATERMARK_VARIABLE, stored)
        return fallback


def persist_incremental_watermark(watermark: datetime) -> None:
    if Variable is None:
        logger.info("Airflow Variable backend not available; skipping watermark persistence.")
        return

    Variable.set(LAST_WATERMARK_VARIABLE, watermark.astimezone(timezone.utc).isoformat())


def _build_news_api_params(config: NewsPipelineConfig, api_key: str, since: datetime, page: int) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "q": config.query,
        "language": config.language,
        "pageSize": config.page_size,
        "page": page,
        "sortBy": "publishedAt",
        "from": since.astimezone(timezone.utc).isoformat(),
        "apiKey": api_key,
    }
    if config.sources:
        params["sources"] = ",".join(config.sources)
    return params


def _build_raw_news_article(item: Dict[str, Any], config: NewsPipelineConfig, published_at: datetime) -> Optional[RawNewsArticle]:
    source = item.get("source") or {}
    source_name = _clean_text(source.get("name")) or "unknown"
    title = _clean_text(item.get("title"))
    url = _clean_text(item.get("url"))

    if not title or not url:
        return None

    return RawNewsArticle(
        article_id=_article_id(source_name, title, url, published_at),
        title=title,
        source_name=source_name,
        source_id=source.get("id"),
        author=_clean_text(item.get("author")) or None,
        description=_clean_text(item.get("description")) or None,
        content=_clean_text(item.get("content")) or None,
        url=url,
        published_at=published_at,
        fetched_at=_utc_now(),
        query=config.query,
        batch_id=_utc_now().strftime("%Y%m%dT%H%M%SZ"),
        language=config.language,
        raw_payload=item,
    )


def _fetch_news_api_page(config: NewsPipelineConfig, api_key: str, since: datetime, page: int) -> List[Dict[str, Any]]:
    response = requests.get(NEWS_API_URL, params=_build_news_api_params(config, api_key, since, page), timeout=30)
    response.raise_for_status()
    payload = response.json()
    batch_articles = payload.get("articles", [])
    logger.info("Fetched %s articles from page %s", len(batch_articles), page)
    return batch_articles


def _append_incremental_articles(
    articles: List[RawNewsArticle],
    batch_articles: Sequence[Dict[str, Any]],
    config: NewsPipelineConfig,
    since: datetime,
) -> bool:
    stop_fetching = False

    for item in batch_articles:
        published_at = _parse_datetime(item.get("publishedAt"))
        if published_at is None:
            continue
        if published_at <= since:
            stop_fetching = True
            break

        article = _build_raw_news_article(item, config, published_at)
        if article is None:
            continue
        articles.append(article)

    return stop_fetching


def fetch_incremental_articles(
    config: NewsPipelineConfig,
    api_key: str,
    since: datetime,
    max_pages: int = 5,
) -> List[RawNewsArticle]:
    if not api_key:
        raise ValueError("NEWS_API_KEY is required to fetch NewsAPI articles.")

    articles: List[RawNewsArticle] = []
    for page in range(1, max_pages + 1):
        batch_articles = _fetch_news_api_page(config, api_key, since, page)
        if not batch_articles:
            break

        stop_fetching = _append_incremental_articles(articles, batch_articles, config, since)
        if stop_fetching or len(batch_articles) < config.page_size:
            break

    return articles


def clean_and_transform_articles(articles: Sequence[RawNewsArticle]) -> Tuple[List[RawNewsArticle], List[ProcessedNewsArticle], List[DailyArticleCount]]:
    seen_ids = set()
    cleaned_raw: List[RawNewsArticle] = []
    processed: List[ProcessedNewsArticle] = []

    for article in sorted(articles, key=lambda item: item.published_at, reverse=True):
        if article.article_id in seen_ids:
            continue
        seen_ids.add(article.article_id)

        normalized = article.model_copy(
            update={
                "title": _clean_text(article.title),
                "source_name": _clean_text(article.source_name) or "unknown",
                "author": _clean_text(article.author) or None,
                "description": _clean_text(article.description) or None,
                "content": _clean_text(article.content) or None,
                "url": _clean_text(article.url),
            }
        )
        cleaned_raw.append(normalized)

        processed.append(
            ProcessedNewsArticle(
                article_id=normalized.article_id,
                title=normalized.title,
                source_name=normalized.source_name,
                published_at=normalized.published_at.astimezone(timezone.utc),
                published_date=normalized.published_at.astimezone(timezone.utc).date(),
                content=normalized.content or "",
                description=normalized.description or "",
                content_length=len((normalized.content or normalized.description or "").strip()),
                url=normalized.url,
                sentiment_placeholder="unknown",
                ingestion_batch_id=normalized.batch_id,
                query=normalized.query,
            )
        )

    counts: Dict[Tuple[Any, Any], Dict[str, Any]] = {}
    for article in processed:
        key = (article.published_date, article.source_name)
        bucket = counts.setdefault(
            key,
            {
                "published_date": article.published_date,
                "source_name": article.source_name,
                "article_count": 0,
                "sentiment_ready_count": 0,
            },
        )
        bucket["article_count"] += 1
        if article.content_length > 0:
            bucket["sentiment_ready_count"] += 1

    daily_counts = [DailyArticleCount(**bucket) for bucket in counts.values()]
    return cleaned_raw, processed, daily_counts


def build_pipeline_summary(processed_articles: Sequence[ProcessedNewsArticle]) -> Dict[str, Any]:
    sources = sorted({article.source_name for article in processed_articles})
    latest_published = max((article.published_at for article in processed_articles), default=None)
    return {
        "article_count": len(processed_articles),
        "source_count": len(sources),
        "sources": sources,
        "latest_published_at": latest_published.astimezone(timezone.utc).isoformat() if latest_published else None,
    }


def write_jsonl_to_gcs(bucket_name: str, object_name: str, rows: Sequence[Any]) -> str:
    if storage is None:
        raise RuntimeError("google-cloud-storage is required to upload raw news data to GCS.")
    if not bucket_name:
        raise ValueError("NEWS_GCS_BUCKET is required for raw data uploads.")

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    body = "\n".join(json.dumps(row.model_dump() if hasattr(row, "model_dump") else row, default=_json_default) for row in rows)
    blob.upload_from_string(body, content_type="application/jsonl")
    return f"gs://{bucket_name}/{object_name}"


def load_jsonl_from_gcs_to_bigquery(
    gcs_uri: str,
    table_id: str,
    schema: Sequence[Dict[str, Any]],
    write_disposition: str = "WRITE_APPEND",
) -> None:
    if bigquery is None:
        raise RuntimeError("google-cloud-bigquery is required to load news data into BigQuery.")

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        schema=[bigquery.SchemaField(**field) for field in schema],
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=write_disposition,
    )
    load_job = client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
    load_job.result()
    logger.info("Loaded %s into BigQuery table %s", gcs_uri, table_id)


def load_rows_to_bigquery(
    rows: Sequence[Any],
    table_id: str,
    schema: Sequence[Dict[str, Any]],
    write_disposition: str = "WRITE_APPEND",
) -> None:
    if bigquery is None:
        raise RuntimeError("google-cloud-bigquery is required to load news data into BigQuery.")

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        schema=[bigquery.SchemaField(**field) for field in schema],
        write_disposition=write_disposition,
    )
    payload = [row.model_dump() if hasattr(row, "model_dump") else row for row in rows]
    load_job = client.load_table_from_json(payload, table_id, job_config=job_config)
    load_job.result()
    logger.info("Loaded %s rows into BigQuery table %s", len(payload), table_id)


def run_bigquery_sql(sql_text: str, parameters: Optional[Dict[str, Any]] = None) -> None:
    if bigquery is None:
        raise RuntimeError("google-cloud-bigquery is required to run ELT SQL.")

    client = bigquery.Client()
    job_config = bigquery.QueryJobConfig(query_parameters=[])
    if parameters:
        job_config.query_parameters = [bigquery.ScalarQueryParameter(key, "STRING", value) for key, value in parameters.items()]

    query_job = client.query(sql_text, job_config=job_config)
    query_job.result()
    logger.info("BigQuery SQL job completed successfully.")


def load_sql_template(sql_filename: str) -> str:
    sql_path = Path(__file__).resolve().parents[1] / "sql" / sql_filename
    return sql_path.read_text(encoding="utf-8")


def render_sql_template(sql_filename: str, **kwargs: Any) -> str:
    return load_sql_template(sql_filename).format(**kwargs)


def build_raw_table_id(project_id: str) -> str:
    return f"{project_id}.{BQ_DATASET}.{RAW_TABLE}"


def build_processed_table_id(project_id: str) -> str:
    return f"{project_id}.{BQ_DATASET}.{PROCESSED_TABLE}"


def build_daily_counts_table_id(project_id: str) -> str:
    return f"{project_id}.{BQ_DATASET}.{DAILY_COUNTS_TABLE}"


def raw_article_schema() -> List[Dict[str, Any]]:
    return [
        {"name": "article_id", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "title", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "source_name", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "source_id", "field_type": "STRING", "mode": "NULLABLE"},
        {"name": "author", "field_type": "STRING", "mode": "NULLABLE"},
        {"name": "description", "field_type": "STRING", "mode": "NULLABLE"},
        {"name": "content", "field_type": "STRING", "mode": "NULLABLE"},
        {"name": "url", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "published_at", "field_type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "fetched_at", "field_type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "query", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "batch_id", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "language", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "raw_payload", "field_type": "JSON", "mode": "NULLABLE"},
    ]


def processed_article_schema() -> List[Dict[str, Any]]:
    return [
        {"name": "article_id", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "title", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "source_name", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "published_at", "field_type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "published_date", "field_type": "DATE", "mode": "REQUIRED"},
        {"name": "content", "field_type": "STRING", "mode": "NULLABLE"},
        {"name": "description", "field_type": "STRING", "mode": "NULLABLE"},
        {"name": "content_length", "field_type": "INTEGER", "mode": "REQUIRED"},
        {"name": "url", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "sentiment_placeholder", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "ingestion_batch_id", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "query", "field_type": "STRING", "mode": "REQUIRED"},
    ]


def daily_article_count_schema() -> List[Dict[str, Any]]:
    return [
        {"name": "published_date", "field_type": "DATE", "mode": "REQUIRED"},
        {"name": "source_name", "field_type": "STRING", "mode": "REQUIRED"},
        {"name": "article_count", "field_type": "INTEGER", "mode": "REQUIRED"},
        {"name": "sentiment_ready_count", "field_type": "INTEGER", "mode": "REQUIRED"},
    ]
