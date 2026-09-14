# iluckydpbi03 宕机无告警 — 证据包与结论修正（2026-09-11 复核）

对 2026-09-09 结论中「`up{job="node-metrics", instance="10.238.65.5:10087"}` 17 小时窗口内持续为 0」
这一条的质疑**成立**。本文给出复核过程、替代证据，以及修正后的（更强的）结论。

---

## 一、被质疑的那条：事实核对

**原表述**：`up{job="node-metrics", instance="10.238.65.5:10087"}` 整个 17 小时窗口持续为 0。
**复核结论**：数值为真，但**不能作为「主机在 10:45 宕机」的证据** —— 因为它在窗口之外也一直是 0。

| 查询 | 结果 |
|---|---|
| `up{instance="10.238.65.5:10087"}`（09-07 08:00 → 09-08 06:00，step 30m） | 45 个点**全部为 0**，含崩溃前 2h45m 与恢复后 2h15m |
| `up{instance="10.238.65.5:10087"}`（09-01 → 09-11，step 6h） | 41 个点**全部为 0** |
| `max_over_time(up{instance="10.238.65.5:10087"}[30d])` | **0** |
| `count(node_time_seconds{instance="10.238.65.5:10087"})` | **空（无任何 node_exporter 指标）** |

也就是说：**这台主机的 node_exporter 目标在可查询的 30 天内从未成功采集过一次**。
`up=0` 是该目标的常态，与 09-07 的宕机无关。拿它当宕机证据不成立，质疑者是对的。

> 附带数据质量问题：该 instance 有**两条重复 up 序列**，仅 `env` 标签不同
> （`env="PROD"` 与 `env="Luckin-PROD"`），其余标签完全一致。

---

## 二、替代证据：AWS EC2 状态检查（独立于 Prometheus，团队无法配置或篡改）

`i-04b4ad1b0469397da` / `AWS/EC2` / `StatusCheckFailed_Instance`，1 分钟粒度：

| 时刻 (UTC) | 值 | 含义 |
|---|---|---|
| 09-07 10:30 – 10:44 | **0**（连续 15 个点） | 正常 |
| **09-07 10:45** | **0 → 1** | 故障起点，与人工判定的 10:45 **精确吻合** |
| 09-07 10:45 – 09-08 03:44 | **1**（全程，1h 聚合 18 个桶全为 1.0） | 持续故障 17h |
| **09-08 03:45** | **1 → 0** | 恢复，与 Console 重启时刻吻合 |
| 09-08 03:45 – 05:59 | **0** | 恢复后正常 |

同期 `StatusCheckFailed_System` **全程 0** → AWS 底层硬件/网络正常，**故障在实例 OS 层**。

佐证（同一实例，2h 平均）：

| 时段 (UTC) | NetworkOut (B/s) | CPUUtilization |
|---|---|---|
| 09-07 08:00 | 201,002 | 5.66% |
| 09-07 10:00 | 2,022 | 37.32%（崩溃瞬间冲高）|
| 09-07 12:00 → 09-08 00:00 | **0**（连续 7 个桶，14 小时） | **2.07–2.15% 恒定** |
| 09-08 02:00 | 99,901 | 6.28% |

**CPU 恒定 2.1% 而 NetworkOut 严格为 0**，正是「内核还在跑、userspace/TCP 全死」的特征 ——
这反而**独立佐证了「半死」判断**（ICMP 由内核应答所以仍通，TCP 连接全部不可建立）。

---

## 三、#66 不触发的原因：不受本次修正影响

`up{job="node-ping-iprod", instance="10.238.65.5"}` 在 09-07 08:00 → 09-08 06:00 **全程为 1**（23 个点）。

#66 要求 `probe_success + up == 0`，即两路探活**同时**为 0。ICMP 全程为 1 ⇒ 和恒 ≥1 ⇒ **永不触发**。
这条判定不依赖「up 是因为宕机才变 0」，所以原结论成立，无需修改。

---

## 四、#76 的排除名单：问题比原结论更严重

原结论说排除名单「应该是当初为了避免允许计划性启停的机器误报而加的」。**这个推测是错的。**

全 fleet 扫描 `job="node-metrics"`（2026-09-11）：

- 总 instance 数：**229**
- `max_over_time(up[7d]) == 0`（≥7 天持续为 0，即长期死目标）：**11**

这 11 个是：

| service | instance | endpoint |
|---|---|---|
| idoris ×8 | 10.238.66.109 / .111 / .140 / .242、10.238.67.68 / .229 / .235 / .240 | ip-10-238-66-*.ec2.internal 等 |
| isslvpn | 10.238.3.180 | luckysslvpn01-prod-usa-aws |
| idpcd | 10.238.62.84 | idpcd01-ngress-elb-prod-usa-aws（**这是 NLB 的 ENI，不是主机**）|
| iluckydpbi | **10.238.65.5** | **iluckydpbi03-prod-usa-aws** |

#76 的排除正则是 `isslvpn|nclbvip|idoris|idpcd|lfetools|iluckydpbi`。
**11 个长期死目标的 service 全部落在这个排除名单内，无一例外。**

所以排除名单的真实成因是：**这些目标的 node_exporter 长期不可采集，`up` 恒为 0，
不排除就会 7×24 不停报 P0**。排除是为了消掉**永久性坏目标**的噪声，不是为了计划性启停。

这比原结论更严重：

1. `iluckydpbi` 被排除，不是「17 小时没被覆盖」，而是**这台机器从来就不在 up 宕机检测范围内，且其 node_exporter 本身也是坏的** —— 即使把排除名单去掉，`up` 也早就恒为 0，#76 会一直报而不是在 10:45 才报，**等于没有宕机检测能力**。
2. 同样处境的还有 **8 台 idoris**（Doris 集群）和 1 台 isslvpn —— 它们**全部没有主机宕机告警**，且全部没有可用的 OS 级指标。
3. `idpcd` 那条（10.238.62.84）是 NLB 的 ENI 被错当主机纳管，本就不该有 node_exporter，
   参见此前结论：它还会反向造成 vm-宕机误报。

---

## 五、回应质疑的建议说法

> 「`up` 那条我收回：复核发现 `max_over_time(up{instance="10.238.65.5:10087"}[30d]) = 0`，
> 这台机器的 node_exporter 目标在 30 天内从未采集成功过，`up=0` 是常态而不是宕机信号，
> 用它当 17 小时宕机的证据不成立。
>
> 宕机事实改用 AWS 侧证据：`StatusCheckFailed_Instance` 在 09-07 10:45 由 0 变 1、
> 09-08 03:45 由 1 变 0，1 分钟粒度可精确对齐，期间 `StatusCheckFailed_System` 全程 0
> （AWS 底层正常、实例 OS 故障）；`NetworkOut` 连续 14 小时严格为 0 而 CPU 恒定 2.1%。
> 这些指标由 AWS 产生，不经过我们的 Prometheus。
>
> 而且这次复核让问题变大了：全 fleet 229 个 node-metrics 目标里有 11 个 `up` 已连续 ≥7 天为 0，
> 它们的 service 恰好**全部**在 #76 的排除正则里。排除名单不是为计划性启停设的，
> 是为了压掉长期坏目标的噪声。所以 iluckydpbi03 的问题不是『17 小时没覆盖』，
> 而是『它和另外 10 个目标一样，长期既无 OS 指标也无宕机告警』。」

---

## 六、复现命令（对方可自行验证）

Grafana 数据源 `victoriametrics-basic-us`（uid `ZBv6_UeHz`）：

```promql
# 1. up 恒为 0，不是宕机才变 0
max_over_time(up{instance="10.238.65.5:10087"}[30d])            # → 0
count(node_time_seconds{instance="10.238.65.5:10087"})          # → 空

# 2. ICMP 全程可达（#66 永不触发的原因）
up{job="node-ping-iprod", instance="10.238.65.5"}               # 09-07 08:00→09-08 06:00 全为 1

# 3. 长期死目标清单 vs #76 排除名单
count(count by (instance) (up{job="node-metrics"}))                          # → 229
count(count by (instance) (max_over_time(up{job="node-metrics"}[7d]) == 0))  # → 11
topk(20, count by (instance, service, endpoint) (max_over_time(up{job="node-metrics"}[7d]) == 0))
```

AWS CLI（任何有 CloudWatch 读权限的账号都可复现）：

```bash
aws cloudwatch get-metric-statistics --region us-east-1 \
  --namespace AWS/EC2 --metric-name StatusCheckFailed_Instance \
  --dimensions Name=InstanceId,Value=i-04b4ad1b0469397da \
  --start-time 2026-09-07T10:30:00Z --end-time 2026-09-08T04:10:00Z \
  --period 60 --statistics Maximum \
  --query 'Datapoints | sort_by(@,&Timestamp)[].[Timestamp,Maximum]' --output text
```

---

## 七、由此产生的待办（新增）

1. **修复 11 个长期死的 node-metrics 目标**，或从 SD 里摘掉不该纳管的（如 `idpcd` 的 NLB ENI）。
   不修就谈不上主机宕机告警 —— 排除名单只是症状。
2. **8 台 idoris + iluckydpbi03 + isslvpn01 当前无任何主机宕机告警**，需要替代方案。
   建议用 **CloudWatch `StatusCheckFailed_Instance`**（AWS 侧产生，不依赖 exporter 健康）
   补一条兜底告警 —— 本次它 1 分钟粒度精确标出了故障起止，是最可靠的那一路信号。
   ⚠ `databasecheck` 无 `cloudwatch:PutMetricAlarm` 权限，需 Michael 授权或代建。
3. 清理 `env="PROD"` / `env="Luckin-PROD"` 造成的重复 up 序列。

---

## 八、在哪里执行这些查询（供复核方自行验证）

### A. Grafana Explore（最方便）
`https://iumbgrafana.luckincoffee.us/explore` → 数据源选 **`victoriametrics-basic-us`**

两个必须注意的 UI 细节：
- `max_over_time(...[30d])` 这类**要切 Instant 模式**（Range 模式会对每个点各做一次 30 天回看，慢且无意义）；求值时刻 = 时间范围的结束时刻。
- **要看"值为 0"还是"序列缺失"，必须切 Table 视图**。Range 图上这两种情况长得几乎一样 ——
  **本次结论出错就是踩了这个视觉陷阱**（把常态 0 读成了宕机期间变 0）。

### B. 直接查 VictoriaMetrics（输出是文本，最适合当证据附在回复里）
端点：`https://ibasicmetrics.luckincoffee.us/select/0/prometheus`
认证：Basic Auth，用户名 **`zeus`**（密码在 Grafana 数据源配置里，或找 SRE）

```bash
VM=https://ibasicmetrics.luckincoffee.us/select/0/prometheus
AUTH='zeus:<password>'

# 1. up 恒为 0（30 天），不是宕机才变 0
curl -sG -u "$AUTH" "$VM/api/v1/query" \
  --data-urlencode 'query=max_over_time(up{instance="10.238.65.5:10087"}[30d])' | jq .

# 2. node_exporter 指标完全不存在
curl -sG -u "$AUTH" "$VM/api/v1/query" \
  --data-urlencode 'query=count(node_time_seconds{instance="10.238.65.5:10087"})' | jq .

# 3. 宕机窗口内 up 的原始序列（含崩溃前后，证明窗口外也是 0）
curl -sG -u "$AUTH" "$VM/api/v1/query_range" \
  --data-urlencode 'query=up{instance="10.238.65.5:10087"}' \
  --data-urlencode 'start=2026-09-07T08:00:00Z' \
  --data-urlencode 'end=2026-09-08T06:00:00Z' \
  --data-urlencode 'step=1800' | jq .

# 4. ICMP 全程为 1（#66 永不触发的原因）
curl -sG -u "$AUTH" "$VM/api/v1/query_range" \
  --data-urlencode 'query=up{job="node-ping-iprod", instance="10.238.65.5"}' \
  --data-urlencode 'start=2026-09-07T08:00:00Z' \
  --data-urlencode 'end=2026-09-08T06:00:00Z' \
  --data-urlencode 'step=3600' | jq .

# 5. 全 fleet 长期死目标 vs #76 排除名单
curl -sG -u "$AUTH" "$VM/api/v1/query" \
  --data-urlencode 'query=count(count by (instance) (up{job="node-metrics"}))' | jq .
curl -sG -u "$AUTH" "$VM/api/v1/query" \
  --data-urlencode 'query=topk(20, count by (instance, service, endpoint) (max_over_time(up{job="node-metrics"}[7d]) == 0))' | jq .
```

### C. vmui（VictoriaMetrics 自带网页版 PromQL 控制台）
`https://ibasicmetrics.luckincoffee.us/select/0/vmui/`（带 Basic Auth）。
三个候选路径 `/select/0/vmui/`、`/select/0/prometheus/vmui/`、`/vmui/` 均返回 401
（说明路由都存在、只差认证），带上凭据试第一个。

### 🔴 不要在 dbtools01 的本地 Prometheus（`10.238.3.136:9090`）上查
`node-metrics` / `node-ping-iprod` 是公司 agent 采集后直接写入
`zeus_basic_victoriametrics` 的，**不经过 dbtools01**。在那台机器的 :9090 上查这两个 job
一定返回空 —— 会被误读成「指标不存在 / 结论有误」。同理那 60+ 个 `db-aws-luckyus-*`
mysqld job 也不在 dbtools01 上采。

### AWS 那部分不需要任何 Grafana/VM 权限
第六节的 `aws cloudwatch get-metric-statistics` 只要有 CloudWatch 读权限就能跑，
**这也是本案最硬的一路证据** —— 复核方可以完全不碰我们的监控系统自行验证。
