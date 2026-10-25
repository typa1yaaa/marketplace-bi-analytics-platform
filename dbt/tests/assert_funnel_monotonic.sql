select * from {{ ref('fct_events_daily') }}
where views > impressions or contacts > views or cohort_deals > contacts
   or cohort_completed > cohort_deals
