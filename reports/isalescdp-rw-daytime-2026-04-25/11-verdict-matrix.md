# Phase 4 — Verdict matrix

| H | Hypothesis | Confirming pattern observed? | Disconfirming pattern observed? | **Verdict** | Share-of-blame |
|---|------------|------------------------------|---------------------------------|-------------|----------------|
| 1 | **Same root cause (CDP realtime ingest hot tables) bleeding into daytime** | Top D1 fingerprints (F1–F6) are the **identical INSERT/DELETE pair** on `t_user_event_track` / `t_user_event` / `t_user_state` as nighttime baseline B1 (2026-04-22 06:36 UTC). Same writer user `icdprealtimeuge_A_w`. No new digest. Slow-log per-minute peak in D1 (326/min) is 2× B1 (164/min) but the *pattern* is the same. | None. | **CONFIRMED — primary** | ~50% |
| 2 | **New daytime workload (cron / endpoint / client) introduced in last 7d** | None. | (a) no SQL digest with FIRST_SEEN < 7d; (b) no MySQL user with password_last_changed < 7d (most recent: 2026-01-30, 85d ago); (c) no table CREATE_TIME < 7d; (d) every D1 fingerprint also appears in nightly baseline. | **DISCONFIRMED** | ~0% |
| 3 | **Cross-region traffic (CN evening 21:00 hitting NA cluster at 13:00 UTC)** | None. | All 9 client IPs at D1 are in `10.238.0.0/16` (us-east-1 EKS pod subnet). Zero non-us-east-1 sources. The Beijing-time alignment is coincidence. | **DISCONFIRMED** | ~0% |
| 4 | **Prior incident remediation not executed → predictable degradation** | (a) `t_user_event_track` frag 201.9% — almost identical to pre-incident 234%, OPTIMIZE TABLE never run; (b) no `is_deleted` column anywhere — soft-delete redesign not implemented (AUTO_INCREMENT 395M vs rows 110K confirms hard-DELETE pattern unchanged); (c) `long_query_time` still 0.1s. | (a) `t_user_event` frag 173% (down from 1005%) — *was* rebuilt 2026-03-13; (b) no parameter-group change in 7d. | **CONFIRMED — secondary, large amplifier** | ~30% |
| 5 | **Organic load growth, instance now undersized for daytime burst** | 14d CPU MAX history shows D1 is the **3rd daytime saturation event in 7 days** (preceded by 2026-04-19 14:23 at 73% and 2026-04-24 11:18 at 81%). Burst amplitude (D1 326 slow-q/min) is 2× the most recent nightly. db.t4g.medium = 2 vCPU / 4 GB / 2 GB buffer pool — saturates at ~1000 WriteIOPS. | Daytime *baseline* CPU has been flat at 7-12% for 14 days (not trending up). Nighttime baseline flat at 6-7%. Growth is in burst peaks, not in continuous load. | **CONFIRMED — secondary, instance-side amplifier** | ~20% |
| 6 | **Strategy migration from legacy id=67 changed threshold or smoothing window** | Cannot be verified from MySQL — alert config lives in Grafana/Prometheus. Open question for DBA Lead. | Cannot be verified. | **UNVERIFIABLE** | unknown — needs alert config diff |

## Reading the matrix

Three hypotheses are simultaneously true. The arithmetic of "why daytime now":

1. The **workload pattern itself was never daytime-exclusive**. The CDP realtime
   ingest pipeline runs 24/7 — it does not sleep during NA business hours.
   (H1 = primary cause.)

2. The **table fragmentation and hard-delete pattern were not fixed** after the
   April 14-16 incident series. Each burst still drags through fragmented B-trees
   on `t_user_event_track`. (H4 = amplifier.)

3. The **instance is structurally too small** for the burst rate the application
   is now generating. db.t4g.medium has only 2 vCPU; once write rate crosses
   ~1000 IOPS or ~50% sustained CPU, headroom for a momentary doubling
   evaporates. (H5 = ceiling.)

The trigger for "today specifically" was a **traffic burst at 13:01 UTC** (NA morning
push notification fan-out + iOS $AppStart events — visible as F1 INSERT into
t_user_event_track with `event_name='push_show_bw'` / `'$AppStart'`). On a
non-fragmented, larger instance the same burst would have peaked at maybe 20-30%
CPU and gone unnoticed.

## Confidence
**HIGH** for H1, H2 disconfirmed, H3 disconfirmed, H4, H5.
**LOW** for H6 (cannot verify without alert-rule diff — flagged as open question).
