# LKUS 慢查询优化建议 —— TOP 10

数据窗口 2026-08-25 ~ 2026-09-01（7 天）· 范围 L0 + L1 共 48 台实例 · 出具 2026-09-02 · DBA 曾翔宇

| # | 实例 | 表 | 7天DB时间 | 单次扫描 → 返回 | 优化方向 | 归属 |
|---|---|---|---:|---|---|---|
| 1 | salesmarketing | t_cyber_ug_data_fetch_task | 23,060.7s | 51,467 → 0.14 | 加复合索引 | 张晓松 |
| 2 | opshopsale | t_shopsale_spu + t_shopsale_rmk | 4,976.9s | 766,796 → 0 | 任务去重＋降频 | 陈培浩／游熖 |
| 3 | ipermission | t_permission_role_menu_relation<br>t_permission_menu | 4,705.8s | 67,727 → 33,974<br>8,203 → 6,280 | 应用侧缓存 | 陈亮／张晓松 |
| 4 | salespayment | t_channel_fee | 3,780.6s | 164,324 → 5,000 | 先修任务逻辑，再加索引 | 张晓松 |
| 5 | isalesprivatedomain | t_private_domain_user | 3,499.5s | 4,933 → 0 | 加复合索引 | 张翔 |
| 6 | salesmarketing | t_coupon_template | 2,534.7s | 1,794 → 965 | 应用侧缓存 | 张晓松 |
| 7 | salespayment | t_trade + t_pay_channel | 2,325.8s | 6,630 → 9.5 | 降频／改写面板 | DBA |
| 8 | salesmarketing | t_market_activity_partake | 1,929.8s | 290,421 → 1 | 计数缓存 | 张晓松 |
| 9 | salesmarketing | t_coupon_record_expired | 371.2s | 3,041,567 → 1 | 加复合索引 | 张晓松 |
| 10 | salesorder | t_finance_refund<br>t_finance_receipt ×2 | 258.4s | 20,597 → 1<br>126 万 → 31／1 | 两个索引（CR 已出） | 张晓松 |

---

## 1 · salesmarketing —— 人群数据拉取任务扫描

`aws-luckyus-salesmarketing-rw` / `luckyus_sales_marketing` · `isalesmktadmin_A_o` · 约每 9 秒一次

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

单次扫 51,467 行返回 0.14 行；表上只有 `PRIMARY` 和 `idx_group_no`，四个过滤列均无索引。

**优化建议**
1. 加复合索引 `(tenant, task_status, deleted, create_time)`；`ALGORITHM=INPLACE, LOCK=NONE`。
2. 加完复跑 `EXPLAIN`，确认不再走 `PRIMARY`。
3. 复核轮询频率是否需要 9 秒一次。
4. 另：`id=18552`（`group_no=LKUSUG119455478458818560`）卡在 `task_status=0` 已 3 个月，
   而轮询条件带 `create_time >= 近窗口`，这行永远捞不到，请确认是否漏处理。

---

## 2 · opshopsale —— 门店售卖备注一致性巡检

`aws-luckyus-opshopsale-rw` / `luckyus_opshopsale` · `iopshopsaleservice_A_o` · 每 30 分钟一次

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

单次扫 766,796 行、恒返回 0 行；两个 Pod 无分布式锁重复执行。

**优化建议**
1. 定时任务去重：加分布式锁，或改由 Chronus 单点调度。
2. 巡检频率从每 30 分钟改为每天一次，放在 06:00~08:00 UTC 低峰（预计降 99%）。
3. 确认 `LEFT JOIN` 语义：若本意是「找无备注的 SPU」，当前写法逻辑有误，应为 `WHERE t2.id IS NULL`。
4. 可选：`t_shopsale_rmk` 加覆盖索引 `idx_rmk_cover(dept_id, spu_code, rmk_status, sale_status, rmk_mid)`。

---

## 3 · ipermission —— 权限数据全量拉取（两条）

`aws-luckyus-ipermission-rw` / `luckyus_ipermission` · `iopenauth_A_o` · 按租户各一次

**3.1 角色菜单关系**（7 天 11,280 次，单次扫 67,727 行返回 33,974 行）

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

**3.2 菜单 URI 映射**（7 天 5,048 次，单次扫 8,203 行返回 6,280 行）

```sql
SELECT code AS menuCode, end_uri uri
  FROM t_permission_menu
 WHERE tenant = 'LKUS' AND status = 1
   AND end_uri IS NOT NULL AND end_uri != ''
   AND tenant = 'LKUS';
```

两条都不是扫描浪费，是每分钟把整张权限表取回一次，加索引解决不了取回量本身。

**优化建议**
1. 应用侧缓存权限数据（权限属低频变更），改为变更时失效。
2. 或降低拉取频率。
3. 两条同属 `iopenauth_A_o`，建议一并处理。

---

## 4 · salespayment —— 渠道费用预估任务捞取

`aws-luckyus-salespayment-rw` / `luckyus_sales_payment` · `isalespmtadmin_A_o` · 7 天 2,304 次

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

单次扫 164,324 行、每次恒返回满 5,000 行；`t_channel_fee` 中 718,696 行（全表 51.6%）
`total_fee_est` 为空且 `fee_est_times` 全为 0，最老一条 2025-03-24。

**优化建议**
1. **先排查费用预估任务为什么不回写**（P0）—— 确认是否存在吞异常、事务未提交、
   或费率方案查不到直接跳过。**必须先修回写，再加索引**；先加索引只会让空转跑得更快。
2. 评估 718,696 条缺失预估值的财务影响，与财务确认是否需要补数。
3. 改写为 SARGable：`ifnull(fee_est_times,0) < 3` → `(fee_est_times IS NULL OR fee_est_times < 3)`。
4. 加索引 `idx_est_pending(total_fee_est, fee_est_times, create_time)`，
   与第 3 点配合可消除 filesort，扫描 161,145 → ≈5,000 行。
5. 收窄 `SELECT` 列，去掉 `remark`、`create_name`、`modify_name` 等。

---

## 5 · isalesprivatedomain —— 私域待处理用户探针

`aws-luckyus-isalesprivatedomain-rw` / `luckyus_isales_privatedomain` · `privatedomainserv_A_o` · 7 天 11,922 次

```sql
SELECT user_no
  FROM t_private_domain_user
 WHERE (support_status = 0 AND user_no IS NOT NULL)
   AND tenant = 'LKUS'
 ORDER BY user_no ASC
 LIMIT 1;
```

单次扫 4,933 行一行不返回；`support_status` 与 `tenant` 均无索引，`LIMIT 1` 起不到提前结束的作用。

**优化建议**
1. 加复合索引 `(tenant, support_status, user_no)`；表仅 5,003 行，DDL 秒级。
2. 另（比索引更值得处理）：`tenant='LKUS' AND support_status=0` 有 **85 行**，
   但这 85 行的 `user_no` **全部为 NULL**（最早 2025-11-07，最晚 2026-07-30），
   被轮询条件里的 `user_no IS NOT NULL` 永久排除。请确认是 `user_no` 该回填没回填，
   还是轮询条件写错了。

---

## 6 · salesmarketing —— 券模板全量分页拉取

`aws-luckyus-salesmarketing-rw` / `luckyus_sales_marketing` · `isalescouponservice_A_o` · 7 天 8,197 次

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

约每分钟把券模板表全量拉一遍，单次扫 1,794 行返回 965 行。

**优化建议**
1. 应用侧缓存模板（模板属低频变更的配置数据）。
2. `id > 0` 是恒真条件；若本意是游标分页，应改为 `id > ${lastId}` 并持久化水位。

---

## 7 · salespayment —— 监控看板取数（DBA 自有）

`aws-luckyus-salespayment-rw` · `dbms_dbsearch`（Grafana MySQL 数据源） · 7 天 8,726 次

```sql
select UNIX_TIMESTAMP() * 1000 AS _timestamp, count(t.id) AS _value, c.name
  from t_trade t
  left join t_pay_channel c on c.id = t.channel_id
 where t.create_time >= CURDATE() and t.create_time <= NOW()
   and tenant = 'LKUS' AND status = 2
 group by t.channel_id
 ORDER BY COUNT(t.id) desc;
```

单次扫 6,630 行返回 9.5 行，扫描量随当天累积逐小时增长。归属 DBA，不是业务查询。

**优化建议**
1. 降低面板刷新频率。
2. 或改为按 `channel_id` 预聚合／缩短时间窗口。

---

## 8 · salesmarketing —— 活动参与人数计数

`aws-luckyus-salesmarketing-rw` / `luckyus_sales_marketing` · `isalesmktadmin_A_o` · 7 天 11,484 次

```sql
select count(1)
  from t_market_activity_partake
 where activity_no = 'LKUSCA118459132616531969';
```

该 `activity_no` 名下实有 300,636 行，单次扫 290,421 行只为拿一个数字，稳定耗时 168 ms。
`idx_activity_no` 已存在且已生效（覆盖索引扫描），**加索引解决不了**。

**优化建议**
1. 计数改为缓存／增量维护：参与数在写入时 +1，读时不做实时 `COUNT`。
2. 或若该数字只用于展示，放宽实时性，改为定时快照。
3. 请确认这个计数的用途和实时性要求。

---

## 9 · salesmarketing —— 过期券归档探针

`aws-luckyus-salesmarketing-rw` / `luckyus_sales_marketing` · `isalescouponservice_A_o` · 每天 04:30 UTC

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

`coupon_source` / `tenant` 均无索引；`ORDER BY 主键 + LIMIT 1` 诱发优化器按主键顺序扫，
扫 312 万行返回 1 行，且扫描位置每天 +3,500 行逐日劣化。

**优化建议**
1. 加复合索引 `idx_tenant_source_id(tenant, coupon_source, id)`。
   表 3,423 万行 / 10.97 GB，须 `ALGORITHM=INPLACE, LOCK=NONE`，
   建议 02:00~04:00 UTC 执行，需走变更申请。
2. 去掉恒真条件 `id >= 0`（对 `bigint unsigned` 主键永远为真，干扰优化器估算）。
3. 收窄 `SELECT` 列，探针只需 `id`。
4. 改为游标式分页：`id > ${lastId}` 并持久化水位。
5. 执行时间从 04:30 UTC 挪开，避免与 05:00 UTC 每日批量叠加。

---

## 10 · salesorder —— 财务对账三条（一份变更申请，两个索引）

`aws-luckyus-salesorder-rw` / `luckyus_sales_order` · `isalesorderservice_A_o` · 每天 02:00~03:00 UTC

**10.1 退款对账计数**（每天 03:00 UTC，单次扫 20,597 行返回 1 行）

```sql
SELECT COUNT(*) AS total
  FROM t_finance_refund
 WHERE deleted = 0
   AND (checking_status = 1 AND checking_date BETWEEN '2026-08-25 03:00:00.03' AND '2026-09-01 03:00:00.03')
   AND t_finance_refund.tenant = 'LKUS';
```

**10.2 收款对账明细查询**（每天 02:01 UTC，单次扫 126 万行返回 31 行）

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

**10.3 收款对账计数**（与 10.2 同一秒触发，单次扫 126 万行返回 1 行）

```sql
SELECT COUNT(*) AS total
  FROM t_finance_receipt
 WHERE deleted = 0
   AND (status = 1 AND checking_date BETWEEN '2026-08-25 02:01:35.818' AND '2026-09-01 02:01:35.818')
   AND t_finance_receipt.tenant = 'IQA2';
```

`checking_date` / `tenant` 均无索引；`t_finance_refund` 上的 `idx_checking_time_and_status`
是名字只差几个字母的近似索引，全部落空。10.2 的 `ORDER BY modify_time DESC + LIMIT 10000`
诱发 Backward index scan，倒着走完 136 万行索引只命中 31 行。

**优化建议**
1. 加两个索引（变更申请《变更申请_salesorder_财务对账索引_2026-09-01》已出，待审批）：

```sql
ALTER TABLE luckyus_sales_order.t_finance_receipt
  ADD INDEX idx_tenant_status_ckdate (tenant, status, deleted, checking_date),
  ALGORITHM=INPLACE, LOCK=NONE;

ALTER TABLE luckyus_sales_order.t_finance_refund
  ADD INDEX idx_tenant_ckstatus_ckdate (tenant, checking_status, deleted, checking_date),
  ALGORITHM=INPLACE, LOCK=NONE;
```

   `idx_tenant_status_ckdate` 一个索引同时解决 10.2 和 10.3。
2. 去掉「先 COUNT 再 SELECT」的分页写法 —— 结果集只有几十行，分页计数没有价值。
