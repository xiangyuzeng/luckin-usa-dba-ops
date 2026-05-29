# Phase 0 — Sources (reused from 5/29 RCA validation)

| Layer | Cluster | Schema.Table | Role |
|---|---|---|---|
| Truth | aws-luckyus-salesorder-rw | luckyus_sales_order.t_order | Authoritative order ledger; create_time in UTC |
| Metric DB | aws-luckyus-iluckyhealth-rw | luckyus_iluckyhealth.t_collect_order_inter | Aggregated collector (`metric_name='order_channel_create'`, `metric_value` = channel id) |
| Alert source | Zeus Prometheus | gauge `business_order_channel_count{channel_id=~"8\|9\|10"}` | NOT directly accessible from this shell |

Channels: 8=DoorDash, 9=Grubhub, 10=UberEats. In-house: 1=In-Store, 2=Mobile App, 3=Mini Program.
LKUS valid filter: `tenant='LKUS' AND status IN (20,90) AND refund_status<>5 AND shop_number LIKE 'US%' AND shop_number<>'US00000'`.

Investigation windows:
- Alert fire: 2026-05-28 21:57:00 UTC (= 17:57 EDT)
- Recovery:  2026-05-28 22:57:31 UTC (= 18:57 EDT)
- Wide window: 2026-05-28 20:30:00 UTC → 2026-05-28 23:59:00 UTC
- Baseline same window: 2026-05-21, 2026-05-26, 2026-05-27
