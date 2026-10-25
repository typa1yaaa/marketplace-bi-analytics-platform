{% set metrics = [('view_rate', 'views', 'impressions'), ('contact_rate', 'contacts', 'views')] %}
{% set n = var('baseline_days') %}

with daily as (
    select event_date, category,
           sum(impressions) as impressions, sum(views) as views, sum(contacts) as contacts
    from {{ ref('fct_events_daily') }}
    group by 1, 2
),
long as (
    {% for name, num, den in metrics %}
    select event_date, category, '{{ name }}' as metric,
           {{ num }}::numeric as numerator, {{ den }}::numeric as denominator
    from daily
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),
rated as (
    select *, numerator / nullif(denominator, 0) as value from long
),
scored as (
    select *,
           avg(value) over w as baseline,
           stddev_samp(value) over w as sd,
           count(value) over w as history_days
    from rated
    window w as (partition by category, metric order by event_date
                 rows between {{ n }} preceding and 1 preceding)
)
select event_date, category, metric, numerator, denominator,
       round(value, 4) as value,
       round(baseline, 4) as baseline,
       round((value - baseline) / nullif(sd, 0), 2) as z_score,
       round(denominator * baseline - numerator, 1) as lost_numerator,
       case when history_days >= 14 and abs((value - baseline) / nullif(sd, 0)) > 3
            then 'anomaly' else 'ok' end as status
from scored
