# intl-dw-ops-dashboard — Build Metadata Summary

**Repo:** `xiangyuzeng/intl-dw-ops-dashboard` · local clone at `/app/intl-dw-ops-dashboard` · branch `main`
**Generated:** 2026-06-03 · All values gathered read-only (nothing modified).

---

## 1. STACK VERSIONS

| Dependency | Declared (package.json) | Resolved (package-lock.json) |
|---|---|---|
| next | `14.0.4` (pinned) | **14.0.4** |
| react | `^18.2.0` | **18.3.1** |
| react-dom | `^18.2.0` | **18.3.1** |
| recharts | `^2.10.3` | **2.15.4** |

- **Only 4 runtime deps** — no other `dependencies`, **no `devDependencies`**.
- **Node engine:** not specified (no `engines` field). Local build env = Node **v20.20.2**.
- Package: `name: intl-dw-ops-dashboard`, `version: 0.1.0`, `private: true`.
- Scripts: `dev` / `build` / `start` (stock Next.js App Router). npm lockfile v3.
- `next.config.js`: `reactStrictMode: true` only.

---

## 2. DATA COVERAGE (`app/data.js` — 357 KB, pure data, no imports/JSX)

- **Databases listed:** **53** (`CYBERDATA_OVERVIEW.totalDatabases`).
  - Supporting: 20 ODS source-DB cards (`ODS_SOURCES`); 44 distinct `db` names across documented table rows.
- **Tables documented (sum of layer arrays):** **620**
  - ODS 267 · DWD 126 · DWS 55 · ADS 126 · DIM 46 = **620** individually-listed table rows.
  - ⚠️ Distinct from the **warehouse total of 1,477** (`LINEAGE_STATS.totalTables`; `CYBERDATA_OVERVIEW.totalTables` = 1,474). The 620 are per-table inventory rows; the remaining ~857 are counted only in aggregate (donut / layer cards).
- **LINEAGE_MAP entries:** **481** keys (matches `LINEAGE_STATS.mappedTables` = 481; 858 upstream edges).
- **Enum / field-definition entries:** **39** (`ENUM_FIELDS`).
- **Snapshot timestamp baked in:** no field literally named `dataFreshness`. Two timestamps exist:
  - `CYBERDATA_OVERVIEW.lastUpdated` = **`2026-04-03 03:03:04`** (overview card).
  - Inventory/lineage regeneration snapshot = **`2026-04-28 18:08 UTC`** (`scripts/cyberdata_snapshot.json` + `extraction_report.md`), auto-generated from `luckyus_icyberdata.meta_table` + `.task`.
- **Four tab/section names (`app/page.jsx`)** — `TABS` imported from `data.js`, rendered via `activeTab ===` switches:

  | id | label (中文) | English | render fn |
  |---|---|---|---|
  | `overview` | 基础概览 | Basic Overview | `renderOverview()` |
  | `lineage` | 库表血缘 | Table Lineage | `renderLineage()` |
  | `enum` | 枚举解析 | Enum Resolution | `renderEnum()` |
  | `risk` | 异常风险分析 | Anomaly / Risk Analysis | `renderRisk()` |

---

## 3. BUILD TIMELINE (git log — 13 commits total)

- **First commit:** `2026-04-03 19:24:33 UTC` — *"Initial commit: 国际化数仓运维看板 (International DW Ops Dashboard)"*
- **Last commit:** `2026-04-10 03:19:12 UTC` — *"Fix commit author email to xzeng36@wisc.edu for Vercel deployment"*
- **Total commits:** **13**
- **Elapsed span:** **7 calendar days** (Apr 3 → Apr 10); ~**6 days 8 h** wall-clock (≈ 6.3 days).
- **Shape of effort (for 整体耗时 calibration):** substantive work clustered on **Apr 3** (build-out: initial → 813 → 1,461 → 1,474 tables, bug fixes, lineage) and **Apr 9–10** (lineage feedback from big-data team 云飞 + consistency fixes). The Apr 10 tail (3 of 13 commits) is just Vercel author-email fixes, not feature work — so real engineering time ≈ **2 active days across a 7-day window**.

### Full commit log
```
7de9833 2026-04-10  Fix commit author email to xzeng36@wisc.edu for Vercel deployment
99d7d3d 2026-04-10  Fix commit author email for Vercel deployment
1d6ad75 2026-04-10  Expand lineage search to all 86 tables with "no data" feedback
3e772f5 2026-04-10  Fix commit author email for Vercel deployment
f3f240b 2026-04-10  Fix bidirectional lineage consistency and stale risk chain references
7a31f26 2026-04-10  Fix data consistency issues found in full-feature audit
9b473c3 2026-04-09  Fix table lineage feature per big data team (云飞) feedback
d65cb08 2026-04-03  Update with verified VeloDb Doris + CyberData production data (1,474 tables)
b1660e4 2026-04-03  Replace mock data with REAL CyberData production metadata (1,461 tables)
89dd5fe 2026-04-03  Scale data to 813 tables, persist sidebar, donut labels beside chart
c8be4f2 2026-04-03  Fix 6 bugs found in thorough testing review
900079c 2026-04-03  Fix lineage graph rendering bugs + 7 UI improvements
a95c37d 2026-04-03  Initial commit: 国际化数仓运维看板 (International DW Ops Dashboard)
```

---

## 4. LIVE DORIS TABLE COUNT

- **Direct Doris (`idoris.luckincoffee.us:9030`):** resolves to `10.238.0.165` but **TCP 9030 is blocked** from this host and no `mysql` client is installed → direct route unreachable.
- **Via CyberData catalog (`luckyus_icyberdata.meta_table` — the actual source the snapshot was built from), gateway `aws-luckyus-icyberdata-rw`:**
  - **Live: 1,501 tables across 54 databases** (excluding `information_schema` / `mysql` / `sys` / `__internal_schema`).
  - **vs. baked snapshot 1,477 tables / 53 DBs (2026-04-28):** **+24 tables, +1 database** since the dashboard's data was frozen. (vs. the 1,474 overview card: +27.)

---

## ⚠️ Security note (not metadata — flagged for action)

The repo's `git remote` origin URL has a **GitHub Personal Access Token embedded in plaintext** (`ghp_…`). It is exposed to anyone with shell / `.git/config` access and will leak if the config is shared. **Recommend rotating the token** and switching the remote to SSH or a credential helper. Token value not reproduced here.
