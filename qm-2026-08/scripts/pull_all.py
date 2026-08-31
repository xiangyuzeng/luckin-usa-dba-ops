#!/usr/bin/env python3
"""
QM 2026-08 raw data pull.  READ-ONLY (SELECT only), single serial MCP-SSE session.
Every query is bounded by an explicit time range and carries a LIMIT.
Windows: primary 2026-08 (America/New_York), control 2026-07, trend 2026-01..2026-08.
No store / supplier / module / item list is hard-coded: everything is selected live.
"""
import json, time
from pathlib import Path
from mcpcli import MCPSSEClient

RAW = Path(__file__).resolve().parent.parent / "raw"; RAW.mkdir(exist_ok=True)
QC  = "aws-luckyus-opqualitycontrol-rw"
SRM = "aws-luckyus-scmsrm-rw"
SHOP= "aws-luckyus-opshop-rw"
SO  = "aws-luckyus-salesorder-rw"
DM  = "aws-luckyus-pubdm-rw"

# ---- audit header/report/opportunity, parameterised by month window -------------
def audit_q(a, b):
    return {
 f"audit_headers_{a[:7]}": (QC, f"""
   SELECT d.id AS check_no, d.tenant, d.dept_id, d.large_category_id, d.large_category_name,
          d.check_date, d.status AS submitted, d.deleted, d.process_status,
          d.checker_id, d.checker_name, d.check_time_start, d.check_time_end, d.check_duration,
          d.create_time AS data_create_time, d.creator_name, d.operation_area,
          d.config_snapshot_id, d.appeal_approve_post_code, d.discard_approve_post_code
   FROM luckyus_opqualitycontrol.t_shopcheck_data d
   WHERE d.tenant='LKUS' AND d.check_date>='{a}' AND d.check_date<'{b}'
   ORDER BY d.id LIMIT 2000"""),

 f"audit_reports_{a[:7]}": (QC, f"""
   SELECT r.shopcheck_data_id AS check_no, r.dept_id, r.large_category_id, r.large_category_name,
          r.second_category_id, r.second_category_name, r.shop_level, r.locality_mid,
          r.brand_no, r.cooperation_no, r.check_approach, r.checker_id, r.checker_name,
          r.checker_post_code, r.check_date, r.score, r.score_desc, r.opportunities,
          r.opportunity_desc, r.create_time AS report_create_time, r.modify_time AS report_modify_time,
          r.status AS report_status
   FROM luckyus_opqualitycontrol.t_shopcheck_report r
   WHERE r.tenant='LKUS' AND r.check_date>='{a}' AND r.check_date<'{b}'
   ORDER BY r.shopcheck_data_id LIMIT 2000"""),

 f"audit_opps_{a[:7]}": (QC, f"""
   SELECT o.id AS opp_id, o.shopcheck_data_id AS check_no, o.check_item_id,
          o.remark AS opp_remark, o.status AS opp_status, o.deleted AS opp_deleted,
          o.create_time AS opp_create_time, o.creator_name AS opp_creator,
          o.modify_time AS opp_modify_time, o.modifier_name AS opp_modifier,
          o.first_appeal_detail, o.second_appeal_detail,
          d.dept_id, d.large_category_id, d.large_category_name, d.check_date,
          d.status AS submitted, d.deleted AS data_deleted, d.process_status,
          ic.deduction_type, ic.score_config AS original_score, ic.score_start,
          ic.content AS item_content, ic.tag_id, ic.category_config_id,
          tg.name AS tag_name, leaf.name AS leaf_name, leaf.parent_id AS leaf_parent,
          mod.name AS module_name
   FROM luckyus_opqualitycontrol.t_shopcheck_opportunity o
   JOIN luckyus_opqualitycontrol.t_shopcheck_data d ON o.shopcheck_data_id=d.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_item_config ic ON o.check_item_id=ic.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_tag tg ON ic.tag_id=tg.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_category_config leaf ON ic.category_config_id=leaf.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_category_config mod ON leaf.parent_id=mod.id
   WHERE d.tenant='LKUS' AND d.check_date>='{a}' AND d.check_date<'{b}'
   ORDER BY o.shopcheck_data_id, o.id LIMIT 5000"""),
}

# ---- PQNC, parameterised (UTC bounds a..b cover the NY month plus 4h margin) -----
PQNC_COLS = """
   SELECT p.id AS pqnc_id, p.pqnc_no, p.wms_pqnc_no, p.tenant, p.initiator,
          p.stock_cell_code, p.warehouse_mid, p.spec_mid, p.unit_mid,
          p.discover_problems_time, p.discover_problems_time_period, p.party_name,
          p.batch_no, p.problem_goods_quantity, p.freeze_quantity, p.refrigerate_quantity,
          p.customer_compensation_info, p.problem_goods_retention_status,
          p.foreign_matter_retention_status, p.factory_name, p.problem_description,
          p.value_amount, p.approved_amount, p.settle_currency,
          p.party_of_judgment, p.responsibility, p.party_of_confirm,
          p.supplier_mid, p.fine_detail_no, p.process_method, p.remarks,
          p.status, p.creator_name, p.created_time, p.modifier_name, p.modified_time,
          p.submit_time, p.judgment_time, p.judgment_dept_name, p.complete_time,
          p.delete_flag, p.appealed_flag, p.auto_confirm_flag, p.ship_order_no, p.price
   FROM luckyus_scm_srm.t_pqnc p
   WHERE p.tenant='LKUS' """

def pqnc_q(a, b, tag):
    return {
 f"pqnc_{tag}": (SRM, PQNC_COLS + f"""
     AND p.created_time>='{a}' AND p.created_time<'{b}'
   ORDER BY p.pqnc_no LIMIT 1000"""),
 f"pqnc_detail_{tag}": (SRM, f"""
   SELECT od.id, od.pqnc_id, od.operate_type, od.responsibility, od.supplier_mid,
          od.factory_name, od.one_pqnc_type_code, od.two_pqnc_type_code, od.three_pqnc_type_code,
          od.process_method, od.weights, od.return_reason, od.description, od.remarks,
          od.auto_flag, od.operator_name, od.operator_dept_name, od.operated_time, od.ship_order_no
   FROM luckyus_scm_srm.t_pqnc_operate_detail od
   JOIN luckyus_scm_srm.t_pqnc p ON od.pqnc_id=p.id
   WHERE p.tenant='LKUS' AND p.created_time>='{a}' AND p.created_time<'{b}'
   ORDER BY od.pqnc_id, od.id LIMIT 3000"""),
 f"pqnc_bill_{tag}": (SRM, f"""
   SELECT b.pqnc_id, b.bill_type, b.relate_ticket_no, b.out_stock_cell_code, b.in_stock_cell_code,
          b.ship_batch_no, b.ship_quantity, b.receive_quantity, b.problem_goods_quantity, b.supplier_mid
   FROM luckyus_scm_srm.t_pqnc_relate_bill b
   JOIN luckyus_scm_srm.t_pqnc p ON b.pqnc_id=p.id
   WHERE p.tenant='LKUS' AND p.created_time>='{a}' AND p.created_time<'{b}'
   ORDER BY b.pqnc_id LIMIT 2000"""),
}

Q = {}
Q.update(audit_q("2026-08-01", "2026-09-01"))
Q.update(audit_q("2026-07-01", "2026-08-01"))
# UTC bounds widened 4h either side of the NY month so the TZ edge can be inspected
Q.update(pqnc_q("2026-07-31 00:00:00", "2026-09-01 12:00:00", "aug_wide"))
Q.update(pqnc_q("2026-06-30 00:00:00", "2026-08-01 12:00:00", "jul_wide"))

Q.update({
 # ---- [3] scoring template: every check item + its module, for the LKUS categories -----
 "item_config": (QC, """
   SELECT ic.id AS check_item_id, ic.category_config_id, ic.sort, ic.content AS item_content,
          ic.status AS item_status, ic.deleted AS item_deleted, ic.tag_id,
          ic.deduction_type, ic.score_config, ic.score_start,
          ic.create_time AS item_create_time, ic.modify_time AS item_modify_time,
          tg.name AS tag_name,
          leaf.id AS leaf_id, leaf.name AS leaf_name, leaf.path AS leaf_path,
          leaf.status AS leaf_status, leaf.parent_id AS leaf_parent_id,
          mod.id AS module_id, mod.name AS module_name, mod.parent_id AS module_parent_id,
          root.id AS large_category_id, root.name AS large_category_name,
          root.create_time AS category_create_time, root.modify_time AS category_modify_time,
          root.status AS category_status
   FROM luckyus_opqualitycontrol.t_shopcheck_item_config ic
   JOIN luckyus_opqualitycontrol.t_shopcheck_category_config leaf ON ic.category_config_id=leaf.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_category_config mod ON leaf.parent_id=mod.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_category_config root ON mod.parent_id=root.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_tag tg ON ic.tag_id=tg.id
   WHERE ic.tenant='LKUS' ORDER BY root.id, mod.id, leaf.id, ic.sort LIMIT 3000"""),

 "category_config": (QC, """
   SELECT id, name, parent_id, path, sort, status, check_approach, deleted,
          need_appeal, appeal_approve_post_code, appeal_limit_time_type, appeal_limit_time_data,
          need_improve, allow_multiple_data, discard_approve_post_code,
          create_time, modify_time, remark
   FROM luckyus_opqualitycontrol.t_shopcheck_category_config
   WHERE tenant='LKUS' ORDER BY path, sort LIMIT 2000"""),

 "config_snapshot_meta": (QC, """
   SELECT s.id AS snapshot_id, s.large_category_id, s.create_time AS snapshot_create_time,
          CHAR_LENGTH(s.item_config_array) AS item_json_len,
          COUNT(d.id) AS used_by_checks, MIN(d.check_date) AS first_check, MAX(d.check_date) AS last_check
   FROM luckyus_opqualitycontrol.t_shopcheck_config_snapshot s
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_data d
          ON d.config_snapshot_id=s.id AND d.tenant='LKUS'
   WHERE s.tenant='LKUS' GROUP BY 1,2,3,4 ORDER BY s.id LIMIT 1000"""),

 # discard (作废) flow — pulled unfiltered by tenant so its emptiness for LKUS is evidenced
 "discard_all": (QC, """
   SELECT id, tenant, shopcheck_data_id, approve, pre_node_id, reason, applicant_post_code,
          remark, approve_time, creator_name, create_time, modifier_name, modify_time
   FROM luckyus_opqualitycontrol.t_shopcheck_discard ORDER BY id LIMIT 500"""),

 # ---- [4] store master ------------------------------------------------------------
 "stores": (SHOP, """
   SELECT id, dept_id, shop_no, shop_name, dept_name, status, shop_level, operation_area,
          set_up_time, shut_up_time, off_time, close_type, time_zone,
          country_name, administrative_area_name, locality_name, sublocality_name,
          address, manager_name, create_time, modify_time, test_flag, tenant
   FROM luckyus_opshop.t_shop_info WHERE tenant='LKUS' ORDER BY shop_no LIMIT 1000"""),

 # ---- [5] PQNC master data ---------------------------------------------------------
 "suppliers": (SRM, """
   SELECT mid AS supplier_mid, name AS supplier_name, sup_class, sup_nature, status,
          nc_code, nc_type, business_source_mid, created_time, creator_name, modified_time
   FROM luckyus_scm_srm.t_mdm_supplier WHERE tenant='LKUS' ORDER BY created_time LIMIT 1000"""),

 "goods_spec": (DM, """
   SELECT gs.mid AS spec_mid, gs.name AS spec_name, gs.goods_mid,
          g.name AS goods_name, g.large_class_mid, g.small_class_mid,
          lc.name AS large_class_name, sc.name AS small_class_name
   FROM luckyus_pub_dm.t_mdm_goods_spec gs
   LEFT JOIN luckyus_pub_dm.t_mdm_goods g ON gs.goods_mid=g.mid AND g.tenant=gs.tenant
   LEFT JOIN luckyus_pub_dm.t_mdm_goods_large_class lc ON g.large_class_mid=lc.mid AND lc.tenant=gs.tenant
   LEFT JOIN luckyus_pub_dm.t_mdm_goods_small_class sc ON g.small_class_mid=sc.mid AND sc.tenant=gs.tenant
   WHERE gs.tenant='LKUS' ORDER BY gs.mid LIMIT 3000"""),

 "stock_cells": (DM, """
   SELECT code AS stock_cell_code, name AS stock_cell_name, type, status, locality_mid, dept_id
   FROM luckyus_pub_dm.t_stock_cell WHERE tenant='LKUS' ORDER BY code LIMIT 1000"""),

 "units": (DM, """
   SELECT mid AS unit_mid, name AS unit_name FROM luckyus_pub_dm.t_mdm_unit
   WHERE tenant='LKUS' ORDER BY mid LIMIT 500"""),

 "localities": (DM, """
   SELECT mid AS locality_mid, name AS locality_name FROM luckyus_pub_dm.t_mdm_locality
   WHERE tenant='LKUS' ORDER BY mid LIMIT 500"""),

 "pqnc_type_cfg": (SRM, """
   SELECT t.id, t.pqnc_type_code, t.name, t.level, t.weights, t.status,
          l.language_code, l.language_value
   FROM luckyus_scm_srm.t_pqnc_type t
   LEFT JOIN luckyus_scm_srm.t_pqnc_type_language l ON l.relate_key=t.pqnc_type_code
   WHERE t.tenant='LKUS' OR l.tenant='LKUS' ORDER BY t.pqnc_type_code LIMIT 50"""),

 # ---- [7] supplier / material admission -------------------------------------------
 "enterprise": (SRM, """
   SELECT id, enterprise_code, enterprise_name, type, status, sup_class, nc_type,
          business_scope, submitter_name, submit_time, first_auditor_name, first_audit_time,
          second_auditor_name, second_audit_time, creator_name, created_time,
          modifier_name, modified_time, reject_remark, delete_flag, tenant
   FROM luckyus_scm_srm.t_enterprise ORDER BY created_time LIMIT 200"""),

 "enterprise_qual": (SRM, """
   SELECT q.id, q.enterprise_id, q.qualification_name, q.validity_start, q.validity_end,
          q.validity_long_term_flag, q.status, q.tenant
   FROM luckyus_scm_srm.t_enterprise_qualification q ORDER BY q.id LIMIT 200"""),

 "supplier_qual": (SRM, """
   SELECT id, supplier_id, qualification_name, validity_long_term_flag,
          validity_start, validity_end, status, modified_time
   FROM luckyus_scm_srm.t_supplier_qualification WHERE tenant='LKUS' ORDER BY id LIMIT 500"""),

 "spec_draft_2026": (SRM, """
   SELECT id, mid AS spec_mid, name AS spec_name, goods_mid, audit_status, tenant,
          created_time, creator_name, modified_time, modifier_name
   FROM luckyus_scm_srm.t_mdm_goods_spec_draft
   WHERE tenant='LKUS' AND created_time>='2026-01-01' AND created_time<'2026-09-01'
   ORDER BY created_time LIMIT 1000"""),

 # ---- [6] customer complaints (order comments + CS tickets) ------------------------
 # UTC bounds; NY month = UTC 04:00 on the 1st .. 04:00 on the next 1st
 "order_comments_aug": (SO, """
   SELECT id, order_id, dept_id, user_no, create_time, level, labels, comment_business_type,
          complaint_flag, origin, customer_reply_status, compensation_send_coupon,
          contact_customer, reach_agreement, comment, remark, customer_reply_content
   FROM luckyus_sales_order.t_order_comment
   WHERE tenant='LKUS' AND create_time>='2026-08-01 04:00:00' AND create_time<'2026-09-01 04:00:00'
     AND comment IS NOT NULL AND comment<>'' ORDER BY create_time LIMIT 4000"""),

 "order_comments_jul": (SO, """
   SELECT id, order_id, dept_id, user_no, create_time, level, labels, comment_business_type,
          complaint_flag, origin, customer_reply_status, compensation_send_coupon,
          contact_customer, reach_agreement, comment, remark, customer_reply_content
   FROM luckyus_sales_order.t_order_comment
   WHERE tenant='LKUS' AND create_time>='2026-07-01 04:00:00' AND create_time<'2026-08-01 04:00:00'
     AND comment IS NOT NULL AND comment<>'' ORDER BY create_time LIMIT 4000"""),

 "cs_sheets_aug": (QC, """
   SELECT sheet_no, id, create_time, dept_id, feedback_source, status, create_source,
          l1_biz_type, l2_biz_type, l3_biz_type, comment_type, comment_tag_name,
          order_id, relate_order_category, has_compensated, feedback_detail, comment
   FROM luckyus_opqualitycontrol.t_cs_sheet
   WHERE tenant='LKUS' AND create_time>='2026-08-01 04:00:00' AND create_time<'2026-09-01 04:00:00'
   ORDER BY create_time LIMIT 1000"""),

 "cs_sheets_jul": (QC, """
   SELECT sheet_no, id, create_time, dept_id, feedback_source, status, create_source,
          l1_biz_type, l2_biz_type, l3_biz_type, comment_type, comment_tag_name,
          order_id, relate_order_category, has_compensated, feedback_detail, comment
   FROM luckyus_opqualitycontrol.t_cs_sheet
   WHERE tenant='LKUS' AND create_time>='2026-07-01 04:00:00' AND create_time<'2026-08-01 04:00:00'
   ORDER BY create_time LIMIT 1000"""),

 "cs_biz_types": (QC, """
   SELECT id, code, name, parent_code, path, level, enabled, deleted
   FROM luckyus_opqualitycontrol.t_cs_biz_type_config WHERE tenant='LKUS' AND deleted=0
   ORDER BY path LIMIT 500"""),

 "cs_sources": (QC, """
   SELECT id, code, name, sort, deleted FROM luckyus_opqualitycontrol.t_cs_feedback_source_config
   WHERE tenant='LKUS' ORDER BY sort LIMIT 100"""),

 # ---- [8] trend series (server-side aggregation, Jan..Aug) --------------------------
 "trend_audits": (QC, """
   SELECT DATE_FORMAT(d.check_date,'%Y-%m') ym, d.large_category_id, d.large_category_name,
          d.status AS submitted, d.deleted,
          COUNT(*) n, COUNT(DISTINCT d.dept_id) stores
   FROM luckyus_opqualitycontrol.t_shopcheck_data d
   WHERE d.tenant='LKUS' AND d.check_date>='2026-01-01' AND d.check_date<'2026-09-01'
   GROUP BY 1,2,3,4,5 ORDER BY 1,2 LIMIT 500"""),

 "trend_pqnc": (SRM, """
   SELECT DATE_FORMAT(p.created_time,'%Y-%m') ym, p.status, p.delete_flag, p.responsibility,
          COUNT(*) n, ROUND(SUM(COALESCE(p.value_amount,0)),2) value_amount
   FROM luckyus_scm_srm.t_pqnc p
   WHERE p.tenant='LKUS' AND p.created_time>='2026-01-01' AND p.created_time<'2026-09-01'
   GROUP BY 1,2,3,4 ORDER BY 1,2,4 LIMIT 500"""),

 "trend_pqnc_type": (SRM, """
   SELECT DATE_FORMAT(p.created_time,'%Y-%m') ym, od.one_pqnc_type_code,
          COUNT(DISTINCT p.id) n
   FROM luckyus_scm_srm.t_pqnc p
   LEFT JOIN luckyus_scm_srm.t_pqnc_operate_detail od
          ON od.pqnc_id=p.id AND od.operate_type=1
   WHERE p.tenant='LKUS' AND p.delete_flag=0
     AND p.created_time>='2026-01-01' AND p.created_time<'2026-09-01'
   GROUP BY 1,2 ORDER BY 1,2 LIMIT 200"""),

 "trend_comments": (SO, """
   SELECT DATE_FORMAT(CONVERT_TZ(create_time,'+00:00','-04:00'),'%Y-%m') ym,
          COUNT(*) n, SUM(CASE WHEN complaint_flag=1 THEN 1 ELSE 0 END) flagged
   FROM luckyus_sales_order.t_order_comment
   WHERE tenant='LKUS' AND create_time>='2026-01-01 04:00:00' AND create_time<'2026-09-01 04:00:00'
   GROUP BY 1 ORDER BY 1 LIMIT 20"""),

 "trend_cs": (QC, """
   SELECT DATE_FORMAT(CONVERT_TZ(create_time,'+00:00','-04:00'),'%Y-%m') ym,
          l1_biz_type, COUNT(*) n, COUNT(DISTINCT dept_id) stores
   FROM luckyus_opqualitycontrol.t_cs_sheet
   WHERE tenant='LKUS' AND create_time>='2026-01-01 04:00:00' AND create_time<'2026-09-01 04:00:00'
   GROUP BY 1,2 ORDER BY 1,2 LIMIT 500"""),

 "trend_suppliers": (SRM, """
   SELECT DATE_FORMAT(created_time,'%Y-%m') ym, sup_class, nc_type, COUNT(*) n
   FROM luckyus_scm_srm.t_mdm_supplier
   WHERE tenant='LKUS' AND created_time>='2026-01-01' AND created_time<'2026-09-01'
   GROUP BY 1,2,3 ORDER BY 1 LIMIT 300"""),
})

def main():
    c = MCPSSEClient(timeout=240); c.start(); c.initialize()
    mid = 1000; log = {}
    for name, (server, sql) in Q.items():
        mid += 1
        t0 = time.time()
        out = c.query(server, sql, mid=mid)
        rows = out.get("rows")
        if rows is None:
            print(f"[pull] {name:26s} !! {str(out)[:200]}")
            log[name] = {"server": server, "error": str(out)[:400], "sql": sql}
            continue
        (RAW / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        log[name] = {"server": server, "rows": len(rows), "sec": round(time.time()-t0, 2), "sql": sql}
        print(f"[pull] {name:26s} -> {len(rows):5d} rows  ({time.time()-t0:.1f}s)")
        time.sleep(0.4)          # rate-limit: keep the gateway to well under 3 q/s
    (RAW / "_pull_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    c.stop(); print("DONE")

main()
