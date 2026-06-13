# Membership Registration Block — Investigation Report

**Number investigated (raw):** `+1 (646) 574-8266` → normalized digits `6465748266` / `16465748266` → masked form `64****8266`, area_code `+1`, tenant `LKUS`
**Mode:** read-only (SELECT/SHOW/INFORMATION_SCHEMA only). No writes performed.
**Date:** 2026-06-13
**Analyst:** DBA/Infra (read-only production investigation via mcp-db-gateway)

---

## VERDICT: ✅ NOT BLACKLISTED — blocker is a duplicate/existing-account collision (high-confidence lead; one residual confirmation step)

The customer's phone is **definitively not on any blacklist.** The registration failure is almost certainly the **unique-constraint collision** on an already-registered account — there are already **two active LKUS accounts in this number's exact mask bucket**, and every other registration gate is ruled out.

---

## Phase 1 — Blacklist check (PRIMARY QUESTION): NEGATIVE

**Risk-control blacklist** `luckyus_iriskcontrolservice.t_blacklist` (黑名单表). `content` stores plaintext E.164 numbers; `type=3` is the phone list (1393 entries). No active-flag column → presence = active.

```sql
SELECT id,type,content,remark,source,create_time,create_name,tenant
FROM luckyus_iriskcontrolservice.t_blacklist
WHERE RIGHT(REGEXP_REPLACE(content,'[^0-9]',''),10) = '6465748266'
   OR REGEXP_REPLACE(content,'[^0-9]','') IN ('6465748266','16465748266');   -- 0 rows
```

- **0 matches.** Reinforcing evidence: **0 of the 1393 type=3 entries even start with `+1`** — the blacklist is exclusively non-US fraud numbers (e.g. `+62…`, `+227…`, `+998…`), and entries explicitly carry the remark *"非美+1区号"* (non-US area code). A US `+1` number being on this list is structurally not how it's populated.
- The 3 rows containing the substring "8266" are Indonesian `+62 88…` numbers (Aug-2025 anti-fraud sweep) — not this number.

**Second blacklist table** `luckyus_sales_marketing.t_contact_blacklist` / `_detail` (触达黑名单 = marketing contact-suppression): keyed by `user_no`, not phone, and governs marketing message delivery — **cannot block a new registration.** Not applicable.

→ **Phone is not blacklisted.**

## Phase 2 — The actual blocker

### (a) Existing ACTIVE account holding this phone — POSITIVE (leading cause)

`salescrm.t_user` enforces registration uniqueness via `UNIQUE KEY (phone_no_encryption, area_code, tenant)`. The phone is stored **encrypted + masked** (`mask_phone_no` = first2`****`last4).

```sql
SELECT id,user_no,status,origin,area_code,mask_phone_no,is_bind_phone,create_time,tenant
FROM luckyus_sales_crm.t_user
WHERE mask_phone_no='64****8266' AND area_code='+1';
```

| id | user_no | status | created | modified |
|----|---------|--------|---------|----------|
| 3796808 | 3584944404481 | **1 (active)** | 2025-06-20 | 2025-06-20 |
| 3933873 | 3617636263937 | **1 (active)** | 2025-12-22 | 2026-03-27 |

Two active accounts already occupy this number's mask+area+tenant bucket.

### (b) Soft-deleted / deactivated account holding the phone — NEGATIVE

`t_user_deactivate` (会员注销表) has no `64…8266` in `+1`. `t_user_change_phone_history` (49 rows) shows the number was never a prior number swapped away.

### (c) Risk / region / velocity gating — NEGATIVE

`t_rms_engine_block_strategy` rules apply only to `LKUS_physical_order_create` and `LKUS_payment` (post-order fraud circuit-breakers), **not registration.** No region gate exists; `+1` is the dominant `area_code` across the user base, so US registration is permitted.

### (d) Registration error log — NOT RETRIEVABLE

CloudWatch holds only RDS slow-query / API-Gateway logs (no app logs); no Loki datasource is connected. The app-side registration error line could not be pulled through available read-only tooling.

---

## The one honest caveat

`phone_no_encryption` is a deterministic 24-char cipher (`security_version=1`) and **every plaintext phone in the DB is masked by design.** The mask `64****8266` spans 10,000 possible numbers, and the two rows above are necessarily two *different* numbers (the unique key forbids duplicates). So from the database alone I can confirm the bucket is occupied but **cannot prove byte-for-byte that one of these two IS `+16465748266`** — that requires encrypting the input with the app's key. Given blacklist, deactivation, region, and velocity are all eliminated, duplicate registration is the only remaining standard gate with positive evidence.

---

## Recommended next step (human to action — no writes performed)

1. **App/CS team run the in-app "phone exists" lookup for `+16465748266`** (it encrypts the input and matches `phone_no_encryption` exactly) — or compare the app-side encryption of `+16465748266` against `t_user.phone_no_encryption` for ids `3796808` / `3933873`. An exact match **confirms duplicate registration → the customer already has an account and should log in / recover access, not re-register.**
2. If no exact match, the cause is app/OTP-layer (SMS delivery, OTP validation, app-version/KYC) — pull the registration error code from the auth service's Loki/Grafana app logs (not reachable from this read-only DB session) at the customer's attempt timestamp.

---

## Tables & sources consulted

| Source | Purpose | Result |
|--------|---------|--------|
| `iriskcontrolservice.t_blacklist` | phone blacklist (type=3, plaintext E.164) | clean — no match, 0 US numbers |
| `iriskcontrolservice.t_rms_engine_block_strategy` | risk/velocity rules | order/payment only, not registration |
| `sales_marketing.t_contact_blacklist(_detail)` | marketing suppression | user_no-keyed, not a registration gate |
| `sales_crm.t_user` | active account store + unique key | **2 active accounts in mask bucket** |
| `sales_crm.t_user_deactivate` | deactivated accounts | no match |
| `sales_crm.t_user_change_phone_history` | prior-number swaps | no match |
| `iluckyauthapi` | auth service | sessions only (282 rows); account store is t_user |
| CloudWatch Logs | registration error log | no app logs available |
| Grafana Loki | registration error log | no Loki datasource connected |
