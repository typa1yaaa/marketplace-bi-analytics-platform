with raw_daily as (
    select event_ts::date as event_date, count(*) as raw_rows
    from {{ source('raw', 'events') }} group by 1
),
stg_daily as (
    select event_date, count(*) as staged_rows
    from {{ ref('stg_events') }} group by 1
),
joined as (
    select r.event_date, r.raw_rows, coalesce(s.staged_rows, 0) as staged_rows
    from raw_daily r left join stg_daily s using (event_date)
),
scored as (
    select *, raw_rows - staged_rows as dropped_rows,
           raw_rows::numeric / nullif(avg(raw_rows) over (order by event_date rows between 7 preceding and 1 preceding), 0) as volume_vs_7d,
           count(*) over (order by event_date rows between 7 preceding and 1 preceding) as history_days
    from joined
)
select event_date, raw_rows, staged_rows, dropped_rows,
       round(100.0 * dropped_rows / nullif(raw_rows, 0), 3) as dropped_pct,
       round(volume_vs_7d, 3) as volume_vs_7d,
       case when dropped_rows::numeric / nullif(raw_rows, 0) > 0.001 then 'rows_dropped'
            when history_days >= 7 and (volume_vs_7d < 0.6 or volume_vs_7d > 1.6) then 'volume_anomaly'
            else 'ok' end as status
from scored
