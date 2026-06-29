# Redis `luckyus-isales-market` — No-TTL Key Audit & Memory Report

**Date:** 2026-06-29
**Author:** David Zeng (曾翔宇) — Senior DBA / Infrastructure
**Cluster:** `luckyus-isales-market` (AWS ElastiCache, primary + replica, Multi-AZ)
**Endpoint:** `rediss://master.luckyus-isales-market.vyllrs.use1.cache.amazonaws.com:6379`
**Trigger:** memory alert investigation → deep-dive on chronic no-TTL key growth
**Related runbook:** `/app/runbooks/redis-isales-market-remediation/` (RUNBOOK.md §7 + `scripts/fix_ttl_contact_freq.py`)

---

## 1. TL;DR

- **No active alarm.** Memory is currently ~**68%** (3.31G / 4.79G), **zero evictions**, zero rejected connections. Any alert that fired was a **transient grazing** of a threshold during the daily write sawtooth (memory oscillates 62–68%).
- **Chronic structural risk confirmed and quantified:** **72.5% of keys (~11.4M of 15.7M) have no TTL.** Under the `volatile-lfu` policy these are **un-evictable** — only the 27% with TTL can ever be reclaimed under pressure.
- **Root cause localized:** **~95% of all no-TTL keys (~10.8M) are legacy `CONTACT_day/week/month/<member>` marketing frequency-control counters** written without `EXPIRE`. They embed a date in the key name yet live forever.
- **Fix shipped (read-only side):** new date-aware backfill script + command cheat-sheet added to the runbook. Apply step needs an account with write perms (`databasecheck` is read-only by policy).

---

## 2. Current Memory Status

| Metric | Value |
|--------|-------|
| used_memory | 3.31 G |
| maxmemory | 4.79 G (5,140,907,060 B) |
| **Usage** | **~68%** (24h range 62–68%) |
| Own peak | 3.40 G (97% of peak ≈ 70% of maxmemory) |
| maxmemory_policy | `volatile-lfu` |
| evicted_keys | **0** |
| rejected_connections | 0 |
| mem_fragmentation_ratio | 1.08 (normal) |
| Total keys (db0) | 15,703,473 |
| Keys with TTL (expires) | 4,318,356 (27.5%) |
| **Keys WITHOUT TTL** | **~11,385,117 (72.5%)** |
| expired_keys (cumulative) | 232,516,249 (expiry is active & healthy) |

Companion node `luckyus-isales-marketcapi` is trivial (5.7 MB / 384 MB) — ignore.

**Verdict:** healthy *right now* (headroom + no evictions), but the no-TTL key count has nearly **4×'d since the 2026-02 incident** (was 2.62M / 39.4%). The problem is getting worse.

---

## 3. Method

- **Never `KEYS`** on 15.7M-key production. Sampled with chained-cursor `SCAN ... COUNT 20000` — 3 non-overlapping batches → **58,812 distinct keys**.
- Classified each key *family* by sampling `TTL` on representative members (TTL policy is homogeneous within a namespace), cross-checked across multiple dates per family.
- Gateway gotcha discovered & documented: `mcp-db-gateway` maps args **positionally** to redis-py `scan(cursor, match, count)`; `EVAL`/`MEMORY`/`RANDOMKEY` are denied. (Details in runbook §7.3.)

**Convergence check** — three independent sample sizes agree, and match the global keyspace ratio:

| Sample size | No-TTL share | `CONTACT_day` share |
|-------------|-------------|---------------------|
| 1,012 | 76.1% | 60.2% |
| 19,631 | 74.9% | 59.7% |
| 58,812 | **74.3%** | **59.1%** |
| global keyspace | 72.5% | — |

---

## 4. No-TTL Key Composition

Share = fraction of the no-TTL subset; extrapolated to the ~11.4M global no-TTL count.

| Key family | Share of no-TTL | Extrapolated | TTL (verified) | Meaning |
|------------|----------------|--------------|----------------|---------|
| `CONTACT_day_<member>_<date>_<n>` | 79.6% | **~9.06 M** | -1 (2025-12 … 2026-06 all confirmed) | per-day contact frequency cap |
| `CONTACT_<member>_<n>_<n>` (bare) | 7.8% | ~0.89 M | -1 | total contact freq cap |
| `CONTACT_week_<member>_<date>_<n>` | 5.4% | ~0.61 M | -1 | per-week cap |
| `CONTACT_month_<member>_<ym>_<n>` | 2.1% | ~0.24 M | -1 | per-month cap |
| **CONTACT_\* subtotal** | **94.8%** | **~10.8 M** | all no-TTL | **dominant driver** |
| `contact:userGroupLabel:set:<member>` | 2.7% | ~0.31 M | -1 | user-group labels |
| `MARKETING:COUPON:UNREAD:<member>:coupon` | 2.5% | ~0.28 M | -1 | coupon unread flags |

**Already correct (no action):** `realtime:ug:event:*` (~20h), `contact:user:contacted:activity:one:day:*` (~42h), `user:activity:Category:FreqCtrl:*` (~29d), `isales:realtime:usergroup:koala:message:*` (~22h), `c:a:r:u:*` (~8d), `popupfrq:*` (~1.5h). One outlier: `contact:activity:freq:ctrl:total:*` has a **~9.3-year** TTL (effectively none — worth shortening).

---

## 5. Root Cause

The legacy code path (uppercase `CONTACT_` prefix) writes **dated** frequency-control counters **without `EXPIRE`**. A `CONTACT_day_..._2025-12-07_0` counter is 6+ months stale and will never be read again (frequency control only cares about recent windows), yet it permanently occupies RAM.

**Evidence it's a legacy-vs-new split:** functionally-equivalent *newer* keys all set TTL correctly (`contact:user:contacted:activity:one:day` = 42h, `user:activity:Category:FreqCtrl` = 29d), and a `cfc:v2:*` ("contact frequency control v2") namespace appears rarely in the sample — the intended replacement. The legacy writers were never updated and the historical keys were never cleaned up.

---

## 6. Recommendations

1. **Write-side (root fix):** iSales/CDP frequency-control module must `EXPIRE` on write for `CONTACT_day/week/month` (suggest day 14d, week ~5w, month ~2m), or complete the migration to `cfc:v2:*`. Kills ~95% of the no-TTL *inflow*.
2. **Backfill existing debt:** run `scripts/fix_ttl_contact_freq.py` (date-aware: rolling `EXPIREAT` for recent keys, jittered 6h–3d grace TTL for past-due keys so ~9M expirations drain gradually instead of a thundering-herd `DEL`). **Needs write perms — `databasecheck` is read-only.**
3. **Shorten** the `contact:activity:freq:ctrl:total` ~9.3y TTL to a sane value.
4. **Alert tuning:** if memory alerts keep firing on the daily sawtooth, raise threshold/for-duration (e.g. ≥80% for 10m) so transient peaks don't page.
5. **Do NOT** switch to `allkeys-lfu` yet (silent data-loss risk for intentionally-persistent keys) — revisit only if no-TTL keys persist after the backfill. (See runbook §4.)

After (1)+(2): no-TTL share should fall from ~72% toward a small residual, the daily memory peak drops well below ~68%, and `volatile-lfu` regains the ability to evict under pressure.

---

## 7. Artifacts

| Path | What |
|------|------|
| `runbooks/redis-isales-market-remediation/RUNBOOK.md` §7 | Audit findings + read-only diagnostics + backfill command cheat-sheet |
| `runbooks/redis-isales-market-remediation/scripts/fix_ttl_contact_freq.py` | New date-aware TTL backfill for `CONTACT_*` (dry-run by default, per-family `--pattern`) |

*Read-only by policy: all production queries used `SCAN`/`TTL`/`INFO`/`DBSIZE` only; no writes were performed. Member IDs in key examples are internal identifiers, not PII.*
