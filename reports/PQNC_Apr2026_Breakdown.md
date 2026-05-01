# PQNC Breakdown — April 2026 (Database Extraction)

**Source:** `aws-luckyus-scmsrm-rw` / `luckyus_scm_srm` / `t_pqnc` + `t_pqnc_operate_detail`  
**Period:** 2026-04-01 to 2026-04-30 inclusive (by `created_time`)  
**Filter set:** `tenant='LKUS' AND delete_flag=0 AND status IN (4,5)` + operate_type=1 dedup via MIN per pqnc_id  
**Generated:** 2026-05-01  
**Note:** April QM Monthly Report `.pptx` not yet published as of generation date — this breakdown is built **directly from the source DB** (the same table the QA team uses to populate the deck). The locked filter set reproduces the canonical March 2026 numbers (33 / 5 / 27 / 30 / 2 / 1) **exactly** — see `reports/april2026-pqnc/march2026_validation.txt`. When the April deck is published, cross-check against this report.

---

## 1. Total & Generated Summary

**Total PQNC reported (Apr 2026): 66**

**Generated narrative (aggregate-only — no fabrication):**

> In Apr 2026, total **66** PQNC reported — roughly **2× March's 33**. **6** food-safety cases (code 0003) were identified, all attributed to suppliers — hair in powder/condensed milk, foreign material in condensed milk, and condensed-milk spoilage are the recurring food-safety patterns. **53** general defects (code 0004), with three dominant clusters: (a) cookie/croissant breakage during delivery (~14 cases); (b) **cup-lid mismatch** on 24oz iced cups — a NEW systemic issue not present in March (6 reports across multiple stores starting 2026-04-07); (c) **wrong sea-salt grade shipped** (coarse instead of fine) — a single-day cluster on 2026-04-18 spanning 8 reports across warehouse + multiple stores. Milk bottle leakage from Cream O Land (~9 reports) is also elevated vs March. By responsibility: **49** supplier, **4** warehouse, **6** joint (supplier+warehouse) — **a new responsibility bucket not used in March**, all 6 are the sea-salt-grade cluster — and **7** rejected/unclassified (incl. 4 same-day duplicate filings of one hair-in-can incident from store US00020). 已反馈给供应链。

**Source-table cross-checks (reproduced from DB):**

| PQNC type | Food | Food contact material |
|---|---:|---:|
| Food Safety Issue (0003) | 6 | - |
| General Defect (0004)    | 53 | - |
| Sensory Abnormal (0001)  | 0 | - |
| Other Unclear Situation (0002) | 0 | - |
| **Unclassified (no operate_type=1 row)** | **7** | - |

> The PQNC Type table sums to 6+53=59; the 7 unclassified cases are the deck's "Unknown/reject" bucket (closed without judgment-typing). Total reconciles to 6+53+7=66.

| PQNC Responsibility | Case |
|---|---:|
| Warehouse | 4 |
| Supplier | 49 |
| Store | 0 |
| Joint (Supplier + Warehouse) | 6 |
| Unknown / reject | 7 |

> April adds a **Joint** bucket (6 cases — the sea-salt cluster) that did not appear in March. The deck's standard 4-bucket layout will need a QA-team decision on how to allocate Joint cases (most natural: split or count separately).

---

## 2. Dimension Breakdowns

### Dimension 1 — By Risk Level (按风险分)

| Risk Level | Count | % of 66 | Notes |
|---|---:|---:|---|
| Critical (严重食安) | 0 | 0.0% | No pathogen contamination, hazardous foreign object, or allergen mislabeling reported |
| Major (食安风险) | 6 | 9.1% | All 0003-coded cases — hair in food (×2 incidents, 1 with 3 rejected dups), foreign material/spoilage in condensed milk (×4) |
| Minor (一般缺陷) | 53 | 80.3% | Cookie breakage, cup-lid mismatch, milk bottle leak, wrong sea-salt grade — no food-safety risk |
| Unclear (不明) | 7 | 10.6% | Rejected/closed-without-classification — incl. 3 same-day dup filings of hair-in-can (940-942 = dups of 939), 1 wrong-sea-salt rejected (905), 1 underfill rejected (926), 1 expired (927), 1 discontinued (921) |
| **Total** | **66** | **100.0%** | |

### Dimension 2 — By Responsibility (按判责)

| Responsibility | Count | % of 66 | Notes |
|---|---:|---:|---|
| Supplier (供应商) | 49 | 74.2% | All 6 food-safety cases + 43 general-defect cases (cookie breakage, milk bottle leak, cup-lid mismatch, missing label/ingredient, etc.) |
| Warehouse (仓库) | 4 | 6.1% | Equipment damage on receipt: Timemore scale (882), Iris drawers (884), Luckin Coffee item with broken handle (928), wet toilet paper in delivery (943) |
| Store (门店) | 0 | 0.0% | — |
| Joint (Supplier + Warehouse) | 6 | 9.1% | All 6 are the 2026-04-18 wrong-sea-salt cluster (coarse shipped instead of fine) — SCM held both supplier (wrong picked SKU) and warehouse (didn't catch on receipt) jointly responsible |
| Unknown / reject (未明确/驳回) | 7 | 10.6% | Closed without classification — see Risk-level Unclear notes above |
| **Total** | **66** | **100.0%** | |

### Dimension 3 — By Material Category (按物料大类)

| Material Category | Count | % of 66 | Notes |
|---|---:|---:|---|
| 原料 (Raw materials) | 19 | 28.8% | Condensed milk × 9 (incl. 4 dup-rejected hair cases), wrong sea salt × 8, hair-in-powder × 1, almond milk rotten × 1 |
| 轻食 (Light food / bakery) | 17 | 25.8% | Broken/cracked cookies × 14, mold on croissants × 1, missing-ingredient sandwiches × 2 |
| 包材 (Packaging) | 25 | 37.9% | Milk bottle leak × 9, cup-lid mismatch × 6, missing label × 2, coffee bag burst × 3, box dent × 1, missing straw × 1, no-date-code × 1, underfill × 2 |
| 其他 / Unclear (Other) | 5 | 7.6% | Equipment/consumables (Timemore scale, Iris drawer, Luckin handle, toilet paper) × 4 + discontinued product × 1 |
| **Total** | **66** | **100.0%** | |

---

## 3. Parsed Detail Items table

Per the original prompt §4: one row per discrete issue, extracted directly from the DB. Locations come from `factory_name` (the supplier/warehouse named in the report); the `discover_problems_time_period` column also encodes 1=at-receipt, 2=in-storage, 3=in-use, 4=after-sale (used in the Source column).

| # | Source (factory/warehouse) | Item Description (EN) | 中文描述 | Quantity | Corrective Action Summary | Source (DB row) |
|---:|---|---|---|---|---|---|
| 1 | Le Petit Paris NY | cookies has a crack | 饼干 | 1 | broken | pqnc_id 869 (at receipt) |
| 2 | FREENOW USA INC. | The cookie came broken in half. | 饼干 | 1 | broken | pqnc_id 870 (at receipt) |
| 3 | Le Petit Paris NY | Broken cookie received during delivery. | 饼干破损 | 1 | broken | pqnc_id 871 (at receipt) |
| 4 | JK Patisserire &Bakery LLC | Looks like mold on the croissants | 牛角包 | 3 | dark spots on surface. | pqnc_id 872 (after sale) |
| 5 | Luckin Medium Roast Beans | Bag was open in container | 包装袋 | 907 | broken package in sealed box. | pqnc_id 873 (in storage) |
| 6 | J.K patisserie & Bakery Chocolate Chip | 2 broken cookies | 饼干破损 | 2 | broken | pqnc_id 874 (at receipt) |
| 7 | Block& Barrel | Missing front label sticker | 缺正面标签 | 1 | missing label | pqnc_id 875 (in storage) |
| 8 | Le petite Paris ny | Item was broken | 破损 | 1 | broken | pqnc_id 876 (at receipt) |
| 9 | New York Raw Material Warehouse Distr... | Lids are loose on the cups and fall off large cups, regular cups are fine | 杯盖 | 119 | wrong size | pqnc_id 877 (in use) |
| 10 | 24 oz ice cups | 4/8 when serving the coster drinks the drinking lid not able to fit the cups. | 吸管盖 | 2 | wrong size | pqnc_id 878 (in use) |
| 11 | 24 ounce ice cup | 04/08 We were attempting to finish a customer drink and the dome lids/drinking lids did not fit p... | 圆顶盖 | 14 | wrong size | pqnc_id 879 (in use) |
| 12 | Large (24oz) iced cups | These large ice cups don't fit the dome and direct sipping lids. The flat lids fit on fine. | 平盖 | 14 | Wrong size | pqnc_id 880 (in use) |
| 13 | Block and Barrel | Missing label | 缺标签 | 1 | missing label | pqnc_id 881 (in storage) |
| 14 | Timemore | Chipped interface upon receiving goods | 破损 | 2 | broken scale | pqnc_id 882 (at receipt) |
| 15 | New York Raw Material Warehouse | Drinking lids do not fit on 24 oz ice cups | 吸管盖 | 1000 | wrong size | pqnc_id 883 (in use) |
| 16 | Iris | Both drawers are structurally cracked | 抽屉 | 2 | cracked upon delivery. | pqnc_id 884 (at receipt) |
| 17 | Freenow USA Inc | There was a hair found in powder upon opening | （参见英文描述） | 300 | foreign material-hair | pqnc_id 885 (in use) |
| 18 | Luckin | No straw inside packaging also unopened. | 无吸管 | 1 | empty package | pqnc_id 886 (in storage) |
| 19 | Casa Solana | Opened the can to find brown clump of slightly hardened milk. Had a small sour smell | 酸味 | 396 | spoilage | pqnc_id 888 (in use) |
| 20 | NBJL | The drinking lids are not fitting firmly (no click noise/too big) onto the 24oz Ice Cups. We have... | 吸管盖 | 26 | wrong size | pqnc_id 889 (in use) |
| 21 | Cream-O-Land Dairy | Whole milk was open when it was discovered | 牛奶 | 3785 | leaking | pqnc_id 891 (in storage) |
| 22 | FREENOW USA INC. | Chocolate chip cookie came broken in the pack. | 饼干 | 1 | broken | pqnc_id 892 (in storage) |
| 23 | First Ray Trading (USA) LLC | There's a hole on the bottle and milk is coming out. | 牛奶 | 3785 | leaking | pqnc_id 893 (in storage) |
| 24 | Cream O Land | A leakage is occurring. There might be a small tiny whole near the opening cap causing the leakage | 泄漏 | 3785 | leaking | pqnc_id 895 (in storage) |
| 25 | Cream O Land | Leakage of the milk before it was even used. The milk is not full to the top | 牛奶 | 3785 | leaking | pqnc_id 897 (in storage) |
| 26 | Cream o land | Milk bottles underfilled | 牛奶瓶 | 578 | underfilled. | pqnc_id 898 (at receipt) |
| 27 | J.k. Patisserie & bakery | Broken cookie when received | 饼干破损 | 1 | broken | pqnc_id 899 (at receipt) |
| 28 | J.K patisserie bakery | Cookies were broken when receiving | 饼干 | 2 | broken | pqnc_id 900 (at receipt) |
| 29 | Casa solana | Found a foreign object inside a brand new condensed milk when we opened it. Looks burnt and it's ... | 异物 | 396 | spoilage, mold was found inside the sealed can. | pqnc_id 901 (in use) |
| 30 | Morton Sea Salt Coarse | Not approved to use | 未批准使用 | 200 | wrong item was shipped to store. | pqnc_id 902 (in storage) |
| 31 | Morton | Recovered course and not fine salt | （参见英文描述） | 193 | wrong item was shipped to store. | pqnc_id 903 (after sale) |
| 32 | New York Raw Materials Warehouse | We received corase and not fine sea salt. | （参见英文描述） | 500 | wrong item was shipped to store. | pqnc_id 904 (at receipt) |
| 33 | Morton | Wrong sea salt | 海盐规格错 | 500 | — | pqnc_id 905 (in storage) |
| 34 | Morton | Different item than what was supposed to be received. Needs to be fine sea salt instead of coarse | 粗盐（应为细盐） | 500 | wrong item was shipped to store. | pqnc_id 906 (in storage) |
| 35 | Morton Salt NY Raw Material Warehouse | Coarse sea salt instead of fine | 粗盐（应为细盐） | 500 | wrong item was shipped to store. | pqnc_id 907 (in storage) |
| 36 | Morton | It's coarse salt instead of fine | 粗盐（应为细盐） | 250 | wrong item was shipped to store. | pqnc_id 908 (in use) |
| 37 | Morton salt | This is coarse instead of fine | 粗盐（应为细盐） | 250 | wrong item was shipped to store. | pqnc_id 909 (in use) |
| 38 | Califia Farms | container was broken open at the top and the almond milk is rotten | 腐败 | 11352 | leak and spoilage. | pqnc_id 910 (in use) |
| 39 | J.k. Patisserie & Bakery LLC | Broken cookie | 饼干破损 | 1 | broken | pqnc_id 914 (at receipt) |
| 40 | Le petit Paris Chocolate cookies | Broken | 破损 | 1 | broken | pqnc_id 915 (at receipt) |
| 41 | Foreign object | Small brownish material found inside | 异物（褐色物质） | 396 | spoilage | pqnc_id 916 (in use) |
| 42 | J.K Patisserie & Bakery LLC | Cookie was found cracked after being stored. It was delivered on April 22nd 2026. | 饼干 | 1 | broken | pqnc_id 917 (in storage) |
| 43 | FreeNow USA INC | Cookie came broken within the pack, not sellable | 饼干 | 1 | broken | pqnc_id 918 (in storage) |
| 44 | Cream O Land | Lid half opened so leaked some out. Can't use it | 杯盖 | 3785 | leaking | pqnc_id 919 (at receipt) |
| 45 | New York Raw Materials Warehouse Dist... | 2 heavy cream boxes were leaking milk all down the sides of them | 牛奶 | 1816 | leaking | pqnc_id 920 (at receipt) |
| 46 | New York Raw Material Warehouse | Product discontinued | 已停产 | 30 | — | pqnc_id 921 (at receipt) |
| 47 | Plant No. 42-169 | No date of expiration , only month and year | 保质期日期 | 3785 | blurry date code | pqnc_id 922 (in storage) |
| 48 | Block and barrel | The sausage egg and cheese croissant is missing the egg | 牛角包 | 1 | missing ingredient | pqnc_id 923 (in use) |
| 49 | Luckin drip coffee blend | Bag broken | 包装袋 | 907 | broken bag | pqnc_id 925 (in storage) |
| 50 | Cream o land | There not enough milk in the bottle | 牛奶 | 3785 | — | pqnc_id 926 (in storage) |
| 51 | Nanjing Apogee Food Tech | Expired on 04/25/2026 | 过期 | 4200 | — | pqnc_id 927 (in storage) |
| 52 | Luckin Coffee | came broken: handle and cracks | 手柄 | 1 | damaged upon delivery. | pqnc_id 928 (at receipt) |
| 53 | Cream O land | Whole seal was broken and whole milk is leaking | 牛奶 | 3785 | broken seal | pqnc_id 929 (in storage) |
| 54 | Cream O Land | Under filled milk gallon | 牛奶桶 | 3785 | leaking cause underweight | pqnc_id 930 (in storage) |
| 55 | Califia Farms | Extreme denting in the boxes | 凹陷 | 1892 | Dented | pqnc_id 931 (in storage) |
| 56 | Block & barrel | The sausage has no cheese inside and it came with double egg instead | 三明治 | 1 | missing ingredient | pqnc_id 933 (in use) |
| 57 | S&D Coffee Inc | Bag was discovered already bursted open inside the closed box | 包装袋 | 907 | broken package | pqnc_id 934 (at receipt) |
| 58 | Jk patlsserie & Bakery LLC | Found Cracked in two pieces | 破裂 | 1 | broken | pqnc_id 935 (at receipt) |
| 59 | New York Materials Warehouse | chunks in condensed milk, not expired. | 结块 | 396 | Solid material in the condensed milk. | pqnc_id 936 (in use) |
| 60 | J.K Pâtisserie & Bakery LLC | Went to make a cookie and saw broken one on bottom | 饼干 | 1 | broken | pqnc_id 937 (in use) |
| 61 | Cream O Land 2% fat milk | Punctured hole and squished | 破孔 | 3785 | punch hole on the bottle | pqnc_id 938 (in storage) |
| 62 | Casa Solana | There was a hair in the can upon opening that did not come from an employee. | 异物（毛发） | 396 | foreign material | pqnc_id 939 (in use) |
| 63 | Casa Solana | There was a hair in the can upon opening that wasn't from an employee. | 异物（毛发） | 396 | — | pqnc_id 940 (in use) |
| 64 | Casa Solana | A hair was found in the can upon opening | （参见英文描述） | 396 | — | pqnc_id 941 (in use) |
| 65 | Casa Solana | There was a hair in the can upon opening | 异物（毛发） | 396 | — | pqnc_id 942 (in use) |
| 66 | HEC | Toilet paper was extreme damp when discovered in the delivery | 厕纸 | 2 | wet during delivery | pqnc_id 943 (at receipt) |

---

## 4. Consolidated Item-Level Classification table

Detail items grouped into issue-types (one row = one issue-type × risk × responsibility × material combination). Counts sum to 66.

| # | Item Description (EN) | 中文描述 | Risk Level | Responsibility | Material Category | Count | Source (pqnc_id) |
|---:|---|---|---|---|---|---:|---|
| 1 | Broken/cracked cookie (multiple bakery suppliers) | 饼干破损/破碎 | Minor | Supplier | 轻食 | 14 | 869,870,871,874,876,892,899,900,914,915,917,918,935,937 |
| 2 | Mold on croissants | 牛角包发霉（外观异常） | Minor | Supplier | 轻食 | 1 | 872 |
| 3 | Sausage croissant missing egg or cheese (recipe error) | 三明治缺料 | Minor | Supplier | 轻食 | 2 | 923,933 |
| 4 | Cup–lid mismatch (24oz iced cups, dome/sipping lids) | 24oz冰杯与圆顶/吸管盖尺寸不匹配 | Minor | Supplier | 包材 | 6 | 877,878,879,880,883,889 |
| 5 | Milk bottle leak from cap/seal/puncture (Cream O Land cluster) | 牛奶瓶盖/密封泄漏（CreamOLand集中） | Minor | Supplier | 包材 | 7 | 891,893,895,897,919,929,938 |
| 6 | Heavy cream box leak | 重奶纸盒泄漏 | Minor | Supplier | 包材 | 1 | 920 |
| 7 | Milk bottle / gallon underfilled | 牛奶瓶装量不足 | Minor | Supplier | 包材 | 2 | 898,930 |
| 8 | Milk underfill (rejected — duplicate or unverified) | 牛奶装量不足（驳回） | Unclear | Unknown/reject | 包材 | 1 | 926 |
| 9 | Missing front label sticker (Block & Barrel) | 缺正面标签 | Minor | Supplier | 包材 | 2 | 875,881 |
| 10 | Coffee bag burst/torn open (3 different suppliers) | 咖啡袋破损/爆裂 | Minor | Supplier | 包材 | 3 | 873,925,934 |
| 11 | Almond milk box dent (Califia) | 杏仁奶纸箱凹陷 | Minor | Supplier | 包材 | 1 | 931 |
| 12 | No expiration date code on packaging | 包装无保质期日期 | Minor | Supplier | 包材 | 1 | 922 |
| 13 | Missing straw inside package | 包装内无吸管 | Minor | Supplier | 包材 | 1 | 886 |
| 14 | **Hair in powder (Freenow USA)** | 粉料异物（毛发） | **Major** | Supplier | 原料 | 1 | 885 |
| 15 | **Spoilage / mold / foreign object in condensed milk (Casa Solana cluster)** | 炼乳变质/异物（CasaSolana集中） | **Major** | Supplier | 原料 | 4 | 888,901,916,936 |
| 16 | **Hair in condensed milk can (Casa Solana — original report)** | 炼乳异物（毛发） | **Major** | Supplier | 原料 | 1 | 939 |
| 17 | Hair in condensed milk (3 same-day duplicate filings — rejected) | 炼乳异物（驳回-同日重复申报） | Unclear | Unknown/reject | 原料 | 3 | 940,941,942 (dup of 939) |
| 18 | Wrong sea salt — coarse instead of fine (joint resp.) | 海盐规格错（共同责任-供应商+仓储） | Minor | Joint(Supplier+Warehouse) | 原料 | 6 | 902,903,906,907,908,909 |
| 19 | Wrong sea salt — coarse (supplier resp.) | 海盐规格错（供应商） | Minor | Supplier | 原料 | 1 | 904 |
| 20 | Wrong sea salt — coarse (rejected) | 海盐规格错（驳回） | Unclear | Unknown/reject | 原料 | 1 | 905 |
| 21 | Almond milk container broken / contents rotten* | 杏仁奶容器破损/变质¹ | Minor | Supplier | 原料 | 1 | 910 |
| 22 | Expired product on receipt (rejected) | 产品过期（驳回） | Unclear | Unknown/reject | 原料 | 1 | 927 |
| 23 | Equipment chipped/cracked on delivery (Timemore scale) | 设备破损（咖啡秤） | Minor | Warehouse | 其他 | 1 | 882 |
| 24 | Equipment cracked on delivery (Iris drawers) | 设备破损（抽屉） | Minor | Warehouse | 其他 | 1 | 884 |
| 25 | Equipment broken on delivery (Luckin Coffee — handle/cracks) | 设备破损（手柄/裂纹） | Minor | Warehouse | 其他 | 1 | 928 |
| 26 | Toilet paper damp during delivery (HEC) | 厕纸运输受潮 | Minor | Warehouse | 其他 | 1 | 943 |
| 27 | Discontinued product (admin rejected) | 已停产产品（驳回） | Unclear | Unknown/reject | 其他 | 1 | 921 |
| | | | | | **Total** | **66** | |

> ¹ pqnc 910 ("container was broken open at the top and the almond milk is rotten") is coded as 0004 (General Defect → Minor) by the QA team but the description names spoilage as a downstream consequence. Material classified as **原料** because the rejected product is the contained almond milk, not the carton itself; risk kept at Minor per QA's coding but flagged for follow-up — if the carton breach was traced to packaging-design failure, this would split into a 包材 cause and 原料 disposition.

### 4a. Risk × Responsibility cross-tab

| | Supplier | Warehouse | Store | Joint(S+W) | Unknown/reject | **Total** |
|---|---:|---:|---:|---:|---:|---:|
| Critical | 0 | 0 | 0 | 0 | 0 | **0** |
| **Major** | 6 | 0 | 0 | 0 | 0 | **6** |
| Minor | 43 | 4 | 0 | 6 | 0 | **53** |
| Unclear | 0 | 0 | 0 | 0 | 7 | **7** |
| **Total** | **49** | **4** | **0** | **6** | **7** | **66** |

**Key takeaways:**
- 100% of food-safety items (Major) trace to suppliers — 6/6 = supplier-corrective-action lever.
- Warehouse-attributed items are exclusively non-food equipment/consumable damage on receipt.
- The Joint bucket is entirely the sea-salt cluster — a single-day SKU pick error that should NOT recur.
- Store responsibility = 0 (no front-of-house PQNC in April).

### 4b. Risk × Material cross-tab

| | 原料 | 轻食 | 包材 | 其他 | **Total** |
|---|---:|---:|---:|---:|---:|
| Critical | 0 | 0 | 0 | 0 | **0** |
| **Major** | 6 | 0 | 0 | 0 | **6** |
| Minor | 8 | 17 | 24 | 4 | **53** |
| Unclear | 5 | 0 | 1 | 1 | **7** |
| **Total** | **19** | **17** | **25** | **5** | **66** |

**Key takeaways:**
- All Major (food-safety) items are 原料 — concentrated in **condensed milk** (Casa Solana, 5 of 6 incidents) and 1 powder (Freenow USA). Casa Solana is a clear-cut supplier-quality escalation.
- 包材 dominates Minor (24 of 53 = 45%), driven by milk bottle leaks (Cream O Land) and cup-lid mismatch (multiple suppliers shipping non-fitting 24oz dome/sipping lids).
- 轻食 = cookie breakage during delivery: 14 of 17 are Le Petit Paris / FreeNow / JK Patisserie broken-cookie-on-receipt — packaging/transport may be the systemic root cause despite 原料-bucket coding.

---

## 5. Reconciliation Check

**Target total: 66 (per locked-filter DB query, verified against canonical March anchor)**

| Dimension | Sum | Matches total? |
|---|---:|:---:|
| Risk Level (Critical+Major+Minor+Unclear) | 0+6+53+7 | ✅ 66 |
| Responsibility (Supplier+Warehouse+Store+Joint+Unknown) | 49+4+0+6+7 | ✅ 66 |
| Material (原料+轻食+包材+其他) | 19+17+25+5 | ✅ 66 |

**Detail-vs-total check:** parsed-detail-items table has 66 rows = total 66 ✅. No inferred rows needed (every detail row maps to a real DB pqnc_id).

**Type-table reconciliation note:** the PQNC Type table sums to 6+53=59, with the 7 unclassified cases living in the Responsibility table's Unknown/reject bucket (same structural pattern as March's slide-7 32-vs-33 quirk).

---

## 6. Notable Changes vs March 2026

(March numbers from `/app/PQNC_Mar2026_Breakdown.md`.)

### 6a. Topline counts

| Metric | March | April | Δ | % change |
|---|---:|---:|---:|---:|
| Total PQNC | 33 | 66 | +33 | +100% |
| Food Safety (Major)    | 5  | 6 | +1  | +20% |
| General Defect (Minor) | 27 | 53 | +26 | +96% |
| Unclear/reject         | 1  | 7 | +6  | +600% |
| Supplier resp.         | 30 | 49| +19| +63% |
| Warehouse resp.        | 2  | 4 | +2  | +100% |
| Joint (S+W) resp.      | 0  | 6 | +6 | NEW bucket |
| Unknown/reject resp.   | 1  | 7| +6 | +600% |

### 6b. Top movers

1. **Total volume doubled** (33 → 66). The increase concentrates in three new clusters:
   - **Cup-lid mismatch on 24oz iced cups** (6 cases starting 2026-04-07) — completely absent in March. Worth a supplier-spec review with the cup vendors.
   - **Wrong sea salt grade** (8 cases on 2026-04-18 alone, coarse shipped instead of fine) — single-day pick-error cluster, joint responsibility.
   - **Milk bottle leakage from Cream O Land** (~9 cases) — March had 2 leaked-bottle cases; April has ~9 spread across April 16–30. Worth a root-cause meeting with Cream O Land (cap/seal redesign vs incoming batch defect).

2. **Hair-in-food incidents emerged** (3 distinct events: 1 hair in powder, 1 hair in condensed milk with 3 same-day duplicate filings = 4 rows, plus 4 condensed-milk spoilage/foreign-object incidents). March had 0 hair incidents. **Casa Solana condensed milk is now an escalation candidate** — 5 of 6 Major food-safety cases trace to it.

3. **Joint (Supplier+Warehouse) responsibility** is a new bucket in April. The deck's standard 4-bucket layout will need a QA decision on whether to (a) split joint across both, (b) keep as a 5th bucket, or (c) attribute to whoever was upstream (likely Supplier for SKU pick errors).

4. **Unknown/reject grew from 1 to 7**, primarily due to same-day duplicate filings (one user, Darwin Coronel, filed 4 hair-in-can reports for the same incident on 2026-04-30 — the deck likely consolidates these). Recommend a UX guard in the PQNC submission flow to dedupe per (user, item, day).

5. **Store responsibility = 0** in both months — no front-of-house PQNC. Consistent.

---

## 7. Methodology & Caveats

- **Source:** `aws-luckyus-scmsrm-rw` MySQL — `t_pqnc` (the SCM Supplier-Relationship Management PQNC table) joined to `t_pqnc_operate_detail` for type/responsibility/corrective fields.
- **Filter set (locked & March-validated):** `tenant='LKUS' AND delete_flag=0 AND status IN (4,5)`. operate_type=1 (judgment) rows are deduped to one per pqnc_id via `MIN(one_pqnc_type_code)`. This filter set reproduces canonical March numbers exactly — see `reports/april2026-pqnc/march2026_validation.txt`.
- **Categorization rules (Risk Level):**
  - Critical = pathogen / hazardous foreign object / allergen mislabeling keyword match — 0 in April.
  - Major = `one_pqnc_type_code='0003'` (Food Safety Issue).
  - Minor = `one_pqnc_type_code='0004'` (General Defect).
  - Unclear = `responsibility ∈ {6, NULL}` OR no operate_type=1 row.
- **Categorization rules (Material):** keyword rules on `factory_name` + `problem_description`. Bakery items (cookie/croissant/sandwich) → 轻食; coffee-bag/lid/bottle/cap defects on packaging → 包材; milk/condensed-milk/sea-salt/powder/coffee-beans content issues → 原料; non-food equipment (scale/drawer/handle) and consumables (toilet paper) → 其他. Rules were re-validated against each individual row in the consolidated table — see `build_pqnc_breakdown.py`.
- **No item descriptions invented.** All 66 detail rows trace to a real `t_pqnc.id`. The consolidated classification table groups identical issue-types but every group cites the underlying pqnc_ids in the Source column.
- **Edge cases ultrathought (see § 4 footnote ¹):** pqnc 910 (almond milk container broken / contents rotten) is QA-coded 0004 Minor but description names spoilage as the consequence — kept at Minor + 原料 with explicit footnote so the QA team can decide whether to split into 包材 cause + 原料 disposition. pqnc 873/925/934 (coffee bags burst/torn) are kept at 包材 because the deck convention is "bag tear → packaging defect" even when contents = beans.
- **Duplicate-filing handling:** pqnc 940/941/942 are same-day re-submissions of the same hair-in-can incident as 939 (same user Darwin Coronel, same factory Casa Solana, same day 2026-04-30). They were closed with responsibility=6 (admin rejected). Per the prompt's split rule ("do NOT collapse them into a single line"), they appear as separate rows in the Parsed Detail Items table; the consolidated classification groups 939 as Major+Supplier and 940-942 as Unclear+Unknown/reject.
- **PII check:** PQNC rows reference suppliers (factories) and store-side reporters by name; no customer email/phone/payment data appears in this extraction. The `party_name` column names internal Luckin USA staff who filed the report — kept verbatim, no masking applied (internal accountability, consistent with QA-team practice).
- **Open items for QA team:**
  1. Confirm the deck's mapping of `responsibility=6` to "Unknown/reject" (undocumented value, matches March 1-of-1).
  2. Decide deck treatment of `responsibility=4` Joint cases (split, keep separate, or attribute to Supplier).
  3. Casa Solana condensed milk: 5 of 6 Major food-safety cases — escalate to supplier audit?
  4. Cream O Land milk bottle leak (~9 cases): cap/seal QC issue or incoming-batch defect?
  5. Cup-lid mismatch on 24oz iced cups (6 cases across multiple lid suppliers): verify cup-spec change vs lid-spec change with SCM.
  6. Implement de-duplication guard in the PQNC submission UI (per user × per item × per day).

