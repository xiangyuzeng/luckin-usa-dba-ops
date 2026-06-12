#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build iAdmin 门店排班 (Store Schedule) CSV exports for SCHEDULE_WEEK.

Source data (read-only, pulled via mcp-db-gateway, see extraction_report.md):
  _raw_emp_map.txt   : iehr  t_ehr_employee   -> emp_no|name|property|status
  _raw_schedule.json : opempefficiency t_emp_scheduling (one row per emp/day)
  STORES (below)     : opshop t_shop_info (dept_id -> shop_no/name/status/tz)

Slot model: 48 x 30-min slots per day. slot i covers [i*30, i*30+30) minutes
of LOCAL store time (America/New_York). On-duty (班) = a scheduling segment
overlaps the slot; rest (休) = a rest segment overlaps the slot (overrides 班).
Hours are NOT recomputed from slots — effect_hours/effect_minutes from the DB
are authoritative (rest excluded). See report for the 15-vs-30-min note.
"""
import json, csv, os, io

BASE = os.path.dirname(os.path.abspath(__file__))
WEEK = ["2026-06-08","2026-06-09","2026-06-10","2026-06-11","2026-06-12","2026-06-13","2026-06-14"]

# dept_id -> (shop_no, shop_name, store_status_code, time_zone, internal, open_date)
STORES = {
 1131:("US00000","NJ Test Kitchen",1,"America/New_York",1,"2025-05-09"),
 1127:("US00001","8th & Broadway",1,"America/New_York",0,"2025-06-30"),
 1128:("US00002","28th & 6th",1,"America/New_York",0,"2025-06-30"),
 1140:("US00003","100 Maiden Ln",1,"America/New_York",0,"2025-09-09"),
 20011:("US00004","37th & Broadway",1,"America/New_York",0,"2025-11-20"),
 1141:("US00005","54th & 8th",1,"America/New_York",0,"2025-08-24"),
 20010:("US00006","102 Fulton",1,"America/New_York",0,"2025-08-28"),
 20009:("US00007","108th & Broadway",1,"America/New_York",0,"2026-04-30"),
 20008:("US00008","33rd & 10th",1,"America/New_York",0,"2025-12-01"),
 20016:("US00010","154 Bleecker",1,"America/New_York",0,"2026-04-28"),
 20019:("US00012","16th & 6th",1,"America/New_York",0,"2026-03-23"),
 20022:("US00015","41st & Lexington",1,"America/New_York",0,"2026-04-30"),
 20025:("US00018","40th & 10th",1,"America/New_York",0,"2026-05-20"),
 20026:("US00019","29th & 3rd",1,"America/New_York",0,"2026-04-11"),
 20027:("US00020","21st & 3rd",1,"America/New_York",0,"2026-02-06"),
 20029:("US00022","23rd & 8th",1,"America/New_York",0,"2026-05-20"),
 20031:("US00024","15th & 3rd",1,"America/New_York",0,"2025-12-14"),
 20032:("US00025","221 Grand",1,"America/New_York",0,"2025-12-15"),
 20035:("US00027","52nd & Madison",1,"America/New_York",0,"2026-02-26"),
 20046:("US99998","Shanghai Test Kitchen",1,"America/New_York",1,"2025-11-14"),
 20007:("US99999","NJ Test Kitchen 2",1,"America/New_York",1,"2025-06-26"),
}
PROP_LABEL = {"0":"FT","1":"PT","2":"INTERN","3":"OUTSRC"}
STORE_STATUS_CN = {1:"已开业"}

def hhmm_to_min(s):
    h,m = s.split(":"); return int(h)*60+int(m)

def parse_segments(s):
    """'06:00~14:30,15:00~17:00' -> [(360,870),(900,1020)]; '' -> []"""
    out=[]
    if not s: return out
    for seg in s.split(","):
        seg=seg.strip()
        if not seg or "~" not in seg: continue
        a,b = seg.split("~"); a=hhmm_to_min(a); b=hhmm_to_min(b)
        if b<=a: b+=24*60          # cross-midnight guard (clamped to grid below)
        out.append((a,b))
    return out

def slots_for(segments):
    """set of 30-min slot indices [0,47] overlapped by any segment"""
    s=set()
    for a,b in segments:
        for i in range(48):
            ss=i*30; se=ss+30
            if a<se and b>ss: s.add(i)
    return s

def slot_label(i):
    ss=i*30; se=ss+30
    return "%02d:%02d"%(ss//60,ss%60), "%02d:%02d"%(se//60,se%60)

# ---- load employees ----
emp={}
with io.open(os.path.join(BASE,"_raw_emp_map.txt"),encoding="utf-8") as f:
    for ln in f:
        ln=ln.rstrip("\n")
        if not ln: continue
        no,name,prop,st = ln.split("|")
        emp[no]=(name,prop,st)

# ---- load schedule rows ----
with io.open(os.path.join(BASE,"_raw_schedule.json"),encoding="utf-8") as f:
    raw=json.load(f)
rows=[]
for r in raw["rows"]:
    p=r["line"].split("|")
    # dept|date|emp_no|work_type|source|status|eff_h|eff_min|sched_times|rest_times|crossday
    rows.append(dict(dept=int(p[0]),date=p[1],emp_no=p[2],work_type=p[3],source=p[4],
                     status=int(p[5]),eff_h=float(p[6]),eff_min=(int(p[7]) if p[7] else None),
                     sched=p[8],rest=p[9],crossday=int(p[10])))

ACTIVE=[r for r in rows if r["status"]==1]          # published board
DRAFT =[r for r in rows if r["status"]!=1]

def base_status(wt):
    return ("训","training") if wt=="4" else ("班","on_duty")

BOM="utf-8-sig"
def w(name,header,data):
    with io.open(os.path.join(BASE,name),"w",encoding=BOM,newline="") as f:
        c=csv.writer(f); c.writerow(header); c.writerows(data)
    return len(data)

# ===== 1. stores.csv =====
sd=[]
for dept,(no,nm,stt,tz,intr,od) in sorted(STORES.items(),key=lambda x:x[1][0]):
    sd.append([no,dept,nm,stt,STORE_STATUS_CN.get(stt,""),tz,od,"Y" if intr else "N"])
n1=w("stores.csv",["store_code","dept_id","store_name","store_status_code",
     "store_status_cn","time_zone","open_date","is_internal"],sd)

# ===== 2. employee_day.csv =====
ed=[]
for r in sorted(ACTIVE,key=lambda r:(STORES.get(r["dept"],("zz",))[0],r["date"],r["emp_no"])):
    st=STORES.get(r["dept"]); code=st[0] if st else str(r["dept"])
    name,prop,_=emp.get(r["emp_no"],("<unknown>","",""))
    sc,_=base_status(r["work_type"])
    ed.append([code,r["dept"],r["date"],r["emp_no"],name,PROP_LABEL.get(prop,prop),
               "%.2f"%r["eff_h"],r["eff_min"] if r["eff_min"] is not None else "",
               sc,r["sched"],r["rest"]])
n2=w("employee_day.csv",["store_code","dept_id","schedule_date","employee_id","employee_name",
     "employment_type","daily_scheduled_hours","scheduled_minutes","status_code",
     "scheduling_times","rest_times"],ed)

# ===== 3. slot_status_long.csv =====
sl=[]
for r in ACTIVE:
    st=STORES.get(r["dept"]); code=st[0] if st else str(r["dept"])
    work=slots_for(parse_segments(r["sched"]))
    rest=slots_for(parse_segments(r["rest"]))
    sc,cn=base_status(r["work_type"])
    for i in sorted(work):
        if i in rest:
            code_s,cn_s="休","rest"
        else:
            code_s,cn_s=sc,cn
        s0,s1=slot_label(i)
        sl.append([code,r["date"],r["emp_no"],i,s0,s1,code_s,cn_s])
n3=w("slot_status_long.csv",["store_code","schedule_date","employee_id","slot_index",
     "slot_start","slot_end","status_code","status_cn"],sl)

# ===== 4. store_slot_aggregates.csv (headcount derived; product_qty not persisted) =====
agg={}   # (code,date,i) -> headcount of on-duty (班/训, excluding 休)
for r in ACTIVE:
    st=STORES.get(r["dept"]); code=st[0] if st else str(r["dept"])
    work=slots_for(parse_segments(r["sched"]))
    rest=slots_for(parse_segments(r["rest"]))
    for i in work:
        if i in rest: continue            # on break -> not counted as present
        agg[(code,r["date"],i)]=agg.get((code,r["date"],i),0)+1
ag=[]
for dept,(no,nm,stt,tz,intr,od) in sorted(STORES.items(),key=lambda x:x[1][0]):
    for d in WEEK:
        for i in range(48):
            hc=agg.get((no,d,i),0)
            if hc==0: continue            # omit empty slots
            s0,s1=slot_label(i)
            ag.append([no,d,i,s0,s1,hc,""])   # slot_product_qty blank: not in DB
n4=w("store_slot_aggregates.csv",["store_code","schedule_date","slot_index","slot_start",
     "slot_end","slot_headcount","slot_product_qty"],ag)

# ===== 5. store_day_summary.csv =====
dd={}
for r in ACTIVE:
    st=STORES.get(r["dept"]); code=st[0] if st else str(r["dept"])
    name,prop,_=emp.get(r["emp_no"],("",""," "))
    k=(code,r["date"]); e=dd.setdefault(k,dict(h=0.0,emps=set(),ft=0,pt=0,first=99,last=-1))
    e["h"]+=r["eff_h"]; e["emps"].add(r["emp_no"])
    if prop=="0": e["ft"]+=1
    elif prop=="1": e["pt"]+=1
    sl_w=slots_for(parse_segments(r["sched"]))
    if sl_w:
        e["first"]=min(e["first"],min(sl_w)); e["last"]=max(e["last"],max(sl_w))
ds=[]
for dept,(no,nm,stt,tz,intr,od) in sorted(STORES.items(),key=lambda x:x[1][0]):
    for d in WEEK:
        e=dd.get((no,d))
        if not e:
            ds.append([no,d,"0.00",0,0,0,"",""]); continue
        f0=slot_label(e["first"])[0] if e["first"]<99 else ""
        l1=slot_label(e["last"])[1] if e["last"]>=0 else ""
        ds.append([no,d,"%.2f"%e["h"],len(e["emps"]),e["ft"],e["pt"],f0,l1])
n5=w("store_day_summary.csv",["store_code","schedule_date","total_hours","employees_scheduled",
     "ft_count","pt_count","first_slot","last_slot"],ds)

# ===== 6. slot_status_wide.csv (one row per emp-day, 48 slot cols) =====
wd=[]
hdr=["store_code","schedule_date","employee_id","employee_name","employment_type",
     "daily_scheduled_hours"]+[slot_label(i)[0] for i in range(48)]
for r in sorted(ACTIVE,key=lambda r:(STORES.get(r["dept"],("zz",))[0],r["date"],r["emp_no"])):
    st=STORES.get(r["dept"]); code=st[0] if st else str(r["dept"])
    name,prop,_=emp.get(r["emp_no"],("<unknown>","",""))
    work=slots_for(parse_segments(r["sched"]))
    rest=slots_for(parse_segments(r["rest"]))
    sc,_=base_status(r["work_type"])
    grid=[]
    for i in range(48):
        if i in work: grid.append("休" if i in rest else sc)
        else: grid.append("")
    wd.append([code,r["date"],r["emp_no"],name,PROP_LABEL.get(prop,prop),"%.2f"%r["eff_h"]]+grid)
n6=w("slot_status_wide.csv",hdr,wd)

print("rows:", dict(stores=n1,employee_day=n2,slot_status_long=n3,
      store_slot_aggregates=n4,store_day_summary=n5,slot_status_wide=n6))
print("active_rows=%d draft_rows(status<>1)=%d"%(len(ACTIVE),len(DRAFT)))

# ---- anchor validation: US00001 / 2026-06-12 ----
A=[r for r in ACTIVE if STORES.get(r["dept"],("",))[0]=="US00001" and r["date"]=="2026-06-12"]
tot=sum(r["eff_h"] for r in A)
print("\nANCHOR US00001 2026-06-12: employees=%d total_hours=%.2f"%(len(A),tot))
hc0630=agg.get(("US00001","2026-06-12",12),0)   # 06:00 slot
hc1330=agg.get(("US00001","2026-06-12",27),0)   # 13:30 slot
print("headcount 06:00(slot12)=%d  13:30(slot27)=%d"%(hc0630,hc1330))
