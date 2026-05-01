#!/usr/bin/env python3
"""Append status=1 vs all-statuses breakdown to the validation output."""
import sys
from collections import defaultdict
sys.path.insert(0, "/app/claude-code-output/april2026-inspection-export")
from build_csvs import HEADERS, TYPE_MAP

months = ["2026-01","2026-02","2026-03","2026-04"]
types  = ["门店自检","QA审计","区经检查"]

all_b = defaultdict(int)
sub_b = defaultdict(int)
for h in HEADERS:
    ym = h["check_date"][:7]
    if ym not in months: continue
    t_zh, _ = TYPE_MAP[h["large_category_id"]]
    all_b[(ym, t_zh)] += 1
    if h["status"] == 1:
        sub_b[(ym, t_zh)] += 1

out_path = "/app/claude-code-output/april2026-inspection-export/april2026_validation_output.txt"
with open(out_path, "a") as f:
    f.write("\n\n" + "="*80 + "\n")
    f.write("ADDITIONAL FINDING: SUBMITTED-ONLY (status=1) vs ALL-STATUSES BREAKDOWN\n")
    f.write("="*80 + "\n")
    f.write("The task brief cites prior-month counts (Jan: 7+5+4=16, Feb: 5+2+0=7, Mar: 12+1+0=13).\n")
    f.write("Those numbers only match when filtering t_shopcheck_data.status=1 (submitted/finalized).\n")
    f.write('Our exports include all rows where deleted=0 (drafts + submitted), per the task rule\n')
    f.write('"DO NOT skip rows or filter out edge cases". Both views below:\n\n')
    f.write(f"{'month':10s} {'type':16s} {'all(deleted=0)':>16s} {'submitted(status=1)':>22s}\n")
    for ym in months:
        for t in types:
            f.write(f"{ym:10s} {t:16s} {all_b[(ym,t)]:>16d} {sub_b[(ym,t)]:>22d}\n")
    f.write("\nAggregate (sum of three types):\n")
    f.write(f"{'month':10s} {'all':>10s} {'submitted':>12s}\n")
    for ym in months:
        a = sum(all_b[(ym,t)] for t in types)
        s = sum(sub_b[(ym,t)] for t in types)
        f.write(f"{ym:10s} {a:>10d} {s:>12d}\n")
    f.write("\nNOTES FOR DOWNSTREAM REPORT LAYER:\n")
    f.write("  - status=1 mirrors what prior monthly reports apparently used.\n")
    f.write("  - all-statuses exposes draft-but-not-submitted activity.\n")
    f.write("  - Drafts (status=0) often represent inspections started but never finalized;\n")
    f.write("    they may signal a data-quality issue worth investigating.\n")
    f.write("  - The CSVs deliberately keep BOTH (no status filter) — the report layer can\n")
    f.write("    project to the desired view.\n")

print("Appended.")
with open(out_path) as f:
    txt = f.read()
print(txt[txt.index("ADDITIONAL FINDING"):])
