# isalestradecapi P1「每分钟异常数大于5」(SocketTimeoutException) 研判报告

- 告警：【全局策略】服务器每分钟异常数大于5 / P1，service=`isalestradecapi`
- 时间：2026-08-19 14:10 → 14:32 EDT（18:10 → 18:32 UTC），异常全部为 `java.net.SocketTimeoutException`
- 调查人：DBA 曾翔宇，完成于 2026-08-19 19:30 UTC

---

## 一、结论

**不是数据库/缓存/节点故障，DBA 侧全部指标健康。**

根因链：
`iriskcontrolservice` 的 **单个 Pod（`...-5c846bf6cd-tblvn` / 10.238.42.255）所有接口被固定卡在 ~6.35–6.40 秒**
→ 约一半风控调用走到这个 Pod
→ `isalestradecapi` 调风控的 HTTP 读超时被打爆 → `java.net.SocketTimeoutException`
→ 触发 tradecapi 的 P1/P0 异常数告警（同窗口 iriskcontrolservice 自身也报 P0）。

**卡住的对象几乎可以确定是该 Pod 到自己 Redis（`luckyus-iriskcontrol`）的客户端连接**，
不是 Redis 服务端：服务端侧看到的是「命令直接不来了」，而不是「命令变慢」。

> ✅ **已恢复（19:27 UTC / 15:27 EDT）**：风控 Deployment 被**手动滚动重启**
> （annotation `kubectl.kubernetes.io/restartedAt: 2026-08-19T19:27:36Z`，镜像版本未变，仍为 v26.8.1，
> 即重启而非回滚）。新 Pod `...-556d5674bf-mc7nt`(10.238.41.61) / `...-btbp4`(10.238.41.248)。
> 重启后：风控全部 HTTP 接口恢复调用（/risk/order/create 7–8 cpm、/risk/pay/orderPay 7 cpm 等）、
> 响应时间回到 23–71 ms、Redis 命令数 19:30 起恢复（484 → 713 → 815 次/5min，接近同时段基线）、
> Redis 连接数回到 31、tradecapi SLA 回到 100%、异常降至 2 个/分钟（阈值 5）。
> 期间新增告警仅 iriskcontrolservice 两条 P2「YGC 耗时大于3000毫秒」（19:29、19:31，各 4 分钟自愈）——
> 属新 JVM 启动预热，与 8/18 上次发版时同型。
>
> ⚠️ 代价：**旧 Pod 已被删除，thread dump / jstack 现场丢失**，6.35s 阻塞点无法再从进程侧坐实；
> 若复发，请在重启前先取栈。
>
> 18:40–19:27 UTC（14:40–15:27 EDT）这 47 分钟内，风控 HTTP 调用量为 0、Redis 命令为 0，
> 下单/支付链路的风控校验实际未执行 —— 需风控/交易团队确认当时是人工降级还是熔断未回落。

---

## 二、时间线（EDT / UTC）

| EDT | UTC | 事件 |
|---|---|---|
| 14:00 | 18:00 | 风控 Redis 连接数 32 → 35；tblvn Pod 响应时间仍 31ms |
| 14:05 | 18:05 | tblvn Pod 响应时间跳到 **6368ms**（兄弟 Pod 仍 15ms） |
| 14:08 | 18:08 | tradecapi 与 iriskcontrolservice **同时**开始异常爆发；Zeus 同分钟触发两条告警（tradecapi P1 #6520、iriskcontrol P0 #6521） |
| 14:10 | 18:10 | 风控 Redis `GetTypeCmds` 1227 → **426**（≈ 掉了坏 Pod 那一半）；本次 P1 告警 #6524 触发 |
| 14:10–14:36 | 18:10–18:36 | tradecapi 异常 6→28 个/分钟，两次冲破 P0 阈值（>20）；tradecapi SLA 100% → **96.07%**；两个 Pod 同等下降 |
| 14:35 | 18:35 | 风控 Redis 连接 35 → **24**，命令数 140 |
| 14:36–14:40 | 18:36–18:40 | 风控 HTTP 接口调用归零、Redis 命令归零；告警陆续 RESOLVED（14:37 / 14:39） |
| 14:40–15:27 | 18:40–19:27 | 风控 HTTP 调用与 Redis 命令持续为 0（47 分钟，风控校验未执行） |
| 15:27 | 19:27 | 风控 Deployment 手动滚动重启（同版本 v26.8.1），新 Pod 起来 |
| 15:30–15:45 | 19:30–19:45 | Redis 命令、风控接口、tradecapi SLA 全部恢复正常 → **本次事件闭环** |

---

## 三、证据

### 1) 故障定位在单个风控 Pod（`service_instance_resp_time`，APM `victoriametrics-apm-us`）

| Pod | 18:00 前 | 18:05–18:35 |
|---|---|---|
| 10.238.40.108（b2q26） | 14–38 ms | **14–38 ms（正常）** |
| 10.238.42.255（tblvn） | 16–31 ms | **6349 / 6364 / 6365 / 6369 / 6379 ms** |

- 全 fleet 扫描：窗口内响应时间 >1.5s 的实例只有 10.238.42.255（6.4s）一个是数量级异常。
- 该 Pod **所有** endpoint 都被顶到同一水平（register 6402 / cancel 6394 / orderPay 6391 / create 6388 / validate 6380 / login 6373 ms）——**共用阻塞点**特征，不是某个接口的业务变慢。
- SLA 全程 10000（100%）：请求最终**成功返回**，只是每个都白等 ~6.35s（说明有兜底/降级路径）。
- ~6.35s 与常见 Redis 客户端「重试×间隔 + 命令超时」的总预算（如 Redisson 默认 3×1500ms + 3000ms ≈ 6s）高度吻合，建议应用侧按此核对配置。

### 2) 受影响的是 tradecapi 调风控的那几个接口（`endpoint_fcpm` 峰值）

`POST:/resource/pay/toPay` 10 · `POST:/resource/isalestradecapi/order/create` 7 ·
`POST:/resource/isalestradecapi/base/validCode` 5 · `POST:/resource/isalestradecapi/orderOperate/cancel` 1

与风控侧 `/risk/pay/orderPay`、`/risk/order/create`、`/risk/general/validate`、`/risk/order/cancel` 一一对应。
tradecapi 两个 Pod（10.238.35.249、10.238.39.91）SLA 同步下降 → 问题在下游，不在 tradecapi 自身。

### 3) Redis 服务端健康，但"命令不来了"（`luckyus-iriskcontrol-001`，cache.t4g.micro，us-east-1b 主）

| 指标 | 结果 |
|---|---|
| EngineCPUUtilization | 0.35–0.50%（无压力） |
| StringBasedCmdsLatency | 3.6–4.1 **微秒**（服务端没变慢） |
| CPUCreditBalance | 288 恒定（无积分耗尽） |
| ElastiCache events（16:00–19:30） | **无**（无 failover、无维护） |
| CurrConnections | 32 → 35（18:00）→ **24**（18:35 起） |
| GetTypeCmds / 5min | 1227 → **426**(18:10) → 140(18:35) → **0**(18:40 起) |
| 副本 -002 | 全程 0 命令（流量未切到副本） |
| 昨日同时段(18:00–19:00 UTC) | 1.3 万次/小时；今日 19:00 = **0** |

服务端延迟正常、命令量骤降 = **客户端发不出/收不到**，而非服务端慢。

### 4) 其他 DBA 侧对象全部健康

- RDS `aws-luckyus-iriskcontrolservice-rw`（db.t4g.medium，MySQL 8.4.9）：CPU 5.5–8.8%、连接 10–12、ReadLatency≈0、EBSByteBalance% 99–100、CPUCreditBalance 576 恒定。
- 宿主节点 `ip-10-238-12-183`（m6i.8xlarge，us-east-1a）：CPUUtilization 全程 2.6–2.9%。
- 容器：CPU 用量 0.03 核（limit 1 核）、CFS 限流 ≈0.005–0.026 s/s（可忽略）→ **不是 GC / 不是 CPU 争抢**，是纯等待。
- Pod `restartCount = 0`，自 2026-08-18 08:45 UTC 起未重启（本次全程未重启，自"恢复"）。
- Doris(`idorisjdbc`)、Kafka 调用量全程平稳，未受影响。

### 5) 业务影响

- tradecapi 约 **30 分钟内 ~2–4% 调用失败**（SLA 最低 96.07%），失败集中在下单、支付、验证码。
- 订单量对比昨日同窗口无明显损失（18:10 桶 69 vs 70、18:20 桶 90 vs 91、18:30 桶 112 vs 93），推测客户端重试吸收了大部分失败。
- 同窗口连带告警：`isalescrmservice`(P1×2)、`isalesmarketingservice`(P1×2/P2)、`iriskcontrolservice`(P0)，均为同一根因的下游计数。
- 5 条告警 `alert_upgrade_status=UPGRADED`（无人认领导致自动提级）。

---

## 四、待办与建议

| 优先级 | 事项 | 责任方 |
|---|---|---|
| **P1** | 复盘 18:40–19:27 这 47 分钟风控调用归零的性质（人工降级 / 熔断未回落），并明确该状态是否应产生告警 | 风控 @桂胜斌 @赵旭 @林洪鹏 + 交易 @王鑫 @张晓松 @李加彬 |
| P1 | ~~取 thread dump~~ 现场已随 19:27 重启丢失；**复发时务必先 jstack 再重启**，确认 6.35s 阻塞在哪个客户端 | 风控团队 |
| P1 | 核对风控 Redis 客户端配置：命令超时 + 重试预算（≈6s 过长）、`keepAlive`/连接健康检查、失败快速降级 | 风控团队 |
| P1 | tradecapi 侧调风控的 HTTP 读超时 + 熔断/降级：单个下游慢 Pod 不应外溢成用户可见失败 | 交易团队 |
| P2 | 监控补齐（DBA）：① 同服务实例间响应时间偏离告警（本次一个 Pod 是兄弟 Pod 的 200 倍，无告警）；② 关键 Redis「命令数长时间为 0」告警（缓存被静默停用无人知） | DBA |

## 五、本次调查的盲点

- 应用日志取不到：`databasecheck` 在 luckyur-log OpenSearch 被 FGAC 拒（403），EKS `get_pod_logs` 未开 `--allow-sensitive-data-access`。因此**风控 Pod 内部的原始异常栈未取到**，"卡在 Redis 客户端"是由「服务端命令量骤降 + 时间吻合 + 全接口同值阻塞 + CPU 全程空闲」推出的强推断，非日志坐实。
- Zeus `t_alert` 不落异常名维度（`alert_target.ex_name = ALL`），风控侧异常类型需从 izeus 控制台看。

参考：Zeus 告警 id 6520/6521/6524/6527/6530/6531（`luckyus_izeus.t_alert`@aws-luckyus-devops-rw）


---

## 六、恢复确认（2026-08-19 19:45 UTC 复核）

| 项 | 事件中 | 现在 |
|---|---|---|
| 风控 Pod 响应时间 | 6349–6402 ms（单 Pod） | 23–71 ms（两个新 Pod） |
| 风控 HTTP 接口调用 | 18:40 起为 0 | 已恢复（order/create 7–8 cpm、pay/orderPay 7 cpm） |
| 风控 Redis 命令/5min | 0 | 484 → 713 → 815（接近基线） |
| Redis 连接数 | 24 | 31 |
| tradecapi SLA | 最低 96.07% | 100%（偶发 99.5% 噪声） |
| tradecapi 异常/分钟 | 峰值 28 | 2（阈值 5） |
| 恢复动作 | — | 19:27:36 UTC 手动滚动重启（同版本，非回滚） |
