{{ config(materialized='table') }}

with ranked as (
    select *, row_number() over (partition by event_id order by event_ts) as rn
    from {{ source('raw', 'events') }}
)
select e.event_id,
       e.event_ts,
       e.event_ts::date as event_date,
       e.user_id,
       e.listing_id,
       e.event_type,
       e.platform,
       l.category,
       l.region
from ranked e
join {{ ref('stg_listings') }} l using (listing_id)
where e.rn = 1
