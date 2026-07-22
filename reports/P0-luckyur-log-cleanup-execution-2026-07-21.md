# P0 执行单 — `luckyur-log` ES 磁盘清理与保留策略修复

**集群:** `luckyur-log`(ES 7.10, VPC + FGAC, 4× m5.xlarge.search / 500GB gp2/节点 = ~1.86 TB 可用,单副本日志域)
**触发:** 2026-07-21 19:31 EDT P0「AWS-ES磁盘空间不足10G_语音」,单节点空闲最低跌至 **1.1 GB**
**执行人需求:** OpenSearch **master 用户**(Kibana Dev Tools)。`databasecheck` 无后端角色、无 `es:UpdateDomainConfig`,无法自行执行。
**当前写入状态:** `ClusterIndexWritesBlocked = 0`(尚未阻断,但零余量,需尽快)

---

## 根因(已由索引明细确认)

- **`iprod_tomcat_lucky_k8s` 独占 ≈ 1030 GB(集群 >50%)**,单日索引 14 天从 53 GB 涨到 **89 GB(+68%）**。
- 14 天固定保留下,每天新进(~89GB)比滚出(~53GB)大 ~36GB → 集群净增 **~+27.5 GB/天**(与 CloudWatch 吻合)。**不是没删,是删不过写。**
- 次要:`skywalking_idx_segment`(~35GB/天,07-16 新增)——对应 07-17 起夜间写入 +40%。

---

## ① 立即降压(秒级见效,先做)

在 **Kibana → Dev Tools** 执行,删 `iprod_tomcat_lucky_k8s` 最老 5 天:

```
DELETE iprod_tomcat_lucky_k8s-2026.07.08-000270,iprod_tomcat_lucky_k8s-2026.07.09-000271,iprod_tomcat_lucky_k8s-2026.07.10-000272,iprod_tomcat_lucky_k8s-2026.07.11-000273,iprod_tomcat_lucky_k8s-2026.07.12-000274
```

| 删除索引 | 释放 |
|---|---|
| 2026.07.08 | 79 GB |
| 2026.07.09 | 66 GB |
| 2026.07.10 | 74 GB |
| 2026.07.11 | 58 GB |
| 2026.07.12 | 53 GB |
| **合计** | **≈ 330 GB** → 单节点回到健康区 |

> 若想一步到位更安全,再加删 07.13(65GB)、07.14(82GB),累计 ≈ 477 GB。

**验证:** 删后重跑
```
GET _cat/allocation?v          # 看各节点 disk.avail 回升
GET _cluster/health            # status 应保持 green/yellow,无 unassigned
```

---

## ② 治本:收紧 `iprod_tomcat_lucky_k8s` 保留期(14→7 天)

单日已 ~89GB,7 天 ≈ 620GB 足够,直接省 ~500GB 长期占用。

**查当前策略:**
```
GET _plugins/_ism/policies
GET _plugins/_ism/explain/iprod_tomcat_lucky_k8s-*
```

**把 delete state 的 `min_index_age` 由 `14d` 改为 `7d`**(示例策略骨架,按现有策略名/结构对齐):
```json
PUT _plugins/_ism/policies/iprod_tomcat_k8s_policy
{
  "policy": {
    "description": "tomcat k8s logs - 7d retention",
    "default_state": "hot",
    "states": [
      { "name": "hot",
        "actions": [],
        "transitions": [ { "state_name": "delete", "conditions": { "min_index_age": "7d" } } ] },
      { "name": "delete",
        "actions": [ { "delete": {} } ],
        "transitions": [] }
    ],
    "ism_template": [ { "index_patterns": ["iprod_tomcat_lucky_k8s-*"], "priority": 100 } ]
  }
}
```
> 若已存在绑定策略,只需 PATCH 其 `min_index_age`,不要新建重复模板。改后对存量索引跑一次 `POST _plugins/_ism/change_policy` 使其生效。

---

## ③ 确认 `skywalking_idx_segment` 保留(建议 3–5 天)

07-16 新增、~35GB/天。若仅用于短期排障,保留 3–5 天即可,避免再吃 100+GB。
```
GET _plugins/_ism/explain/skywalking_idx_segment-*
```
按需将其保留期设为 `5d`(同 ② 方式)。

---

## ④ 卫生整改(非紧急,降 shard 数)

以下索引单个 <1GB 但**从不清理、rep=1**,大量占用 shard 槽位(拖累 master):
- `vpn-audit-*`(回溯 2025-05)
- `auditing-lcp-prod-*`(回溯 2025-07)
- `kube-event-prod-*`(回溯 2025-03)
- `prod-worker01-eks-*`(6 月起,数百个)

建议挂统一删除策略(如审计类保留 6 个月、eks 系统日志保留 30 天)。省空间有限,但显著减少 shard 总数。

---

## ⑤ 若在获得访问前写入已被阻断

`ClusterIndexWritesBlocked` 翻 1 → 索引变 `read_only_allow_delete`。腾出空间后,master 用户执行解除:
```
PUT _all/_settings
{ "index.blocks.read_only_allow_delete": null }
```

---

## 长期建议

- 单靠删索引/改保留是止血;若业务日志量持续增长,考虑 EBS 扩容 500→650 GB/节点(gp2 原地扩,无蓝绿,~30min,≈+$41/月 EDP)作为缓冲,与 ②③ 并行。
- 给该域加 **磁盘水位预警**(单节点空闲 <50 GB 提前告警),避免再次踩到 10 GB 红线才发现。
