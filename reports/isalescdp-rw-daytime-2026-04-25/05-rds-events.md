# Phase 1E — RDS / CloudTrail events (last 7 days)

## Result: only routine backups. Nothing changed on the RDS side.

```
2026-04-19 03:51:24Z   backup    Backing up DB instance
2026-04-19 03:57:27Z   backup    Finished DB Instance backup
2026-04-20 03:52:33Z   backup    Backing up DB instance
2026-04-20 03:56:36Z   backup    Finished DB Instance backup
2026-04-21 03:51:38Z   backup    Backing up DB instance
2026-04-21 03:57:41Z   backup    Finished DB Instance backup
2026-04-22 03:51:36Z   backup    Backing up DB instance
2026-04-22 03:57:39Z   backup    Finished DB Instance backup
2026-04-23 03:51:42Z   backup    Backing up DB instance
2026-04-23 03:57:45Z   backup    Finished DB Instance backup
2026-04-24 03:51:44Z   backup    Backing up DB instance
2026-04-24 03:57:49Z   backup    Finished DB Instance backup
2026-04-25 03:51:51Z   backup    Backing up DB instance
2026-04-25 03:57:54Z   backup    Finished DB Instance backup
```

## What this rules out

- **Parameter group change**: none. Confirmed via `ParameterApplyStatus = in-sync` and
  no `configuration` events.
- **Instance class change**: none.
- **Reboot / failover / restart**: none.
- **Storage class change**: none.
- **Manual modification**: none.
- **Maintenance event**: none. Next maintenance window: `sat:04:52-sat:05:22` (i.e. Sat 2026-04-26).

## Implication for the verdict

Whatever caused the daytime spike, it was **not** an RDS-side change. The cause is
in the workload (or its sensitivity to existing workload + instance capacity).
This eliminates the "did the DBA team do something Tuesday" line of questioning
preemptively.
