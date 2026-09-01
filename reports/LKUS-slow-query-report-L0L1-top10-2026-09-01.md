# LKUS 慢查询 TOP10 报告 —— L0 + L1，剔除 DBA 自有

| 项目 | 内容 |
|------|------|
| 报告编号 | LCNA-DBA-SQL-2026-0901-E |
| 前序报告 | -0901（L0 TOP3）、-0901-B（L0 剩余 9 条）、-0901-C（按账号回溯）、-0901-D（效能看板） |
| 出具日期 | 2026-09-01 |
| 出具人 | 曾翔宇（DBA / Infrastructure） |
| 范围 | **L0 + L1 共 51 台实例**（等级表本次按新判据整体重排，见第一节） |
| 排除 | **账号 `diagtools` 的全部查询**（DBA 自有：看板采集容器 + mcp-db-gateway 临时查询） |
| 数据窗口 | 2026-08-25 ~ 2026-09-01（7 天日差分） |
| 数据来源 | `ldas01` 采集表（≥1s 指纹）+ CloudWatch 慢日志原文按 `User@Host` 归属 + 现场 `EXPLAIN` / `performance_schema` 计时 |

---

## 一、先更正分级：整张表按组件角色重排

David 2026-09-01 给出的分级判据，与此前映射表的依据**不是一回事**。此前等级取自
「MySQL 8.4.9 升级跟踪表」的服务等级列，那是**业务重要性**口径；新判据是**组件角色**：

| 等级 | 定义 |
|---|---|
| **L0 基础组件** | 一旦出问题会影响**大部分业务系统**。例：登录、权限、日志 |
| **L1 业务功能** | 一旦出问题会影响**某个业务功能** |
| **L2 辅助系统** | 系统周边运维、保障系统安全运行；出问题则业务系统处于**不安全状态** |
| **L3 统计分析系统** | 围绕业务系统提供支持活动，对**时效性要求不高** |
| **L4 其他测试系统** | — |

据此整表重排，**65 台中 32 台等级变化**：

| 方向 | 台数 | 实例 |
|---|---:|---|
| → **L0** | 8 台变更 | `iluckyauthapi`（登录）、`ipermission`（权限）、`oplog`（日志）、`ibizconfigcenter`（配置中心）、`framework01` / `framework02` / `horae`（Chronus 调度）、`upush`（统一推送）、`iworkflowmidlayer`（工作流中间层）；`ipermission` 原本就是 L0，未变 |
| L0 → **L1** | 13 | `salesorder`、`salespayment`、`salesmarketing`、`salescrm`、`cdpactivity`、`isalescdp`、`isalesprivatedomain`、`opshop`、`opshopsale`、`opproduction`、`scm-shopstock`、`scmcommodity`、`fitax` |
| L2 → **L1** | 4 | `fichargecontrol`、`ifiaccounting`、`iopocp`、`opqualitycontrol` |
| → **L2** | 2 | `ijumpserver`（堡垒机）、`iriskcontrolservice`（风控） |
| → **L3** | 2 | `pubdm`、`isalesdatamarketing`（另有 `icyberdata`、`iluckydorisops`、`ldas`、`ldas01` 本就在 L3） |
| → **L4** | 3 | `ldasverify01/02`、`scm-wmssimulate` |

新分布：**L0 × 9、L1 × 42、L2 × 5、L3 × 6、L4 × 3**。

> ⚠️ **6 处判断待 David 确认**：`iriskcontrolservice`→L2（风控算辅助还是业务功能）、
> `upush`→L0、`iworkflowmidlayer`→L0（是否算基础组件）、`framework02`→L0（库内容未核实，
> 按与 framework01 同族推断）、`pubdm`→L3、`isalesdatamarketing`→L3。
> 判据原文与这 6 处都写在 `/app/luckin-slow-sql-tier-map.csv` 表头。
> **任何从升级跟踪表重新生成映射的脚本都会覆盖本表**，必须按新判据重新套用。

### 重排后最重要的一个事实

**按新判据，基础组件层几乎没有慢 SQL 问题。** 新 L0 的 9 台实例 7 天只有 5 条 ≥5s 的指纹、
合计 **64.6 秒**；本报告 TOP10 里那些几千秒级的大头，**全部落在 L1 业务功能层**。
换句话说：慢查询集中在业务功能，不在公共基础设施 —— 这与重排前「TOP10 里 8 条在 L0」的
印象完全相反，只是因为口径换了。

> 顺带保留上一轮的结论：`ldas01` / `ldas`（DBA 自有数据平台）归 L3、`devops`（iZeus 告警库）
> 归 L2 —— 新判据下依然成立。这一步让它们出榜；否则 `ldas01` 三条（151.3s / 100.8s / 61.7s，
> 账号 `idbtask_w`）会占据第 5、6、10 名。**那也是我们自己的东西，只是换了个账号名，
> 「剔除 diagtools」这条过滤拦不住它** —— 按账号过滤不够，还得按归属看。

---

## 二、TOP10（采集表口径：单次 ≥1s 指纹，7 天新增 DB 时间）

| # | 等级 | 实例 | 指纹 | DB时间 | 次数 | 均耗 | 执行账号 | 结论出处 |
|---|---|---|---|---:|---:|---:|---|---|
| 1 | L1 | opshopsale | `00259408` | **4,976.9s** | 768 | 6.48s | `iopshopsaleservice_A_o` | -0901 |
| 2 | L1 | salespayment | `fe67d6b5` | **3,780.6s** | 2,304 | 1.64s | `isalespmtadmin_A_o` | -0901 |
| 3 | L1 | salesmarketing | `9919be27` | 371.2s | 8 | 46.40s | `isalescouponservice_A_o` | -0901 |
| 4 | L1 | cdpactivity | `142b98a6` | 191.7s | 104 | 1.84s | `icdpactivityengine_A_o` | -0901-B |
| 5 | L1 | salesorder | `792aa5a0` | 93.9s | 80 | 1.17s | `isalesorderservice_A_o` | -0901-B |
| 6 | L1 | salesorder | `8d07ade5` | 84.3s | 14 | 6.02s | `isalesorderservice_A_o` | -0901-B |
| 7 | L1 | salesorder | `ba25fea5` | 80.2s | 16 | 5.01s | `isalesorderservice_A_o` | -0901-B |
| 8 | L1 | salesorder | `397899b0` | 55.7s | 13 | 4.29s | `isalesorderservice_A_o` | -0901-B（已停跑） |
| 9 | L1 | opempefficiency | `a0258469` | 36.4s | 14 | 2.60s | `iopempefficiency_A_o` | **本报告新增** |
| 10 | L1 | opempefficiency | `8d7d1910` | 31.2s | 14 | 2.23s | `iopempefficiency_A_w` | **本报告新增** |

**被剔除的 `diagtools` 条目**（按 DB 时间本会排在第 5、6、11 名）：
`e5a8e692` 179.8s、`09d7feb6` 142.1s（store-ops 看板 SPU 双扫描）、`e2b527f7` 44.6s（store-ops 效能）。
三条今天已改完并部署，见 -0901-B / -0901-C。

**分布**：按新判据 **TOP10 全部 10 条都在 L1 业务功能层，L0 基础组件层一条都没有**；按实例集中在 4 台（salesorder ×4、opempefficiency ×2、
opshopsale / salespayment / salesmarketing / cdpactivity 各 1）。
第 1、2 名合计 8,757.5s，占本 TOP10 总量（9,702.1s）的 **90.3%**——「头部两条吃掉九成」的格局，
在换判据前后都成立。

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

## 四、🔴 口径警告：这个 TOP10 依赖 ≥1s 门槛，换个口径完全是另一张榜

采集表 `t_dba_collect_slow_query` **只收 `avg_sec ≥ 1s` 的指纹**。
直接对同样 51 台实例的慢日志原文按语句聚合（同样剔除 `diagtools`，`long_query_time=0.1s`）：

| # | 实例 | 账号 | 7天次数 | DB时间 | 均耗 | 扫描行数 | 在采集表榜单上？ |
|---|---|---|---:|---:|---:|---:|---|
| 1 | salesmarketing | `isalesmktadmin_A_o` | 66,990 | **23,060.7s** | 0.34s | **3,447,785,825** | ❌ 均耗 <1s |
| 2 | opshopsale | `iopshopsaleservice_A_o` | 752 | 4,865.9s | 6.47s | 573,099,416 | ✅ 第 1 名 |
| 3 | salespayment | `isalespmtadmin_A_o` | 2,256 | 3,671.4s | 1.63s | 366,259,114 | ✅ 第 2 名 |
| 4 | isalesprivatedomain | `privatedomainserv_A_o` | 11,918 | 3,499.3s | 0.29s | 58,795,601 | ❌ 均耗 <1s |
| 5 | ipermission | `iopenauth_A_o` | 11,280 | 2,716.8s | 0.24s | 763,957,415 | ❌ 均耗 <1s |
| 6 | salesmarketing | `isalescouponservice_A_o` | 8,197 | 2,534.7s | 0.31s | 14,701,778 | ❌ 均耗 <1s |
| 7 | framework01 | `kbx_w` | 10,090 | 2,440.4s | 0.24s | 10,090 | ❌ 均耗 <1s |
| 8 | iopenlinker | `iopenlinker_A_o` | 7,087 | 1,887.2s | 0.27s | 25,137 | ❌ 均耗 <1s |

**第 1 名 7 天扫了 34.5 亿行、烧掉 23,061 秒 DB 时间 —— 是采集表榜单第 1 名的 4.6 倍，
却因为平均 0.34 秒而完全不在榜上。** 它每次执行平均扫 51,467 行返回不多，
执行 66,990 次（约每 9 秒一次）。

第 7 名 `kbx_w` 的 `SELECT * FROM es_qrtz_LOCKS WHERE SCHED_NAME='KBXScheduler' AND LOCK_NAME='TRIGGER_ACCESS' FOR UPDATE`
扫描行数等于执行次数（10,090 行 / 10,090 次，每次 1 行）—— **典型的行锁等待**，
Quartz 调度器抢锁，与 SQL 效率无关。

**结论**：「单次耗时」和「累计影响」是两把不同的尺子。现有台账只有前者，
高频低耗型查询（`isalesmktadmin_A_o` 这类）在治理视野之外。已记为行动项 E-03。

---

## 五、行动项

| 编号 | 事项 | 优先级 | 归属 | 状态 |
|---|---|---|---|---|
| E-01 | opempefficiency 两个定时任务从整点 `:00` / `05:00` 错峰 | P2 | 国际运营（陈培浩/游熖） | 待沟通 |
| E-02 | 分级映射表三台降级（ldas01/ldas→L3、devops→L2）；重新生成后需重新套用 | P1 | DBA | **已改** |
| E-03 | 周度分诊补「扫描行数 / 累计 DB 时间」维度，覆盖均耗 <1s 的高频查询 | P2 | DBA | 待做（与 -0901-C 的 C-02 合并） |
| E-04 | 复核 `isalesmktadmin_A_o` 那条（7 天 34.5 亿行）—— 新口径下的真·第一名 | P1 | DBA + 张晓松 | 待做 |
| — | TOP10 第 1~8 名的处置见 -0901 / -0901-B，本次无变化 | — | — | — |

---

## 六、台账处置

本轮 L0+L1 分诊命中 24 条，`--append-new` 追加 12 条 `pending`，其中 2 条（本报告第三节）已改判
`analyzed` 并回填结论；台账现为 **24 条 = analyzed 12 / pending 10 / accepted 2**。

剩余 10 条 `pending` 均为 L1 新入册、单条 DB 时间 12~27 秒（scmsrm、upush、scm-wds、framework01、
ibillingcentersrv、ijumpserver、scm-shopstock 等），量级远低于 TOP10 头部，按周流程后续排期分析。
