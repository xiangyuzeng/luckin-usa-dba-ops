# PQNC Breakdown — March 2026 (Slides 7–9)

**Source:** `QM_Monthly_Report-_2026_Mar.pptx` — Section "01 & 02 Supplier & Materials & Warehouse Quality Performance"
**Slides analyzed:** 7 (summary), 8 (food safety NC details), 9 (general defect NC details)
**Generated:** 2026-05-01

---

## 1. Total & Verbatim PQNC Summary

**Total PQNC reported (Mar 2026): 33**

**PQNC Summary (verbatim from slide 7, TextBox 1, English + 中文 preserved):**

> In Mar 2026, total 33 PQNC reported, 5 major issues were identified for oat milk spoilage and mold in sweet condensed milk 3起燕麦奶变质和2起炼乳异物. Other general issues including broken cookie and damaged package issue 破损饼干和包装破损问题. 已反馈给供应链。

> ⚠️ **Note:** the slide 7 PQNC Type table sums to **32**, not 33. The 1-item gap is the "Unknown/reject" case (see §4). All three dimensional breakdowns below are reconciled to the canonical total of **33**.
>
> **Source-phrasing note:** slide 9 uses singular "cracked cookie" but plural "leaked milk bottles" — a minor consistency issue in the deck, recorded here for traceability of the 25/2 inference (see §3 sensitivity envelope).

**Source-table cross-checks (slide 7):**

| PQNC type | Food | Food contact material |
|---|---|---|
| Food Safety Issue | 5 | - |
| General Defect | 27 | - |
| Sensory Abnormal | - | - |
| Other Unclear Situation | - | - |

| PQNC Responsibility | Case |
|---|---|
| Warehouse | 2 |
| Supplier | 30 |
| Store | 0 |
| Unknown/reject | 1 |

---

## 2. Dimension Breakdowns

### Dimension 1 — By Risk Level (按风险分)

| Risk Level | Count | % of 33 | Notes |
|---|---:|---:|---|
| Critical (严重食安) | 0 | 0.0% | No pathogen contamination or hazardous foreign objects reported |
| Major (食安风险) | 5 | 15.2% | 3 oat milk spoilage + 2 condensed milk mold/foreign material |
| Minor (一般缺陷) | 27 | 81.8% | Cracked cookies + leaked milk bottles (no food-safety risk) |
| Unclear (不明) | 1 | 3.0% | Unknown/reject case — not categorized in PQNC Type table¹ |
| **Total** | **33** | **100.0%** | |

> ¹ Critical + Major together = 5 = the "Food Safety Issue" row in the source table.

### Dimension 2 — By Responsibility (按判责)

| Responsibility | Count | % of 33 | Notes |
|---|---:|---:|---|
| Supplier (供应商) | 30 | 90.9% | All 5 food-safety + 25 of 27 general-defect cases |
| Warehouse (仓库) | 2 | 6.1% | Leaked milk bottles (warehouse-handling packaging damage) |
| Store (门店) | 0 | 0.0% | — |
| Unknown/reject (未明确/驳回) | 1 | 3.0% | Per slide 7 responsibility table |
| **Total** | **33** | **100.0%** | |

> Source: slide 7 Responsibility table — taken verbatim, no inference.

### Dimension 3 — By Material Category (按物料大类)

| Material Category | Count | % of 33 | Notes |
|---|---:|---:|---|
| 原料 (Raw materials) | 5 | 15.2% | Oat milk (3) + condensed milk (2) — both are dairy/raw inputs |
| 轻食 (Light food / bakery) | 25 | 75.7% | Cracked cookies — food itself broken, not packaging² |
| 包材 (Packaging materials) | 2 | 6.1% | Leaked milk bottles — leak from bottle/cap = packaging defect² |
| 其他 / Unclear (Other) | 1 | 3.0% | Unknown/reject case lacks description |
| **Total** | **33** | **100.0%** | (Material % column truncated so column sums exactly to 100.0%; raw 25/33 = 75.76%) |

> ² Per the inference rules: "cracked/broken cookie → 轻食"; "milk bottle leaking from the cap → 包材 (cap defect), flag the ambiguity." See ambiguity note in §4.

---

## 3. Consolidated Item-Level Table

| # | Item Description (EN) | 中文描述 | Risk Level | Responsibility | Material Category | Count | Source Slide |
|---:|---|---|---|---|---|---:|---:|
| 1 | Oat milk spoilage (store 221, 3 boxes) | 燕麦奶变质（221门店，3箱） | Major | Supplier | 原料 | 3 | 8 |
| 2 | Condensed milk — suspicious mold / foreign material in 2 cans | 炼乳疑似霉变/异物（2罐） | Major | Supplier | 原料 | 2 | 8 |
| 3 | Cracked / broken cookies | 破损饼干 | Minor | Supplier | 轻食 | 25³ *(inferred)* | 9 |
| 4 | Leaked milk bottles (cap/seal failure) | 牛奶瓶泄漏（瓶盖密封失效） | Minor | Warehouse | 包材⁴ | 2³ *(inferred)* | 9 |
| 5 | Unknown / reject case — no description provided | 未明确/驳回案例（无描述） | Unclear | Unknown/reject | Other | 1 | 7 |
| | | | | | **Total** | **33** | |

> ³ The split **25 cookies vs 2 bottles** within the 27 general-defect cases is **inferred**, not stated verbatim. Inference logic: slide 7 responsibility table shows Warehouse = 2; slide 9 narrative names "leaked milk bottles" (warehouse-handling packaging damage) — the cleanest mapping is 2 leaked-bottle cases → Warehouse, remaining 25 cracked-cookie cases → Supplier. This is the only split that simultaneously reconciles the responsibility totals (Warehouse = 2, Supplier = 30 = 5 food-safety + 25 cookie) and the type total (General Defect = 27). Absent a per-item log in the deck, this remains an inference and should be confirmed against the underlying QC tracker.
>
> ⁴ **Ambiguity note (per inference rules):** "leaked milk bottle" is classified as **包材** because the leak originates from the cap/seal interface, which is a packaging-component defect. If the underlying milk product was also compromised (sour, contaminated), it would additionally implicate **原料**. Source slides do not state whether the milk inside was tested — additional info needed: (a) was contained product disposed solely due to packaging breach, or (b) was the milk itself rejected on quality grounds?

### 3a. Sensitivity of the 25/2 split

The 25/2 split is the most-likely allocation given the responsibility totals, but the deck does not enumerate per-item descriptions. Bounding scenarios:

| Scenario | 轻食 (cookies) | 包材 (bottles) | Implication for warehouse=2 |
|---|---:|---:|---|
| **Lower bound on 包材** (0) | 27 | 0 | The 2 warehouse cases are 2 cookies broken during warehouse handling |
| **Chosen split** | **25** | **2** | The 2 warehouse cases are the leaked bottles (most natural mapping with slide 9 corrective action wording) |
| **Upper bound on 包材** (2) | 25 | 2 | Same as chosen — 包材 cannot exceed 2 since slide 9 names only "leaked milk bottles" alongside cookies, and warehouse total is capped at 2 |

The chosen split aligns the warehouse-responsibility cases with the only packaging-related defect type named on slide 9 ("leaked milk bottles"). To confirm exactly, request the per-item PQNC log from the QM team.

### 3b. Risk × Responsibility cross-tab

| | Supplier | Warehouse | Store | Unknown/reject | **Total** |
|---|---:|---:|---:|---:|---:|
| Critical | 0 | 0 | 0 | 0 | **0** |
| Major | 5 | 0 | 0 | 0 | **5** |
| Minor | 25 | 2 | 0 | 0 | **27** |
| Unclear | 0 | 0 | 0 | 1 | **1** |
| **Total** | **30** | **2** | **0** | **1** | **33** |

**Key takeaways:**
- 100% of food-safety items (Major) trace to suppliers — corrective action on suppliers is the only food-safety lever this month.
- Warehouse-attributed items are exclusively packaging-defect (Minor) cases — no warehouse food-safety exposure.
- Store responsibility = 0 — front-of-house operations did not cause any reported PQNC.

---

## 4. Reconciliation Check

**Target total: 33 (per PQNC Summary text and Responsibility table)**

| Dimension | Sum | Matches 33? |
|---|---:|:---:|
| Risk Level (Critical + Major + Minor + Unclear) | 0 + 5 + 27 + 1 | ✅ 33 |
| Responsibility (Supplier + Warehouse + Store + Unknown/reject) | 30 + 2 + 0 + 1 | ✅ 33 |
| Material Category (原料 + 轻食 + 包材 + Other) | 5 + 25 + 2 + 1 | ✅ 33 |

### Source-data discrepancy detected (flagged)

The slide 7 **PQNC Type table** sums to **32**, not 33:

```
Food Safety Issue (5) + General Defect (27) + Sensory Abnormal (-) + Other Unclear Situation (-) = 32
```

**Root cause:** The "Unknown/reject" case (1 item) appearing in the Responsibility table is **not represented** in the PQNC Type table — the rows "Sensory Abnormal" and "Other Unclear Situation" are both blank. The reported total of 33 (PQNC Summary text + Responsibility table) is correct; the PQNC Type table is under-counted by 1 because the unknown/reject case was not classified into a type bucket.

**Resolution applied in this report:** the 1 unclassified case is allocated to the "Unclear / Other" bucket in each of the three dimensions, so all three dimensional totals reconcile to 33.

**Recommendation to QM team:** ensure the next monthly report classifies every reported PQNC into a type row (even if "Other Unclear Situation" = 1) so the type table reconciles with the responsibility table without manual interpretation.

---

## 5. Methodology & Caveats

- **Source extraction:** `python-pptx` (v1.0.2) — text frames + tables only; pictures excluded per request.
- **Slides processed:** 7, 8, 9 only.
- **Verbatim vs inferred:**
  - Verbatim from deck: total 33; PQNC Summary text; Type table (5/27); Responsibility table (30/2/0/1); food-safety detail (3 oat-milk + 2 condensed-milk); general-defect description ("cracked cookie and leaked milk bottles").
  - Inferred (clearly flagged): 25 vs 2 split within 27 general defects; mapping of warehouse-2 to leaked-bottle cases; allocation of unknown/reject case to "Other"/"Unclear" bucket per dimension.
- **No item descriptions were invented.** All descriptions are grounded in slide text.
- **Counts within the general-defect bucket are inferred** (25 cookies vs 2 bottles) from the responsibility totals — see §3a sensitivity envelope. The bounding scenarios show the inference is well-constrained: 包材 is bounded at 0–2; 轻食 at 25–27.
- **Ambiguities are flagged with footnotes**, not silently resolved.
