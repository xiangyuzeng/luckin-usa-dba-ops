# July 2026 QA 门店稽核 — 数据包 (DATA PACK)
- Doc: **LCNA-QA-2026-007**  ·  Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol
- Window: 2026-07-01 .. 2026-07-31 (31 天, closed month)  ·  Built by DBA data-collection agent
- Scope locks: 主巡检 (QA审计>区经检查>门店自检, latest) for §2.2/§2.3/§3.1/§3.2/§3.4/§3.5/§4.1/§4.5/§7 per-type; 全月 for §3.3/§7.x totals
- Module mapping: "Site Security" → 职业安全 (carried from 2026-07-01 resolution); UNMAPPED this month: NONE

## [COVER/文档信息]

- 文档编号：**LCNA-QA-2026-007**　报告期：**2026年7月**（2026-07-01 .. 2026-07-31，31 天）
- 活跃门店：**21 家运营在营门店**（主巡检口径），全部完成巡检；未巡检门店 0 家
  - 计数口径：t_shop_info status=1 且非测试厨房（SL12/US999xx/US00000），open_date≤2026-07-31
  - 本月新纳入主巡检门店（6月无主巡检基准）：48th & 3rd(US00009) 开业2026-06-30，Grand Central Terminal(US00013) 开业2026-06-30，128 W 32nd St(US00021) 开业2026-07-16
- 巡检类型次数：门店自检 54 / QA审计 19 / 区经检查 21 = **共 94 次**（94 次提交 − 0 误提交）
- 全月发现项：S 33 / M 59 / G 377 / L 169 = **638**
- 主巡检发现项：S 13 / M 7 / G 72 / L 15 = **107**
- 申诉：**19 起立案（16 获批 / 0 驳回 / 3 审批中）**
- QA 审计人员：Eamonn Caballar 19 次（Senior QA Manager）
- 区经检查人员：Jung Han Liang 21 次（Area Operations Manager）
- 节奏区间：门店自检 2026-07-01~2026-07-31；QA审计 2026-07-07~2026-07-24；区经检查 2026-07-08~2026-07-31

## [§管理摘要]

- 主巡检均分 **89.4**（6月 88.7，**+0.7**）；门店覆盖 **21/21 = 100%**（6月基准 18 家，本月 +3 家新店纳管）
- 同口径（仅 6 月有主巡检的 18 家）均分 **92.1**（6月 88.7，+3.4）
- 全月发现项合计 **638**（主巡检 107）
- (a) 体系 vs 6月：巡检量 85→94（+9 次）；主巡检均分 88.7→89.4（**+0.7**）；覆盖率维持 100%
- (b) 最大系统性 S 项集群：**Sinks and Pipes** — 17 项 S，涉及 11 家门店
- (c) 巡检员一致性旗标：9 家门店存在同店跨类型 ≥20 分背离 → 41st & Lexington(US00015) [QA 94 / 区经 88 / 自检 54.0]（差 40.0）；28th & 6th(US00002) [区经 57 / QA 94 / 自检 94.0]（差 37）；154 Bleecker(US00010) [QA 95 / 区经 62 / 自检 70.5]（差 33）；128 W 32nd St(US00021) [区经 64 / 自检 94.0]（差 30.0）；48th & 3rd(US00009) [区经 60 / 自检 85.7]（差 25.7）；29th & 3rd(US00019) [QA 98 / 区经 79 / 自检 72.5]（差 25.5）；102 Fulton(US00006) [QA 91 / 区经 66 / 自检 75.0]（差 25）；40th & 10th(US00018) [区经 69 / QA 94 / 自检 77.2]（差 25）；21st & 3rd(US00020) [QA 94 / 区经 76 / 自检 71.0]（差 23.0）
  - 最大改善：52nd & Madison(US00027) 64→90（+26）
  - 最大下滑：21st & 3rd(US00020) 97→94（-3）

## [§1.1] 主巡检概览

- 最高分门店：**29th & 3rd(US00019) = 98**
- 最低分门店：**48th & 3rd(US00009) = 60**
- S 项门店数：**12** 家（54th & 8th(US00005), 102 Fulton(US00006), 33rd & 10th(US00008), 48th & 3rd(US00009), 154 Bleecker(US00010), 40th & 10th(US00018), 29th & 3rd(US00019), 21st & 3rd(US00020), 128 W 32nd St(US00021), 15th & 3rd(US00024), 221 Grand(US00025), 52nd & Madison(US00027)）
- <80 分门店数：**2** 家（48th & 3rd(US00009) 60, 128 W 32nd St(US00021) 64）
- 覆盖率：**21/21 = 100%**（6月 18/18 = 100%）

## [§1.2] 主巡检全门店明细（按得分降序）

| # | 门店 | 编号 | 得分 | 巡检类型 | 扣分 | S | M | G | L | 巡检员 | ※ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 29th & 3rd | US00019 | 98 | QA审计 | -7 | 1 | 0 | 1 | 0 | Eamonn Caballar | ※ |
| 2 | Grand Central Terminal | US00013 | 96 | 区经检查 | -4 | 0 | 0 | 1 | 2 | Jung Han Liang |  |
| 3 | 154 Bleecker | US00010 | 95 | QA审计 | -12 | 1 | 0 | 3 | 1 | Eamonn Caballar | ※ |
| 4 | 8th & Broadway | US00001 | 94 | QA审计 | -8 | 0 | 0 | 4 | 0 | Eamonn Caballar | ※ |
| 5 | 28th & 6th | US00002 | 94 | QA审计 | -8 | 0 | 0 | 4 | 0 | Eamonn Caballar | ※ |
| 6 | 41st & Lexington | US00015 | 94 | QA审计 | -12 | 0 | 0 | 6 | 0 | Eamonn Caballar | ※ |
| 7 | 40th & 10th | US00018 | 94 | QA审计 | -13 | 1 | 0 | 4 | 0 | Eamonn Caballar | ※ |
| 8 | 21st & 3rd | US00020 | 94 | QA审计 | -13 | 1 | 0 | 4 | 0 | Eamonn Caballar | ※ |
| 9 | 221 Grand | US00025 | 94 | QA审计 | -17 | 1 | 0 | 5 | 2 | Eamonn Caballar | ※ |
| 10 | 37th & Broadway | US00004 | 93 | QA审计 | -7 | 0 | 0 | 3 | 1 | Eamonn Caballar |  |
| 11 | 16th & 6th | US00012 | 93 | QA审计 | -7 | 0 | 1 | 1 | 0 | Eamonn Caballar |  |
| 12 | 33rd & 10th | US00008 | 92 | QA审计 | -13 | 1 | 0 | 3 | 2 | Eamonn Caballar | ※ |
| 13 | 23rd & 8th | US00022 | 92 | QA审计 | -8 | 0 | 0 | 4 | 0 | Eamonn Caballar |  |
| 14 | 102 Fulton | US00006 | 91 | QA审计 | -16 | 1 | 1 | 3 | 0 | Eamonn Caballar | ※ |
| 15 | 15th & 3rd | US00024 | 91 | QA审计 | -14 | 1 | 1 | 2 | 0 | Eamonn Caballar | ※ |
| 16 | 52nd & Madison | US00027 | 90 | QA审计 | -17 | 1 | 0 | 5 | 2 | Eamonn Caballar | ※ |
| 17 | 108th & Broadway | US00007 | 89 | QA审计 | -11 | 0 | 0 | 5 | 1 | Eamonn Caballar |  |
| 18 | 100 Maiden Ln | US00003 | 85 | QA审计 | -15 | 0 | 1 | 5 | 0 | Eamonn Caballar |  |
| 19 | 54th & 8th | US00005 | 84 | QA审计 | -21 | 1 | 2 | 3 | 0 | Eamonn Caballar | ※ |
| 20 | 128 W 32nd St | US00021 | 64 | 区经检查 | -16 | 1 | 1 | 2 | 2 | Jung Han Liang |  |
| 21 | 48th & 3rd | US00009 | 60 | 区经检查 | -20 | 2 | 0 | 4 | 2 | Jung Han Liang |  |

注：扣分=名义扣分（Σ score_config，与 S/M/G/L 计数一致，不随申诉变动）；得分=官方调整后分（申诉获批已反映，含 S 项 −20 惩罚）；※=申诉获批调整。

## [§1.3] 分数带 / 跨月 / 申诉 / 背离 / 自检 S 项

- 分数带：≥85 **18** 家 / 80–84 **1** 家 / <80 **2** 家
- S 项分布：12 家主巡检含 S 项
- 环比改善（10 家）：52nd & Madison(US00027) 64→90(+26)，54th & 8th(US00005) 71→84(+13)，28th & 6th(US00002) 86→94(+8)，8th & Broadway(US00001) 87→94(+7)，37th & Broadway(US00004) 89→93(+4)，29th & 3rd(US00019) 94→98(+4)，154 Bleecker(US00010) 92→95(+3)，40th & 10th(US00018) 91→94(+3)，15th & 3rd(US00024) 88→91(+3)，16th & 6th(US00012) 91→93(+2)
- 环比下滑（7 家）：21st & 3rd(US00020) 97→94(-3)，102 Fulton(US00006) 93→91(-2)，108th & Broadway(US00007) 91→89(-2)，33rd & 10th(US00008) 94→92(-2)，100 Maiden Ln(US00003) 86→85(-1)，41st & Lexington(US00015) 95→94(-1)，23rd & 8th(US00022) 93→92(-1)
- 环比持平（1 家）：221 Grand(US00025) 94
- 新纳管门店（无 6 月基准，3 家）：48th & 3rd(US00009) 60（区经检查，开业2026-06-30），Grand Central Terminal(US00013) 96（区经检查，开业2026-06-30），128 W 32nd St(US00021) 64（区经检查，开业2026-07-16）
- 最大变动：改善 52nd & Madison(US00027) +26；下滑 21st & 3rd(US00020) -3
- 申诉调整门店（13 家 ※）：8th & Broadway(US00001), 28th & 6th(US00002), 54th & 8th(US00005), 102 Fulton(US00006), 33rd & 10th(US00008), 154 Bleecker(US00010), 41st & Lexington(US00015), 40th & 10th(US00018), 29th & 3rd(US00019), 21st & 3rd(US00020), 15th & 3rd(US00024), 221 Grand(US00025), 52nd & Madison(US00027)
- 同店跨类型背离（≥20分）：41st & Lexington(US00015) [QA 94 / 区经 88 / 自检 54.0](差40.0)；28th & 6th(US00002) [区经 57 / QA 94 / 自检 94.0](差37)；154 Bleecker(US00010) [QA 95 / 区经 62 / 自检 70.5](差33)；128 W 32nd St(US00021) [区经 64 / 自检 94.0](差30.0)；48th & 3rd(US00009) [区经 60 / 自检 85.7](差25.7)；29th & 3rd(US00019) [QA 98 / 区经 79 / 自检 72.5](差25.5)；102 Fulton(US00006) [QA 91 / 区经 66 / 自检 75.0](差25)；40th & 10th(US00018) [区经 69 / QA 94 / 自检 77.2](差25)；21st & 3rd(US00020) [QA 94 / 区经 76 / 自检 71.0](差23.0)
- 自检发现 S 项（15 项）：108th & Broadway(US00007) Expiration Date “Partners aren’t printing proper open lab”；33rd & 10th(US00008) Cross-Contamination “ice scoop containers have a milky water ”；154 Bleecker(US00010) Sinks and Pipes “Air gap causes flooding”；154 Bleecker(US00010) Sinks and Pipes “Airgap makes overflow”；16th & 6th(US00012) Cross-Contamination “”；41st & Lexington(US00015) Expiration Date “Two expired materials in fridge”；41st & Lexington(US00015) Product Storage Conditions “Refrigeratorated materials left out of f”；41st & Lexington(US00015) Cross-Contamination “Cross contamination”；41st & Lexington(US00015) Foreign Material Control “Stain”；41st & Lexington(US00015) Expiration Date “No expiration date”；40th & 10th(US00018) Sinks and Pipes “No air gap for the front bar grease trap”；29th & 3rd(US00019) Expiration Date “”；21st & 3rd(US00020) Cross-Contamination “Open pitcher lids, matcha stain on juice”；15th & 3rd(US00024) Sinks and Pipes “”；15th & 3rd(US00024) No Sign of Insect Pests “”

## [§2.1] 模块风险分层（主巡检覆盖率）

- 🔴 ≥50% 门店：清洁卫生(100.0%), 设施(57.1%)
- 🟡 30–49% 门店：无
- 🟢 <30% 门店：过程控制(28.6%), 职业安全(19.0%), 虫害防控(14.3%), 温控有效期(23.8%), 员工健康卫生(14.3%), 设备维护(14.3%)
- 主巡检无扣分模块（未列示）：证照, 供应链

## [§2.2] 模块排名（主巡检，按扣分）

| 模块 | 问题数 | 扣分 | 门店(n/N) | 覆盖率 | S | M | G | L | 风险 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 清洁卫生 | 65 | -118 | 21/21 | 100.0% | 0 | 1 | 49 | 15 | 🔴 |
| 设施 | 13 | -56 | 12/21 | 57.1% | 10 | 0 | 3 | 0 | 🔴 |
| 温控有效期 | 5 | -25 | 5/21 | 23.8% | 0 | 5 | 0 | 0 | 🟢 |
| 过程控制 | 9 | -24 | 6/21 | 28.6% | 2 | 0 | 7 | 0 | 🟢 |
| 虫害防控 | 4 | -11 | 3/21 | 14.3% | 0 | 1 | 3 | 0 | 🟢 |
| 职业安全 | 5 | -10 | 4/21 | 19.0% | 0 | 0 | 5 | 0 | 🟢 |
| 员工健康卫生 | 3 | -9 | 3/21 | 14.3% | 1 | 0 | 2 | 0 | 🟢 |
| 设备维护 | 3 | -6 | 3/21 | 14.3% | 0 | 0 | 3 | 0 | 🟢 |

Σ主巡检模块扣分 = -259

## [§2.3] 扣分 Top5 模块逐条发现（主巡检，原文）


**清洁卫生**（65 项，扣分 -118；空描述跳过 0，超额省略 45）
| 门店(code) | 子项 | 严重度 | 扣分 | 描述原文 |
| --- | --- | --- | --- | --- |
| 54th & 8th(US00005) | Clean & Sanitize | M | -5 | Sanitizer reading below standard. |
| 8th & Broadway(US00001) | Equipment and utensils | G | -2 | Dust on fridges. |
| 8th & Broadway(US00001) | Equipment and utensils | G | -2 | Cleaned utensils sitting in standing water. |
| 8th & Broadway(US00001) | Equipment and utensils | G | -2 | coffee grounds found on coffee grinder. |
| 28th & 6th(US00002) | Equipment and utensils | G | -2 | Dust on fridges and ice machine. |
| 28th & 6th(US00002) | Equipment and utensils | G | -2 | Food residue on utensils. |
| 28th & 6th(US00002) | Equipment and utensils | G | -2 | Dust on top of coffee grinder. /  / Dust on top of drip machine /  / Food material found on blender head .  /  / Staining on blender rubber gasket. |
| 100 Maiden Ln(US00003) | Equipment and utensils | G | -2 | Fridges found with dust on tops |
| 100 Maiden Ln(US00003) | Clean & Sanitize | G | -2 | Tasks out of grace period. |
| 100 Maiden Ln(US00003) | Equipment and utensils | G | -2 | coffee grounds / matcha staining on counter surfaces. |
| 100 Maiden Ln(US00003) | Equipment and utensils | G | -2 | Staining inside ice machine |
| 37th & Broadway(US00004) | Equipment and utensils | G | -2 | Dust on tops of fridges. |
| 37th & Broadway(US00004) | Equipment and utensils | G | -2 | Food residue on utensils. |
| 37th & Broadway(US00004) | Equipment and utensils | G | -2 | Milk Machine stains |
| 54th & 8th(US00005) | Clean & Sanitize | G | -2 | Tasks out of 15 min window. |
| 54th & 8th(US00005) | Equipment and utensils | G | -2 | Food residue on warming station utensils. |
| 54th & 8th(US00005) | Equipment and utensils | G | -2 | Dust on tops of oven / drip machine.  /  / Syrup machine spill pad stained. /  /  / Stains on blender. |
| 102 Fulton(US00006) | Equipment and utensils | G | -2 | Dust on fridges. |
| 102 Fulton(US00006) | Equipment and utensils | G | -2 | Staining / Food residue found on utensils. |
| 102 Fulton(US00006) | Equipment and utensils | G | -2 | Sanitizer residue located on ice machine. |

**设施**（13 项，扣分 -56；空描述跳过 0，超额省略 0）
| 门店(code) | 子项 | 严重度 | 扣分 | 描述原文 |
| --- | --- | --- | --- | --- |
| 54th & 8th(US00005) | Sinks and Pipes | S | -5 | Plumbing fixtures behind milk machine not to standard. |
| 102 Fulton(US00006) | Sinks and Pipes | S | -5 | Airgap compliance breached on following drains.  /  / 1. Ice Machine  / 2. Drain located under drip machine |
| 33rd & 10th(US00008) | Sinks and Pipes | S | -5 | Airgap not within standard. |
| 154 Bleecker(US00010) | Sinks and Pipes | S | -5 | Handwashing / 3 compartment sink continues to flood upon draining. /  / Backflow Issue in drain under drip machine. |
| 40th & 10th(US00018) | Sinks and Pipes | S | -5 | Piping too close to filter / Wrapping coming off. |
| 29th & 3rd(US00019) | Sinks and Pipes | S | -5 | Faulty Pipe wrapping |
| 21st & 3rd(US00020) | Sinks and Pipes | S | -5 | Grease trap piping touching filter.  /  / Airgap under coffee machine. |
| 15th & 3rd(US00024) | Sinks and Pipes | S | -5 | Airgap not in compliance. (3 compartment sink.) |
| 221 Grand(US00025) | Sinks and Pipes | S | -5 | Pipe touching filter under drip machine. |
| 52nd & Madison(US00027) | Sinks and Pipes | S | -5 | Air gap not within standard. (3 compartment sink.) |
| Grand Central Terminal(US00013) | Grease traps | G | -2 | Not odor free and the filter was opposite and jeopardized by BD |
| 41st & Lexington(US00015) | Good condition | G | -2 | Exterior: Dirty store front. |
| 221 Grand(US00025) | Good condition | G | -2 | Gap in door. (Main entrance.) |

**温控有效期**（5 项，扣分 -25；空描述跳过 0，超额省略 0）
| 门店(code) | 子项 | 严重度 | 扣分 | 描述原文 |
| --- | --- | --- | --- | --- |
| 100 Maiden Ln(US00003) | Expiration Date | M | -5 | Missing date. |
| 54th & 8th(US00005) | Expiration Date | M | -5 | Missing expiration label. |
| 102 Fulton(US00006) | Expiration Date | M | -5 | Missing expiration date on syrup bottle. |
| 16th & 6th(US00012) | Expiration Date | M | -5 | Missing expiration tag on syrup bottle. |
| 128 W 32nd St(US00021) | Expiration Date | M | -5 | No label |

**过程控制**（9 项，扣分 -24；空描述跳过 0，超额省略 0）
| 门店(code) | 子项 | 严重度 | 扣分 | 描述原文 |
| --- | --- | --- | --- | --- |
| 48th & 3rd(US00009) | Cross-Contamination | S | -5 | A spoiled milk isn’t disposed and not marked left in the mop sink |
| 128 W 32nd St(US00021) | Cross-Contamination | S | -5 | Chia seeds in the container of smoothie powder.  / And |
| 28th & 6th(US00002) | Storage/Maintenance of Utensils | G | -2 | Standing water sighted on ice machine. |
| 108th & Broadway(US00007) | Material Storage Location Specification | G | -2 | Lock box unlocked and accessible |
| 108th & Broadway(US00007) | Cross-Contamination | G | -2 | Clumping sighted in cloud beverage. |
| 33rd & 10th(US00008) | Material Storage Location Specification | G | -2 | Lock Box unlocked and accessible. |
| 48th & 3rd(US00009) | Cross-Contamination | G | -2 | Lid isn’t closed |
| 48th & 3rd(US00009) | Cross-Contamination | G | -2 | Shouldn’t use this after defrost |
| 23rd & 8th(US00022) | Material Storage Location Specification | G | -2 | Lock box unlocked. |

**虫害防控**（4 项，扣分 -11；空描述跳过 0，超额省略 0）
| 门店(code) | 子项 | 严重度 | 扣分 | 描述原文 |
| --- | --- | --- | --- | --- |
| 15th & 3rd(US00024) | No Sign of Insect Pests | M | -5 | Live cockroach found running across floor. (Downstairs)  /  / Traps filled with bugs. |
| 21st & 3rd(US00020) | No Sign of Insect Pests | G | -2 | Flies seen on drainage system. |
| 21st & 3rd(US00020) | Prevent pests from outside | G | -2 | Air curtain out of commission. |
| 23rd & 8th(US00022) | Pest control devices | G | -2 | Service report for June missing. |

## [§3.1] 严重度分布（主巡检）

| 严重度 | 数量 | 占比 | SLA | 主要模块 |
| --- | --- | --- | --- | --- |
| S | 13 | 12.1% | 2 天 | 设施(10)、过程控制(2)、员工健康卫生(1) |
| M | 7 | 6.5% | 7 天 | 温控有效期(5)、清洁卫生(1)、虫害防控(1) |
| G | 72 | 67.3% | 14 天 | 清洁卫生(49)、过程控制(7)、职业安全(5)、设备维护(3)、设施(3) |
| L | 15 | 14.0% | 14 天 | 清洁卫生(15) |

## [§3.2] S 项明细（主巡检）

| # | 门店(code) | 模块/子项 | 描述原文 | 扣分 | 巡检类型 | 巡检员 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 54th & 8th(US00005) | 设施/Sinks and Pipes | Plumbing fixtures behind milk machine not to standard. | -5 | QA审计 | Eamonn Caballar |
| 2 | 102 Fulton(US00006) | 设施/Sinks and Pipes | Airgap compliance breached on following drains.  /  / 1. Ice Machine  / 2. Drain located under drip machine | -5 | QA审计 | Eamonn Caballar |
| 3 | 33rd & 10th(US00008) | 设施/Sinks and Pipes | Airgap not within standard. | -5 | QA审计 | Eamonn Caballar |
| 4 | 48th & 3rd(US00009) | 员工健康卫生/Handwashing Standards | No paper towel | -5 | 区经检查 | Jung Han Liang |
| 5 | 48th & 3rd(US00009) | 过程控制/Cross-Contamination | A spoiled milk isn’t disposed and not marked left in the mop sink | -5 | 区经检查 | Jung Han Liang |
| 6 | 154 Bleecker(US00010) | 设施/Sinks and Pipes | Handwashing / 3 compartment sink continues to flood upon draining. /  / Backflow Issue in drain under drip machine. | -5 | QA审计 | Eamonn Caballar |
| 7 | 40th & 10th(US00018) | 设施/Sinks and Pipes | Piping too close to filter / Wrapping coming off. | -5 | QA审计 | Eamonn Caballar |
| 8 | 29th & 3rd(US00019) | 设施/Sinks and Pipes | Faulty Pipe wrapping | -5 | QA审计 | Eamonn Caballar |
| 9 | 21st & 3rd(US00020) | 设施/Sinks and Pipes | Grease trap piping touching filter.  /  / Airgap under coffee machine. | -5 | QA审计 | Eamonn Caballar |
| 10 | 128 W 32nd St(US00021) | 过程控制/Cross-Contamination | Chia seeds in the container of smoothie powder.  / And | -5 | 区经检查 | Jung Han Liang |
| 11 | 15th & 3rd(US00024) | 设施/Sinks and Pipes | Airgap not in compliance. (3 compartment sink.) | -5 | QA审计 | Eamonn Caballar |
| 12 | 221 Grand(US00025) | 设施/Sinks and Pipes | Pipe touching filter under drip machine. | -5 | QA审计 | Eamonn Caballar |
| 13 | 52nd & Madison(US00027) | 设施/Sinks and Pipes | Air gap not within standard. (3 compartment sink.) | -5 | QA审计 | Eamonn Caballar |

## [§3.3] 全月 S 项汇总（按子项）

| 子项[模块] | S项数 | 门店数 | 典型问题(截取) |
| --- | --- | --- | --- |
| Sinks and Pipes[设施] | 17 | 11 | Air gap not reach 1 inch |
| Cross-Contamination[过程控制] | 7 | 7 | Please request a new ice machine, this is foreign object haz |
| Expiration Date[温控有效期] | 4 | 3 | Partners aren’t printing proper open labels |
| Foreign Material Control[过程控制] | 2 | 2 | This is potential risk to drop to oven or in the pastry bag |
| Handwashing Standards[员工健康卫生] | 1 | 1 | No paper towel |
| Product Storage Conditions[温控有效期] | 1 | 1 | Refrigeratorated materials left out of fridge and above temp |
| No Sign of Insect Pests[虫害防控] | 1 | 1 |  |

全月 S/M/G/L 合计：S 33 / M 59 / G 377 / L 169 = 638
主巡检 vs 全月：S 项 13/33；全部发现 107/638

## [§3.4] M 项明细（主巡检）

| # | 门店(code) | 模块/子项 | 描述原文 | 扣分 |
| --- | --- | --- | --- | --- |
| 1 | 100 Maiden Ln(US00003) | 温控有效期/Expiration Date | Missing date. | -5 |
| 2 | 54th & 8th(US00005) | 温控有效期/Expiration Date | Missing expiration label. | -5 |
| 3 | 54th & 8th(US00005) | 清洁卫生/Clean & Sanitize | Sanitizer reading below standard. | -5 |
| 4 | 102 Fulton(US00006) | 温控有效期/Expiration Date | Missing expiration date on syrup bottle. | -5 |
| 5 | 16th & 6th(US00012) | 温控有效期/Expiration Date | Missing expiration tag on syrup bottle. | -5 |
| 6 | 128 W 32nd St(US00021) | 温控有效期/Expiration Date | No label | -5 |
| 7 | 15th & 3rd(US00024) | 虫害防控/No Sign of Insect Pests | Live cockroach found running across floor. (Downstairs)  /  / Traps filled with bugs. | -5 |

## [§3.5] G/L 项按模块计数（主巡检）

- G 项：清洁卫生(49)，过程控制(7)，设施(3)，职业安全(5)，虫害防控(3)，员工健康卫生(2)，设备维护(3)
- L 项：清洁卫生(15)

## [§4.1] 门店 × 模块 扣分矩阵（主巡检）

| 门店(code) | 清洁卫生 | 过程控制 | 设施 | 证照 | 职业安全 | 虫害防控 | 温控有效期 | 员工健康卫生 | 设备维护 | 供应链 | 合计 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 54th & 8th(US00005) | -11 |  | -5 |  |  |  | -5 |  |  |  | -21 |
| 48th & 3rd(US00009) | -6 | -9 |  |  |  |  |  | -5 |  |  | -20 |
| 221 Grand(US00025) | -8 |  | -7 |  | -2 |  |  |  |  |  | -17 |
| 52nd & Madison(US00027) | -8 |  | -5 |  | -2 |  |  | -2 |  |  | -17 |
| 102 Fulton(US00006) | -6 |  | -5 |  |  |  | -5 |  |  |  | -16 |
| 128 W 32nd St(US00021) | -6 | -5 |  |  |  |  | -5 |  |  |  | -16 |
| 100 Maiden Ln(US00003) | -8 |  |  |  |  |  | -5 |  | -2 |  | -15 |
| 15th & 3rd(US00024) | -4 |  | -5 |  |  | -5 |  |  |  |  | -14 |
| 33rd & 10th(US00008) | -6 | -2 | -5 |  |  |  |  |  |  |  | -13 |
| 40th & 10th(US00018) | -6 |  | -5 |  |  |  |  |  | -2 |  | -13 |
| 21st & 3rd(US00020) | -4 |  | -5 |  |  | -4 |  |  |  |  | -13 |
| 154 Bleecker(US00010) | -7 |  | -5 |  |  |  |  |  |  |  | -12 |
| 41st & Lexington(US00015) | -4 |  | -2 |  | -4 |  |  |  | -2 |  | -12 |
| 108th & Broadway(US00007) | -7 | -4 |  |  |  |  |  |  |  |  | -11 |
| 8th & Broadway(US00001) | -6 |  |  |  | -2 |  |  |  |  |  | -8 |
| 28th & 6th(US00002) | -6 | -2 |  |  |  |  |  |  |  |  | -8 |
| 23rd & 8th(US00022) | -2 | -2 |  |  |  | -2 |  | -2 |  |  | -8 |
| 37th & Broadway(US00004) | -7 |  |  |  |  |  |  |  |  |  | -7 |
| 16th & 6th(US00012) | -2 |  |  |  |  |  | -5 |  |  |  | -7 |
| 29th & 3rd(US00019) | -2 |  | -5 |  |  |  |  |  |  |  | -7 |
| Grand Central Terminal(US00013) | -2 |  | -2 |  |  |  |  |  |  |  | -4 |
| 合计 | -118 | -24 | -56 |  | -10 | -11 | -25 | -9 | -6 |  | -259 |

100% 门店命中的模块：清洁卫生

## [§4.2] 最低分门店归因

- 门店：**128 W 32nd St(US00021)**　主巡检得分 **64**（区经检查，2026-07-28，Jung Han Liang）
  - 模块扣分构成：清洁卫生 -6，过程控制 -5，温控有效期 -5
  - S 项：Cross-Contamination “Chia seeds in the container of smoothie powder. 
And”
  - 新店？是（6月主巡检基准 —，环比 n/a；开业 2026-07-16）
- 门店：**48th & 3rd(US00009)**　主巡检得分 **60**（区经检查，2026-07-23，Jung Han Liang）
  - 模块扣分构成：过程控制 -9，清洁卫生 -6，员工健康卫生 -5
  - S 项：Handwashing Standards “No paper towel”；Cross-Contamination “A spoiled milk isn’t disposed and not marked left in the mop sink”
  - 新店？是（6月主巡检基准 —，环比 n/a；开业 2026-06-30）

## [§4.3] 申诉明细（全量）

| 门店(code) | 巡检类型 | 申诉结果 | 日期 | 分数变动(orig→adj) | 巡检员 |
| --- | --- | --- | --- | --- | --- |
| 8th & Broadway(US00001) | QA审计 | 获批※ | 2026-07-24 | 92→94 | Eamonn Caballar |
| 28th & 6th(US00002) | QA审计 | 获批※ | 2026-07-16 | 92→94 | Eamonn Caballar |
| 100 Maiden Ln(US00003) | 区经检查 | 获批※ | 2026-07-31 | 79→81 | Jung Han Liang |
| 54th & 8th(US00005) | QA审计 | 获批※ | 2026-07-09 | 59→84 | Eamonn Caballar |
| 102 Fulton(US00006) | QA审计 | 获批※ | 2026-07-14 | 64→91 | Eamonn Caballar |
| 33rd & 10th(US00008) | QA审计 | 获批※ | 2026-07-08 | 67→92 | Eamonn Caballar |
| 154 Bleecker(US00010) | QA审计 | 获批※ | 2026-07-23 | 68→95 | Eamonn Caballar |
| 41st & Lexington(US00015) | QA审计 | 获批※ | 2026-07-07 | 88→94 | Eamonn Caballar |
| 40th & 10th(US00018) | QA审计 | 获批※ | 2026-07-24 | 67→94 | Eamonn Caballar |
| 29th & 3rd(US00019) | QA审计 | 获批※ | 2026-07-21 | 73→98 | Eamonn Caballar |
| 21st & 3rd(US00020) | QA审计 | 获批※ | 2026-07-21 | 67→94 | Eamonn Caballar |
| 15th & 3rd(US00024) | QA审计 | 获批※ | 2026-07-21 | 66→91 | Eamonn Caballar |
| 15th & 3rd(US00024) | 区经检查 | 获批※ | 2026-07-31 | 83→85 | Jung Han Liang |
| 221 Grand(US00025) | QA审计 | 获批※ | 2026-07-23 | 63→94 | Eamonn Caballar |
| 221 Grand(US00025) | 区经检查 | 获批※ | 2026-07-31 | 59→84 | Jung Han Liang |
| 52nd & Madison(US00027) | QA审计 | 获批※ | 2026-07-09 | 63→90 | Eamonn Caballar |
| 16th & 6th(US00012) | 区经检查 | 审批中 | 2026-07-22 | 93→93 | Jung Han Liang |
| Grand Central Terminal(US00013) | 区经检查 | 审批中 | 2026-07-23 | 96→96 | Jung Han Liang |
| 40th & 10th(US00018) | 区经检查 | 审批中 | 2026-07-24 | 69→69 | Jung Han Liang |

合计 **19 起（16 获批 / 0 驳回 / 3 审批中）**
申诉相关 finding 条数：37

## [§4.4] 同店跨类型背离（≥20分）

| 门店(code) | 较低类型(分) | 较高类型(分) | 差值 | 一句解读 |
| --- | --- | --- | --- | --- |
| 41st & Lexington(US00015) | 自检(54.0) | QA(94) | 40.0 | 自检(54.0)偏严于QA(94)，一线自查更保守 |
| 28th & 6th(US00002) | 区经(57) | QA(94) | 37 | 区经(57)较QA(94)严格，正式巡检间尺度差异 |
| 154 Bleecker(US00010) | 区经(62) | QA(95) | 33 | 区经(62)较QA(95)严格，正式巡检间尺度差异 |
| 128 W 32nd St(US00021) | 区经(64) | 自检(94.0) | 30.0 | 自检(94.0)显著宽松，区经(64)暴露更多问题 |
| 48th & 3rd(US00009) | 区经(60) | 自检(85.7) | 25.7 | 自检(85.7)显著宽松，区经(60)暴露更多问题 |
| 29th & 3rd(US00019) | 自检(72.5) | QA(98) | 25.5 | 自检(72.5)偏严于QA(98)，一线自查更保守 |
| 102 Fulton(US00006) | 区经(66) | QA(91) | 25 | 区经(66)较QA(91)严格，正式巡检间尺度差异 |
| 40th & 10th(US00018) | 区经(69) | QA(94) | 25 | 区经(69)较QA(94)严格，正式巡检间尺度差异 |
| 21st & 3rd(US00020) | 自检(71.0) | QA(94) | 23.0 | 自检(71.0)偏严于QA(94)，一线自查更保守 |

## [§4.5] 模块覆盖表（主巡检）

| 模块 | 影响门店(n/N) | 覆盖率 | 扣分 | 风险 |
| --- | --- | --- | --- | --- |
| 清洁卫生 | 21/21 | 100.0% | -118 | 🔴 |
| 设施 | 12/21 | 57.1% | -56 | 🔴 |
| 温控有效期 | 5/21 | 23.8% | -25 | 🟢 |
| 过程控制 | 6/21 | 28.6% | -24 | 🟢 |
| 虫害防控 | 3/21 | 14.3% | -11 | 🟢 |
| 职业安全 | 4/21 | 19.0% | -10 | 🟢 |
| 员工健康卫生 | 3/21 | 14.3% | -9 | 🟢 |
| 设备维护 | 3/21 | 14.3% | -6 | 🟢 |

## [§5.1] 关键词归因（全部发现）

| 归因类别 | 数量 | 占比 | 典型问题 |
| --- | --- | --- | --- |
| 门店 | 370 | 58.0% | 日常清洁、消毒、标签、储存卫生 |
| 机修+营建 | 99 | 15.5% | sinks and pipes / air gap / 油脂阱 / 灯具 / 门 |
| 供应链+行政 | 14 | 2.2% | license / certificate / 文件记录 / no smoking sign |
| 未知 | 155 | 24.3% | 描述缺失或少于 10 字符 |

空/短描述（<10字符）占比：155/638 = 24.3%（其中门店自检 136 条）

## [§7.1] 三类巡检总览

| 巡检类型 | 次数 | 覆盖门店(n/N) | 巡检员数 | 平均分 | S项 | M项 | 日期区间 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 门店自检 | 54 | 21/21 | 27 | 80.5 | 15 | 30 | 2026-07-01~2026-07-31 |
| QA审计 | 19 | 18/21 | 1 | 92.5 | 10 | 6 | 2026-07-07~2026-07-24 |
| 区经检查 | 21 | 21/21 | 1 | 78.9 | 8 | 23 | 2026-07-08~2026-07-31 |

## [§7.2] 同店三类对比

| 门店(code) | 自检均分 | QA审计 | 区经检查 | QA-自检差 |
| --- | --- | --- | --- | --- |
| 8th & Broadway(US00001) | 89.5 | 94 | 94 | 4.5 |
| 28th & 6th(US00002) | 94.0 | 94 | 57 | 0.0 |
| 100 Maiden Ln(US00003) | 93.0 | 85 | 81 | -8.0 |
| 37th & Broadway(US00004) | 87.2 | 93 | 84 | 5.8 |
| 54th & 8th(US00005) | 87.5 | 84 | 82 | -3.5 |
| 102 Fulton(US00006) | 75.0 | 91 | 66 | 16.0 |
| 108th & Broadway(US00007) | 78.7 | 89 | 75 | 10.3 |
| 33rd & 10th(US00008) | 80.3 | 92 | 89 | 11.7 |
| 48th & 3rd(US00009) | 85.7 |  | 60 |  |
| 154 Bleecker(US00010) | 70.5 | 95 | 62 | 24.5 |
| 16th & 6th(US00012) | 82.0 | 93 | 93 | 11.0 |
| Grand Central Terminal(US00013) | 84.0 |  | 96 |  |
| 41st & Lexington(US00015) | 54.0 | 94 | 88 | 40.0 |
| 40th & 10th(US00018) | 77.2 | 94 | 69 | 16.8 |
| 29th & 3rd(US00019) | 72.5 | 98 | 79 | 25.5 |
| 21st & 3rd(US00020) | 71.0 | 94 | 76 | 23.0 |
| 128 W 32nd St(US00021) | 94.0 |  | 64 |  |
| 23rd & 8th(US00022) | 91.5 | 92 | 92 | 0.5 |
| 15th & 3rd(US00024) | 76.0 | 91 | 85 | 15.0 |
| 221 Grand(US00025) | 88.0 | 94 | 84 | 6.0 |
| 52nd & Madison(US00027) | 80.7 | 90 | 80 | 9.3 |

## [§7.3] 自检一致性（同员同店≥2次）

| 巡检员 | 门店(code) | 次数 | 历次得分 | 摆动(max-min) |
| --- | --- | --- | --- | --- |
| Laurel Vorhies | 16th & 6th(US00012) | 3 | 59→94→93 | 35 |
| Afsana Gu | 41st & Lexington(US00015) | 3 | 29→37→58 | 29 |
| Yaqing Zuo | 33rd & 10th(US00008) | 3 | 68→81→92 | 24 |
| Jian Ming Juo | 40th & 10th(US00018) | 4 | 89→77→73→70 | 19 |
| Joselyn Pacheco Trejo | Grand Central Terminal(US00013) | 2 | 75→93 | 18 |
| Austin Gebhardt | 108th & Broadway(US00007) | 3 | 79→87→70 | 17 |
| Huichen Jiang | 8th & Broadway(US00001) | 2 | 80→95 | 15 |
| Derson Liang | 37th & Broadway(US00004) | 5 | 81→80→94→90→91 | 14 |
| Javier Cruz | 21st & 3rd(US00020) | 2 | 78→64 | 14 |
| Juliana Li | 48th & 3rd(US00009) | 3 | 82→83→92 | 10 |
| Wenny Lin | 52nd & Madison(US00027) | 3 | 76→84→82 | 8 |
| Andrew Chen | 23rd & 8th(US00022) | 2 | 89→94 | 5 |
| Andrew Hu | 8th & Broadway(US00001) | 2 | 90→93 | 3 |
| Eric Park | 54th & 8th(US00005) | 2 | 89→86 | 3 |
| Alexander G Harry | 154 Bleecker(US00010) | 2 | 71→70 | 1 |

最大摆动：Laurel Vorhies @ 16th & 6th(US00012) 摆动 35

## [§7.4] 巡检员尺度（≥2次）

| 巡检员 | 角色 | 巡检类型 | 次数 | 均分 | 尺度 |
| --- | --- | --- | --- | --- | --- |
| Afsana Gu | Store Manager | 门店自检 | 3 | 41.3 | 偏严(<70) |
| Alexander G Harry | Store Manager | 门店自检 | 2 | 70.5 | 正常 |
| Javier Cruz | Store Manager | 门店自检 | 2 | 71.0 | 正常 |
| Jian Ming Juo | Store Manager | 门店自检 | 4 | 77.2 | 正常 |
| Austin Gebhardt | Store Manager | 门店自检 | 2 | 78.5 | 正常 |
| Jung Han Liang | Area Operations Manager | 区经检查 | 21 | 78.9 | 正常 |
| Yaqing Zuo | Store Manager | 门店自检 | 3 | 80.3 | 正常 |
| Wenny Lin | Store Manager | 门店自检 | 3 | 80.7 | 正常 |
| Laurel Vorhies | Store Manager | 门店自检 | 3 | 82.0 | 正常 |
| Joselyn Pacheco Trejo | Store Manager | 门店自检 | 2 | 84.0 | 正常 |
| Juliana Li | Store Manager | 门店自检 | 3 | 85.7 | 正常 |
| Derson Liang | Assistant Store Manager | 门店自检 | 5 | 87.2 | 正常 |
| Huichen Jiang | Store Manager | 门店自检 | 2 | 87.5 | 正常 |
| Eric Park | Store Manager | 门店自检 | 2 | 87.5 | 正常 |
| Andrew Hu | Assistant Store Manager | 门店自检 | 3 | 88.3 | 正常 |
| Andrew Chen | Store Manager | 门店自检 | 2 | 91.5 | 正常 |
| Eamonn Caballar | Senior QA Manager | QA审计 | 19 | 92.5 | 偏宽(>92) |

## [§7.5] 覆盖趋势（1–7月）

| 月份 | 自检 | QA | 区经 | 合计 | 自检均分 | QA均分 | 区经均分 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-01 | 7 | 5 | 4 | 16 |  |  |  |
| 2026-02 | 5 | 2 | 0 | 7 |  |  |  |
| 2026-03 | 13 | 1 | 0 | 14 |  |  |  |
| 2026-04 | 32 | 12 | 14 | 58 | 80.2 | 84.6 | 80.1 |
| 2026-05 | 49 | 16 | 21 | 86 | 81.3 | 85.1 | 82.2 |
| 2026-06 | 51 | 16 | 18 | 85 | 82.8 | 88.2 | 84.3 |
| 2026-07 | 54 | 19 | 21 | 94 | 80.5 | 92.5 | 78.9 |

## [§7.6] 三类发现差异

| 巡检类型 | S项 | M项 | 价值说明 |
| --- | --- | --- | --- |
| 门店自检 | 15 | 30 | 高频暴露（日常一线自查） |
| QA审计 | 10 | 6 | 专业定级 / 结构性 S 项（air gap 等） |
| 区经检查 | 8 | 23 | 全覆盖复核 |

## [§X] 跨月 S 项子项对比（6月 vs 7月，全月口径）

| 子项 | 6月S项 | 6月门店 | 7月S项 | 7月门店 | Δ |
| --- | --- | --- | --- | --- | --- |
| Sinks and Pipes | 13 | 10 | 17 | 11 | 4 |
| Cross-Contamination | 3 | 3 | 7 | 7 | 4 |
| Expiration Date | 1 | 1 | 4 | 3 | 3 |
| Foreign Material Control | 0 | 0 | 2 | 2 | 2 |
| Handwashing Standards | 3 | 3 | 1 | 1 | -2 |
| No Sign of Insect Pests | 0 | 0 | 1 | 1 | 1 |
| Product Storage Conditions | 1 | 1 | 1 | 1 | 0 |
| Personal certificate | 1 | 1 | 0 | 0 | -1 |
| Site Security | 1 | 1 | 0 | 0 | -1 |

**Sinks and Pipes** 跨月门店：6月 10 家、7月 11 家、连续两月复现 **9** 家 → 54th & 8th(US00005), 102 Fulton(US00006), 33rd & 10th(US00008), 154 Bleecker(US00010), 29th & 3rd(US00019), 21st & 3rd(US00020), 15th & 3rd(US00024), 221 Grand(US00025), 52nd & Madison(US00027)
7月新增（6月无）：28th & 6th(US00002), 40th & 10th(US00018)
7月已消除（6月有）：16th & 6th(US00012)