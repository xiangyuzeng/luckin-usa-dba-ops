# Communication Templates

## Slack Message to iSales Marketing Dev Team

### English Version

---

**:rotating_light: [ACTION REQUIRED] Redis Memory Alert — `luckyus-isales-market` — TTL Policy Changes Needed**

Hi iSales Marketing team,

**What happened:**
Today (2026-02-12, ~14:00 UTC) the Redis cluster `luckyus-isales-market` hit **87.5% memory usage** (2.10G / 2.32G maxmemory), triggering a critical memory alert. Memory has since recovered to ~85% as short-TTL burst keys expired, but the **underlying issue remains unresolved**.

**Root Cause:**
**2,623,984 keys (39.2% of all keys) have NO TTL** — they never expire and cannot be evicted under our current `volatile-lfu` eviction policy. This number grows monotonically as new users/campaigns are created, leaving progressively less headroom for transient workloads.

**Key patterns that need TTL in application code:**

| Key Pattern | Current Count | Current TTL | Proposed TTL | Priority |
|-------------|---------------|-------------|-------------|----------|
| `MARKETING:COUPON:UNREAD:{userId}` | 147,111 | **None (never expires)** | **60 days** | P1 |
| `contact:userGroupLabel:set:{groupId}` | 177,450 | **None (never expires)** | **30 days** | P1 |
| `exchange:coupon:high:commodity:price:{id}` | 473 | **None (never expires)** | **7 days** | P2 |
| `contact:last:activity:{contactId}` | 374,639 | ~364 days | **90 days** | P2 |

**What SRE will do (immediate):**
- We will run one-time TTL remediation scripts to set TTL on existing keys (after your sign-off)
- Deploy enhanced monitoring (60% warning threshold, no-TTL ratio tracking)

**What we need from you:**
1. **Review the proposed TTLs above** — confirm they are acceptable for your business logic
2. **Update application code** to include TTL when creating these keys:
   - Use `EXPIRE` or set TTL at write time (e.g., `SET key value EX 5184000` or `client.expire(key, 2592000)`)
3. **Identify the burst source** — around 13:57 UTC today, something generated ~5.2M numeric keys in ~20 minutes. Was this a marketing campaign trigger? A batch job? Please check your deployment and cron schedules.
4. **Target timeline:** Application code changes within **1 sprint (2 weeks)**

**If no action is taken**, memory incidents will become more frequent and eventually lead to cache evictions (data loss) or require expensive node scaling (+$135/month).

Please reply in this thread or DM me to discuss. Happy to jump on a quick call.

cc: @sre-oncall @isales-marketing-lead

---

### Chinese Version / 中文版

---

**:rotating_light: [需要处理] Redis 内存告警 — `luckyus-isales-market` — 需要添加 TTL 策略**

iSales 营销团队大家好，

**事件概要：**
今天（2026-02-12，约 UTC 14:00）Redis 集群 `luckyus-isales-market` 内存使用率飙升至 **87.5%**（2.10G / 2.32G 最大内存），触发了内存严重告警。随着短 TTL 突发键的过期，内存已回落至约 85%，但**根本问题尚未解决**。

**根本原因：**
**2,623,984 个键（占所有键的 39.2%）没有设置 TTL** — 它们永远不会过期，在当前的 `volatile-lfu` 淘汰策略下无法被清除。随着新用户/活动的创建，这个数字只增不减，导致可用内存空间越来越少。

**需要在应用代码中添加 TTL 的键模式：**

| 键模式 | 当前数量 | 当前 TTL | 建议 TTL | 优先级 |
|--------|---------|---------|---------|--------|
| `MARKETING:COUPON:UNREAD:{userId}` | 147,111 | **无（永不过期）** | **60 天** | P1 |
| `contact:userGroupLabel:set:{groupId}` | 177,450 | **无（永不过期）** | **30 天** | P1 |
| `exchange:coupon:high:commodity:price:{id}` | 473 | **无（永不过期）** | **7 天** | P2 |
| `contact:last:activity:{contactId}` | 374,639 | ~364 天 | **90 天** | P2 |

**SRE 团队将执行（立即）：**
- 在你们确认后，运行一次性 TTL 修复脚本为现有键设置 TTL
- 部署增强监控（60% 预警阈值、无 TTL 键占比追踪）

**需要你们配合的事项：**
1. **审核上述建议的 TTL 值** — 确认是否符合业务逻辑需求
2. **修改应用代码**，在创建这些键时带上 TTL：
   - 使用 `EXPIRE` 命令或在写入时设置 TTL（例如 `SET key value EX 5184000` 或 `client.expire(key, 2592000)`）
3. **排查突发键来源** — 今天 UTC 13:57 左右，约 20 分钟内突然产生了约 520 万个纯数字键。是否有营销活动触发？定时任务执行？请检查你们的部署和定时任务日志
4. **目标时间线：** 应用代码修改在 **1 个迭代周期内（2 周）** 完成

**如果不采取措施**，内存告警将越来越频繁，最终导致缓存数据被淘汰（数据丢失）或者需要升级节点（每月增加约 $135 成本）。

请在此帖回复或私信我讨论，也可以随时拉个简短会议。

cc: @sre-oncall @isales-marketing-lead

---

## Email Subject Line (if needed)

**[P1] Redis Memory Alert — luckyus-isales-market — Application TTL Changes Required Within 2 Weeks**
