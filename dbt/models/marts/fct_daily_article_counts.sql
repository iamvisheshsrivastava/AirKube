with staged as (
    select *
    from {{ ref('stg_news_articles') }}
)

select
    published_date,
    source_name,
    count(*) as article_count,
    countif(content_length > 0) as sentiment_ready_count,
    count(distinct article_id) as distinct_article_count
from staged
group by 1, 2
