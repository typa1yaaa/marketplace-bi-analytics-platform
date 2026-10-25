with weekly as (
    select date_trunc('week', deal_date)::date as week, category,
           count(distinct deal_date) as days_with_data,
           sum(deals) filter (where status = 'completed') as deals_completed,
           coalesce(sum(amount) filter (where status = 'completed'), 0) as gmv
    from {{ ref('fct_deals_daily') }}
    group by 1, 2
),
full_weeks as (
    select week from weekly group by 1 having max(days_with_data) = 7
)
select w.week, w.category, w.deals_completed, w.gmv,
       round(100.0 * (w.gmv - lag(w.gmv) over p) / nullif(lag(w.gmv) over p, 0), 1) as gmv_wow_pct,
       round(100.0 * w.gmv / nullif(sum(w.gmv) over (partition by w.week), 0), 1) as gmv_share_pct
from weekly w
join full_weeks using (week)
window p as (partition by w.category order by w.week)
