#!/usr/bin/env python3
"""
Cross-check the DB pull (raw/pqnc_july.json) against the business-system export
`/app/reports/PQNC 2026-07.xlsx`, so every PQNC figure in the deck is provably
identical to what the SRM system exports.

Run:  qmvenv/bin/python verify_vs_xlsx.py        (needs openpyxl)

The export is NOT a plain "created in July" list — it also carries records whose
creation is in June but whose judgment landed in July.  We therefore compare on
the deck's locked period basis (created_time in July) and report the out-of-period
rows separately instead of silently folding them in.
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("need openpyxl:  python3 -m venv qmvenv && qmvenv/bin/pip install openpyxl python-pptx")

HERE = Path(__file__).resolve().parent
XLSX = HERE.parent / "PQNC 2026-07.xlsx"
RAW  = HERE / "raw"

KEY = "Product quality unqualified order number"
# xlsx "Judgment Result" -> t_pqnc.responsibility
JUDGMENT_TO_RESP = {
    "Procurement Supplier Responsibility":                   1,
    "Warehousing logistics service provider responsibility":  2,
    "Store Responsibility":                                   3,
    "Joint responsibility of suppliers and warehousing":       4,
    "irresponsibility":                                       6,
}
RESP_LABEL = {1: "Supplier 供应商", 2: "Warehouse 仓储", 3: "Store 门店",
              4: "Joint 共担", 5: "Unclear 未明确", 6: "Unclear 未明确"}

FAIL = []
def check(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        FAIL.append(msg)


def load_xlsx():
    ws = openpyxl.load_workbook(XLSX, data_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h).strip() if h is not None else "" for h in rows[0]]
    return [dict(zip(hdr, r)) for r in rows[1:]
            if any(v is not None and str(v).strip() for v in r)]


def main():
    xls = load_xlsx()
    jul = {r["pqnc_no"]: r for r in json.loads((RAW / "pqnc_july.json").read_text())}
    jun = {r["pqnc_no"]: r for r in json.loads((RAW / "pqnc_june.json").read_text())}

    x_jul = {r[KEY]: r for r in xls if str(r["Creation Time"])[:7] == "2026-07"}
    x_out = [r for r in xls if str(r["Creation Time"])[:7] != "2026-07"]

    print(f"\nexport rows              : {len(xls)}")
    print(f"  created in 2026-07     : {len(x_jul)}   <- deck period basis")
    print(f"  created outside 2026-07: {len(x_out)}   <- judged in July, counted in their own month")
    print(f"DB pull raw/pqnc_july    : {len(jul)}\n")

    print("[1] record-set identity (created_time in July)")
    check(set(x_jul) == set(jul),
          f"export July set == DB July set  (only-in-export={sorted(set(x_jul)-set(jul))}, "
          f"only-in-DB={sorted(set(jul)-set(x_jul))})")

    print("\n[2] responsibility judgment agrees row-by-row")
    mism = [(k, x_jul[k]["Judgment Result"], jul[k]["resp_code"])
            for k in set(x_jul) & set(jul)
            if JUDGMENT_TO_RESP.get(str(x_jul[k]["Judgment Result"]).strip()) != jul[k]["resp_code"]]
    check(not mism, f"judgment result == responsibility code for all rows  (mismatches={mism[:5]})")

    print("\n[3] goods value agrees row-by-row (2dp)")
    vm = [(k, x_jul[k]["Amount of goods value"], jul[k]["value_amount"])
          for k in set(x_jul) & set(jul)
          if round(float(x_jul[k]["Amount of goods value"] or 0), 2)
             != round(float(jul[k]["value_amount"] or 0), 2)]
    check(not vm, f"value_amount matches for all rows  (mismatches={vm[:5]})")

    x_val = round(sum(float(r["Amount of goods value"] or 0) for r in x_jul.values()), 2)
    d_val = round(sum(float(r["value_amount"] or 0) for r in jul.values()), 2)
    check(x_val == d_val, f"July total goods value  export ${x_val:,.2f} == DB ${d_val:,.2f}")

    print("\n[4] PQNC type (Major=food safety / Minor=general defect)")
    x_type = Counter("Major" if str(r["PQNC type"]).strip() == "Major"
                     else "Minor" if str(r["PQNC type"]).strip() == "Minor"
                     else "blank" for r in x_jul.values())
    d_type = Counter({"0003": "Major", "0004": "Minor"}.get(r["one_pqnc_type_code"], "blank")
                     for r in jul.values())
    check(x_type == d_type, f"type mix  export {dict(x_type)} == DB {dict(d_type)}")

    print("\n[5] responsibility mix (the numbers that reach the deck)")
    mix = Counter(jul[k]["resp_code"] for k in jul)
    for code in sorted(mix):
        rows = [r for r in jul.values() if r["resp_code"] == code]
        print(f"       {RESP_LABEL.get(code, code):18s} {len(rows):3d} 起   "
              f"${sum(float(r['value_amount'] or 0) for r in rows):>9,.2f}")
    print(f"       {'TOTAL':18s} {len(jul):3d} 起   ${d_val:>9,.2f}")

    print("\n[6] out-of-period rows carried by the export (created ≠ July)")
    for r in sorted(x_out, key=lambda r: str(r["Creation Time"])):
        n = r[KEY]
        print(f"       {n}  created {str(r['Creation Time'])[:10]}  judged {str(r['Judgment Time'])[:10]}  "
              f"{'in June pull ✓' if n in jun else 'NOT in June pull ✗'}")
    check(all(r[KEY] in jun for r in x_out),
          "every out-of-period export row is already counted in its own month's pull")

    if not FAIL:
        # Fields the deck needs that t_pqnc does not carry as text (store name,
        # goods name).  Emitted only once the export is proven identical to the
        # pull, so build_deck.py can stay a plain JSON reader.
        enrich = {r[KEY]: {"store":  r["Inventory Unit Name"],
                           "store_code": r["No. of inventory holding facility"],
                           "goods":  r["Specific Goods Name"],
                           "batch":  r["Batch number/production date"],
                           "judgment_result": r["Judgment Result"],
                           "judgment_desc":   r["Judgment Description"]}
                  for r in x_jul.values()}
        (RAW / "xlsx_enrich.json").write_text(
            json.dumps(enrich, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nwrote raw/xlsx_enrich.json ({len(enrich)} rows)")

    print("\n" + ("ALL CHECKS PASSED" if not FAIL else f"{len(FAIL)} CHECK(S) FAILED"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
