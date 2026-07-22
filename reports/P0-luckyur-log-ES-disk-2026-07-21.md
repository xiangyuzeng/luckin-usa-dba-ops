# P0 — OpenSearch `luckyur-log` Disk Exhaustion (2026-07-21)

**Alert:** 【DB告警】AWS-ES磁盘空间不足10G_语音 · P0 · 集群 `luckyur-log`
**Fired:** 2026-07-21 19:31 EDT (23:31 UTC), value 9,739.95 MB free · legacy policy id=97
**Investigated:** 2026-07-22 by David Zeng (databasecheck)

## Verdict
**Real P0 — chronic capacity exhaustion, not a blip.** The cluster is effectively **full**. The alarm's 9.7 GB is already stale: since it fired, the hottest data node has repeatedly dipped to **1.1–3 GB free** (min 1,131 MB @ 21:20 UTC).

- ✅ **Writes NOT yet blocked** — `ClusterIndexWritesBlocked = 0` throughout. Ingest still working.
- ✅ **Cluster not RED** — `ClusterStatus.red = 0`; all 7 nodes present (4 data + 3 master).
- 🔴 **Zero headroom** — hottest node oscillating 1–4 GB free at flood-stage watermark. Write-block / read-only indices imminent (hours, not days).

## Evidence

**Domain:** ES 7.10, 4× `m5.xlarge.search` data + 3× `t3.medium.search` master, **500 GB gp2/node = 2 TB gross (~1.86 TB usable)**, 2-AZ, VPC-only. Single-copy by design (0 replicas — no replica lever available).

**14-day trend (`ClusterUsedSpace` / min `FreeStorageSpace`):**

| Date | Used | Min free/node |
|------|------|---------------|
| Jul 08 | 1.47 TB | ~70 GB |
| Jul 15 | 1.56 TB | ~49 GB |
| Jul 19 | 1.70 TB | ~16 GB |
| Jul 20 | 1.70–1.82 TB | 5.7 GB |
| Jul 21 | 1.74–1.85 TB | **1.1 GB** |

- **Net growth ≈ +27.5 GB/day** (retention is NOT keeping pace with ingest → indices accumulating).
- Daily sawtooth: free recovers ~00:00–06:00 UTC (nightly rollover/deletion) then depletes through the day; baseline climbing steadily into saturation.
- **Days of runway remaining: ~0** — already at the wall.

## Why I can't self-remediate
- **ES API (delete indices / inspect ISM):** VPC endpoint reachable + SigV4 auth OK, but FGAC returns `security_exception` — `databasecheck` has `backend_roles=[]`, no OpenSearch permissions. Needs the OpenSearch master user via **Kibana Dev Tools**.
- **EBS expansion:** `databasecheck` is explicitly denied `es:UpdateDomainConfig` (`luckin-deny-iam-write`). Needs Michael / elevated role.

## Recommended actions (need elevated access — Michael)

**1. Immediate relief — reclaim space (fastest, free).** Via Kibana Dev Tools:
   - `GET _cat/indices?v&s=store.size:desc` — find largest / oldest indices.
   - Delete oldest log indices (log data, low value). Each day of retention ≈ **~27 GB** freed per node's worth.
   - Confirm/repair the ISM rollover+delete policy — the +27.5 GB/day net growth means deletion isn't running or a new high-volume log source was added.

**2. Buy runway — expand EBS (in-place, no blue/green, ~30 min):**
   - 500 → 650 GB/node (`aws opensearch update-domain-config --domain-name luckyur-log --ebs-options ...`).
   - Cost: +600 GB × $0.10/GB-mo × 0.69 EDP ≈ **+$41/mo**. Buys ~22 days at current growth. Does NOT fix root cause — pair with (1).

**Recommendation:** do both — expand now for safety margin, then fix retention/ISM to stop the bleed. Then lower the alert threshold cushion won't help; the real fix is retention.

## Immediate mitigation if writes block before access is available
If `ClusterIndexWritesBlocked` flips to 1, indices go `read_only_allow_delete`. After freeing space, clear the block (master user):
`PUT _all/_settings {"index.blocks.read_only_allow_delete": null}`
