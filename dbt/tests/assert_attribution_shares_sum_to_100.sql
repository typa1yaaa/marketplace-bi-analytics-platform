select dimension, sum(share_of_loss_pct) as total
from {{ ref('mart_contact_rate_attribution') }}
group by 1
having abs(sum(share_of_loss_pct) - 100) > 0.5
