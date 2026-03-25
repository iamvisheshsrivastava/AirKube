from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NewsPipelineConfig(BaseModel):
    query: str = Field(default="technology OR artificial intelligence OR machine learning")
    language: str = Field(default="en")
    page_size: int = Field(default=100, ge=1, le=100)
    lookback_hours: int = Field(default=24, ge=1)
    sources: Optional[List[str]] = None


class RawNewsArticle(BaseModel):
    article_id: str
    title: str
    source_name: str
    source_id: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    url: str
    published_at: datetime
    fetched_at: datetime
    query: str
    batch_id: str
    language: str = "en"
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


class ProcessedNewsArticle(BaseModel):
    article_id: str
    title: str
    source_name: str
    published_at: datetime
    published_date: date
    content: str = ""
    description: str = ""
    content_length: int = 0
    url: str
    sentiment_placeholder: str = "unknown"
    ingestion_batch_id: str
    query: str


class DailyArticleCount(BaseModel):
    published_date: date
    source_name: str
    article_count: int
    sentiment_ready_count: int