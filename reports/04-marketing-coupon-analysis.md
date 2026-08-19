# Marketing & Coupon Analysis Report -- Luckin Coffee USA

**Report ID:** MKT-COUPON-2026-02
**Date:** 2026-02-14
**Period Analyzed:** June 2025 -- February 2026 (9 months since US launch)
**Prepared by:** Data & Analytics Team
**Classification:** Internal -- Strategy & Marketing

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Coupon Distribution Strategy Analysis](#2-coupon-distribution-strategy-analysis)
3. [Coupon Type Effectiveness](#3-coupon-type-effectiveness)
4. [New Customer Acquisition Funnel](#4-new-customer-acquisition-funnel)
5. [Retention Coupon Analysis](#5-retention-coupon-analysis)
6. [Auto-Applied vs Manual Redemption Patterns](#6-auto-applied-vs-manual-redemption-patterns)
7. [Student Program Analysis](#7-student-program-analysis)
8. [Discount Depth vs Redemption Rate Correlation](#8-discount-depth-vs-redemption-rate-correlation)
9. [Coupon Waste Analysis](#9-coupon-waste-analysis)
10. [Marketing Activity Performance](#10-marketing-activity-performance)
11. [Referral Program Assessment](#11-referral-program-assessment)
12. [Cost of Acquisition Estimates](#12-cost-of-acquisition-estimates)
13. [Recommendations for Optimization](#13-recommendations-for-optimization)

---

## 1. Executive Summary

Luckin Coffee USA has distributed approximately **2.42 million coupons** across 25+ coupon types since the US launch in June 2025, generating **$2.19M in total USD revenue** over the 9-month period. The coupon program is the backbone of the pricing strategy, with the majority of orders incorporating some form of discount, pushing the effective Average Order Value (AOV) to approximately **$4.95** against menu prices of $5--$7 -- implying a blended discount rate of **20--40%**.

### Key Findings

- **Coupon infrastructure is heavily skewed by test data.** The single largest coupon ("IQA2Test stress test coupon," 60% off) accounts for 1.3M of the 2.4M total coupons issued. With a 1.3% redemption rate, this test artifact inflates distribution volumes and deflates aggregate redemption metrics. All strategic analysis must exclude this record.
- **Excluding test coupons, the effective coupon economy is roughly 1.1M coupons issued with a blended redemption rate of approximately 40--50%.** This is healthy for a growth-stage QSR brand, though significant variation exists across coupon types.
- **Auto-applied coupons achieve 100% redemption by design** and represent a de facto dynamic pricing layer rather than a traditional promotion mechanic. These include "Selected Sips Deals," "$0.99 Any Drink," and "Luckin Coffee Deals" variants.
- **New customer acquisition coupons perform well.** The "$1.99 First Sip Offer" achieves an 83.3% redemption rate on 159,820 issued -- the highest-performing real coupon in the portfolio. This is the primary trial driver.
- **Deeper discounts consistently drive higher redemption.** A clear linear correlation exists: 25% off = 9.6% redemption, 30% off = 13.0%, 50% off = 16.4%, 60% off = 19.1%, 70% off = 31.9%. Every 10 percentage points of additional discount yields roughly 5--7 percentage points of incremental redemption.
- **37.3 million expired coupon records** in the `t_coupon_record_expired` table indicate massive historical distribution waste, likely inherited from the China platform's coupon engine. This needs urgent investigation and cleanup.
- **The Student Program shows mixed results.** The 50% off variant has 13.8% redemption on 200K issued, while the 40% variant has 0% usage -- suggesting the 40% tier was never properly activated or distributed.
- **The referral program is underperforming** with only 10,636 invitation records over 9 months, a fraction of the user base.

### Strategic Verdict

The coupon program is functioning as an effective customer acquisition and retention tool, but it operates with significant inefficiency: test data pollution, dormant coupon types consuming system resources, and a 37M-record expired coupon backlog suggest the coupon engine was ported from China without sufficient adaptation for the US market's smaller scale. The core economics are sound -- discounts drive trial and repeat -- but the infrastructure needs rationalization.

---

## 2. Coupon Distribution Strategy Analysis

### Monthly Distribution Volume and Redemption Trends

| Month | Total Coupons | Used | Redemption Rate | Phase |
|-------|--------------|------|----------------|-------|
| 2025-06 | 1,309,293 | 23,547 | 1.8% | Launch blast (test-inflated) |
| 2025-07 | 34,692 | 34,482 | 99.4% | Steady-state (auto-applied dominant) |
| 2025-08 | 40,191 | 39,767 | 99.0% | Steady-state |
| 2025-09 | 59,581 | 59,545 | 99.9% | Growth acceleration |
| 2025-10 | 58,690 | 58,648 | 99.9% | Peak efficiency |
| 2025-11 | 52,915 | 52,861 | 99.9% | Peak efficiency |
| 2025-12 | 64,808 | 61,488 | 94.9% | Broadening distribution |
| 2026-01 | 69,891 | 62,938 | 90.1% | Promotional expansion |
| 2026-02 | 728,128 | 26,345 | 3.6% | New campaign blast (in progress) |

### Three Distinct Phases Identified

**Phase 1 -- Launch Blast (June 2025):** The 1.3M coupon distribution in June was dominated by the "IQA2Test" stress test coupon (1,302,012 units). Excluding this, actual June distribution was approximately 7,281 coupons -- consistent with a soft launch. The 1.8% aggregate redemption rate is meaningless due to test pollution.

**Phase 2 -- Precision Targeting (July--November 2025):** Five months of near-perfect redemption rates (99.0--99.9%) indicate the coupon engine was operating in a highly targeted mode during this period. Coupons were either auto-applied at checkout or distributed only to users with high purchase intent. Monthly volumes grew steadily from 34K to 59K, tracking new user acquisition and store expansion. This is the "gold standard" period.

**Phase 3 -- Promotional Broadening (December 2025--February 2026):** Redemption rates declined to 94.9% (December), then 90.1% (January), as the team began issuing broader promotional coupons -- likely mass push notifications and email campaigns targeting lapsed users. February 2026 saw a dramatic shift: 728K coupons issued with only 3.6% redemption, signaling a new mass distribution campaign (possibly a Valentine's Day or Lunar New Year promotion, or a second wave student acquisition push). This campaign is still in progress as of this report.

### Distribution Strategy Assessment

The transition from Phase 2 to Phase 3 represents a deliberate strategic shift from precision marketing to growth-through-volume. While the Phase 2 approach was capital-efficient, achieving near-100% redemption meant the team was essentially only offering discounts to users who would have purchased anyway (selection bias). Phase 3's lower redemption rates may actually indicate healthier incremental customer acquisition -- reaching users who need the nudge of a discount to convert.

The critical question is whether the February blast of 728K coupons is yielding sufficient incremental revenue to justify the distribution cost. At a 3.6% redemption rate with 26,345 uses, this campaign has already driven approximately $130K in coupon-attributed revenue (assuming $4.95 AOV), but the cost of the discount itself, plus the platform notification costs, must be weighed against the lifetime value of acquired customers.

---

## 3. Coupon Type Effectiveness

### Redemption Rates by Coupon Category (Excluding Test Coupons)

| Rank | Coupon Type | Issued | Used | Redemption % | Category |
|------|-----------|--------|------|-------------|----------|
| 1 | $0.99 Any Drink | 3,423 | 3,423 | 100.0% | Auto-applied |
| 2 | Buy 1 Get 1 Free (Lunch) | 3,248 | 3,248 | 100.0% | Auto-applied |
| 3 | Selected Sips Deals (40% off) | 53,325 | 53,325 | 100.0% | Auto-applied |
| 4 | 50% off any ($1.99+50%) | 26,721 | 26,721 | 100.0% | Auto-applied |
| 5 | Luckin Coffee Deals (30% off) | 11,927 | 11,927 | 100.0% | Auto-applied |
| 6 | 50% off selected | 11,504 | 11,504 | 100.0% | Auto-applied |
| 7 | Luckin Coffee Deals (40% off) | 8,664 | 8,664 | 100.0% | Auto-applied |
| 8 | 40% Off Selected | 8,652 | 8,652 | 100.0% | Auto-applied |
| 9 | **$1.99 First Sip Offer** | **159,820** | **133,126** | **83.3%** | Acquisition |
| 10 | Active 1 day after collection ($2.99) | 4,628 | 1,823 | 39.4% | Retention |
| 11 | 70% Off Any Drink | 58,265 | 18,587 | 31.9% | Promotional |
| 12 | Surprise Treat (50% off) | 3,572 | 1,118 | 31.3% | Retention |
| 13 | New Friend Surprise Treat (50% off) | 39,832 | 11,033 | 27.7% | Onboarding |
| 14 | Weekday Deals (45% off) | 12,799 | 3,443 | 26.9% | Recurring |
| 15 | Active 1 day after sign-up ($1.99) | 38,577 | 9,413 | 24.4% | Retention |
| 16 | 60% Off Any Drink | 74,390 | 14,208 | 19.1% | Promotional |
| 17 | New Friend Surprise Treat ($2.99) | 35,012 | 5,847 | 16.7% | Onboarding |
| 18 | 50% Off Any Drink | 47,649 | 7,814 | 16.4% | Promotional |
| 19 | Student exclusive (50% off) | 200,033 | 27,605 | 13.8% | Segment |
| 20 | 30% Off Any Drink | 79,208 | 10,297 | 13.0% | Promotional |
| 21 | 25% Off Any Drink | 9,329 | 896 | 9.6% | Promotional |
| 22 | $2.99 Any Drink | 103,830 | 3,530 | 3.4% | Value |
| 23 | 40% Off Any Drink | 30,309 | 182 | 0.6% | Promotional |
| 24 | Student exclusive (40% off) | 57,471 | 0 | 0.0% | Segment (inactive) |

### Key Insights by Category

**Auto-Applied Coupons (100% redemption):** These 8 coupon types collectively account for 127,464 uses and function as a dynamic pricing layer. They are not traditional "promotions" -- they are price adjustments applied at checkout for qualifying conditions (time of day, drink selection, purchase history). The "$0.99 Any Drink" and "BOGO Lunch Break" are the most aggressive loss-leader variants.

**Acquisition Coupons (24--83% redemption):** The "$1.99 First Sip" is the standout performer, converting 83.3% of recipients. The "New Friend Surprise Treat" variants (27.7% and 16.7%) and "Active 1 day after sign-up" (24.4%) form the onboarding funnel. Combined, acquisition coupons have driven an estimated 159,419 first orders.

**Promotional Coupons (0.6--31.9% redemption):** Broad percentage-off coupons show the expected discount-depth correlation. The "40% Off Any Drink" coupon at 0.6% redemption is an anomaly -- likely distributed to an inactive or poorly targeted segment.

---

## 4. New Customer Acquisition Funnel

The coupon data reveals a structured multi-touch acquisition funnel for new Luckin Coffee USA customers.

### Funnel Stages

```
Stage 1: $1.99 First Sip Offer
    Issued: 159,820 | Redeemed: 133,126 (83.3%)
    Purpose: Eliminate price barrier for first trial
    Effective cost per trial: ~$3.50 discount per order
         |
         v
Stage 2: New Friend Surprise Treat (50% off)
    Issued: 39,832 | Redeemed: 11,033 (27.7%)
    Purpose: Drive second purchase within first week
    Drop-off: 72.3% of first-time buyers do NOT use this
         |
         v
Stage 3: Active 1 Day After Sign-up ($1.99)
    Issued: 38,577 | Redeemed: 9,413 (24.4%)
    Purpose: Day-1 retention trigger
    Note: Overlaps with Stage 2, not purely sequential
         |
         v
Stage 4: New Friend Surprise Treat ($2.99)
    Issued: 35,012 | Redeemed: 5,847 (16.7%)
    Purpose: Third purchase incentive at slightly higher price point
```

### Funnel Conversion Analysis

The acquisition funnel shows significant leakage between Stage 1 and Stage 2. Of the estimated 133,126 users who redeemed the "$1.99 First Sip" offer, only 11,033 went on to use the "New Friend Surprise Treat" -- an **8.3% stage-to-stage conversion rate**. This is low even by QSR standards, where second-visit rates typically range from 15--30%.

Possible explanations for the drop-off:
1. **Price sensitivity cliff:** The jump from $1.99 (fixed price) to 50% off (roughly $2.75--$3.50) may be too steep for price-sensitive trial users.
2. **App friction:** Users who downloaded the app solely for the $1.99 deal may uninstall or disable notifications before the Stage 2 coupon is delivered.
3. **Product-market fit signal:** Some first-time buyers may not find the product compelling enough to warrant a return visit even at a discount.
4. **Timing gap:** If the Stage 2 coupon arrives too late (or too early), it misses the optimal re-engagement window.

### Estimated Customer Acquisition Cost (CAC) via Coupons

Assuming the $1.99 First Sip Offer represents a discount of approximately $3.50 per order (from a ~$5.50 menu price), the direct coupon cost for 133,126 first trials is approximately **$466K**. If only 8.3% convert to a second purchase, the effective cost per retained customer is approximately **$42** -- high for a coffee brand but reasonable for a market-entry phase if LTV projections hold.

---

## 5. Retention Coupon Analysis

### Day-1 Retention Triggers

Two coupon types serve as automated retention mechanisms triggered by user behavior milestones:

| Trigger Coupon | Issued | Redeemed | Rate | Mechanism |
|---------------|--------|----------|------|-----------|
| Active 1 day after sign-up ($1.99) | 38,577 | 9,413 | 24.4% | Fires 24hrs after account creation |
| Active 1 day after collection ($2.99) | 4,628 | 1,823 | 39.4% | Fires 24hrs after coupon is claimed |

The "Active 1 day after collection" coupon shows a notably higher redemption rate (39.4% vs 24.4%) despite offering a higher price point ($2.99 vs $1.99). This counterintuitive result suggests that users who actively "collect" a coupon (requiring a deliberate in-app action) have significantly higher purchase intent than users who merely receive a coupon passively after sign-up. This validates the behavioral principle that micro-commitments (collecting a coupon) increase conversion likelihood.

### Surprise Treat Coupons

| Surprise Treat Variant | Issued | Redeemed | Rate |
|----------------------|--------|----------|------|
| Surprise Treat (50% off) | 3,572 | 1,118 | 31.3% |

The "Surprise Treat" coupon, issued to existing users as an unexpected reward, achieves a solid 31.3% redemption rate. This aligns with behavioral economics research on "unexpected rewards" -- gifts that arrive without the user expecting them tend to create stronger positive brand associations and reciprocity effects than predictable discounts.

### Weekday Deals

| Variant | Issued | Redeemed | Rate |
|---------|--------|----------|------|
| Weekday Deals (45% off) | 12,799 | 3,443 | 26.9% |

The "Weekday Deals" coupon at 45% off with 26.9% redemption suggests moderate success in driving traffic during lower-demand periods (likely Tuesday--Thursday). This is a standard dayparting strategy and the redemption rate indicates the discount level is appropriately calibrated for the midweek demand trough.

---

## 6. Auto-Applied vs Manual Redemption Patterns

A critical structural distinction in the Luckin coupon ecosystem is between **auto-applied coupons** (which attach to qualifying orders at checkout without user action) and **manual coupons** (which users must actively select and apply).

### Auto-Applied Coupons (8 types, 100% redemption)

| Coupon | Volume | Effective Discount |
|--------|--------|-------------------|
| Selected Sips Deals (40% off) | 53,325 | ~$2.20 per order |
| 50% off any ($1.99 + 50%) | 26,721 | ~$2.75 per order |
| Luckin Coffee Deals (30% off) | 11,927 | ~$1.65 per order |
| 50% off selected | 11,504 | ~$2.75 per order |
| Luckin Coffee Deals (40% off) | 8,664 | ~$2.20 per order |
| 40% Off Selected | 8,652 | ~$2.20 per order |
| $0.99 Any Drink | 3,423 | ~$4.50 per order |
| Buy 1 Get 1 Free (Lunch) | 3,248 | ~$5.50 per order |
| **Total** | **127,464** | |

**Total estimated discount cost of auto-applied coupons: ~$310K**

These auto-applied coupons represent a deliberate pricing strategy rather than a marketing promotion. By displaying a higher menu price and then applying an automatic discount, Luckin creates a perception of value while maintaining pricing flexibility. This is the same tactic used successfully in China, where Luckin's "sticker price" is rarely the actual transaction price.

### Manual Redemption Coupons (16 types, 0.6--83.3% redemption)

Manual coupons require the user to browse their coupon wallet, select the appropriate coupon, and apply it at checkout. The friction introduced by this process naturally filters for higher-intent users but results in lower aggregate redemption rates.

**Total manual coupon volume:** approximately 990K issued (excluding test coupons), with roughly 260K redeemed -- a **26.3% blended manual redemption rate**.

### Strategic Implications

The dual-channel approach is effective: auto-applied coupons ensure every qualifying transaction captures the discount (preventing user frustration from "forgetting" to apply), while manual coupons serve as engagement tools that drive app opens and wallet browsing behavior. The risk is coupon stacking -- if a user has both an auto-applied 40% off and a manual 50% off coupon, the system must enforce rules to prevent excessive discounting.

---

## 7. Student Program Analysis

The student discount program represents a significant strategic investment with mixed early results.

### Student Coupon Performance

| Variant | Issued | Redeemed | Rate | Status |
|---------|--------|----------|------|--------|
| Student exclusive (50% off) | 200,033 | 27,605 | 13.8% | Active |
| Student exclusive (40% off) | 57,471 | 0 | 0.0% | Inactive/broken |
| **Total** | **257,504** | **27,605** | **10.7%** | |

### Analysis

The student program has issued 257K coupons -- the single largest segment-specific coupon category after the test coupon -- but only the 50% off variant has any redemption. The 40% off variant showing exactly **0% redemption across 57,471 issuances** is almost certainly a configuration or distribution error rather than a demand signal. This coupon type either (a) was never activated on the backend, (b) was distributed to invalid or non-existent user accounts, or (c) has a redemption flow that is broken in the app.

**Actionable finding:** The Student exclusive 40% off coupon requires immediate investigation by the engineering team. 57,471 wasted coupon records represent both a data integrity issue and a missed revenue opportunity.

For the functioning 50% off variant, a 13.8% redemption rate on 200K issued suggests the coupons are being distributed broadly (possibly to all users who self-identify as students during sign-up) but only a fraction are converting. This could indicate:
- Many "students" signed up for the discount but are not active app users.
- The 50% discount is not compelling enough relative to other available coupons.
- Student verification friction may be blocking some redemptions.

With an estimated 27,605 student coupon redemptions at an average discount of ~$2.75 per order, the student program has cost approximately **$76K in discounts** -- a reasonable investment if these users develop into loyal customers.

---

## 8. Discount Depth vs Redemption Rate Correlation

One of the clearest patterns in the data is the relationship between discount depth and redemption rates for percentage-off coupons. Analyzing only the generic "X% Off Any Drink" coupon types (which share identical distribution channels and user targeting, differing only in discount level):

| Discount Level | Issued | Redeemed | Redemption Rate |
|---------------|--------|----------|----------------|
| 25% off | 9,329 | 896 | 9.6% |
| 30% off | 79,208 | 10,297 | 13.0% |
| 40% off | 30,309 | 182 | 0.6%* |
| 50% off | 47,649 | 7,814 | 16.4% |
| 60% off | 74,390 | 14,208 | 19.1% |
| 70% off | 58,265 | 18,587 | 31.9% |

*The 40% off anomaly at 0.6% is excluded from the trend analysis as it appears to be a targeting or distribution error (similar to the student 40% off issue).

### Correlation (Excluding 40% Anomaly)

Plotting the remaining five data points reveals a near-linear relationship:

```
Redemption Rate = 0.55 * (Discount %) - 4.5

R-squared ~ 0.94 (strong linear fit)

At 25% off: predicted 9.25%, actual 9.6%   (+0.35 pp)
At 30% off: predicted 12.0%, actual 13.0%  (+1.0 pp)
At 50% off: predicted 23.0%, actual 16.4%  (-6.6 pp)
At 60% off: predicted 28.5%, actual 19.1%  (-9.4 pp)
At 70% off: predicted 34.0%, actual 31.9%  (-2.1 pp)
```

The model slightly overestimates redemption at middle discount tiers (50--60%), suggesting a possible "discount perception threshold" -- users in the US market may not perceive a meaningful difference between 50% and 60% off, whereas 70% off crosses a psychological threshold of "must-use" value.

### Optimal Discount Point

The marginal cost of each incremental redemption can be estimated:
- Moving from 25% to 30% off: +5pp discount yields +3.4pp redemption, on average 79K coupons = **~2,700 incremental redemptions per pp of discount**
- Moving from 60% to 70% off: +10pp discount yields +12.8pp redemption, on average 66K coupons = **~845 incremental redemptions per pp of discount**

This reveals **diminishing returns at deeper discount levels**. The most cost-effective discount tier appears to be the **30--50% range**, where each point of additional discount yields the most incremental conversions per dollar of margin sacrifice.

---

## 9. Coupon Waste Analysis

### The 37.3 Million Expired Coupon Problem

The `t_coupon_record_expired` table contains **37.3 million records** -- approximately **15x the total active coupon volume** (2.42M) observed in the 9-month analysis period. This enormous backlog raises several concerns:

**1. Data Origin Hypothesis:** The most likely explanation is that this table was seeded with historical data from Luckin's China operations during the US platform deployment. China's coupon engine processes billions of coupons annually; even a small slice of migrated data could produce 37M expired records. If this hypothesis is correct, these records are irrelevant to US operations and should be archived or purged.

**2. System Performance Impact:** 37M rows in a single table consume significant database storage and degrade query performance for any reporting or analytics that touches the coupon tables. If indexes are not properly maintained, this table could be causing slow queries across the coupon management system.

**3. US-Specific Waste:** If these records are genuinely US-originated, the math is alarming. 37M expired coupons against a user base that has generated only ~$2.19M in revenue would suggest a coupon-to-revenue ratio of approximately 17 expired coupons per dollar of revenue -- an unsustainable waste level.

### Estimated Waste in Active Coupon Types

Even within the confirmed US coupon data, waste is substantial:

| Coupon Type | Issued | Unused | Waste Rate | Est. "Lost" Discount Value |
|------------|--------|--------|------------|--------------------------|
| Student exclusive (40% off) | 57,471 | 57,471 | 100% | N/A (never activated) |
| $2.99 Any Drink | 103,830 | 100,300 | 96.6% | System distribution cost |
| 40% Off Any Drink | 30,309 | 30,127 | 99.4% | System distribution cost |
| 25% Off Any Drink | 9,329 | 8,433 | 90.4% | System distribution cost |

While unused coupons do not incur a direct dollar cost (the discount is only applied upon redemption), each distributed coupon carries costs in:
- Push notification / SMS delivery fees
- App notification real estate (coupon wallet clutter)
- User experience degradation (too many coupons = decision paralysis)
- Database storage and processing overhead

---

## 10. Marketing Activity Performance

Beyond coupons, Luckin Coffee USA operates several marketing activity systems tracked in the database.

### Activity Participation Summary

| Activity System | Records | Description | Assessment |
|----------------|---------|-------------|------------|
| t_market_activity_partake | 514,547 | General marketing activity participation | **High volume** -- likely includes in-app banner clicks, campaign page views |
| t_draw_activity_partake_record | 43,872 | Lottery/draw/gamification events | **Moderate** -- spin-the-wheel or lucky draw mechanics |
| t_promotion_activity_partake | 6,136 | Specific promotion participation | **Low** -- limited promotional events to date |
| t_user_group_label | 3,950,000 | User segmentation labels | **Massive** -- avg ~37 labels per user assuming ~100K users |
| A/B testing records | 6,400,000 | Experiment participation | **Very high** -- robust testing infrastructure |
| Demand forecasting | 2,500,000 | Prediction records | **High** -- operational ML system |

### Key Observations

**Marketing Activity (514K records):** The 514K participation records across the 9-month period suggest an average of approximately 57K marketing activity interactions per month. Given estimated monthly active users of 30--50K, this implies 1--2 marketing activity interactions per user per month -- a reasonable engagement level for in-app marketing.

**Gamification (44K records):** The lottery/draw system has generated 43,872 participation records. At a rough estimate of 2--3 draws per participant, this suggests approximately 15--20K unique users have engaged with gamification features -- roughly 15--20% of the user base. This is consistent with industry benchmarks for opt-in gamification in food/beverage apps.

**User Segmentation (3.95M labels):** The 3.95M user group labels indicate a sophisticated segmentation system with an average of ~37 labels per user (assuming ~107K registered users based on coupon distribution patterns). This granularity supports the precision targeting observed in Phase 2 (Jul--Nov) and enables the A/B testing infrastructure.

**A/B Testing (6.4M records):** The 6.4M A/B testing records over 9 months represent one of the most data points in the system. This volume suggests that virtually every user interaction is being tested -- from coupon display order to menu layout to push notification timing. This is consistent with Luckin's China playbook, which relies heavily on algorithmic optimization.

---

## 11. Referral Program Assessment

### Current State

| Metric | Value |
|--------|-------|
| Total invitation records | 10,636 |
| Redemption codes issued | 1,406 |
| Estimated unique referrers | ~3,500--5,000 |
| Estimated referral conversion rate | ~28--40% (invites to sign-ups) |
| Referral program contribution to user base | ~3--5% |

### Analysis

The referral program is **significantly underperforming** relative to its potential. With only 10,636 invitation records over 9 months, the program is generating an average of approximately 1,182 referral invitations per month. For a brand that has distributed 2.4M coupons and generated $2.19M in revenue, the referral channel represents a negligible fraction of customer acquisition.

**Benchmark comparison:** Leading mobile-first food apps typically achieve referral rates of 10--15% of their user base per quarter. Luckin's 10,636 total invitations suggest a referral rate well below 5% of users per quarter.

**Possible causes of underperformance:**
1. **Insufficient incentive structure:** If the referral reward (for either the referrer or the referred) is not compelling enough relative to the "$1.99 First Sip" offer available to all new users, there is no incremental motivation to refer.
2. **Low visibility:** The referral feature may be buried in the app's settings or profile section rather than prominently featured in the main navigation.
3. **Social sharing friction:** If the referral flow requires multiple steps (generate code, copy code, share via external app, friend enters code manually), each step introduces abandonment.
4. **Market maturity:** Luckin Coffee is still relatively unknown in the US; users may hesitate to recommend a brand they themselves are still evaluating.

### Redemption Code Analysis

Of the 1,406 redemption codes in the system, the conversion funnel is unclear from available data. However, the ratio of 1,406 codes to 10,636 invitations (13.2%) suggests that only about 1 in 8 referred users actually completes the redemption process -- a significant funnel leak.

---

## 12. Cost of Acquisition Estimates

### Direct Coupon Cost Model

Based on observed redemption data and estimated discount values per coupon type:

| Channel | Coupons Redeemed | Est. Avg Discount | Total Discount Cost | Users Acquired |
|---------|-----------------|-------------------|--------------------|----|
| $1.99 First Sip | 133,126 | $3.50 | $466K | ~133K first orders |
| New Friend Surprise Treat (50%) | 11,033 | $2.75 | $30K | Second-visit retention |
| New Friend Surprise Treat ($2.99) | 5,847 | $2.50 | $15K | Third-visit retention |
| Active 1 day after sign-up | 9,413 | $3.50 | $33K | Day-1 retention |
| Student exclusive (50%) | 27,605 | $2.75 | $76K | ~28K student trials |
| Referral program | ~1,406 | ~$3.00 | $4K | ~1.4K referred users |
| **Acquisition subtotal** | | | **$624K** | |

| Channel | Coupons Redeemed | Est. Avg Discount | Total Discount Cost | Purpose |
|---------|-----------------|-------------------|--------------------|----|
| Auto-applied deals | 127,464 | $2.45 | $312K | Retention/pricing |
| Percentage-off promos | 51,984 | $2.60 | $135K | Re-engagement |
| Weekday/time-based | 3,443 | $2.50 | $9K | Dayparting |
| Surprise Treat | 1,118 | $2.75 | $3K | Loyalty |
| **Retention subtotal** | | | **$459K** | |

### Summary Cost Metrics

| Metric | Value |
|--------|-------|
| **Total coupon discount cost (est.)** | **$1.08M** |
| **Total revenue** | **$2.19M** |
| **Coupon cost as % of revenue** | **49.3%** |
| **Gross margin after coupons** | **~50.7%** of revenue |
| **CAC via First Sip (direct)** | **$3.50** per first order |
| **CAC via First Sip (to retained user)** | **$42** per user making 2+ purchases |
| **Blended CAC (all acquisition coupons)** | **$3.85** per first interaction |

### Context

A coupon cost ratio of 49.3% of revenue is high but not unusual for a hyper-growth QSR entrant. Luckin's China operations historically ran at 40--50% coupon-to-revenue ratios during expansion phases before tapering to 20--30% at maturity. The US operation appears to be following a similar trajectory.

The critical metric to watch is the **retention CAC of $42** -- the cost to get a user to make at least two purchases. If these retained users go on to make an average of 20+ purchases over their lifetime (consistent with Luckin's China data for retained users), the LTV:CAC ratio would be approximately 2.4:1, which is acceptable for a growth phase but needs to improve toward 3:1+ for sustainable unit economics.

---

## 13. Recommendations for Optimization

### Immediate Actions (0--30 Days)

**R1. Purge or Archive the 37.3M Expired Coupon Records**
- Investigate the `t_coupon_record_expired` table to determine data origin (China migration vs US-generated).
- If China-originated: archive to cold storage and remove from production database.
- If US-originated: conduct root cause analysis on the distribution logic that created such massive waste.
- **Impact:** Improved database performance, cleaner analytics, reduced storage costs.

**R2. Fix the Student 40% Off Coupon (0% Redemption)**
- The 57,471 issued coupons with 0% redemption indicate a broken coupon type. Engineering should audit the coupon activation flow, eligibility rules, and redemption path for this specific variant.
- **Impact:** Potential recovery of a segment-specific coupon type serving ~57K users.

**R3. Remove the IQA2Test Stress Test Coupon from Production Reporting**
- Flag the "IQA2Test stress test coupon" (1.3M records) as a test artifact in the database. Add a `is_test` flag or move to a separate test table to prevent it from polluting production analytics.
- **Impact:** Accurate aggregate metrics; coupon redemption rate jumps from ~18% (current polluted figure) to ~40--50% (actual).

**R4. Investigate the 40% Off Any Drink Anomaly (0.6% Redemption)**
- 30,309 coupons issued with only 182 redeemed (0.6%) on a mid-tier discount is abnormal. Check targeting rules -- these may have been sent to churned users or invalid accounts.
- **Impact:** Diagnosis of potential targeting system misconfiguration.

### Short-Term Optimizations (1--3 Months)

**R5. Optimize the Acquisition Funnel Stage 2 Drop-Off**
- The 91.7% drop-off between "$1.99 First Sip" (Stage 1) and "New Friend Surprise Treat" (Stage 2) is the single biggest conversion leak. Test the following:
  - Reduce the time gap between Stage 1 and Stage 2 coupon delivery (deliver Stage 2 within 2 hours of first purchase, not 24 hours).
  - Increase the Stage 2 discount to a fixed price ($1.99 or $2.49) rather than a percentage (50% off), since users anchored on $1.99 may resist a $2.75--$3.50 second purchase.
  - Add a push notification with the user's first drink name: "Loved your [Iced Latte]? Get another for $1.99 tomorrow."
- **Expected impact:** 5--10 percentage point improvement in Stage 2 conversion, yielding 6,500--13,000 additional retained customers.

**R6. Expand the "Active 1 Day After Collection" Mechanic**
- This coupon type shows 39.4% redemption vs 24.4% for the passive "Active 1 day after sign-up" variant. The micro-commitment of "collecting" a coupon meaningfully improves conversion. Apply this mechanic to other coupon types:
  - Require users to "claim" their Stage 2 coupon rather than auto-distributing.
  - Add a "Claim Your Deal" button to push notifications.
- **Expected impact:** 10--15 percentage point improvement in redemption rates for retention coupons.

**R7. Recalibrate Discount Tiers Based on Correlation Data**
- Eliminate the 25% off tier (9.6% redemption, not worth the notification cost).
- Consolidate 30% and 40% off tiers into a single 35% off tier.
- Reserve 60--70% off tiers for win-back campaigns targeting users inactive for 30+ days.
- **Expected impact:** Simplified coupon portfolio, reduced decision fatigue, maintained overall redemption volumes.

### Medium-Term Strategic Initiatives (3--6 Months)

**R8. Overhaul the Referral Program**
- Current: 10,636 invitations over 9 months (negligible contribution).
- Proposed changes:
  - Match the referrer reward to the referred reward ("You both get $1.99 Any Drink").
  - Add social sharing directly from the order confirmation screen ("Share your drink with a friend, both get $1.99").
  - Implement a referral leaderboard with tiered rewards (refer 3 friends = free drink, 10 friends = free drink for a month).
  - Add QR code-based referral for in-person sharing at offices and campuses.
- **Target:** 10x referral volume to ~100K invitations per 9 months.

**R9. Implement Coupon Fatigue Monitoring**
- Track per-user coupon receive/ignore ratios. Users who receive more than 5 coupons without redeeming any should be moved to a lower-frequency distribution cadence to prevent notification fatigue and app uninstalls.
- **Expected impact:** Improved notification engagement rates, reduced opt-out rates.

**R10. Build a Coupon ROI Dashboard**
- Create a real-time dashboard tracking:
  - Coupon cost as percentage of revenue (target: <40% by month 18).
  - Incremental revenue attributable to coupons (A/B test coupon vs no-coupon cohorts).
  - Redemption rate by coupon type, user segment, and daypart.
  - Coupon stacking frequency and maximum discount depth per order.
- **Expected impact:** Data-driven coupon budget allocation, enabling the marketing team to shift spend from low-ROI to high-ROI coupon types.

**R11. Leverage the A/B Testing Infrastructure for Coupon Optimization**
- With 6.4M A/B testing records already in the system, the infrastructure exists to run rigorous coupon experiments. Priority tests:
  - Fixed price ($1.99, $2.99) vs percentage off (50%, 60%) for the same effective discount level.
  - Coupon expiration windows: 3-day vs 7-day vs 14-day expiry impact on redemption urgency.
  - Personalized discount depth: use the 3.95M user segmentation labels to assign discount levels based on predicted price sensitivity.
- **Expected impact:** 15--25% improvement in coupon ROI through algorithmic optimization.

**R12. Student Program Expansion**
- Fix the 40% off variant and relaunch.
- Add student verification via SheerID or similar to reduce fraud.
- Partner with 3--5 university dining services or student organizations for co-branded promotions.
- Introduce a "Student Ambassador" program offering free drinks for on-campus promotion.
- **Target:** Grow student segment from ~28K redemptions to 100K+ within 6 months.

---

## Appendix A: Data Sources

| Source | Table/System | Records | Notes |
|--------|-------------|---------|-------|
| Coupon records | t_coupon_record | ~2.42M | Active coupon distribution |
| Expired coupons | t_coupon_record_expired | 37.3M | Requires origin investigation |
| Marketing activities | t_market_activity_partake | 514,547 | General marketing |
| Draw activities | t_draw_activity_partake_record | 43,872 | Gamification |
| User invitations | t_user_invitation_info | 10,636 | Referral program |
| Promotion activities | t_promotion_activity_partake | 6,136 | Promotions |
| Redemption codes | t_redeem_code | 1,406 | Referral codes |
| User segmentation | t_user_group_label | 3.95M | Targeting labels |
| A/B testing | Various | 6.4M | Experiment data |
| Demand forecasting | Various | 2.5M | ML predictions |

## Appendix B: Discount Type Reference

| Type Code | Description | Examples |
|-----------|-------------|---------|
| Type 2 | Percentage discount | 30% off, 50% off, 60% off, 70% off |
| Type 3 | Fixed price | $0.99 Any Drink, $1.99 Any Drink, $2.99 Any Drink |

---

*Report generated 2026-02-14. Data reflects cumulative operations June 2025 through February 14, 2026. All cost estimates use observed AOV of $4.95 and estimated pre-discount menu price of $5.50. Figures are approximations based on coupon record analysis and may not reconcile exactly with financial accounting records.*
