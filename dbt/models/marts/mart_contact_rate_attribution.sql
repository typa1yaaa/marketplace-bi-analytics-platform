{% set recent = var('recent_days') %}
{% set base = var('baseline_days') %}

with bounds as (
    select max(event_date) as as_of from {{ ref('fct_events_daily') }}
),
tagged as (
    select f.*,
           case when f.event_date >  b.as_of - {{ recent }} then 'recent'
                when f.event_date >  b.as_of - {{ recent }} - {{ base }} then 'baseline' end as period
    from {{ ref('fct_events_daily') }} f cross join bounds b
),
by_dim as (
    {% for dim in ['category', 'region', 'platform'] %}
    select '{{ dim }}' as dimension, {{ dim }}::text as segment,
           sum(views) filter (where period = 'recent') as views_recent,
           sum(contacts) filter (where period = 'recent') as contacts_recent,
           sum(views) filter (where period = 'baseline') as views_base,
           sum(contacts) filter (where period = 'baseline') as contacts_base
    from tagged where period is not null group by 1, 2
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),
rates as (
    select *, contacts_recent::numeric / nullif(views_recent, 0) as rate_recent,
              contacts_base::numeric / nullif(views_base, 0) as rate_base
    from by_dim
),
loss as (
    select *, views_recent * rate_base - contacts_recent as lost_contacts from rates
)
select dimension, segment, views_recent, contacts_recent,
       round(rate_base, 4)   as rate_base,
       round(rate_recent, 4) as rate_recent,
       round(100.0 * (rate_recent - rate_base) / nullif(rate_base, 0), 1) as rate_change_pct,
       round(lost_contacts, 1) as lost_contacts,
       round(100.0 * lost_contacts / nullif(sum(lost_contacts) over (partition by dimension), 0), 1) as share_of_loss_pct
from loss
