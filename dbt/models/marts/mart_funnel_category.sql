with daily as (
    select event_date, category,
           sum(impressions) as impressions, sum(views) as views, sum(contacts) as contacts,
           sum(cohort_deals) as cohort_deals, sum(cohort_completed) as cohort_completed
    from {{ ref('fct_events_daily') }}
    group by 1, 2
)
select event_date, category, impressions, views, contacts, cohort_deals, cohort_completed,
       round(views::numeric / nullif(impressions, 0), 4) as view_rate,
       round(contacts::numeric / nullif(views, 0), 4) as contact_rate,
       round(cohort_deals::numeric / nullif(contacts, 0), 4) as deal_rate,
       round(sum(contacts) over w7::numeric / nullif(sum(views) over w7, 0), 4) as contact_rate_7d
from daily
window w7 as (partition by category order by event_date rows between 6 preceding and current row)
