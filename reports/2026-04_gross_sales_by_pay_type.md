# Luckin Coffee USA — April 2026 Gross Sales by Payment Processor

| pay_type      | 4月          |
|---------------|--------------|
| Adyen         | $325,996     |
| PayPal Wallet | $12,357      |
| Stripe        | $222,660     |
| **总计**      | **$561,014** |

> All figures are USD, tax-inclusive (含税价格), rounded to the nearest dollar.
> Grand total covers the three card-processor buckets only. A non-processor "tail" of $25,138 (Doordash / Grubhub / Ubereats 3rd-party delivery platforms — these collect on Luckin's behalf and do not appear in Adyen/Stripe/PayPal merchant reports) is excluded from 总计 and broken out in the footer.

---

## Methodology

- **Source of truth**: `luckyus_sales_order.t_order` on cluster `aws-luckyus-salesorder-rw` joined 1:1 to `luckyus_sales_order.t_order_pay` (child payment record, unique on `(order_id, tenant)`).
- **Provider discriminator**: `t_order_pay.pay_channel` (smallint). `t_order_pay.pay_type` is always `1` for LKUS and is **not** a useful discriminator — the actual channel identity lives in `pay_channel`. Mapping resolved against `luckyus_sales_payment.t_pay_channel` master on cluster `aws-luckyus-salespayment-rw`.
- **Channel → bucket mapping** (resolved via `t_pay_channel.parent_id` hierarchy):
  - **Adyen** ← pay_channel IN (51 Adyen-Card, 52 Adyen-Google, 53 Adyen-Apple, 54 Adyen-WeChatPay, 55 Adyen-Alipay) — parent_id = 50
  - **Stripe** ← pay_channel IN (3 Stripe-Card, 5 Stripe-Google, 6 Stripe-Apple) — parent_id = 2
  - **PayPal Wallet** ← pay_channel = 91 (exact match; PayPal Venmo = 92 had zero April volume)
- **Gross amount**: `SUM(t_order.pay_money)` (decimal(12,4), USD). Confirmed tax-inclusive — `pay_money` is the amount actually charged to the card. There is no separate `tax_amount` column on either `t_order` or `t_order_pay`, so no additive expression is required.
  - Sanity check: `t_order_pay.pay_money` stores the **same amount in cents** (sample order `119202174306992128`: `t_order.pay_money = 7.03`, `t_order_pay.pay_money = 703.0`). Using the order-level column avoids the unit confusion.
- **Filters**: `tenant = 'LKUS'`, `status IN (20, 90)`, `refund_status != 5`, `shop_number LIKE 'US%'` AND `shop_number != 'US00000'`.
- **Time window** (America/New_York, April 2026): rewritten as native UTC `create_time >= '2026-04-01 04:00:00' AND create_time < '2026-05-01 04:00:00'` so MySQL can use `idx_create_time`. April 2026 is entirely in EDT (DST runs 2026-03-08 → 2026-11-01), so the offset is a flat UTC−4. EXPLAIN confirms `type: range` with `key: idx_create_time` (234K rows examined vs 916K for the `CONVERT_TZ`-wrapped form).
- **Refund handling**: `refund_status != 5` excludes fully-refunded orders. Partial refunds remain at their original capture amount, which matches the finance definition of 含税价格 (gross revenue at capture).
- **Total transactions aggregated**: 116,078 valid orders (115,928 with a `t_order_pay` row; the 150 orders without a payment row are all $0 free/promo orders and contribute nothing to gross).

### Tail buckets (excluded from 总计)

| pay_channel | name | gross USD | txns | share of all-channel |
|---|---|---|---|---|
| 1005 | Ubereats | $14,880.47 | 919 | 2.54% |
| 1003 | Doordash | $7,756.41 | 542 | 1.32% |
| 1004 | Grubhub | $2,501.25 | 178 | 0.43% |
| NULL | No `t_order_pay` row (free / comp orders) | $0.00 | 150 | 0.00% |
| **Tail subtotal** | | **$25,138.13** | **1,789** | **4.29%** |

Doordash, Grubhub, and Ubereats are **3rd-party delivery aggregators**, not payment processors — they remit settlement to Luckin separately and do not flow through Adyen/Stripe/PayPal merchant accounts. Excluding them from the processor-level total is the standard finance treatment.

### Reconciliation

- **Standalone monthly total (all channels)**: $586,151.90 / 116,078 txns.
- **Σ buckets + tail**: $325,996.44 + $222,660.43 + $12,356.90 + $25,138.13 = $586,151.90 ✓ exact match.
- **Daily Σ = monthly Σ**: $586,151.90 (30 daily rows summed independently) ✓ exact match. Per-day range: $10,131.60 (Apr-05 Sun) to $26,933.97 (Apr-30 Thu).
- **iluckyhealth cross-check (`t_collect_payment_inter`)**:
  - Amount field (`order_payment_amount`) is **not tenant-filterable** in this aggregator (it mixes LKUS with other Luckin tenants), so a direct $-level cross-check is not meaningful.
  - At the **channel-mix proportion** level (using `order_pay_channel_success` counts), every Adyen/Stripe/PayPal channel agrees with `t_order` within ±0.3 percentage points:

    | channel | iluckyhealth share | t_order share |
    |---|---|---|
    | Adyen-Apple | 48.1% | 48.4% |
    | Stripe-Apple | 32.6% | 32.6% |
    | Stripe-Card | 5.4% | 5.4% |
    | Adyen-Card | 5.3% | 5.1% |
    | Adyen-Google | 4.4% | 4.4% |
    | PayPal Wallet | 2.0% | 2.1% |
    | Stripe-Google | 1.8% | 1.8% |
    | Adyen-WeChatPay | 0.26% | 0.26% |

  - iluckyhealth emits ~2 events per transaction (its raw count is ~2.04× the t_order count, uniformly across every channel — likely an initiation + callback emission pattern), reinforcing that the channel distribution is consistent across both sources.

- **Source of truth**: `t_order` wins — the figures above come directly from it.

---

## SQL used

### Phase 2 — aggregation by pay_channel (post-bucketed in this document)

```sql
SELECT op.pay_channel                            AS pay_channel,
       ROUND(SUM(o.pay_money), 2)                AS gross_sales_usd,
       COUNT(*)                                  AS txn_count
FROM   luckyus_sales_order.t_order      o
LEFT JOIN luckyus_sales_order.t_order_pay op
       ON op.order_id = o.id
      AND op.tenant   = o.tenant
WHERE  o.tenant = 'LKUS'
  AND  o.status IN (20, 90)
  AND  o.refund_status != 5
  AND  o.shop_number LIKE 'US%'
  AND  o.shop_number != 'US00000'
  AND  o.create_time >= '2026-04-01 04:00:00'   -- 2026-04-01 00:00 America/New_York (EDT, UTC-4)
  AND  o.create_time <  '2026-05-01 04:00:00'   -- 2026-05-01 00:00 America/New_York
GROUP BY op.pay_channel
ORDER BY gross_sales_usd DESC;
```

EXPLAIN: `t_order` uses `idx_create_time` (`type: range`, ~234K rows examined). `t_order_pay` join uses `uniq_order_id` (`type: eq_ref`, 1 row).

### Phase 3 — reconciliation

```sql
-- 3.1 Standalone grand total (same filters)
SELECT ROUND(SUM(o.pay_money), 2) AS grand_total_usd,
       COUNT(*)                   AS total_txns
FROM   luckyus_sales_order.t_order o
WHERE  o.tenant = 'LKUS'
  AND  o.status IN (20, 90)
  AND  o.refund_status != 5
  AND  o.shop_number LIKE 'US%'
  AND  o.shop_number != 'US00000'
  AND  o.create_time >= '2026-04-01 04:00:00'
  AND  o.create_time <  '2026-05-01 04:00:00';

-- 3.2 Daily breakdown (America/New_York)
SELECT DATE(CONVERT_TZ(o.create_time, 'UTC', 'America/New_York')) AS d,
       ROUND(SUM(o.pay_money), 2)                                  AS gross_usd,
       COUNT(*)                                                    AS txns
FROM   luckyus_sales_order.t_order o
WHERE  o.tenant = 'LKUS'
  AND  o.status IN (20, 90)
  AND  o.refund_status != 5
  AND  o.shop_number LIKE 'US%'
  AND  o.shop_number != 'US00000'
  AND  o.create_time >= '2026-04-01 04:00:00'
  AND  o.create_time <  '2026-05-01 04:00:00'
GROUP BY d
ORDER BY d;

-- 3.3 iluckyhealth channel-mix cross-check
SELECT metric_name,
       metric_name_comment           AS channel,
       SUM(metric_count)             AS aggregate
FROM   luckyus_iluckyhealth.t_collect_payment_inter
WHERE  metric_name IN ('order_payment_amount', 'order_pay_channel_success')
  AND  insert_time BETWEEN '2026-04-01 04:00:00' AND '2026-05-01 04:00:00'
GROUP BY metric_name, metric_name_comment
ORDER BY metric_name, aggregate DESC;
```

---

## Endpoints and runtime

| Cluster | Role | Mode |
|---|---|---|
| `aws-luckyus-salesorder-rw` | `t_order` + `t_order_pay` | read-only SELECT |
| `aws-luckyus-salespayment-rw` | `t_pay_channel` (master) | read-only SELECT |
| `aws-luckyus-iluckyhealth-rw` | `t_collect_payment_inter` (aggregator cross-check) | read-only SELECT |

No `-ro` read replicas are exposed via the MCP DB Gateway for these clusters; queries ran against the `-rw` primaries with read-only SELECTs only (no DML/DDL).

Total wall-clock for the investigation: ~14 queries, all sub-second except the daily/monthly aggregations (~1–2s each on the indexed range scan).

---

_Report generated 2026-05-12 by Luckin USA DBA copilot via MCP DB Gateway._
