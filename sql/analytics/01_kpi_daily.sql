WITH ev AS (
    SELECT event_ts::date AS day,
           count(*) FILTER (WHERE event_type = 'impression') AS impressions,
           count(*) FILTER (WHERE event_type = 'view') AS views,
           count(*) FILTER (WHERE event_type = 'contact') AS contacts
    FROM events
    GROUP BY 1
),
cohort AS (
    SELECT c.event_ts::date AS day,
           count(d.deal_id) AS cohort_deals,
           count(d.deal_id) FILTER (WHERE d.status = 'completed') AS cohort_completed
    FROM events c
    LEFT JOIN deals d ON d.contact_event_id = c.event_id
    WHERE c.event_type = 'contact'
    GROUP BY 1
),
revenue AS (
    SELECT created_at::date AS day,
           count(*) AS deals_created,
           count(*) FILTER (WHERE status = 'completed') AS deals_completed,
           coalesce(sum(amount) FILTER (WHERE status = 'completed'), 0) AS gmv
    FROM deals
    GROUP BY 1
),
daily AS (
    SELECT ev.day, ev.impressions, ev.views, ev.contacts,
           coalesce(cohort.cohort_deals, 0) AS cohort_deals,
           coalesce(cohort.cohort_completed, 0) AS cohort_completed,
           coalesce(revenue.deals_created, 0) AS deals_created,
           coalesce(revenue.deals_completed, 0) AS deals_completed,
           coalesce(revenue.gmv, 0) AS gmv
    FROM ev
    LEFT JOIN cohort  USING (day)
    LEFT JOIN revenue USING (day)
)
SELECT day, impressions, views, contacts, deals_created, deals_completed, gmv,
       round(views::numeric / nullif(impressions, 0), 4) AS view_rate,
       round(contacts::numeric / nullif(views, 0), 4) AS contact_rate,
       round(cohort_completed::numeric / nullif(contacts, 0), 4) AS completed_per_contact,
       round(sum(contacts) OVER w7 ::numeric / nullif(sum(views) OVER w7, 0), 4) AS contact_rate_7d
FROM daily
WINDOW w7 AS (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY day;
