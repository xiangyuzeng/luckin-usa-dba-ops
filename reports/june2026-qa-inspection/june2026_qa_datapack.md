# June 2026 QA 门店稽核 — 数据包 (DATA PACK)
- Doc: **LCNA-QA-2026-006**  ·  Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol
- Window: 2026-06-01 .. 2026-06-30 (30 天, closed month)  ·  Built by DBA data-collection agent
- Scope locks: 主巡检 (QA审计>区经检查>门店自检, latest) for §2.2/§2.3/§3.1/§3.2/§3.4/§3.5/§4.1/§4.5/§7 per-type; 全月 for §3.3/§7.x totals
- **UNMAPPED resolution**: raw module "Site Security" → 职业安全 (user-confirmed 2026-07-01)

## [COVER/文档信息]

- 文档编号：**LCNA-QA-2026-006**　报告期：**2026年6月**（2026-06-01 .. 2026-06-30，30 天）
- 活跃门店：**18 家运营在营门店**（主巡检口径）；另有 2 家 6/30 新开业未及巡检 → 计 20 家在营门店
  - 计数口径：t_shop_info status=1 且非测试厨房（SL12/US999xx/US00000），open_date≤2026-06-30；6/30 新开业=48th & 3rd(US00009), Grand Central Terminal(US00013)
- 巡检类型次数：门店自检 51 / QA审计 16 / 区经检查 18 = **共 85 次**（86 次提交 − 1 误提交 = 85）
- 全月发现项：S 23 / M 44 / G 301 / L 130 = **498**
- 主巡检发现项：S 8 / M 6 / G 58 / L 16 = **88**
- 申诉：**10 起立案（7 获批 / 0 驳回 / 3 审批中）**
- QA 审计人员：Eamonn Caballar 16 次（Senior QA Manager）
- 区经检查人员：Jung Han Liang 18 次（Area Operations Manager）

## [§管理摘要]

- 主巡检均分 **88.7**（5月 85.8，**+2.9**）；门店覆盖 **18/18 = 100%**（5月基准 18 家）
- 全月发现项合计 **498**（主巡检 88）
- (a) 体系里程碑 vs 5月：巡检量 85（5月 86，−1 次）；主巡检均分 85.8→88.7（**+2.9**）；覆盖率维持 100%
- (b) 最大系统性 S 项集群：**Sinks and Pipes** — 13 项 S，涉及 10 家门店（延续 5 月 air gap / Sinks and Pipes 遗留）
- (c) 巡检员一致性旗标：4 家门店存在同店跨类型 ≥20 分背离 → 154 Bleecker(US00010) [区经 58 / QA 92 / 自检 78.5]（差 34）；54th & 8th(US00005) [区经 62 / QA 71 / 自检 92.0]（差 30.0）；16th & 6th(US00012) [区经 70 / QA 91 / 自检 88.7]（差 21）；108th & Broadway(US00007) [区经 87 / QA 91 / 自检 71.0]（差 20.0）
  - 最大改善：108th & Broadway(US00007) 65→91（+26）
  - 最大下滑：52nd & Madison(US00027) 84→64（-20）

## [§1.1] 主巡检概览

- 最高分门店：**21st & 3rd(US00020) = 97**
- 最低分门店：**52nd & Madison(US00027) = 64**
- S 项门店数：**8** 家（54th & 8th(US00005), 102 Fulton(US00006), 33rd & 10th(US00008), 154 Bleecker(US00010), 29th & 3rd(US00019), 21st & 3rd(US00020), 221 Grand(US00025), 52nd & Madison(US00027)）
- <80 分门店数：**2** 家（52nd & Madison(US00027) 64, 54th & 8th(US00005) 71）
- 覆盖率：**18/18 = 100%**（5月 18/18 = 100%）

## [§1.2] 主巡检全门店明细（按得分降序）

| # | 门店 | 编号 | 得分 | 巡检类型 | 扣分 | S | M | G | L | 巡检员 | ※ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 21st & 3rd | US00020 | 97 | QA审计 | -8 | 1 | 0 | 1 | 1 | Eamonn Caballar | ※ |
| 2 | 41st & Lexington | US00015 | 95 | QA审计 | -7 | 0 | 0 | 3 | 1 | Eamonn Caballar | ※ |
| 3 | 33rd & 10th | US00008 | 94 | QA审计 | -11 | 1 | 0 | 3 | 0 | Eamonn Caballar | ※ |
| 4 | 29th & 3rd | US00019 | 94 | QA审计 | -15 | 1 | 0 | 5 | 0 | Eamonn Caballar | ※ |
| 5 | 221 Grand | US00025 | 94 | QA审计 | -13 | 1 | 0 | 3 | 2 | Eamonn Caballar | ※ |
| 6 | 102 Fulton | US00006 | 93 | QA审计 | -12 | 1 | 0 | 3 | 1 | Eamonn Caballar | ※ |
| 7 | 23rd & 8th | US00022 | 93 | 区经检查 | -7 | 0 | 1 | 1 | 0 | Jung Han Liang |  |
| 8 | 154 Bleecker | US00010 | 92 | QA审计 | -13 | 1 | 0 | 4 | 0 | Eamonn Caballar | ※ |
| 9 | 108th & Broadway | US00007 | 91 | QA审计 | -9 | 0 | 0 | 4 | 1 | Eamonn Caballar |  |
| 10 | 16th & 6th | US00012 | 91 | QA审计 | -9 | 0 | 0 | 4 | 1 | Eamonn Caballar |  |
| 11 | 40th & 10th | US00018 | 91 | 区经检查 | -9 | 0 | 0 | 4 | 1 | Jung Han Liang |  |
| 12 | 37th & Broadway | US00004 | 89 | QA审计 | -11 | 0 | 1 | 2 | 2 | Eamonn Caballar |  |
| 13 | 15th & 3rd | US00024 | 88 | QA审计 | -12 | 0 | 0 | 5 | 2 | Eamonn Caballar |  |
| 14 | 8th & Broadway | US00001 | 87 | QA审计 | -13 | 0 | 1 | 3 | 2 | Eamonn Caballar |  |
| 15 | 28th & 6th | US00002 | 86 | QA审计 | -14 | 0 | 2 | 2 | 0 | Eamonn Caballar |  |
| 16 | 100 Maiden Ln | US00003 | 86 | QA审计 | -14 | 0 | 1 | 4 | 1 | Eamonn Caballar |  |
| 17 | 54th & 8th | US00005 | 71 | QA审计 | -9 | 1 | 0 | 2 | 0 | Eamonn Caballar |  |
| 18 | 52nd & Madison | US00027 | 64 | QA审计 | -16 | 1 | 0 | 5 | 1 | Eamonn Caballar |  |

注：扣分=名义扣分（Σ score_config，与 S/M/G/L 计数一致，不随申诉变动）；得分=官方调整后分（申诉获批已反映）；※=申诉获批调整。

## [§1.3] 分数带 / 跨月 / 申诉 / 背离 / 自检 S 项

- 分数带：≥85 **16** 家 / 80–84 **0** 家 / <80 **2** 家
- S 项分布：8 家主巡检含 S 项
- 环比改善（11 家）：108th & Broadway(US00007) 65→91(+26)，102 Fulton(US00006) 77→93(+16)，33rd & 10th(US00008) 83→94(+11)，21st & 3rd(US00020) 89→97(+8)，41st & Lexington(US00015) 90→95(+5)，221 Grand(US00025) 89→94(+5)，54th & 8th(US00005) 67→71(+4)，23rd & 8th(US00022) 91→93(+2)，15th & 3rd(US00024) 86→88(+2)，37th & Broadway(US00004) 88→89(+1)，29th & 3rd(US00019) 93→94(+1)
- 环比下滑（5 家）：52nd & Madison(US00027) 84→64(-20)，100 Maiden Ln(US00003) 91→86(-5)，8th & Broadway(US00001) 89→87(-2)，16th & 6th(US00012) 93→91(-2)，40th & 10th(US00018) 92→91(-1)
- 最大变动：改善 108th & Broadway(US00007) +26；下滑 52nd & Madison(US00027) -20
- 申诉调整门店（7 家 ※）：102 Fulton(US00006), 33rd & 10th(US00008), 154 Bleecker(US00010), 41st & Lexington(US00015), 29th & 3rd(US00019), 21st & 3rd(US00020), 221 Grand(US00025)
- 同店跨类型背离（≥20分）：154 Bleecker(US00010) [区经 58 / QA 92 / 自检 78.5](差34)；54th & 8th(US00005) [区经 62 / QA 71 / 自检 92.0](差30.0)；16th & 6th(US00012) [区经 70 / QA 91 / 自检 88.7](差21)；108th & Broadway(US00007) [区经 87 / QA 91 / 自检 71.0](差20.0)
- 自检发现 S 项（10 项）：8th & Broadway(US00001) Cross-Contamination “Tongs are dirty (cross contamination)”；108th & Broadway(US00007) Cross-Contamination “”；33rd & 10th(US00008) Site Security “No employee only indicator on BOH doors”；154 Bleecker(US00010) Handwashing Standards “No trash near handwashing sink”；40th & 10th(US00018) Cross-Contamination “”；29th & 3rd(US00019) Personal certificate “”；21st & 3rd(US00020) Handwashing Standards “A paper towel dispenser was low on paper”；15th & 3rd(US00024) Sinks and Pipes “”；221 Grand(US00025) Product Storage Conditions “Missing standing thermometer”；52nd & Madison(US00027) Expiration Date “No expiration date”

## [§2.1] 模块风险分层（主巡检覆盖率）

- 🔴 ≥50% 门店：清洁卫生(100.0%), 设施(61.1%)
- 🟡 30–49% 门店：过程控制(44.4%)
- 🟢 <30% 门店：证照(5.6%), 职业安全(5.6%), 温控有效期(11.1%), 员工健康卫生(16.7%)

## [§2.2] 模块排名（主巡检，按扣分）

| 模块 | 问题数 | 扣分 | 门店(n/N) | 覆盖率 | S | M | G | L | 风险 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 清洁卫生 | 59 | -108 | 18/18 | 100.0% | 0 | 2 | 41 | 16 | 🔴 |
| 设施 | 13 | -53 | 11/18 | 61.1% | 8 | 1 | 4 | 0 | 🔴 |
| 过程控制 | 9 | -18 | 8/18 | 44.4% | 0 | 0 | 9 | 0 | 🟡 |
| 温控有效期 | 2 | -10 | 2/18 | 11.1% | 0 | 2 | 0 | 0 | 🟢 |
| 员工健康卫生 | 3 | -6 | 3/18 | 16.7% | 0 | 0 | 3 | 0 | 🟢 |
| 证照 | 1 | -5 | 1/18 | 5.6% | 0 | 1 | 0 | 0 | 🟢 |
| 职业安全 | 1 | -2 | 1/18 | 5.6% | 0 | 0 | 1 | 0 | 🟢 |

Σ主巡检模块扣分 = -202

## [§2.3] 扣分 Top5 模块逐条发现（主巡检，原文）


**清洁卫生**（59 项，扣分 -108；空描述跳过 1，超额省略 38）
| 门店(code) | 子项 | 严重度 | 扣分 | 描述原文 |
| --- | --- | --- | --- | --- |
| 28th & 6th(US00002) | Clean & Sanitize | M | -5 | Multiple noncompliant reading of PPM taken from food processing sani buckets. |
| 37th & Broadway(US00004) | Clean & Sanitize | M | -5 | Sanitizer stains on ice machine. |
| 8th & Broadway(US00001) | Equipment and utensils | G | -2 | Dust on refrigerator tops. |
| 28th & 6th(US00002) | Equipment and utensils | G | -2 | Dust found on refrigerator doors. |
| 28th & 6th(US00002) | Equipment and utensils | G | -2 | Coffee grounds found on grinder. /  / Matcha staining found on rubber mat of blender. |
| 100 Maiden Ln(US00003) | Equipment and utensils | G | -2 | Dust found on tops of fridges. |
| 100 Maiden Ln(US00003) | Equipment and utensils | G | -2 | Sanitizer residue found on ice machine.  /  / Significant amount of dust on top of Ice machine |
| 100 Maiden Ln(US00003) | Equipment and utensils | G | -2 | Food residue found in warming station utensils. |
| 37th & Broadway(US00004) | Equipment and utensils | G | -2 | Dust found on refrigerator tops. |
| 37th & Broadway(US00004) | Equipment and utensils | G | -2 | Matcha stains on dispensers.  / Matcha stains on blender pads. |
| 54th & 8th(US00005) | Clean & Sanitize | G | -2 | Tasks out of grace period. |
| 54th & 8th(US00005) | Equipment and utensils | G | -2 | Sanitizer Residue found in Ice machine  /  / Plastic found in warming oven vent. |
| 102 Fulton(US00006) | Equipment and utensils | G | -2 | Dust on tops of fridges.  /  / Staining on inside of fridges. |
| 108th & Broadway(US00007) | Equipment and utensils | G | -2 | Dust located on tops of refrigerators. |
| 108th & Broadway(US00007) | Equipment and utensils | G | -2 | Utensils with food residue. |
| 33rd & 10th(US00008) | Equipment and utensils | G | -2 | Dust located on refrigerator door hinges. |
| 33rd & 10th(US00008) | Clean & Sanitize | G | -2 | Tasks outside 15 min window. |
| 33rd & 10th(US00008) | Equipment and utensils | G | -2 | Sanitizer residue found in ice machine.  /  / Food residue on blenders. |
| 154 Bleecker(US00010) | Equipment and utensils | G | -2 | Dust on refrigerators. |
| 154 Bleecker(US00010) | Equipment and utensils | G | -2 | Dust found on top of lock box, Ice machine, drip machine, light food display. |

**设施**（13 项，扣分 -53；空描述跳过 0，超额省略 0）
| 门店(code) | 子项 | 严重度 | 扣分 | 描述原文 |
| --- | --- | --- | --- | --- |
| 54th & 8th(US00005) | Sinks and Pipes | S | -5 | Airgap issue found behind milk machine. /  / Significant leak behind dish washer. |
| 102 Fulton(US00006) | Sinks and Pipes | S | -5 | Ice machine pipe not properly connected. Causing flow issues.  /  / Airgap under three compartment sink not compliant. (outlet distance.) |
| 33rd & 10th(US00008) | Sinks and Pipes | S | -5 | Airgap is non compliant. (Outlet Pipe) |
| 154 Bleecker(US00010) | Sinks and Pipes | S | -5 | Piping for 3 compartment sink not in compliance. |
| 29th & 3rd(US00019) | Sinks and Pipes | S | -5 | Pipe under rinsing sink not properly wrapped. /  / Faucet not properly connected. |
| 21st & 3rd(US00020) | Sinks and Pipes | S | -5 | Non compliant outlet pipe. Less than one inch. |
| 221 Grand(US00025) | Sinks and Pipes | S | -5 | Airgap out of compliance. |
| 52nd & Madison(US00027) | Sinks and Pipes | S | -5 | Air gap non compliant. |
| 8th & Broadway(US00001) | Good condition | M | -5 | Lights in storage area are inoperable. |
| 41st & Lexington(US00015) | Good condition | G | -2 | Floors with unclean-able stains. |
| 29th & 3rd(US00019) | Good condition | G | -2 | Hole in wall found in boiler room. |
| 29th & 3rd(US00019) | Sinks and Pipes | G | -2 | Backflow located on water dispenser (Location: Milk Machine) |
| 15th & 3rd(US00024) | Sinks and Pipes | G | -2 | Leak sighted under rinsing sink. |

**过程控制**（9 项，扣分 -18；空描述跳过 0，超额省略 0）
| 门店(code) | 子项 | 严重度 | 扣分 | 描述原文 |
| --- | --- | --- | --- | --- |
| 8th & Broadway(US00001) | Cross-Contamination | G | -2 | 2 Pitchers found uncovered and exposed to air in storage. |
| 8th & Broadway(US00001) | Cross-Contamination | G | -2 | Cloud Beverage clumping. Signs of moisture. |
| 100 Maiden Ln(US00003) | Cross-Contamination | G | -2 | Clumping food material found in 9th pan. |
| 102 Fulton(US00006) | Cross-Contamination | G | -2 | Pitcher exposed after use. |
| 108th & Broadway(US00007) | Cross-Contamination | G | -2 | Signs of moisture in 9th pans. |
| 154 Bleecker(US00010) | Cross-Contamination | G | -2 | Pitcher found exposed to open air. |
| 16th & 6th(US00012) | Storage/Maintenance of Utensils | G | -2 | Utensils sitting on standing water. (Location: Milk Station Pad) |
| 15th & 3rd(US00024) | Cross-Contamination | G | -2 | Clumping sighted in cloud powder. |
| 52nd & Madison(US00027) | Cross-Contamination | G | -2 | Signs of moisture found in cloud powder. |

**温控有效期**（2 项，扣分 -10；空描述跳过 0，超额省略 0）
| 门店(code) | 子项 | 严重度 | 扣分 | 描述原文 |
| --- | --- | --- | --- | --- |
| 28th & 6th(US00002) | Expiration Date | M | -5 | Missing expiration date label on syrup bottle. |
| 100 Maiden Ln(US00003) | Expiration Date | M | -5 | Missing expiration date on product. |

**员工健康卫生**（3 项，扣分 -6；空描述跳过 0，超额省略 0）
| 门店(code) | 子项 | 严重度 | 扣分 | 描述原文 |
| --- | --- | --- | --- | --- |
| 102 Fulton(US00006) | Personal Hygiene | G | -2 | Personal item found on work floor. |
| 40th & 10th(US00018) | Personal Hygiene | G | -2 | One of female partners nail is not trimmed |
| 52nd & Madison(US00027) | Personal Hygiene | G | -2 | Employee wearing hat backwards. |

## [§3.1] 严重度分布（主巡检）

| 严重度 | 数量 | 占比 | SLA | 主要模块 |
| --- | --- | --- | --- | --- |
| S | 8 | 9.1% | 2 天 | 设施(8) |
| M | 6 | 6.8% | 7 天 | 温控有效期(2)、清洁卫生(2)、设施(1) |
| G | 58 | 65.9% | 14 天 | 清洁卫生(41)、过程控制(9)、设施(4) |
| L | 16 | 18.2% | 14 天 | 清洁卫生(16) |

## [§3.2] S 项明细（主巡检）

| # | 门店(code) | 模块/子项 | 描述原文 | 扣分 | 巡检类型 | 巡检员 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 54th & 8th(US00005) | 设施/Sinks and Pipes | Airgap issue found behind milk machine. /  / Significant leak behind dish washer. | -5 | QA审计 | Eamonn Caballar |
| 2 | 102 Fulton(US00006) | 设施/Sinks and Pipes | Ice machine pipe not properly connected. Causing flow issues.  /  / Airgap under three compartment sink not compliant. (outlet distance.) | -5 | QA审计 | Eamonn Caballar |
| 3 | 33rd & 10th(US00008) | 设施/Sinks and Pipes | Airgap is non compliant. (Outlet Pipe) | -5 | QA审计 | Eamonn Caballar |
| 4 | 154 Bleecker(US00010) | 设施/Sinks and Pipes | Piping for 3 compartment sink not in compliance. | -5 | QA审计 | Eamonn Caballar |
| 5 | 29th & 3rd(US00019) | 设施/Sinks and Pipes | Pipe under rinsing sink not properly wrapped. /  / Faucet not properly connected. | -5 | QA审计 | Eamonn Caballar |
| 6 | 21st & 3rd(US00020) | 设施/Sinks and Pipes | Non compliant outlet pipe. Less than one inch. | -5 | QA审计 | Eamonn Caballar |
| 7 | 221 Grand(US00025) | 设施/Sinks and Pipes | Airgap out of compliance. | -5 | QA审计 | Eamonn Caballar |
| 8 | 52nd & Madison(US00027) | 设施/Sinks and Pipes | Air gap non compliant. | -5 | QA审计 | Eamonn Caballar |

## [§3.3] 全月 S 项汇总（按子项）

| 子项[模块] | S项数 | 门店数 | 典型问题(截取) |
| --- | --- | --- | --- |
| Sinks and Pipes[设施] | 13 | 10 | Two pipe issues |
| Cross-Contamination[过程控制] | 3 | 3 | Tongs are dirty (cross contamination) |
| Handwashing Standards[员工健康卫生] | 3 | 3 | No trash near handwashing sink |
| Site Security[职业安全] | 1 | 1 | No employee only indicator on BOH doors |
| Personal certificate[证照] | 1 | 1 |  |
| Product Storage Conditions[温控有效期] | 1 | 1 | Missing standing thermometer |
| Expiration Date[温控有效期] | 1 | 1 | No expiration date |

全月 S/M/G/L 合计：S 23 / M 44 / G 301 / L 130 = 498
主巡检 vs 全月：S 项 8/23；全部发现 88/498

## [§3.4] M 项明细（主巡检）

| # | 门店(code) | 模块/子项 | 描述原文 | 扣分 |
| --- | --- | --- | --- | --- |
| 1 | 8th & Broadway(US00001) | 设施/Good condition | Lights in storage area are inoperable. | -5 |
| 2 | 28th & 6th(US00002) | 温控有效期/Expiration Date | Missing expiration date label on syrup bottle. | -5 |
| 3 | 28th & 6th(US00002) | 清洁卫生/Clean & Sanitize | Multiple noncompliant reading of PPM taken from food processing sani buckets. | -5 |
| 4 | 100 Maiden Ln(US00003) | 温控有效期/Expiration Date | Missing expiration date on product. | -5 |
| 5 | 37th & Broadway(US00004) | 清洁卫生/Clean & Sanitize | Sanitizer stains on ice machine. | -5 |
| 6 | 23rd & 8th(US00022) | 证照/Licenses and certificates | Missing handwashing sign | -5 |

## [§3.5] G/L 项按模块计数（主巡检）

- G 项：清洁卫生(41)，过程控制(9)，设施(4)，职业安全(1)，员工健康卫生(3)
- L 项：清洁卫生(16)

## [§4.1] 门店 × 模块 扣分矩阵（主巡检）

| 门店(code) | 清洁卫生 | 过程控制 | 设施 | 证照 | 职业安全 | 虫害防控 | 温控有效期 | 员工健康卫生 | 设备维护 | 供应链 | 合计 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 52nd & Madison(US00027) | -7 | -2 | -5 |  |  |  |  | -2 |  |  | -16 |
| 29th & 3rd(US00019) | -6 |  | -9 |  |  |  |  |  |  |  | -15 |
| 28th & 6th(US00002) | -9 |  |  |  |  |  | -5 |  |  |  | -14 |
| 100 Maiden Ln(US00003) | -7 | -2 |  |  |  |  | -5 |  |  |  | -14 |
| 8th & Broadway(US00001) | -4 | -4 | -5 |  |  |  |  |  |  |  | -13 |
| 154 Bleecker(US00010) | -6 | -2 | -5 |  |  |  |  |  |  |  | -13 |
| 221 Grand(US00025) | -8 |  | -5 |  |  |  |  |  |  |  | -13 |
| 102 Fulton(US00006) | -3 | -2 | -5 |  |  |  |  | -2 |  |  | -12 |
| 15th & 3rd(US00024) | -8 | -2 | -2 |  |  |  |  |  |  |  | -12 |
| 37th & Broadway(US00004) | -11 |  |  |  |  |  |  |  |  |  | -11 |
| 33rd & 10th(US00008) | -6 |  | -5 |  |  |  |  |  |  |  | -11 |
| 54th & 8th(US00005) | -4 |  | -5 |  |  |  |  |  |  |  | -9 |
| 108th & Broadway(US00007) | -5 | -2 |  |  | -2 |  |  |  |  |  | -9 |
| 16th & 6th(US00012) | -7 | -2 |  |  |  |  |  |  |  |  | -9 |
| 40th & 10th(US00018) | -7 |  |  |  |  |  |  | -2 |  |  | -9 |
| 21st & 3rd(US00020) | -3 |  | -5 |  |  |  |  |  |  |  | -8 |
| 41st & Lexington(US00015) | -5 |  | -2 |  |  |  |  |  |  |  | -7 |
| 23rd & 8th(US00022) | -2 |  |  | -5 |  |  |  |  |  |  | -7 |
| 合计 | -108 | -18 | -53 | -5 | -2 |  | -10 | -6 |  |  | -202 |

100% 门店命中的模块：清洁卫生

## [§4.2] 最低分门店归因

- 门店：**52nd & Madison(US00027)**　主巡检得分 **64**（QA审计，2026-06-17，Eamonn Caballar）
- 模块扣分构成：清洁卫生 -7，设施 -5，员工健康卫生 -2，过程控制 -2
- S 项：Sinks and Pipes “Air gap non compliant.”
- 新店？否（5月主巡检基准 84，环比 -20）

## [§4.3] 申诉明细（全量）

| 门店(code) | 巡检类型 | 申诉结果 | 日期 | 分数变动(orig→adj) | 巡检员 |
| --- | --- | --- | --- | --- | --- |
| 102 Fulton(US00006) | QA审计 | 获批※ | 2026-06-15 | 68→93 | Eamonn Caballar |
| 33rd & 10th(US00008) | QA审计 | 获批※ | 2026-06-17 | 69→94 | Eamonn Caballar |
| 154 Bleecker(US00010) | QA审计 | 获批※ | 2026-06-15 | 67→92 | Eamonn Caballar |
| 41st & Lexington(US00015) | QA审计 | 获批※ | 2026-06-17 | 93→95 | Eamonn Caballar |
| 29th & 3rd(US00019) | QA审计 | 获批※ | 2026-06-16 | 65→94 | Eamonn Caballar |
| 21st & 3rd(US00020) | QA审计 | 获批※ | 2026-06-16 | 72→97 | Eamonn Caballar |
| 221 Grand(US00025) | QA审计 | 获批※ | 2026-06-15 | 67→94 | Eamonn Caballar |
| 8th & Broadway(US00001) | QA审计 | 审批中 | 2026-06-18 | 87→87 | Eamonn Caballar |
| 54th & 8th(US00005) | QA审计 | 审批中 | 2026-06-17 | 71→71 | Eamonn Caballar |
| 15th & 3rd(US00024) | QA审计 | 审批中 | 2026-06-16 | 88→88 | Eamonn Caballar |

合计 **10 起（7 获批 / 0 驳回 / 3 审批中）**

## [§4.4] 同店跨类型背离（≥20分）

| 门店(code) | 较低类型(分) | 较高类型(分) | 差值 | 一句解读 |
| --- | --- | --- | --- | --- |
| 154 Bleecker(US00010) | 区经(58) | QA(92) | 34 | 区经(58)较QA(92)严格，正式巡检间尺度差异 |
| 54th & 8th(US00005) | 区经(62) | 自检(92.0) | 30.0 | 自检(92.0)显著宽松，区经(62)暴露更多问题 |
| 16th & 6th(US00012) | 区经(70) | QA(91) | 21 | 区经(70)较QA(91)严格，正式巡检间尺度差异 |
| 108th & Broadway(US00007) | 自检(71.0) | QA(91) | 20.0 | 自检(71.0)偏严于QA(91)，一线自查更保守 |

## [§4.5] 模块覆盖表（主巡检）

| 模块 | 影响门店(n/N) | 覆盖率 | 扣分 | 风险 |
| --- | --- | --- | --- | --- |
| 清洁卫生 | 18/18 | 100.0% | -108 | 🔴 |
| 设施 | 11/18 | 61.1% | -53 | 🔴 |
| 过程控制 | 8/18 | 44.4% | -18 | 🟡 |
| 温控有效期 | 2/18 | 11.1% | -10 | 🟢 |
| 员工健康卫生 | 3/18 | 16.7% | -6 | 🟢 |
| 证照 | 1/18 | 5.6% | -5 | 🟢 |
| 职业安全 | 1/18 | 5.6% | -2 | 🟢 |

## [§5.1] 关键词归因（全部发现）

| 归因类别 | 数量 | 占比 | 典型问题 |
| --- | --- | --- | --- |
| 门店 | 258 | 51.8% | 日常清洁、消毒、标签、储存卫生 |
| 机修+营建 | 87 | 17.5% | sinks and pipes / air gap / 油脂阱 / 灯具 / 门 |
| 供应链+行政 | 18 | 3.6% | license / certificate / 文件记录 / no smoking sign |
| 未知 | 135 | 27.1% | 描述缺失或少于 10 字符 |

空/短描述（<10字符）占比：135/498 = 27.1%

## [§7.1] 三类巡检总览

| 巡检类型 | 次数 | 覆盖门店(n/N) | 巡检员数 | 平均分 | S项 | M项 | 节奏 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 门店自检 | 51 | 18/18 | 27 | 82.8 | 10 | 32 | 全月高频（日常暴露） |
| QA审计 | 16 | 16/18 | 1 | 88.2 | 8 | 5 | 月中集中（6/10–18 专业定级） |
| 区经检查 | 18 | 18/18 | 1 | 84.3 | 5 | 7 | 全月+月末复核 |

## [§7.2] 同店三类对比

| 门店(code) | 自检均分 | QA审计 | 区经检查 | QA-自检差 |
| --- | --- | --- | --- | --- |
| 8th & Broadway(US00001) | 80.7 | 87 | 94 | 6.3 |
| 28th & 6th(US00002) | 87.0 | 86 | 92 | -1.0 |
| 100 Maiden Ln(US00003) | 88.5 | 86 | 88 | -2.5 |
| 37th & Broadway(US00004) | 91.8 | 89 | 96 | -2.8 |
| 54th & 8th(US00005) | 92.0 | 71 | 62 | -21.0 |
| 102 Fulton(US00006) | 87.5 | 93 | 86 | 5.5 |
| 108th & Broadway(US00007) | 71.0 | 91 | 87 | 20.0 |
| 33rd & 10th(US00008) | 78.2 | 94 | 91 | 15.8 |
| 154 Bleecker(US00010) | 78.5 | 92 | 58 | 13.5 |
| 16th & 6th(US00012) | 88.7 | 91 | 70 | 2.3 |
| 41st & Lexington(US00015) | 83.7 | 95 | 89 | 11.3 |
| 40th & 10th(US00018) | 82.2 |  | 91 |  |
| 29th & 3rd(US00019) | 79.7 | 94 | 94 | 14.3 |
| 21st & 3rd(US00020) | 80.0 | 97 | 90 | 17.0 |
| 23rd & 8th(US00022) | 90.5 |  | 93 |  |
| 15th & 3rd(US00024) | 72.3 | 88 | 88 | 15.7 |
| 221 Grand(US00025) | 80.7 | 94 | 87 | 13.3 |
| 52nd & Madison(US00027) | 75.5 | 64 | 61 | -11.5 |

## [§7.3] 自检一致性（同员同店≥2次）

| 巡检员 | 门店(code) | 次数 | 历次得分 | 摆动(max-min) |
| --- | --- | --- | --- | --- |
| Jian Ming Juo | 40th & 10th(US00018) | 4 | 86→60→87→96 | 36 |
| Wenny Lin | 52nd & Madison(US00027) | 4 | 82→77→87→56 | 31 |
| Huichen Jiang | 8th & Broadway(US00001) | 3 | 66→96→80 | 30 |
| Yaqing Zuo | 33rd & 10th(US00008) | 3 | 61→91→75 | 30 |
| Darwin Coronel | 29th & 3rd(US00019) | 2 | 63→86 | 23 |
| Kayen Wu He | 221 Grand(US00025) | 2 | 85→66 | 19 |
| Joselyn Pacheco Trejo | 16th & 6th(US00012) | 2 | 80→98 | 18 |
| Tunisia Hayward | 37th & Broadway(US00004) | 2 | 83→98 | 15 |
| Shangxian Piao | 102 Fulton(US00006) | 4 | 88→81→86→95 | 14 |
| Clara Mae Venturina | 15th & 3rd(US00024) | 2 | 80→68 | 12 |
| Afsana Gu | 41st & Lexington(US00015) | 2 | 88→78 | 10 |
| Dominique Meadows | 100 Maiden Ln(US00003) | 2 | 84→93 | 9 |
| Austin Gebhardt | 37th & Broadway(US00004) | 2 | 91→95 | 4 |
| Eric Park | 54th & 8th(US00005) | 2 | 90→94 | 4 |
| Andrew Chen | 23rd & 8th(US00022) | 2 | 92→89 | 3 |

最大摆动：Jian Ming Juo @ 40th & 10th(US00018) 摆动 36

## [§7.4] 巡检员尺度（≥2次）

| 巡检员 | 角色 | 巡检类型 | 次数 | 均分 | 尺度 |
| --- | --- | --- | --- | --- | --- |
| Clara Mae Venturina | Store Manager | 门店自检 | 2 | 74.0 | 正常 |
| Darwin Coronel | Store Manager | 门店自检 | 2 | 74.5 | 正常 |
| Kayen Wu He | Store Manager | 门店自检 | 2 | 75.5 | 正常 |
| Wenny Lin | Store Manager | 门店自检 | 4 | 75.5 | 正常 |
| Yaqing Zuo | Store Manager | 门店自检 | 3 | 75.7 | 正常 |
| Huichen Jiang | Store Manager | 门店自检 | 3 | 80.7 | 正常 |
| Jian Ming Juo | Store Manager | 门店自检 | 4 | 82.2 | 正常 |
| Afsana Gu | Store Manager | 门店自检 | 2 | 83.0 | 正常 |
| Jung Han Liang | Area Operations Manager | 区经检查 | 18 | 84.3 | 正常 |
| Shangxian Piao | Store Manager | 门店自检 | 4 | 87.5 | 正常 |
| Betty Xu | Assistant Store Manager | 门店自检 | 2 | 87.5 | 正常 |
| Eamonn Caballar | Senior QA Manager | QA审计 | 16 | 88.2 | 正常 |
| Dominique Meadows | Store Manager | 门店自检 | 2 | 88.5 | 正常 |
| Joselyn Pacheco Trejo | Store Manager | 门店自检 | 2 | 89.0 | 正常 |
| Tunisia Hayward | Store Manager | 门店自检 | 2 | 90.5 | 正常 |
| Andrew Chen | Store Manager | 门店自检 | 2 | 90.5 | 正常 |
| Eric Park | Store Manager | 门店自检 | 2 | 92.0 | 正常 |
| Austin Gebhardt | Assistant Store Manager | 门店自检 | 2 | 93.0 | 偏宽(>92) |

## [§7.5] 覆盖趋势（1–6月）

| 月份 | 自检 | QA | 区经 | 合计 | 自检均分 | QA均分 | 区经均分 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-01 | 7 | 5 | 4 | 16 |  |  |  |
| 2026-02 | 5 | 2 | 0 | 7 |  |  |  |
| 2026-03 | 13 | 1 | 0 | 14 |  |  |  |
| 2026-04 | 32 | 12 | 14 | 58 | 80.2 | 84.6 | 80.1 |
| 2026-05 | 49 | 16 | 21 | 86 | 81.3 | 85.1 | 82.2 |
| 2026-06 | 51 | 16 | 18 | 85 | 82.8 | 88.2 | 84.3 |

## [§7.6] 三类发现差异

| 巡检类型 | S项 | M项 | 价值说明 |
| --- | --- | --- | --- |
| 门店自检 | 10 | 32 | 高频暴露（日常一线自查） |
| QA审计 | 8 | 5 | 专业定级 / 结构性 S 项（air gap 等） |
| 区经检查 | 5 | 7 | 全覆盖复核 |