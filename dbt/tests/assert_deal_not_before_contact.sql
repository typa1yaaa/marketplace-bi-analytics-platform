select d.deal_id
from {{ ref('stg_deals') }} d
join {{ ref('stg_events') }} e on e.event_id = d.contact_event_id
where d.created_at < e.event_ts
