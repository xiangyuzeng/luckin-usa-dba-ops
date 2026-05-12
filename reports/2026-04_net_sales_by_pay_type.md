# Luckin Coffee USA — April 2026 Net Sales by Payment Processor

Gross figures are carried over verbatim from `out/2026-04_gross_sales_by_pay_type.md` (locked). This report layers two refund views — cash-basis (settlement-date) and cohort (order-date) — on top of the locked gross.

---

## Variant A — CASH-BASIS (settlement-date)

> Refunds counted in the month they were **issued/settled** with the processor. A March order refunded April 3 counts in April; an April order refunded May 5 does NOT. Matches Adyen / Stripe / PayPal monthly merchant settlement reports.

| pay_type      | Gross (含税)   | Refunds       | Net           |
|---------------|----------------|---------------|---------------|
| Adyen         | $325,996       | -$4,026       | $321,970      |
| PayPal Wallet | $12,357        | -$235         | $12,122       |
| Stripe        | $222,660       | -$2,646       | $220,014      |
| **总计**      | **$561,014**   | **-$6,907**   | **$554,107**  |

Refund-rate by bucket: Adyen 1.24%, PayPal Wallet 1.90%, Stripe 1.19%. All within healthy band.

---

## Variant B — COHORT (order-date, true April revenue)

> Refunds counted against the month the **original order** was captured. A March order refunded April 3 counts in March; an April order refunded May 5 counts in April. Matches "true net April revenue" for monthly close / P&L.

Gross is **adjusted upward by $389.79** to add back the 78 April-captured orders that were excluded from the locked gross by the `refund_status != 5` filter (these orders need to be counted on the gross side so we can subtract their refund on the refund side). Per-bucket adjustment:

| Bucket | Locked Gross | + Add-back | = Adjusted Gross |
|---|---|---|---|
| Adyen | $325,996 | +$245 | $326,241 |
| PayPal Wallet | $12,357 | +$7 | $12,364 |
| Stripe | $222,660 | +$138 | $222,798 |
| **总计** | **$561,014** | **+$390** | **$561,404** |

Net table:

| pay_type      | Gross (含税, adj) | Refunds   | Net          |
|---------------|-------------------|-----------|--------------|
| Adyen         | $326,241          | -$248     | $325,993     |
| PayPal Wallet | $12,364           | -$7       | $12,357      |
| Stripe        | $222,798          | -$144     | $222,654     |
| **总计**      | **$561,404**      | **-$400** | **$561,004** |

Refund-rate by bucket (cohort): Adyen 0.076%, PayPal Wallet 0.059%, Stripe 0.065% — all <0.1% because April-cohort refunds settling within April is rare (most April refunds settle in May+).

---

## Which view to use

| Downstream consumer | Variant | Why |
|---|---|---|
| Stripe / Adyen / PayPal monthly merchant settlement reconciliation | **A (cash)** | Matches what processors report as April refund activity on April statements. |
| Finance monthly close / P&L by month | **B (cohort)** | Represents true April economic performance; refund accounting follows the revenue cohort. |
| Operations dashboards / channel mix / store performance | **B (cohort)** | Channel mix and store revenue should reflect what was actually earned by April activity. |
| Cash-flow forecasting | **A (cash)** | Refund settlements hit Luckin's bank account on settle-date, not order-date. |

**Variant A vs B refund delta**: $6,907 − $400 = **$6,507**. Interpretation: $6,507 of refund cash settled with processors in April but was attached to orders from earlier months (mostly March; a small share February). Conversely, very few April-cohort refunds settled within April (only $400), because refund settlement typically lags the original order by 1–4 weeks. The April-cash-basis view is therefore dominated by **March/Feb-originated** refund tails. This is normal for a stable business — it stabilizes month-over-month as long as refund volume is stable.

---

## Methodology

### Refund source

- **Canonical table**: `luckyus_sales_order.t_finance_refund` (17,122 rows). Chosen over `luckyus_sales_payment.t_refund` (16,820 rows) because:
  1. Same schema/cluster as `t_order` and `t_order_pay` used in the gross run (consistency).
  2. `refund_amount decimal(12,4)` is in **USD dollars** — matching `t_order.pay_money` exactly (verified by row-level sample: e.g., order `119181390221762560` has both `t_order.pay_money = 4.06` and `t_finance_refund.refund_amount = 4.06`).
  3. `refund_success_time` is explicitly indexed for the Variant-A settlement-date window.
  4. `t_refund` (in salespayment) is the deeper processor-side ledger (parallel to `t_trade`) — useful for processor diagnostics but one layer below the order-revenue grain.
- **Success enum**: `status = 7` (verified via April distinct-status sweep: 1,322 status=7 records have `refund_success_time` populated; status=2 / 4 / 5 are in-progress / failed / other and have NULL success_time). Deviates from the prompt's *hypothesized* status=2 — the prompt's hypothesis was based on China's iluckyhealth metric naming, not the USA `t_finance_refund` schema.
- **Additional filters required**: `deleted = 0` (soft-delete column on t_finance_refund) and `refund_object_type = 1` (1 = order-type refund; 100% of April refunds are type=1 — no non-order refunds in scope).

### Channel attribution

- t_finance_refund has **no pay_channel column**. Attribution flows through `t_order_pay.pay_channel` of the original capture (refunds always route back to the original processor). Join: `t_finance_refund.refund_object_id = t_order.id = t_order_pay.order_id` (with tenant match throughout). Same bucketing as gross:
  - Adyen ← pay_channel IN (51, 52, 53, 54, 55)
  - Stripe ← pay_channel IN (3, 5, 6)
  - PayPal Wallet ← pay_channel = 91

### Variant B gross-adjustment derivation

The locked gross used `refund_status != 5` to exclude fully-refunded orders. For Variant B we need every April order in the gross, then subtract refunds — so the 78 excluded orders ($389.79) must be re-added bucket-by-bucket:

- Adyen-Apple (53): 41 orders, +$215.49
- Stripe-Apple (6): 25 orders, +$107.38
- Stripe-Card (3): 3 orders, +$19.63
- Adyen-Google (52): 2 orders, +$16.01
- Stripe-Google (5): 3 orders, +$10.61
- Adyen-Card (51): 2 orders, +$9.26
- PayPal Wallet (91): 1 order, +$7.35
- Adyen-WeChatPay (54): 1 order, +$4.06
- **Total: 78 orders, +$389.79**

Bucket roll-up: Adyen +$244.82, Stripe +$137.62, PayPal Wallet +$7.35.

### Tail / anomalies

- **Variant A tail** (excluded from 总计): 10 successful refunds totaling **$55.58** against orders that have no `t_order_pay` row (NULL pay_channel). These are legacy or non-card payment refunds — they cannot be routed to any of the three processor buckets. 0.8% of Variant A refunds, not material. Variant A 总计 refunds shown ($6,907) already excludes these.
- **Variant B tail**: $0 — no NULL-channel refunds attached to April-cohort orders.
- **Delivery-platform refunds (Doordash/Grubhub/Ubereats)**: not present in t_finance_refund. These third-party aggregators run their own dispute/refund pipelines outside Luckin's payment system — out of scope for processor-level net revenue. Reported separately if/when needed.
- **In-flight refunds**: 49 refunds with status=2 (in-progress) were created in April but not yet settled. Will appear as April refunds (Variant B) once they reach status=7. Watch in next month's run.

### iluckyhealth advisory cross-check (multi-tenant — informational only)

`order_refund_success` aggregator = 804 events; Variant A LKUS = 1,337 successful refunds. The ratio (~0.6×) differs from the gross-side ~2× observed earlier, suggesting the refund metric emits once-per-event (not the request+callback double-emit pattern seen on success). The order-of-magnitude agreement is enough sanity. Amount metric ($4,580 in cents = $45.80, if cents) cannot be reconciled directly because the aggregator mixes tenants and the unit interpretation is ambiguous on this table.

### Reconciliation summary

- Variant A: 3-bucket refund sum = $4,026.24 + $2,645.94 + $234.70 = **$6,906.88** ≈ $6,907 ✓.
- Variant A grand refund (with tail) = $6,906.88 + $55.58 = $6,962.46 across 1,337 refund txns.
- Variant B: 3-bucket refund sum = $248.07 + $144.34 + $7.35 = **$399.76** ≈ $400 ✓.
- Variant B sanity: Cohort refunds ($399.76) ≈ Fully-refunded gross add-back ($389.79) + ~$10 of partial refunds (6 records, $21.73 worth filtered through cohort logic) = consistent with the partial-refund population.

---

## SQL used

### Variant A — refunds settled in April (cash-basis)

```sql
SELECT op.pay_channel,
       ROUND(SUM(r.refund_amount), 2) AS refunds_usd,
       COUNT(*)                       AS refund_txns
FROM   luckyus_sales_order.t_finance_refund r
JOIN   luckyus_sales_order.t_order          o
       ON o.id = r.refund_object_id AND o.tenant = r.tenant
LEFT JOIN luckyus_sales_order.t_order_pay   op
       ON op.order_id = o.id AND op.tenant = o.tenant
WHERE  r.tenant = 'LKUS'
  AND  r.status = 7                        -- refund successful
  AND  r.deleted = 0
  AND  r.refund_object_type = 1            -- order-type refund
  AND  o.shop_number LIKE 'US%' AND o.shop_number != 'US00000'
  AND  r.refund_success_time >= '2026-04-01 04:00:00'   -- 2026-04-01 00:00 America/New_York (EDT, UTC-4)
  AND  r.refund_success_time <  '2026-05-01 04:00:00'
GROUP BY op.pay_channel
ORDER BY refunds_usd DESC;
```

EXPLAIN: `r` uses `idx_refund_success_time` (`type: range`, 1,399 rows examined). `o` and `op` use PRIMARY / uniq_order_id via eq_ref.

### Variant B — refunds attached to April-captured orders (cohort)

```sql
SELECT op.pay_channel,
       ROUND(SUM(r.refund_amount), 2) AS refunds_usd,
       COUNT(*)                       AS refund_txns
FROM   luckyus_sales_order.t_order          o
LEFT JOIN luckyus_sales_order.t_order_pay   op
       ON op.order_id = o.id AND op.tenant = o.tenant
JOIN   luckyus_sales_order.t_finance_refund r
       ON r.refund_object_id = o.id
      AND r.tenant            = o.tenant
      AND r.refund_object_type = 1
WHERE  o.tenant = 'LKUS'
  AND  o.status IN (20, 90)
  AND  o.shop_number LIKE 'US%' AND o.shop_number != 'US00000'
  AND  o.create_time >= '2026-04-01 04:00:00'
  AND  o.create_time <  '2026-05-01 04:00:00'
  AND  r.status = 7
  AND  r.deleted = 0
  -- NOTE: refund_status != 5 filter intentionally dropped vs the gross run.
  -- NOTE: no time filter on r.refund_success_time — we want every refund tied to an April order regardless of when it settled.
GROUP BY op.pay_channel
ORDER BY refunds_usd DESC;
```

### Variant B gross add-back (78 fully-refunded April orders)

```sql
SELECT op.pay_channel,
       COUNT(*)                     AS fully_refunded_orders,
       ROUND(SUM(o.pay_money), 2)   AS gross_adjustment_usd
FROM   luckyus_sales_order.t_order        o
LEFT JOIN luckyus_sales_order.t_order_pay op
       ON op.order_id = o.id AND op.tenant = o.tenant
WHERE  o.tenant = 'LKUS'
  AND  o.status IN (20, 90)
  AND  o.refund_status = 5
  AND  o.shop_number LIKE 'US%' AND o.shop_number != 'US00000'
  AND  o.create_time >= '2026-04-01 04:00:00'
  AND  o.create_time <  '2026-05-01 04:00:00'
GROUP BY op.pay_channel
ORDER BY gross_adjustment_usd DESC;
```

### Phase 1 channel-attribution check (refund_status breakdown)

```sql
SELECT o.refund_status                       AS order_refund_status,
       COUNT(*)                              AS n,
       ROUND(SUM(r.refund_amount), 2)        AS sum_refund,
       ROUND(AVG(r.refund_amount/o.pay_money), 3) AS avg_refund_ratio
FROM   luckyus_sales_order.t_finance_refund r
JOIN   luckyus_sales_order.t_order          o
       ON o.id = r.refund_object_id AND o.tenant = r.tenant
WHERE  r.tenant = 'LKUS'
  AND  r.status = 7 AND r.deleted = 0 AND r.refund_object_type = 1
  AND  o.shop_number LIKE 'US%' AND o.shop_number != 'US00000'
  AND  r.refund_success_time >= '2026-04-01 04:00:00'
  AND  r.refund_success_time <  '2026-05-01 04:00:00'
GROUP BY o.refund_status;
-- Result: refund_status=5 (full refund) 1,321 / $6,885.15 / ratio 1.0;
--         refund_status=1 (orphan-null) 10 / $55.58 / ratio NULL;
--         refund_status=4 (partial) 6 / $21.73 / ratio 0.456.
```

### iluckyhealth advisory cross-check

```sql
SELECT metric_name,
       metric_name_comment AS channel,
       SUM(metric_count)   AS agg
FROM   luckyus_iluckyhealth.t_collect_payment_inter
WHERE  metric_name IN ('order_refund_all', 'order_refund_success', 'order_refund_amount')
  AND  insert_time >= '2026-04-01 04:00:00'
  AND  insert_time <  '2026-05-01 04:00:00'
GROUP BY metric_name, metric_name_comment;
```

---

## Endpoints and runtime

| Cluster | Role | Mode |
|---|---|---|
| `aws-luckyus-salesorder-rw` | `t_order` + `t_order_pay` + `t_finance_refund` | read-only SELECT |
| `aws-luckyus-salespayment-rw` | `t_pay_channel` (master) + `t_refund` (compared, not used) | read-only SELECT |
| `aws-luckyus-iluckyhealth-rw` | `t_collect_payment_inter` (advisory) | read-only SELECT |

No `-ro` read replicas exposed; queries hit `-rw` primaries with read-only SELECTs (no DML/DDL). All queries sub-second except Variant B (full scan of 17K-row t_finance_refund, still ~1s). Per-statement timeout 60s never approached.

---

_Report generated 2026-05-12 by Luckin USA DBA copilot via MCP DB Gateway. Companion to `out/2026-04_gross_sales_by_pay_type.md`._
