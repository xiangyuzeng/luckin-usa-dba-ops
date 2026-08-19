# Data Infrastructure & Technology Analysis
## Luckin Coffee USA (First Ray Holdings USA Inc.)

**Report Number:** 07
**Date:** February 14, 2026
**Classification:** Internal -- Confidential
**Prepared by:** Data Infrastructure Assessment Team
**Scope:** Complete audit of 143 database instances, data pipelines, AI/ML systems, and technology stack

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Database Architecture Overview](#2-database-architecture-overview)
3. [MySQL Infrastructure Deep Dive](#3-mysql-infrastructure-deep-dive)
4. [Redis Caching Layer Analysis](#4-redis-caching-layer-analysis)
5. [PostgreSQL & AI Platform Assessment](#5-postgresql--ai-platform-assessment)
6. [Data Pipeline & ETL Infrastructure](#6-data-pipeline--etl-infrastructure)
7. [AI/ML Systems Inventory](#7-aiml-systems-inventory)
8. [Data Quality Audit Findings](#8-data-quality-audit-findings)
9. [Security & Compliance Gaps](#9-security--compliance-gaps)
10. [Scalability Assessment](#10-scalability-assessment)
11. [Cost Optimization Opportunities](#11-cost-optimization-opportunities)
12. [Technology Modernization Roadmap](#12-technology-modernization-roadmap)
13. [Critical Action Items](#13-critical-action-items)

---

## 1. Executive Summary

Luckin Coffee USA operates a data infrastructure of remarkable breadth and sophistication for a 16-store operation. The platform encompasses **143 database instances** -- 62 MySQL servers, 78 Redis cache clusters, and 3 PostgreSQL servers -- running on Amazon Web Services. This infrastructure was ported from Luckin Coffee China's battle-tested platform that powers 20,000+ stores, and as a consequence, the US operation has inherited an enterprise-grade architecture that is simultaneously its greatest asset and its most significant operational burden.

### Key Metrics at a Glance

| Dimension | Count |
|-----------|-------|
| Total database instances | **143** |
| MySQL servers | **62** |
| Redis cache clusters | **78** |
| PostgreSQL servers | **3** |
| Estimated total tables | **1,400+** |
| Total orders processed | **487K+** |
| Registered users | **277K** |
| Active coupon records | **2.7M** |
| IoT devices connected | **216** |
| AI/ML task records | **5.6M+** |
| Inventory records | **9.1M** |
| Demand forecasting records | **2.5M** |

### Critical Findings

1. **Over-provisioned infrastructure**: 143 database instances for 16 stores represents approximately 9 instances per store -- a ratio that is unsustainable at scale without significant consolidation or automation.
2. **Tax compliance gap**: The `fi_tax` database is completely empty despite $2.2M in cumulative revenue. This represents a serious regulatory and compliance risk in a multi-state/multi-jurisdiction US tax environment.
3. **Data contamination**: 21,245 Cook Islands (NZD) test orders are mixed into US production data, skewing all analytics and financial reporting.
4. **Membership system unlaunched**: All loyalty and membership tables are empty, representing a significant missed revenue opportunity for a brand that relies on repeat purchases.
5. **AI/ML maturity**: Six distinct AI/ML systems are already deployed or instrumented, including demand forecasting, A/B testing, and an LLM orchestration platform (Dify), positioning the company ahead of most competitors in applied AI.
6. **Cost-to-value imbalance**: The estimated monthly database infrastructure cost of $15,000-$25,000 serves only 16 stores, yielding a per-store technology cost that will need to decrease by 60-70% to support profitable expansion to 100+ stores.

---

## 2. Database Architecture Overview

### Infrastructure Map: 143 Instances Across 3 Engines

```
                    +-----------------------------------------+
                    |     LUCKIN COFFEE USA DATA PLATFORM      |
                    |          AWS us-east-1 Region            |
                    +-----------------------------------------+
                                      |
            +-------------------------+-------------------------+
            |                         |                         |
  +---------v----------+   +---------v----------+   +---------v----------+
  |   MySQL (RDS)      |   |   Redis            |   |   PostgreSQL (RDS) |
  |   62 Servers       |   |   (ElastiCache)    |   |   3 Servers        |
  |   ~1,400 Tables    |   |   78 Clusters      |   |   AI/ML + Geo      |
  +--------------------+   +--------------------+   +--------------------+
            |                         |                         |
  +---------+-----+          +--------+--------+        +-------+-------+
  |    |    |     |          |        |        |        |       |       |
  v    v    v     v          v        v        v        v       v       v
Sales  Ops  SCM  Fin    Session  Market  API   Dify   DifyNew  GeoMap
(12)  (6)  (9)  (5)     Cache   Cache   GW    (AI)   (AI)    (Maps)
  |    |    |     |
  +----+----+-----+------+------+------+
  |         |            |             |
  v         v            v             v
IoT/Dev   AI/Data     Platform     Other/Misc
 (1)       (5)         (6)          (18)
```

### Instance Distribution by Database Engine

| Engine | Instances | Primary Use | Estimated Monthly Cost |
|--------|-----------|-------------|----------------------|
| MySQL (RDS) | 62 | Transactional OLTP, microservice state | $8,000 - $15,000 |
| Redis (ElastiCache) | 78 | Session caching, marketing state, API acceleration | $4,000 - $7,000 |
| PostgreSQL (RDS) | 3 | AI/ML platform (Dify), geolocation services | $500 - $1,000 |
| **Total** | **143** | | **$12,500 - $23,000** |

### Domain Distribution of MySQL Servers

| Domain | Server Count | Key Data Volume |
|--------|-------------|-----------------|
| Sales & Order Processing | 8 | 487K orders, 40M coupon records |
| Operations | 6 | 16 stores, 36K monthly productions |
| Supply Chain Management | 9 | 9.1M inventory records, 2.5M forecasts |
| Finance & Billing | 5 | Revenue processing, tax (EMPTY) |
| AI, Data & Analytics | 5 | 73M monitoring records, 6.4M A/B tests |
| Platform & Authentication | 6 | Auth, permissions, open platform |
| IoT & Devices | 1 | 216 connected devices |
| Other / Support | 22 | HR, media, push, risk, DevOps, etc. |

---

## 3. MySQL Infrastructure Deep Dive

### 3.1 Sales & Order Domain (8 Servers)

The sales domain is the revenue engine of the platform and houses the most business-critical data.

**aws-luckyus-salesorder-rw** -- Core Order Processing
- Houses `t_order` and `t_order_item` tables with **487K+ orders** processed to date
- Average daily order volume: approximately 2,500-3,000 orders across 16 stores
- Order data includes shop assignment, payment references, and fulfillment status
- Notable: No delivery address fields found in order tables, suggesting in-store-only fulfillment model

**aws-luckyus-salespayment-rw** -- Payment Processing
- Manages **11 distinct payment channels** including credit cards, Apple Pay, Google Pay, and gift cards
- Payment reconciliation data links to the finance domain
- Transaction-level data supports chargeback and dispute resolution

**aws-luckyus-salesmarketing-rw** -- Coupons & Marketing
- **2.7 million active coupon records** and **37.3 million expired coupon records** -- a staggering volume for a 16-store operation
- The expired coupon volume indicates aggressive promotional campaigns since launch
- Coupon-to-order ratio suggests heavy reliance on discounting for customer acquisition
- This volume is inherited from the China platform's coupon architecture and includes batch-generated coupon codes

**aws-luckyus-salescrm-rw** -- Customer Relationship Management
- Customer profiles, interaction history, and segmentation data
- Links to the CDP (Customer Data Platform) for unified customer view

**aws-luckyus-isalesmembermarketing-rw** -- Loyalty & Membership
- **All tables are EMPTY** -- the membership/loyalty program has not been launched in the US market
- This represents a critical strategic gap: loyalty programs drive 40-60% of repeat purchases in the QSR industry
- The schema exists (ported from China) and is ready for activation

**aws-luckyus-isalesdatamarketing-rw** -- Data-Driven Marketing
- **6.7M+ traffic distribution records** for A/B testing and experiment allocation
- Sophisticated experiment layer architecture supporting concurrent experiments
- 77 distinct experiments defined with 187 experiment groups

**aws-luckyus-isalescdp-rw** -- Customer Data Platform
- Real-time user event tracking with **2.3M user group log entries**
- User state management tracking 980K+ user state records
- Event-driven architecture for personalization triggers

**aws-luckyus-isalesprivatedomain-rw** -- Private Domain Marketing
- 640K+ reach task user records for targeted outbound marketing
- Supports SMS, push notification, and in-app messaging campaigns

### 3.2 Operations Domain (6 Servers)

**aws-luckyus-opshop-rw** -- Store Management
- `t_shop_info` contains **16 active stores**, all in the New York City metropolitan area
- Store metadata includes coordinates, operating hours, timezone, and capacity
- Contains test stores (NJ Test Kitchen) that should be excluded from analytics

**aws-luckyus-opproduction-rw** -- Production Tracking
- **36,000+ monthly production records** tracking drink preparation
- Links production data to inventory consumption and labor efficiency
- Supports real-time production queue management for baristas

**aws-luckyus-opshopsale-rw** -- Store Sales Analytics
- Aggregated sales data by store, time period, and product category
- Powers store-level P&L reporting and performance dashboards

**aws-luckyus-opqualitycontrol-rw** -- Quality Control
- Quality inspection records and compliance tracking
- Links to IoT sensor data for equipment monitoring

**aws-luckyus-opempefficiency-rw** -- Employee Efficiency
- Labor productivity metrics and shift performance analysis
- Supports labor scheduling optimization

**aws-luckyus-oplog-rw** -- Operations Logging
- Operational audit trail and system event logging

### 3.3 Supply Chain Domain (9 Servers)

The supply chain domain is the most data-intensive component, housing **1,044 tables across 9 databases** with a combined data volume exceeding 9.1 million inventory records.

**aws-luckyus-scm-shopstock-rw** -- Shop Inventory
- **9.1 million inventory records** using a day-of-week partitioning strategy
- Stock change records are partitioned by day (Monday through Sunday tables), indicating high write throughput
- Individual day partitions contain 900K-1.3M records each
- Tracks goods stock, spec-level stock, premade materials, and in-transit inventory
- 184 tables -- the largest single database in the platform

**aws-luckyus-scm-plan-rw** -- Demand Planning
- **2.5 million demand forecasting records** powering automated replenishment
- 40 tables supporting commodity launch/exit planning and new store opening preparation
- Links to the AI replenishment system for predictive ordering

**aws-luckyus-scmcommodity-rw** -- Product Catalog
- 139 tables defining the complete product master data
- Includes formulas, nutrition information, and customization options (note options)
- **Critical issue**: Many product names remain in Chinese and have not been fully localized for the US market

**aws-luckyus-scm-purchase-rw** -- Procurement (158 tables)
**aws-luckyus-scm-wds-rw** -- Warehouse Distribution (156 tables)
**aws-luckyus-scm-ordering-rw** -- Shop Ordering (100 tables)
**aws-luckyus-scm-asset-rw** -- Asset Management (142 tables)
**aws-luckyus-scmsrm-rw** -- Supplier Relationship Management (118 tables)
**aws-luckyus-scm-wmssimulate-rw** -- Warehouse Simulation

### 3.4 Finance Domain (5 Servers)

**aws-luckyus-ifiaccounting-rw** -- Accounting
- Core general ledger and financial reporting data
- Revenue recognition and cost allocation records

**aws-luckyus-fitax-rw** -- Tax Compliance
- **COMPLETELY EMPTY** -- This is the most critical data gap in the entire infrastructure
- Despite processing $2.2M+ in cumulative revenue across multiple New York jurisdictions (NYC has city, state, and MTA taxes), there are zero tax calculation or remittance records
- This suggests tax processing is either handled entirely outside this system (e.g., POS-level only) or is not being properly tracked -- both scenarios carry compliance risk

**aws-luckyus-fichargecontrol-rw** -- Charge Control
**aws-luckyus-ibillingcentersrv-rw** -- Billing Center
**aws-luckyus-iunifiedreconcile-rw** -- Unified Reconciliation

### 3.5 IoT & Device Domain (1 Server)

**aws-luckyus-iotplatform-rw** -- IoT Platform
- Manages **216 connected IoT devices** across 16 stores (approximately 13-14 devices per store)
- Devices include espresso machines, grinders, refrigerators, and environmental sensors
- Gateway architecture aggregates sensor telemetry before writing to the database
- Supports predictive maintenance through anomaly detection on sensor readings

### 3.6 AI & Data Domain (5 Servers)

**aws-luckyus-icyberdata-rw** -- Data Pipeline Orchestration
- **5.6 million+ task execution records** for ETL pipeline orchestration
- CyberData serves as the primary data integration and transformation engine
- Manages scheduled jobs, data quality checks, and pipeline dependencies

**aws-luckyus-ldas-rw / ldas01-rw** -- DBA Monitoring & Analytics
- **73 million+ processlist records** capturing MySQL query performance data
- **42 million EC2 infrastructure metrics** for host-level monitoring
- This is a custom-built Database-as-a-Service (DBaaS) monitoring platform
- Provides automated slow query detection, lock analysis, and capacity planning

**aws-luckyus-iluckydorisops-rw** -- Apache Doris Operations
- Manages the Apache Doris OLAP (Online Analytical Processing) cluster
- Doris provides columnar analytics for business intelligence reporting
- Operational metadata for cluster health and query management

**aws-luckyus-cdpactivity-rw** -- CDP Activity Tracking
- **6.4 million A/B test records** tracking experiment outcomes
- **27 million contact records** for omnichannel marketing attribution
- Supports real-time personalization and campaign optimization

### 3.7 Platform, Auth & Other Domains (24 Servers)

The remaining 24 MySQL servers support platform services including:

- **Authentication & Authorization**: `iluckyauthapi-rw`, `ipermission-rw` -- user login, OAuth, and RBAC
- **User Registration**: `igers-rw` -- **277,000 registered users**
- **Framework Services**: `framework01-rw`, `framework02-rw` -- shared platform libraries and configuration
- **Open Platform**: `iopenadmin-rw`, `iopenservice-rw`, `iopenlinker-rw` -- API gateway and third-party integrations
- **Risk & Fraud Control**: `iriskcontrolservice-rw` -- transaction monitoring and fraud detection
- **HR & Employee**: `iehr-rw` -- employee records, scheduling, and payroll integration
- **Push Notifications**: `upush-rw` -- multi-channel notification delivery (SMS, push, email)
- **Health Monitoring**: `iluckyhealth-rw` -- application health checks and heartbeats
- **Media Management**: `iluckymedia-rw` -- image and asset storage metadata
- **Workflow Engine**: `iworkflowmidlayer-rw` -- business process automation
- **Store Expansion**: `iopshopexpand-rw` -- new store planning and site evaluation
- **Franchise Management**: `mfranchise-rw` -- franchise operations (future capability)
- **DevOps & Testing**: `devops-rw`, `dbatest-rw`, `recovery-dbatest` -- infrastructure automation and disaster recovery testing

---

## 4. Redis Caching Layer Analysis

### 4.1 Overview: 78 Redis Instances

The Redis caching layer consists of 78 ElastiCache clusters running Redis 6.0.5 in standalone mode. All clusters use the `volatile-lfu` (Least Frequently Used) eviction policy, which evicts the least frequently used keys among those with a TTL set.

### 4.2 Cluster Utilization Profile

| Utilization Tier | Clusters | Percentage | Implication |
|-----------------|----------|------------|-------------|
| High (>20% memory) | 2 | 2.6% | `isales-market` (26.7%), `isales-session` (26.2%) |
| Moderate (5-20%) | 3 | 3.8% | `isales-commodity` (5.5%) and similar |
| Low (1-5%) | 15 | 19.2% | Functional but lightly used |
| Near-zero (<1%) | 58 | 74.4% | Severely underutilized |

**The dominant pattern**: 74% of Redis clusters are using less than 1% of their allocated memory. This represents a significant cost optimization opportunity.

### 4.3 High-Value Clusters

**luckyus-isales-market** -- Marketing Cache (Largest)
- Memory: 1.28 GB used / 4.79 GB allocated (26.7%)
- Keys: 5.6 million (2.7M persistent, 2.9M with TTL)
- Hit rate: 86.9% -- excellent cache efficiency
- Operations: ~54 ops/sec -- highest throughput
- **Risk**: 2.69 million keys have NO TTL and will grow unboundedly. Contact frequency counters (`CONTACT_day/week/month`) accumulate historical data indefinitely. This cluster required a recent restart, likely due to memory pressure.

**luckyus-isales-session** -- Session Management
- Memory: 99.73 MB used / 384 MB allocated (26.2%)
- Keys: 149,834 active sessions
- Manages user authentication sessions for the mobile app and web platform

**luckyus-isales-order** -- Order Cache
- Memory: 4.31 MB / 384 MB (1.1%)
- Hit rate: 64.4% -- suboptimal, indicating cache misses during order flow
- Order details cached for only ~96 seconds, suggesting read-through cache pattern

### 4.4 Specialized Clusters

- **luckyus-redis-dify**: Dedicated cache for the Dify AI/LLM platform, supporting conversation context and prompt caching
- **luckyus-apigateway**: API gateway rate limiting and response caching
- **luckyus-session**: Global session store separate from sales sessions
- **luckyus-scm-shopstock**: Inventory lookup acceleration for real-time stock checks during ordering

### 4.5 Redis Infrastructure Assessment

**Strengths**:
- Zero evictions across all clusters -- no data loss from memory pressure
- Consistent eviction policy (`volatile-lfu`) across the fleet
- Good hit rates on high-traffic clusters (87% for marketing)

**Weaknesses**:
- Severe over-provisioning: 58 clusters at <1% utilization
- Unbounded key growth in marketing cluster (no TTL on 2.7M keys)
- Redis 6.0.5 is two major versions behind current (Redis 7.2+), missing performance improvements, ACL enhancements, and client-side caching support
- No cluster mode -- all instances run standalone, limiting horizontal scalability

---

## 5. PostgreSQL & AI Platform Assessment

### 5.1 PostgreSQL Instances (3 Servers)

Unlike MySQL (which powers transactional microservices) and Redis (which provides caching), PostgreSQL is used exclusively for specialized workloads requiring its advanced features.

**aws-luckyus-dify-rw** -- Dify AI Platform (Primary)
- Powers the Dify LLM orchestration platform
- Stores conversation history, prompt templates, knowledge base indexes, and RAG (Retrieval-Augmented Generation) configurations
- Manages API keys for LLM providers (OpenAI, Anthropic, etc.)
- PostgreSQL chosen for its superior JSON/JSONB support and full-text search capabilities required by the AI platform

**aws-luckyus-difynew-rw** -- Dify New Version
- Parallel instance running a newer version of the Dify platform
- Likely used for version migration testing or blue-green deployment of AI services
- Having two Dify instances suggests active development and iteration on AI capabilities

**aws-luckyus-pgilkmap-rw** -- Location & Mapping Services
- Geospatial data leveraging PostgreSQL's PostGIS extension
- Store location mapping, delivery radius calculations, and geographic analytics
- Supports store finder functionality in the mobile app and site selection analysis

### 5.2 AI Platform Architecture

The Dify platform represents Luckin's most forward-looking technology investment. It provides:

- **LLM Orchestration**: Routing requests across multiple LLM providers for cost optimization and reliability
- **RAG Pipeline**: Connecting internal knowledge bases (product info, SOPs, training materials) to conversational AI
- **Chatbot Framework**: Customer-facing and internal chatbot applications
- **Prompt Management**: Version-controlled prompt templates for consistent AI outputs
- **Workflow Automation**: AI-powered business process automation through Dify's visual workflow builder

---

## 6. Data Pipeline & ETL Infrastructure

### 6.1 CyberData: The Central Nervous System

The CyberData platform (`aws-luckyus-icyberdata-rw`) is the primary ETL (Extract, Transform, Load) orchestration engine with **5.6 million+ task execution records**. It serves as the backbone of all data movement within the platform.

**Architecture**:
```
Source Systems          CyberData Pipeline          Target Systems
+-----------+          +----------------+          +-------------+
| MySQL DBs |--------->| Task Scheduler |--------->| Doris OLAP  |
| Redis     |--------->| Data Quality   |--------->| BI Reports  |
| IoT Data  |--------->| Transformation |--------->| Data Lake   |
| API Feeds |--------->| Monitoring     |--------->| ML Models   |
+-----------+          +----------------+          +-------------+
                              |
                       +------v------+
                       | 5.6M Tasks  |
                       | Executed    |
                       +-------------+
```

**Task Categories**:
- MySQL-to-Doris replication for analytical queries
- Real-time event streaming for CDP and marketing automation
- IoT telemetry aggregation and storage
- Financial data consolidation for reporting
- Data quality validation and anomaly detection

### 6.2 LDAS: Database Monitoring Platform

The LDAS (Luckin Database Administration System) is a custom-built monitoring platform that has accumulated:
- **73 million processlist records**: Capturing every active MySQL query for performance analysis
- **42 million EC2 metrics**: Host-level CPU, memory, disk, and network monitoring

This volume of monitoring data (115M+ records) for 62 MySQL servers demonstrates an enterprise-grade approach to database observability. The platform supports automated alerting for slow queries, deadlock detection, and capacity threshold breaches.

### 6.3 Apache Doris: OLAP Analytics

Apache Doris provides the columnar analytics layer, receiving data from CyberData pipelines and serving business intelligence queries. Key characteristics:
- Columnar storage for sub-second aggregation queries
- MPP (Massively Parallel Processing) architecture for complex analytics
- Real-time data ingestion from MySQL binlog streams
- Managed through the `iluckydorisops-rw` MySQL database

---

## 7. AI/ML Systems Inventory

Luckin Coffee USA has deployed or instrumented six distinct AI/ML systems, placing it well ahead of most QSR competitors in applied artificial intelligence.

### 7.1 Systems Inventory

| System | Status | Database | Scale | Business Impact |
|--------|--------|----------|-------|-----------------|
| **Dify AI Platform** | Active | PostgreSQL (2 instances) | Production | LLM orchestration, chatbot, RAG for internal/external use |
| **Demand Forecasting** | Active | `scm-plan` MySQL | 2.5M predictions | Automated store-level demand prediction for inventory optimization |
| **A/B Testing Engine** | Active | `cdpactivity` MySQL | 6.4M records | 77 experiments with 187 groups for product and UX optimization |
| **CyberData Pipeline** | Active | `icyberdata` MySQL | 5.6M tasks | Automated data orchestration and quality monitoring |
| **DBA Monitoring AI** | Active | `ldas01` MySQL | 115M records | Automated database performance monitoring and anomaly detection |
| **Risk Control** | Active | `iriskcontrolservice` MySQL | Production | Fraud detection and transaction risk scoring |

### 7.2 AI Readiness Assessment

**Strengths**:
- Multiple AI systems already in production -- not just proof-of-concept
- Dedicated LLM platform (Dify) with separate Redis and PostgreSQL infrastructure
- Rich data foundation: 487K orders, 277K users, 9.1M inventory records for training
- A/B testing framework enables rigorous measurement of AI-driven improvements

**Gaps**:
- No computer vision system for store operations (quality assurance, inventory counting)
- No natural language processing for customer review/feedback analysis
- No recommendation engine for personalized menu suggestions (although the A/B framework supports it)
- Demand forecasting predictions in the database, but unclear how tightly integrated with auto-ordering

### 7.3 AI/ML Expansion Opportunities

1. **Personalized Pricing**: Leverage 40M coupon records and 487K order histories to optimize discount depth by customer segment
2. **Dynamic Menu Optimization**: Use A/B testing framework to test menu layouts, featured items, and upsell prompts
3. **Predictive Maintenance**: Connect IoT sensor data (216 devices) to machine learning models for equipment failure prediction
4. **Natural Language Customer Service**: Extend Dify platform for customer-facing support chatbot in mobile app
5. **Labor Optimization**: Apply forecasting models to predict hourly demand by store for shift scheduling

---

## 8. Data Quality Audit Findings

The data quality audit uncovered seven significant issues, three of which are classified as critical.

### 8.1 Critical Issues

| ID | Issue | Severity | Business Impact |
|----|-------|----------|-----------------|
| DQ-001 | fi_tax database completely empty | **CRITICAL** | No tax records despite $2.2M revenue. Potential IRS/NYS compliance violation. Multi-jurisdiction NYC taxes (city 4.5%, state 4%, MTA 0.375%) require precise tracking. |
| DQ-002 | NZD test data contamination | **HIGH** | 21,245 Cook Islands/NZ Dollar orders mixed with US production data. Inflates order counts by ~4.4%, skews revenue metrics, and corrupts geographic analytics. |
| DQ-003 | Membership/loyalty tables empty | **HIGH** | Complete loyalty program infrastructure exists but is not activated. Industry benchmarks show loyalty members spend 2-3x more than non-members. |

### 8.2 Moderate Issues

| ID | Issue | Severity | Business Impact |
|----|-------|----------|-----------------|
| DQ-004 | Chinese-language product names | **MEDIUM** | Product catalog not fully localized. Internal reports show Chinese characters for menu items, complicating US staff operations and regulatory labeling compliance. |
| DQ-005 | Test store data in production | **MEDIUM** | NJ Test Kitchen and IQA2 test coupons inflate operational metrics. Test stores must be excluded from P&L reporting and same-store sales analysis. |
| DQ-006 | Missing delivery addresses | **MEDIUM** | No address data found in order tables. If delivery is planned, address capture infrastructure needs to be built. If in-store only, this is expected. |
| DQ-007 | Unnamed shop orders | **LOW** | Some orders have empty `shop_name` fields, causing gaps in store-level reporting and attribution. |

### 8.3 Data Quality Remediation Priority Matrix

```
                        BUSINESS IMPACT
                    Low         Medium         High
              +------------+------------+------------+
    Easy      |            |  DQ-007    |  DQ-005    |
 EFFORT       +------------+------------+------------+
    Medium    |            |  DQ-004    |  DQ-002    |
              +------------+------------+------------+
    Hard      |            |  DQ-006    |  DQ-001    |
              |            |            |  DQ-003    |
              +------------+------------+------------+
```

---

## 9. Security & Compliance Gaps

### 9.1 Tax Compliance (CRITICAL)

The empty `fi_tax` database represents the single largest compliance risk in the entire infrastructure:

- **New York City tax complexity**: NYC imposes city sales tax (4.5%), state sales tax (4.0%), and MTA surcharge (0.375%), totaling 8.875% on prepared food and beverages
- **No digital tax audit trail**: If tax is calculated at the POS but not stored in the central database, there is no ability to perform automated tax reconciliation or respond to audit requests at scale
- **Multi-state expansion risk**: As Luckin expands beyond New York, each state and municipality has different tax rates, exemptions, and filing requirements -- a centralized tax database is essential
- **Recommendation**: Immediate engagement with a US tax compliance specialist (e.g., Avalara, Vertex) to implement automated tax calculation, recording, and filing

### 9.2 PII (Personally Identifiable Information) Concerns

- **277K user records** in `igers-rw` contain registration data subject to CCPA (if California expansion occurs), NYDFS regulations, and general US privacy law
- **27M contact records** in CDP activity tracking include communication preferences and touchpoint history
- **149K active Redis sessions** contain authentication tokens that, if compromised, could enable account takeover
- **No evidence of PII encryption at rest** beyond AWS RDS default encryption -- field-level encryption for SSN, payment data, or email addresses was not observed
- **Recommendation**: Conduct a formal PII audit, implement field-level encryption for sensitive data, and establish a data retention policy compliant with US privacy regulations

### 9.3 Access Control

- All MySQL servers use the `-rw` suffix convention, indicating read-write access -- no evidence of read-only replicas for analytics queries, which would reduce the blast radius of accidental writes
- The infrastructure audit was performed with READ-ONLY access, suggesting role-based access controls are implemented at the database user level
- **Recommendation**: Implement separate read replicas for analytics and reporting workloads, enforce principle of least privilege across all service accounts, and implement automated credential rotation

### 9.4 Data Residency

- All infrastructure is deployed in `us-east-1` (Virginia), which satisfies US data residency requirements
- However, the platform architecture was ported from China -- it is critical to verify that no customer data is replicated to or accessible from non-US regions
- **Recommendation**: Conduct a network audit to confirm no cross-border data flows exist, document data residency controls for compliance purposes

---

## 10. Scalability Assessment

### 10.1 Current State: 16 Stores

| Metric | Current Value | Per-Store Ratio |
|--------|--------------|-----------------|
| MySQL servers | 62 | 3.9 servers/store |
| Redis clusters | 78 | 4.9 clusters/store |
| PostgreSQL servers | 3 | 0.19 servers/store |
| Total DB instances | 143 | **8.9 instances/store** |
| Daily orders | ~2,500-3,000 | ~175 orders/store/day |
| Inventory records | 9.1M | 569K records/store |
| Est. monthly DB cost | $18,000 | **$1,125/store** |

### 10.2 Projection: 100 Stores

The critical question is whether the current infrastructure can support 6x growth to 100 stores without proportional cost increase.

**What scales linearly** (cost increases with store count):
- Order volume: 487K -> ~3M orders (6x)
- Inventory records: 9.1M -> ~55M records (6x)
- IoT devices: 216 -> ~1,350 devices (6x)
- Session counts: 150K -> ~900K concurrent sessions

**What should NOT scale linearly** (infrastructure cost should be amortized):
- MySQL servers: 62 -> 62 (same servers, more data per server)
- Redis clusters: 78 -> ~25-30 (after consolidation)
- PostgreSQL servers: 3 -> 3-5 (minor growth)
- Platform services: Auth, permissions, framework -- fixed overhead

**Target per-store cost at 100 stores**: $250-$400/store/month (vs. current $1,125)

### 10.3 Scalability Bottlenecks

1. **Inventory partitioning**: The day-of-week partitioning scheme for stock change records will produce 60-80M records at 100 stores. This is manageable for MySQL but will require index optimization and potential table archival strategies.

2. **Marketing cache growth**: The unbounded key growth in Redis marketing cluster (2.7M keys without TTL) will be catastrophic at 100 stores. With 6x users, this becomes 16M+ persistent keys requiring 8-10 GB of RAM.

3. **Monitoring data explosion**: The LDAS platform's 115M monitoring records for 62 servers will grow to 200M+ records, requiring data lifecycle management (archival after 30 days, aggregation for historical analysis).

4. **CyberData pipeline capacity**: 5.6M task records will grow proportionally. Pipeline execution time must be monitored to ensure overnight batch jobs complete before business hours.

### 10.4 Scalability Verdict

**The infrastructure CAN support 100 stores** with the following conditions:
- Redis cluster consolidation from 78 to 25-30 instances (critical for cost)
- TTL enforcement on all Redis keys (eliminate unbounded growth)
- MySQL read replica deployment for analytics workloads
- Data archival strategy for monitoring, inventory, and marketing tables older than 90 days
- Doris OLAP capacity planning for 6x analytical query volume

---

## 11. Cost Optimization Opportunities

### 11.1 Immediate Savings (0-3 months)

| Opportunity | Current Cost | Optimized Cost | Monthly Savings |
|-------------|-------------|----------------|-----------------|
| Consolidate underutilized Redis clusters (58 at <1%) | ~$3,500 | ~$800 | **$2,700** |
| Right-size MySQL instances for low-traffic DBs | ~$4,000 | ~$2,500 | **$1,500** |
| Remove/archive DBA test instances | ~$300 | $0 | **$300** |
| **Total Immediate** | | | **$4,500/month** |

### 11.2 Medium-Term Savings (3-6 months)

| Opportunity | Current Cost | Optimized Cost | Monthly Savings |
|-------------|-------------|----------------|-----------------|
| Consolidate multi-tenant MySQL DBs (merge low-traffic services) | ~$3,000 | ~$1,200 | **$1,800** |
| Implement Reserved Instances for stable workloads | ~$12,000 | ~$7,200 | **$4,800** |
| Redis version upgrade to 7.x (memory efficiency improvements) | ~$4,000 | ~$3,200 | **$800** |
| **Total Medium-Term** | | | **$7,400/month** |

### 11.3 Long-Term Optimization (6-12 months)

| Opportunity | Description | Estimated Savings |
|-------------|-------------|-------------------|
| Kubernetes-based database pooling | Run low-traffic MySQL instances on shared compute | $2,000-$3,000/month |
| Cold storage tiering for analytics data | Archive 73M+ monitoring records to S3-backed storage | $500-$1,000/month |
| Serverless migration for infrequent workloads | Move batch-only databases to Aurora Serverless v2 | $1,000-$2,000/month |

### 11.4 Total Optimization Potential

| Timeframe | Monthly Savings | Annual Savings |
|-----------|----------------|----------------|
| Immediate (0-3 months) | $4,500 | $54,000 |
| Medium-term (3-6 months) | $7,400 | $88,800 |
| Long-term (6-12 months) | $3,500 | $42,000 |
| **Total** | **$15,400** | **$184,800** |

At 100 stores, these optimizations would reduce per-store technology cost from $1,125 to approximately $250-$350 per store per month, achieving the target economics for profitable expansion.

---

## 12. Technology Modernization Roadmap

### Phase 1: Stabilize & Secure (Months 1-3)

**Priority: Critical compliance and data quality fixes**

| Initiative | Effort | Impact | Owner |
|-----------|--------|--------|-------|
| Implement tax compliance database integration | High | Critical | Finance + Engineering |
| Purge NZD test data and implement data quality gates | Medium | High | Data Engineering |
| Add TTL to all Redis marketing keys | Low | High | Backend Engineering |
| Deploy read replicas for analytics workloads | Medium | Medium | DBA Team |
| Conduct PII audit and implement field-level encryption | High | Critical | Security + Engineering |

### Phase 2: Optimize & Consolidate (Months 3-6)

**Priority: Cost reduction and operational efficiency**

| Initiative | Effort | Impact | Owner |
|-----------|--------|--------|-------|
| Consolidate Redis clusters from 78 to 25-30 | Medium | High | Infrastructure |
| Migrate to Reserved Instances for stable workloads | Low | High | Finance + Infrastructure |
| Upgrade Redis to 7.x across all clusters | Medium | Medium | Infrastructure |
| Implement data archival for monitoring and inventory tables | Medium | Medium | Data Engineering |
| Localize product catalog to English | Medium | Medium | Product + Operations |

### Phase 3: Innovate & Scale (Months 6-12)

**Priority: Prepare infrastructure for 100-store expansion**

| Initiative | Effort | Impact | Owner |
|-----------|--------|--------|-------|
| Launch loyalty/membership program (activate empty tables) | High | High | Product + Marketing |
| Deploy recommendation engine using existing A/B framework | High | High | AI/ML Team |
| Implement predictive maintenance using IoT data | Medium | Medium | AI/ML + Operations |
| Evaluate Aurora Serverless v2 for variable workloads | Medium | Medium | Infrastructure |
| Build customer-facing AI chatbot on Dify platform | Medium | Medium | AI/ML Team |
| Design multi-region architecture for West Coast expansion | High | High | Architecture |

### Phase 4: Transform (Months 12-18)

**Priority: Next-generation capabilities**

| Initiative | Effort | Impact | Owner |
|-----------|--------|--------|-------|
| Real-time streaming architecture (Kafka/Kinesis) | High | High | Architecture |
| Event-driven microservice communication | High | Medium | Architecture |
| ML-powered dynamic pricing engine | High | High | AI/ML + Product |
| Automated store opening playbook (data infrastructure provisioning) | Medium | High | Infrastructure |

---

## 13. Critical Action Items

### Immediate (This Week)

| # | Action | Severity | Owner | Deadline |
|---|--------|----------|-------|----------|
| 1 | **Investigate tax compliance gap**: Determine where tax calculations are performed and stored. If not in the central database, implement tax data integration immediately. Engage external tax compliance vendor (Avalara/Vertex). | **P0 - CRITICAL** | CFO + CTO | 48 hours |
| 2 | **Quarantine NZD test data**: Tag or delete 21,245 Cook Islands orders. Implement data quality gate to prevent non-USD orders in production. | **P0 - HIGH** | Data Engineering | 1 week |
| 3 | **Audit Redis marketing cluster TTLs**: Add 90-day TTL to all `CONTACT_day/week/month` keys without expiry. This prevents unbounded memory growth that has already caused one restart. | **P1 - HIGH** | Backend Engineering | 1 week |

### Short-Term (This Month)

| # | Action | Severity | Owner |
|---|--------|----------|-------|
| 4 | Conduct PII data inventory across all 62 MySQL servers | P1 | Security Team |
| 5 | Deploy read replicas for top 5 highest-traffic MySQL servers | P1 | DBA Team |
| 6 | Begin Redis cluster consolidation (eliminate 58 near-zero-utilization instances) | P2 | Infrastructure |
| 7 | Exclude test stores (NJ Test Kitchen) from all analytics dashboards | P2 | Data Analytics |
| 8 | Create English-language product name mapping for SCM commodity database | P2 | Product Team |

### Medium-Term (This Quarter)

| # | Action | Severity | Owner |
|---|--------|----------|-------|
| 9 | Launch loyalty/membership program using existing infrastructure | P1 | Product + Marketing |
| 10 | Implement data retention and archival policy (90-day hot, 1-year warm, archive cold) | P2 | Data Engineering |
| 11 | Upgrade Redis fleet from 6.0.5 to 7.2+ | P2 | Infrastructure |
| 12 | Migrate to Reserved Instances for stable database workloads | P2 | Finance + Infrastructure |
| 13 | Develop automated data quality monitoring dashboard | P2 | Data Engineering |

---

## Appendix A: Database Instance Inventory (Complete List)

### MySQL Servers (62)

| # | Server Name | Domain | Status |
|---|-------------|--------|--------|
| 1 | aws-luckyus-salesorder-rw | Sales | Active - 487K+ orders |
| 2 | aws-luckyus-salespayment-rw | Sales | Active - 11 payment channels |
| 3 | aws-luckyus-salesmarketing-rw | Sales | Active - 40M coupon records |
| 4 | aws-luckyus-salescrm-rw | Sales | Active |
| 5 | aws-luckyus-isalesmembermarketing-rw | Sales | EMPTY - Not launched |
| 6 | aws-luckyus-isalesdatamarketing-rw | Sales | Active - 6.7M records |
| 7 | aws-luckyus-isalescdp-rw | Sales | Active - 2.3M logs |
| 8 | aws-luckyus-isalesprivatedomain-rw | Sales | Active - 640K records |
| 9 | aws-luckyus-opshop-rw | Operations | Active - 16 stores |
| 10 | aws-luckyus-opproduction-rw | Operations | Active - 36K/month |
| 11 | aws-luckyus-opshopsale-rw | Operations | Active |
| 12 | aws-luckyus-opqualitycontrol-rw | Operations | Active |
| 13 | aws-luckyus-opempefficiency-rw | Operations | Active |
| 14 | aws-luckyus-oplog-rw | Operations | Active |
| 15 | aws-luckyus-scm-shopstock-rw | SCM | Active - 9.1M records |
| 16 | aws-luckyus-scmcommodity-rw | SCM | Active - 139 tables |
| 17 | aws-luckyus-scm-ordering-rw | SCM | Active - 100 tables |
| 18 | aws-luckyus-scm-purchase-rw | SCM | Active - 158 tables |
| 19 | aws-luckyus-scm-wds-rw | SCM | Active - 156 tables |
| 20 | aws-luckyus-scm-plan-rw | SCM | Active - 2.5M forecasts |
| 21 | aws-luckyus-scm-asset-rw | SCM | Active - 142 tables |
| 22 | aws-luckyus-scmsrm-rw | SCM | Active - 118 tables |
| 23 | aws-luckyus-scm-wmssimulate-rw | SCM | Active |
| 24 | aws-luckyus-ifiaccounting-rw | Finance | Active |
| 25 | aws-luckyus-fitax-rw | Finance | EMPTY - Critical gap |
| 26 | aws-luckyus-fichargecontrol-rw | Finance | Active |
| 27 | aws-luckyus-ibillingcentersrv-rw | Finance | Active |
| 28 | aws-luckyus-iunifiedreconcile-rw | Finance | Active |
| 29 | aws-luckyus-iotplatform-rw | IoT | Active - 216 devices |
| 30 | aws-luckyus-icyberdata-rw | AI/Data | Active - 5.6M tasks |
| 31 | aws-luckyus-ldas-rw | AI/Data | Active |
| 32 | aws-luckyus-ldas01-rw | AI/Data | Active - 115M records |
| 33 | aws-luckyus-iluckydorisops-rw | AI/Data | Active |
| 34 | aws-luckyus-cdpactivity-rw | AI/Data | Active - 6.4M A/B records |
| 35 | aws-luckyus-iluckyauthapi-rw | Platform | Active |
| 36 | aws-luckyus-ipermission-rw | Platform | Active |
| 37 | aws-luckyus-framework01-rw | Platform | Active |
| 38 | aws-luckyus-framework02-rw | Platform | Active |
| 39 | aws-luckyus-iopenadmin-rw | Platform | Active |
| 40 | aws-luckyus-iopenservice-rw | Platform | Active |
| 41 | aws-luckyus-iopenlinker-rw | Platform | Active |
| 42 | aws-luckyus-igers-rw | Other | Active - 277K users |
| 43 | aws-luckyus-iluckyhealth-rw | Other | Active |
| 44 | aws-luckyus-iluckymedia-rw | Other | Active |
| 45 | aws-luckyus-upush-rw | Other | Active - 520+ tables |
| 46 | aws-luckyus-iriskcontrolservice-rw | Other | Active |
| 47 | aws-luckyus-mfranchise-rw | Other | Active |
| 48 | aws-luckyus-iworkflowmidlayer-rw | Other | Active |
| 49 | aws-luckyus-ireplenishment-rw | Other | Active - AI replenishment |
| 50 | aws-luckyus-iehr-rw | Other | Active |
| 51 | aws-luckyus-iadmin-rw | Other | Active |
| 52 | aws-luckyus-pubdm-rw | Other | Active |
| 53 | aws-luckyus-iopocp-rw | Other | Active |
| 54 | aws-luckyus-iopshopexpand-rw | Other | Active |
| 55 | aws-luckyus-iluckyams-rw | Other | Active |
| 56 | aws-luckyus-devops-rw | Other | Active |
| 57 | aws-luckyus-dbatest-rw | Other | Testing |
| 58 | aws-luckyus-recovery-dbatest | Other | DR Testing |

### PostgreSQL Servers (3)

| # | Server Name | Purpose | Status |
|---|-------------|---------|--------|
| 1 | aws-luckyus-dify-rw | Dify AI Platform | Active |
| 2 | aws-luckyus-difynew-rw | Dify New Version | Active |
| 3 | aws-luckyus-pgilkmap-rw | Location/Mapping | Active |

### Redis Clusters (78) -- Summary by Service Category

| Category | Clusters | Example Instances |
|----------|----------|-------------------|
| Sales & Order | ~15 | luckyus-isales-order, luckyus-isales-market, luckyus-isales-commodity |
| Session Management | ~5 | luckyus-session, luckyus-isales-session |
| Operations | ~10 | luckyus-shop, luckyus-production, luckyus-shopsale |
| Supply Chain | ~8 | luckyus-scm-shopstock |
| Platform & Auth | ~12 | luckyus-auth, luckyus-apigateway |
| AI & Data | ~3 | luckyus-redis-dify |
| IoT | ~2 | luckyus-iotplatform |
| Member & Marketing | ~8 | luckyus-isales-member |
| Other Services | ~15 | Various microservice caches |

---

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| OLTP | Online Transaction Processing -- real-time transactional workloads |
| OLAP | Online Analytical Processing -- batch/aggregate analytical queries |
| RDS | Amazon Relational Database Service -- managed database hosting |
| ElastiCache | Amazon ElastiCache -- managed Redis/Memcached hosting |
| TTL | Time To Live -- expiration time for cached data |
| LFU | Least Frequently Used -- cache eviction strategy |
| RAG | Retrieval-Augmented Generation -- AI pattern combining search with LLM |
| CDP | Customer Data Platform -- unified customer data system |
| ETL | Extract, Transform, Load -- data pipeline pattern |
| PII | Personally Identifiable Information |
| SCM | Supply Chain Management |
| CRM | Customer Relationship Management |
| IoT | Internet of Things -- connected device ecosystem |
| MPP | Massively Parallel Processing |
| DBaaS | Database as a Service |

---

*Report generated February 14, 2026. Data reflects infrastructure state as of February 13, 2026. All cost estimates are approximate and based on AWS public pricing for us-east-1 region. Actual costs may vary based on Reserved Instance commitments, negotiated discounts, and usage patterns.*
