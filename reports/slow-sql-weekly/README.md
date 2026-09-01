# 慢 SQL 周度分析 —— 台账与分诊

每周做慢查询分析时，先跑分诊脚本，它把本周榜单和台账做差集，只把**真正需要人看的**推出来。
已经分析过的指纹自动静默，不再重复分析。

```bash
cd /app/reports/slow-sql-weekly
python3 weekly_slow_sql_triage.py --show-sql          # L0，近 7 天
```

---

## 每周固定流程

| 步骤 | 命令 / 动作 |
|---|---|
| 1. 分诊 | `python3 weekly_slow_sql_triage.py --level L0,L1 --show-sql` |
| 2. 入册 | `python3 weekly_slow_sql_triage.py --level L0,L1 --append-new`（把 NEW 以 `pending` 追进台账，附本周基线）|
| 3. 分析 | 只分析 NEW / REGRESSED / RECURRED / DUE 四类；KNOWN 直接跳过 |
| 4. 回写 | 手工编辑 `analyzed-registry.csv`：`status` 改 `analyzed`，填 `verdict` / `report_id` / `action_ids` / `last_reviewed` |
| 5. 贴周报 | `python3 weekly_slow_sql_triage.py --emit-md /tmp/slowsql.md`，把生成的表格贴进周报 |
| 6. 提交 | 台账改动跟着周报一起 push 到 `dba-ops` |

退出码：出现 `RECURRED` 或 `REGRESSED` 时返回 **1**，其余返回 0 —— 可以直接挂 cron 做「有异常才告警」。

---

## 六类分诊结果

| 类别 | 含义 | 要做什么 |
|---|---|---|
| `RECURRED` | 台账标了 `fixed`，本周却又上榜 | **最高优先级** —— 修复没生效 |
| `REGRESSED` | 台账里有，但日均 DB 时间或平均耗时超过基线 ×1.5 | 复查；确认新水位合理就更新基线 |
| `NEW` | 台账里没有 | 本周要分析的对象 |
| `DUE` | `recheck_after` 到期 | 到期复查（如「改造后 30 天验证效果」）|
| `STALE` | `pending` 挂满 30 天还没结论 | 催办，或改判 `deferred` / `accepted` |
| `KNOWN` | 已在台账且指标稳定 | 静默。`--show-known` 才显示 |

阈值都可调：`--regress-factor`、`--stale-days`、`--min-dbtime`、`--days`。

---

## 台账 `analyzed-registry.csv`

主键 = `(instance, schema_name, digest_id)`，`digest_id = MD5(t_dba_collect_slow_query.query)`。

**status 只能是这五个**（脚本会校验，写错直接报错退出）：

| status | 含义 | 分诊行为 |
|---|---|---|
| `pending` | 已入册、尚未出结论 | 静默；满 `--stale-days` 天转 STALE |
| `analyzed` | 已出结论，改造未完成 | 静默；劣化时重新弹出 |
| `fixed` | 已修复 | 再上榜即 RECURRED |
| `accepted` | 已评估，接受现状不改造 | 永久静默，除非劣化 |
| `deferred` | 本期不处理 | 静默至 `recheck_after` |

`base_*` 四列是登记当时的基线，用于判断「是否变差了」。**复查后确认新水位合理，就手工更新基线并更新 `last_reviewed`**，否则它会每周都报 REGRESSED。

---

## 六个坑

1. **应用改了 SQL 文本 → digest 变 → 台账认不出，会当作 NEW 重新分析。** 这是期望行为（SQL 变了本来就该重看），但要知道「同一个业务查询」可能在台账里留下多条历史记录。

2. **采集表只收录 `avg_sec ≥ 1s` 的指纹**，所以本工具看到的永远是「单次很慢的 SQL」，不是慢查询总量。总量看 Prometheus `mysql_global_status_slow_queries`（阈值 0.1s，全 fleet 24h 约 16.8 万条）。周报里两个口径不能混写。

3. **采集表存的是累计量**，脚本内部已用 `LAG()` 按 `(instance, database_name, MD5(query))` 分区做日差分。直接对 `sum_sec` 排序会得到「终身榜」——早就不跑的 SQL 会霸榜。

4. **凭据来自 `/app/alert-mailserver/scripts/.env`（`diagtools` 账号），值是带引号的，必须 `strip('"')`**，否则报 `Access denied for user '"diagtools"'`。也可以用环境变量 `SLOWSQL_MYSQL_USER` / `SLOWSQL_MYSQL_PASSWORD` 覆盖。

5. **分级映射表 `/app/luckin-slow-sql-tier-map.csv` 由 `make_tier_map.py` 生成，重跑会覆盖手工修改。** 新实例上线后要么重跑生成器、要么手工补行，否则该实例的慢 SQL 在分诊里等级显示为 `?`。

---

6. **台账是 CSV，`verdict` 里不能有裸逗号。** 手工编辑时若在备注中打了英文逗号又没加引号，`DictReader` 会多切一列、后面所有列跟着错位。脚本已加校验，遇到会直接 `[FATAL]` 报错退出（不会静默错位）；修法是用 `csv` 模块重写该文件——含逗号的字段会自动加引号。中文顿号「、」和分号「；」都是安全的。

---

## 相关文件

| 路径 | 内容 |
|---|---|
| `analyzed-registry.csv` | 本目录 · 已分析台账（唯一真源，手工可编辑）|
| `weekly_slow_sql_triage.py` | 本目录 · 分诊脚本 |
| `/app/luckin-slow-sql-tier-map.csv` | L0–L4 分级映射（65 台）|
| `/app/luckin-slow-sql-topn-dashboard.json` | Grafana 看板 `lkus-slow-sql-topn`，18 panel |
| `LKUS-slow-query-report-L0-2026-09-01.md` | `/app/reports/` · TOP3 分析报告（LCNA-DBA-SQL-2026-0901）|
| `LKUS-slow-query-report-L0-pending9-2026-09-01.md` | `/app/reports/` · 剩余 9 条分析报告（LCNA-DBA-SQL-2026-0901-B）|
