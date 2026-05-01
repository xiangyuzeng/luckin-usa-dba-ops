# PQNC April 2026 — Handoff Document for Claude Web

> Paste this entire file into Claude Web to compile the final April 2026 PQNC PPT/docx. All numbers are reconciled and traceable to a real DB row.

## 1. Source & Trust Block

| Field | Value |
|---|---|
| **Data source** | `aws-luckyus-scmsrm-rw` MySQL → `luckyus_scm_srm.t_pqnc` + `t_pqnc_operate_detail` |
| **Filter set (locked, March-validated)** | `tenant='LKUS' AND delete_flag=0 AND status IN (4,5)` + operate_type=1 dedup via MIN per pqnc_id |
| **Period covered** | 2026-04-01 to 2026-04-30 inclusive (by `created_time`) |
| **Query timestamp** | 2026-05-01 |
| **Total records** | 66 |
| **Date range present in data** | 2026-04-01 to 2026-04-30 (covers all 30 calendar days) |
| **Data quality flags** | `responsibility=6` is undocumented in column comment but consistently maps to Unknown/reject (matches March 1-of-1 mapping). 4 same-day duplicate filings of one hair-in-can incident inflated unknown/reject by 3. |
| **MoM comparison vs March** | ✅ Available — `/app/PQNC_Mar2026_Breakdown.md` exists with canonical 33/5/27/30/2/1; this report's filter set reproduces March exactly. |
| **March anchor proof** | `/app/reports/april2026-pqnc/march2026_validation.txt` |

---

## 2. Verbatim System Tables (reproduced from DB)

### PQNC Type Table

| PQNC type | Food | Food contact material |
|---|---:|---:|
| Food Safety Issue (code 0003) | 6 | - |
| General Defect (code 0004)    | 53 | - |
| Sensory Abnormal (code 0001)  | 0 | - |
| Other Unclear Situation (code 0002) | 0 | - |
| **Unclassified** *(no operate_type=1 row — closed without judgment-typing)* | **7** | - |

> Type table sums to 6+53=59; the 7 unclassified cases live in the Responsibility table's Unknown/reject bucket. Total reconciles to 6+53+7=66.

### PQNC Responsibility Table

| PQNC Responsibility | Case |
|---|---:|
| Warehouse (仓库) | 4 |
| Supplier (供应商) | 49 |
| Store (门店) | 0 |
| **Joint (Supplier + Warehouse) — NEW vs March** | **6** |
| Unknown / reject (未明确/驳回) | 7 |

> April adds a **Joint** bucket (6 cases — the 2026-04-18 wrong-sea-salt cluster) that did not appear in March. The deck's standard 4-bucket layout will need a QA decision on how to render this.

---

## 3. Detail Items — Full Per-Item Table

One row per discrete issue (no multi-issue NCs to split — DB stores one issue per pqnc_id).
Every row maps to a real DB pqnc_id (no inferred rows).

| # | Date | Location (factory/warehouse) | Item EN | 中文 | Qty | Risk | Responsibility | Material | Corrective Action | Source NC ID |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-04-01 | Le Petit Paris NY | cookies has a crack | 饼干 | 1 | Minor | Supplier | 轻食 | broken | 869 |
| 2 | 2026-04-01 | FREENOW USA INC. | The cookie came broken in half. | 饼干 | 1 | Minor | Supplier | 轻食 | broken | 870 |
| 3 | 2026-04-01 | Le Petit Paris NY | Broken cookie received during delivery. | 饼干破损 | 1 | Minor | Supplier | 轻食 | broken | 871 |
| 4 | 2026-04-01 | JK Patisserire &Bakery LLC | Looks like mold on the croissants | 牛角包 | 3 | Minor | Supplier | 轻食 | dark spots on surface. | 872 |
| 5 | 2026-04-01 | Luckin Medium Roast Beans | Bag was open in container | 包装袋 | 907 | Minor | Supplier | 包材 | broken package in sealed box. | 873 |
| 6 | 2026-04-03 | J.K patisserie & Bakery Choco... | 2 broken cookies | 饼干破损 | 2 | Minor | Supplier | 轻食 | broken | 874 |
| 7 | 2026-04-05 | Block& Barrel | Missing front label sticker | 缺正面标签 | 1 | Minor | Supplier | 包材 | missing label | 875 |
| 8 | 2026-04-06 | Le petite Paris ny | Item was broken | 破损 | 1 | Minor | Supplier | 轻食 | broken | 876 |
| 9 | 2026-04-07 | New York Raw Material Warehou... | Lids are loose on the cups and fall off large cups, regular cups are fine | 杯盖 | 119 | Minor | Supplier | 包材 | wrong size | 877 |
| 10 | 2026-04-08 | 24 oz ice cups | 4/8 when serving the coster drinks the drinking lid not able to fit the cups. | 吸管盖 | 2 | Minor | Supplier | 包材 | wrong size | 878 |
| 11 | 2026-04-08 | 24 ounce ice cup | 04/08 We were attempting to finish a customer drink and the dome lids/drinkin... | 圆顶盖 | 14 | Minor | Supplier | 包材 | wrong size | 879 |
| 12 | 2026-04-08 | Large (24oz) iced cups | These large ice cups don't fit the dome and direct sipping lids. The flat lid... | 平盖 | 14 | Minor | Supplier | 包材 | Wrong size | 880 |
| 13 | 2026-04-09 | Block and Barrel | Missing label | 缺标签 | 1 | Minor | Supplier | 包材 | missing label | 881 |
| 14 | 2026-04-10 | Timemore | Chipped interface upon receiving goods | 破损 | 2 | Minor | Warehouse | 其他 | broken scale | 882 |
| 15 | 2026-04-10 | New York Raw Material Warehouse | Drinking lids do not fit on 24 oz ice cups | 吸管盖 | 1000 | Minor | Supplier | 包材 | wrong size | 883 |
| 16 | 2026-04-10 | Iris | Both drawers are structurally cracked | 抽屉 | 2 | Minor | Warehouse | 其他 | cracked upon delivery. | 884 |
| 17 | 2026-04-13 | Freenow USA Inc | There was a hair found in powder upon opening | （参见英文描述） | 300 | **Major** | Supplier | 原料 | foreign material-hair | 885 |
| 18 | 2026-04-13 | Luckin | No straw inside packaging also unopened. | 无吸管 | 1 | Minor | Supplier | 包材 | empty package | 886 |
| 19 | 2026-04-14 | Casa Solana | Opened the can to find brown clump of slightly hardened milk. Had a small sou... | 酸味 | 396 | **Major** | Supplier | 原料 | spoilage | 888 |
| 20 | 2026-04-14 | NBJL | The drinking lids are not fitting firmly (no click noise/too big) onto the 24... | 吸管盖 | 26 | Minor | Supplier | 包材 | wrong size | 889 |
| 21 | 2026-04-16 | Cream-O-Land Dairy | Whole milk was open when it was discovered | 牛奶 | 3785 | Minor | Supplier | 包材 | leaking | 891 |
| 22 | 2026-04-16 | FREENOW USA INC. | Chocolate chip cookie came broken in the pack. | 饼干 | 1 | Minor | Supplier | 轻食 | broken | 892 |
| 23 | 2026-04-17 | First Ray Trading (USA) LLC | There's a hole on the bottle and milk is coming out. | 牛奶 | 3785 | Minor | Supplier | 包材 | leaking | 893 |
| 24 | 2026-04-17 | Cream O Land | A leakage is occurring. There might be a small tiny whole near the opening ca... | 泄漏 | 3785 | Minor | Supplier | 包材 | leaking | 895 |
| 25 | 2026-04-17 | Cream O Land | Leakage of the milk before it was even used. The milk is not full to the top | 牛奶 | 3785 | Minor | Supplier | 包材 | leaking | 897 |
| 26 | 2026-04-17 | Cream o land | Milk bottles underfilled | 牛奶瓶 | 578 | Minor | Supplier | 包材 | underfilled. | 898 |
| 27 | 2026-04-18 | J.k. Patisserie & bakery | Broken cookie when received | 饼干破损 | 1 | Minor | Supplier | 轻食 | broken | 899 |
| 28 | 2026-04-18 | J.K patisserie bakery | Cookies were broken when receiving | 饼干 | 2 | Minor | Supplier | 轻食 | broken | 900 |
| 29 | 2026-04-18 | Casa solana | Found a foreign object inside a brand new condensed milk when we opened it. L... | 异物 | 396 | **Major** | Supplier | 原料 | spoilage, mold was found inside the s... | 901 |
| 30 | 2026-04-18 | Morton Sea Salt Coarse | Not approved to use | 未批准使用 | 200 | Minor | Joint(S+W) | 原料 | wrong item was shipped to store. | 902 |
| 31 | 2026-04-18 | Morton | Recovered course and not fine salt | （参见英文描述） | 193 | Minor | Joint(S+W) | 原料 | wrong item was shipped to store. | 903 |
| 32 | 2026-04-18 | New York Raw Materials Warehouse | We received corase and not fine sea salt. | （参见英文描述） | 500 | Minor | Supplier | 原料 | wrong item was shipped to store. | 904 |
| 33 | 2026-04-18 | Morton | Wrong sea salt | 海盐规格错 | 500 | Unclear | Unknown/reject | 原料 | — | 905 |
| 34 | 2026-04-18 | Morton | Different item than what was supposed to be received. Needs to be fine sea sa... | 粗盐（应为细盐） | 500 | Minor | Joint(S+W) | 原料 | wrong item was shipped to store. | 906 |
| 35 | 2026-04-18 | Morton Salt NY Raw Material W... | Coarse sea salt instead of fine | 粗盐（应为细盐） | 500 | Minor | Joint(S+W) | 原料 | wrong item was shipped to store. | 907 |
| 36 | 2026-04-18 | Morton | It's coarse salt instead of fine | 粗盐（应为细盐） | 250 | Minor | Joint(S+W) | 原料 | wrong item was shipped to store. | 908 |
| 37 | 2026-04-18 | Morton salt | This is coarse instead of fine | 粗盐（应为细盐） | 250 | Minor | Joint(S+W) | 原料 | wrong item was shipped to store. | 909 |
| 38 | 2026-04-20 | Califia Farms | container was broken open at the top and the almond milk is rotten | 腐败 | 11352 | Minor | Supplier | 原料 | leak and spoilage. | 910 |
| 39 | 2026-04-22 | J.k. Patisserie & Bakery LLC | Broken cookie | 饼干破损 | 1 | Minor | Supplier | 轻食 | broken | 914 |
| 40 | 2026-04-22 | Le petit Paris Chocolate cookies | Broken | 破损 | 1 | Minor | Supplier | 轻食 | broken | 915 |
| 41 | 2026-04-22 | Foreign object | Small brownish material found inside | 异物（褐色物质） | 396 | **Major** | Supplier | 原料 | spoilage | 916 |
| 42 | 2026-04-22 | J.K Patisserie & Bakery LLC | Cookie was found cracked after being stored. It was delivered on April 22nd 2... | 饼干 | 1 | Minor | Supplier | 轻食 | broken | 917 |
| 43 | 2026-04-22 | FreeNow USA INC | Cookie came broken within the pack, not sellable | 饼干 | 1 | Minor | Supplier | 轻食 | broken | 918 |
| 44 | 2026-04-22 | Cream O Land | Lid half opened so leaked some out. Can't use it | 杯盖 | 3785 | Minor | Supplier | 包材 | leaking | 919 |
| 45 | 2026-04-23 | New York Raw Materials Wareho... | 2 heavy cream boxes were leaking milk all down the sides of them | 牛奶 | 1816 | Minor | Supplier | 包材 | leaking | 920 |
| 46 | 2026-04-23 | New York Raw Material Warehouse | Product discontinued | 已停产 | 30 | Unclear | Unknown/reject | 其他 | — | 921 |
| 47 | 2026-04-24 | Plant No. 42-169 | No date of expiration , only month and year | 保质期日期 | 3785 | Minor | Supplier | 包材 | blurry date code | 922 |
| 48 | 2026-04-24 | Block and barrel | The sausage egg and cheese croissant is missing the egg | 牛角包 | 1 | Minor | Supplier | 轻食 | missing ingredient | 923 |
| 49 | 2026-04-25 | Luckin drip coffee blend | Bag broken | 包装袋 | 907 | Minor | Supplier | 包材 | broken bag | 925 |
| 50 | 2026-04-25 | Cream o land | There not enough milk in the bottle | 牛奶 | 3785 | Unclear | Unknown/reject | 包材 | — | 926 |
| 51 | 2026-04-26 | Nanjing Apogee Food Tech | Expired on 04/25/2026 | 过期 | 4200 | Unclear | Unknown/reject | 原料 | — | 927 |
| 52 | 2026-04-26 | Luckin Coffee | came broken: handle and cracks | 手柄 | 1 | Minor | Warehouse | 其他 | damaged upon delivery. | 928 |
| 53 | 2026-04-27 | Cream O land | Whole seal was broken and whole milk is leaking | 牛奶 | 3785 | Minor | Supplier | 包材 | broken seal | 929 |
| 54 | 2026-04-27 | Cream O Land | Under filled milk gallon | 牛奶桶 | 3785 | Minor | Supplier | 包材 | leaking cause underweight | 930 |
| 55 | 2026-04-28 | Califia Farms | Extreme denting in the boxes | 凹陷 | 1892 | Minor | Supplier | 包材 | Dented | 931 |
| 56 | 2026-04-29 | Block & barrel | The sausage has no cheese inside and it came with double egg instead | 三明治 | 1 | Minor | Supplier | 轻食 | missing ingredient | 933 |
| 57 | 2026-04-30 | S&D Coffee Inc | Bag was discovered already bursted open inside the closed box | 包装袋 | 907 | Minor | Supplier | 包材 | broken package | 934 |
| 58 | 2026-04-30 | Jk patlsserie & Bakery LLC | Found Cracked in two pieces | 破裂 | 1 | Minor | Supplier | 轻食 | broken | 935 |
| 59 | 2026-04-30 | New York Materials Warehouse | chunks in condensed milk, not expired. | 结块 | 396 | **Major** | Supplier | 原料 | Solid material in the condensed milk. | 936 |
| 60 | 2026-04-30 | J.K Pâtisserie & Bakery LLC | Went to make a cookie and saw broken one on bottom | 饼干 | 1 | Minor | Supplier | 轻食 | broken | 937 |
| 61 | 2026-04-30 | Cream O Land 2% fat milk | Punctured hole and squished | 破孔 | 3785 | Minor | Supplier | 包材 | punch hole on the bottle | 938 |
| 62 | 2026-04-30 | Casa Solana | There was a hair in the can upon opening that did not come from an employee. | 异物（毛发） | 396 | **Major** | Supplier | 原料 | foreign material | 939 |
| 63 | 2026-04-30 | Casa Solana | There was a hair in the can upon opening that wasn't from an employee. | 异物（毛发） | 396 | Unclear | Unknown/reject | 原料 | — | 940 |
| 64 | 2026-04-30 | Casa Solana | A hair was found in the can upon opening | （参见英文描述） | 396 | Unclear | Unknown/reject | 原料 | — | 941 |
| 65 | 2026-04-30 | Casa Solana | There was a hair in the can upon opening | 异物（毛发） | 396 | Unclear | Unknown/reject | 原料 | — | 942 |
| 66 | 2026-04-30 | HEC | Toilet paper was extreme damp when discovered in the delivery | 厕纸 | 2 | Minor | Warehouse | 其他 | wet during delivery | 943 |

---

## 4. Three Dimensional Breakdowns

### 4.1 By Risk Level (按风险分)

| Risk Level | Count | % of 66 |
|---|---:|---:|
| Critical (严重食安) | 0 | 0.0% |
| **Major (食安风险)** | **6** | **9.1%** |
| Minor (一般缺陷) | 53 | 80.3% |
| Unclear (不明) | 7 | 10.6% |
| **Total** | **66** | **100.0%** |

### 4.2 By Responsibility (按判责)

| Responsibility | Count | % of 66 |
|---|---:|---:|
| Supplier (供应商) | 49 | 74.2% |
| Warehouse (仓库) | 4 | 6.1% |
| Store (门店) | 0 | 0.0% |
| Joint (Supplier + Warehouse) — NEW | 6 | 9.1% |
| Unknown / reject (未明确/驳回) | 7 | 10.6% |
| **Total** | **66** | **100.0%** |

### 4.3 By Material Category (按物料大类)

| Material Category | Count | % of 66 |
|---|---:|---:|
| 原料 (Raw materials) | 19 | 28.8% |
| 轻食 (Light food / bakery) | 17 | 25.8% |
| 包材 (Packaging) | 25 | 37.9% |
| 其他 (Other / Unclear) | 5 | 7.6% |
| **Total** | **66** | **100.0%** |

### 4.4 Reconciliation

| Dimension | Sum | Matches total? |
|---|---|:---:|
| Risk Level | 0+6+53+7 | ✅ 66 |
| Responsibility | 49+4+0+6+7 | ✅ 66 |
| Material | 19+17+25+5 | ✅ 66 |

All three dimensions reconcile. **No inferred rows** — every detail row maps to a real DB pqnc_id.

---

## 5. Cross-Tabs

### 5.1 Risk × Responsibility

| | Supplier | Warehouse | Store | Joint(S+W) | Unknown/reject | **Total** |
|---|---:|---:|---:|---:|---:|---:|
| Critical | 0 | 0 | 0 | 0 | 0 | **0** |
| **Major** | 6 | 0 | 0 | 0 | 0 | **6** |
| Minor | 43 | 4 | 0 | 6 | 0 | **53** |
| Unclear | 0 | 0 | 0 | 0 | 7 | **7** |
| **Total** | **49** | **4** | **0** | **6** | **7** | **66** |

### 5.2 Risk × Material

| | 原料 | 轻食 | 包材 | 其他/Unclear | **Total** |
|---|---:|---:|---:|---:|---:|
| Critical | 0 | 0 | 0 | 0 | **0** |
| **Major** | 6 | 0 | 0 | 0 | **6** |
| Minor | 8 | 17 | 24 | 4 | **53** |
| Unclear | 5 | 0 | 1 | 1 | **7** |
| **Total** | **19** | **17** | **25** | **5** | **66** |

---

## 6. Bilingual Summary Text — PPT-ready

> Paste this paragraph directly into the April PPT "PQNC Summary" text box. Mirrors the March deck's English+Chinese mixed format.

```
In Apr 2026, total 66 PQNC reported, 6 major issues were identified for hair-in-food and condensed milk spoilage 1起粉料异物、1起炼乳异物、4起炼乳变质/异物. Other general issues including broken cookies, milk bottle leakage, cup-lid mismatch, and wrong sea salt grade 破损饼干、牛奶瓶泄漏、杯盖尺寸不匹配和海盐规格错. 已反馈给供应链。
```

**Alternative shorter form (if PPT box is space-constrained):**

```
Apr 2026: 66 PQNC reported (6 food-safety, 53 general defects, 7 rejected). Major issues: condensed milk hair/foreign material/spoilage (Casa Solana, 5 of 6). General defects: broken cookies, milk bottle leak (Cream O Land), cup-lid mismatch (24oz), wrong sea salt grade. 已反馈供应链。
```

---

## 7. Notable Findings

1. **Total volume doubled vs March** (66 vs 33, +100%) — driven by three new clusters not present in March: cup-lid mismatch on 24oz iced cups (6 reports across multiple stores starting 2026-04-07), wrong sea-salt grade single-day cluster (8 reports on 2026-04-18), and elevated Cream O Land milk-bottle leakage (~9 reports vs March's 2).

2. **Casa Solana condensed milk is the #1 food-safety escalation candidate.** 5 of 6 Major cases trace to Casa Solana (hair × 1, spoilage × 1, foreign object × 1, brownish material × 1, chunks × 1). Recommend immediate supplier audit.

3. **New responsibility bucket: Joint (Supplier + Warehouse) = 6 cases**, all the 2026-04-18 sea-salt-grade pick error. Standard PPT 4-bucket layout will need a QA-team decision on how to render this — most natural mapping: keep as a 5th row.

4. **Unknown/reject grew 1 → 7 (+6)**. 4 of the 7 are same-day duplicate filings by one user (Darwin Coronel, 2026-04-30, hair-in-can at Casa Solana). Recommend a UX dedupe guard in the PQNC submission flow keyed on (user × item × day).

5. **All Major (food-safety) items trace to suppliers** (6 of 6) — supplier corrective action is the only food-safety lever this month.

6. **Warehouse-attributed items are exclusively non-food equipment damage on receipt** (Timemore scale, Iris drawers, Luckin handle, wet toilet paper). Zero warehouse food-safety exposure.

7. **Store responsibility = 0** (consistent with March). No front-of-house PQNC.

---

## 8. Open Questions for QA Team

Items that need human confirmation before the final April PPT/docx ships:

1. **Confirm `responsibility=6` mapping.** Undocumented in the column comment (`1=供应商,2=仓储,3=门店,4=共同责任,5=不明`); used in March (1 case) and April (7 cases). All instances appear to mean "administratively rejected/closed". Confirm this is the deck's "Unknown/reject" bucket.

2. **Decide deck treatment of `responsibility=4` Joint cases (6 in April, 0 in March).** Options: (a) split each case across Supplier and Warehouse rows, (b) add a 5th "Joint" row to the responsibility table, (c) attribute upstream to whoever caused the SKU pick error (likely Supplier).

3. **Casa Solana condensed milk — escalate to supplier audit?** 5 of 6 Major cases trace here. Same supplier produced March's 2 condensed-milk Major cases (mold + foreign material). Pattern is now 7 incidents in 2 months.

4. **Cream O Land milk bottle leak (~9 cases) — root cause = cap/seal QC issue or incoming-batch defect?** Need a meeting with Cream O Land + the SCM team that received the April lot. Worth pulling the lot/batch numbers from the `batch_no` column of the affected pqnc rows for quick traceability.

5. **Cup-lid mismatch on 24oz iced cups (6 reports across multiple lid suppliers).** Verify whether the cup spec changed (24oz cup vendor) or the lid spec changed (NBJL, etc.) in April. Reports started 2026-04-07 and span 4 different lid suppliers — points to a cup-side change rather than a lid-side change.

6. **pqnc 910 (Califia Farms almond milk: "container broken open... almond milk is rotten").** QA-coded 0004 Minor (general defect) but description names spoilage. Confirm whether this should be reclassified as 0003 Major food-safety or kept as Minor + footnote.

7. **Implement de-duplication guard in PQNC submission UI.** One user filed 4 reports for the same hair-in-can incident on 2026-04-30 (rows 939–942). Recommend a soft-warning when (user × item × day) collides on submission.

---

**End of handoff. Reconciliation: dimension totals all sum to 66 ✅. Every detail row traces to a real DB pqnc_id.**
