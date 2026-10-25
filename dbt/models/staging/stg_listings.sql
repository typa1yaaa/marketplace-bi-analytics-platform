select listing_id, seller_id, category, region, price, created_at::date as created_date
from {{ source('raw', 'listings') }}
