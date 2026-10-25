WITH daily AS (
    SELECT e.event_ts::date AS day, l.category,
           count(*) FILTER (WHERE e.event_type = 'view') AS views,
           count(*) FILTER (WHERE e.event_type = 'contact') AS contacts
    FROM events e
    JOIN listings l USING (listing_id)
    WHERE e.event_type IN ('view', 'contact')
    GROUP BY 1, 2
),
rated AS (
    SELECT *, contacts::numeric / nullif(views, 0) AS rate FROM daily
),
scored AS (
    SELECT *,
           avg(rate) OVER w AS baseline,
           stddev_samp(rate) OVER w AS sd,
           count(rate) OVER w AS history_days
    FROM rated
    WINDOW w AS (PARTITION BY category ORDER BY day ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING)
)
SELECT day, category, views, contacts,
       round(rate, 4) AS rate,
       round(baseline, 4) AS baseline,
       round((rate - baseline) / nullif(sd, 0), 2) AS z_score,
       round(views * baseline - contacts, 1) AS lost_contacts,
       CASE WHEN history_days >= 14 AND abs((rate - baseline) / nullif(sd, 0)) > 3
            THEN 'anomaly' ELSE 'ok' END AS status
FROM scored
ORDER BY day, category;
