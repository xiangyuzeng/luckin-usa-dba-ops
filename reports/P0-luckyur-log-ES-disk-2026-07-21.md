# P0 — OpenSearch `luckyur-log` 磁盘耗尽调查(2026-07-21)

**告警:** 【DB告警】AWS-ES磁盘空间不足10G_语音 · P0 · 集群 `luckyur-log`
**触发:** 2026-07-21 19:31 EDT(23:31 UTC),空闲 9,739.95 MB · 旧策略 id=97
**调查:** 2026-07-22

## 结论
**真实 P0 —— 容量长期性耗尽,非瞬时抖动。集群已接近写满。** 告警的 9.7 GB 已过时:自告警触发后,最满数据节点空闲反复跌至 **1.1–3 GB**(最低 1,131 MB @ 21:20 UTC)。

- ✅ **写入尚未阻断** —— `ClusterIndexWritesBlocked = 0`,采集仍正常。
- ✅ **集群未 RED** —— `ClusterStatus.red = 0`;7 节点(4 数据 + 3 master)齐全。
- 🔴 **零余量** —— 最满节点在 1–4 GB 空闲的 flood-stage 水位反复震荡,写入阻断/索引转只读风险迫近(以小时计)。

## 证据

**集群:** ES 7.10,4× `m5.xlarge.search` 数据 + 3× `t3.medium.search` master,**500 GB gp2/节点 = 2 TB 毛容量(~1.86 TB 可用)**,2-AZ,单副本日志域(0 副本 —— 无副本可降)。

**14 天趋势(`ClusterUsedSpace` / 单节点最小 `FreeStorageSpace`):**

| 日期 | 已用 | 单节点最小空闲 |
|------|------|---------------|
| 07-08 | 1.47 TB | ~70 GB |
| 07-15 | 1.56 TB | ~49 GB |
| 07-19 | 1.70 TB | ~16 GB |
| 07-20 | 1.70–1.82 TB | 5.7 GB |
| 07-21 | 1.74–1.85 TB | **1.1 GB** |

- **净增长 ≈ +27.5 GB/天**(清理跟不上写入,索引持续累积)。
- 每日锯齿:空闲在 00:00–06:00 UTC 回升(夜间滚动/删除),白天耗尽;基线持续攀升进入饱和区。

**索引级根因(`_cat/indices` 明细):**

| 日志源 | 副本 | 每天大小 | 保留 | 累计 | 判断 |
|---|---|---|---|---|---|
| **`iprod_tomcat_lucky_k8s`** | 0 | 53→**89 GB**(+68%) | ~14 天 | **≈ 1030 GB** | **元凶,占集群 >50%** |
| `skywalking_idx_segment` | 0 | ~30–41 GB | ~7 天(07-16 新增) | ≈ 220 GB | 新增大源,对应夜间写入 +40% |
| `iprod_tomcat_lucky` | 0 | ~8–9 GB | 14 天 | ≈ 110 GB | 一般 |
| `fe-log` / `prod_json_lucky` / `skywalking_idx_metrics-all` | 0/1 | ~4–8 GB | 7–14 天 | 各 <90 GB | 一般 |
| `vpn-audit` / `auditing-lcp-prod` / `kube-event` / `prod-worker01-eks-*` | 1 | <0.5 GB | 回溯 2025 年 | 单个 <1 GB | 非空间问题,但拖累 shard 数 |

**根因判定:** ISM 并未停摆(最老 tomcat_k8s 停在 07-08、skywalking segment 停在 07-16,删除在跑),真正问题是 **`iprod_tomcat_lucky_k8s` 单日体积爆炸式增长(两周 +68%),14 天保留期相对太长**,加上 07-16 新增的 skywalking tracing 源,共同把集群推到饱和。

## 处置
详见配套处置方案:`reports/P0-luckyur-log-cleanup-execution-2026-07-21.md`
- ① 删 `iprod_tomcat_lucky_k8s` 最老 5 天 ≈ 释放 330 GB(立即降压)
- ② `iprod_tomcat_lucky_k8s` 保留期 14→7 天(长期省 ~500GB)
- ③ `skywalking_idx_segment` 保留期 → 3–5 天
- ④ 老审计/eks 索引挂统一删除策略(降 shard 数)
- ⑤ 磁盘水位预警 + 可选 EBS 500→650GB/节点缓冲
