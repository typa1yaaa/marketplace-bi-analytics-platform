select k.event_date
from {{ ref('mart_kpi_daily') }} k
join (select event_date, sum(contacts) as contacts, sum(views) as views
      from {{ ref('mart_funnel_category') }} group by 1) f using (event_date)
where k.contacts <> f.contacts or k.views <> f.views
