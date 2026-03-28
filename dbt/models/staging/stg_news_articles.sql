with source_data as (
    select
        article_id,
        title,
        source_name,
        source_id,
        author,
        description,
        content,
        url,
        published_at,
        fetched_at,
        query,
        batch_id,
        language,
        raw_payload
    from {{ source('news_raw', env_var('NEWS_RAW_TABLE', 'news_articles_raw')) }}
),

cleaned as (
    select
        article_id,
        trim(title) as title,
        trim(source_name) as source_name,
        source_id,
        nullif(trim(author), '') as author,
        nullif(trim(description), '') as description,
        nullif(trim(content), '') as content,
        trim(url) as url,
        published_at,
        fetched_at,
        query,
        batch_id,
        language,
        raw_payload,
        date(published_at) as published_date,
        length(coalesce(content, description, '')) as content_length
    from source_data
)

select *
from cleaned
