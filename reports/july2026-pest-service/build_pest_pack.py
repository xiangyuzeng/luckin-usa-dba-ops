#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
July-2026 pest-control (Orkin) service-report data pack.

Input : reports/July Service Report.zip  — 21 per-store PDF service reports
Output: july2026_pest_visits.csv       one row per store visit
        july2026_pest_observations.csv one row per observation block
        july2026_pest_products.csv     one row per product applied
        july2026_pest_datapack.json    everything, for the deck builder
        july2026_pest_datapack.md      human-readable summary
        july2026_pest_validation.txt   parse coverage + anomalies

Store identity: matched on the SERVICE ADDRESS house number against
july2026-qa-inspection/july2026_store_master.csv, so pest data lines up with the
QA store names. House numbers are unique across the 21 active NYC stores.
(Do NOT use the `us000NN@luckincoffee.us` recipients — `us00022@` is a shared
distribution address that appears on almost every report, so it identifies nothing.)

Two observation layouts appear in the wild and both are parsed:
  A  "Location: Common Area(s)"            key and value on one line
  B  "Observation" / "Activity - Dead"     key on its own line, value on the next

A report may also carry an "OPEN ACTIONS FROM PREVIOUS SERVICE" section — items
rolled over from the prior month, each with its own "Date Entered". Those are
parsed separately into july2026_pest_open_actions.csv and are NOT counted as July
observations; folding them in would double-count June's findings.

Run: qmvenv/bin/python build_pest_pack.py   (needs pypdf)
"""
import csv, json, re, sys, zipfile, io
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("need pypdf:  qmvenv/bin/pip install pypdf")

HERE = Path(__file__).resolve().parent
ZIP  = HERE.parent / "July Service Report.zip"
MASTER = HERE.parent / "july2026-qa-inspection" / "july2026_store_master.csv"

FIELD = {
    "address":     r"Address\s+(.+?)\s*\n",
    "program_id":  r"Program ID\s+(\d+)",
    "account":     r"Account #\s+(\d+)",
    "tech":        r"YOUR ORKIN PRO\s*\n\s*(.+?)\s*\n",
    "license":     r"LICENSE #\s*(\S+)",
    "svc_date":    r"Date of Service\s+(\d{1,2}/\d{1,2}/\d{4})",
    "svc_type":    r"Service Type\s+(.+?)\s*\n",
    "event_type":  r"Service Event Type\s+(.+?)\s*\n",
    "time_in":     r"Time In\s+(\d{1,2}:\d{2}\s*[AP]M)",
    "time_out":    r"Time Out\s+(\d{1,2}:\d{2}\s*[AP]M)",
    "invoice":     r"Invoice / Service Report #\s*(\d+)",
    "amount":      r"Today's Service \$\s*([\d.,]+)",
    "tax":         r"Tax\s+([\d.,]+)",
    "total_due":   r"Total Amount Due\s+([\d.,]+)",
}
OBS_KEYS = ["Location", "Observation", "Pest Type", "Recommendation", "Responsibility", "Status"]
OPEN_HDR = "OPEN ACTIONS FROM PREVIOUS SERVICE"
# in the open-actions block Orkin merges two column headers onto one line
OPEN_KEYS = {"Observation": "observation", "Recommendation": "recommendation",
             "Date Entered": "date_entered", "Pest Type Status": "status",
             "Zone Name Responsibility": "responsibility"}


def house_no(addr):
    """Leading house number of a street address, normalised ('052' -> '52')."""
    m = re.match(r"\s*(\d+)", addr or "")
    return str(int(m.group(1))) if m else ""


def load_master():
    """house number -> store row, restricted to real operating stores."""
    m = {}
    with MASTER.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r["status"].startswith("active") or "Test" in r["store_name"]:
                continue
            h = house_no(r["address"])
            if h and h in m:
                raise SystemExit(f"ambiguous house number {h}: {m[h]['store_code']} vs {r['store_code']}")
            if h:
                m[h] = r
    return m


def one(rx, text, default=""):
    m = re.search(rx, text, re.S)
    return m.group(1).strip() if m else default


def parse_observations(text):
    """Blocks between TODAY'S OBSERVATIONS and PRODUCT DETAILS, one dict each.

    Handles both layouts (see module docstring). A repeated key starts a new
    block, so the key order does not have to be stable between reports.
    """
    seg = text.split("TODAY'S OBSERVATIONS")
    if len(seg) < 2:
        return []
    # stop at the carry-over section and at the product table
    body = re.split(r"PRODUCT DETAILS|" + re.escape(OPEN_HDR) + r"|Orkin Pro Signature", seg[1])[0]
    lines = [l.strip() for l in body.split("\n")]
    out, cur, i = [], {}, 0
    while i < len(lines):
        line = lines[i]
        hit = None
        for k in OBS_KEYS:
            if line.startswith(k + ":"):                 # layout A
                hit, val = k, line[len(k) + 1:].strip()
                break
            if line == k:                                # layout B
                nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
                # a bare key followed by another bare key means an empty value
                hit, val = k, ("" if nxt in OBS_KEYS else nxt)
                if val:
                    i += 1
                break
        if hit:
            if hit in cur:                               # repeated key -> new block
                out.append(cur); cur = {}
            cur[hit] = val
        i += 1
    if cur:
        out.append(cur)
    return [{k: o.get(k, "") for k in OBS_KEYS} for o in out if o.get("Observation")]


def parse_open_actions(text):
    """Carry-over items from the previous service, each with its own Date Entered."""
    if OPEN_HDR not in text:
        return []
    body = re.split(r"PRODUCT DETAILS|Orkin Pro Signature", text.split(OPEN_HDR)[1])[0]
    lines = [l.strip() for l in body.split("\n")]
    out, cur, i = [], {}, 0
    while i < len(lines):
        k = lines[i]
        if k in OPEN_KEYS:
            val = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if val in OPEN_KEYS:
                val = ""
            else:
                i += 1
            fld = OPEN_KEYS[k]
            if fld in cur:
                out.append(cur); cur = {}
            cur[fld] = val
        i += 1
    if cur:
        out.append(cur)
    cols = ["observation", "recommendation", "date_entered", "status", "responsibility"]
    return [{c: o.get(c, "") for c in cols} for o in out if o.get("observation")]


def parse_products(text):
    seg = text.split("PRODUCT DETAILS")
    if len(seg) < 2:
        return []
    body = seg[1]
    names = re.findall(r"Product Name\s*\n\s*(.+?)\s*\n", body)
    qtys  = re.findall(r"Quantity\s*\n\s*(.+?)\s*\n", body)
    tgts  = re.findall(r"Target Pests\s*\n\s*(.+?)\s*\n", body)
    out = []
    for i, n in enumerate(names):
        out.append({"product": n,
                    "quantity": qtys[i] if i < len(qtys) else "",
                    "target_pests": tgts[i] if i < len(tgts) else ""})
    return out


def main():
    master = load_master()
    visits, observations, products, open_actions, warn = [], [], [], [], []

    with zipfile.ZipFile(ZIP) as z:
        pdfs = sorted(n for n in z.namelist() if n.lower().endswith(".pdf"))
        for name in pdfs:
            label = re.match(r".*?/(\d+)", name)
            label = label.group(1) if label else Path(name).stem
            text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(z.read(name))).pages)

            rec = {k: one(rx, text) for k, rx in FIELD.items()}
            rec["file_label"] = label
            h = house_no(rec["address"]) or house_no(label)
            row = master.get(h, {})
            rec["house_no"]   = h
            rec["store_code"] = row.get("store_code", "")
            rec["store_name"] = row.get("store_name", "")
            if not row:
                warn.append(f"{label}: address '{rec['address']}' (house {h or '?'}) "
                            f"not matched to any active store")

            obs = parse_observations(text)
            if not obs:
                warn.append(f"{label}: no observation block parsed")
            dup = len(obs) - len({tuple(o.values()) for o in obs})
            if dup:
                warn.append(f"{label}: source PDF repeats {dup} identical observation block(s) "
                            f"— kept as-is, see distinct_observations")
            rec["observations"] = len(obs)
            rec["distinct_observations"] = len({tuple(o.values()) for o in obs})
            rec["has_live_activity"] = any("Live" in o["Observation"] for o in obs)
            rec["pest_types"] = "; ".join(sorted({o["Pest Type"] for o in obs if o["Pest Type"]}))
            rec["comments"] = re.sub(r"\s+", " ",
                one(r"COMMENTS ABOUT TODAY'S SERVICE\s*\n(.*?)TODAY'S OBSERVATIONS", text)).strip()
            visits.append(rec)

            for o in obs:
                observations.append({"file_label": label, "store_code": rec["store_code"],
                                     "store_name": rec["store_name"], "svc_date": rec["svc_date"],
                                     **{k.lower().replace(" ", "_"): o[k] for k in OBS_KEYS}})
            for pr in parse_products(text):
                products.append({"file_label": label, "store_code": rec["store_code"],
                                 "store_name": rec["store_name"], **pr})
            for oa in parse_open_actions(text):
                open_actions.append({"file_label": label, "store_code": rec["store_code"],
                                     "store_name": rec["store_name"], "svc_date": rec["svc_date"], **oa})
            rec["open_actions"] = sum(1 for o in open_actions if o["file_label"] == label)

    # ---------- derived ----------
    # svc_date is m/d/Y text — sort as dates, not strings, or 7/9 > 7/11
    svc_dates = [datetime.strptime(v["svc_date"], "%m/%d/%Y") for v in visits if v["svc_date"]]
    live   = [o for o in observations if "Live" in o["observation"]]
    dead   = [o for o in observations if "Dead" in o["observation"]]
    # Orkin uses two labels for the same outcome — "No Activity" and the compound
    # "No Activity / Inspection Provided" (verified against the source PDFs).
    noact  = [o for o in observations if o["observation"].strip().startswith("No Activity")]
    prev   = [o for o in observations if o["observation"].strip() == "Preventative"]
    facil  = [o for o in observations
              if o["observation"].strip() in ("Drain Issue", "Gaps", "Moisture Accumulation")]
    by_pest  = Counter(o["pest_type"] for o in observations if o["pest_type"])
    by_loc   = Counter(l.strip() for o in observations for l in o["location"].split(",") if l.strip())
    live_by_store = Counter(o["store_name"] or o["file_label"] for o in live)
    unresolved = [o for o in observations if o["status"].strip().lower() != "resolved"]

    derived = {
        "visits": len(visits),
        "stores_identified": len({v["store_code"] for v in visits if v["store_code"]}),
        "date_range": [d.strftime("%m/%d/%Y") for d in
                       (min(svc_dates), max(svc_dates))] if svc_dates else ["", ""],
        "observations": len(observations),
        "live": len(live), "dead": len(dead), "no_activity": len(noact),
        "preventative": len(prev), "facility": len(facil),
        "stores_with_live": len({o["store_code"] or o["file_label"] for o in live}),
        "by_observation": Counter(o["observation"] for o in observations).most_common(),
        "by_pest_type": by_pest.most_common(),
        "by_location": by_loc.most_common(),
        "live_by_store": live_by_store.most_common(),
        "unresolved": unresolved,
        "spend_total": round(sum(float(v["total_due"].replace(",", "") or 0) for v in visits), 2),
        "products_used": Counter(p["product"] for p in products).most_common(),
        "technicians": Counter(v["tech"] for v in visits).most_common(),
        "open_actions": len(open_actions),
        "open_actions_unresolved": sum(1 for o in open_actions
                                       if o["status"].strip().lower() != "resolved"),
        "open_actions_by_type": Counter(o["observation"] for o in open_actions).most_common(),
    }

    # ---------- write ----------
    def dump(fn, rows, cols):
        with (HERE/fn).open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader(); w.writerows(rows)
        print(f"  {fn:38s} {len(rows):3d} rows")

    dump("july2026_pest_visits.csv", visits,
         ["file_label","house_no","store_code","store_name","address","svc_date","svc_type","event_type",
          "time_in","time_out","tech","license","invoice","amount","tax","total_due",
          "observations","distinct_observations","open_actions","has_live_activity","pest_types","program_id","comments"])
    dump("july2026_pest_observations.csv", observations,
         ["file_label","store_code","store_name","svc_date","location","observation",
          "pest_type","recommendation","responsibility","status"])
    dump("july2026_pest_products.csv", products,
         ["file_label","store_code","store_name","product","quantity","target_pests"])
    dump("july2026_pest_open_actions.csv", open_actions,
         ["file_label","store_code","store_name","svc_date","observation","recommendation",
          "date_entered","status","responsibility"])

    pack = {"source": "reports/July Service Report.zip (Orkin per-store PDFs)",
            "period": "2026-07", "derived": derived, "visits": visits,
            "observations": observations, "products": products, "open_actions": open_actions}
    (HERE/"july2026_pest_datapack.json").write_text(
        json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")

    md = [f"# 7 月虫害防控（Orkin）服务数据包\n",
          f"来源：`reports/July Service Report.zip` — {len(visits)} 份门店服务报告",
          f"门店识别：按服务地址门牌号匹配 `july2026_store_master.csv`"
          f"（`us00022@` 是共用收件人，不能用作门店标识）\n",
          f"- 服务门店：{derived['stores_identified']} 家，每店 1 次月度例行（PC Standard - Monthly）",
          f"- 服务日期：{derived['date_range'][0]} ~ {derived['date_range'][1]}",
          f"- 本月观察记录：{derived['observations']} 条 —— **活体 {derived['live']}**、"
          f"死体 {derived['dead']}、无活动 {derived['no_activity']}、"
          f"预防性处理 {derived['preventative']}、设施类 {derived['facility']}"
          f"（排水/缝隙/积水）",
          f"- 出现活体的门店：{derived['stores_with_live']} 家",
          f"- 本月未闭环观察项：{len(unresolved)} 条",
          f"- 6 月结转未闭环项：{derived['open_actions_unresolved']} / {derived['open_actions']} 条",
          f"- 服务费合计：${derived['spend_total']:,.2f}\n",
          "## 观察类型分布\n", "| 观察结果 | 次数 |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in derived["by_observation"]]
    md += ["\n## 虫害类型分布（仅有虫害类型的记录）\n", "| 类型 | 次数 |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in derived["by_pest_type"]]
    md += ["\n## 发现位置分布\n", "| 位置 | 次数 |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in derived["by_location"]]
    md += ["\n## 活体发现门店\n", "| 门店 | 次数 |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in derived["live_by_store"]]
    md += ["\n## 未闭环项（本月 + 6 月结转）\n",
           "| 门店 | 来源 | 观察 | 建议 | 责任方 | 状态 |", "|---|---|---|---|---|---|"]
    md += [f"| {o['store_name']} | 本月 | {o['observation']} | {o['recommendation']} "
           f"| {o['responsibility']} | {o['status']} |" for o in unresolved]
    md += [f"| {o['store_name']} | 结转 {o['date_entered']} | {o['observation']} | {o['recommendation']} "
           f"| {o['responsibility']} | {o['status']} |"
           for o in open_actions if o["status"].strip().lower() != "resolved"]
    (HERE/"july2026_pest_datapack.md").write_text("\n".join(md)+"\n", encoding="utf-8")

    val = [f"parsed {len(visits)}/{len(pdfs)} PDFs",
           f"observations parsed: {len(observations)}",
           f"products parsed: {len(products)}",
           f"stores identified by address: {derived['stores_identified']}/{len(visits)}",
           f"visits with no observation block: {sum(1 for v in visits if v['observations']==0)}",
           f"July observations not marked Resolved: {len(unresolved)}",
           f"carry-over (open) actions from June: {derived['open_actions']}, "
           f"still unresolved {derived['open_actions_unresolved']}", ""]
    val += ["WARNINGS:"] + ([f"  - {w}" for w in warn] or ["  none"])
    (HERE/"july2026_pest_validation.txt").write_text("\n".join(val)+"\n", encoding="utf-8")
    print("\n".join(val))


if __name__ == "__main__":
    main()
