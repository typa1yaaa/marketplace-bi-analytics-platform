WITH weekly AS (
    SELECT date_trunc('week', d.created_at)::date AS week,
           l.category,
           count(DISTINCT d.created_at::date) AS days_in_week,
           count(*) FILTER (WHERE d.status = 'completed') AS deals_completed,
           coalesce(sum(d.amount) FILTER (WHERE d.status = 'completed'), 0) AS gmv
    FROM deals d
    JOIN listings l USING (listing_id)
    GROUP BY 1, 2
),
calendar AS (
    SELECT date_trunc('week', created_at)::date AS week,
           count(DISTINCT created_at::date) AS days_with_data
    FROM deals GROUP BY 1
)
SELECT w.week, w.category, w.deals_completed, w.gmv,
       round(100.0 * (w.gmv - lag(w.gmv) OVER p) / nullif(lag(w.gmv) OVER p, 0), 1) AS gmv_wow_pct,
       round(100.0 * w.gmv / nullif(sum(w.gmv) OVER (PARTITION BY w.week), 0), 1) AS gmv_share_pct
FROM weekly w
JOIN calendar c USING (week)
WHERE c.days_with_data = 7
WINDOW p AS (PARTITION BY w.category ORDER BY w.week)
ORDER BY w.week, w.category;
