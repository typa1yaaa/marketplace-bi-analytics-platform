WITH ev AS (
    SELECT l.category,
           count(*) FILTER (WHERE e.event_type = 'impression') AS impressions,
           count(*) FILTER (WHERE e.event_type = 'view') AS views,
           count(*) FILTER (WHERE e.event_type = 'contact') AS contacts
    FROM events e
    JOIN listings l USING (listing_id)
    GROUP BY 1
),
dl AS (
    SELECT l.category,
           count(*) AS deals,
           count(*) FILTER (WHERE d.status = 'completed') AS deals_completed,
           coalesce(sum(d.amount) FILTER (WHERE d.status = 'completed'), 0) AS gmv
    FROM deals d
    JOIN listings l USING (listing_id)
    GROUP BY 1
)
SELECT ev.category, ev.impressions, ev.views, ev.contacts,
       coalesce(dl.deals, 0) AS deals, coalesce(dl.deals_completed, 0) AS deals_completed,
       coalesce(dl.gmv, 0) AS gmv,
       round(ev.views::numeric / nullif(ev.impressions, 0), 4) AS view_rate,
       round(ev.contacts::numeric / nullif(ev.views, 0), 4) AS contact_rate,
       round(coalesce(dl.deals, 0)::numeric / nullif(ev.contacts, 0), 4) AS deal_rate
FROM ev LEFT JOIN dl USING (category)
ORDER BY gmv DESC;
