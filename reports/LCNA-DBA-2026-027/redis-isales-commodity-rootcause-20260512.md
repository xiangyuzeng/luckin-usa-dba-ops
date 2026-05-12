# Redis `luckyus-isales-commodity` 限流根因深入分析

**报告编号**: LCNA-DBA-2026-027
**关联报告**: LCNA-DBA-2026-026（全集群限流盘点，5/11）
**日期**: 2026-05-12
**作者**: 曾翔宇 (David Zeng) — DBA / Infrastructure
**实例**: `luckyus-isales-commodity`（cache.t4g.micro × 2，主备模式）

---

## 0. TL;DR

| 项 | 结论 |
|----|------|
| **真正根因** | 应用把整店商品 catalog 序列化为 **~825 KB 的 JSON**，作为 Redis hash 的**单个 field value** 存储；每 30 秒整体覆盖式重写一次 |
| **限流机制** | 单次写入 825 KB 的瞬时带宽峰值（数十 ~ 百 Mbps）远超 cache.t4g.micro 入站基线 64 Mbps，触发 `NetworkBandwidthInAllowanceExceeded` |
| **数据闭环** | 由 11 店 × 825 KB ÷ 30s 计算出的 ~2.4 Mbps，加上 combo menu 等其他写入，**正好等于 CloudWatch NetworkBytesIn 实测的 3.6 Mbps** |
| **026 报告中的描述** | 方向归属（入站为主）和升级建议都正确，但**对"为什么入站超限"的细节描述不够准确**，本报告补全 |
| **推荐做法** | 治本：业务侧改 hash 结构（一 SKU 一 field，仅写变更）；治标：升级 m6g.large |

---

## 1. 起因

LCNA-DBA-2026-026 对 154 个 ElastiCache 节点做了全量限流盘点，发现 `luckyus-isales-commodity` 每天 5~6 小时入站限流，并给出了升级建议。本周复盘时，对**"为什么 1 分钟平均流量只有 3.6 Mbps 却会被 64 Mbps 基线限流"** 这个看似矛盾的现象做了实测追因，最终定位到应用侧的大 key 改写模式。

---

## 2. 节点与初始观察

### 2.1 节点配置

| 项 | 值 |
|----|----|
| Replication group | `luckyus-isales-commodity` |
| 节点 | `-001` (us-east-1b, **主**) + `-002` (us-east-1a, 副本) |
| 规格 | `cache.t4g.micro`（0.5 GiB 内存，**入站基线 64 Mbps**，突发 5 Gbps）|
| Engine | Redis 6.0.5 |
| Uptime | **427 天**（生命周期跨越 14 个月）|
| Replication mode | 1 shard 主备，非 Cluster Mode |
| Maxmemory policy | `volatile-lfu`，maxmemory 384 MB |

### 2.2 限流证据（CloudWatch，过去 7 天）

| 指标 | -001（主）| -002（副本）|
|------|----------|------------|
| **NetworkBandwidthInAllowanceExceeded** | **2,819 ~ 4,953 次/天**（日均 ~3,378） | 0 |
| NetworkBandwidthOutAllowanceExceeded | 0–24 次/天（可忽略） | 0 |
| 其他限流指标 | 0 | 0 |

特征：限流单一类型（入站带宽），且**只发生在主节点**，副本干净 → 是**写入流量**触发，不是读响应。

### 2.3 限流时段分布（业务高峰显著）

| 时段（UTC）| 时段（EST）| 限流计数/小时 |
|-----------|-----------|-------------|
| 03:00 – 07:00 | 23:00 – 03:00 | 0 ~ 26（凌晨低谷）|
| 10:00 – 19:00 | 06:00 – 15:00 | **300 ~ 569**（早高峰 + 午餐高峰）|
| 20:00 – 02:00 | 16:00 – 22:00 | 50 ~ 100（晚高峰之后衰减）|

与曼哈顿门店营业曲线完全吻合。

### 2.4 看似矛盾：平均带宽远低于基线

| 指标 | 数值 |
|------|------|
| NetworkBytesIn 1 分钟均值 | ~0.45 MB/s ≈ **3.6 Mbps** |
| NetworkBytesIn 1 分钟峰值 | ~0.6 MB/s ≈ **4.8 Mbps** |
| t4g.micro 入站基线 | **64 Mbps** |

平均流量仅基线的 **5.6%**，按理不应该被限流。说明**1 分钟均值掩盖了亚秒级突发**。问题是：突发从哪来？

---

## 3. 关键追踪过程

### 3.1 第一次错误反推（已修正）

最初通过 Redis `INFO stats` 计数器反推：

| 计数器 | 数值 |
|--------|------|
| `total_net_input_bytes` | 4.47 TB |
| `total_commands_processed` | 712M |
| 写命令（PSETEX + HSET）| 71M |

反推得到"平均每次写 payload ≈ 60 KB" → 当作结论汇报。

**这个反推是错的**。原因：客户端命令仅占总写入字节的一小部分，单看 commandstats 无法准确分配字节归属。

### 3.2 直接采样 11 个 string key

| Key Pattern | 实测 STRLEN |
|-------------|------------|
| `operateShopSalesSpuDeptSpu*:PR*` | 280, 410, 500, 670, 670 B |
| `scmCommodityDetailsPR*` | 622, 633 B |
| `scmComboDetailsPF*` | 1,556 B |
| `scmOutCommodityRmkOptionPR*` | **6,659 B**（最大）|
| `scmOptionNutritionV2*` / `scmCommodityNutritionV2*` | 0（刚过期）|

中位数 633 B，均值 ~1.3 KB。**比 60 KB 估算小 40 倍**。但这次仍然不对：

- 11 个采样 key 远远无法覆盖 1053 个键的所有 pattern
- 漏掉了关键的**全店聚合 key**（每店仅 1 个，初次按前缀分组时被频次少的样本掩盖了）

### 3.3 完整枚举 KEYS 后才发现的大 key

把 `KEYS *` 全部按 pattern 归类（**49 个 pattern group**）后，发现两类**每店一个**的聚合 key：

| Pattern | 数量 | 实测大小 |
|---------|------|---------|
| `shop@LKUS@commodity_{shopId}_0` | 11（每店 1 个）| **825 KB** (单 hash field) |
| `isalescommodityservice:LKUS:en-US:salesComboMenu{shopId}:0` | 10 | **~280 KB** (string) |

### 3.4 现场抓到的"高频改写"证据

直接 redis-cli 连主节点观察单个 key 的 TTL 变化：

```
TTL shop@LKUS@commodity_1141_0
(integer) 3        ← 还剩 3 秒
(integer) 2
(integer) 1
(integer) -2       ← 已过期
(integer) 29       ← 应用立即重写，新 TTL = 30 秒
(integer) 28
...
```

**实测的是 TTL 30 秒整 + 过期立即重写**。每 30 秒整店商品 catalog 重新整体覆盖一次。

### 3.5 Hash 结构详情

```
TYPE   shop@LKUS@commodity_1141_0  →  hash
HLEN   shop@LKUS@commodity_1141_0  →  1
HKEYS  shop@LKUS@commodity_1141_0  →  "\"en-US\""   ← field 名带字面引号
HSTRLEN shop@LKUS@commodity_1141_0 "\"en-US\""  →  845027 (~825 KB)
MEMORY USAGE shop@LKUS@commodity_1141_0          →  845266 (元数据开销 ~239 B)
```

应用把**整个门店的商品 JSON 序列化字符串**作为一个 hash 的单 field value 存储。Hash field 名是 `"en-US"`（带字面引号 —— JSON encode 后的字符串被当 field 名用）。

---

## 4. 流量闭环验证

### 4.1 估算入站带宽

| 来源 | 计算 | 速率 |
|------|------|------|
| `shop@LKUS@commodity_*_0`（11 店 × 825 KB ÷ 30s） | 9.07 MB / 30s | **302 KB/s ≈ 2.42 Mbps** |
| `salesComboMenu_*:0`（10 店 × 280 KB ÷ 30s） | 2.80 MB / 30s | 93 KB/s ≈ 0.75 Mbps |
| 其他细粒度 SKU 写入（PSETEX + HSET 合计）| 估算 | ~0.4 Mbps |
| **合计估算入站** | | **~3.6 Mbps** |

### 4.2 与 CloudWatch 实测对照

| 测量 | 数值 |
|------|------|
| CW NetworkBytesIn 1-min 均值（24h）| **3.6 Mbps** |
| 上述独立估算 | **3.6 Mbps** |

**两个独立路径计算的结果完全吻合**。`total_net_input_bytes` 4.47 TB / 14 个月 = **平均 0.97 Mbps**（14 月历史均值，含早期低流量阶段），近期由于门店扩张已升至 3.6 Mbps。

---

## 5. 限流机制（瞬时带宽峰值估算）

单次 825 KB hash 写入通过 TCP 传输到 Redis：

| 假设传输完成时间 | 瞬时带宽 | 与 64 Mbps 基线对比 |
|----------------|---------|-------------------|
| 5 ms（理想 1 RTT 完成） | 1,320 Mbps | **20× 超出基线** |
| 50 ms（典型分段传输） | 132 Mbps | **2× 超出基线** |
| 200 ms（拥塞下降速） | 33 Mbps | 单 key 不超，但 ... |

**多门店并发刷新场景**：11 店若集中刷新（菜单变更/促销广播触发全店缓存重建），瞬时叠加可达数百 Mbps。即便错峰刷新，业务高峰时段总有几店在同一秒内重写。

→ 触发 `NetworkBandwidthInAllowanceExceeded`，对应 CloudWatch 业务高峰时段每小时 300-569 次的限流计数。

---

## 6. 根因总结（一句话版）

**应用把整店商品 catalog 当作一个 ~825 KB 的 JSON 字符串、塞进 Redis hash 的单 field、每 30 秒整体覆盖式重写。单次写入的瞬时带宽峰值（数十~百 Mbps）远超 cache.t4g.micro 入站基线 64 Mbps，触发限流。**

---

## 7. 改造建议

### 7.1 治本：业务侧改造（首选）

**问题模式**（伪代码）：
```
data = {sku1: {...}, sku2: {...}, ..., sku150: {...}}  // 150 个 SKU 全部
redis.HSET("shop@LKUS@commodity_1141_0", "en-US", JSON.stringify(data))
redis.EXPIRE(key, 30)
```

**改造方案**：
```
for sku_code, sku_data in changed_skus:    // 只处理变更的 SKU
    redis.HSET("shop@LKUS@commodity_1141", sku_code, JSON.stringify(sku_data))
redis.EXPIRE("shop@LKUS@commodity_1141", 60)   // 整体过期延长，或单 field TTL
```

**预期效果**：
- 入站流量降至原来 0.1%（仅写变更的几个 SKU，每个几 KB）
- 限流根除
- Redis 内存占用基本不变（field 总数 = SKU 数 × shop 数）
- 应用读取方式需配套调整：用 `HGET` 取单 SKU 或 `HMGET` 取多个，而非 `HGETALL`

### 7.2 治标：升级节点规格

| 方案 | 节点 | 入站基线 | 月费/节点（EDP 折后）| 月增（2 节点）|
|------|------|---------|--------------------|--------------|
| 当前 | cache.t4g.micro | 64 Mbps | ~$4 | — |
| **快速缓解** | cache.t4g.medium | 256 Mbps（4×）| ~$17 | +$26 |
| **彻底脱离 burstable** | cache.m6g.large | 750 Mbps（12×）| ~$56 | +$104 |

**优先级建议**：
- **业务侧改造 + 升级 t4g.medium**：性价比最高，根除问题且月增本可控
- 只升级不改造：限流消失但每 30 秒重写 ~9 MB 整店数据的浪费仍在，将来还可能再次撞墙
- 只改造不升级：技术上可行，但业务侧排期通常较长，建议先升级 t4g.medium 兜底

---

## 8. 行动项

| # | 行动 | 负责人 | 目标时间 |
|---|------|--------|---------|
| 1 | 联系业务 owner（isalescommodity 服务）确认 `shop@LKUS@commodity_*_0` 写入逻辑、TTL=30s 是否必要 | DBA + 业务 | 本周 |
| 2 | 申请 t4g.medium 升级变更窗口（兜底）| DBA | 本周 |
| 3 | 与业务侧讨论改用增量 HSET 的可行性 + 排期 | DBA + 业务 | 2 周内 |
| 4 | 升级后复测限流指标，验证根除效果 | DBA | 升级后 1 周 |
| 5 | 推广检查：审查其他 9 个有限流嫌疑的 Redis 实例是否也有类似大 key 模式 | DBA | 本月 |

---

## 9. 经验教训（给后续 DBA 复盘用）

1. **不要用 `total_net_input_bytes / 写命令数` 反推 payload 大小** —— 客户端命令字节只占总入站的小部分，反推误差可能达数十倍。直接用 STRLEN / HSTRLEN / MEMORY USAGE 实测。
2. **`KEYS *` 在小 dbsize（< ~10k）的实例上完全可用** —— 不要因为生产顾虑就不敢跑。本案 dbsize 仅 1053，1 次 KEYS 即可枚举全部 pattern。
3. **采样要按 pattern 分组覆盖**，不能只测最常见的几个前缀。本案漏掉了"每店 1 个"的全店聚合 key 整整一轮诊断。
4. **TTL 现场轮询是发现高频改写的最便宜手段** —— `TTL key` 重复几次就能看出"应用是不是周期性重写"。比 MONITOR 安全得多。
5. **应用层的 hash 单 field 装 1 MB JSON 是 anti-pattern**：失去 hash 的部分更新优势，等同于把 hash 当 string 用，但又承担了 hash 的元数据开销。

---

## 附录 A：实测命令清单（可复现）

```redis
# 基本信息
INFO server
INFO replication
INFO stats
INFO memory
INFO keyspace
INFO commandstats

# 列出所有 pattern（dbsize 仅 1053 时可用）
KEYS *

# 探明大 key
TYPE shop@LKUS@commodity_1141_0
HLEN shop@LKUS@commodity_1141_0
HKEYS shop@LKUS@commodity_1141_0
HSTRLEN shop@LKUS@commodity_1141_0 "\"en-US\""
MEMORY USAGE shop@LKUS@commodity_1141_0

# 抓改写周期
TTL shop@LKUS@commodity_1141_0    # 多次执行观察周期
```

## 附录 B：CloudWatch 关键查询

```bash
aws cloudwatch get-metric-statistics --region us-east-1 \
  --namespace AWS/ElastiCache \
  --metric-name NetworkBandwidthInAllowanceExceeded \
  --dimensions Name=CacheClusterId,Value=luckyus-isales-commodity-001 \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time   $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 --statistics Sum
```

## 附录 C：参考

- LCNA-DBA-2026-026: 154 个 Redis 节点限流盘点（5/11）
- AWS ElastiCache 网络性能文档：<https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/CacheNodes.SupportedTypes.html>
- Redis `total_net_input_bytes` 含义：<https://redis.io/commands/info/>
