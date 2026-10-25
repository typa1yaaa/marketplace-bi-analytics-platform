select d.created_date as deal_date, l.category, l.region, d.status,
       count(*) as deals,
       sum(d.amount) as amount
from {{ ref('stg_deals') }} d
join {{ ref('stg_listings') }} l using (listing_id)
group by 1, 2, 3, 4
