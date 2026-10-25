with ev as (
    select event_date,
           sum(impressions) as impressions, sum(views) as views, sum(contacts) as contacts,
           sum(cohort_deals) as cohort_deals, sum(cohort_completed) as cohort_completed
    from {{ ref('fct_events_daily') }}
    group by 1
),
money as (
    select deal_date as event_date,
           sum(deals)  as deals_created,
           sum(deals) filter (where status = 'completed')  as deals_completed,
           coalesce(sum(amount) filter (where status = 'completed'), 0) as gmv
    from {{ ref('fct_deals_daily') }}
    group by 1
),
joined as (
    select ev.*, coalesce(m.deals_created, 0) as deals_created,
           coalesce(m.deals_completed, 0) as deals_completed, coalesce(m.gmv, 0) as gmv
    from ev left join money m using (event_date)
)
select event_date, impressions, views, contacts, deals_created, deals_completed, gmv,
       round(views::numeric    / nullif(impressions, 0), 4) as view_rate,
       round(contacts::numeric / nullif(views, 0), 4)       as contact_rate,
       round(cohort_completed::numeric / nullif(contacts, 0), 4) as completed_per_contact,
       round(sum(contacts) over w7::numeric / nullif(sum(views) over w7, 0), 4) as contact_rate_7d,
       round(sum(gmv) over w7, 2) as gmv_7d,

       event_date <= max(event_date) over () - 4 as cohort_is_mature
from joined
window w7 as (order by event_date rows between 6 preceding and current row)
