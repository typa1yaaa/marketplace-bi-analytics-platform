select deal_id, listing_id, buyer_id, contact_event_id,
       created_at, created_at::date as created_date,
       amount, status
from {{ source('raw', 'deals') }}
