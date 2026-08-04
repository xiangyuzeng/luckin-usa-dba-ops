#!/usr/bin/env python3
"""
Pull July-2026 QM Monthly Report datasets (PQNC + supplier) to raw/*.json via MCP-SSE.
READ-ONLY (SELECT only). Reuses the March-validated PQNC filter set.

Filter set (locked): tenant='LKUS' AND delete_flag=0 AND status IN (4,5),
                     period by created_time, operate_type=1 dedup via MIN(id) per pqnc_id.
NOTE: June is RE-PULLED with the same as-of-today filter so the MoM delta is
      apples-to-apples. The published June deck figure (65) was a 2026-07-01
      point-in-time snapshot; re-judgments and deletions since then move it.
      The same applies to July: a 2026-08-03 15:5x pull returned 46 because the
      13-case Cream-O-Land spoilage cluster was still awaiting judgment; it was
      judged at 2026-08-03 ~16:00 and the July total settled at 59.
      Always re-pull before rebuilding, then run verify_vs_xlsx.py.
TZ:   t_pqnc timestamps are UTC; the SRM UI/export renders them in America/New_York.
      Period bounds here are UTC. Verified for Jul-2026: zero rows fall in the
      00:00–04:00 UTC boundary window at either month edge, so both bases agree.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "july2026-qa-inspection"))
from mcp_sse_pull import MCPSSEClient

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"; RAW.mkdir(exist_ok=True)
SRM = "aws-luckyus-scmsrm-rw"

PQNC_COLS = """
   SELECT p.id AS pqnc_id, p.pqnc_no, p.created_time, p.discover_problems_time,
          p.status, p.initiator, p.discover_problems_time_period, p.party_name,
          p.factory_name, p.problem_description, p.problem_goods_quantity AS problem_qty,
          p.value_amount, p.approved_amount, p.responsibility AS resp_code,
          p.supplier_mid, p.batch_no, p.appealed_flag,
          p.stock_cell_code, p.judgment_time, p.modified_time,
          (SELECT d.one_pqnc_type_code FROM luckyus_scm_srm.t_pqnc_operate_detail d
            WHERE d.pqnc_id=p.id AND d.operate_type=1 ORDER BY d.id LIMIT 1) AS one_pqnc_type_code,
          (SELECT d.description FROM luckyus_scm_srm.t_pqnc_operate_detail d
            WHERE d.pqnc_id=p.id AND d.operate_type=1 ORDER BY d.id LIMIT 1) AS corrective_desc
   FROM luckyus_scm_srm.t_pqnc p
   WHERE p.tenant='LKUS' AND p.delete_flag=0 AND p.status IN (4,5)
"""

Q = {
 "pqnc_july": (SRM, PQNC_COLS + """
     AND p.created_time>='2026-07-01' AND p.created_time<'2026-08-01'
   ORDER BY p.id"""),

 "pqnc_june": (SRM, PQNC_COLS + """
     AND p.created_time>='2026-06-01' AND p.created_time<'2026-07-01'
   ORDER BY p.id"""),

 # Jan-Jul monthly totals + responsibility split, recomputed on one consistent filter
 "pqnc_trend": (SRM, """
   SELECT DATE_FORMAT(p.created_time,'%Y-%m') AS ym,
          COUNT(*) AS n,
          SUM(CASE WHEN p.responsibility=1 THEN 1 ELSE 0 END) AS supplier,
          SUM(CASE WHEN p.responsibility=2 THEN 1 ELSE 0 END) AS warehouse,
          SUM(CASE WHEN p.responsibility=3 THEN 1 ELSE 0 END) AS store,
          SUM(CASE WHEN p.responsibility=4 THEN 1 ELSE 0 END) AS joint,
          SUM(CASE WHEN p.responsibility NOT IN (1,2,3,4) OR p.responsibility IS NULL THEN 1 ELSE 0 END) AS unknown_reject,
          ROUND(SUM(COALESCE(p.value_amount,0)),2) AS value_amount
   FROM luckyus_scm_srm.t_pqnc p
   WHERE p.tenant='LKUS' AND p.delete_flag=0 AND p.status IN (4,5)
     AND p.created_time>='2026-01-01' AND p.created_time<'2026-08-01'
   GROUP BY ym ORDER BY ym"""),

 # supplier master (supplier_mid -> name), for the supplier-responsibility slide
 "suppliers": (SRM, """
   SELECT mid AS supplier_mid, name AS supplier_name, created_time
   FROM luckyus_scm_srm.t_mdm_supplier
   WHERE tenant='LKUS'
   ORDER BY supplier_mid"""),
}

def main():
    c = MCPSSEClient(timeout=120); c.start(); c.initialize()
    mid = 10
    for name, (server, sql) in Q.items():
        mid += 1
        out = c.query(server, sql, mid=mid)
        rows = out.get("rows", [])
        if not rows and "raw" in out:
            print(f"[pull] {name:14s} !! {str(out)[:200]}")
            continue
        (RAW / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[pull] {name:14s} -> {len(rows):4d} rows")
    c.stop(); print("DONE")

if __name__ == "__main__":
    main()
