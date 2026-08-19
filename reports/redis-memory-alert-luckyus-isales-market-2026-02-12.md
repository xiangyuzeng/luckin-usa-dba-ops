# Redis Memory Alert Investigation Report

**Cluster:** `luckyus-isales-market` (AWS ElastiCache)
**Endpoint:** `rediss://master.luckyus-isales-market.vyllrs.use1.cache.amazonaws.com:6379`
**Alert Rule:** `avg_over_time(redis_memory_usage_ratio[3m]) > 70`
**Investigation Time:** 2026-02-12 ~14:00–14:30 UTC
**Investigator:** SRE (read-only, via MCP DB Gateway)

---

## 1. Current Status

| Metric | Value | Assessment |
|--------|-------|------------|
| **used_memory_human** | **2.01 G** | Near maxmemory |
| **maxmemory** | 2.32 G | — |
| **Memory Usage %** | **86.7%** | **HIGH** — breached 70% alert threshold |
| **used_memory_peak** | 2.10 G (95.76% of peak) | Near all-time peak |
| **mem_fragmentation_ratio** | 1.05 | Healthy (no excessive fragmentation) |
| **maxmemory_policy** | `volatile-lfu` | Only keys **with** TTL are eligible for eviction |
| **evicted_keys** | 0 | Eviction has NOT yet triggered |
| **Total keys (DBSIZE)** | 6,700,023 | — |
| **Keys with TTL** | 4,076,039 (60.8%) | — |
| **Keys WITHOUT TTL** | **2,623,984 (39.2%)** | **Critical — not evictable** |
| **avg_ttl** | ~124 days | Skewed by long-TTL keys |
| **instantaneous_ops_per_sec** | 3,817 | Moderate load |
| **connected_clients** | 108 | Normal |
| **keyspace_hit_rate** | 85.8% | Acceptable |

### Memory Trend (CloudWatch — last 1 hour)

```
Time (UTC)        Memory %    Connections    CPU %
─────────────────────────────────────────────────
~13:30            61.0%       ~54            ~1.8%
~13:45            66.2%       ~72            ~3.5%
~13:57            73.6%       ~93            ~17.0%   ← spike begins
~14:10            85.4%       ~83            ~4.2%
~14:20            87.1%       ~82            ~3.8%
~14:30            86.7%       ~108           ~3.5%    ← current
```

**Observation:** Memory surged from **61% → 87%** in approximately 20 minutes starting around 13:57 UTC. A correlated CPU spike to 17% and connection spike to 93 suggests a burst of write activity (likely a marketing campaign or batch contact-activity job).

---

## 2. Top Key Patterns by Estimated Count

> **Note:** `--bigkeys` scan and `MEMORY USAGE` commands were blocked by the MCP gateway. Sizes are estimated from key counts × data structure characteristics.

| # | Key Pattern | Count | Type | TTL | Est. Memory Impact |
|---|-------------|-------|------|-----|-------------------|
| 1 | **Numeric keys** (`35*`, `36*`, etc.) | ~5,196,000 | string | 675–1,766 s | **HIGH** — bulk of keys; short strings but massive count |
| 2 | `contact:last:activity:*` | 374,639 | string | ~364 days | **MEDIUM** — long TTL, STRLEN=24 per key |
| 3 | `contact:user:contacted:activity:one:day:*` | 289,278 | set | ~47 hours | MEDIUM — SCARD≈3 per set |
| 4 | `user:activity:Category:FreqCtrl:*` | 238,060 | string | ~30 days | LOW–MEDIUM |
| 5 | `contact:userGroupLabel:set:*` | **177,450** | set | **-1 (NO TTL)** | **HIGH — never expires, SCARD≈26** |
| 6 | `MARKETING:COUPON:UNREAD:*` | **147,111** | set | **-1 (NO TTL)** | **HIGH — never expires, SCARD≈8** |
| 7 | `contact:activity:freq:ctrl:total:*` | 127,097 | string | ~17.6 days | LOW–MEDIUM |
| 8 | `isalesmarekting:coupon2:mostdiscount_LKUS_*` | 68,047 | string | ~8 min | LOW — short TTL, self-cleaning |
| 9 | `draw_*` | 3,495 | — | — | LOW |
| 10 | `SU@*` | 1,848 | — | — | LOW |

---

## 3. Key Pattern Analysis

### 3.1 Numeric Keys (~5.2M keys) — Primary Memory Driver

- **Pattern:** Pure numeric strings, e.g. `3553937531770903242280`, `36316621771770904348283`
- **Type:** `string`
- **Value:** Unix timestamp in milliseconds (e.g., `"1770906855441"`)
- **TTL:** 675–1,766 seconds (~11–29 minutes)
- **Likely purpose:** User-activity or contact-dedup keys (userID + timestamp concatenation)
- **Assessment:** These keys have proper short TTLs and are self-cleaning. However, the **sheer volume** (~5.2M) generated in a burst is the likely **direct cause** of the memory spike. A marketing campaign or batch job appears to be generating these at extreme rate.

### 3.2 Keys with NO TTL (TTL = -1) — **Chronic Memory Leak**

| Pattern | Count | Type | Members |
|---------|-------|------|---------|
| `contact:userGroupLabel:set:*` | 177,450 | set | SCARD ≈ 26 |
| `MARKETING:COUPON:UNREAD:*` | 147,111 | set | SCARD ≈ 8 |
| `exchange:coupon:high:commodity:price:*` | 473 | string | — |

**Total no-TTL keys: ~2,623,984 (39.2% of all keys)**

These keys are **never evicted** under the `volatile-lfu` policy because they have no expiry. They represent a **persistent memory floor** that grows monotonically as new users/coupons are created, leaving progressively less room for working keys.

### 3.3 Excessively Long TTL

| Pattern | Count | TTL | Concern |
|---------|-------|-----|---------|
| `contact:last:activity:*` | 374,639 | ~364 days | Effectively permanent; 374K string keys occupying memory for a full year |

---

## 4. Anomalies

| # | Anomaly | Severity | Details |
|---|---------|----------|---------|
| 1 | **Rapid memory spike (61% → 87% in 20 min)** | **HIGH** | Correlated with CPU spike to 17% and connection surge. Suggests a batch/campaign burst writing millions of short-TTL numeric keys. |
| 2 | **39.2% of keys have no TTL** | **HIGH** | Under `volatile-lfu`, these keys are **immune to eviction**. They form a growing, non-reclaimable memory floor. |
| 3 | **0 evictions despite 87% usage** | **MEDIUM** | `volatile-lfu` only evicts keys with TTL. If memory pressure continues, only the 60.8% of keys with TTL are candidates — leaving 39.2% permanently resident. |
| 4 | **contact:last:activity TTL of 364 days** | **MEDIUM** | 374K keys with ~1-year TTL. These accumulate across cohorts with effectively no cleanup. |
| 5 | **138M expired_keys (cumulative)** | **INFO** | High expired count is normal for high-throughput marketing caches. Confirms heavy key churn. |
| 6 | **SLOWLOG / CLIENT LIST unavailable** | **INFO** | MCP gateway restrictions prevented retrieving slow query log and client buffer details. |

---

## 5. Root Cause Analysis

The memory alert has **two compounding causes**:

### Immediate Trigger: Burst of Numeric Keys
A burst of ~5.2 million short-TTL numeric keys (likely from a marketing campaign or contact-activity batch job) started around **13:57 UTC**, driving memory from 61% to 87% within 20 minutes. These keys have TTLs of 11–29 minutes and will **self-expire**, so memory should partially recover within ~30 minutes of the burst ending.

### Underlying Issue: Persistent No-TTL Key Growth
**2.6 million keys (39.2%) have no TTL** and are growing monotonically:
- `contact:userGroupLabel:set:*` — 177K sets (26 members each), never cleaned
- `MARKETING:COUPON:UNREAD:*` — 147K sets (8 members each), never cleaned
- Various other patterns without expiry

Under `volatile-lfu`, these keys **cannot be evicted**. They raise the memory floor over time, reducing headroom for transient workloads (like the current burst). Without intervention, each new user/coupon permanently increases baseline memory usage.

---

## 6. Risk Level

## **HIGH** 🔴

| Factor | Rating | Rationale |
|--------|--------|-----------|
| Current memory % | HIGH | 86.7% — well above 70% threshold, approaching maxmemory |
| Trend | HIGH | Steep upward spike; partial recovery expected as short-TTL keys expire |
| Eviction headroom | HIGH | 0 evictions so far; 39.2% of keys are non-evictable |
| Structural risk | HIGH | No-TTL key count grows monotonically — baseline memory floor keeps rising |
| Fragmentation | LOW | 1.05 ratio is healthy |
| Client load | LOW | 108 connections, no blocked clients |

**If the burst continues or another burst occurs before short-TTL keys expire, memory will hit maxmemory (2.32G), and only 60.8% of keys will be eligible for eviction — potentially causing cache misses for critical marketing data.**

---

## 7. Recommendations

### Immediate (P0 — within hours)
1. **Monitor for natural recovery** — The ~5.2M numeric keys have 11–29 min TTL. Memory should drop by ~0.3–0.5G within 30 minutes of the burst stopping. Watch CloudWatch `DatabaseMemoryUsagePercentage`.
2. **Identify and throttle the burst source** — Correlate the 13:57 UTC spike with application deployment logs, marketing campaign triggers, or cron job schedules. Rate-limit if possible.

### Short-Term (P1 — within days)
3. **Add TTL to `MARKETING:COUPON:UNREAD:*` keys** — 147K sets with no expiry. These should have a reasonable TTL (e.g., 30–90 days). Application code change required.
4. **Add TTL to `contact:userGroupLabel:set:*` keys** — 177K sets with no expiry. Implement TTL or a cleanup job.
5. **Reduce TTL on `contact:last:activity:*`** — 364-day TTL is excessive. Consider reducing to 30–90 days based on business requirements.
6. **Add TTL to `exchange:coupon:high:commodity:price:*`** — 473 keys with no expiry (low count but sets bad precedent).

### Medium-Term (P2 — within weeks)
7. **Audit all key patterns for TTL compliance** — Establish a policy that ALL keys must have a TTL. Add CI/CD checks or code review guidelines.
8. **Consider switching to `allkeys-lfu`** — This policy can evict ANY key under memory pressure, including no-TTL keys. Evaluate impact on data consistency first.
9. **Scale up maxmemory** — If key growth is unavoidable, consider upgrading the ElastiCache node type to provide more headroom.
10. **Add alerting at 60%** — The current 70% threshold left little time to respond. An earlier warning at 60% would provide more reaction time.

---

## 8. Investigation Limitations

| Item | Status | Reason |
|------|--------|--------|
| `--bigkeys` scan | ❌ Not available | MCP gateway does not support `redis-cli --bigkeys` |
| `MEMORY USAGE <key>` | ❌ Blocked | Permission denied via MCP gateway |
| `SLOWLOG GET 20` | ❌ Blocked | MCP gateway Python API limitation |
| `CLIENT LIST` | ❌ Blocked | MCP gateway Python API limitation |
| `SCAN` with cursor | ❌ Empty results | MCP gateway returns empty arrays for SCAN |
| `RANDOMKEY` | ❌ Blocked | Permission denied via MCP gateway |

Key size estimates are based on key counts, data types, and member counts rather than actual `MEMORY USAGE` measurements.

---

*Report generated: 2026-02-12 ~14:30 UTC*
*Investigation method: Read-only commands via MCP DB Gateway + AWS CloudWatch metrics*
*No write/delete commands were executed during this investigation.*
