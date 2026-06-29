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

---
---

## 2026-06-29 Follow-up — `CONTACT_*` is now the dominant no-TTL family

> Send this as a NEW thread (not a reply to the Feb message). Tone: not an emergency,
> but a chronic problem that has worsened ~4× since Feb and needs a code-side fix.

### English Version

---

**:warning: [ACTION REQUIRED – not urgent] Redis `luckyus-isales-market` — legacy `CONTACT_*` keys have no TTL (~10.8M keys)**

Hi iSales team,

Following up on the Feb memory work. Good news first: **the cluster is healthy right now** — ~68% memory, **zero evictions**, no active alarm (it was scaled up since Feb, maxmemory is now 4.79G).

The bad news: the **no-TTL key problem has nearly quadrupled**. We re-audited today with statistical sampling (58,812 keys sampled, `SCAN`-based, no `KEYS`):

| | Feb 2026 | **Jun 2026** |
|---|---|---|
| Total keys | 6.66 M | **15.7 M** |
| Keys with NO TTL | 2.62 M (39%) | **~11.4 M (72.5%)** |

**Root cause — and it's mostly one thing:** **~95% of all no-TTL keys (~10.8M) are the legacy `CONTACT_*` frequency-control counters:**

| Key pattern | Est. count | Current TTL | Proposed TTL on write |
|-------------|-----------|-------------|------------------------|
| `CONTACT_day_{member}_{YYYY-MM-DD}_{n}` | **~9.06 M** | **None** | **14 days** |
| `CONTACT_{member}_{n}_{n}` (no date) | ~0.89 M | **None** | **30 days** |
| `CONTACT_week_{member}_{YYYY-MM-DD}_{n}` | ~0.61 M | **None** | **35 days** |
| `CONTACT_month_{member}_{YYYY-MM}_{n}` | ~0.24 M | **None** | **60 days** |
| `contact:userGroupLabel:set:{member}` | ~0.31 M | **None** | 30 days *(flagged in Feb — still unfixed?)* |
| `MARKETING:COUPON:UNREAD:{member}:coupon` | ~0.28 M | **None** | 60 days *(flagged in Feb — still unfixed?)* |

We can see your **newer** code already does this right — `contact:user:contacted:activity:one:day:*` (42h TTL), `user:activity:Category:FreqCtrl:*` (29d), and the `cfc:v2:*` namespace all carry TTLs. It's specifically the **old uppercase `CONTACT_*` writer** that never sets `EXPIRE`, so dated counters from as far back as 2025-12 are still sitting in RAM.

**What we need from you:**
1. **Set `EXPIRE` at write time** on `CONTACT_day/week/month/<member>` (TTLs above), **or** confirm these are fully superseded by `cfc:v2:*` and the legacy writer can be retired.
2. **Confirm the proposed TTLs** are safe for frequency-control logic (we assume only recent windows are ever read — please verify).
3. Re-confirm whether `contact:userGroupLabel:set` and `MARKETING:COUPON:UNREAD` got their Feb fixes — they're still showing no TTL.

**What SRE will do (after your sign-off):** run a **date-aware backfill** on the ~10.8M existing keys — recent dates get a rolling expiry, already-stale keys drain gradually over 6h–3d (no mass delete, no latency spike). Script is ready (`fix_ttl_contact_freq.py`, dry-run first).

No emergency, but until the code-side fix lands the no-TTL count keeps climbing and we lose eviction headroom. **Target: within 1 sprint (2 weeks).**

Reply here or DM me — happy to pair on the writer change.

cc: @sre-oncall @isales-marketing-lead

---

### Chinese Version / 中文版

---

**:warning: [需要处理 · 非紧急] Redis `luckyus-isales-market` — 旧版 `CONTACT_*` 键无 TTL(约 1080 万)**

iSales 团队大家好，

接 2 月内存治理的后续。先说好消息：**集群目前健康** —— 内存约 68%、**零淘汰**、无活跃告警(2 月之后已升配，maxmemory 现为 4.79G)。

坏消息：**无 TTL 键的问题几乎翻了两番**。今天用统计抽样重新审计(`SCAN` 采样 58,812 个 key,未用 `KEYS`):

| | 2026-02 | **2026-06** |
|---|---|---|
| 总 key 数 | 666 万 | **1570 万** |
| 无 TTL key | 262 万(39%) | **约 1140 万(72.5%)** |

**根因——而且高度集中:无 TTL key 的 ~95%(约 1080 万)是旧版 `CONTACT_*` 触达频控计数器:**

| 键模式 | 估算数量 | 当前 TTL | 建议写入时 TTL |
|--------|---------|---------|----------------|
| `CONTACT_day_{member}_{YYYY-MM-DD}_{n}` | **~906 万** | **无** | **14 天** |
| `CONTACT_{member}_{n}_{n}`(无日期) | ~89 万 | **无** | **30 天** |
| `CONTACT_week_{member}_{YYYY-MM-DD}_{n}` | ~61 万 | **无** | **35 天** |
| `CONTACT_month_{member}_{YYYY-MM}_{n}` | ~24 万 | **无** | **60 天** |
| `contact:userGroupLabel:set:{member}` | ~31 万 | **无** | 30 天 *(2 月已提过 — 仍未修?)* |
| `MARKETING:COUPON:UNREAD:{member}:coupon` | ~28 万 | **无** | 60 天 *(2 月已提过 — 仍未修?)* |

你们**较新的**代码其实已经做对了 —— `contact:user:contacted:activity:one:day:*`(TTL 42h)、`user:activity:Category:FreqCtrl:*`(29d)以及 `cfc:v2:*` 命名空间都带 TTL。问题只出在**旧版大写 `CONTACT_*` 的写入路径**从不设 `EXPIRE`,导致连 2025-12 的按天计数都还堆在内存里。

**需要你们配合：**
1. 在写入 `CONTACT_day/week/month/<member>` 时**加 `EXPIRE`**(TTL 见上),**或者**确认这些已被 `cfc:v2:*` 完全取代、旧写入逻辑可以下线。
2. **确认建议 TTL** 对频控逻辑安全(我们假设只会读近期窗口,请核实)。
3. 复核 `contact:userGroupLabel:set` 与 `MARKETING:COUPON:UNREAD` 的 2 月修复是否落地 —— 目前仍显示无 TTL。

**SRE 将执行(在你们确认后):** 对约 1080 万存量键做**按日期感知的回填** —— 近期日期滚动到期,已过期的在 6h–3d 内抖动渐进排空(不批量删除、不抖延迟)。脚本已就绪(`fix_ttl_contact_freq.py`,先 dry-run)。

非紧急,但在代码侧修复落地前,无 TTL 数量会持续上涨、淘汰余量被吃掉。**目标:1 个迭代周期内(2 周)。**

请在此回复或私信我,写入逻辑改动我可以一起结对。

cc: @sre-oncall @isales-marketing-lead

---

### Email Subject Line (2026-06-29)

**[P2 · chronic] Redis luckyus-isales-market — legacy CONTACT_\* keys need write-time TTL (~10.8M no-TTL keys)**
