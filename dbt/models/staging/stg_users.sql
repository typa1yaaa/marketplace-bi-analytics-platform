select user_id, region, platform, registered_at::date as registered_date
from {{ source('raw', 'users') }}
