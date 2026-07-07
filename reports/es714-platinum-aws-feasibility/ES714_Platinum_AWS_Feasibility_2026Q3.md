# 海外日志平台对齐国内 ES 7.14.x + 白金许可证 — AWS 可行性与成本调研

- **背景:** 2026 Q3 计划推动海外日志平台对齐国内版本(Elasticsearch 7.14.x + Platinum 白金许可证),DBA/基础设施团队预先调研 AWS 侧可行性与成本。
- **AWS 账号:** 257394478466 / us-east-1 / EDP 折扣 31%(实付 = On-Demand × 0.69)
- **调研日期:** 2026-07-07
- **调研人:** 曾翔宇 (David Zeng),Senior DBA / Infrastructure Engineer

---

## 结论速览

AWS 托管服务上**拿不到** Elastic 官方 7.14.x,更没有官方白金许可证。要 100% 对齐国内(官方 ES + Platinum),只有两条路:**Elastic Cloud(AWS Marketplace 上 Elastic 自营托管)** 或 **EC2 自建 + 单独采购 Elastic 订阅**。自建的话,**服务器成本很低(~$1.5万–2万/年),真正的大头是许可证(~$7.5万–15万/年,需向 Elastic 销售单独报价)**。

---

## 问题 1:AWS 上有没有 ElasticSearch 7.14.x 官方版?

**没有。** 直接查当前 AWS us-east-1 账号可用的引擎版本清单(`aws opensearch list-versions`):

| 服务 | 最高 ES 版本 | 说明 |
|------|------------|------|
| Amazon OpenSearch Service(前身 Amazon ES) | **Elasticsearch_7.10** | 到 7.10 封顶,再往上就是 OpenSearch_1.x/2.x/3.x |

关键点:
- 2021 年初 Elastic 把开源协议从 Apache 2.0 改成 SSPL/Elastic License 后,AWS 直接**分叉**出了 OpenSearch。现在 AWS 控制台看到的 "Elasticsearch" **最高只到 7.10,且是带 AWS Open Distro 安全插件的分叉版,不是 Elastic 官方发行版**。
- **7.11 及以后(含要用的 7.14.x)的所有版本,AWS 托管服务永远不会提供** —— 协议冲突导致,不是版本没跟上。
- 结论:AWS 托管侧看到的都是 OpenSearch,**7.14.x 官方版在 Amazon OpenSearch Service 上不可能有**。

---

## 问题 2:要官方 ES 7.14.x + 白金许可证,怎么拿?

两条合规途径:

### 途径 A:Elastic Cloud(AWS Marketplace,Elastic 官方自营托管)
- Elastic 在 AWS Marketplace 上架了官方 Elastic Cloud,订阅层级可选 Standard / Gold / **Platinum** / Enterprise。
- 官方发行版,**Platinum 层解锁 ML、告警(Watcher)、企业级认证(SAML/LDAP/SSO)、跨集群复制等**,带 99.95% SLA。
- 走 AWS Marketplace 结算,可计入 AWS 账单/EDP。
- **注意:** Elastic Cloud 默认推最新版(8.x/9.x)。7.14.x 是 2021 年 8 月的老版本,7.x 整个系列已 EOL,官方托管基本拿不到 7.14 这么老的版本部署——若硬对齐 7.14.x,需与 Elastic 确认能否指定老版本。

### 途径 B:EC2 自建 + 单独买 Elastic 订阅(最贴合"对齐国内"的做法)
- 在 EC2 上自己装官方 Elasticsearch 7.14.x(版本完全可控,精确对齐国内),然后**单独向 Elastic 采购 Platinum 订阅证书**授权到集群。
- 这也是国内那套大概率的部署方式(自建 + 商业订阅)。
- **两个坑:**
  1. **Platinum 层官方已停售给新客户** —— Elastic 现在只对老客户续约/扩容 Platinum,新签只让选 Enterprise 或 Elastic Cloud。若国内 First Ray / 瑞幸主体已有 Platinum 合同,**优先看能否把海外主体挂到现有全球合同下扩容**,而非重新签。
  2. **7.14.x 已 EOL** —— Elastic 商业支持只覆盖维护版本,买 Platinum 订阅通常要求跑受支持的版本,7.14 拿到"带官方支持的白金授权"会有阻力,建议至少评估 7.17(7.x 最后一版)或直接上 8.x。

---

## 问题 3:AWS 自建 3 节点白金集群成本估算

分成两块:**基础设施(便宜)+ 许可证(贵,决定性成本)**。基础设施按 EDP 31% 折扣(× 0.69)算实付,us-east-1 当前价格(EC2 Price List API 实时查询)。

### A. EC2 计算(3 节点,On-Demand × 730h × 0.69)

| 机型 | 规格 | On-Demand/时 | 单节点/月(EDP) | 3 节点/月 | 3 节点/年 |
|------|------|-------------|----------------|----------|----------|
| r6g.xlarge | 4 vCPU / 32G | $0.2016 | $101.5 | $305 | **$3,655** |
| **r6g.2xlarge**(推荐日志场景) | 8 vCPU / 64G | $0.4032 | $203.1 | **$609** | **$7,312** |
| r6i.2xlarge (x86) | 8 vCPU / 64G | $0.5040 | $253.9 | $762 | $9,140 |

> 走 1 年期 RI / Savings Plan 计算这层还能再省 ~40%(3× r6g.2xlarge 约降到 ~$365/月)。

### B. 存储 + 备份 + 网络(以推荐档 r6g.2xlarge 为例)

| 项目 | 假设 | 月成本(EDP) | 年成本 |
|------|------|-------------|--------|
| EBS gp3 | 2TB/节点 × 3 = 6TB @ $0.08/GB × 0.69 | ~$339 | ~$4,072 |
| gp3 额外 IOPS/吞吐 | 日志写入密集,预留冗余 | ~$50 | ~$600 |
| S3 快照备份 | 冷备/滚动快照 | ~$30 | ~$360 |
| 跨 AZ 数据传输 | 3 节点跨 AZ 复制 | ~$40 | ~$480 |
| **基础设施小计** | | **~$1,070/月** | **≈ $12,800/年** |

> 存储按实际日志量线性放大——此处按中等日志平台估的 6TB。

### C. Elastic Platinum 许可证(决定性大头,报价制)

| 项 | 金额 |
|----|------|
| 自建 Platinum 订阅(按节点数 + RAM 计价,需联系 Elastic 销售报价) | **~$75,000 – $150,000/年**(中型部署行业区间) |

- 自建订阅按**节点数 × 每节点内存**授权,不公开挂牌价,必须 Elastic 销售单独报价。
- 3 节点是小集群,大概率落在区间偏低端,但白金证书基本没有低于 5 位数/年的。

### 💰 自建总成本汇总(3 节点,推荐档)

| 组成 | 年成本 |
|------|--------|
| EC2 计算(On-Demand+EDP) | ~$7,300(RI 可降到 ~$4,400) |
| 存储/备份/网络 | ~$12,800 |
| **AWS 基础设施小计** | **~$15,000 – $20,000/年** |
| **Elastic Platinum 许可证** | **~$75,000 – $150,000/年** |
| **合计** | **≈ $90,000 – $170,000/年** |

**一句话:自建的钱 80–90% 都花在许可证上,AWS 服务器本身很便宜。**

---

## 给决策的建议

1. **先确认"对齐国内"到底对齐什么** —— 是"必须官方 7.14.x + Platinum",还是"功能对齐即可"?若是后者,**OpenSearch 3.x 免费自带安全/告警/ML/异常检测**(把老 Platinum 大部分功能白送),日志平台成本能压到只剩 ~$1.5–2万/年基础设施,**省掉 $7.5万–15万/年许可证**。
2. **若硬对齐官方 ES:** 优先查国内/集团有没有现成 Elastic 全球合同能覆盖海外主体(Platinum 已停新签,几乎是唯一拿到 Platinum 的路),否则新签只能上 Enterprise 或 Elastic Cloud。
3. **版本别锁死 7.14:** 7.14/7.x 已 EOL,买官方支持会卡版本,建议评估 7.17 或 8.x 对齐。

---

## 三方方案对比

| 维度 | OpenSearch 自建/托管 | 官方 ES + Platinum 自建(EC2) | Elastic Cloud (Marketplace) |
|------|---------------------|------------------------------|-----------------------------|
| 是否官方 ES | 否(AWS 分叉) | 是,版本完全可控 | 是,Elastic 自营 |
| 对齐国内 7.14.x | 否(最高 7.10) | ✅ 精确对齐 | 需确认能否指定老版本 |
| 许可证成本/年 | $0 | ~$7.5万–15万(报价制,已停新签) | 按用量计,Platinum 从 ~$131/月起按资源计 |
| AWS 基础设施/年 | ~$1.5–2万(自建) | ~$1.5–2万 | 含在订阅内 |
| 运维负担 | 中(自建)/ 低(托管) | 高(全自管) | 低(全托管) |
| 白金功能 | 免费自带等价功能 | ✅ | ✅ |

---

## 附:数据来源
- AWS OpenSearch 引擎版本清单:`aws opensearch list-versions --region us-east-1`(实时)
- EC2 定价:AWS Price List API,us-east-1,2026-07-06 版本(实时)
- Elastic 订阅/许可证:
  - Elastic self-managed pricing — https://www.elastic.co/pricing/self-managed
  - Elastic Subscriptions — https://www.elastic.co/subscriptions
  - Elastic Cloud on AWS Marketplace — https://aws.amazon.com/marketplace/pp/prodview-voru33wi6xs7k
  - Elastic Pricing FAQ — https://www.elastic.co/pricing/faq
