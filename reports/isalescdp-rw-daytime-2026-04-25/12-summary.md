# aws-luckyus-isalescdp-rw — daytime active-threads spike (2026-04-25 13:05 UTC)
**Investigator:** xiangyu.zeng / DBA · **Date:** 2026-04-25 · **Status:** evidence-backed, ready for action

## Bottom line
**The daytime spike is the same nightly root cause hitting a new time window — not a new problem.** The CDP real-time ingest pipeline (`icdprealtimeuge_A_w`) ran its usual `INSERT … t_user_event_track / t_user_event` + `INSERT/DELETE … t_user_state` pattern at 13:01 UTC, driven by NA morning push-notification + iOS `$AppStart` traffic. The same workload that wakes us up at night now also saturates us in the daytime because **(1) the post-April-14 remediation was only half-applied and (2) `db.t4g.medium` no longer has enough headroom for the bursts the app generates.**

This was the **3rd daytime saturation event in 7 days** (precursors 2026-04-19 14:23 at 73 % CPU, 2026-04-24 11:18 at 81 % CPU). It is not an outlier; it is a trend.

**Confidence: HIGH.** Pinned by:
- Slow-log fingerprint set in D1 = identical to nightly baseline B1 (same SQL, same writer user, same tables) — no new digest, no new user, no new schema in last 7 days.
- All 9 client IPs at peak in `10.238.0.0/16` (us-east-1 EKS) — **cross-region/CN traffic is disconfirmed**, the Beijing-time alignment is coincidence.
- `t_user_event_track` fragmentation still **201.9 %** (was 234 % pre-incident — barely improved); no `is_deleted` column on either hot table; `long_query_time` still 0.1 s. **Remediations #1 and #3 were never applied; #2 was applied once to `t_user_event` only.**
- 14 d CloudWatch CPU MAX series shows daytime *baseline* flat (7-12 %), but daytime *burst* events appearing roughly twice a week and intensifying.

**Confidence: LOW** for one hypothesis only — H6 (whether the migrated alert strategy widened threshold vs legacy id=67). Cannot be verified from the database; needs the Grafana/Prometheus alert-rule diff. **Open question for the Lead.**

## Three ranked next actions

| # | Action | Owner | ETA | Why this rank |
|---|--------|-------|-----|---------------|
| **1** | **Resize `aws-luckyus-isalescdp-rw` from `db.t4g.medium` (2 vCPU / 4 GB) to `db.r6g.large` (2 vCPU / 16 GB) or `db.t4g.large` (2 vCPU / 8 GB).** Schedule for the 2026-04-26 Sat 04:52 UTC maintenance window. | xiangyu.zeng (DBA) | **2 days** | Single-step, reversible, **buys the largest immediate headroom** (4× buffer pool, 4× memory). Highest ROI. Does not require any app coordination. EDP-discounted cost delta: ~$120/mo for r6g.large vs t4g.medium. |
| **2** | **`OPTIMIZE TABLE luckyus_isales_cdp.t_user_event_track`** (the table that was *missed* during the April 14-16 remediation). Run during off-peak window with `ALGORITHM=INPLACE, LOCK=NONE`. Then add a recurring weekly OPTIMIZE for both hot tables until soft-delete (action #3) is live. | xiangyu.zeng (DBA) | **1 day** | Cheap, reversible, **directly addresses the 201.9 % fragmentation** that was never fixed. Weekly recurrence patches the gap until #3 lands. |
| **3** | **Implement soft-delete on `t_user_event` and `t_user_event_track`** (recommendation #1 from the April incident series). Add `is_deleted` column, change app-side `DELETE FROM …` to `UPDATE … SET is_deleted=1`, add nightly housekeeping job to physically purge with `pt-archiver`. | iSales CDP app team (China HQ collab) | **2-3 weeks** | The structural fix. Without it, fragmentation rebuilds in days and we are back here. Confirms with code that the AUTO_INCREMENT (395 M) vs row-count (110 K) gap stops growing. Long lead time → why it is #3 not #1. |

### Bonus, low-priority but worth doing once #1 is done
- Raise `innodb_io_capacity` 200 → **1500** and `innodb_io_capacity_max` 2000 → **3000** to match the gp3 volume's actual IOPS provision. Lets dirty pages drain faster after a burst — the post-spike "WriteIOPS held at ~440 for 8 minutes" tail in 01-cloudwatch-D1.csv is exactly the symptom this fixes.
- Raise `long_query_time` 0.1 s → **1.0 s** (recommendation #3). Will cut slow-log noise by ~95 % and surface only true problem queries.
- Enable Performance Insights — it is currently off, which made this investigation 3× harder than it needed to be.

## Open questions for the Lead

1. **Alert-rule diff (H6 — unverifiable from DB side).** Did the migration from legacy strategy id=67 change the threshold or smoothing window? Specifically: was id=67 a 2-min window of `threads_running > 24`, or something else? If the new rule is genuinely more sensitive, some of the daytime "fire" pattern is alerting noise rather than worsening load. Resolution: 5-minute Grafana check on the rule history.
2. **Recent app deployments to `icdprealtimeuge` since 2026-04-18?** No new SQL digest was observed, but a config change that increases ingest fan-out concurrency (without changing the queries themselves) would be invisible to the database. Resolution: ask the iSales CDP team for change-log of the last 2 weeks.
3. **Push-notification scheduling.** The 09:00 EDT (= 13:00 UTC) and 09:00 UTC mid-spikes both correlate with what looks like push-notification fan-out (`event_name='push_show_bw'` dominates the slow-log). Is the marketing team scaling NA push delivery? If so, this trend will continue and #1 alone will only buy a few weeks.

## Files in this bundle
- `00-anchor.md` — instance facts, baseline window selection, strategy migration notes
- `01-cloudwatch-D1.csv` — 1-min metric series across the spike window
- `02-pi-D1.md` — why PI is unavailable + substitute mapping
- `03-perfschema-digest-D1.csv` — empty (overwritten by burst); explains why
- `04-slowlog-D1-digest.txt` — full per-min count, top users, fingerprint samples (the heavy artifact)
- `05-rds-events.md` — 7-day RDS event log (only routine backups)
- `06-diff-top-sql.csv` — D1 vs B side-by-side, rank_delta = 0 across the board
- `07-diff-clients.csv` — client IP table + cross-region disconfirmation
- `08-new-workload.md` — disconfirmation of new digests / users / tables / deploys
- `09-lock-chain-D1.md` — no lock contention; spike was CPU + commit-IOPS
- `10-remediation-status.md` — scorecard of post-April-14 recommendations + parameter sanity
- `11-verdict-matrix.md` — 6-hypothesis matrix with cells filled
- `12-summary.md` — this file
