with ev as (
    select e.event_date, e.category, e.region, e.platform, e.event_type,
           d.deal_id, d.status, d.amount
    from {{ ref('stg_events') }} e
    left join {{ ref('stg_deals') }} d
           on d.contact_event_id = e.event_id and e.event_type = 'contact'
)
select event_date, category, region, platform,
       count(*) filter (where event_type = 'impression') as impressions,
       count(*) filter (where event_type = 'view') as views,
       count(*) filter (where event_type = 'contact') as contacts,
       count(deal_id) as cohort_deals,
       count(deal_id) filter (where status = 'completed') as cohort_completed,
       coalesce(sum(amount) filter (where status = 'completed'), 0) as cohort_gmv
from ev
group by 1, 2, 3, 4
