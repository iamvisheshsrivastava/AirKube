import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence

from ml.env import load_env

load_env()

from ml.news_schemas import ProcessedNewsArticle


def build_ml_trigger_conf(
    project_id: str,
    dataset_id: str,
    processed_table: str,
    daily_counts_table: str,
) -> Dict[str, Any]:
    return {
        "news_project_id": project_id,
        "news_dataset_id": dataset_id,
        "news_processed_table": processed_table,
        "news_daily_counts_table": daily_counts_table,
        "news_feature_mode": os.getenv("NEWS_FEATURE_MODE", "processed_articles"),
    }


def build_training_snapshot(processed_articles: Sequence[ProcessedNewsArticle]) -> List[Dict[str, Any]]:
    snapshot = []
    for article in processed_articles:
        snapshot.append(
            {
                "article_id": article.article_id,
                "published_date": article.published_date.isoformat(),
                "source_name": article.source_name,
                "content_length": article.content_length,
                "sentiment_placeholder": article.sentiment_placeholder,
                "query": article.query,
            }
        )
    return snapshot


def build_training_metadata(processed_articles: Sequence[ProcessedNewsArticle]) -> Dict[str, Any]:
    latest_published = max((article.published_at for article in processed_articles), default=None)
    return {
        "training_source": "news_pipeline_processed_table",
        "article_count": len(processed_articles),
        "latest_published_at": latest_published.astimezone(timezone.utc).isoformat() if latest_published else None,
        "feature_hint": "published_date, source_name, content_length, sentiment_placeholder",
    }
