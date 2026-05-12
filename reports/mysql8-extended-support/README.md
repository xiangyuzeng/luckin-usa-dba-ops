# MySQL 8.0.x RDS Extended Support 月成本测算

**生成日期**: 2026-05-12
**AWS Account**: 257394478466 / us-east-1
**作者**: 曾翔宇 (David Zeng) — DBA / Infrastructure

---

## 1. 背景与定价规则

MySQL 8.0 社区版 standard support 截止 **2026-07-31**。从 **2026-08-01** 起，AWS 对仍运行在 RDS MySQL 8.0.x 的实例自动开启 **Extended Support** 并按 vCPU-小时计费。

**官方来源**
- <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-charges.html>
- <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MySQL.Concepts.VersionMgmt.html>
- <https://aws.amazon.com/rds/mysql/pricing/>

**计费要点**
- 按 **vCPU-小时** 计价
- **Multi-AZ 双倍计费**：主实例 + Standby 两份 vCPU 都收费
- **不享受 EDP 31% 折扣**（Extended Support 是单独的支持费用，AWS 政策不打折）
- 本报告每月按 **30 天 × 24 小时 = 720 小时** 计算

### 1.1 价目表（per vCPU-hour, us-east-1）

| 阶段 | 计费区间 | 起始日 | 截止日 | 单价 USD/vCPU-hr |
|------|---------|--------|--------|-----------------|
| Year 1 | 第 1 个 12 个月 | 2026-08-01 | 2027-07-31 | **$0.100** |
| Year 2 | 第 2 个 12 个月 | 2027-08-01 | 2028-07-31 | **$0.100** |
| Year 3 | 第 3 个 12 个月 | 2028-08-01 | 2029-07-31 | **$0.200** |

### 1.2 按实例规格折算月成本（Multi-AZ）

| Instance Class | vCPU/实例 | Multi-AZ 计费 vCPU | Y1/Y2 月成本 | Y3 月成本 |
|----------------|-----------|---------------------|--------------|-----------|
| db.t3.micro    | 2 | 4 | $288 | $576 |
| db.t3.small    | 2 | 4 | $288 | $576 |
| db.t4g.micro   | 2 | 4 | $288 | $576 |
| db.t4g.medium  | 2 | 4 | $288 | $576 |
| db.t4g.large   | 2 | 4 | $288 | $576 |
| db.t4g.xlarge  | 4 | 8 | $576 | $1,152 |

**公式**：`月成本 = vCPU × Multi-AZ系数(=2) × 单价 × 720h`

---

## 2. 范围与剔除规则

**总盘点**：当前 us-east-1 共 92 个 MySQL RDS 实例（其中 1 个 8.4.7，91 个 8.0.x）。

剔除以下两类实例后聚焦真正生产负载：

| 剔除类别 | 匹配规则 | 数量 |
|----------|---------|------|
| 蓝绿部署残留 | 实例名以 `-old1` 结尾，或包含 `-green-` | 26 |
| 测试环境 | 实例名包含 `test` 或 `dbatest-` | 4 |
| **保留生产实例** | | **61** |

> 注：剔除的实例本身仍在收费（约 $7,200/月 Y1, $14,400/月 Y3），**建议升级前优先清理**。

---

## 3. 测算结果（61 生产实例）

| 维度 | Year 1 月成本 | Year 2 月成本 | Year 3 月成本 |
|------|---------------|---------------|---------------|
| 合计（USD） | **$17,856** | **$17,856** | **$35,712** |
| 年度小计（USD） | $214,272 | $214,272 | $428,544 |
| **三年累计** | colspan=3 | **$857,088** | |

按汇率 7.2 折算 ≈ **¥6.17M RMB（三年累计）**。

### 3.1 与当前 AWS 月支出对比

- 当前月度总 AWS 支出：$49,645
- Y1 增量占比：$17,856 / $49,645 ≈ **36%**
- Y3 增量占比：$35,712 / $49,645 ≈ **72%**

### 3.2 单台月成本分布

- 60 台 × $288/mo (Y1) = $17,280
- 1 台 db.t4g.xlarge (`aws-luckyus-salesmarketing-rw`) × $576/mo = $576
- Y3 全部翻倍

---

## 4. 文件清单

| 文件 | 内容 |
|------|------|
| `instances.csv` | 61 个生产实例明细 + 合计行 |
| `pricing_reference.csv` | Extended Support 价目表 + 按规格的月成本换算 |
| `README.md` | 本说明 |

---

## 5. 建议（节流方向）

1. **立即清理 30 个蓝绿/测试实例**：节省 Y1 月费 ~$7,200，三年累计 ~$414K
2. **升级到 MySQL 8.4 LTS**（standard support 至 2032）：彻底规避 Extended Support 费用
3. **若 2026-07-31 前无法完成 8.4 升级**，至少在 Year 3 之前完成（避免 $0.200 翻倍区间）
4. **统计 8.0.40 实例**（40 台）的升级路径，8.0.45 已是最新 minor，无 minor patch 收益

---

## 6. 校验脚本

```bash
aws rds describe-db-instances --region us-east-1 \
  --query 'DBInstances[?Engine==`mysql`].[DBInstanceIdentifier,DBInstanceClass,EngineVersion,MultiAZ]' \
  --output json
```

> 计费模型：`per_instance_monthly = vCPU × (2 if MultiAZ else 1) × rate × 720`
