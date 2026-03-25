MERGE `{project_id}.{dataset_id}.{processed_table}` T
USING (
  SELECT
    article_id,
    TRIM(title) AS title,
    TRIM(source_name) AS source_name,
    TIMESTAMP(published_at) AS published_at,
    DATE(TIMESTAMP(published_at)) AS published_date,
    NULLIF(TRIM(content), '') AS content,
    NULLIF(TRIM(description), '') AS description,
    COALESCE(LENGTH(NULLIF(TRIM(content), '')), LENGTH(NULLIF(TRIM(description), '')), 0) AS content_length,
    TRIM(url) AS url,
    'unknown' AS sentiment_placeholder,
    batch_id AS ingestion_batch_id,
    query
  FROM `{project_id}.{dataset_id}.{raw_table}`
  WHERE article_id IS NOT NULL
    AND title IS NOT NULL
    AND source_name IS NOT NULL
    AND published_at IS NOT NULL
    AND url IS NOT NULL
) S
ON T.article_id = S.article_id
WHEN MATCHED THEN UPDATE SET
  title = S.title,
  source_name = S.source_name,
  published_at = S.published_at,
  published_date = S.published_date,
  content = S.content,
  description = S.description,
  content_length = S.content_length,
  url = S.url,
  sentiment_placeholder = S.sentiment_placeholder,
  ingestion_batch_id = S.ingestion_batch_id,
  query = S.query
WHEN NOT MATCHED THEN
  INSERT (
    article_id,
    title,
    source_name,
    published_at,
    published_date,
    content,
    description,
    content_length,
    url,
    sentiment_placeholder,
    ingestion_batch_id,
    query
  )
  VALUES (
    S.article_id,
    S.title,
    S.source_name,
    S.published_at,
    S.published_date,
    S.content,
    S.description,
    S.content_length,
    S.url,
    S.sentiment_placeholder,
    S.ingestion_batch_id,
    S.query
  );

CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.{daily_counts_table}` AS
SELECT
  published_date,
  source_name,
  COUNT(1) AS article_count,
  COUNTIF(content_length > 0) AS sentiment_ready_count
FROM `{project_id}.{dataset_id}.{processed_table}`
GROUP BY published_date, source_name;