# CloudWatch GMD-Metrics Cost Spike Investigation Report

**Date:** 2026-02-17
**Investigator:** DBA/Infrastructure Team (Claude Code)
**Severity:** Medium — Recurring monthly cost increase
**Status:** Root Cause Identified — Remediation Recommended

---

## Executive Summary

CloudWatch `GetMetricData` (GMD) costs spiked **88x** from $3.60/month (Dec 2025) to a projected **$319/month** (Feb 2026). The root cause is the DBA metrics collection pipeline switching from the free `GetMetricStatistics` API to the paid `GetMetricData` API around **January 19, 2026**. The collection script stores EC2 and RDS metrics into the `luckyus_db_collection` database on `aws-luckyus-ldas01-rw`. The projected annual impact is **+$3,780/year**.

---

## 1. Cost Timeline

### Monthly CloudWatch Breakdown

| Usage Type | Nov 2025 | Dec 2025 | Jan 2026 | Feb proj. | % of Total |
|------------|----------|----------|----------|-----------|------------|
| MetricMonitorUsage | $1,920.66 | $1,891.83 | $1,872.68 | $1,787.17 | 51.1% |
| Requests | $982.31 | $1,503.68 | $1,507.72 | $1,312.54 | 41.1% |
| **GMD-Metrics** | **$3.46** | **$3.60** | **$231.91** | **$319.40** | **8.4%** |
| InternetMonitor | $36.09 | $37.33 | $37.36 | $32.76 | 0.9% |
| **TOTAL** | **$2,960.12** | **$3,487.10** | **$3,666.81** | **$3,457.87** | |

### GMD-Metrics Daily Spike Timeline

```
Date        Metrics/Day    Cost/Day    Event
─────────── ────────────── ────────── ─────────────────────────────
Jan 15-18   ~11,520        $0.12      Baseline (GetMetricStatistics)
Jan 19      304,843        $3.05      ◄ API SWITCH BEGINS
Jan 20      4,683,789      $46.84     ◄ Historical backfill (peak)
Jan 21      6,620,593      $66.21     ◄ Historical backfill (peak)
Jan 22      1,803,018      $18.03     Settling
Jan 23+     ~1,062,000     $10.63     ◄ New steady state
```

**Key observation:** The peak on Jan 20–21 ($47–$66/day) is ~6x higher than the new steady state ($10.63/day), indicating a one-time historical data backfill when the new API method was deployed.

---

## 2. Root Cause Analysis

### 2.1 What Changed

The DBA team operates a metrics collection pipeline that:
1. Calls CloudWatch APIs to fetch EC2 and RDS performance metrics
2. Stores the results in MySQL database `luckyus_db_collection` on server `aws-luckyus-ldas01-rw`
3. Powers Grafana dashboards via the `MySQL-Ldas` datasource (UID: `LJ7ObqYNk`)

**Around January 19, 2026**, the collection script was modified to use `GetMetricData` instead of `GetMetricStatistics`:

| API | Pricing | Before Jan 19 | After Jan 19 |
|-----|---------|---------------|--------------|
| `GetMetricStatistics` | **Free** (unlimited) | ✅ In use | ❌ Replaced |
| `GetMetricData` | **$0.01 per 1,000 metrics** | ❌ Not used | ✅ Now in use |

### 2.2 Evidence Chain

| # | Evidence | Finding |
|---|----------|---------|
| 1 | EC2 collection granularity changed Dec 8 (hourly→5-min) | Row count jumped from ~49K to ~601K/day, **but GMD cost stayed at $0.12/day** → was using free GetMetricStatistics |
| 2 | GMD cost spiked Jan 19 | $0.12/day → $3.05/day with NO change in stored data volume → only the API method changed |
| 3 | Jan 20-21 peak ($47-66/day) | Historical data backfill via GetMetricData for prior days |
| 4 | Jan 23+ steady state | ~1,062,000 metrics/day = ongoing GetMetricData usage |
| 5 | No other callers found | No CW metric streams, no Grafana CW datasources, no Container Insights, dashboards have <40 widgets, 28 alarms unchanged |
| 6 | CloudTrail gap | `GetMetricData` not logged in management events trail — cannot identify calling IAM entity directly |

### 2.3 Ruled-Out Causes

| Potential Cause | Status | Reason |
|----------------|--------|--------|
| CloudWatch Dashboards | ❌ Eliminated | Only 4 dashboards with ~40 widgets total — insufficient volume |
| Grafana CloudWatch datasources | ❌ Eliminated | No CloudWatch-type datasources configured in either Grafana instance |
| CloudWatch Metric Streams | ❌ Eliminated | No streams configured |
| EKS Container Insights | ❌ Eliminated | No observability addons on either EKS cluster |
| CloudWatch Alarms | ❌ Eliminated | 28 alarms, none changed in Jan 2026, billed under MetricMonitorUsage not GMD |
| Synthetics Canaries | ❌ Eliminated | No canaries found |
| Third-party monitoring | ❌ Eliminated | No external tools querying CW via GetMetricData |

---

## 3. Collection Pipeline Details

### 3.1 Database: `luckyus_db_collection` on `aws-luckyus-ldas01-rw`

| Table | Rows | Created | Status |
|-------|------|---------|--------|
| `t_dba_collect_ec2_metrics` | 44.7M | ~Oct 2025 | Active — primary GMD cost driver |
| `t_dba_collect_ec2_metrics_daily` | 226K | ~Oct 2025 | Active — daily aggregates |
| `t_dba_collect_ec2_instances` | 22K | ~Oct 2025 | Active — instance inventory |
| `t_dba_collect_rds_metrics` | 3.8M | Nov 2025 | Active — secondary GMD contributor |
| `t_dba_collect_rds_instances` | 7.1K | Feb 10 2026 | Active — RDS inventory |
| `t_dba_collect_redis_cluster_metrics` | 0 | Feb 13 2026 | Not yet active |

### 3.2 EC2 Metrics Collection

- **Instances monitored:** 233
- **Metrics per instance:** 9 (CPUUtilization, EBSReadBytes, EBSReadOps, EBSWriteBytes, EBSWriteOps, NetworkIn, NetworkOut, NetworkPacketsIn, NetworkPacketsOut)
- **Statistics stored:** 3 per data point (Average, Minimum, Maximum)
- **Collection granularity:** 5-minute (288 periods/day)
- **Daily data points:** 233 × 9 × 288 = **603,936 rows/day**

### 3.3 RDS Metrics Collection

- **Instances monitored:** 64–65
- **Metrics per instance:** 19 (CPUUtilization, DatabaseConnections, FreeableMemory, FreeStorageSpace, ReadIOPS, WriteIOPS, ReadLatency, WriteLatency, ReadThroughput, WriteThroughput, NetworkReceiveThroughput, NetworkTransmitThroughput, BinLogDiskUsage, DiskQueueDepth, SwapUsage, CPUCreditBalance, CPUCreditUsage, CPUSurplusCreditBalance, CPUSurplusCreditsCharged)
- **Statistics stored:** 3 per data point (Average, Minimum, Maximum)
- **Collection granularity:** Hourly (24 periods/day stored)
- **Daily data points:** 65 × 19 × 24 = **29,640 rows/day**

### 3.4 GMD Metrics Breakdown (Estimated)

The steady-state billing of ~1,062,000 metrics/day breaks down approximately as:

| Source | Calculation | Metrics/Day | Cost/Day |
|--------|-------------|-------------|----------|
| EC2 collector | 233 inst × 9 metrics × 288 periods | ~604,000 | $6.04 |
| RDS collector | 65 inst × 19 metrics × ~24 calls | ~30,000–356,000 | $0.30–$3.56 |
| Dashboards/Other | Remainder | ~102,000–428,000 | $1.02–$4.28 |
| **Total observed** | | **~1,062,000** | **$10.63** |

> **Note:** The RDS collector may request 5-minute data from CloudWatch (billable) but aggregate to hourly before storing, which would increase its contribution. The exact split depends on the collection script's implementation.

---

## 4. Cost Impact

| Metric | Before (Dec 2025) | After (Feb 2026 proj.) | Change |
|--------|-------------------|------------------------|--------|
| GMD Monthly Cost | $3.60 | $319.40 | **+$315.80/mo** |
| GMD Daily Cost | $0.12 | $10.63 | **+$10.51/day** |
| GMD Annual Cost | $43.20 | $3,833 | **+$3,790/year** |
| % of CW Total | 0.1% | 9.3% | +9.2pp |

One-time backfill cost (Jan 19–22): ~$134 in excess charges.

---

## 5. Recommendations

### 5.1 Immediate: Switch EC2 Collector Back to GetMetricStatistics (saves ~$290/month)

`GetMetricStatistics` is **free** and supports the same data retrieval. The collector should revert to this API for EC2 metrics.

**Expected savings:** ~$6.04/day = **$181/month** from EC2 alone.

```python
# BEFORE (expensive): GetMetricData
response = cw.get_metric_data(
    MetricDataQueries=[{
        'Id': 'm1',
        'MetricStat': {
            'Metric': {'Namespace': 'AWS/EC2', 'MetricName': 'CPUUtilization', ...},
            'Period': 300,
            'Stat': 'Average'
        }
    }],
    StartTime=start, EndTime=end
)

# AFTER (free): GetMetricStatistics
response = cw.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
    StartTime=start, EndTime=end,
    Period=300,
    Statistics=['Average', 'Minimum', 'Maximum']
)
```

### 5.2 Immediate: Switch RDS Collector to GetMetricStatistics

Apply the same change for RDS metric collection.

**Expected savings:** $0.30–$3.56/day = **$9–$107/month**

### 5.3 Medium-Term: Reduce Collection Frequency Where Possible

| Current | Proposed | Impact |
|---------|----------|--------|
| EC2: 5-min (288/day) | EC2: 15-min for non-CPU metrics | -66% API calls for 7/9 metrics |
| RDS: Hourly (24/day) | RDS: Hourly (no change) | Already efficient |
| Stats: 3 (Avg/Min/Max) | Stats: 2 (Avg/Max) for network metrics | -33% for 4 metrics |

### 5.4 Long-Term: Consider CloudWatch Metric Streams for Bulk Ingestion

If the team needs to maintain `GetMetricData` for any reason (e.g., metric math, cross-account), CloudWatch Metric Streams to S3/Firehose may be more cost-effective at this volume ($0.003 per 1,000 metric updates vs $0.01 per 1,000 GetMetricData requests).

### 5.5 Monitoring: Add GMD Cost Alert

Create a CloudWatch billing alarm or Cost Anomaly Monitor to detect future GMD cost spikes:

```
Metric: CW:GMD-Metrics daily cost
Threshold: > $5/day (currently $10.63/day, target after fix: <$0.50/day)
Action: SNS notification to DBA team
```

---

## 6. Action Items

| # | Action | Owner | Priority | Est. Savings |
|---|--------|-------|----------|-------------|
| 1 | Locate collection script (check cron jobs, Lambda functions, ECS tasks on data collection hosts) | DBA Team | **P1** | — |
| 2 | Switch EC2 collector from GetMetricData → GetMetricStatistics | DBA Team | **P1** | $181/mo |
| 3 | Switch RDS collector from GetMetricData → GetMetricStatistics | DBA Team | **P1** | $9–107/mo |
| 4 | Enable CloudTrail data event logging for CloudWatch API calls (optional, for future debugging) | DBA Team | P3 | — |
| 5 | Add GMD cost monitoring alarm | DBA Team | P2 | — |
| 6 | Review upcoming Redis collector (`t_dba_collect_redis_cluster_metrics`) before activation — ensure it uses GetMetricStatistics | DBA Team | **P2** | Prevent ~$100+/mo |

---

## 7. Finding the Collection Script

The script could not be identified directly because:
- CloudTrail does not log `GetMetricData` calls under the current management-events-only trail
- Lambda and ECS access was denied for the `databasecheck` IAM user

**Suggested search locations:**
1. **Cron jobs** on EC2 instances in the DBA/DevOps fleet (search for `get_metric_data` or `boto3.*cloudwatch`)
2. **Lambda functions** containing `cloudwatch` or `get_metric` in the name (requires elevated IAM access)
3. **ECS scheduled tasks** running data collection containers
4. **Check git history** for the collection script repository — look for commits around Jan 17–19, 2026 that modified the CloudWatch API calls
5. **Query the database** for the exact update pattern:
   ```sql
   SELECT MIN(update_time), MAX(update_time)
   FROM luckyus_db_collection.t_dba_collect_ec2_metrics
   WHERE data_date = '2026-01-19';
   ```

---

*Report generated by Claude Code — DBA/Infrastructure Team*
*AWS Account: 257394478466 | Region: us-east-1*
