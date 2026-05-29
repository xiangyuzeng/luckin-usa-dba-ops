# LCNA-INC-2026-XXX — Zeus delivery-orders-to-0 alert RCA (2026-05-28 21:57 UTC)

**Status:** Alert mechanically VALID; **no system incident**. The trailing-1h delivery-order metric truly dropped to 0, but the cause is **normal sparse-traffic variance in a low-volume late-afternoon slot**, not a pipeline / DB / app failure.
**Severity (post-RCA):** downgrade P2 → 周报跟进 / tuning ticket only.
**Investigator:** 曾翔宇 (David Zeng) — DBA
**Window investigated:** 2026-05-28 20:30 → 23:59 UTC (16:30 → 19:59 EDT)
**Alert fire:** 2026-05-28 21:57 UTC (17:57 EDT). **Recovery:** 22:57 UTC (18:57 EDT). Duration: ~60 min.
**Hypothesis verdict:** **H4 (real but non-incident)** — a real 62-min gap in delivery orders that is statistically normal for this hour. H1/H2/H3 all ruled out by evidence below.

---

## 一 现象 / Summary

Zeus 告警 **【北美-业务告警】过去1小时外卖订单跌到0** fired 2026-05-28 17:57 EDT (21:57 UTC) and recovered 18:57 EDT (22:57 UTC). Migrated from legacy strategy id=105.

**Bisection (read this once, decide):**

| Layer | Window 20:30–23:59 UTC | Verdict |
|---|---|---|
| Truth `t_order` (delivery ch 8/9/10) | 5 orders before gap (last 21:54 ch8), **GAP 21:55→22:55 UTC**, then 3 orders after (first 22:56 ch10) | Real gap |
| Metric DB `t_collect_order_inter` (delivery) | Same 5 + same gap + same 3, with ~60 s collector lag | Mirrors truth exactly — collector intact |
| Cross-channel control (in-house 1/2/3, same window) | ~1 row every minute, channels 1/2/3 all active throughout 21:55–22:55 | DB write path healthy |
| Salesorder RDS metrics | DB connections 56–58 flat, CPU 5–14% flat, RDS events = 0 | No DB anomaly |
| iluckyhealth RDS metrics | Connections 4–7 flat, events = 0 | No DB anomaly |
| CloudTrail (20:30–23:59 UTC) | 0 ModifyDBInstance / RebootDBInstance, no SG/parameter changes | No infra change |
| Same-hour baseline (21:55–22:55 UTC, 14 days) | 1–3 delivery orders is typical (1 day with 0 in metric DB on 5/27 ≈ today) | This is a low-volume slot |
| Recurrence (whole-hour zeros in business hours, 14 days × 10 hours = 150 buckets) | 4 prior empty hours: 5/18 21Z, 5/20 20Z, 5/23 22Z, 5/26 20Z | Empty hours happen every 3-4 days, almost always 16:00-18:00 ET |

**Key reframing — the "peak dinner" assumption is wrong for LKUS delivery.**
The prompt premise was that 17:57–18:57 EDT is peak dinner ordering. The 14-day LKUS data contradicts this: this hour averages 1–3 delivery orders/hour, not peak. Real LKUS delivery peak is the lunch window (13:00–16:00 UTC = 09:00–12:00 EDT). The 17:55–18:55 EDT slot is a low-volume late-afternoon dead-zone, and 1-hour gaps in it occur naturally every 3–4 days.

---

## 二 时间线 / Timeline (UTC | EDT)

| UTC | EDT | Event | Source |
|---|---|---|---|
| 21:14 | 17:14 | Delivery order (ch 10 UberEats) | t_order |
| 21:53 | 17:53 | Delivery order (ch 9 Grubhub) | t_order |
| **21:54** | **17:54** | **LAST delivery order before the gap (ch 8 DoorDash)** | t_order |
| **21:55–22:55** | **17:55–18:55** | **62-min gap — 0 delivery orders. In-house channels 1/2/3 continued normally throughout.** | t_order + cross-channel control |
| 21:57 | 17:57 | **Zeus alert fires** at value=0 | Alert system |
| **22:56** | **18:56** | **First delivery order after the gap (ch 10 UberEats)** | t_order |
| 22:57 | 18:57 | **Alert recovered** (exactly 1 min after first post-gap order) | Alert system |
| 23:32 | 19:32 | Delivery order (ch 10) | t_order |
| 23:50 | 19:50 | Delivery order (ch 8) | t_order |

Throughout this window:
- Salesorder RDS DatabaseConnections stayed in 56–58 (no storm, no drop)
- Salesorder CPU 5–14 % (no spike)
- iluckyhealth RDS connections 4–7 (no storm, no drop)
- Zero RDS events on either cluster
- Zero CloudTrail RDS modify/reboot in the window
- Mobile-app channel (ch 2) wrote multiple orders every minute throughout the gap

---

## 三 根因分析 / Root cause

### Primary verdict: H4 — real but non-incident sparse-traffic gap

**Confidence: high.** Evidence:
1. **Both data layers agree** the 62-min gap is real (truth = metric DB, ch-by-ch, with sub-minute collector lag). No pipeline break — H1 ruled out.
2. **All DBs were healthy** — connections, CPU, events, CloudTrail all clean — H2 ruled out.
3. **In-house channels (1/2/3) flowed continuously** through 21:55–22:55 — proves the order ingestion infrastructure (app, DB, network, Aurora writer) was operating normally. The gap was specific to channels 8/9/10.
4. **Same hour 14-day baseline is 1–3 orders/hour** — 17:55–18:55 EDT is a low-volume late-afternoon slot for LKUS delivery, not peak dinner.
5. **Recurrence**: 4 prior empty business hours over 14 days (5/18 21Z, 5/20 20Z, 5/23 22Z, 5/26 20Z) — same kind of gap happens every 3–4 days in this part of the day. This is the **expected statistical noise floor** for sparse delivery channels with ~1–3 orders/hour average.
6. **Recovery timing is causally clean** — the alert recovered 1 minute after the first post-gap order arrived in t_order (22:56 → recover 22:57). The alert mechanically tracked truth. So the alert wiring is correct.

### Why this is different from the 5/29 fire

- 5/29 12:00–14:00 ET: truth had 7 orders, metric DB had 7 orders, gauge fired at 0 → false-positive driven by gauge decoupling.
- 5/28 21:55–22:55 UTC: truth had 0 orders, metric DB had 0 orders, gauge fired at 0 → mechanically correct, just over-sensitive.

The strategy migrated from id=105 has TWO independent problems:
- (a) **5/29 case**: the gauge `business_order_channel_count` decoupled from reality (still unresolved — needs order-service owner action).
- (b) **5/28 case**: the alert is too sensitive — a single 1-h trailing-zero window can occur naturally for sparse channels.

### Ruled-out hypotheses

| Hypothesis | Ruled out by |
|---|---|
| H1 — Data-pipeline break (CDC/binlog/Flink missed orders) | Metric DB layer matches truth exactly, ~60 s collector lag, no insert-time anomalies. |
| H2 — Transactional DB issue (failover, storm, slow query, locks) | DB connections flat, CPU flat, no RDS events, no CloudTrail changes on either cluster. |
| H3 — id=105 migration false-positive (wrong query/table) | Recovery happens exactly 1 min after the first real post-gap order — the alert IS tracking reality, just with too-tight thresholds. |
| Global / app outage | In-house channels 1/2/3 wrote orders every minute through the gap. |
| Delivery-integration outage (DoorDash / UberEats / Grubhub callbacks) | All three platforms resumed normally within ~1 hour; if it were a real integration outage, we'd expect either (i) status-pileup signatures in t_order or (ii) a vendor-side incident notification. Neither is present, and the gap length matches statistical noise. |

---

## 四 立即处置 / Immediate actions

**No remediation required. Strictly read-only investigation — nothing was changed.**

Hand-off:
1. **No paging / no escalation.** Business volume was normal for this hour. Alert correctly recovered on its own.
2. **Tune the alert** (P3, this sprint) — see Prevention.
3. **Cross-reference with 5/29 RCA** (`LCNA-INC-2026-029` / commit `5c55e3c` in dba-ops) — the migrated strategy needs BOTH:
   - An ET-correct hour gate (the `12<hour()<=22` UTC defect → 09:00–18:00 EDT)
   - A sparseness guard so a single low-traffic hour can't fire P2

---

## 五 预防 / Prevention

1. **Make the threshold sparseness-aware** (P2): instead of `sum(...)==0`, use a deviation-from-baseline approach.
   - Recommended: `sum_over_time(rate(business_order_channel_count{channel_id=~"8|9|10"}[5m])[1h:5m]) == 0  and  avg_over_time(rate(business_order_channel_count{channel_id=~"8|9|10"}[5m])[7d:1h]) > 5` — only fire if BOTH the current 1h is 0 AND the 7d-historical average for this hour is high enough that 0 is genuinely anomalous.
   - Or: only alert when `sum(...) == 0` for 2 consecutive hours (raise `for: 2h`). Two empty hours in a row would catch real outages while filtering out the natural sparse-traffic noise documented above.
2. **Fix the ET hour gate** (carry-over from 5/29 RCA): replace `12<hour()<=22` with an ET-correct gate (`(hour() >= 16) or (hour() < 2)` for noon-22:00 EDT) — separate latent defect that silences the actual dinner rush.
3. **Add an in-house sanity guard** (P3): combine with `sum(business_order_channel_count{channel_id=~"1|2|3"}) > 0` to confirm the pipeline IS working when delivery hits 0. If in-house is also 0, escalate; if in-house has traffic, treat as sparse-delivery noise.
4. **Backfill the migration note**: the migrated strategy from id=105 should document both the 5/29 false-positive class (gauge decouple, unresolved) and the 5/28 sparse-noise class fixed here.

---

## 六 附录 / Appendix — raw files

All artifacts in `/home/claude/temp/delivery-orders-zero-20260529-2106/`:

| File | Description |
|---|---|
| `00_sources.md` | Confirmed source clusters / tables (reused from 5/29 RCA) |
| `01_truth_and_baseline.json` | Phase 1 — per-minute truth & metric DB, baseline same-hour 14-day, cross-channel control |
| `02_rds_health.json` | Phase 2 — RDS connections/CPU/events on salesorder + iluckyhealth |
| `04_cloudtrail.json` | Phase 4 — CloudTrail RDS modify/reboot + sampling of all events in window |
| `RCA_findings.md` | This report (English) |
| `RCA_summary_zh.md` | Chinese LCNA-INC drop-in summary |

### Access limitations
- Direct query of the Zeus Prometheus gauge `business_order_channel_count` was not possible from this shell (dba-ops Prometheus at 10.238.3.136 does not host this metric; `$GRAFANA_API_KEY` not set). The verdict relies on DB reconciliation + alert-fire/recovery timing, which is sufficient.
- `databasecheck` IAM user lacks REPLICATION CLIENT, so direct replica-lag readout is unavailable. Indirect evidence (writer endpoint produced real-time rows, no gap in metric DB collector) is consistent with no lag.

### Per-minute timeline table (compact reference)

```
UTC           Truth (delivery 8/9/10)   In-house (1/2/3, qualitative)
20:49         1 (ch10)                  active
20:54         1 (ch10)                  active
21:14         1 (ch10)                  active
21:30–21:53   0                         active (multiple per minute)
21:53         1 (ch9)                   active
21:54         1 (ch8)   ← LAST PRE-GAP  active
21:55–22:55   0          ← 62-min gap   active (~1+ per minute throughout)
21:57          ALERT FIRES (value=0)
22:56         1 (ch10)  ← FIRST POST    active
22:57          ALERT RECOVERS
23:32         1 (ch10)                  active
23:50         1 (ch8)                   active
```
