# LKUS 需要优化的慢 SQL 清单

| | |
|---|---|
| 报告编号 | LCNA-DBA-SQL-2026-0902 |
| 来源 | LCNA-DBA-SQL-2026-0901-E《慢查询 TOP10 报告》两张榜单合并去重 |
| 数据窗口 | 2026-08-25 ~ 2026-09-01（7 天） |
| 范围 | L0 + L1 共 48 台实例 |
| 排序 | 按 7 天累计 DB 时间降序 |
| EXPLAIN 复核 | 2026-09-02 已跑第 1、4、9、10 条（原「待复核」四条），结论见各条 |

---

## 清单

| # | 实例 | 表 | 7天DB时间 | 7天次数 | 单次扫描 | 单次返回 | 动作类型 | 状态 |
|---|---|---|---:|---:|---:|---:|---|---|
| 1 | salesmarketing | t_cyber_ug_data_fetch_task | 23,060.7s | 66,990 | 51,467 | 0.14 | 加索引 | **已验证** |
| 2 | opshopsale | t_shopsale_spu + t_shopsale_rmk | 4,976.9s | 768 | 766,796 | 0 | 去重＋降频 | 已定论 |
| 3 | salespayment | t_channel_fee | 3,780.6s | 2,304 | 164,324 | 5,000 | 修任务逻辑＋加索引 | 已定论 |
| 4 | isalesprivatedomain | t_private_domain_user | 3,499.5s | 11,922 | 4,933 | 0 | 加索引 | **已验证** |
| 5 | ipermission | t_permission_role_menu_relation | 2,716.8s | 11,280 | 67,727 | 33,974 | 应用侧缓存 | 待沟通 |
| 6 | salesmarketing | t_coupon_template | 2,534.7s | 8,197 | 1,794 | 965 | 应用侧缓存 | 待沟通 |
| 7 | salespayment | t_trade + t_pay_channel | 2,325.8s | 8,726 | 6,630 | 9.5 | 降频／改写面板 | DBA 自有 |
| 8 | ipermission | t_permission_menu | 1,989.0s | 5,048 | 8,203 | 6,280 | 应用侧缓存 | 待沟通 |
| 9 | salesorder | t_order | 1,957.7s | 5,599 | 779 | 0.44 | ~~加索引~~ 排查争用 | **已改判** |
| 10 | salesmarketing | t_market_activity_partake | 1,929.8s | 11,484 | 290,421 | 1 | ~~加索引~~ 计数缓存 | **已改判** |
| 11 | salesmarketing | t_coupon_record_expired | 371.2s | 8 | 3,041,567 | 1 | 加索引 | 已定论 |
| 12 | cdpactivity | t_contact_activity_instance_record | 191.7s | 104 | 12,337 | 42 | 错峰＋加索引 | CR 已出 |
| 13 | salesorder | t_finance_refund | 93.9s | 80 | 20,597 | 1 | 加索引 | CR 已出 |
| 14 | salesorder | t_finance_receipt | 84.3s | 14 | 1,265,167 | 31 | 加索引 | CR 已出 |
| 15 | salesorder | t_finance_receipt | 80.2s | 16 | 1,264,122 | 1 | 加索引 | CR 已出 |
| 16 | opempefficiency | t_training_time | 36.4s | 14 | 2,185 | 0 | 错峰 | 已定论 |
| 17 | opempefficiency | t_attendance_change | 31.2s | 14 | 2,603 | 0 | 错峰 | 已定论 |
| 18 | ibillingcentersrv | t_income_bill | 12.4s | 4 | 228,777 | 1 | 待分析 | 待排期 |

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
53,321 行的表走完。与第 11 条券归档探针是同一个 `ORDER BY 主键 + LIMIT` 陷阱。

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

## 3 · salespayment —— 渠道费用预估任务捞取

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

## 4 · isalesprivatedomain —— 私域待处理用户探针

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
> 要么是 `user_no` 该回填没回填，要么是轮询条件写错了。与第 3 条 salespayment
> 空转 17 个月是同一类问题，建议交研发确认。

---

## 5 · ipermission —— 角色菜单关系全量拉取

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

**动作**：应用侧缓存权限关系（权限数据低频变更），或降低拉取频率、改为变更时失效。
加索引解决不了取回量本身。

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

## 8 · ipermission —— 菜单 URI 映射拉取

`aws-luckyus-ipermission-rw` / `luckyus_ipermission` · 账号 `iopenauth_A_o` · 7 天 5,048 次

```sql
SELECT code AS menuCode, end_uri uri
  FROM t_permission_menu
 WHERE tenant = 'LKUS' AND status = 1
   AND end_uri IS NOT NULL AND end_uri != ''
   AND tenant = 'LKUS';
```

**现状**：单次扫 8,203 行、返回 6,280 行（1.3:1）。与第 5 条同一服务、同一模式。

**动作**：与第 5 条合并处理 —— 应用侧缓存 / 降低调用频次。

---

## 9 · salesorder —— 异常订单轮询

`aws-luckyus-salesorder-rw` / `luckyus_sales_order` · 账号 `isalesorderservice_A_o` · 每分钟一次（慢日志中 7 天 5,599 条）

```sql
SELECT id, tenant, parent_id, channel, order_category, order_type, order_sub_type, user_no,
       user_type, user_nick_name, user_sex, shop_id, shop_type, shop_name, shop_number,
       country_code, country_name, city_code, city_name, status, produce_status, express_status,
       fulfill_status, invoice_status, refund_status, refund_time, comment_status, display_flag,
       currency_code, total_money, payable_money, pay_money, pay_time, cancel_time, finish_time,
       create_type, create_id, create_name, create_time, modify_id, modify_name, modify_time,
       version, order_language, user_timezone, invoiced_time
  FROM t_order
 WHERE (STATUS = 10 OR (display_flag = 0 AND STATUS != 0))
   AND create_time BETWEEN '2026-09-01 11:50:00.014' AND '2026-09-01 13:50:00.014'
 ORDER BY id
 LIMIT 100;
```

**现状**：7 天 5,599 次、1,957.7 秒，单次扫 779 行返回 0.44 行（1,780:1）。
每分钟重扫**过去 2 小时**的窗口，窗口高度重叠；且**没有 `tenant` 过滤**。

**EXPLAIN（2026-09-02）**：`type=range`、`key=idx_create_time`、`rows=1863`、`filtered=18.1`、
`Extra=Using index condition; Using where; Using filesort`。
**执行计划本身是对的** —— `idx_create_time(create_time, tenant, display_flag)` 已经把
时间窗口收成 1,863 行的范围扫描，不是全表扫。

**实测耗时**：2026-09-02 16:00 UTC（业务高峰，2 小时窗口）现场跑 **4.0 ms**，
记录均值 350 ms —— **差 87 倍**。

**动作（已改判）**：**不加索引。** 这条与第 16、17 两条 opempefficiency 同类，
是争用受害者而不是慢 SQL —— 4 ms 的语句被记成 350 ms，问题在执行时刻不在语句。
可做的两件低成本整改：① 每分钟重扫过去 2 小时、窗口重叠 120 倍，改为游标水位
（`id > ${lastId}`）或把窗口收到轮询间隔量级；② 补 `tenant` 条件，
让 `idx_create_time` 的第二列也能用上。两项都不是为了降这 4 ms，是减少无谓的重复读。

---

## 10 · salesmarketing —— 活动参与人数计数

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

## 11 · salesmarketing —— 过期券归档探针

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

## 12 · cdpactivity —— 触达活动实例去重

`aws-luckyus-cdpactivity-rw` / `luckyus_cdp_activity` · 账号 `icdpactivityengine_A_o` · 每小时整点

```sql
SELECT DISTINCTROW activity_id
  FROM t_contact_activity_instance_record
 WHERE create_time >= ? AND create_time <= ? AND tenant = ?
 ORDER BY create_time;
```

**现状**：记录均值 1.65 s，我现场实测同一语句 **27 ms**（差 60 倍）—— 是整点批量争用的受害者，
不是 SQL 本身慢。`create_time` / `tenant` 无索引是次要隐患。

**动作**：① 主修 = 从整点 `:00` 错峰；② 预防性索引（变更申请已出）：

```sql
ALTER TABLE luckyus_cdp_activity.t_contact_activity_instance_record
  ADD INDEX idx_tenant_create_time (tenant, create_time),
  ALGORITHM=INPLACE, LOCK=NONE;
```

---

## 13 · salesorder —— 退款对账计数

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

**动作**（变更申请已出，待审批）：

```sql
ALTER TABLE luckyus_sales_order.t_finance_refund
  ADD INDEX idx_tenant_ckstatus_ckdate (tenant, checking_status, deleted, checking_date),
  ALGORITHM=INPLACE, LOCK=NONE;
```

---

## 14 · salesorder —— 收款对账明细查询

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

**动作**（变更申请已出，待审批）：

```sql
ALTER TABLE luckyus_sales_order.t_finance_receipt
  ADD INDEX idx_tenant_status_ckdate (tenant, status, deleted, checking_date),
  ALGORITHM=INPLACE, LOCK=NONE;
```

---

## 15 · salesorder —— 收款对账计数（与第 14 条配套）

`aws-luckyus-salesorder-rw` / `luckyus_sales_order` · 账号 `isalesorderservice_A_o` · 与第 14 条同一秒触发

```sql
SELECT COUNT(*) AS total
  FROM t_finance_receipt
 WHERE deleted = 0
   AND (status = 1 AND checking_date BETWEEN '2026-08-25 02:01:35.818' AND '2026-09-01 02:01:35.818')
   AND t_finance_receipt.tenant = 'IQA2';
```

**现状**：`performance_schema` 累计 80 次扫描 **1.01 亿行**，只为拿 80 个数字；全表扫 100%。

**动作**：第 14 条的同一个索引 `idx_tenant_status_ckdate` 一并解决；
另建议去掉「先 COUNT 再 SELECT」——结果集只有几十行，分页计数没有价值。

---

## 16 · opempefficiency —— 培训工时校验

`aws-luckyus-opempefficiency-rw` / `luckyus_opempefficiency` · 账号 `iopempefficiency_A_o` · 每天 2 次，固定整点 `:00`

```sql
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

**现状**：应用记录均值 2,572 ms，我 20:20（非整点）现场跑同一语句 **332 ms**，差 7.7 倍。
两张表分别只有 512 行 / 3,442 行 —— 争用受害者，不是慢 SQL。

**动作**：**错峰**，从整点 `:00` 挪开。不要加索引、不要改写语句（表太小，改写最多省几百毫秒）。

---

## 17 · opempefficiency —— 考勤异动状态推进

`aws-luckyus-opempefficiency-rw` / `luckyus_opempefficiency` · 账号 `iopempefficiency_A_w` · 每天 2 次，05:00 UTC

```sql
UPDATE t_attendance_change
   SET status = 4, modify_time = now(), modifier_name = 'system'
 WHERE status = 1 AND attendance_date < '2026-08-30'
   AND sub_type IN (101,102,201,202,203,204)
   AND ((sub_type IN (101,102) AND clock_dept_id IN (…33 个门店 id…))
     OR (sub_type NOT IN (101,102) AND source_scheduling_dept_id IN (…33 个门店 id…)))
   AND tenant = 'LKUS';
```

**现状**：全表只有 2,515 行 / 4.5 MB，这条扫 2,630 行 ≈ 整张表却耗时 2.83 秒 ——
4.5 MB 的全表扫本该是毫秒级。执行时刻 05:00:03 正在夜间批量窗口内。

**动作**：**错峰**，从 05:00 UTC 挪开。加索引无意义。

---

## 18 · ibillingcentersrv —— 账单商品明细计数

`aws-luckyus-ibillingcentersrv-rw` / `luckyus_ibillingcenterservice` · 7 天 4 次

```sql
SELECT COUNT(*) AS total
  FROM t_income_bill bill
  STRAIGHT_JOIN t_income_bill_commodity_detail detail
    ON bill.bill_no = detail.bill_no
   AND detail.biz_type = ?
   AND detail.tenant = ?
 WHERE bill.local_bill_date >= ?
   AND bill.local_bill_date <= ?
   AND bill.department_code NOT IN (...)
   AND bill.tenant = ?;
```

**现状**：单次扫 228,777 行返回 1 行，是 L1 尾部单次扫描量最高的一条。
`STRAIGHT_JOIN` 强制了连接顺序，可能阻止优化器选更优路径。

**动作**：待分析 —— 需取慢日志原文补齐参数、跑 `EXPLAIN`、核对两表索引后给结论。

---

## 口径与遗漏说明

- 第 1、4、5、6、7、8、9、10 条来自**慢日志原文口径**（含均耗 <1s 的高频查询）；
  其余来自**采集表口径**（`t_dba_collect_slow_query`，只收均耗 ≥1s 的指纹）。两个口径对同一条 SQL
  的 DB 时间会有几个百分点差异（如 opshopsale 4,976.9s vs 4,865.9s）。
- 账号 `diagtools`（DBA 自有 store-ops 看板取数）的三条已于 2026-09-01 修复合并，不在本清单。
  第 7 条 `dbms_dbsearch` 同属 DBA 自有，因未修复而保留在清单内。
- **不在本清单的慢查询**（原报告已判定无优化动作）：salesorder `397899b0`（已停跑）、
  salespayment `18f0b86c`（执行计划已最优）、scmsrm `53e2bc9c`（INSERT，扫 0 行）、
  upush `04bc9a2d`（慢在提交延迟）、cdpactivity `t_contact_activity` 计数（单次只扫 52 行）、
  framework01 `es_qrtz_LOCKS ... FOR UPDATE`（Quartz 抢锁，扫 1 行）、
  ijumpserver `151b0ae8`（L3 安全运维，出范围）。
- **第 1、4、9、10 条的 `EXPLAIN` 已于 2026-09-02 跑完**，结论写在各条内：
  第 1、4 条索引方案**成立**；第 9 条**改判为争用受害者，不加索引**；
  第 10 条**索引已存在且已生效，加索引作废**，只能靠计数缓存。
- 三台被复核实例的 `long_query_time` 均为 **0.1 秒**，因此原文口径的「7 天次数」
  只是超过 100 ms 的尾部，不是真实执行次数（真实次数更高）。
- 复核中另外查出两处积压，与 SQL 优化无关但更值得处理：
  第 1 条 1 行任务卡在 `task_status=0` 已 3 个月；
  第 4 条 85 行 `support_status=0` 因 `user_no` 全为 NULL 被轮询条件永久排除，最久近 10 个月。
