import json, time
from pathlib import Path
from mcpcli import MCPSSEClient
RAW = Path(__file__).resolve().parent.parent / "raw"
QC="aws-luckyus-opqualitycontrol-rw"; SRM="aws-luckyus-scmsrm-rw"; DM="aws-luckyus-pubdm-rw"

def opps(a,b):
    return (QC, f"""
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
          mdl.name AS module_name, mdl.id AS module_id
   FROM luckyus_opqualitycontrol.t_shopcheck_opportunity o
   JOIN luckyus_opqualitycontrol.t_shopcheck_data d ON o.shopcheck_data_id=d.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_item_config ic ON o.check_item_id=ic.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_tag tg ON ic.tag_id=tg.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_category_config leaf ON ic.category_config_id=leaf.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_category_config mdl ON leaf.parent_id=mdl.id
   WHERE d.tenant='LKUS' AND d.check_date>='{a}' AND d.check_date<'{b}'
   ORDER BY o.shopcheck_data_id, o.id LIMIT 5000""")

Q={
 "audit_opps_2026-08": opps("2026-08-01","2026-09-01"),
 "audit_opps_2026-07": opps("2026-07-01","2026-08-01"),
 "item_config": (QC, """
   SELECT ic.id AS check_item_id, ic.category_config_id, ic.sort, ic.content AS item_content,
          ic.status AS item_status, ic.deleted AS item_deleted, ic.tag_id,
          ic.deduction_type, ic.score_config, ic.score_start,
          ic.create_time AS item_create_time, ic.modify_time AS item_modify_time,
          tg.name AS tag_name,
          leaf.id AS leaf_id, leaf.name AS leaf_name, leaf.path AS leaf_path,
          leaf.status AS leaf_status, leaf.parent_id AS leaf_parent_id,
          mdl.id AS module_id, mdl.name AS module_name, mdl.parent_id AS module_parent_id,
          root.id AS large_category_id, root.name AS large_category_name,
          root.create_time AS category_create_time, root.modify_time AS category_modify_time,
          root.status AS category_status
   FROM luckyus_opqualitycontrol.t_shopcheck_item_config ic
   JOIN luckyus_opqualitycontrol.t_shopcheck_category_config leaf ON ic.category_config_id=leaf.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_category_config mdl ON leaf.parent_id=mdl.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_category_config root ON mdl.parent_id=root.id
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_tag tg ON ic.tag_id=tg.id
   WHERE ic.tenant='LKUS' ORDER BY root.id, mdl.id, leaf.id, ic.sort LIMIT 3000"""),
 "goods_spec": (DM, """
   SELECT gs.mid AS spec_mid, gs.name AS spec_name, gs.goods_mid,
          g.name AS goods_name, g.large_mid, g.small_mid,
          lc.name AS large_class_name, sc.name AS small_class_name
   FROM luckyus_pub_dm.t_mdm_goods_spec gs
   LEFT JOIN luckyus_pub_dm.t_mdm_goods g ON gs.goods_mid=g.mid AND g.tenant=gs.tenant
   LEFT JOIN luckyus_pub_dm.t_mdm_goods_large_class lc ON g.large_mid=lc.mid AND lc.tenant=gs.tenant
   LEFT JOIN luckyus_pub_dm.t_mdm_goods_small_class sc ON g.small_mid=sc.mid AND sc.tenant=gs.tenant
   WHERE gs.tenant='LKUS' ORDER BY gs.mid LIMIT 3000"""),
 "stock_cells": (DM, """
   SELECT code AS stock_cell_code, name AS stock_cell_name, cell_type, sub_type, status,
          relate_dept_id, storage_dept_id, locality_mid
   FROM luckyus_pub_dm.t_stock_cell WHERE tenant='LKUS' ORDER BY code LIMIT 1000"""),
 "spec_draft_2026": (SRM, """
   SELECT id, mid AS spec_mid, name AS spec_name, goods_mid, draft_status,
          approve_instance_no, current_approve_node, quality_config_status,
          created_time, creator_name, modified_time, modifier_name
   FROM luckyus_scm_srm.t_mdm_goods_spec_draft
   WHERE tenant='LKUS' AND created_time>='2026-01-01' AND created_time<'2026-09-01'
   ORDER BY created_time LIMIT 1000"""),
 "spec_draft_approved_2026": (SRM, """
   SELECT id, mid AS spec_mid, name AS spec_name, goods_mid, draft_status,
          created_time, modified_time, modifier_name
   FROM luckyus_scm_srm.t_mdm_goods_spec_draft
   WHERE tenant='LKUS' AND draft_status IN (4,6)
     AND modified_time>='2026-01-01' AND modified_time<'2026-09-01'
   ORDER BY modified_time LIMIT 1000"""),
 "config_snapshot_meta": (QC, """
   SELECT d.config_snapshot_id AS snapshot_id, d.large_category_id,
          s.create_time AS snapshot_create_time,
          COUNT(*) used_by_checks, MIN(d.check_date) first_check, MAX(d.check_date) last_check
   FROM luckyus_opqualitycontrol.t_shopcheck_data d
   LEFT JOIN luckyus_opqualitycontrol.t_shopcheck_config_snapshot s ON s.id=d.config_snapshot_id
   WHERE d.tenant='LKUS' AND d.check_date>='2026-01-01' AND d.check_date<'2026-09-01'
   GROUP BY 1,2,3 ORDER BY 2,3 LIMIT 500"""),
 # goods large classes = the material-admission categories, pulled live
 "goods_large_class": (DM, """
   SELECT mid, name, status FROM luckyus_pub_dm.t_mdm_goods_large_class
   WHERE tenant='LKUS' ORDER BY mid LIMIT 200"""),
}
c=MCPSSEClient(timeout=240); c.start(); c.initialize(); mid=2000
log=json.loads((RAW/"_pull_log.json").read_text())
for k,(s,sql) in Q.items():
    mid+=1; t0=time.time(); out=c.query(s,sql,mid=mid); rows=out.get("rows")
    if rows is None:
        print(f"[fix] {k:26s} !! {str(out)[:220]}"); log[k]={"server":s,"error":str(out)[:400],"sql":sql}; continue
    (RAW/f"{k}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding="utf-8")
    log[k]={"server":s,"rows":len(rows),"sec":round(time.time()-t0,2),"sql":sql}
    print(f"[fix] {k:26s} -> {len(rows):5d} rows")
    time.sleep(0.4)
(RAW/"_pull_log.json").write_text(json.dumps(log,ensure_ascii=False,indent=1),encoding="utf-8")
c.stop(); print("DONE")
