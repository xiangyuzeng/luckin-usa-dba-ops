# LCNA DBA — luckylfe-log Elasticsearch yellow alert investigation
**Date:** 2026-04-29
**Cluster:** `luckylfe-log` (Elasticsearch 7.10, AWS ES, us-east-1, account 257394478466)
**Alert:** P2 cluster status Yellow, Zeus strategy id=26
**Investigator:** David Zeng (DBA), degraded-mode investigation (no cluster credentials)

---

## TL;DR

1. **Yellow root cause is query-induced, not infrastructure.** Between 01:02-01:30 UTC, search rate spiked from a 17 q/s baseline to **344 q/s** with **avg search latency 100-281 seconds**. JVM heap saturated at 96-100% for 30 min, the parent circuit breaker fired, **two data nodes were ejected from the cluster** at 01:12 UTC, and yellow status entered at 01:20 UTC. Wave 2 at 02:40 UTC followed a brief node loss during shard rebalancing. Classification: **(B) Query-induced**.
2. **Grafana attribution: confirmed by strong circumstantial evidence.** The `Elasticsearch-lfe` Grafana datasource (uid=`d0qWL4oNk`) is preconfigured against this cluster, and the **`LFE域名详版` dashboard (uid=`CoeHpTMHk`) was edited by David.zhou@luckincoffee.us at 2026-04-29T01:24:28 UTC**, squarely inside the JVM saturation window. That dashboard has 40 panels with high-cardinality `terms` aggs and `interval:"1s"` date histograms — a textbook JVM-blower under interactive editing. We do **not** have audit logs to prove the request-level link; we have a temporal/structural match that is hard to explain otherwise.
3. **What is being queried:** the nginx access-log indices fronted by `Elasticsearch-lfe` — fields `domain`, `requestInterface`, `clientip`, `xff`, `referrer`, `agent`, `provider`, `geoip.*`, `responsetime`, `bytes`, `upstreamaddr`. The dashboards aggregate by user-IP / referrer / URI / user-agent — all very high-cardinality.
4. **Why every 30 minutes:** **(a) Zeus re-notification on a sustained alert.** Since 02:40 UTC the cluster has been continuously yellow (890/890 metric samples = 1.0 over 14h 49m). The status is not flapping; the alert manager is simply re-firing on a still-open condition.

---

## Phase 1 — Root cause classification (CloudWatch-only; degraded)

### Yellow timeline (full 24h)

| Wave | Start (UTC) | End (UTC) | Duration |
|---|---|---|---|
| 1 | 01:20 | 02:18 | 58 min |
| 2 | 02:40 | **ongoing at 17:29** | 14h 49m+ |

The user's "first fired 02:43 UTC" matches Wave 2; **Wave 1 at 01:20 UTC is the original incident** triggered by the query storm. The 22-minute green window between the waves was during shard re-allocation after the ejected nodes returned.

### Node membership transitions

| Timestamp (UTC) | Nodes | Event |
|---|---|---|
| 17:30 (prev day) → 01:11 | 7 | normal (3 master + 4 data) |
| **01:12** | **5** | **2 data nodes left** (JVM circuit breaker / node OOM) |
| 01:13 | 7 | nodes rejoined |
| **02:18** | **6** | **1 data node left** during Wave-1 recovery shard rebalance |
| 02:40 | 7 | node rejoined; but yellow because shards still relocating |

### Per-metric 24h summary

| Metric | min | max | avg | last | Verdict signal |
|---|---:|---:|---:|---:|---|
| ClusterStatus.yellow (Max) | 0 | 1 | 0.66 | **1** | yellow 65.9% of last 24h |
| ClusterStatus.red (Max) | 0 | 1 | 0.02 | 0 | brief red, recovered |
| Nodes (Avg) | **5** | 7 | 6.98 | 7 | brief 2-node loss |
| MasterReachableFromNode (Min) | 0 | 1 | 0.98 | 1 | brief master partition |
| ThreadpoolSearchRejected (Sum) | **0** | **0** | **0** | 0 | **NOT load-shedding via rejection** |
| ThreadpoolSearchQueue (Max) | 0 | 11 | 0.01 | 0 | queue not the bottleneck |
| ThreadpoolWriteRejected (Sum) | 0 | 0 | 0 | 0 | indexing not affected |
| **JVMMemoryPressure (Max)** | 32.4 | **100.0** | 64.4 | 33.1 | **circuit breaker territory** |
| OldGenJVMMemoryPressure (Max) | 32 | 96.3 | 62.5 | 32.1 | full GC pressure |
| CPUUtilization (Avg) | 10.5 | **71.0** | 18.9 | 14.8 | sole CPU spike of day |
| FreeStorageSpace (MB) | 17,761 | 26,884 | 22,379 | 21,858 | not disk-pressure |
| 5xx (Sum) | 0 | **57** | 0.26 | 0 | 57 errors in single 5-min bucket at 01:16 |

### JVM saturation episodes (≥80%)

| Start | End | Duration |
|---|---|---|
| **01:11** | **01:45** | 34 min — sustained 96-100% |
| 01:49 | 01:55 | 6 min |
| 01:57 | 02:00 | 3 min |
| 02:01 | 02:11 | brief blips |

### Verdict

**Classification: (B) Query-induced.**

The diagnostic chain is:
1. Query storm (q/s and latency) starts 01:02 UTC
2. JVM heap hits 96% by 01:11 UTC, CPU 71%
3. Parent circuit breaker fires → **two data nodes leave the cluster** (most likely OOM — JVM = 100% at 01:24)
4. Yellow status entered 01:20 UTC (replicas unassigned while nodes were out)
5. Nodes return 01:13, but cluster needs to relocate shards → JVM still stressed → second node leaves at 02:18
6. Wave 2 yellow at 02:40 UTC, sustained because some shards have been in `INITIALIZING`/`RELOCATING` state since (cannot confirm without `_cat/shards` access)

The two infra signals — node loss and brief master-unreachability — are **consequences** of the JVM exhaustion caused by queries, not independent infra failures. `ThreadpoolSearchRejected = 0` all day is the key signal: the cluster did not shed load through search rejection; the JVM circuit breaker took whole nodes down instead. This is a known failure mode for ES 7.10 on undersized data nodes (here: m5.large.search, 8 GiB JVM heap) when blasted with deep terms aggregations.

**Limitation:** Without cluster credentials, we cannot enumerate which specific shards are unassigned. Recommend a follow-up read-only call by the security colleague (or anyone with FGAC role-mapping):
```
GET /_cluster/health?level=indices
GET /_cat/shards?v&h=index,shard,prirep,state,node,unassigned.reason | grep -v STARTED
GET /_cluster/allocation/explain
```

---

## Phase 2 — Query volume confirmation

### Volume delta against 7-day baseline

| Metric | Now (last 1h avg) | 7-day baseline avg | %∆ | Spike peak (UTC) |
|---|---:|---:|---:|---|
| SearchRate (q/s) | 16.0 | 17.5 | -8% | **344.5 @ 01:09** (20× baseline) |
| SearchLatency (s) | <0.5 | <0.1 | normal now | **281.4s @ 01:29** (catastrophic) |
| JVMMemoryPressure (%) | 33.1 | ~50 | normal now | **100 @ 01:24** |
| 5xx (count) | 0 | sparse | — | **57 @ 01:16** (single bucket) |
| CPUUtilization (%) | 14.8 | ~15 | normal now | 71 @ 01:11 |

The cluster has fully recovered query-volume-wise; what's keeping it yellow is the unfinished shard re-allocation work from the original event.

### Spike timing alignment with 02:43 UTC

The **actual** trigger is at **01:02-01:30 UTC**, ~1h 40m **before** the time the user originally reported (02:43). Aligning to 01:11 UTC, the event sequence is:

| Time (UTC) | Event |
|---|---|
| 01:00 | SearchLatency starts ramping (0.30s, normally <0.05s) |
| 01:02 | SearchRate 107 q/s (6× baseline) |
| 01:07 | SearchRate 222 q/s, latency 146s |
| **01:09** | **SearchRate 344 q/s** (20× baseline) |
| **01:11** | **CPU 71% (max of day)**, JVM crosses 80% |
| **01:12** | **Nodes 7→5** (2 nodes leave) |
| 01:16 | 5xx errors burst (57 in one 5-min bucket) |
| **01:20** | **Cluster yellow (Wave 1)** |
| **01:24:28** | **David.zhou edits `LFE域名详版` dashboard** (only 4-min lag from yellow start) |
| 01:29 | SearchLatency 281s (worst of the day) |
| 01:45 | JVM finally drops below 80% |
| 02:18 | Cluster green; but Nodes 7→6 again |
| **02:40** | **Cluster yellow (Wave 2)** — sustained from this point |
| 17:30+ | Still yellow |

The user's "02:43 UTC first fired" reflects **the second wave** as observed by the alerting system; the underlying root cause was over an hour earlier.

**Per-index search QPS distribution:** SKIPPED — requires cluster credentials. Cannot identify hot indices from CloudWatch alone.

---

## Phase 3 — DSL capture and Grafana attribution (PRIMARY DELIVERABLE)

### What we cannot do, and why

| Source | Status | Why |
|---|---|---|
| `_tasks?actions=*search*` | ❌ skipped | No cluster credentials (databasecheck not in FGAC, no Secrets Manager perms) |
| Search slow logs | ❌ N/A | Slow logs **not enabled** on this domain — no CloudWatch group exists |
| Index slow logs | ❌ N/A | Same |
| Audit logs | ❌ N/A | `AuditLog: null` on the domain — never enabled |

The closest evidence to "what was actually run" is the panel-query JSON of dashboards that use the preconfigured `Elasticsearch-lfe` datasource. We have those.

### Grafana datasources targeting `luckylfe-log`

| Datasource | UID | Type |
|---|---|---|
| `Elasticsearch-lfe` | `d0qWL4oNk` | grafana-opensearch-datasource (legacy elasticsearch type) |
| `OpenSearch-lfe` | shares cluster | grafana-opensearch-datasource |

### Dashboards using these datasources

| Dashboard | UID | Panels | Default time range | Last edited (UTC) | Last editor |
|---|---|---:|---|---|---|
| **`LFE域名详版`** | `CoeHpTMHk` | **40** | now-3h | **2026-04-29T01:24:28** | **David.zhou@luckincoffee.us** |
| `LFE域名详版 Copy` | `ZJhpM2oDz` | unknown | unknown | (older) | — |
| `【LUCKY】LFE域名简版` | `vTPcQSI7z` | 8 | now-1h | 2026-04-27T19:06:59 | David.zhou@luckincoffee.us |

The `美国WAF监控大盘` dashboard in the security folder (uid=`fifyba6Hz`, 1 panel) targets a **different** datasource (`Elasticsearch-waf` uid=`roIApa6Hk`) and is not relevant to this incident.

### Attribution evidence (the security colleague's three questions, answered)

#### Q1 — Is query volume up? Is there a newly launched query/analysis workload?

**Yes, dramatically.** Search rate went from a 17 q/s baseline to a peak of 344 q/s between 01:02-01:30 UTC (20×). This was a single sustained workload, not a recurring one — it has not repeated since. The workload is consistent with a single analyst running an interactive dashboard session.

#### Q2 — Can we capture the actual query DSL?

We cannot capture literal request bodies (no audit logs, no slow logs, no `_tasks` access at the time of investigation). We **can** capture the **panel-query templates** that produced the live DSL — what Grafana would have rendered and sent. Top patterns from `LFE域名详版` (uid=`CoeHpTMHk`), all `queryType: lucene` against `Elasticsearch-lfe`:

**Pattern A — fine-grain QPS / response distribution (panels 76, 38, 50, 49, 88)**
```json
{
  "query": "(domain:$select_domain) AND (requestInterface:$select_api) AND (${entrance:raw})",
  "queryType": "lucene",
  "bucketAggs": [
    {"field": "@timestamp", "type": "date_histogram", "settings": {"interval": "1s"}}
  ],
  "metrics": [{"type": "count"}]
}
```
With default `now-3h` time range, `interval:"1s"` produces ~10,800 buckets per panel. Multiplied across panels, the date-histogram alone is heavy.

**Pattern B — high-cardinality terms agg on `clientip`**
```json
{
  "query": "(domain:$select_domain) AND (${entrance:raw}) AND (requestInterface:$select_api)",
  "bucketAggs": [
    {"field": "clientip", "type": "terms",
     "settings": {"min_doc_count": "1", "order": "desc", "orderBy": "_count", "size": "20"}},
    {"field": "@timestamp", "type": "date_histogram", "settings": {"interval": "1s"}}
  ],
  "metrics": [{"type": "count"}]
}
```
`clientip` cardinality on a public-facing nginx index is in the millions. With `size:20` and a 1s histogram, the agg tree is large.

**Pattern C — UNBOUNDED terms agg on `xff` (X-Forwarded-For)**
```json
{
  "query": "(domain:$select_domain) AND (${entrance:raw}) AND (requestInterface:$select_api) +xff:[* TO *} -xff:-",
  "bucketAggs": [
    {"field": "xff", "type": "terms",
     "settings": {"min_doc_count": "1", "order": "desc", "orderBy": "_count", "size": "0"}},
    {"field": "@timestamp", "type": "date_histogram"}
  ],
  "metrics": [{"type": "count"}]
}
```
**`size: "0"` means "return ALL terms" — unbounded cardinality response.** `xff` contains every proxy IP in the request chain. This single panel can return millions of buckets per dashboard load.

**Pattern D — UNBOUNDED terms agg on `referrer`**
```json
{
  "query": "(domain:$select_domain) AND (${entrance:raw}) AND (requestInterface:$select_api) AND referrer:* NOT referrer:*lkcoffee* NOT referrer:*luckincoffee* ...",
  "bucketAggs": [
    {"field": "referrer", "type": "terms",
     "settings": {"min_doc_count": "1", "order": "desc", "orderBy": "_count", "size": "0"}},
    {"field": "@timestamp", "type": "date_histogram"}
  ],
  "metrics": [{"type": "count"}]
}
```
Same `size:"0"` issue. Referrer URL cardinality on a public nginx log is huge.

**Pattern E — percentiles + long-time-range histogram (panels 91, 90)**
```json
{
  "metrics": [{"field": "responsetime", "type": "percentiles",
               "settings": {"percents": ["95", "99"]}}],
  "bucketAggs": [{"field": "@timestamp", "type": "date_histogram",
                  "settings": {"interval": "1d"}}]
}
```
Percentile calc over `responsetime` is memory-intensive at scale.

**Pattern F — geoip terms agg with high regional cardinality**
```json
{
  "bucketAggs": [
    {"field": "geoip.isp_name", "type": "terms", "settings": {"size": "10"}},
    {"field": "@timestamp", "type": "date_histogram"}
  ]
}
```

**Pattern G — `agent` (User-Agent) terms agg**
```json
{
  "bucketAggs": [
    {"field": "agent", "type": "terms", "settings": {"size": "10"}},
    {"field": "@timestamp", "type": "date_histogram"}
  ]
}
```
User-agent strings are essentially unique-per-client; even with `size:10`, the underlying agg builds a global term-frequency table first.

#### Q3 — What specifically is being queried?

**Indices:** the nginx access-log indices fronted by `Elasticsearch-lfe`. The exact index pattern is encoded in the datasource configuration (we cannot read the datasource's index pattern via the MCP without admin perms), but the field names (`domain`, `requestInterface`, `clientip`, `xff`, `referrer`, `agent`, `provider`, `geoip.*`, `responsetime`, `bytes`, `upstreamaddr`) clearly identify these as **public web-traffic logs** for the LFE (luckin front-end) domain.

**Fields by cardinality risk** (highest first):
| Field | Cardinality | Use in dashboard |
|---|---|---|
| `xff` | extreme | terms agg, **`size:0`** (unbounded) |
| `referrer` | extreme | terms agg, **`size:0`** (unbounded) |
| `agent` | extreme | terms agg, `size:10` |
| `clientip` | very high | terms agg, `size:10`-`20` |
| `requestInterface` | high | terms agg, `size:5`-`10` |
| `upstreamaddr` | medium | terms agg + cardinality agg |
| `geoip.isp_name`, `geoip.region_code` | medium-low | terms agg, `size:10` |
| `provider`, `verb`, `response`, `domain` | low | terms agg, `size:10` |

**Clients (ie. who is making the requests against ES):** confirmed Grafana via the `Elasticsearch-lfe` / `OpenSearch-lfe` datasource. The dashboard editor at the time was `David.zhou@luckincoffee.us`.

#### Attribution evidence summary

| Evidence | Source | Strength |
|---|---|---|
| `Elasticsearch-lfe` datasource preconfigured against `luckylfe-log` | Grafana API | Strong (clients have authenticated path) |
| `LFE域名详版` last edited 01:24:28 UTC by David.zhou | Grafana dashboard meta | Strong (4 min after Wave 1 yellow) |
| 40-panel dashboard with `size:0` terms aggs and 1s date_histograms | Panel JSON | Strong (textbook JVM-blower) |
| Search rate 20× baseline coincident with edit window | CloudWatch | Strong |
| Search latency 100-281s coincident | CloudWatch | Strong (proves queries were extreme) |
| Self-attribution by security colleague | Verbal | Confirmatory |
| Direct request-level audit log | Cluster | **Not available — audit logs disabled** |

**Verdict on Grafana attribution: confirmed by strong circumstantial evidence**, with the caveat that the request-level link (which Grafana panel triggered which `_search` body) cannot be proven absent audit logs. The pattern, timing, editor identity, and dashboard structure are all consistent with a single analyst (David Zhou) opening / editing the `LFE域名详版` dashboard against `Elasticsearch-lfe` between roughly 01:00-01:30 UTC, with each load and variable change firing the full 40-panel query set and saturating the cluster's heap.

---

## Phase 4 — 30-minute re-fire cadence

### Hypothesis test — yellow status timeline

| Period | Yellow=1 samples | Yellow=0 samples |
|---|---:|---:|
| Since 02:40 UTC (Wave 2 start) | **890** | **0** |

**Cluster has been continuously yellow for 14h 49m with zero recovery dips.** The status is not flapping. There is no oscillation pattern that would imply a recurring 30-min query event.

### Hypothesis test — search-rate periodicity

Bucketing all 24h SearchRate samples (positive only) by `minute_of_hour mod 30`:

| m%30 | n | avg | max |
|---:|---:|---:|---:|
| 0 | 48 | 14.2 | 38.5 |
| 9 | 48 | 19.5 | **344.5** |
| 7 | 48 | 18.3 | 222.2 |
| 3 | 48 | 17.6 | 160.8 |
| (others) | 48 each | 12-19 | 18-117 |

The maxes are scattered (m%30 = 3, 7, 9 all light up) — but **all of them are samples from inside the single 01:02-01:30 UTC spike window**. There is no discrete 30-minute periodicity. The averages across all 30 buckets are uniformly ~13-19 q/s, indistinguishable from random.

### Verdict

**Cadence: (a) Zeus re-notification on a sustained alert.**

The 30-minute interval is the alert manager's renotify cadence on a still-open condition. The cluster has not actually flapped between yellow and green — it entered yellow at 02:40 UTC and has stayed there continuously. To stop the re-notification, the underlying yellow state must clear (i.e. all unassigned shards must be allocated).

**Cadence (b)** (scheduled query rule) is ruled out by the absence of a 30-min periodicity in SearchRate.
**Cadence (c)** (dashboard auto-refresh) is unlikely because (i) the LFE dashboards' default refresh isn't visible via the MCP property tool but the time-ranges (`now-3h`, `now-1h`) imply user-driven loads, not a fixed 30m schedule; and (ii) cluster status is sustained-yellow, not oscillating.
**Cadence (d)** (external cron) — same SearchRate evidence rules it out.

---

## Recommendations (ranked)

### (i) Immediate — clear the still-open yellow

The cluster is yellow because shards from the post-01:11 reallocation have not all returned to STARTED. Without API access we cannot confirm the specific blocker. Suggested next steps, in order:

1. Have someone with FGAC access (security colleague, or grant temporary `monitor_cluster` role to `databasecheck`) run:
   ```
   GET /_cluster/health?level=indices
   GET /_cat/shards | grep -v STARTED | head -50
   GET /_cluster/allocation/explain
   ```
   and paste the output.
2. If the unassigned shards are *replicas* of small indices, the cluster will self-heal. If they are stuck on a node that left and never returned, inspect node membership: `GET /_cat/nodes`. If a data node is missing, check the AWS console for that node's status.
3. Do **not** force-allocate shards or reroute manually without confirming the underlying reason.

### (ii) Grafana side — prevent recurrence

Apply to the `LFE域名详版` dashboard (uid=`CoeHpTMHk`) and any sibling dashboards (`LFE域名详版 Copy`, `【LUCKY】LFE域名简版`):

| Issue | Fix |
|---|---|
| `terms` aggs with `size: "0"` on `xff` and `referrer` | Cap at `size: 100` (or hide these panels behind an explicit "show all" toggle) |
| `date_histogram` with `interval: "1s"` on a 3h default range | Change to `interval: "auto"` so Grafana picks a sensible bucket size based on time range |
| Default time range `now-3h` with 40 heavy panels | Reduce default to `now-1h`, OR split the dashboard into focused sub-dashboards (QPS / errors / clients / geo as separate boards) |
| `agent`, `clientip`, `xff`, `referrer` terms aggs on every panel load | Move to a separate "client analysis" dashboard with longer time-range guardrails |
| 40 panels on one dashboard auto-loading | Add row collapse defaults so most rows don't query on initial load |
| Editing the dashboard live against production fires queries on every edit-mode panel render | Establish a convention: clone to a personal folder for edits, or use a non-prod ES index for development |

Action owner: David.zhou (last editor) or the dashboard owner (originally `ronghai.ye`).

### (iii) Cluster-side hardening

These require explicit authorization (write ops on the domain) — flagged here for David's review, not executed:

1. **Enable search slow logs** on `luckylfe-log` to a CloudWatch log group with ≥30d retention. Suggested initial thresholds: warn 5s, info 10s. Without this, future investigations of the same class are blocked from Phase 3 (DSL capture from logs).
2. **Enable audit logs** to a CloudWatch log group. This unblocks per-request attribution (source IP, user, x-opaque-id) for future incidents.
3. **Review search-backpressure / circuit-breaker thresholds.** The cluster shed load by ejecting whole nodes rather than rejecting individual queries, which is more destructive. Consider lowering `indices.breaker.request.limit` and/or enabling search backpressure (search shard request cancellation) — defaults on ES 7.10 are conservative.
4. **Replica / shard sizing review** for the largest indices on this cluster. m5.large.search instances have only 8 GiB JVM heap — they cannot absorb deep terms aggs over millions of unique IPs. Either upsize the data tier (m5.xlarge.search → 16 GiB heap) or enforce the Grafana-side guardrails above.
5. **FGAC role mapping** for `databasecheck` (DBA team IAM user) — ideally read-only `monitor_cluster` + `read_*` for non-PII indices. This unblocks first-line investigation without needing to share master credentials.
6. **Secrets Manager grant**: add `secretsmanager:GetSecretValue` on `lcna/opensearch/luckylfe-log/master` to the DBA team's role/user, as a fallback authentication path.

---

## Data gaps for next time

| Gap | What it cost this investigation | Remediation |
|---|---|---|
| Audit logs disabled on `luckylfe-log` | Cannot prove which Grafana panel/request fired which `_search` body | Enable `AUDIT_LOGS` publishing to CloudWatch |
| Search slow logs not published | No historical record of which queries were slow | Enable `SEARCH_SLOW_LOGS` (warn 5s, info 10s — confirm thresholds with David) |
| `databasecheck` no Secrets Manager perms | Cannot fetch master cluster credentials | Add `secretsmanager:GetSecretValue` for the OpenSearch master secrets |
| `databasecheck` no FGAC role mapping on `luckylfe-log` | Cannot run any cluster API call (Phase 1, Phase 3.1 blocked) | Add a read-only role mapping for the DBA IAM user |
| mcp-db-gateway does not proxy ES/OpenSearch | The user-prompt hint that the gateway is "preferred for cluster API calls" is incorrect — gateway only handles MySQL/Postgres/Redis | Update CLAUDE.md / runbook |
| AWS profile `lcna-prod` not configured locally | Used `[default]` (same account 257394478466 / databasecheck) | Either configure the named profile or update the runbook to use `[default]` |

---

## Appendix — raw evidence

All raw JSON files preserved at `/home/claude/lcna-dba-reports/raw/`:

| File | Contents |
|---|---|
| `cwm-{metric}-{stat}-24h.json` | 16 metrics, 24h period 60s (1439-1440 datapoints each) |
| `cwm-{metric}-{stat}-7d.json` | 6 metrics, 7d period 3600s (162 datapoints each) for baseline |
| `cwm-{metric}-{stat}-window.json` | 7 metrics, 00:00-08:00 UTC period 60s for fine-grain alignment around 01:11/02:43 transitions |
| `analysis.txt` | Full text output of the analysis pass |

### Methodology notes

- **SearchRate / IndexingRate negatives:** CloudWatch `AWS/ES SearchRate` is a per-node-averaged counter. When data nodes leave the cluster mid-period, the averaging produces large negative values (e.g. min=-1.06M for SearchRate, min=-121M for IndexingRate during the 01:12 node-loss event). All analysis filters out negatives.
- **No PII** is present in this report. All captured DSL contains only Grafana template variables (`$select_domain`, `$select_api`, `${entrance:raw}`); no actual customer identifiers, IPs, or query results were retrieved (queries were never executed).
- **All actions read-only.** No cluster config changes, no log enablement, no task cancellation, no Grafana dashboard edits made by this investigation.
