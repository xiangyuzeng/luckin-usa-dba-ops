# SAVEPOINT 5 — Dedup & sanity checks

## Window result
- **8 rows** in window where to_post_code='LKUS00000082' AND from != SM
- **8 distinct emp_no** — no duplicates, no dedup needed
- subsequent_changes_count = 0 for all 8 (no one was promoted to SM twice; subsequent same-code transfers are dept changes, not post changes)

## Cross-check vs current SM population
- Total currently-active employees with primary post = SM: **17**
- Promoted-to-SM in window: **8** (≤ 17 ✓ sane)
- Interpretation: ~47% of current SM headcount was promoted in the past 5 months — consistent with rapid 10-store expansion

## "From" post distribution
| from_post_code | from_post_name | count |
|---|---|---|
| LKUS00000098 | Store Manager Trainee | 8 |

All 8 promotions came from SMT — clean linear progression (no Barista→SM or ASM→SM leapfrog in window).

## Per-emp full history verification (61 lifetime rows for the 8 emps)
- Each emp has exactly **one** SM transition (SMT→SM) within window
- All 8 have post-SM same-code transfers (dept changes only); none demoted back out of SM
- Pre-SM career paths varied:
  - 3 directly hired as SMT (US202507280004 Shangxian Piao, US202509090009 Kayen Wu He, US202510210001 Javier Cruz)
  - 4 promoted via ASMT→ASM→SMT path
  - 1 (Huichen Jiang) climbed from Barista Trainee → BT → SS → ASM → SMT → SM in 10 months
