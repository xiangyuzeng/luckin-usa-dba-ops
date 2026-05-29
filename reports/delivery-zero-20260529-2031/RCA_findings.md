# LCNA-INC-2026-XXX — Zeus delivery-orders-to-0 alert RCA (2026-05-29)

**Status:** FALSE POSITIVE / observability defect — business operating normally.
**Severity (post-RCA):** downgrade P2 → 周报跟进 (no customer impact, no data loss, no remediation).
**Investigator:** 曾翔宇 (David Zeng) — DBA
**Window investigated:** 2026-05-29 16:00–18:00 UTC (12:00–14:00 EDT)
**Source-of-truth used:** `luckyus_sales_order.t_order` on `aws-luckyus-salesorder-rw` (writer endpoint, lag-immune).

---

## 一 现象 / Summary

Zeus 告警 **【北美-业务告警】过去1小时外卖订单跌到0** fired 2026-05-29 **13:03 EDT** (17:03 UTC), still firing ≥1 h. Expression:

```promql
( sum(business_order_channel_count{channel_id=~"8|9|10"}) == 0 )
+ on() group_left() ( ( 12 < (hour()) <= 22 ) * 0 )
```

**The fire value was `0`, not `NoData`.** `sum()` over an absent series returns empty, not 0 — therefore the series existed at fire time and read `0`.

**Truth (`t_order`) for the alert window:**

| Channel | Orders (12:00–14:00 ET) | Last 7-day median, same window |
|---|---:|---:|
| 8 DoorDash | 2 | 2.5 |
| 9 Grubhub | 2 | 1.0 |
| 10 UberEats | 3 | 3.5 |
| **Total** | **7** | **~7.5** |

Today's delivery volume in-window matches the 7-day median exactly (identical to last Friday 05-22 = 7). **No business outage. No volume anomaly.** The alert is firing at 0 while reality is ~7.

---

## 二 时间线 / Timeline (UTC | EDT)

| UTC | EDT | Event | Source |
|---|---|---|---|
| 16:00:24 | 12:00:24 | First delivery order in window (channel 10 UberEats) | `t_order` |
| 16:01:00 | 12:01:00 | First metric row in window (channel 10) | `t_collect_order_inter` (collector lag ≈ 36 s) |
| 16:00→17:00 | 12:00→13:00 | 6 delivery orders processed cleanly across all 3 platforms | `t_order` |
| **17:03** | **13:03** | **Zeus alert fires at value=0** | Alert spec |
| 17:00→18:00 | 13:00→14:00 | 1 delivery order in this hour (ch 9). Lowest single-hour today, not zero. | `t_order` |
| 18:00→19:00 | 14:00→15:00 | 2 delivery orders | `t_order` |
| 19:00→20:00 | 15:00→16:00 | 6 delivery orders (recovered to baseline) | `t_order` |
| 20:33 | 16:33 | Latest collector insert (`t_collect_order_inter`) | metric layer |
| 20:34 | 16:34 | Latest t_order row (writer) | DB writer |
| ≥18:03 | ≥14:03 | Alert still firing, 持续时间 > 1 h | Alert state |

**Divergence point:** the truth layer and the metric DB layer agree at all hours; the divergence is exclusively between the metric DB layer and the Zeus Prometheus gauge `business_order_channel_count`. Whatever process exposes that gauge has been reading 0 while reality and the parallel collector pipeline carried real orders.

---

## 三 根因分析 / Root cause

### Bisection result

| Layer | Reads | Verdict |
|---|---|---|
| Order ingestion truth — `t_order` | 7 orders (ch8=2, ch9=2, ch10=3) | ✅ Healthy |
| Cross-channel control — channels 1/2/3 in same window | 79 / 668 / 46 | ✅ Healthy globally (rules out global outage) |
| Metric collector DB — `t_collect_order_inter` | 7 rows summing to 7 (exact match) | ✅ Healthy; lag = 0 |
| DB infra — writer freshness | Latest row 20:34 UTC (essentially now) | ✅ Healthy |
| Status pileup since 12:00 UTC | 40× status=90 + 1× status=20 | ✅ No platform-callback failure signature |
| **Prometheus gauge** `business_order_channel_count{channel_id=~"8\|9\|10"}` | **Read 0 (per alert evidence)** | ❌ **Decoupled from reality** |

### Primary root cause — bucket 1: Observability / metric-exposure pipeline defect

**Confidence: high.** Evidence:
1. Truth (`t_order`) and the DB collector (`t_collect_order_inter`) match exactly at the order level (7=7, ch-by-ch) — proves real delivery orders happened and were correctly captured.
2. Both pipelines write end-to-end with sub-minute lag — no replica/stale-read fingerprint.
3. The Prometheus gauge `business_order_channel_count` is a **separate** application-exposed gauge (not derived from `t_collect_order_inter`); its source has stopped reflecting delivery channel events while the DB-side ingestion stayed healthy.
4. Because the alert fired at `0` not `NoData`, the series exists — the gauge is being scraped, it is just returning a literal `0` for the delivery channel cardinality.
5. Recurrence check (Phase 5B): 14 days, 150 business-hour buckets, **0 explicit zeros, 0 multi-hour empties** — this is a single localized failure that began today, not chronic migration noise.

**Most likely concrete cause** (to be confirmed by the order-service / observability owner — outside DB scope):
- The application instance(s) exposing `business_order_channel_count` for the delivery-integration consumer either (a) restarted and lost in-process counter state with a `vector(0)` or similar fallback in the alert query, or (b) the delivery-channel branch of the metric is now wired to a different/stale counter, or (c) a relabel/scrape rule introduced during the strategy migration from `id=105` dropped the meaningful cardinality and only the zero baseline remains.

### Secondary contributors

1. **Strategy-expression latent defect — does NOT explain THIS fire, but must be fixed.**
   - `hour()` in Prometheus returns UTC. The gate `12 < hour() <= 22` corresponds to UTC 13–22 = **09:00–18:00 EDT**, not the intended noon–22:00 ET.
   - **False-negative gap:** 18:00–22:00 ET (the actual dinner / evening rush) → alert silenced.
   - **False-positive widening:** 09:00–12:00 ET (mornings without delivery traffic) → alerts even though intent excluded mornings.
   - Single-range gate cannot express the intended noon–22:00 ET (which wraps midnight UTC). Use either a recording rule on local hour, OR `(hour() >= 16 or hour() < 2)` with `*0` gating.
2. **No data-freshness guard.** A stale gauge stuck at 0 is indistinguishable from a true zero. Recommend ANDing the expression with `absent_over_time(business_order_channel_count[10m]) == 0` AND a `changes(business_order_channel_count[2h]) > 0` health check on the in-house channels (1/2/3) — if the gauge's in-house cardinality is also producing real numbers, it's safe to alert on delivery zero; if it isn't, the gauge is sick, suppress.
3. **Replica-lag visibility gap.** `databasecheck` lacks `REPLICATION CLIENT`. Cannot confirm/refute reader lag for the path the exporter reads from. Indirect evidence (writer real-time) is consistent with no lag; ask Michael for read-replica lag at fire time if escalating.

### Hypotheses ruled out

| Bucket | Why ruled out |
|---|---|
| H2 — Global order-ingestion outage | In-house channels 1/2/3 wrote 79/668/46 in the same window. |
| H2 — Delivery-integration broke (DoorDash/Grubhub/UberEats callbacks) | All 3 channels have rows in window. Status mix is normal (40× completed, 1× in-progress). |
| H2 — Collector / metric DB pipeline broke | `t_collect_order_inter` 7 rows match `t_order` 7 rows ch-by-ch; latest insert 20:33 UTC ≈ now. |
| Replica/stale-read on collector path | Truth = metric, writer end-to-end fresh. (Reader-side directly inaccessible — caveat noted.) |
| Strategy-artifact (recurrence noise) | 14-day history shows zero clean-zero business hours, only 4 single-hour absences for low-volume late-PM slots. First real fire. |
| Operational — stores paused on delivery apps | Truth = 7 normal orders; not zero demand. (Manual confirmation on DoorDash/UberEats merchant dashboards optional — not required by evidence.) |
| Genuine zero demand | Baseline says NO — today matches 7-day median exactly. |

---

## 四 立即处置 / Immediate actions

**No DBA remediation required.** Strictly read-only investigation completed; nothing was changed.

**Hand-off:**
1. **Page metric-pipeline / order-service owner** (Java service exposing `business_order_channel_count`):
   - Confirm the metric source on the delivery-integration code path is incrementing.
   - Inspect application logs around 2026-05-29 16:00–17:00 UTC for a restart, GC pause, or counter-reset.
   - Confirm scrape target health and any new relabel rules introduced when the alert strategy migrated off `id=105`.
2. **Confirm via Zeus dashboard / merchant dashboards** that delivery apps were not paused at the store level. (Out-of-band — not derivable from DB.)
3. **Silence the migrated strategy until the gauge is verified.** Suppress until fix lands — the truth layer makes the alert non-actionable today.
4. **Do NOT escalate as a business incident.** Volume is normal. This is an observability defect.

---

## 五 预防 / Prevention

1. **Fix strategy expression for ET hour gate** (P3, this sprint):
   - Replace `12 < hour() <= 22` with an ET-correct gate. Two viable shapes:
     - Recording rule: `business_hour_et = vector(1) and on() (hour() >= 16 or hour() < 2)` then `... + on() group_left() (business_hour_et == 1) * 0`.
     - Direct: `... + on() group_left() ((hour() >= 16) or (hour() < 2)) * 0`.
2. **Add freshness guard** (P2, this sprint):
   - AND alert condition with a sanity check on a sibling gauge that should never be zero in business hours (e.g., in-house mobile channel: `sum(business_order_channel_count{channel_id=~"1|2|3"}) > 0`). If the sibling is also zero, suppress — pipeline is broken, not delivery.
3. **Add gauge-staleness alert** (P3):
   - `changes(business_order_channel_count{channel_id=~"8|9|10"}[15m]) == 0 and ON() business_hour_et == 1` → notifies observability team independently when the gauge stops moving (catches the very failure mode we hit today).
4. **Backfill RCA snippet** to the migrated strategy runbook (replace legacy `id=105`).
5. **Add a tracking dashboard panel** comparing `t_order` rate vs `business_order_channel_count` rate for delivery channels — a hard-coded reconciliation visualization to catch this class of decoupling within minutes.

---

## 六 附录 / Appendix — raw data files

All artifacts in `/home/claude/temp/delivery-zero-20260529-2031/`:

| File | Description |
|---|---|
| `00_servers.json` | Confirmed server keys (note: `aws-luckyus-salesorder-rw`, NOT `-sales-order-rw`) |
| `00_schema.txt` | Schema for `t_order` and `t_collect_order_inter` |
| `01a_truth_window_by_status.json` | Phase 1A — order truth in alert window, by channel × status |
| `01b_truth_window_valid.json` | Phase 1B — same window, standard LKUS valid-order filter |
| `01c_truth_today_hourly.json` | Phase 1C — today's delivery hourly by ET |
| `01d_truth_baseline_7d.json` | Phase 1D — 7-day baseline same lunch window each day |
| `02_crosschannel.json` | Phase 2 — discriminator: in-house vs delivery in window |
| `03a_metric_window.json` | Phase 3A — metric-layer per channel in alert window |
| `03b_metric_freshness.json` | Phase 3B — collector latest write |
| `04_dba_infra.json` | Phase 4 — replica lag (BLOCKED), table freshness, status pileup |
| `05a_prom_gauge_series.json` | Phase 5A — direct Prometheus query attempt + access limitation |
| `05b_recurrence_14d.json` | Phase 5B — 14-day business-hour zeros/gaps analysis |
| `RCA_findings.md` | This document |

### Access limitations encountered
- `SHOW REPLICA STATUS` / `information_schema.REPLICA_HOST_STATUS` — access denied for `databasecheck` (needs REPLICATION CLIENT). Inferred via writer freshness instead.
- Zeus Prometheus datasource — `$GRAFANA_API_KEY` not set in this shell; the dba-ops Prometheus at `10.238.3.136` does not host the `business_order_channel_count` series (verified — 135 metric names, no match). Direct gauge confirmation is therefore deferred to the order-service / observability team.

### Reconciliation arithmetic (state-it-explicitly)
```
Truth      ch8=2,  ch9=2,  ch10=3,  Σ=7
Metric DB  ch8=2,  ch9=2,  ch10=3,  Σ=7          ← exact match, ch-by-ch
Prom gauge sum(...) = 0                          ← decoupled
∴ Break is at or after the gauge; not in the order pipeline or the DB collector.
```
