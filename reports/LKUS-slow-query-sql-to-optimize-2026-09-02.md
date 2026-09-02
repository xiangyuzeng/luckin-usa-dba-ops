# LKUS 需要优化的慢 SQL —— 10 条

| | |
|---|---|
| 报告编号 | LCNA-DBA-SQL-2026-0902 |
| 来源 | LCNA-DBA-SQL-2026-0901-E《慢查询 TOP10 报告》两张榜单合并去重 |
| 数据窗口 | 2026-08-25 ~ 2026-09-01（7 天） |
| 范围 | L0 + L1 共 48 台实例 |
| EXPLAIN 复核 | 2026-09-02 |
| 入选判据 | ① 执行计划确有缺陷（缺索引／扫描量远大于返回量／取回量本身过大）；② 实测确认该缺陷就是耗时来源。**两条都满足才占名额。** |

两张榜单去重后原始 18 条，经 `EXPLAIN` 与现场实测复核后 **剔除 5 条、合并 3 条 → 10 条**，
剔除与合并的明细列在文末，不是漏掉。

---

## 清单

| # | 实例 | 表 | 7天DB时间 | 单次扫描 | 单次返回 | 优化动作 | 状态 |
|---|---|---|---:|---:|---:|---|---|
| 1 | salesmarketing | t_cyber_ug_data_fetch_task | 23,060.7s | 51,467 | 0.14 | 加复合索引 | EXPLAIN 已验证 |
| 2 | opshopsale | t_shopsale_spu + t_shopsale_rmk | 4,976.9s | 766,796 | 0 | 任务去重＋降频 -99% | 已定论 |
| 3 | ipermission | t_permission_role_menu_relation<br>t_permission_menu | 4,705.8s | 67,727<br>8,203 | 33,974<br>6,280 | 应用侧缓存 | 待沟通 |
| 4 | salespayment | t_channel_fee | 3,780.6s | 164,324 | 5,000 | 先修回写逻辑，再加索引 | 已定论 |
| 5 | isalesprivatedomain | t_private_domain_user | 3,499.5s | 4,933 | 0 | 加复合索引 | EXPLAIN 已验证 |
| 6 | salesmarketing | t_coupon_template | 2,534.7s | 1,794 | 965 | 应用侧缓存 | 待沟通 |
| 7 | salespayment | t_trade + t_pay_channel | 2,325.8s | 6,630 | 9.5 | 降频／改写面板 | DBA 自有 |
| 8 | salesmarketing | t_market_activity_partake | 1,929.8s | 290,421 | 1 | 计数缓存（**加索引作废**） | EXPLAIN 已验证 |
| 9 | salesmarketing | t_coupon_record_expired | 371.2s | 3,041,567 | 1 | 加复合索引 | 已定论 |
| 10 | salesorder | t_finance_refund<br>t_finance_receipt ×2 | 258.4s | 20,597<br>126 万 | 1<br>31 / 1 | 两个索引，一份 CR | CR 已出 |

第 1 条占 10 条总量（47,443.4s）的 **48.6%**，前三条占 **69.0%**。

---

## 1 · salesmarketing —— 人群数据拉取任务扫描

`aws-luckyus-salesmarketing-rw` / `luckyus_sales_marketing` · 账号 `isalesmktadmin_A_o` · 约每 9 秒一次

```sql
select
    id, group_no, group_name, group_type, group_member_num, trigger_group_no, trigger_trace, trigger_by,
    create_time, modify_time, task_status, wait_time, process_time, deleted, calc_status, tenant, node_id
  from t_cyber_ug_data_fetch_task
 where tenant = 'IQA2'
   and create_time >= '2026-09-01 10:00:00'
   and task_status = 0
   and deleted = 0
 order by id asc
 limit 20;
```

**现状**：7 天 66,990 次，累计 23,060.7 秒、扫描 34.5 亿行，单次扫 51,467 行只返回 0.14 行（37 万:1）。
当前 L0+L1 范围内最大的单条优化机会。

**EXPLAIN（2026-09-02）**：`type=index`、`possible_keys=NULL`、`key=PRIMARY`、`rows=20`、`filtered=0.25`。
表上只有 `PRIMARY` 和 `idx_group_no`，四个过滤列一个都没索引 —— 优化器无索引可用，
被 `ORDER BY id ASC LIMIT 20` 骗去按主键顺序扫，指望"扫几行就凑够 20 条"，实际把整张
53,321 行的表走完。与第 9 条券归档探针是同一个 `ORDER BY 主键 + LIMIT` 陷阱。

**选择率实测**：`task_status=0 AND deleted=0` 全表只有 **1 行**；`tenant='IQA2'` 一行都没有
（IQA2 历史累计仅 99 行，且全是 `task_status=3`）。即这个轮询**永远扫全表、永远查无结果**。

**实测耗时**：2026-09-02 16:00 UTC（业务高峰）现场跑同一语句 **55.6 ms**，记录均值 344 ms（6.2 倍差）。
慢日志阈值 `long_query_time=0.1s`，所以 66,990 次只是超过 100ms 的尾部，真实执行次数更高。

**动作（已验证）**：建复合索引 `(tenant, task_status, deleted, create_time)`，
等值三列定位后 `create_time` 有序收敛，扫描 51,467 行 → 个位数行。
`(tenant, task_status, deleted, id)` 亦可，还能顺带消掉 `ORDER BY id` 的 filesort；
命中行数 ≤1，两者差别不大。**加索引后须复跑 `EXPLAIN` 确认优化器不再走 `PRIMARY`** ——
这张表已经栽在 LIMIT 陷阱上一次。

> 🔴 **顺带发现**：`task_status=0` 的那 1 行是 `id=18552` / `group_no=LKUSUG119455478458818560`，
> `create_time = modify_time = 2026-05-29 03:58:07`，**卡了 3 个月没动过**。
> 而轮询条件带 `create_time >= <最近若干小时>`，这行永远不会被捞起来。需要研发确认是否漏处理。

---

## 2 · opshopsale —— 门店售卖备注一致性巡检

`aws-luckyus-opshopsale-rw` / `luckyus_opshopsale` · 账号 `iopshopsaleservice_A_o` · 每 30 分钟一次

```sql
SELECT t1.dept_id AS '门店Id',
       t1.spu_code AS '商品'
  FROM t_shopsale_spu t1
  LEFT JOIN t_shopsale_rmk t2
         ON t1.dept_id   = t2.dept_id
        AND t1.spu_code  = t2.spu_code
        AND t2.sale_status = 1
        AND t2.rmk_status  = 1
 WHERE FIND_IN_SET(t2.rmk_mid, t1.sale_rmks) = 0
   AND t1.sale_status = 1
 GROUP BY t1.dept_id, t1.spu_code
 LIMIT 10;
```

**现状**：单次扫 766,796 行、恒返回 0 行；两个 Pod 无分布式锁重复执行；`FIND_IN_SET` 不可索引。

**动作**：① 定时任务去重（分布式锁或 Chronus 单点调度）；② 巡检频率每 30 分钟改为每天一次（-99%）；
③ 确认 `LEFT JOIN` 语义是否应为 `WHERE t2.id IS NULL`；④ 可选覆盖索引
`idx_rmk_cover(dept_id, spu_code, rmk_status, sale_status, rmk_mid)`。

---

## 3 · ipermission —— 权限数据全量拉取（两条，同一服务同一模式）

### 3.1 角色菜单关系

`aws-luckyus-ipermission-rw` / `luckyus_ipermission` · 账号 `iopenauth_A_o` · 7 天 11,280 次，按租户各一次

```sql
SELECT t_relation.role_id, t_relation.menu_code, t_menu.relate_menu_code
  FROM t_permission_role_menu_relation t_relation
  LEFT JOIN t_permission_menu t_menu
         ON t_menu.code = t_relation.menu_code
        AND t_relation.tenant = t_menu.tenant
        AND t_menu.status = 1
        AND t_menu.tenant = 'LKUS'
 WHERE t_relation.tenant = 'LKUS'
   AND t_relation.tenant = 'LKUS';
```

**现状**：单次扫 67,727 行、**返回 33,974 行**（2:1）。不是扫描浪费，是每分钟把整张权限关系表取回一次。

### 3.2 菜单 URI 映射

`aws-luckyus-ipermission-rw` / `luckyus_ipermission` · 账号 `iopenauth_A_o` · 7 天 5,048 次

```sql
SELECT code AS menuCode, end_uri uri
  FROM t_permission_menu
 WHERE tenant = 'LKUS' AND status = 1
   AND end_uri IS NOT NULL AND end_uri != ''
   AND tenant = 'LKUS';
```

**现状**：单次扫 8,203 行、返回 6,280 行（1.3:1）。与 3.1 同一服务、同一模式。

**动作（两条合并处理）**：单次扫 67,727 行返回 33,974 行、8,203 行返回 6,280 行 ——
**不是扫描浪费，是每分钟把整张权限表取回一次**，加索引解决不了取回量本身。
方向是应用侧缓存权限数据（权限属低频变更），改为变更时失效；或直接降低拉取频率。
两条同属 `iopenauth_A_o`，一次沟通一起改。

---

## 4 · salespayment —— 渠道费用预估任务捞取

`aws-luckyus-salespayment-rw` / `luckyus_sales_payment` · 账号 `isalespmtadmin_A_o` · 7 天 2,304 次

```sql
select id, tenant, trade_no, channel_pay_type_id, fee_plan_no, transaction_fee_est,
       merchant_service_fee_est, merchant_service_fee_vat_est, total_fee_est, transaction_fee,
       merchant_service_fee, merchant_service_fee_vat, total_fee, fee_est_times, fee_query_times,
       remark, delete_flag, create_id, create_name, create_time, modify_id, modify_name,
       modify_time, version
  from t_channel_fee f
 where 1 = 1
   and create_time >= '2026-08-02 14:20:00.025'
   and create_time <= '2026-09-01 14:20:00.025'
   and total_fee_est is null
   and ifnull(fee_est_times, 0) < 3
 order by fee_est_times, create_time
 limit 5000;
```

**现状**：单次扫 164,324 行、每次恒返回满 5,000 行；718,696 行（51.6%）`total_fee_est` 为空且
`fee_est_times` 全为 0 —— 预估任务空转 17 个月，是业务数据缺口。

**动作**：① **先修回写逻辑**（P0，先加索引只会让空转跑得更快）；
② 改写为 SARGable：`ifnull(fee_est_times,0) < 3` → `(fee_est_times IS NULL OR fee_est_times < 3)`；
③ 加索引 `idx_est_pending(total_fee_est, fee_est_times, create_time)`，消除 filesort，
扫描 161,145 → ≈5,000 行；④ 收窄 SELECT 列。

---

## 5 · isalesprivatedomain —— 私域待处理用户探针

`aws-luckyus-isalesprivatedomain-rw` · 账号 `privatedomainserv_A_o` · 7 天 11,922 次（慢日志计）

```sql
SELECT user_no
  FROM t_private_domain_user
 WHERE (support_status = 0 AND user_no IS NOT NULL)
   AND tenant = 'LKUS'
 ORDER BY user_no ASC
 LIMIT 1;
```

**现状**：7 天 11,922 次、3,499.5 秒，单次扫 4,933 行**一行不返回** —— 与 opshopsale 同型的空转探针。

**EXPLAIN（2026-09-02）**：`type=range`、`key=idx_user_no`、`rows=2584`、`filtered=1.0`、
`Extra=Using index condition; Using where`。走的是 `user_no IS NOT NULL` 这个范围条件，
按 `user_no` 顺序逐行回表检查 `support_status` 和 `tenant`；因为一行都不匹配，
`LIMIT 1` 起不到提前结束的作用，整棵索引走到底。`support_status` 与 `tenant` 均无索引。

**实测耗时**：现场跑 **12.9 ms**，记录均值 294 ms（23 倍差）。表只有 5,003 行，
所以记录里的 294 ms 大头是执行时刻的争用，不是这条语句本身。

**动作（已验证）**：建复合索引 `(tenant, support_status, user_no)` —— 等值两列定位后
`user_no` 有序，`LIMIT 1` 可即时返回，同时消除 `ORDER BY user_no` 的额外代价。
5,003 行的小表，DDL 秒级。**但绝对收益有限（12.9 ms → 亚毫秒），优先级低于第 1 条。**

> 🔴 **顺带发现（比索引更值得看）**：`tenant='LKUS' AND support_status=0` 有 **85 行**，
> 但这 85 行的 `user_no` **全部为 NULL**（最早 2025-11-07，最晚 2026-07-30）。
> 轮询条件里的 `user_no IS NOT NULL` 把它们全部排除 —— 也就是说这个待处理队列里
> 积压了 85 条、最久的将近 10 个月，而轮询任务永远看不到它们。
> 要么是 `user_no` 该回填没回填，要么是轮询条件写错了。与第 4 条 salespayment
> 空转 17 个月是同一类问题，建议交研发确认。

---

## 6 · salesmarketing —— 券模板全量分页拉取

`aws-luckyus-salesmarketing-rw` / `luckyus_sales_marketing` · 账号 `isalescouponservice_A_o` · 7 天 8,197 次

```sql
SELECT id, template_no, coupon_name, coupon_show_name, valid_status, coupon_type,
       coupon_discount_type, coupon_discount_sub_type, effective_time_type, effective_from_receive,
       effective_start_time, effective_end_time, effective_day_of_week, invalid_time_type,
       invalid_from_receive, expire_time, expire_day_of_week, threshold_amount, threshold_commodity,
       target_commodity, discount, coupon_denomination, coupon_currency, max_discount_amount,
       max_commodity_number_per_discount, commodity_sort_type, give_away, copy_from, readme_type,
       readme, remark, create_user_id, create_user, modify_user_id, modify_user, deleted,
       commodity_mix_type, default_template, create_time, modify_time, tenant
  FROM t_coupon_template
 WHERE (id > 0) AND tenant = 'LKUS'
 ORDER BY id ASC
 LIMIT 1000;
```

**现状**：7 天 8,197 次、2,534.7 秒，单次扫 1,794 行返回 965 行 —— 每分钟把券模板表全量拉一遍。

**动作**：应用侧缓存模板（模板属低频变更的配置数据）；`id > 0` 是恒真条件，
若为游标分页应改为 `id > ${lastId}` 并持久化水位。

---

## 7 · salespayment —— 监控看板取数（DBA 自有）

`aws-luckyus-salespayment-rw` · 账号 `dbms_dbsearch`（Grafana MySQL 数据源） · 7 天 8,726 次

```sql
select UNIX_TIMESTAMP() * 1000 AS _timestamp, count(t.id) AS _value, c.name
  from t_trade t
  left join t_pay_channel c on c.id = t.channel_id
 where t.create_time >= CURDATE() and t.create_time <= NOW()
   and tenant = 'LKUS' AND status = 2
 group by t.channel_id
 ORDER BY COUNT(t.id) desc;
```

**现状**：7 天 8,726 次、2,325.8 秒，单次扫 6,630 行返回 9.5 行；扫描量随当天累积逐小时增长。
**归属是我们自己的 Grafana 面板，不是业务查询。**

**动作**：降低面板刷新频率，或改写为按 `channel_id` 预聚合／缩短时间窗口。

---

## 8 · salesmarketing —— 活动参与人数计数

`aws-luckyus-salesmarketing-rw` / `luckyus_sales_marketing` · 账号 `isalesmktadmin_A_o` · 7 天 11,484 次

```sql
select count(1)
  from t_market_activity_partake
 where activity_no = 'LKUSCA118459132616531969';
```

**现状**：单次扫 290,421 行只为拿一个数字（29 万:1），7 天累计 1,929.8 秒。
与第 1 条合计每周扫描 68 亿行。

**EXPLAIN（2026-09-02）**：`type=ref`、`key=idx_activity_no`、`rows=544352`、`filtered=100`、
`Extra=Using index`。—— **索引已经有了，而且已经用上了，还是覆盖索引扫描。**

**实测**：该 `activity_no` 名下实有 **300,636 行**；现场跑 **168.3 ms**，
记录均值 168 ms —— **两者完全一致**。说明这不是争用问题，是稳定复现的真实成本：
数 30 万条索引项就是要 168 ms。

**动作（已改判）**：**加索引不是解法**（`idx_activity_no` 已存在且生效），
上一版报告里"给 `activity_no` 建索引"这条作废。真正的修法只有两条路：
① 计数改为缓存／增量维护（活动参与数写入时 +1，读时不做实时 `COUNT`）；
② 若该数字只用于展示，放宽实时性，改为定时快照。
需与营销研发（张晓松）确认这个计数的用途和实时性要求。

---

## 9 · salesmarketing —— 过期券归档探针

`aws-luckyus-salesmarketing-rw` / `luckyus_sales_marketing` · 账号 `isalescouponservice_A_o` · 每天 04:30 UTC

```sql
SELECT id, coupon_no, activity_id, activity_no, activity_name, marketing_proposal_id,
       marketing_proposal_no, marketing_proposal_name, proposal_id, proposal_no, proposal_name,
       coupon_template_id, coupon_type, coupon_discount_type, coupon_discount_sub_type, coupon_name,
       coupon_show_name, threshold_amount, threshold_commodity, coupon_denomination, coupon_currency,
       discount, marketing_cost, member_no, member_phone, order_no, receive_time, coupon_status,
       use_status, use_time, effective_time_type, effective_begin_time, effective_end_time,
       effective_day_of_week, invalid_time_type, expire_time, expire_day_of_week, coupon_source,
       invite_code, invite_code_type, manual_coupon_send_id, send_type, member_status,
       target_commodity, allowance_program_id, allowance_sub_program_id, promo_code, redeem_code,
       create_time, modify_time, tenant
  FROM t_coupon_record_expired
 WHERE (coupon_source = 15 AND expire_time < '2026-08-02 04:30:00.032' AND id >= 0)
   AND tenant = 'LKUS'
 ORDER BY id ASC
 LIMIT 1;
```

**现状**：`ORDER BY 主键 + LIMIT 1` 诱发优化器误判（估 3 行、实扫 312 万行）；
`coupon_source` / `tenant` 均无索引；扫描位置每天 +3,500 行逐日劣化。

**动作**：加索引 `idx_tenant_source_id(tenant, coupon_source, id)`
（3,423 万行 / 10.97 GB 表，须 `ALGORITHM=INPLACE, LOCK=NONE`，02:00~04:00 UTC 执行，走变更申请）；
去掉恒真条件 `id >= 0`；收窄 SELECT 列；改为游标式分页。

---

## 10 · salesorder —— 财务对账三条（一份变更申请，两个索引）

每天 02:00~03:00 UTC 的财务对账任务，账号 `isalesorderservice_A_o`，
三条 SQL 由**同一份变更申请的两个索引**一并解决，因此合为一条。

### 10.1 退款对账计数

`aws-luckyus-salesorder-rw` / `luckyus_sales_order` · 账号 `isalesorderservice_A_o` · 每天 03:00 UTC

```sql
SELECT COUNT(*) AS total
  FROM t_finance_refund
 WHERE deleted = 0
   AND (checking_status = 1 AND checking_date BETWEEN '2026-08-25 03:00:00.03' AND '2026-09-01 03:00:00.03')
   AND t_finance_refund.tenant = 'LKUS';
```

**现状**：`checking_date` 无索引、`EXPLAIN possible_keys = NULL` 全表扫；
表上 `idx_checking_time_and_status` 是名字只差几个字母的**近似索引**，全部落空。

### 10.2 收款对账明细查询

`aws-luckyus-salesorder-rw` / `luckyus_sales_order` · 账号 `isalesorderservice_A_o` · 每天 02:01 UTC，按租户循环

```sql
SELECT id, receipt_no, receipt_account_no, status, receipt_method_no, payment_method,
       tp_serial_no, third_serial_no, receipt_object_type, order_no, user_no,
       receipt_amount, discount_amount, currency, receipt_date, checking_date,
       checking_amount, checking_result, checking_failed_reason, checking_time,
       difference_amount, create_time, modify_time, creator_id, creator_name,
       modifier_id, modifier_name, remark, tenant
  FROM t_finance_receipt
 WHERE deleted = 0
   AND (status = 1 AND checking_date BETWEEN '2026-08-25 02:01:35.818' AND '2026-09-01 02:01:35.818')
   AND t_finance_receipt.tenant = 'IQA2'
 ORDER BY modify_time DESC
 LIMIT 10000;
```

**现状**：`ORDER BY modify_time DESC + LIMIT 10000` 诱发 Backward index scan，
倒着走完 136 万行索引只命中 31 行；`checking_date` / `tenant` 均无索引。

### 10.3 收款对账计数（与 10.2 配套，同一秒触发）

`aws-luckyus-salesorder-rw` / `luckyus_sales_order` · 账号 `isalesorderservice_A_o` · 与 10.2 同一秒触发

```sql
SELECT COUNT(*) AS total
  FROM t_finance_receipt
 WHERE deleted = 0
   AND (status = 1 AND checking_date BETWEEN '2026-08-25 02:01:35.818' AND '2026-09-01 02:01:35.818')
   AND t_finance_receipt.tenant = 'IQA2';
```

**现状**：`performance_schema` 累计 80 次扫描 **1.01 亿行**，只为拿 80 个数字；全表扫 100%。

**动作**（变更申请《变更申请_salesorder_财务对账索引_2026-09-01》已出，待审批）：

```sql
ALTER TABLE luckyus_sales_order.t_finance_receipt
  ADD INDEX idx_tenant_status_ckdate (tenant, status, deleted, checking_date),
  ALGORITHM=INPLACE, LOCK=NONE;

ALTER TABLE luckyus_sales_order.t_finance_refund
  ADD INDEX idx_tenant_ckstatus_ckdate (tenant, checking_status, deleted, checking_date),
  ALGORITHM=INPLACE, LOCK=NONE;
```

`idx_tenant_status_ckdate` 一个索引同时解决 10.2 和 10.3。
另建议去掉「先 COUNT 再 SELECT」—— 结果集只有几十行，分页计数没有价值。

---

## 18 条如何收敛到 10 条

### 剔除 5 条：实测证明是争用受害者或量级太小

| 原序号 | 实例 / 表 | 7天DB时间 | 剔除理由 |
|---|---|---:|---|
| 9 | salesorder `t_order` | 1,957.7s | `EXPLAIN` 显示已走 `idx_create_time` 范围扫描（1,863 行），计划本来就对；高峰期现场实测 **4.0 ms** vs 记录均值 350 ms，**差 87 倍** —— 争用受害者，加索引无从加起 |
| 12 | cdpactivity `t_contact_activity_instance_record` | 191.7s | 现场实测 **27 ms** vs 记录均值 1.65 s，**差 60 倍** —— 同为争用受害者；主修是错峰，预防性索引的 CR 已出，不必占名额 |
| 16 | opempefficiency `t_training_time` | 36.4s | 非整点实测 **332 ms** vs 记录 2,572 ms，差 7.7 倍；两张表分别只有 512 行 / 3,442 行 —— 修法是错峰，不是改 SQL |
| 17 | opempefficiency `t_attendance_change` | 31.2s | 全表 2,515 行 / 4.5 MB，全表扫本该毫秒级却记 2.83 s —— 同上，修法是错峰 |
| 18 | ibillingcentersrv `t_income_bill` | 12.4s | 7 天仅 4 次、12.4 秒，量级比第 1 条小三个数量级；且尚未分析，按周度分诊流程排期即可 |

> 剔除依据是一条统一判据：**现场实测耗时 ÷ 慢日志记录均值**。
> 比值 ≈ 1 → 真实成本，留榜（如第 8 条 168.3 ms vs 168 ms）；
> 差 10 倍以上 → 慢在执行时刻而不在语句，修法是错峰／排查争用，不是优化 SQL。

> ⚠️ **一处例外要说明**：第 5 条 isalesprivatedomain 实测 12.9 ms vs 记录 294 ms，
> 比值 23 倍，按上面的判据本该剔除。留下它是因为它与 `t_order` 有一点不同 ——
> **`t_order` 的执行计划本来就是对的，而它的计划确有缺陷**（走 `idx_user_no` 逐行回表
> 滤 `support_status`，扫 4,933 行返回 0 行，`LIMIT 1` 完全失效）。
> 即入选判据的 ① 成立、② 不成立，因此**它留榜但绝对收益只有十几毫秒，排期上应排在最后**。
> 真正值得从这条里拿走的是那 85 行积压（见文末）。

### 合并 3 条：同一个动作一次解决

| 合并进 | 原序号 | 理由 |
|---|---|---|
| 第 3 条 | 原 5 + 原 8 | 同属 `iopenauth_A_o`、同一模式（每分钟全量取回权限表），同一次沟通一起改 |
| 第 10 条 | 原 13 + 14 + 15 | 同一份变更申请的两个索引解决三条 SQL，`idx_tenant_status_ckdate` 一个索引管两条 |

---

## 口径说明

- 第 1、3、5、6、7、8 条来自**慢日志原文口径**（含均耗 <1s 的高频查询）；
  其余来自**采集表口径**（`t_dba_collect_slow_query`，只收均耗 ≥1s 的指纹）。
  原文口径第一名（第 1 条，23,061 秒）**不在采集表榜单上**，只搬采集表 TOP10 会漏掉最大的一条。
- 被复核实例的 `long_query_time` 均为 **0.1 秒**，所以原文口径的次数只是超过 100 ms 的尾部，
  不是真实执行次数（真实次数更高）。
- 账号 `diagtools`（DBA 自有 store-ops 看板取数）三条已于 2026-09-01 修复合并，不在清单。
  第 7 条 `dbms_dbsearch` 同属 DBA 自有，因未修复而保留。
- 上一版报告已判定无优化动作、本次未再列入的：salesorder `397899b0`（已停跑）、
  salespayment `18f0b86c`（执行计划已最优）、scmsrm `53e2bc9c`（INSERT，扫 0 行）、
  upush `04bc9a2d`（慢在提交延迟）、cdpactivity `t_contact_activity` 计数（单次只扫 52 行）、
  framework01 `es_qrtz_LOCKS ... FOR UPDATE`（Quartz 抢锁，扫 1 行）、
  ijumpserver `151b0ae8`（L3 安全运维，出范围）。
- 复核中另查出两处队列积压，与 SQL 优化无关但更值得处理：
  第 1 条 1 行任务卡在 `task_status=0` 已 3 个月；
  第 5 条 85 行 `support_status=0` 因 `user_no` 全为 NULL 被轮询条件永久排除，最久近 10 个月。
