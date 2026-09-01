# LKUS 慢查询 TOP10 报告 —— L0 + L1，剔除 DBA 自有

| 项目 | 内容 |
|------|------|
| 报告编号 | LCNA-DBA-SQL-2026-0901-E |
| 前序报告 | -0901（L0 TOP3）、-0901-B（L0 剩余 9 条）、-0901-C（按账号回溯）、-0901-D（效能看板） |
| 出具日期 | 2026-09-01 |
| 出具人 | 曾翔宇（DBA / Infrastructure） |
| 范围 | **L0 + L1 共 48 台实例**（等级表本次按六级标准定稿，见第一节） |
| 排除 | ① 账号 `diagtools` 的全部查询（DBA 自有）；② **不存在优化动作的条目**（已停跑、计划已最优、纯行锁等待、单次只扫几十行等），排除理由逐条列出 |
| 入选判据 | **单次扫描行数** + **扫描/返回比** —— 榜单服务于优化，产不出动作的不占名额 |
| 数据窗口 | 2026-08-25 ~ 2026-09-01（7 天日差分） |
| 数据来源 | `ldas01` 采集表（≥1s 指纹）+ CloudWatch 慢日志原文按 `User@Host` 归属 + 现场 `EXPLAIN` / `performance_schema` 计时 |

---

## 一、分级标准（David 2026-09-01 定稿，五级）

| 等级 | 名称 | 定义 |
|---|---|---|
| **L0** | 核心业务功能 | — |
| **L1** | 重要业务功能 | — |
| **L2** | 次要业务功能 | — |
| **L3** | **安全运维** | 系统周边运维、保障系统安全运行；出问题则业务系统处于不安全状态 |
| **L4** | **数据分析** | 围绕业务系统提供支持活动，对时效性要求不高 |

**套用规则**：L0/L1/L2 一律沿用「MySQL 8.4.9 升级跟踪表」的服务等级列（业务重要性口径，
一台挂多个服务取最高），本表不对业务库的重要性做二次判断；只把**本身不是业务功能**的实例
移出业务档，改按角色归 L3 / L4。据此移出 11 台：

| 新档 | 台数 | 实例（括号内为跟踪表原档） |
|---|---:|---|
| **L3 安全运维** | 4 | `devops`（L1，iZeus 告警）、`ijumpserver`（L1，堡垒机）、`iluckyhealth`（L2，巡检）、`ilsopdevopsdata`（L2，LSOP 运维数据） |
| **L4 数据分析** | 7 | `icyberdata`（L3）、`iluckydorisops`（L3）、`ldas`（L1，CMDB）、`ldas01`（L1，DBA 数据平台）、`pubdm`（L1，公共数据集市）、`ldasverify01/02`（L3，DBA 验证实例） |

`scm-wmssimulate` 保持跟踪表原档 **L2**，不移出业务档。

分布：**L0 × 15、L1 × 33、L2 × 6、L3 × 4、L4 × 7**（共 65 台）。

> ⚠️ **3 处待确认**：`iriskcontrolservice` 保持 L0（风控属信息安全，也可论证为 L3 安全运维；
> 按「跟踪表说它是核心业务就不擅自降档」保守保留）、`isalesdatamarketing` 保持 L1（名字像分析、
> 分组属营销增长，未确认）、`pubdm` L1→L4（若视作业务链路应退回 L1）。
>
> ⚠️ **标准本身有一处空缺**：登录 / 权限 / 日志这类「基础组件」没有独立档位，
> 按规则沿用跟踪表 —— `ipermission`=L0、`iluckyauthapi`=L1、`oplog`=L2。若认为它们的故障
> 影响面应高于跟踪表给的档位，需要另行指定。
>
> 🔴 **重跑任何从升级跟踪表生成映射的脚本，只会还原 L0/L1/L2，上面 11 台的归类会丢失**，
> 必须按 `/app/luckin-slow-sql-tier-map.csv` 各行 note 重新套用。

### 这一步对本报告的影响

`ldas01`（DBA 自有数据平台）归 L4 数据分析后出榜 —— 否则它三条（151.3s / 100.8s / 61.7s，
账号 `idbtask_w`）会占据第 5、6、10 名。**那也是我们自己的东西，只是换了个账号名，
「剔除 diagtools」这条过滤拦不住它** —— 按账号过滤不够，还得按归属看。
`devops` 归 L3 安全运维同理出榜。

---

## 二、TOP10（采集表口径：单次 ≥1s 指纹，7 天新增 DB 时间）

> **入选判据**：榜单的目的是产出优化动作，因此**不存在优化动作的条目直接排除**，
> 不占用 TOP10 名额。筛选依据是两个可量化信号 —— **单次扫描行数** 与 **扫描/返回比**：
> 单次扫描量大、或扫很多却返回很少 = 有优化空间；单次只扫几十行、或扫描量约等于返回量
> = 已经很优化了，慢在别处（争用、锁、频次），列出来不产生动作。

| # | 等级 | 实例 | 指纹 | DB时间 | 次数 | 单次扫描行 | 优化动作 | 出处 |
|---|---|---|---|---:|---:|---:|---|---|
| 1 | L0 | opshopsale | `00259408` | **4,976.9s** | 768 | 766,796 | 巡检去重 + 降频（每 30min→每天，-99%） | -0901 |
| 2 | L0 | salespayment | `fe67d6b5` | **3,780.6s** | 2,304 | 164,324 | 先修费用预估回写逻辑，再加索引 | -0901 |
| 3 | L0 | salesmarketing | `9919be27` | 371.2s | 8 | 3,041,567 | 加 `(tenant, coupon_source, id)` | -0901 |
| 4 | L0 | cdpactivity | `142b98a6` | 191.7s | 104 | 12,337 | **错峰**（SQL 实测 27ms，无 SQL 优化空间）+ 预防性索引 B-01 | -0901-B |
| 5 | L0 | salesorder | `792aa5a0` | 93.9s | 80 | 20,597 | 加 `(tenant, checking_status, deleted, checking_date)` B-06 | -0901-B |
| 6 | L0 | salesorder | `8d07ade5` | 84.3s | 14 | 1,265,167 | 加 `(tenant, status, deleted, checking_date)` B-08 | -0901-B |
| 7 | L0 | salesorder | `ba25fea5` | 80.2s | 16 | 1,264,122 | 同 B-08 一个索引解决两条 | -0901-B |
| 8 | L1 | opempefficiency | `a0258469` | 36.4s | 14 | 2,185 | **错峰**（非整点实测 332ms vs 记录 2,572ms） | 本报告 |
| 9 | L1 | opempefficiency | `8d7d1910` | 31.2s | 14 | 2,603 | **错峰**（2,515 行 / 4.5MB 的表扫 2.83 秒） | 本报告 |
| 10 | L1 | ibillingcentersrv | `efba7db1` | 12.4s | 4 | **228,777** | 待分析 —— 单次扫 22.9 万行，扫描量在 L1 尾部最高 | 待排期 |

**分布**：8 条在 L0、2 条在 L1，集中在 5 台实例。第 1、2 名合计 8,757.5s，
占本 TOP10 总量（9,701.9s）的 **90.3%** —— 优化收益也集中在这两条。

### 本轮排除的条目（不是漏掉，是没有优化动作）

| 指纹 | 实例 | DB时间 | 排除理由 |
|---|---|---:|---|
| `397899b0` | salesorder | 55.7s | **已停跑** —— `LAST_SEEN 2026-08-28`，功能疑似下线，无需优化 |
| `18f0b86c` | salespayment | 27.6s | **执行计划已最优** —— range 走 `idx_create_time`，无 filesort 无临时表；-0901-B 明确「不建议加索引」 |
| `53e2bc9c` | scmsrm | 27.4s | **`INSERT`，扫描 0 行** —— 没有可优化的读路径，慢在写入/提交 |
| `04bc9a2d` | upush | 21.6s | **已最优** —— 该库慢日志前四是 `select * from t_mdm_tenant`（扫 10 行返回 1 行）、`commit;`（953 次 304 秒）、`INSERT`；一条可优化的都没有，慢在提交延迟 |
| `151b0ae8` | ijumpserver | 18.9s | 分级调整后归 **L3 安全运维**，出范围 |

被剔除的 `diagtools` 三条（`e5a8e692` 179.8s、`09d7feb6` 142.1s、`e2b527f7` 44.6s，
store-ops 看板取数）按 DB 时间本会排在第 5、6、11 名，**今天已改完并部署**，见 -0901-B / -0901-C。

---

## 三、新增分析：opempefficiency 两条（第 9、10 名）

两条都在 `aws-luckyus-opempefficiency-rw`（L1，国际运营 / 陈培浩·游熖），
每天各执行 2 次。**结论：两条都是争用受害者，不是慢 SQL —— 不要去优化语句本身。**

### 3.1 `a0258469` · 培训工时校验（SELECT）

慢日志原文（`2026-09-01T15:00:02.739112Z`，`iopempefficiency_A_o` @ `10.238.32.7`）：

```sql
# Query_time: 2.659437  Rows_sent: 0  Rows_examined: 550
SELECT ttt.emp_no
  FROM t_training_time ttt
  JOIN t_training_time_detail tttd
    ON ttt.emp_no = tttd.emp_no AND tttd.tenant = 'IQA2'
  JOIN (SELECT emp_no, MAX(scheduling_date) AS latest_scheduling_date
          FROM t_training_time_detail WHERE tenant = 'IQA2' GROUP BY emp_no) latest
    ON tttd.emp_no = latest.emp_no
   AND tttd.scheduling_date = latest.latest_scheduling_date
   AND tttd.scheduling_date > '2024-07-30'
 WHERE ttt.trained_hours != (ttt.init_train_hours - tttd.rest_train_hours)
   AND ttt.multiple_join IS NULL AND ttt.tenant = 'IQA2';
```

**扫 550 行、返回 0 行、耗时 2.66 秒。** 550 行不可能要 2.66 秒。

`performance_schema` 差分实测（2026-09-01 20:20 UTC，非整点）：

| 口径 | 耗时 | 扫描行 |
|---|---:|---:|
| 应用记录（`COUNT_STAR=16` 累计均值） | **2,572.4 ms** | 34,986（均 2,187） |
| 我现场跑同一语句 | **332.2 ms** | 557 |

**差 7.7 倍。** 该任务固定在整点 `:00` 触发（观察到 05:00:03 / 09:00:03 / 15:00:02），
与全 fleet 整点批量窗口重合。

`EXPLAIN`：`ttt` 走全表扫（`possible_keys=uniq_emp`，`key=NULL`，512 行），
派生表 `latest` 物化后带 `<auto_key0>`，`tttd` 走 `uniq_emp_date`。
两张表分别只有 **512 行 / 3,442 行**，绝对代价很小。

**判断**：332 ms 里确实有可优化的部分（派生表每次重算 `MAX(scheduling_date)`、`ttt` 全表扫），
但表这么小，改写或加索引最多省掉几百毫秒；**2.57 秒里的大头是执行时刻**。

### 3.2 `8d7d1910` · 考勤异动状态推进（UPDATE）

慢日志原文（`2026-09-01T05:00:03.294912Z`，`iopempefficiency_A_w` @ `10.238.33.77`）：

```sql
# Query_time: 2.829529  Rows_sent: 0  Rows_examined: 2630
UPDATE t_attendance_change SET status = 4, modify_time = now(), modifier_name = 'system'
 WHERE status = 1 AND attendance_date < '2026-08-30'
   AND sub_type IN (101,102,201,202,203,204)
   AND ((sub_type IN (101,102) AND clock_dept_id IN (…33 个门店 id…))
     OR (sub_type NOT IN (101,102) AND source_scheduling_dept_id IN (…33 个门店 id…)))
   AND tenant = 'LKUS';
```

`t_attendance_change` **全表只有 2,515 行 / 4.5 MB**，索引 `PRIMARY` / `idx_attendance_date` /
`idx_emp_no`。这条扫了 2,630 行 ≈ 整张表 —— **4.5 MB 的全表扫本该是毫秒级，实测 2.83 秒**。
执行时刻 `05:00:03`，正在夜间批量窗口内（该时段全 fleet 资源争用最重）。

> 网关按只读规则拒绝了 `EXPLAIN UPDATE`（符合预期），本条结论据慢日志原文 + 表规模 + 索引清单判断。

**判断**：与 3.1 同类。加索引没有意义（表只有 4.5 MB），**修法是错峰**。

---

## 四、🔴 口径警告：换成慢日志原文口径，第一名完全不同

采集表 `t_dba_collect_slow_query` **只收 `avg_sec ≥ 1s` 的指纹**，高频低耗型查询整体不在其中。
对同一批 L0+L1 实例（48 台中 46 台有慢日志组）按慢日志原文聚合，同样剔除 `diagtools`，
并套用与第二节相同的「有无优化价值」判据：

| # | 实例 | 7天次数 | DB时间 | 单次扫描 | 单次返回 | 扫描/返回 | 优化价值 |
|---|---|---:|---:|---:|---:|---:|---|
| 1 | salesmarketing | 66,990 | **23,060.7s** | 51,467 | **0.14** | **37 万:1** | ✅✅ 每 9 秒一次、每次扫 5 万行几乎不返回 |
| 2 | opshopsale | 752 | 4,865.9s | 762,100 | 0 | ∞ | ✅ 已有结论（-0901 第 1 名） |
| 3 | salespayment | 2,256 | 3,671.4s | 162,349 | 5,000 | 32:1 | ✅ 已有结论（-0901 第 2 名，每次捞满 5000） |
| 4 | isalesprivatedomain | 11,922 | 3,499.5s | 4,933 | **0** | ∞ | ✅ 扫 4,933 行**一行不返回**，与 opshopsale 同型 |
| 5 | salesmarketing | 11,484 | 1,929.8s | **290,421** | 1 | **29 万:1** | ✅✅ `count(1) from t_market_activity_partake`，扫 29 万行只为一个数 |
| 6 | salesorder | 5,599 | 1,957.7s | 779 | 0.44 | 1,780:1 | ✅ 选择率极低 |
| 7 | salespayment | 8,726 | 2,325.8s | 6,630 | 9.5 | 700:1 | ✅ 但归属是**监控看板**（`dbms_dbsearch`，Grafana 取数），修法是降频/改写面板 |
| 8 | ipermission | 11,280 | 2,716.8s | 67,727 | **33,974** | 2:1 | 🟡 不是扫描浪费，是**一次取回 3.4 万行**；方向是应用侧缓存/减少调用，不是加索引 |
| 9 | ipermission | 5,048 | 1,989.0s | 8,203 | 6,280 | 1.3:1 | 🟡 同上 |
| 10 | salesmarketing | 8,197 | 2,534.7s | 1,794 | 965 | 1.9:1 | 🟡 选择率合理、扫描量小，优化空间有限 |

**排除（无优化价值）**：

| 实例 | 语句 | DB时间 | 排除理由 |
|---|---|---:|---|
| cdpactivity | `SELECT COUNT(*) FROM t_contact_activity WHERE deleted != 1 …` | 2,444.7s | **单次只扫 52 行**、返回 1 行，0.21 秒 —— 已经很优化了，慢在频次与争用，加索引改写都无意义 |
| framework01 | `SELECT * FROM es_qrtz_LOCKS … FOR UPDATE` | 2,440.4s | **扫描 1 行、返回 1 行** —— Quartz 调度器抢锁，纯行锁等待，SQL 层没有任何可优化处 |

**两点结论**：

1. **原文口径的第一名（23,061 秒 / 34.5 亿行）完全不在采集表榜单上**，只因为均耗 0.34 秒。
   它和第 5 名同属 `salesmarketing`，两条合计 **每周扫 68 亿行** —— 是当前 L0+L1 里最大的优化机会，
   比采集表榜首 `opshopsale` 大 4.6 倍。已记为 E-04。
2. **`dbms_dbsearch` 大概率也是我们自己的**（`_timestamp` / `_value` 是 Grafana MySQL 数据源约定），
   与 `ldas01` 的 `idbtask_w` 同类：**「剔除 `diagtools`」只挡住一个账号**。已记为 E-05。

---

## 五、行动项

| 编号 | 事项 | 优先级 | 归属 | 状态 |
|---|---|---|---|---|
| E-01 | opempefficiency 两个定时任务从整点 `:00` / `05:00` 错峰 | P2 | 国际运营（陈培浩/游熖） | 待沟通 |
| E-02 | 分级映射表按五级标准定稿，11 台移出业务档；重新生成后需重新套用 | P1 | DBA | **已改**（3 处待确认） |
| E-03 | 周度分诊补「扫描行数 / 累计 DB 时间」维度，覆盖均耗 <1s 的高频查询 | P2 | DBA | 待做（与 -0901-C 的 C-02 合并） |
| E-05 | 过滤 DBA 自有查询改为按「归属」而非账号名（`diagtools` 之外还有 `idbtask_w`、`dbms_dbsearch`） | P2 | DBA | 待做 |
| E-04 | 复核 salesmarketing 两条（`isalesmktadmin_A_o` 66,990 次/34.5 亿行/23,061s；`count(1) from t_market_activity_partake` 11,484 次/单次扫 29 万行）—— 合计每周 68 亿行，当前最大优化机会 | P1 | DBA + 张晓松 | 待做 |
| E-06 | `isalesprivatedomain` 那条：单次扫 4,933 行**返回 0 行**，与 opshopsale 空转型同构 | P2 | DBA + 张翔 | 待做 |
| E-07 | `ipermission` 两条不是扫描浪费而是单次取回 3.4 万行；方向是应用侧缓存/减少调用频次 | P2 | 陈亮/张晓松 | 待沟通 |
| — | TOP10 第 1~8 名的处置见 -0901 / -0901-B，本次无变化 | — | — | — |

---

## 六、台账处置

本轮 L0+L1 分诊命中 24 条，`--append-new` 追加 12 条 `pending`，其中 2 条（本报告第三节）已改判
`analyzed` 并回填结论；台账现为 **24 条 = analyzed 12 / pending 10 / accepted 2**。

剩余 10 条 `pending` 均为 L1 新入册、单条 DB 时间 12~27 秒（scmsrm、upush、scm-wds、framework01、
ibillingcentersrv、ijumpserver、scm-shopstock 等），量级远低于 TOP10 头部，按周流程后续排期分析。
