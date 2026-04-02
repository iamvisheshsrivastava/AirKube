import os
import sys
from datetime import datetime, timezone

# Add root to path so ml modules can be imported
sys.path.append(os.getcwd())

from ml.news_pipeline import NewsPipelineConfig, RawNewsArticle, fetch_incremental_articles


def test_fetch_incremental_articles_uses_shared_batch_id(monkeypatch):
    config = NewsPipelineConfig(page_size=10)
    since = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)

    sample_payload = [
        {
            "source": {"name": "Source A"},
            "title": "Article One",
            "url": "https://example.com/one",
            "publishedAt": "2026-04-01T01:00:00Z",
        },
        {
            "source": {"name": "Source B"},
            "title": "Article Two",
            "url": "https://example.com/two",
            "publishedAt": "2026-04-01T02:00:00Z",
        },
    ]

    monkeypatch.setattr("ml.news_pipeline._fetch_news_api_page", lambda *args, **kwargs: sample_payload)

    articles = fetch_incremental_articles(
        config=config,
        api_key="test-key",
        since=since,
        batch_id="scheduled__2026-04-02T00:00:00+00:00",
        max_pages=1,
    )

    assert len(articles) == 2
    assert {article.batch_id for article in articles} == {"scheduled_2026-04-02T00_00_00_00_00"}
    assert all(isinstance(article, RawNewsArticle) for article in articles)