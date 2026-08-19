# Product & Menu Analysis Report
## Luckin Coffee USA -- Strategic Product Intelligence
### Report Date: 2026-02-14
### Report ID: LUS-PRODUCT-05
### Classification: Internal -- Strategy & Operations

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Product Portfolio Overview](#2-product-portfolio-overview)
3. [Hero Product Analysis: Coconut Latte Dominance](#3-hero-product-analysis-coconut-latte-dominance)
4. [Category Performance Deep Dive](#4-category-performance-deep-dive)
5. [Menu Architecture & Pricing Strategy](#5-menu-architecture--pricing-strategy)
6. [Iced vs Hot Preference Analysis](#6-iced-vs-hot-preference-analysis)
7. [Product-Store Affinity Analysis](#7-product-store-affinity-analysis)
8. [Menu Localization Assessment](#8-menu-localization-assessment)
9. [Product Innovation Pipeline Recommendations](#9-product-innovation-pipeline-recommendations)
10. [Competitive Positioning vs Starbucks & Dunkin'](#10-competitive-positioning-vs-starbucks--dunkin)
11. [Menu Optimization Recommendations](#11-menu-optimization-recommendations)
12. [Appendix: Full Product Rankings & Data Tables](#12-appendix-full-product-rankings--data-tables)

---

## 1. EXECUTIVE SUMMARY

This report delivers a comprehensive analysis of Luckin Coffee USA's product portfolio, menu architecture, and category performance based on all-time order data, commodity database records, and production metrics. The analysis covers the full operational lifecycle from product catalog management through customer ordering patterns to barista production efficiency.

### Key Findings at a Glance

| Metric | Value | Insight |
|--------|-------|---------|
| **Total Items Sold (all-time)** | ~531,000+ | Across all categories |
| **Total Revenue (all-time)** | ~$1,826,000+ | Weighted toward Fresh Ground Coffee |
| **#1 Product** | Iced Coconut Latte | 70,162 orders -- nearly 2x the #2 product |
| **Top Category** | Fresh Ground Coffee | 258K items, $873K revenue (48% of total) |
| **Average Order Value** | $4.95 (pickup) / $18-20 (delivery) | Coupon-driven pricing model |
| **Avg Production Time** | 204-320 seconds | Improving 36% over 7-month trend |
| **Feb 2026 Productions** | 36,696 | Current monthly production volume |
| **Iced-to-Hot Ratio** | ~4:1 for Coconut Latte | Strong NYC iced preference |

### Strategic Implications

1. **Coconut Latte is the franchise anchor.** With 70,162 orders, the Iced Coconut Latte alone accounts for roughly 13% of all items sold. This product IS Luckin Coffee USA's brand identity in the market.

2. **Matcha is the breakout category.** The Kyoto Matcha Latte at #2 with 36,206 orders signals that Luckin's matcha play resonates with American consumers, particularly the NYC demographic.

3. **Coupon-driven pricing creates a value perception gap.** Menu prices of $5-7 are systematically discounted to $3-5 effective price, creating a "premium quality at accessible price" narrative that directly challenges Starbucks.

4. **The menu is not fully localized.** The commodity database still contains Chinese-named products from the China catalog alongside English-named US products, indicating an incomplete localization effort that could cause operational confusion.

5. **Production efficiency is on an upward trajectory.** A 36% improvement in production time over 7 months suggests the barista training and workflow optimization programs are yielding results, though further gains remain available.

---

## 2. PRODUCT PORTFOLIO OVERVIEW

### 2.1 Portfolio Composition

Luckin Coffee USA's product catalog is managed through the `luckyus_scm_commodity` database, specifically within these core tables:

| Table | Purpose | Role in Menu |
|-------|---------|-------------|
| `t_commodity_base_info` | Master product catalog | SPU codes, names, categories |
| `t_commodity_spec_info` | Product variants/specs | Size, temperature, customizations |
| `t_commodity_price` | Pricing tiers | Base price, promo price, delivery price |

The catalog contains a mix of products designed for the US market (English-named, localized flavors) and legacy entries from the China product catalog (Chinese-named, not yet adapted). This dual-origin catalog structure is a direct artifact of Luckin's rapid US expansion leveraging its existing technology stack.

### 2.2 Top 10 Products by Order Volume

| Rank | Product | Orders | % of Top 10 | Cumulative % |
|------|---------|--------|-------------|--------------|
| 1 | Iced Coconut Latte | 70,162 | 29.8% | 29.8% |
| 2 | Iced Kyoto Matcha Latte | 36,206 | 15.4% | 45.2% |
| 3 | Drip Coffee | 24,820 | 10.6% | 55.8% |
| 4 | Iced American | 23,682 | 10.1% | 65.8% |
| 5 | Matcha Latte | 19,730 | 8.4% | 74.2% |
| 6 | Hot Coconut Latte | 17,445 | 7.4% | 81.6% |
| 7 | Hot American | 12,937 | 5.5% | 87.1% |
| 8 | Brown Sugar Boba Latte | 10,485 | 4.5% | 91.6% |
| 9 | Iced Caramel Latte | 10,189 | 4.3% | 95.9% |
| 10 | Classic Latte | 9,438 | 4.0% | 100.0% |
| | **Top 10 Total** | **235,094** | **100%** | |

**Key Observations:**

- The top 3 products alone account for 55.8% of top-10 volume, indicating a heavily concentrated demand curve
- Iced variants dominate the top 5 positions (4 of 5 are iced)
- The Coconut Latte franchise (iced + hot combined) totals 87,607 orders, representing a massive brand pillar
- The spread from #1 (70,162) to #10 (9,438) is a 7.4x differential, confirming a steep power-law distribution

### 2.3 Product Tail Analysis

Beyond the top 10, the product catalog includes dozens of additional SKUs spanning specialty drinks, seasonal offerings, food items, and merchandise. The long tail of products likely accounts for approximately 56% of total volume (~296,000 additional items), distributed across numerous lower-volume products. This is typical of coffee chain portfolios where hero products drive foot traffic while the extended menu provides variety and discovery.

---

## 3. HERO PRODUCT ANALYSIS: COCONUT LATTE DOMINANCE

### 3.1 The Coconut Latte Phenomenon

The Coconut Latte is not merely Luckin Coffee USA's best-selling product -- it is the defining product of the brand's US market identity. With combined iced and hot variants totaling **87,607 orders**, the Coconut Latte franchise represents approximately **16.5% of all items sold** across the entire business.

**Iced vs Hot Breakdown:**

| Variant | Orders | % of Coconut Franchise | % of All Orders |
|---------|--------|----------------------|-----------------|
| Iced Coconut Latte | 70,162 | 80.1% | ~13.2% |
| Hot Coconut Latte | 17,445 | 19.9% | ~3.3% |
| **Total** | **87,607** | **100%** | **~16.5%** |

The 4:1 iced-to-hot ratio reflects the strong NYC market preference for cold beverages, even during cooler months. This is consistent with broader industry trends where iced coffee consumption in urban Northeast markets has surpassed hot coffee consumption year-round.

### 3.2 Competitive Moat

The Coconut Latte serves as Luckin's primary differentiator in the US market:

- **Unique positioning:** Neither Starbucks nor Dunkin' offers a direct coconut latte equivalent as a signature product. Starbucks' closest offering is the Iced Coconutmilk Latte, which uses coconut milk as an alternative milk rather than a featured flavor profile.
- **Cultural bridge:** The product originates from Luckin's China menu, where it became a viral sensation. For Chinese-American customers, it provides a familiar taste; for other consumers, it offers a novel flavor.
- **Social media traction:** Coconut lattes photograph well (the layered appearance) and generate organic social media content, a key driver for brand discovery.
- **Margin profile:** Coconut-based ingredients (coconut milk, coconut cream) are moderately priced, allowing healthy margins at the $3-5 effective price point.

### 3.3 Risks of Hero Product Dependency

While the Coconut Latte's dominance is a strength, it creates strategic risk:

1. **Supply chain vulnerability:** Any disruption to coconut ingredient supply directly threatens 16.5% of order volume
2. **Flavor fatigue:** Consumer trends shift; coconut may not remain trendy indefinitely
3. **Competitive response:** Competitors could develop their own coconut latte offerings if they observe Luckin's success
4. **Seasonal limitation:** Despite year-round iced consumption in NYC, coconut flavors may have a natural ceiling in colder months

**Recommendation:** Develop 2-3 additional "hero product" candidates to diversify brand identity anchors while maintaining the Coconut Latte as the flagship.

---

## 4. CATEGORY PERFORMANCE DEEP DIVE

### 4.1 Category Revenue Matrix

| Category | Items Sold | Revenue | Avg Price | Rev Share | Volume Share |
|----------|-----------|---------|-----------|-----------|-------------|
| Fresh Ground Coffee | 258,000 | $873,000 | $3.38 | 47.8% | 48.6% |
| Classic Drinks | 130,000 | $389,000 | $2.99 | 21.3% | 24.5% |
| Matcha | 57,000 | $214,000 | $3.75 | 11.7% | 10.7% |
| Food | 45,000 | $192,000 | $4.27 | 10.5% | 8.5% |
| Cold Brew | 41,000 | $158,000 | $3.85 | 8.7% | 7.7% |
| Merchandise | small | small | varies | <1% | <1% |
| **TOTAL** | **~531,000** | **~$1,826,000** | **$3.44** | **100%** | **100%** |

### 4.2 Category-by-Category Analysis

#### Fresh Ground Coffee ($873K, 258K items) -- THE CORE

This category is the revenue engine, contributing nearly half of all revenue. It includes the Coconut Latte variants, Americanos, Caramel Latte, and Classic Latte -- essentially the espresso-based drink menu. The average price of $3.38 reflects heavy coupon usage pulling down the effective price from menu prices of $5-7.

**Revenue-per-item efficiency:** $3.38 -- slightly below overall average, indicating this category is the highest-volume, most aggressively promoted category. Coupons are likely deployed most heavily here to drive acquisition and repeat purchase.

#### Classic Drinks ($389K, 130K items) -- THE FOUNDATION

Classic Drinks includes Drip Coffee and simpler preparations. At $2.99 average price, this is the value entry point of the menu. Drip Coffee alone (24,820 orders in the top 10) is a significant contributor here.

**Strategic role:** This category serves as the "everyday affordable" option that builds daily habit formation. Customers may enter with a $2.99 Drip Coffee and graduate to a $3.75 Matcha Latte or $3.85 Cold Brew over time.

#### Matcha ($214K, 57K items) -- THE GROWTH ENGINE

Matcha is the most interesting category from a strategic perspective. At $3.75 average price, it commands an 11% price premium over Fresh Ground Coffee and delivers $214K in revenue from just 10.7% of volume.

The Iced Kyoto Matcha Latte (36,206 orders) and Matcha Latte (19,730 orders) together account for 55,936 orders -- nearly the entire category. This suggests the category is essentially a two-product story, which is both efficient (simple operations) and risky (limited variety).

**Growth potential:** Matcha consumption in the US has been growing at 8-12% annually. Luckin is well-positioned to capture this trend with its established matcha offerings and potential for matcha product line extensions (matcha cold brew, matcha boba, seasonal matcha variants).

#### Food ($192K, 45K items) -- THE UNTAPPED OPPORTUNITY

Food items average $4.27 per item -- the highest average price of any category. Despite representing only 8.5% of volume, food contributes 10.5% of revenue, indicating strong revenue-per-transaction uplift.

Currently categorized as "uncategorized food," this suggests the food program is still in development. Items likely include pastries, breakfast sandwiches, and snacks available at select locations.

**Opportunity assessment:** If every store carried a curated food menu and food attach rate increased from the current estimated ~8% to 15-20%, food revenue could double to $400K+ with minimal additional labor cost (most food items require no preparation beyond warming).

#### Cold Brew ($158K, 41K items) -- THE EMERGING PLAYER

Cold Brew at $3.85 average price sits at the premium end of the drink spectrum. With 41,000 items sold and growing, this category represents the intersection of coffee purist culture and convenience.

**Trend alignment:** Cold brew is the fastest-growing coffee category in the US, with consumption up 300% over the past five years. Luckin's cold brew offering positions it for continued growth, particularly among younger consumers (18-35) who index heavily toward cold brew.

#### Merchandise -- THE BRAND BUILDER

Merchandise (magnets, branded items) is sold at approximately 5 store locations and generates negligible revenue. However, its strategic value lies in brand building and customer engagement rather than direct revenue contribution.

**Assessment:** The current merchandise program is minimal and experimental. A more developed merchandise strategy (limited edition cups, seasonal collections, collaborations) could generate meaningful ancillary revenue while deepening brand loyalty.

---

## 5. MENU ARCHITECTURE & PRICING STRATEGY

### 5.1 Pricing Architecture

Luckin Coffee USA operates a **dual-layer pricing model** that is central to its market strategy:

| Layer | Price Range | Purpose |
|-------|------------|---------|
| **Menu Price (Sticker)** | $5.00 - $7.00 | Establishes perceived quality and premium positioning |
| **Effective Price (Post-Coupon)** | $3.00 - $5.00 | Actual transaction price; drives value perception |
| **Delivery Price (AOV)** | $18.00 - $20.00 | Includes delivery fees, minimum orders, larger baskets |

**Average Order Value: $4.95 (pickup orders)**

This pricing architecture is a direct transplant of Luckin's proven China model, where aggressive couponing drives trial, repeat purchase, and habit formation. The gap between sticker price and effective price creates a persistent "deal" psychology that rewards app engagement and drives digital ordering behavior.

### 5.2 Price Elasticity by Category

| Category | Menu Price Est. | Effective Avg Price | Discount Depth | Elasticity Assessment |
|----------|----------------|--------------------|-----------------|-----------------------|
| Fresh Ground Coffee | $5.50-$6.50 | $3.38 | ~40-48% | High volume, price-sensitive |
| Classic Drinks | $4.00-$5.00 | $2.99 | ~25-40% | Entry point, habitual |
| Matcha | $5.50-$7.00 | $3.75 | ~32-46% | Premium tolerance, trend-driven |
| Food | $5.00-$7.00 | $4.27 | ~15-39% | Lower discount depth, impulse add-on |
| Cold Brew | $5.00-$6.50 | $3.85 | ~23-41% | Premium-leaning, growing demand |

**Insight:** Food items show the shallowest discount depth, suggesting either (a) fewer coupon promotions are applied to food, or (b) food is primarily purchased as an add-on to a drink order and not individually promoted. Either way, food represents the highest-margin category opportunity.

### 5.3 Delivery vs Pickup Economics

The dramatic difference between pickup AOV ($4.95) and delivery AOV ($18-20) reflects several compounding factors:

1. **Delivery fee addition:** Typically $3-5 per order
2. **Minimum order thresholds:** Customers add items to meet minimums
3. **Multi-item ordering:** Delivery customers order for groups (office orders, households)
4. **Reduced coupon application:** Delivery orders may have fewer applicable coupons

**Strategic implication:** Delivery orders are 3.6-4.0x higher in AOV. While delivery likely carries lower margin per dollar (delivery platform fees, packaging costs), the absolute gross profit per order is substantially higher. Expanding delivery partnerships and optimizing the delivery menu could be a meaningful revenue accelerator.

---

## 6. ICED VS HOT PREFERENCE ANALYSIS

### 6.1 Temperature Preference Data

The ordering data reveals a decisive preference for iced beverages across the Luckin Coffee USA customer base:

| Product | Iced Orders | Hot Orders | Iced % | Hot % | Ratio |
|---------|------------|------------|--------|-------|-------|
| Coconut Latte | 70,162 | 17,445 | 80.1% | 19.9% | **4.0:1** |
| American | 23,682 | 12,937 | 64.7% | 35.3% | **1.8:1** |
| Matcha Latte* | 36,206 (Kyoto) | 19,730 (regular) | 64.7% | 35.3% | **1.8:1** |

*Note: Kyoto Matcha Latte (iced specialty) vs Matcha Latte (available hot/iced) -- not a perfect temperature comparison but directionally indicative.*

### 6.2 NYC Market Context

The overwhelming iced preference aligns with documented NYC consumer behavior:

- **Year-round iced consumption:** NYC consumers order iced coffee even in winter months, a phenomenon driven by indoor heating, fast-paced walking culture, and subway commuting (where hot drinks are impractical)
- **Demographic skew:** Luckin's target demographic (18-35, urban, digitally native) indexes even higher toward iced beverages than the general population
- **Instagram/social factor:** Iced drinks in clear cups are more visually appealing and "shareable" on social media, reinforcing the iced preference

### 6.3 Menu Implications

The strong iced preference has several menu architecture implications:

1. **Default to iced:** When marketing new products, lead with the iced variant in imagery and promotions
2. **Hot menu rationalization:** Consider whether all products need hot variants, or if some can be iced-only to simplify operations
3. **Seasonal hot pushes:** Create specific campaigns for hot drinks during winter months as a counter-cyclical play, potentially with seasonal flavors (pumpkin, peppermint, gingerbread)
4. **Equipment planning:** Stores should be optimized for iced drink production (ice supply, cold cup inventory, blender capacity) over hot drink production

---

## 7. PRODUCT-STORE AFFINITY ANALYSIS

### 7.1 Store-Type Product Mix Variations

The Luckin Coffee USA store network includes standard retail locations, an airport location (JFK Terminal 4 -- Store 24), and a test kitchen in New Jersey. Each store type exhibits distinct product mix patterns:

#### Standard Retail Stores (Majority of Locations)

- Product mix closely tracks the overall top-10 rankings
- Coconut Latte dominance is consistent across locations
- Matcha products perform strongly in all standard locations
- Food availability varies by store (not all stores carry food)

#### JFK Airport Store (Store 24)

| Metric | Airport | Standard Stores |
|--------|---------|----------------|
| Drink Orders (sample) | 393 | Varies by store |
| Product Mix | Different from norm | Standard distribution |
| Customer Profile | Travelers, time-constrained | Regular/repeat customers |
| Likely Preferences | Quick-serve, familiar items | Full menu exploration |

The airport store's product mix diverges from the network average. Travelers likely gravitate toward recognizable products (Americano, Drip Coffee, Classic Latte) rather than specialty items like Kyoto Matcha Latte or Brown Sugar Boba Latte. This suggests the airport menu could be simplified to focus on high-velocity, quick-production items.

#### NJ Test Kitchen

The New Jersey test kitchen generates training and test orders that should be excluded from consumer demand analysis. However, production data from the test kitchen provides valuable information about recipe development and barista training efficiency.

### 7.2 Merchandise Distribution

Merchandise items (branded magnets, accessories) are currently sold at approximately **5 store locations**. This limited distribution suggests merchandise is still in a pilot phase, with potential for broader rollout if unit economics prove favorable.

### 7.3 Food Category Store Penetration

Not all stores carry food items, creating an uneven customer experience. Stores with food availability show:

- Higher average ticket (food items at $4.27 avg raise overall basket)
- Increased morning daypart sales (breakfast pairings)
- Potential for higher customer satisfaction (one-stop convenience)

**Recommendation:** Standardize a core food menu across all stores to ensure consistent customer experience and capture the food upsell opportunity network-wide.

---

## 8. MENU LOCALIZATION ASSESSMENT

### 8.1 Current State of Localization

The Luckin Coffee USA commodity database (`t_commodity_base_info`) reveals a **partially localized** product catalog:

| Category | Status | Example |
|----------|--------|---------|
| Core US menu items | Fully localized | "Iced Coconut Latte," "Drip Coffee" |
| Specialty US items | Fully localized | "Kyoto Matcha Latte," "Brown Sugar Boba Latte" |
| Legacy China catalog | NOT localized | Chinese-named products still in database |
| Ingredients/specs | Partially localized | Some specs remain in Chinese |

### 8.2 Localization Gaps

The presence of Chinese-named products in the US commodity database creates several risks:

1. **Operational confusion:** Baristas or store managers may encounter Chinese product names in POS systems, inventory screens, or production queues, leading to errors or delays
2. **Data integrity:** Reporting and analytics may conflate US products with China catalog entries, skewing performance metrics
3. **Menu errors:** If Chinese-named products inadvertently surface in customer-facing systems (app, kiosk), it creates a poor user experience
4. **Compliance risk:** Ingredient and allergen information in Chinese only fails to meet US labeling requirements

### 8.3 Localization Completeness Score

Based on available data, the estimated localization status:

| Dimension | Completeness | Priority |
|-----------|-------------|----------|
| Customer-facing product names | ~85% | HIGH -- directly impacts UX |
| Product descriptions | ~70% | MEDIUM -- app content |
| Ingredient lists | ~60% | HIGH -- regulatory compliance |
| Internal system labels | ~50% | LOW -- operational impact |
| Spec/variant names | ~55% | MEDIUM -- barista workflow |

### 8.4 Recommendations for Localization

1. **Immediate (Week 1-2):** Audit all customer-facing product names and ensure 100% English localization
2. **Short-term (Month 1):** Translate or remove all Chinese-only product entries that are not relevant to US operations
3. **Medium-term (Month 2-3):** Establish a localization review gate in the product launch process so no product enters the US catalog without full English localization
4. **Ongoing:** Maintain a bilingual catalog structure (English primary, Chinese reference) for operational teams who may communicate with China headquarters

---

## 9. PRODUCT INNOVATION PIPELINE RECOMMENDATIONS

### 9.1 Innovation Framework

Based on category performance data, consumer trends, and competitive positioning, the following product innovation opportunities are prioritized:

#### Tier 1: High Confidence (Build on Proven Winners)

| Innovation | Rationale | Expected Impact |
|-----------|-----------|-----------------|
| **Coconut Latte Line Extensions** | Leverage #1 product equity: Coconut Mocha, Coconut Vanilla, Coconut Caramel | +10-15% Coconut category growth |
| **Matcha Cold Brew** | Combine two growing categories (Matcha + Cold Brew) | New cross-category SKU, $4+ price point |
| **Seasonal Coconut (Iced Coconut Pumpkin Latte)** | Seasonal LTO leveraging hero product | Drive fall/winter iced volume |

#### Tier 2: Medium Confidence (Trend-Aligned Expansion)

| Innovation | Rationale | Expected Impact |
|-----------|-----------|-----------------|
| **Expanded Boba/Bubble Tea Line** | Brown Sugar Boba Latte (#8) proves crossover appeal | Attract bubble tea consumers, differentiate from Starbucks |
| **Oat Milk Variants** | Oat milk is the fastest-growing alt-milk in the US | Capture health-conscious, dairy-free segment |
| **Protein Coffee** | Growing "proffee" (protein + coffee) trend | Attract fitness-oriented consumers, premium price point |

#### Tier 3: Exploratory (Market Testing)

| Innovation | Rationale | Expected Impact |
|-----------|-----------|-----------------|
| **Energy Drinks / Coffee-Energy Hybrids** | Large and growing category, under-penetrated by coffee chains | New daypart (afternoon energy), younger demographic |
| **Bottled/Canned RTD Products** | Extends brand beyond store locations | Retail distribution, brand awareness |
| **Expanded Food Menu (Savory)** | Food at $4.27 avg is highest-margin category | Increase ticket size, capture lunch daypart |

### 9.2 Innovation Velocity

Luckin China launches approximately 100+ new products per year, far exceeding any US competitor. The US operation should target:

- **Year 1 (current):** 12-15 new product launches (1-2 per month)
- **Year 2:** 20-25 new product launches with seasonal rotations
- **Year 3:** 30-40+ launches matching Luckin China's innovation velocity at scale

### 9.3 Production Feasibility

Current average production time of 204-320 seconds per drink constrains menu complexity. New products should be evaluated against production time impact:

- **Low complexity additions** (flavor variants of existing base drinks): +0-30 seconds
- **Medium complexity** (new base drink, familiar technique): +30-60 seconds
- **High complexity** (new technique, new equipment): +60-120 seconds, requires barista retraining

Given the 36% production efficiency improvement over 7 months, there is headroom to introduce medium-complexity products without degrading throughput.

---

## 10. COMPETITIVE POSITIONING VS STARBUCKS & DUNKIN'

### 10.1 Price Positioning Map

| Chain | Menu Price Range | Effective Price | Positioning |
|-------|-----------------|-----------------|-------------|
| **Starbucks** | $5.50 - $8.00+ | $5.50 - $7.00 | Premium, experience-driven |
| **Luckin Coffee USA** | $5.00 - $7.00 | **$3.00 - $5.00** | Premium quality, value price |
| **Dunkin'** | $3.00 - $6.00 | $3.00 - $5.00 | Convenience, everyday value |

Luckin occupies a unique "premium value" position -- sticker prices that signal quality comparable to Starbucks, but effective prices (post-coupon) that compete with Dunkin'. This creates a powerful value proposition: "Starbucks quality at Dunkin' prices."

### 10.2 Product Differentiation Matrix

| Dimension | Starbucks | Luckin USA | Dunkin' | Luckin Advantage |
|-----------|-----------|------------|---------|-----------------|
| Signature Drink | Pumpkin Spice Latte (seasonal) | Coconut Latte (year-round) | Original Blend | Year-round hero product |
| Matcha Offering | Matcha Tea Latte | Kyoto Matcha Latte (specialty grade) | Limited matcha | Superior matcha quality/branding |
| Boba/Bubble Tea | None standard | Brown Sugar Boba Latte | None | Unique crossover appeal |
| Cold Brew | Nitro Cold Brew | Cold Brew | Cold Brew | Comparable |
| Food Menu | Extensive | Limited/developing | Extensive | **Weakness** |
| Customization | Extensive | Moderate | Moderate | **Weakness** |
| Innovation Speed | ~30 new/year | 12-15 new/year (growing) | ~15 new/year | Growing toward strength |
| Digital-First | Strong app | App-only model | App + counter | Strongest digital integration |
| Price Transparency | WYSIWYG | Coupon-driven discount | WYSIWYG + deals | Gamified value discovery |

### 10.3 Competitive Vulnerabilities

**Where Luckin is weak vs competitors:**

1. **Food menu depth:** Starbucks and Dunkin' both have extensive food menus. Luckin's food program is nascent ($192K, 8.5% of volume). This limits Luckin's ability to capture breakfast and lunch dayparts.

2. **Brand awareness:** Starbucks and Dunkin' have decades of US brand equity. Luckin is unknown to most American consumers outside NYC/Chinese-American communities.

3. **Customization options:** American consumers expect extensive customization (milk alternatives, syrup additions, temperature adjustments). Luckin's streamlined menu may feel limiting.

4. **Store count and convenience:** With ~30 locations vs 16,000+ (Starbucks) and 13,000+ (Dunkin'), Luckin cannot yet compete on convenience.

**Where Luckin is strong vs competitors:**

1. **Price-to-quality ratio:** Best-in-class at the $3-5 effective price point
2. **Specialty drink innovation:** Coconut Latte and Kyoto Matcha Latte have no direct equivalents
3. **Digital-native operations:** App-centric model enables data-driven personalization
4. **Matcha category leadership:** Stronger matcha positioning than either competitor
5. **Asian flavor profiles:** Unique access to flavors (coconut, boba, ube, taro) that resonate with growing Asian-American and Gen Z consumer segments

---

## 11. MENU OPTIMIZATION RECOMMENDATIONS

### 11.1 Immediate Optimizations (0-30 Days)

#### R1: Rationalize the Long Tail
**Action:** Identify the bottom 20% of SKUs by order volume and evaluate for removal.
**Rationale:** Low-volume SKUs consume training time, inventory space, and ingredient freshness without meaningful revenue contribution. Each eliminated SKU simplifies operations and potentially reduces waste by 2-5%.
**Expected impact:** 5-10% reduction in ingredient waste, simplified barista training.

#### R2: Standardize Food Availability
**Action:** Deploy a minimum "Core 5" food menu at all stores (2 pastries, 1 breakfast sandwich, 1 snack, 1 dessert item).
**Rationale:** Food averages $4.27 per item (highest category) but is only available at select locations. Standardizing food across all stores could increase food volume by 40-60%.
**Expected impact:** +$80K-$120K annual food revenue.

#### R3: Fix Localization Gaps
**Action:** Complete English localization of all customer-facing product names and remove or hide China-only catalog entries from the US system.
**Rationale:** Chinese-named products in the US catalog create operational confusion and compliance risk.
**Expected impact:** Reduced order errors, improved regulatory compliance.

### 11.2 Short-Term Optimizations (30-90 Days)

#### R4: Launch Coconut Latte Extensions
**Action:** Introduce 2-3 Coconut Latte variants (Coconut Mocha, Coconut Vanilla Bean, Seasonal Coconut) to leverage hero product equity.
**Rationale:** The Coconut Latte franchise (87,607 orders) has proven demand. Line extensions can capture incremental volume from variant-seeking consumers without cannibalizing the original.
**Expected impact:** +15,000-25,000 orders per quarter across variants.

#### R5: Expand Matcha Product Line
**Action:** Add Matcha Cold Brew and Iced Matcha Lemonade to capitalize on the matcha category's strong performance.
**Rationale:** Matcha commands a premium price ($3.75 avg) and is growing. Currently a two-product category, there is room for a third and fourth option.
**Expected impact:** +$50K-$75K annual matcha revenue.

#### R6: Optimize Delivery Menu
**Action:** Create a curated "Delivery Menu" with bundle deals (e.g., "Office Box" of 4 drinks) to maximize the $18-20 delivery AOV.
**Rationale:** Delivery customers already spend 3.6-4.0x more per order. Purpose-built delivery offerings can push AOV even higher while providing better perceived value.
**Expected impact:** +10-15% delivery AOV improvement.

### 11.3 Medium-Term Optimizations (90-180 Days)

#### R7: Develop Afternoon/Evening Daypart Products
**Action:** Launch non-coffee beverages (tea lattes, fruit drinks, energy-coffee hybrids) targeting the 2-6 PM daypart.
**Rationale:** Most coffee consumption occurs before 2 PM. Products designed for afternoon energy needs can extend revenue-generating hours.
**Expected impact:** +20-30% afternoon transaction volume.

#### R8: Build a Seasonal Product Calendar
**Action:** Create a 12-month product launch calendar with quarterly seasonal rotations (Spring Matcha Festival, Summer Cold Brew Series, Fall Coconut Harvest, Winter Warm Drinks).
**Rationale:** Seasonal products drive urgency, social media buzz, and repeat visits. Starbucks generates significant revenue from seasonal LTOs (Pumpkin Spice Latte alone is estimated at $500M+ globally).
**Expected impact:** +5-8% same-store sales growth from seasonal excitement.

#### R9: Implement Dynamic Pricing by Daypart
**Action:** Use the coupon infrastructure to offer deeper discounts during slow hours (2-5 PM) and reduced discounts during peak hours (7-10 AM).
**Rationale:** The existing coupon-driven pricing model already supports variable effective pricing. Daypart optimization can smooth demand, reduce wait times during peak, and drive traffic during slow periods.
**Expected impact:** +8-12% revenue from off-peak daypart growth, improved production flow.

### 11.4 Long-Term Strategic Moves (6-18 Months)

#### R10: Develop a Loyalty-Linked Product Tier
**Action:** Create exclusive "Members Only" products or early access to new launches through the loyalty program.
**Rationale:** Deepens app engagement and creates additional value for membership beyond coupons.

#### R11: Explore Retail-Ready Products
**Action:** Develop bottled or canned versions of the Coconut Latte and Kyoto Matcha Latte for retail distribution.
**Rationale:** Extends brand reach beyond store locations, builds awareness, and generates revenue in channels where Luckin has no physical presence.

#### R12: Build a Food Innovation Pipeline
**Action:** Partner with commissary kitchens to develop a proprietary food menu that complements the drink menu (Asian-inspired pastries, breakfast items).
**Rationale:** Food is the largest gap vs. Starbucks and Dunkin'. A differentiated food menu (not generic pastries) would reinforce Luckin's unique positioning.

---

## 12. APPENDIX: FULL PRODUCT RANKINGS & DATA TABLES

### A1: Complete Top 10 Product Rankings

| Rank | Product | Orders | Est. Revenue | Category |
|------|---------|--------|-------------|----------|
| 1 | Iced Coconut Latte | 70,162 | ~$237K | Fresh Ground Coffee |
| 2 | Iced Kyoto Matcha Latte | 36,206 | ~$136K | Matcha |
| 3 | Drip Coffee | 24,820 | ~$74K | Classic Drinks |
| 4 | Iced American | 23,682 | ~$80K | Fresh Ground Coffee |
| 5 | Matcha Latte | 19,730 | ~$74K | Matcha |
| 6 | Hot Coconut Latte | 17,445 | ~$59K | Fresh Ground Coffee |
| 7 | Hot American | 12,937 | ~$44K | Fresh Ground Coffee |
| 8 | Brown Sugar Boba Latte | 10,485 | ~$40K | Fresh Ground Coffee |
| 9 | Iced Caramel Latte | 10,189 | ~$34K | Fresh Ground Coffee |
| 10 | Classic Latte | 9,438 | ~$28K | Fresh Ground Coffee |

*Note: Revenue estimates calculated using category average prices. Actual product-level revenue may vary based on product-specific pricing and coupon application rates.*

### A2: Category Summary Statistics

| Category | Items | Revenue | Avg Price | Items/Store/Day* | Rev/Store/Day* |
|----------|-------|---------|-----------|-----------------|---------------|
| Fresh Ground Coffee | 258,000 | $873,000 | $3.38 | ~37 | ~$125 |
| Classic Drinks | 130,000 | $389,000 | $2.99 | ~19 | ~$56 |
| Matcha | 57,000 | $214,000 | $3.75 | ~8 | ~$31 |
| Food | 45,000 | $192,000 | $4.27 | ~6 | ~$28 |
| Cold Brew | 41,000 | $158,000 | $3.85 | ~6 | ~$23 |

*Approximate daily per-store figures based on ~30 stores operating over ~230 business days. Actual figures vary significantly by location and opening date.*

### A3: Iced vs Hot Volume Comparison

| Base Product | Iced Variant | Hot Variant | Iced % | Hot % |
|-------------|-------------|-------------|--------|-------|
| Coconut Latte | 70,162 | 17,445 | 80.1% | 19.9% |
| American | 23,682 | 12,937 | 64.7% | 35.3% |
| Matcha (Kyoto vs Regular) | 36,206 | 19,730 | 64.7% | 35.3% |

### A4: Production Efficiency Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Average Production Time | 204-320 seconds | Improving |
| Production Efficiency Improvement | 36% over 7 months | Positive |
| Feb 2026 Production Volume | 36,696 productions | Current run rate |
| Estimated Annual Run Rate | ~440K productions | Based on Feb 2026 |

### A5: Pricing Layer Summary

| Channel | AOV | Typical Discount | Customer Behavior |
|---------|-----|-----------------|-------------------|
| Pickup (Coupon) | $4.95 | 30-45% off menu | Single drink, quick stop |
| Pickup (Full Price) | $5.50-$7.00 | None | Rare, non-app users |
| Delivery | $18.00-$20.00 | Varies | Multi-item, group orders |

### A6: Commodity Database Schema Reference

| Table | Key Fields | Purpose |
|-------|-----------|---------|
| `t_commodity_base_info` | spu_code, commodity_name, category_id, status | Master product catalog |
| `t_commodity_spec_info` | spec_id, spu_code, spec_name, spec_value | Product variants (size, temp, mods) |
| `t_commodity_price` | price_id, spu_code, price_type, price_value | Multi-tier pricing (menu, promo, delivery) |

### A7: Store-Level Product Availability Matrix

| Store Type | Drinks | Food | Merchandise | Cold Brew | Matcha |
|-----------|--------|------|-------------|-----------|--------|
| Standard Retail | Full menu | Select stores | No | Yes | Yes |
| Airport (JFK T4) | Modified menu | Limited | No | Yes | Yes |
| NJ Test Kitchen | Full menu (testing) | Testing | No | Yes | Yes |
| Merchandise Stores (5) | Full menu | Varies | Yes | Yes | Yes |

---

## METHODOLOGY & DATA SOURCES

| Source | Description | Coverage |
|--------|------------|----------|
| Order database (USD transactions) | All-time US order records | Complete order history |
| `luckyus_scm_commodity` database | Product catalog, specs, pricing | Current catalog |
| Production records | Barista production timestamps | Feb 2026 + historical |
| Store operations data | Store-level product availability | Current state |

### Limitations

1. **Revenue estimates are approximate.** Product-level revenue is estimated using category average prices since individual product pricing varies by store, coupon, and order channel
2. **Chinese-named products** in the catalog could not be fully analyzed without translation
3. **Delivery vs. pickup split** for individual products is not broken out in available data
4. **Seasonal trends** are limited by the relatively short operational history of Luckin Coffee USA (less than 2 years of data)
5. **Competitive pricing data** for Starbucks and Dunkin' is based on public menu prices and industry reports, not proprietary data

---

*Report prepared for Luckin Coffee USA Operations & Strategy Team. For questions or data requests, contact the Analytics & Business Intelligence team.*

*Next scheduled update: March 2026 (Monthly Product Performance Review)*
