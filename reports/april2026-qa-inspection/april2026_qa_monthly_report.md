# 瑞幸咖啡北美
# QA门店巡检月度分析报告
# Monthly QA Store Audit Analysis Report
# **2026年04月**

**质量保障部 / 基础设施部**
编制：曾翔宇    日期：2026-05-01

---

## 文档信息

| 项目 | 内容 |
|---|---|
| 报告编号 | LCNA-QA-2026-004 |
| 报告周期 | 2026年04月 |
| 数据范围 | 2026-04-01 至 2026-04-30 |
| 有效门店 | 13 家（已巡检活跃门店）|
| 巡检类型 | 门店自检(33次) + QA审计(12次) + 区经检查(14次) = 共59次 |
| 问题总数 | 371 个有效扣分项（S项17、M项38、G项241、L项75）|
| 编制人 | 曾翔宇 |
| 部门 | 质量保障部 / 基础设施部 |
| 数据来源 | empapp 门店稽核系统（aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol）|
| 状态 | V1稿 |

## ⚠ 数据说明

1. **本月巡检体系全面恢复**：4月共完成59次有效巡检（status=1已提交），涵盖12家活跃门店与1家新开业门店的全部三类巡检（门店自检/QA审计/区经检查），与3月报告「巡检体系崩溃」形成鲜明对比。区经检查在中断3个月后于4月**完全恢复**（14次）。
2. **数据过滤口径**：本报告主体使用 `t_shopcheck_data.status=1`（已提交/已生成）的巡检数据，与1月、3月报告保持一致；如包含未提交草稿（status=0），4月总数为63次，详见数据集附录。
3. **本报告标准分析部分（一至六章）使用各门店最新巡检数据**，优先级 QA审计 > 区经检查 > 门店自检；同优先级取最近日期。第七章为巡检类型对比分析。
4. **新开门店纳入巡检**：US00012（16th & 6th，3月23日开业）、US00019（29th & 3rd，4月11日开业）首次进入月度巡检覆盖。
5. **QA审计人员变更**：Yu Jiang 4月未执行任何巡检（1月5次、2月2次、3月2次后退出）；Eamonn Caballar 4月执行12次，已全面接管 QA审计 角色。
6. **区经检查人员**：Daniel Chu 完成7次，Jung Han Liang 完成7次，区经巡检节奏已恢复正常。
7. **测试门店**：US00000（NJ Test Kitchen）4月有1次草稿巡检（status=0，未提交），未计入活跃门店覆盖。

---

## 管理摘要

本月共完成 **59 次有效巡检**，覆盖 **13 家活跃门店**，发现 **371 个有效扣分项**。基于各门店最新巡检（QA审计优先），本月平均分 **80.0 分**。

✅ **巡检体系全面恢复**：连续3个月退化的区经检查在4月完全恢复（14次），QA审计从3月的1次激增至12次，门店自检33次，**12家活跃门店均获得三类巡检全覆盖**——这是2026年首次实现。

⚠ **食品安全风险仍存**：发现 17 个S项（关键项）和 38 个M项（重要项），分布在多家门店。最低分门店 **US00005 54th & 8th**（69分）。

⚠ **核心发现**：4月有 5 起同店同日多次巡检案例，其中 US00020（21st & 3rd）于4月21日由 Darwin Coronel 单人提交三次自检，得分100/100/64，**摆动幅度36分**——再次印证门店自检评分一致性问题。

✅ **跨类型一致性显著改善**：与3月 52nd & Madison 自检-QA 差距21分形成对比，4月同店跨类型对比的差距大幅收窄（多数<10分），QA审计与区经检查互为校准基准的体系开始发挥作用。

---

## 一、门店整体表现

### 1.1 本月概览

本月巡检覆盖 **13 家活跃门店**，共执行 **59 次巡检**（门店自检33次、QA审计12次、区经检查14次）。以下得分使用各门店最新巡检结果（优先 QA审计 > 区经检查 > 门店自检）。整体平均得分 **80.0 分**。

| 最高分门店 | 最低分门店 | S项门店数 | <80分门店数 |
|---|---|---|---|
| 221 Grand<br>87分 | 54th & 8th<br>69分 | 9 家 | 6 家 |

### 1.2 各门店得分明细（基于最新巡检）

| # | 门店 | 编号 | 得分 | 巡检类型 | 扣分 | S | M | G | L | 巡检员 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 33rd & 10th | US00008 | 87 | QA审计 | -13 | 0 | 0 | 6 | 1 | Eamonn Caballar |
| 2 | 221 Grand | US00025 | 87 | QA审计 | -13 | 0 | 0 | 6 | 1 | Eamonn Caballar |
| 3 | 102 Fulton | US00006 | 86 | QA审计 | -14 | 0 | 1 | 4 | 1 | Eamonn Caballar |
| 4 | 28th & 6th | US00002 | 84 | QA审计 | -16 | 0 | 1 | 5 | 1 | Eamonn Caballar |
| 5 | 100 Maiden Ln | US00003 | 84 | QA审计 | -16 | 0 | 1 | 4 | 3 | Eamonn Caballar |
| 6 | 37th & Broadway | US00004 | 83 | QA审计 | -17 | 0 | 0 | 8 | 1 | Eamonn Caballar |
| 7 | 21st & 3rd | US00020 | 82 | QA审计 | -18 | 0 | 2 | 4 | 0 | Eamonn Caballar |
| 8 | 8th & Broadway | US00001 | 79 | QA审计 | -21 | 0 | 2 | 5 | 1 | Eamonn Caballar |
| 9 | 52nd & Madison | US00027 | 78 | QA审计 | -22 | 0 | 2 | 6 | 0 | Eamonn Caballar |
| 10 | 16th & 6th | US00012 | 75 | QA审计 | -25 | 0 | 2 | 8 | 1 | Eamonn Caballar |
| 11 | 29th & 3rd | US00019 | 75 | 区经检查 | -5 | 1 | 0 | 0 | 0 | Daniel Chu |
| 12 | 15th & 3rd | US00024 | 71 | QA审计 | -9 | 1 | 0 | 1 | 2 | Eamonn Caballar |
| 13 | 54th & 8th | US00005 | 69 | QA审计 | -11 | 1 | 0 | 3 | 0 | Eamonn Caballar |

### 1.3 管理解读

本月得分呈现以下特征：

- **3 家门店达到85分以上**：33rd & 10th 87分、221 Grand 87分、102 Fulton 86分 等。
- **6 家门店低于80分**：54th & 8th 69分、15th & 3rd 71分、16th & 6th 75分、29th & 3rd 75分、52nd & Madison 78分。
- **17 个S项分布在 9 家门店**，涉及证照文件、化学品管理、交叉污染防控、饮用水管道等关键模块；其中部分门店出现重复S项，需重点跟进。
- **跨类型对比有所改善**：US00008 33rd & 10th QA审计87分 vs 区经检查47分，差距 **40 分**。与3月最大差距21分相比，4月跨类型校准效果显著。
- **同日重复巡检暴露评分一致性问题**：US00020 在 2026-04-21 同日由 Darwin Coronel 提交3次巡检，得分摆动 **36 分**（详见 §7.3）。

## 二、12模块风险分析

本月共发现 **371 个有效扣分项**，分布在 12 个模块中。

### 2.1 风险分层

- 🔴 **系统性风险（影响≥50%门店）**：饮用水与管道系统、清洁卫生、工作场所安全、交叉污染防控（各影响门店占比≥50%）
- 🟡 **中等覆盖面（影响30-49%）**：产品与有效期管理、虫害防控、员工健康与个人卫生、证照文件记录、设备设施维护
- 🟢 **低覆盖面（<30%）**：化学品管理、供应商管理、场地安全

### 2.2 模块排名总览（按扣分排序）

| # | 模块 | 问题数 | 扣分 | 门店 | 覆盖率 | S | M | G | L | 风险 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 清洁卫生 | 181 | -322 | 13/13 | 100% | 0 | 19 | 87 | 75 | ⚠ 系统性 |
| 2 | 交叉污染防控 | 63 | -132 | 13/13 | 100% | 2 | 0 | 61 | 0 | ⚠ 含S项 / ⚠ 系统性 |
| 3 | 饮用水与管道系统 | 46 | -131 | 10/13 | 77% | 9 | 4 | 33 | 0 | ⚠ 含S项 / ⚠ 系统性 |
| 4 | 员工健康与个人卫生 | 16 | -53 | 6/13 | 46% | 5 | 2 | 9 | 0 | ⚠ 含S项 |
| 5 | 产品与有效期管理 | 13 | -44 | 6/13 | 46% | 0 | 6 | 7 | 0 | 含M项 |
| 6 | 工作场所安全 | 17 | -34 | 9/13 | 69% | 0 | 0 | 17 | 0 | ⚠ 系统性 |
| 7 | 证照文件记录 | 6 | -30 | 4/13 | 31% | 0 | 6 | 0 | 0 | 含M项 |
| 8 | 设备设施维护 | 13 | -26 | 6/13 | 46% | 0 | 0 | 13 | 0 | --- |
| 9 | 虫害防控 | 10 | -23 | 5/13 | 38% | 1 | 0 | 9 | 0 | ⚠ 含S项 |
| 10 | 化学品管理 | 3 | -6 | 3/13 | 23% | 0 | 0 | 3 | 0 | --- |
| 11 | 场地安全 | 1 | -5 | 1/13 | 8% | 0 | 1 | 0 | 0 | 含M项 |
| 12 | 供应商管理 | 2 | -4 | 2/13 | 15% | 0 | 0 | 2 | 0 | --- |

### 2.3 重点模块详细分析（TOP 5）

#### 1. 清洁卫生 — 181个扣分项，-322分，影响13家门店

严重级别：S项0个、M项19个、G项87个、L项75个。

具体问题（引用原始描述，最多展示前30条；按严重度排序）：

- **8th & Broadway** (US00001)｜Clean & Sanitize｜M项 -5分｜Less than 50 ppm
- **8th & Broadway** (US00001)｜Clean & Sanitize｜M项 -5分｜Gloves found not in designated hanging rack.
- **8th & Broadway** (US00001)｜Clean & Sanitize｜M项 -5分｜Limescale in ice bin and water remaining on in the bin.
- **28th & 6th** (US00002)｜Clean & Sanitize｜M项 -5分｜Gloves inappropriately stored below three compartment sink.
- **37th & Broadway** (US00004)｜Clean & Sanitize｜M项 -5分｜Sanitizer not at 200ppm in three compartment sink. / Sanitizer in buckets not 100ppm.
- **54th & 8th** (US00005)｜Clean & Sanitize｜M项 -5分｜Not at 100 ppm
- **33rd & 10th** (US00008)｜Clean & Sanitize｜M项 -5分｜(无描述)
- **33rd & 10th** (US00008)｜Clean & Sanitize｜M项 -5分｜(无描述)
- **33rd & 10th** (US00008)｜Clean & Sanitize｜M项 -5分｜(无描述)
- **33rd & 10th** (US00008)｜Clean & Sanitize｜M项 -5分｜Ice machine debris, foreign material and fiber of towel left
- **16th & 6th** (US00012)｜Clean & Sanitize｜M项 -5分｜Gloves improperly stored.
- **16th & 6th** (US00012)｜Clean & Sanitize｜M项 -5分｜Sanitizer showing different PPM every bucket tested (Plus Main)
- **21st & 3rd** (US00020)｜Clean & Sanitize｜M项 -5分｜Towels on rack
- **21st & 3rd** (US00020)｜Clean & Sanitize｜M项 -5分｜Sink does not fit the largest item completely(toddy bucket)
- **21st & 3rd** (US00020)｜Clean & Sanitize｜M项 -5分｜Gloves not properly stored.  /  / Dirty / Used Towels seen on dry rack.
- **15th & 3rd** (US00024)｜Clean & Sanitize｜M项 -5分｜Dirty sanitation water
- **52nd & Madison** (US00027)｜Clean & Sanitize｜M项 -5分｜(无描述)
- **52nd & Madison** (US00027)｜Clean & Sanitize｜M项 -5分｜Sanitizer at coffee station not up to standard
- **52nd & Madison** (US00027)｜Clean & Sanitize｜M项 -5分｜Wiping Cloths not stored in buckets with sanitizer solution.
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜Fridges unclean, with some residues
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜(无描述)
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜Ice trolly has water / Blender has matcha
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜(无描述)
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜Dust found on ice machine.  /  / Water clumps found  in smoothie powder.
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜Cheese covered oil paper left food tray. Tong bin not wiped out
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜Espresso has coffee buildup
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜Residual and foam leftover when cold brew premix ran out, this is less food safety concern but more brand imagine from the perspective of customers.  / This should be cleaned when available.
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜Matcha stain on blender.
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜Fridges unclean
- **8th & Broadway** (US00001)｜Equipment and utensils｜G项 -2分｜Matcha on the mat and milk pitcher
- … 另有 151 条未在此展示，详见 `april2026_inspection_items.csv`。

#### 2. 交叉污染防控 — 63个扣分项，-132分，影响13家门店

严重级别：S项2个、M项0个、G项61个、L项0个。

具体问题（引用原始描述，最多展示前30条；按严重度排序）：

- ⚠ **54th & 8th** (US00005)｜Cross-Contamination｜S项 -5分｜Matcha stains on chocolate bottle. Milk splatters and stain on milk containers.
- ⚠ **29th & 3rd** (US00019)｜Cross-Contamination｜S项 -5分｜Milk spillage in milk dispenser fridge
- **8th & Broadway** (US00001)｜Material Storage Location Specification｜G项 -2分｜Not in lick box
- **8th & Broadway** (US00001)｜Material Storage Location Specification｜G项 -2分｜Rack is not 6” off ground
- **8th & Broadway** (US00001)｜Cross-Contamination｜G项 -2分｜Storing sealed and open packages together
- **8th & Broadway** (US00001)｜Storage/Maintenance of Utensils｜G项 -2分｜Keep supplies clean and free of cobtamjnation
- **8th & Broadway** (US00001)｜Cross-Contamination｜G项 -2分｜Clumping seen in smoothie powder.
- **8th & Broadway** (US00001)｜Cross-Contamination｜G项 -2分｜Open matcha pitcher.
- **28th & 6th** (US00002)｜Material Storage Location Specification｜G项 -2分｜Contaminated water in clean spoon holder
- **28th & 6th** (US00002)｜Cross-Contamination｜G项 -2分｜Pitcher placed in top of machine
- **28th & 6th** (US00002)｜Standard procedures｜G项 -2分｜Delivery station not kept clean
- **100 Maiden Ln** (US00003)｜Cross-Contamination｜G项 -2分｜1. Open matcha container found.
- **100 Maiden Ln** (US00003)｜Material Storage Location Specification｜G项 -2分｜Standing water found in “Clean” spoons container.
- **100 Maiden Ln** (US00003)｜Material Storage Location Specification｜G项 -2分｜After washing clean spoons we put them back still dripping filling the milk pitcher with water.
- **100 Maiden Ln** (US00003)｜Storage/Maintenance of Utensils｜G项 -2分｜Found in “clean” pitcher
- **100 Maiden Ln** (US00003)｜Standard procedures｜G项 -2分｜Glove just sitting here. Unsure if clean or dirty
- **37th & Broadway** (US00004)｜Storage/Maintenance of Utensils｜G项 -2分｜Standing water in clean utensils.  / Dirty utensils left unclean for over 10 mins.
- **37th & Broadway** (US00004)｜Standard procedures｜G项 -2分｜Incorrect labeling.
- **37th & Broadway** (US00004)｜Cross-Contamination｜G项 -2分｜2L pitcher left open when not in use.
- **37th & Broadway** (US00004)｜Cross-Contamination｜G项 -2分｜Ice machine top screw loose
- **37th & Broadway** (US00004)｜Storage/Maintenance of Utensils｜G项 -2分｜Potential risk of cross contamination after making SEC
- **37th & Broadway** (US00004)｜Material Storage Location Specification｜G项 -2分｜Lock box unlocked and open.
- **54th & 8th** (US00005)｜Standard procedures｜G项 -2分｜PQNC filed product left in the fridge
- **102 Fulton** (US00006)｜Cross-Contamination｜G项 -2分｜Moist vanilla powder. It was disposed of and waste was reported.
- **102 Fulton** (US00006)｜Cross-Contamination｜G项 -2分｜(无描述)
- **102 Fulton** (US00006)｜Storage/Maintenance of Utensils｜G项 -2分｜We should probably order more
- **102 Fulton** (US00006)｜Standard procedures｜G项 -2分｜We should clean it if we see it
- **33rd & 10th** (US00008)｜Storage/Maintenance of Utensils｜G项 -2分｜(无描述)
- **33rd & 10th** (US00008)｜Material Storage Location Specification｜G项 -2分｜(无描述)
- **33rd & 10th** (US00008)｜Cross-Contamination｜G项 -2分｜Clumping found in Smoothie powder.
- … 另有 33 条未在此展示，详见 `april2026_inspection_items.csv`。

#### 3. 饮用水与管道系统 — 46个扣分项，-131分，影响10家门店

严重级别：S项9个、M项4个、G项33个、L项0个。

具体问题（引用原始描述，最多展示前30条；按严重度排序）：

- ⚠ **8th & Broadway** (US00001)｜Sinks and Pipes｜S项 -5分｜3 components sinks leaking
- ⚠ **8th & Broadway** (US00001)｜Sinks and Pipes｜S项 -5分｜3 compartment sink is leaking
- ⚠ **54th & 8th** (US00005)｜Sinks and Pipes｜S项 -5分｜Filed before with Bd list, no air gap
- ⚠ **54th & 8th** (US00005)｜Sinks and Pipes｜S项 -5分｜Store presents air gap issue.
- ⚠ **102 Fulton** (US00006)｜Sinks and Pipes｜S项 -5分｜BD is aware
- ⚠ **33rd & 10th** (US00008)｜Sinks and Pipes｜S项 -5分｜The lowest pipe doesn’t have 1 inch to the drainer for air gap.
- ⚠ **15th & 3rd** (US00024)｜Sinks and Pipes｜S项 -5分｜Plumbing not properly secured and touching drain.  /  / Pipes touching filters.
- ⚠ **52nd & Madison** (US00027)｜Sinks and Pipes｜S项 -5分｜No air gap
- ⚠ **52nd & Madison** (US00027)｜Sinks and Pipes｜S项 -5分｜Air gap not wide enough
- **8th & Broadway** (US00001)｜Good condition｜M项 -5分｜Lights in 2 pest boxes not working
- **8th & Broadway** (US00001)｜Good condition｜M项 -5分｜4 pest lights out
- **102 Fulton** (US00006)｜Good condition｜M项 -5分｜One light is not working
- **52nd & Madison** (US00027)｜Good condition｜M项 -5分｜(无描述)
- **8th & Broadway** (US00001)｜Good condition｜G项 -2分｜Gaps on the light food fridge and near the hand wash shink
- **8th & Broadway** (US00001)｜Good condition｜G项 -2分｜No seal here bakery chiller and counter
- **8th & Broadway** (US00001)｜Grease traps｜G项 -2分｜Grease trap not cleaned and giving odor.
- **8th & Broadway** (US00001)｜Good condition｜G项 -2分｜Gap found at POS.
- **8th & Broadway** (US00001)｜Good condition｜G项 -2分｜Needs seeling
- **28th & 6th** (US00002)｜Good condition｜G项 -2分｜Constant leaking , no faucet.
- **28th & 6th** (US00002)｜Good condition｜G项 -2分｜All counters should be sealed
- **28th & 6th** (US00002)｜Good condition｜G项 -2分｜Not fully functional
- **28th & 6th** (US00002)｜Good condition｜G项 -2分｜Please remove the delivery campaign and file BD of the tent film
- **28th & 6th** (US00002)｜Sinks and Pipes｜G项 -2分｜Clog found in “Washing” portion of 3 compartment sink.
- **37th & Broadway** (US00004)｜Good condition｜G项 -2分｜Faucet loose and wiggles around.
- **37th & Broadway** (US00004)｜Grease traps｜G项 -2分｜pungent odor coming from closed grease trap although it has been cleaned the past two nights.
- **37th & Broadway** (US00004)｜Good condition｜G项 -2分｜Improper “door knob” used for bathroom Access.
- **102 Fulton** (US00006)｜Good condition｜G项 -2分｜Door not operating properly.
- **102 Fulton** (US00006)｜Sinks and Pipes｜G项 -2分｜Drain keeps overflowing
- **33rd & 10th** (US00008)｜Sinks and Pipes｜G项 -2分｜(无描述)
- **33rd & 10th** (US00008)｜Grease traps｜G项 -2分｜(无描述)
- … 另有 16 条未在此展示，详见 `april2026_inspection_items.csv`。

#### 4. 员工健康与个人卫生 — 16个扣分项，-53分，影响6家门店

严重级别：S项5个、M项2个、G项9个、L项0个。

具体问题（引用原始描述，最多展示前30条；按严重度排序）：

- ⚠ **33rd & 10th** (US00008)｜Handwashing Standards｜S项 -5分｜No materials to dry hands after handwashing, spotted this in restroom and BOH hand sink
- ⚠ **29th & 3rd** (US00019)｜Handwashing Standards｜S项 -5分｜Paper towel dispenser not mounted
- ⚠ **29th & 3rd** (US00019)｜Handwashing Standards｜S项 -5分｜BOH handwash sink does not have a paper towel dispenser
- ⚠ **29th & 3rd** (US00019)｜Handwashing Standards｜S项 -5分｜No handwashing sink
- ⚠ **21st & 3rd** (US00020)｜Handwashing Standards｜S项 -5分｜No hand soap in BOH hand wash sink
- **28th & 6th** (US00002)｜Handwashing Standards｜M项 -5分｜Did not wash hands for 20 seconds, continuously touching face
- **15th & 3rd** (US00024)｜Personal Hygiene｜M项 -5分｜No name tags (2 employees)
- **28th & 6th** (US00002)｜Personal Hygiene｜G项 -2分｜Beard net not in use
- **37th & Broadway** (US00004)｜Personal Hygiene｜G项 -2分｜Please keep employee area always clean and neat
- **37th & Broadway** (US00004)｜Personal Hygiene｜G项 -2分｜Employee drinks found in garbage area.
- **33rd & 10th** (US00008)｜Personal Hygiene｜G项 -2分｜Employee table with food leftover and not cleaned
- **29th & 3rd** (US00019)｜Personal Hygiene｜G项 -2分｜Aprons would need disposable aprons for cleaning tasks.
- **21st & 3rd** (US00020)｜Personal Hygiene｜G项 -2分｜No
- **15th & 3rd** (US00024)｜Personal Hygiene｜G项 -2分｜Matcha stains and no name tag
- **15th & 3rd** (US00024)｜Personal Hygiene｜G项 -2分｜No name tag and dirty apron
- **15th & 3rd** (US00024)｜Personal Hygiene｜G项 -2分｜(无描述)

#### 5. 产品与有效期管理 — 13个扣分项，-44分，影响6家门店

严重级别：S项0个、M项6个、G项7个、L项0个。

具体问题（引用原始描述，最多展示前30条；按严重度排序）：

- **8th & Broadway** (US00001)｜Expiration Date｜M项 -5分｜Missing expiration date on syrup bottle.
- **8th & Broadway** (US00001)｜Expiration Date｜M项 -5分｜Needs to be chilled
- **33rd & 10th** (US00008)｜Expiration Date｜M项 -5分｜No expiration label
- **29th & 3rd** (US00019)｜Expiration Date｜M项 -5分｜Missing expiration
- **21st & 3rd** (US00020)｜Expiration Date｜M项 -5分｜Missing Expiration Date Tag on syrup bottle.
- **52nd & Madison** (US00027)｜Expiration Date｜M项 -5分｜Missing expiration date on syrup bottle.
- **8th & Broadway** (US00001)｜Devices for Monitoring the Temperatures of All Refrigerators and Freezers｜G项 -2分｜Thermometer in back
- **8th & Broadway** (US00001)｜Storage and Inventory Transfer of Food｜G项 -2分｜Should be in fridge
- **33rd & 10th** (US00008)｜Devices for Monitoring the Temperatures of All Refrigerators and Freezers｜G项 -2分｜(无描述)
- **33rd & 10th** (US00008)｜Devices for Monitoring the Temperatures of All Refrigerators and Freezers｜G项 -2分｜(无描述)
- **33rd & 10th** (US00008)｜Devices for Monitoring the Temperatures of All Refrigerators and Freezers｜G项 -2分｜(无描述)
- **33rd & 10th** (US00008)｜Devices for Monitoring the Temperatures of All Refrigerators and Freezers｜G项 -2分｜(无描述)
- **15th & 3rd** (US00024)｜Devices for Monitoring the Temperatures of All Refrigerators and Freezers｜G项 -2分｜Oat and skim milk out of temp. Refrigerator above 40F

#### 6+. 其他模块概要

- **工作场所安全**（-34分，影响9家）：S0/M0/G17/L0。
- **证照文件记录**（-30分，影响4家）：S0/M6/G0/L0。
- **设备设施维护**（-26分，影响6家）：S0/M0/G13/L0。
- **虫害防控**（-23分，影响5家）：S1/M0/G9/L0。
- **化学品管理**（-6分，影响3家）：S0/M0/G3/L0。
- **场地安全**（-5分，影响1家）：S0/M1/G0/L0。
- **供应商管理**（-4分，影响2家）：S0/M0/G2/L0。

## 三、风险等级分布

### 3.1 整体分布

| 风险等级 | 数量 | 占比 | SLA要求 | 主要分布模块 |
|---|---|---|---|---|
| S项（关键项） | 17 | 4.6% | 2天内闭环 | 饮用水与管道系统(9)、员工健康与个人卫生(5)、交叉污染防控(2)、虫害防控(1) |
| M项（重要项） | 38 | 10.2% | 7天内闭环 | 清洁卫生(19)、产品与有效期管理(6)、证照文件记录(6)、饮用水与管道系统(4) |
| G项（一般项） | 241 | 65.0% | 14天内闭环 | 清洁卫生(87)、交叉污染防控(61)、饮用水与管道系统(33)、工作场所安全(17) |
| L项（轻微项） | 75 | 20.2% | 14天内闭环 | 清洁卫生(75) |
| **合计** | **371** | 100% | --- | --- |

### 3.2 S项（关键项）详情 — 必须立即整改

本月共发现 **17 个S项**，分布在 **9 家门店**。

| # | 门店 | 模块 / 子类 | 问题描述（原文） | 扣分 | 巡检类型 | 巡检员 | 日期 |
|---|---|---|---|---|---|---|---|
| 1 | 8th & Broadway<br>US00001 | 饮用水与管道系统<br>Sinks and Pipes | 3 components sinks leaking | -5 | 门店自检 | Jian Ming Juo | 2026-04-04 |
| 2 | 8th & Broadway<br>US00001 | 饮用水与管道系统<br>Sinks and Pipes | 3 compartment sink is leaking | -5 | 门店自检 | Jian Ming Juo | 2026-04-06 |
| 3 | 221 Grand<br>US00025 | 虫害防控<br>No Sign of Insect Pests | More than 20 flies. Requested more paper has not recieved /  Store has been shut down for over a week. | -5 | 门店自检 | Alexander G Harry | 2026-04-13 |
| 4 | 29th & 3rd<br>US00019 | 员工健康与个人卫生<br>Handwashing Standards | Paper towel dispenser not mounted | -5 | 门店自检 | Juan Ortiz-Fontanez | 2026-04-14 |
| 5 | 29th & 3rd<br>US00019 | 交叉污染防控<br>Cross-Contamination | Milk spillage in milk dispenser fridge | -5 | 门店自检 | Juan Ortiz-Fontanez | 2026-04-14 |
| 6 | 52nd & Madison<br>US00027 | 饮用水与管道系统<br>Sinks and Pipes | No air gap | -5 | 区经检查 | Jung Han Liang | 2026-04-16 |
| 7 | 54th & 8th<br>US00005 | 交叉污染防控<br>Cross-Contamination | Matcha stains on chocolate bottle. Milk splatters and stain on milk containers. | -5 | 门店自检 | Eric Park | 2026-04-17 |
| 8 | 21st & 3rd<br>US00020 | 员工健康与个人卫生<br>Handwashing Standards | No hand soap in BOH hand wash sink | -5 | 门店自检 | Darwin Coronel | 2026-04-21 |
| 9 | 52nd & Madison<br>US00027 | 饮用水与管道系统<br>Sinks and Pipes | Air gap not wide enough | -5 | 门店自检 | Brionna Jiles | 2026-04-22 |
| 10 | 54th & 8th<br>US00005 | 饮用水与管道系统<br>Sinks and Pipes | Filed before with Bd list, no air gap | -5 | 区经检查 | Jung Han Liang | 2026-04-26 |
| 11 | 15th & 3rd<br>US00024 | 饮用水与管道系统<br>Sinks and Pipes | Plumbing not properly secured and touching drain.  /  / Pipes touching filters. | -5 | QA审计 | Eamonn Caballar | 2026-04-28 |
| 12 | 29th & 3rd<br>US00019 | 员工健康与个人卫生<br>Handwashing Standards | BOH handwash sink does not have a paper towel dispenser | -5 | 门店自检 | Darwin Coronel | 2026-04-29 |
| 13 | 54th & 8th<br>US00005 | 饮用水与管道系统<br>Sinks and Pipes | Store presents air gap issue. | -5 | QA审计 | Eamonn Caballar | 2026-04-30 |
| 14 | 102 Fulton<br>US00006 | 饮用水与管道系统<br>Sinks and Pipes | BD is aware | -5 | 区经检查 | Daniel Chu | 2026-04-30 |
| 15 | 33rd & 10th<br>US00008 | 员工健康与个人卫生<br>Handwashing Standards | No materials to dry hands after handwashing, spotted this in restroom and BOH hand sink | -5 | 区经检查 | Jung Han Liang | 2026-04-30 |
| 16 | 33rd & 10th<br>US00008 | 饮用水与管道系统<br>Sinks and Pipes | The lowest pipe doesn’t have 1 inch to the drainer for air gap. | -5 | 区经检查 | Jung Han Liang | 2026-04-30 |
| 17 | 29th & 3rd<br>US00019 | 员工健康与个人卫生<br>Handwashing Standards | No handwashing sink | -5 | 区经检查 | Daniel Chu | 2026-04-30 |

### 3.3 M项（重要项）— 7天内闭环

本月共发现 **38 个M项**。完整列表（截取前40条）：

| # | 门店 | 模块 / 子类 | 问题描述（原文） | 扣分 | 日期 |
|---|---|---|---|---|---|
| 1 | 100 Maiden Ln<br>US00003 | 证照文件记录<br>Licenses and certificates | No smoking sign missing in restroom. | -5 | 2026-04-01 |
| 2 | 102 Fulton<br>US00006 | 证照文件记录<br>Licenses and certificates | Missing No smoking sign in restroom. | -5 | 2026-04-01 |
| 3 | 102 Fulton<br>US00006 | 场地安全<br>Site Security | One garbage bin was reported missing on April 2nd. | -5 | 2026-04-03 |
| 4 | 8th & Broadway<br>US00001 | 清洁卫生<br>Clean & Sanitize | Less than 50 ppm | -5 | 2026-04-06 |
| 5 | 8th & Broadway<br>US00001 | 饮用水与管道系统<br>Good condition | Lights in 2 pest boxes not working | -5 | 2026-04-06 |
| 6 | 8th & Broadway<br>US00001 | 清洁卫生<br>Clean & Sanitize | Gloves found not in designated hanging rack. | -5 | 2026-04-09 |
| 7 | 8th & Broadway<br>US00001 | 产品与有效期管理<br>Expiration Date | Missing expiration date on syrup bottle. | -5 | 2026-04-09 |
| 8 | 100 Maiden Ln<br>US00003 | 证照文件记录<br>Licenses and certificates | No smoking sign in the bathroom | -5 | 2026-04-09 |
| 9 | 33rd & 10th<br>US00008 | 清洁卫生<br>Clean & Sanitize | (无描述) | -5 | 2026-04-09 |
| 10 | 102 Fulton<br>US00006 | 饮用水与管道系统<br>Good condition | One light is not working | -5 | 2026-04-11 |
| 11 | 37th & Broadway<br>US00004 | 清洁卫生<br>Clean & Sanitize | Sanitizer not at 200ppm in three compartment sink. / Sanitizer in buckets not 100ppm. | -5 | 2026-04-13 |
| 12 | 8th & Broadway<br>US00001 | 饮用水与管道系统<br>Good condition | 4 pest lights out | -5 | 2026-04-14 |
| 13 | 8th & Broadway<br>US00001 | 产品与有效期管理<br>Expiration Date | Needs to be chilled | -5 | 2026-04-14 |
| 14 | 21st & 3rd<br>US00020 | 证照文件记录<br>Licenses and certificates | (无描述) | -5 | 2026-04-14 |
| 15 | 21st & 3rd<br>US00020 | 清洁卫生<br>Clean & Sanitize | Towels on rack | -5 | 2026-04-14 |
| 16 | 21st & 3rd<br>US00020 | 证照文件记录<br>Licenses and certificates | Need employees must wash hands | -5 | 2026-04-14 |
| 17 | 29th & 3rd<br>US00019 | 产品与有效期管理<br>Expiration Date | Missing expiration | -5 | 2026-04-16 |
| 18 | 15th & 3rd<br>US00024 | 清洁卫生<br>Clean & Sanitize | Dirty sanitation water | -5 | 2026-04-16 |
| 19 | 52nd & Madison<br>US00027 | 清洁卫生<br>Clean & Sanitize | (无描述) | -5 | 2026-04-16 |
| 20 | 52nd & Madison<br>US00027 | 饮用水与管道系统<br>Good condition | (无描述) | -5 | 2026-04-16 |
| 21 | 28th & 6th<br>US00002 | 员工健康与个人卫生<br>Handwashing Standards | Did not wash hands for 20 seconds, continuously touching face | -5 | 2026-04-17 |
| 22 | 54th & 8th<br>US00005 | 清洁卫生<br>Clean & Sanitize | Not at 100 ppm | -5 | 2026-04-17 |
| 23 | 8th & Broadway<br>US00001 | 清洁卫生<br>Clean & Sanitize | Limescale in ice bin and water remaining on in the bin. | -5 | 2026-04-21 |
| 24 | 33rd & 10th<br>US00008 | 清洁卫生<br>Clean & Sanitize | (无描述) | -5 | 2026-04-21 |
| 25 | 21st & 3rd<br>US00020 | 清洁卫生<br>Clean & Sanitize | Sink does not fit the largest item completely(toddy bucket) | -5 | 2026-04-21 |
| 26 | 52nd & Madison<br>US00027 | 清洁卫生<br>Clean & Sanitize | Sanitizer at coffee station not up to standard | -5 | 2026-04-22 |
| 27 | 28th & 6th<br>US00002 | 证照文件记录<br>Licenses and certificates | No allergen sign | -5 | 2026-04-23 |
| 28 | 33rd & 10th<br>US00008 | 清洁卫生<br>Clean & Sanitize | (无描述) | -5 | 2026-04-24 |
| 29 | 15th & 3rd<br>US00024 | 员工健康与个人卫生<br>Personal Hygiene | No name tags (2 employees) | -5 | 2026-04-25 |
| 30 | 28th & 6th<br>US00002 | 清洁卫生<br>Clean & Sanitize | Gloves inappropriately stored below three compartment sink. | -5 | 2026-04-27 |
| 31 | 21st & 3rd<br>US00020 | 清洁卫生<br>Clean & Sanitize | Gloves not properly stored.  /  / Dirty / Used Towels seen on dry rack. | -5 | 2026-04-28 |
| 32 | 21st & 3rd<br>US00020 | 产品与有效期管理<br>Expiration Date | Missing Expiration Date Tag on syrup bottle. | -5 | 2026-04-28 |
| 33 | 16th & 6th<br>US00012 | 清洁卫生<br>Clean & Sanitize | Gloves improperly stored. | -5 | 2026-04-29 |
| 34 | 16th & 6th<br>US00012 | 清洁卫生<br>Clean & Sanitize | Sanitizer showing different PPM every bucket tested (Plus Main) | -5 | 2026-04-29 |
| 35 | 33rd & 10th<br>US00008 | 清洁卫生<br>Clean & Sanitize | Ice machine debris, foreign material and fiber of towel left | -5 | 2026-04-30 |
| 36 | 33rd & 10th<br>US00008 | 产品与有效期管理<br>Expiration Date | No expiration label | -5 | 2026-04-30 |
| 37 | 52nd & Madison<br>US00027 | 清洁卫生<br>Clean & Sanitize | Wiping Cloths not stored in buckets with sanitizer solution. | -5 | 2026-04-30 |
| 38 | 52nd & Madison<br>US00027 | 产品与有效期管理<br>Expiration Date | Missing expiration date on syrup bottle. | -5 | 2026-04-30 |

### 3.4 G项/L项分布

**G项（一般项）共 241 个**，主要集中模块：

- 清洁卫生：87个
- 交叉污染防控：61个
- 饮用水与管道系统：33个
- 工作场所安全：17个
- 设备设施维护：13个
- 虫害防控：9个
- 员工健康与个人卫生：9个
- 产品与有效期管理：7个
- 化学品管理：3个
- 供应商管理：2个

**L项（轻微项）共 75 个**，主要集中模块：

- 清洁卫生：75个

## 四、模块与门店关联分析

### 4.1 门店×模块扣分矩阵

| 门店 | 清洁 | 交叉 | 管道 | 员工 | 产品 | 安全 | 证照 | 设备 | 虫害 | 化学 | 场地 | 供应 | 合计 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 33rd & 10th (US00008) | -58 | -10 | -23 | -7 | -13 | -2 |  | -12 | -2 |  |  |  | -127 |
| 8th & Broadway (US00001) | -46 | -12 | -30 |  | -14 | -4 |  |  | -6 |  |  |  | -112 |
| 52nd & Madison (US00027) | -39 | -12 | -17 |  | -5 | -6 |  | -4 | -6 | -2 |  |  | -91 |
| 21st & 3rd (US00020) | -23 | -12 |  | -7 | -5 | -6 | -10 |  |  | -2 |  |  | -65 |
| 28th & 6th (US00002) | -19 | -6 | -10 | -7 |  | -2 | -5 | -4 | -4 |  |  |  | -57 |
| 15th & 3rd (US00024) | -14 | -12 | -15 | -11 | -2 |  |  |  |  |  |  |  | -54 |
| 37th & Broadway (US00004) | -23 | -12 | -6 | -4 |  | -2 |  |  |  |  |  | -2 | -49 |
| 16th & 6th (US00012) | -25 | -10 | -4 |  |  | -6 |  | -2 |  |  |  |  | -47 |
| 102 Fulton (US00006) | -10 | -8 | -14 |  |  |  | -5 | -2 |  |  | -5 | -2 | -46 |
| 29th & 3rd (US00019) | -6 | -13 |  | -17 | -5 | -4 |  |  |  |  |  |  | -45 |
| 54th & 8th (US00005) | -23 | -7 | -10 |  |  |  |  | -2 |  |  |  |  | -42 |
| 100 Maiden Ln (US00003) | -16 | -10 |  |  |  |  | -10 |  |  | -2 |  |  | -38 |
| 221 Grand (US00025) | -20 | -8 | -2 |  |  | -2 |  |  | -5 |  |  |  | -37 |

### 4.2 最低分门店归因：54th & 8th（69分）

扣分 -11 分，集中在：清洁卫生（-6分）、饮用水与管道系统（-5分）。
巡检类型为 QA审计（2026-04-30），巡检员 Eamonn Caballar。

### 4.3 最高分门店分析：221 Grand（87分）

扣分 -13 分，问题较少。巡检类型 QA审计，巡检员 Eamonn Caballar。

### 4.4 模块覆盖面分析

| 模块 | 影响门店 | 覆盖率 | 扣分 | 风险标记 |
|---|---|---|---|---|
| 清洁卫生 | 13 | 100% | -322 | ⚠ 系统性 |
| 交叉污染防控 | 13 | 100% | -132 | ⚠ 含S项 / ⚠ 系统性 |
| 饮用水与管道系统 | 10 | 77% | -131 | ⚠ 含S项 / ⚠ 系统性 |
| 员工健康与个人卫生 | 6 | 46% | -53 | ⚠ 含S项 |
| 产品与有效期管理 | 6 | 46% | -44 | 含M项 |
| 工作场所安全 | 9 | 69% | -34 | ⚠ 系统性 |
| 证照文件记录 | 4 | 31% | -30 | 含M项 |
| 设备设施维护 | 6 | 46% | -26 | --- |
| 虫害防控 | 5 | 38% | -23 | ⚠ 含S项 |
| 化学品管理 | 3 | 23% | -6 | --- |
| 场地安全 | 1 | 8% | -5 | 含M项 |
| 供应商管理 | 2 | 15% | -4 | --- |

## 五、整改归因与效率

### 5.1 基于关键词的初步归因

⚠ 以下归因基于问题描述关键词自动匹配，仅供参考。实际归因需以整改工单系统数据为准。

| 归因类别 | 数量 | 占比 | 典型问题 |
|---|---|---|---|
| 门店 | 约265 | ~71% | 日常清洁、标签、卫生、消毒 |
| 机修 | 约22 | ~6% | 设备泄漏、管道、油脂阱 |
| 营建 | 约7 | ~2% | 天花板、墙面、瓷砖 |
| 未知 | 约77 | ~21% | 描述模糊或缺失 |

### 5.2 SLA整改时限标准

| 风险等级 | 整改时限 | 要求 |
|---|---|---|
| S项（关键项）| 2天 | 发现后2天内完成整改并验证 |
| M项（重要项）| 7天 | 发现后7天内完成整改并验证 |
| G项（一般项）| 14天 | 发现后14天内完成整改并验证 |
| L项（轻微项）| 14天 | 发现后14天内完成整改并验证 |

### 5.3 建议整改闭环流程

1. 巡检发现问题 → 系统自动生成整改工单
2. 根据问题类型自动分配责任方（门店/机修/营建）
3. 责任方在SLA时限内完成整改
4. QA复核验证整改效果
5. 系统记录闭环时间，计算SLA达标率

## 六、建议与下一步行动

### 6.1 本月关键发现

- ✅ **巡检体系全面恢复**：4月共完成 59 次巡检（自检33/QA12/区经14），12家活跃门店均获得三类巡检全覆盖，区经检查在中断3个月后恢复正常节奏。
- ✅ **跨类型校准开始发挥作用**：QA审计与区经检查互为基准，自检与外部审计差距大幅收窄（多数<10分）。
- ⚠ **17 个S项分布在 9 家门店**：102 Fulton（饮用水与管道系统）、15th & 3rd（饮用水与管道系统）、21st & 3rd（员工健康与个人卫生）、221 Grand（虫害防控）、29th & 3rd（交叉污染防控）、29th & 3rd（员工健康与个人卫生）、33rd & 10th（员工健康与个人卫生）、33rd & 10th（饮用水与管道系统）、52nd & Madison（饮用水与管道系统）、54th & 8t
- ⚠ **门店自检评分一致性仍有问题**：US00020 同日 Darwin Coronel 三次自检 100/100/64（摆动36分）。
- ⚠ **首要风险模块**：清洁卫生(-322分)、交叉污染防控(-132分)、饮用水与管道系统(-131分)
- ⚠ **QA审计人员单点依赖**：Eamonn Caballar 单人完成12次QA（占100%）。Yu Jiang 已退出，需评估QA团队冗余度。

### 6.2 优先行动项

| P | 紧急度 | 行动项 | 责任方 | 时限 |
|---|---|---|---|---|
| P0 | 紧急 | 立即处理 17 个S项：US00001（饮用水与管道系统）, US00005（交叉污染防控）, US00005（饮用水与管道系统）, US00006（饮用水与管道系统）, US00008（员工健康与个人卫生）（如有更多见 §3.2），确保2天内闭环 | 门店+QA | 48小时 |
| P1 | 紧急 | 处理 38 个M项，重点关注扣分集中门店：US00005 | 门店+QA | 7天 |
| P2 | 高 | 维持当前QA审计节奏（每月12+次），评估增加第二位QA Manager以避免单点依赖 | QA部门 | 本月内 |
| P3 | 高 | 对最低分门店开展专项辅导，重点改进高扣分模块 | 区域经理 | 1周内 |
| P4 | 高 | 针对自检评分不一致问题（US00020 100→100→64），开展自检标准校准培训 | QA部门 | 2周内 |
| P5 | 中 | 跟踪新开门店（US00007 4/30、US00010 4/28、US00015 4/30）首月巡检计划 | 运营部+QA | 5月内 |
| P6 | 中 | 维持区经检查节奏，确保 Daniel Chu / Jung Han Liang 月度均衡负荷 | 运营部 | 持续 |

### 6.3 模块改善建议（TOP 5）

**清洁卫生**（影响13家门店，扣分-322分）：
- ①清洁消毒程序每班次执行并记录；②消毒液浓度（ppm）每日校准；③食品加工区域和设备每日深度清洁。

**交叉污染防控**（影响13家门店，扣分-132分）：
- ①食品存储分区标准重新培训；②器具维护和清洁班次检查；③物料存储高度要求（6英寸）每日巡查。

**饮用水与管道系统**（影响10家门店，扣分-131分）：
- ①水滤芯更换台账建立，提前7天预警；②油脂阱/残渣阱清理纳入月度必检；③管道泄漏立即报修。

**员工健康与个人卫生**（影响6家门店，扣分-53分）：
- ①每日开班健康申报；②个人卫生（指甲、首饰、头发）班前班中检查；③洗手程序每周复训。

**产品与有效期管理**（影响6家门店，扣分-44分）：
- ①开封后标签管理纳入每日开店清单；②FIFO执行每日检查；③过期产品零容忍政策。

## 七、巡检体系分析（2026年4月专题）

✅ **4月巡检体系全面恢复**：三类巡检均处于正常节奏，区经检查在中断3个月后于4月7日由 Jung Han Liang 在 US00019 重启，本月共完成14次。

### 7.1 巡检概况

| 维度 | 门店自检 | QA审计 | 区经检查 |
|---|---|---|---|
| 巡检次数 | 33次 | 12次 | 14次 |
| 覆盖门店 | 13家 | 12家 | 13家 |
| 巡检员 | Afsana Gu、Alexander G Harry、Austin Gebhardt、Brionna Jiles、Clara Mae Venturina、Darwin Coronel、Derson Liang、Dominique Meadows、Eric Park、Huichen Jiang、Javier Cruz、Jian Ming Juo、Jonathan Soto、Joselyn Pacheco Trejo、Juan Ortiz-Fontanez、Juliana Li、Sami Dalao、Shangxian Piao、Wenny Lin、Yaqing Zuo | Eamonn Caballar | Daniel Chu、Jung Han Liang |
| 平均得分 | 81.9 分 | 80.4 分 | 80.1 分 |
| S项发现 | 9个 | 2个 | 6个 |
| M项发现 | 21个 | 11个 | 6个 |

### 7.2 同店跨类型评分对比

4月共有多家门店同时拥有两种以上巡检类型。以下为 QA审计 vs 自检/区经检查 对比：

| 门店 | QA审计得分 | 对比类型 | 对比得分 | 差距 | QA日期 | 对比日期 |
|---|---|---|---|---|---|---|
| 8th & Broadway（US00001）| 79 | 门店自检 | 91 | -12 | 2026-04-09 | 2026-04-24 |
| 8th & Broadway（US00001）| 79 | 区经检查 | 85 | -6 | 2026-04-09 | 2026-04-21 |
| 28th & 6th（US00002）| 84 | 门店自检 | 71 | +13 | 2026-04-27 | 2026-04-17 |
| 28th & 6th（US00002）| 84 | 区经检查 | 88 | -4 | 2026-04-27 | 2026-04-23 |
| 100 Maiden Ln（US00003）| 84 | 门店自检 | 96 | -12 | 2026-04-01 | 2026-04-17 |
| 100 Maiden Ln（US00003）| 84 | 区经检查 | 91 | -7 | 2026-04-01 | 2026-04-24 |
| 37th & Broadway（US00004）| 83 | 门店自检 | 79 | +4 | 2026-04-29 | 2026-04-13 |
| 37th & Broadway（US00004）| 83 | 区经检查 | 89 | -6 | 2026-04-29 | 2026-04-26 |
| 54th & 8th（US00005）| 69 | 门店自检 | 63 | +6 | 2026-04-30 | 2026-04-17 |
| 54th & 8th（US00005）| 69 | 区经检查 | 66 | +3 | 2026-04-30 | 2026-04-26 |
| 102 Fulton（US00006）| 86 | 门店自检 | 98 | -12 | 2026-04-01 | 2026-04-24 |
| 102 Fulton（US00006）| 86 | 区经检查 | 68 | +18 | 2026-04-01 | 2026-04-30 |
| 33rd & 10th（US00008）| 87 | 门店自检 | 81 | +6 | 2026-04-27 | 2026-04-24 |
| 33rd & 10th（US00008）| 87 | 区经检查 | 47 | +40 | 2026-04-27 | 2026-04-30 |
| 16th & 6th（US00012）| 75 | 门店自检 | 94 | -19 | 2026-04-29 | 2026-04-25 |
| 16th & 6th（US00012）| 75 | 区经检查 | 88 | -13 | 2026-04-29 | 2026-04-26 |
| 21st & 3rd（US00020）| 82 | 门店自检 | 100 | -18 | 2026-04-28 | 2026-04-21 |
| 21st & 3rd（US00020）| 82 | 区经检查 | 94 | -12 | 2026-04-28 | 2026-04-23 |
| 15th & 3rd（US00024）| 71 | 门店自检 | 90 | -19 | 2026-04-28 | 2026-04-25 |
| 15th & 3rd（US00024）| 71 | 区经检查 | 85 | -14 | 2026-04-28 | 2026-04-25 |
| 221 Grand（US00025）| 87 | 门店自检 | 90 | -3 | 2026-04-30 | 2026-04-26 |
| 221 Grand（US00025）| 87 | 区经检查 | 94 | -7 | 2026-04-30 | 2026-04-30 |
| 52nd & Madison（US00027）| 78 | 门店自检 | 59 | +19 | 2026-04-30 | 2026-04-22 |
| 52nd & Madison（US00027）| 78 | 区经检查 | 67 | +11 | 2026-04-30 | 2026-04-16 |

自检 vs 区经检查对比（无 QA审计直接关系，但反映自检偏高度）：

| 门店 | 自检得分 | 区经得分 | 差距 | 自检日期 | 区经日期 |
|---|---|---|---|---|---|
| 8th & Broadway（US00001）| 91 | 85 | +6 | 2026-04-24 | 2026-04-21 |
| 28th & 6th（US00002）| 71 | 88 | -17 | 2026-04-17 | 2026-04-23 |
| 100 Maiden Ln（US00003）| 96 | 91 | +5 | 2026-04-17 | 2026-04-24 |
| 37th & Broadway（US00004）| 79 | 89 | -10 | 2026-04-13 | 2026-04-26 |
| 54th & 8th（US00005）| 63 | 66 | -3 | 2026-04-17 | 2026-04-26 |
| 102 Fulton（US00006）| 98 | 68 | +30 | 2026-04-24 | 2026-04-30 |
| 33rd & 10th（US00008）| 81 | 47 | +34 | 2026-04-24 | 2026-04-30 |
| 16th & 6th（US00012）| 94 | 88 | +6 | 2026-04-25 | 2026-04-26 |
| 29th & 3rd（US00019）| 69 | 75 | -6 | 2026-04-29 | 2026-04-30 |
| 21st & 3rd（US00020）| 100 | 94 | +6 | 2026-04-21 | 2026-04-23 |
| 15th & 3rd（US00024）| 90 | 85 | +5 | 2026-04-25 | 2026-04-25 |
| 221 Grand（US00025）| 90 | 94 | -4 | 2026-04-26 | 2026-04-30 |
| 52nd & Madison（US00027）| 59 | 67 | -8 | 2026-04-22 | 2026-04-16 |

**关键发现**：

- **QA审计 vs 自检平均差距明显存在**：
  最大差距出现在 **16th & 6th（US00012）**——QA审计 75分 vs 自检 94分，差距 **19 分**。
- **门店自检 vs 区经检查仍有大幅偏离**：最严重案例 **33rd & 10th（US00008）**——自检 81分 vs 区经 47分，差距 **34 分**。
- 与3月报告 **52nd & Madison 单点21分差距** 不同，4月通过 **13家门店全覆盖** 暴露了系统性的自检偏高问题：多家自检95分以上的门店在区经/QA审计中跌至60-70分区间。
- 但相较3月仅有1组对比数据，4月的多点对比为校准培训提供了**充分样本**。门店自检评分的系统性偏高已成为关键改进点。

### 7.3 自检评分一致性分析

**US00020（21st & 3rd）4月21日 Darwin Coronel 单人三次自检案例**：

| 巡检ID | 时间 | 得分 | 扣分 | 问题数 | S | M | G | L |
|---|---|---|---|---|---|---|---|---|
| 2016 | 2026-04-21 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2017 | 2026-04-21 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2018 | 2026-04-21 | 64 | -16 | 5 | 1 | 1 | 3 | 0 |

同一巡检员、同店、同日提交三次自检：前两次均为100分零扣分，第三次发现5个扣分项（含1个S项）。摆动幅度36分，暴露门店自检在不同时段执行严格度差异巨大。建议：①自检需在交班前一次性完成而非班中分次；②对同日多次自检的情况由系统自动校验；③系统提示「今日已自检」。

**其他同日重复或大幅摆动案例：**

| 门店 | 日期 | 巡检数 | 摆动 | 详情 |
|---|---|---|---|---|
| US00020 | 2026-04-14 | 2 | 15 | Javier Cruz (门店自检, 95分) / Javier Cruz (门店自检, 80分) |
| US00025 | 2026-04-30 | 2 | 7 | Eamonn Caballar (QA审计, 87分) / Daniel Chu (区经检查, 94分) |
| US00024 | 2026-04-25 | 2 | 5 | Clara Mae Venturina (门店自检, 90分) / Daniel Chu (区经检查, 85分) |
| US00027 | 2026-04-16 | 2 | 2 | Wenny Lin (门店自检, 65分) / Jung Han Liang (区经检查, 67分) |

### 7.4 巡检员严格度对比

| 巡检员 | 职位 | 类型主导 | 巡检次 | 平均分 | 平均扣分 | 平均问题数 | S项 | M项 |
|---|---|---|---|---|---|---|---|---|
| Brionna Jiles | Shift Supervisor / Trainer | 门店自检 | 1 | 59.0 | -21.0 | 8.0 | 1 | 1 |
| Eric Park | Store Manager | 门店自检 | 1 | 63.0 | -17.0 | 7.0 | 1 | 1 |
| Jian Ming Juo | Store Manager | 门店自检 | 3 | 64.3 | -22.3 | 10.7 | 2 | 4 |
| Wenny Lin | Store Manager | 门店自检 | 1 | 65.0 | -35.0 | 16.0 | 0 | 2 |
| Juan Ortiz-Fontanez | Store Manager | 门店自检 | 1 | 66.0 | -14.0 | 4.0 | 2 | 0 |
| Afsana Gu | Store Manager | 门店自检 | 1 | 71.0 | -29.0 | 14.0 | 0 | 1 |
| Alexander G Harry | Assistant Store Manager | 门店自检 | 1 | 72.0 | -8.0 | 3.0 | 1 | 0 |
| Jung Han Liang | Area Operations Manager | 区经检查 | 7 | 75.3 | -16.1 | 7.1 | 4 | 5 |
| Austin Gebhardt | Assistant Store Manager | 门店自检 | 1 | 79.0 | -21.0 | 9.0 | 0 | 1 |
| Derson Liang | Assistant Store Manager | 门店自检 | 3 | 79.3 | -20.7 | 11.3 | 0 | 2 |
| Eamonn Caballar | Senior QA Manager | QA审计 | 12 | 80.4 | -16.2 | 7.1 | 2 | 11 |
| Yaqing Zuo | Store Manager | 门店自检 | 1 | 81.0 | -19.0 | 9.0 | 0 | 1 |
| Darwin Coronel | Store Manager | 门店自检 | 4 | 83.2 | -6.8 | 2.2 | 2 | 1 |
| Daniel Chu | Area Operations Manager | 区经检查 | 7 | 85.0 | -9.3 | 4.1 | 2 | 1 |
| Javier Cruz | Shift Supervisor / Trainer | 门店自检 | 2 | 87.5 | -12.5 | 4.0 | 0 | 3 |
| Clara Mae Venturina | Store Manager | 门店自检 | 3 | 90.0 | -10.0 | 6.0 | 0 | 1 |
| Jonathan Soto | Assistant Store Manager | 门店自检 | 1 | 90.0 | -10.0 | 7.0 | 0 | 0 |
| Huichen Jiang | Shift Supervisor / Trainer | 门店自检 | 1 | 91.0 | -9.0 | 5.0 | 0 | 0 |
| Sami Dalao | Shift Supervisor / Trainer | 门店自检 | 1 | 93.0 | -7.0 | 5.0 | 0 | 1 |
| Dominique Meadows | Store Manager | 门店自检 | 2 | 93.5 | -6.5 | 3.0 | 0 | 1 |
| Shangxian Piao | Store Manager | 门店自检 | 2 | 93.5 | -6.5 | 3.5 | 0 | 1 |
| Juliana Li | Store Manager | 门店自检 | 1 | 96.0 | -4.0 | 2.0 | 0 | 0 |
| Joselyn Pacheco Trejo | Store Manager | 门店自检 | 2 | 97.0 | -3.0 | 2.0 | 0 | 0 |

### 7.5 巡检覆盖趋势（2026年Q1+4月）

使用 **status=1（已提交）** 口径以与1月、3月报告保持一致。

| 月份 | 门店自检 | QA审计 | 区经检查 | 总数 | 状态 |
|---|---|---|---|---|---|
| 2026-01 | 7次 | 5次 | 4次 | 16 | ✅ 三类齐全 |
| 2026-02 | 5次 | 2次 | 0次 | 7 | ⚠ 区经检查中断 |
| 2026-03 | 13次 | 1次 | 0次 | 14 | 🔴 体系崩溃 |
| 2026-04 | 33次 | 12次 | 14次 | 59 | ✅ 全面恢复 |

（如包含未提交草稿 status=0：1月21次、2月13次、3月16次、4月63次。）

> **趋势分析**：从1月的三类齐全（16次），到2-3月区经检查断流、QA审计萎缩（仅14次），再到4月的全面恢复（59次），北美QA巡检体系完成了一次典型的「危机—响应」循环。Eamonn Caballar 接任 QA Senior Manager 与 Jung Han Liang/Daniel Chu 区经巡检的同步恢复是关键转折点。下一阶段需关注：①体系是否能维持4月节奏，②自检评分校准的落地效果，③单点QA Manager 的冗余安排。

---

**报告结束**

*本报告由 Claude Code 基于 empapp 门店稽核系统数据自动生成，原始 CSV 数据见 `/app/claude-code-output/april2026-inspection-export/`。*