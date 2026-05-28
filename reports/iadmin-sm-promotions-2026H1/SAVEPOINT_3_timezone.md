# SAVEPOINT 3 — Timezone echo

| Field | Value |
|---|---|
| @@global.time_zone | UTC |
| @@session.time_zone | UTC |
| NOW() (server) | 2026-05-27 23:52:59 UTC |
| UTC_TIMESTAMP() | 2026-05-27 23:52:59 UTC |

## Window interpretation
- Business window: 2026-01-01 00:00 → 2026-05-27 23:59 PT
- `effective_date` column is VARCHAR(10) — date-only, no time component
- Used filter: `effective_date BETWEEN '2026-01-01' AND '2026-05-27'` (inclusive)
- This treats effective_date as a logical date string — matches how the application records the day a change took effect (no TZ ambiguity for date-only field).
