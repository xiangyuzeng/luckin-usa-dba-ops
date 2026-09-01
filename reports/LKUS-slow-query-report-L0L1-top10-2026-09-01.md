# LKUS 慢查询 TOP10 报告 —— L0 + L1，剔除 DBA 自有

| 项目 | 内容 |
|------|------|
| 报告编号 | LCNA-DBA-SQL-2026-0901-E |
| 前序报告 | -0901（L0 TOP3）、-0901-B（L0 剩余 9 条）、-0901-C（按账号回溯）、-0901-D（效能看板） |
| 出具日期 | 2026-09-01 |
| 出具人 | 曾翔宇（DBA / Infrastructure） |
| 范围 | **L0 + L1 共 48 台实例**（等级表本次按六级标准定稿，见第一节） |
| 排除 | **账号 `diagtools` 的全部查询**（DBA 自有：看板采集容器 + mcp-db-gateway 临时查询） |
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

| # | 等级 | 实例 | 指纹 | DB时间 | 次数 | 均耗 | 执行账号 | 结论出处 |
|---|---|---|---|---:|---:|---:|---|---|
| 1 | L0 | opshopsale | `00259408` | **4,976.9s** | 768 | 6.48s | `iopshopsaleservice_A_o` | -0901 |
| 2 | L0 | salespayment | `fe67d6b5` | **3,780.6s** | 2,304 | 1.64s | `isalespmtadmin_A_o` | -0901 |
| 3 | L0 | salesmarketing | `9919be27` | 371.2s | 8 | 46.40s | `isalescouponservice_A_o` | -0901 |
| 4 | L0 | cdpactivity | `142b98a6` | 191.7s | 104 | 1.84s | `icdpactivityengine_A_o` | -0901-B |
| 5 | L0 | salesorder | `792aa5a0` | 93.9s | 80 | 1.17s | `isalesorderservice_A_o` | -0901-B |
| 6 | L0 | salesorder | `8d07ade5` | 84.3s | 14 | 6.02s | `isalesorderservice_A_o` | -0901-B |
| 7 | L0 | salesorder | `ba25fea5` | 80.2s | 16 | 5.01s | `isalesorderservice_A_o` | -0901-B |
| 8 | L0 | salesorder | `397899b0` | 55.7s | 13 | 4.29s | `isalesorderservice_A_o` | -0901-B（已停跑） |
| 9 | L1 | opempefficiency | `a0258469` | 36.4s | 14 | 2.60s | `iopempefficiency_A_o` | **本报告新增** |
| 10 | L1 | opempefficiency | `8d7d1910` | 31.2s | 14 | 2.23s | `iopempefficiency_A_w` | **本报告新增** |

**被剔除的 `diagtools` 条目**（按 DB 时间本会排在第 5、6、11 名）：
`e5a8e692` 179.8s、`09d7feb6` 142.1s（store-ops 看板 SPU 双扫描）、`e2b527f7` 44.6s（store-ops 效能）。
三条今天已改完并部署，见 -0901-B / -0901-C。

**分布**：TOP10 里 8 条在 L0、2 条在 L1；按实例集中在 4 台（salesorder ×4、opempefficiency ×2、
opshopsale / salespayment / salesmarketing / cdpactivity 各 1）。
第 1、2 名合计 8,757.5s，占本 TOP10 总量（9,702.1s）的 **90.3%** —— 加进 L1 并没有改变
「头部两条吃掉九成」的格局。

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
直接对同样 48 台实例的慢日志原文按语句聚合（同样剔除 `diagtools`，`long_query_time=0.1s`）：

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
| E-02 | 分级映射表按五级标准定稿，11 台移出业务档；重新生成后需重新套用 | P1 | DBA | **已改**（3 处待确认） |
| E-03 | 周度分诊补「扫描行数 / 累计 DB 时间」维度，覆盖均耗 <1s 的高频查询 | P2 | DBA | 待做（与 -0901-C 的 C-02 合并） |
| E-04 | 复核 `isalesmktadmin_A_o` 那条（7 天 34.5 亿行）—— 新口径下的真·第一名 | P1 | DBA + 张晓松 | 待做 |
| — | TOP10 第 1~8 名的处置见 -0901 / -0901-B，本次无变化 | — | — | — |

---

## 六、台账处置

本轮 L0+L1 分诊命中 24 条，`--append-new` 追加 12 条 `pending`，其中 2 条（本报告第三节）已改判
`analyzed` 并回填结论；台账现为 **24 条 = analyzed 12 / pending 10 / accepted 2**。

剩余 10 条 `pending` 均为 L1 新入册、单条 DB 时间 12~27 秒（scmsrm、upush、scm-wds、framework01、
ibillingcentersrv、ijumpserver、scm-shopstock 等），量级远低于 TOP10 头部，按周流程后续排期分析。
