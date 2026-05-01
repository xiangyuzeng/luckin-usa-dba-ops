#!/usr/bin/env python3
"""
Build April 2026 inspection-export CSVs from data pulled via mcp-db-gateway.

Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol
Tables: t_shopcheck_data (header), t_shopcheck_opportunity (deductions),
        t_shopcheck_report (scores), t_shopcheck_item_config, t_shopcheck_category_config
Store master: aws-luckyus-opshop-rw / luckyus_opshop.t_shop_info

Inspection-type mapping (large_category_id -> inspection_type):
  1084 'Store food safety self-check' -> 门店自检
  1134 'Store food safety audit'      -> QA审计
  1184 'Area food safety Check'       -> 区经检查

Severity mapping (deduction_type -> S/M/G/L), inferred from item content prefix
('(S)','(M)') and score_config:
  1 -> S (severe, -5 typical)
  2 -> G (general, -2 typical)
  3 -> M (major, -5 typical)
  4 -> L (light, -1 typical)
"""

import csv
import json
import os
import re
from collections import defaultdict
from pathlib import Path

OUT = Path("/app/claude-code-output/april2026-inspection-export")
RAW = OUT / "raw"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TYPE_MAP = {
    1084: ("门店自检", "Store food safety self-check"),
    1134: ("QA审计",   "Store food safety audit"),
    1184: ("区经检查", "Area food safety Check"),
}
SEV_MAP = {1: "S", 2: "G", 3: "M", 4: "L"}

# Inspector role (post code -> role label). Derived from data.
POSTCODE_ROLE = {
    "LKUS00000076": "Area Operations Manager",
    "LKUS00000078": "Senior QA Manager",
    "LKUS00000223": "Senior QA Manager",
    "LKUS00000082": "Store Manager",
    "LKUS00000083": "Assistant Store Manager",
    "LKUS00000098": "Shift Supervisor / Trainer",
}

# Role inferred when post code missing — based on inspection_type
ROLE_FALLBACK = {
    "门店自检": "Store Manager",
    "QA审计":   "Senior QA Manager",
    "区经检查": "Area Operations Manager",
}

# ---------------------------------------------------------------------------
# Embedded data pulled via mcp-db-gateway (verbatim)
# ---------------------------------------------------------------------------

# Inspection headers (Jan-Apr 2026, deleted=0, large_category_id IN 1084,1134,1184)
HEADERS = json.loads(r'''[
{"id":1898,"dept_id":1140,"large_category_id":1134,"check_date":"2026-01-08","checker_name":"Yu Jiang","checker_id":140,"status":1,"process_status":40},
{"id":1899,"dept_id":20010,"large_category_id":1134,"check_date":"2026-01-08","checker_name":"Yu Jiang","checker_id":140,"status":1,"process_status":40},
{"id":1900,"dept_id":20010,"large_category_id":1084,"check_date":"2026-01-10","checker_name":"Shangxian Piao","checker_id":10101,"status":1,"process_status":40},
{"id":1901,"dept_id":20031,"large_category_id":1184,"check_date":"2026-01-11","checker_name":"Daniel Chu","checker_id":10251,"status":1,"process_status":40},
{"id":1902,"dept_id":1128,"large_category_id":1084,"check_date":"2026-01-11","checker_name":"Afsana Gu","checker_id":10127,"status":1,"process_status":40},
{"id":1915,"dept_id":20011,"large_category_id":1184,"check_date":"2026-01-16","checker_name":"Jung Han Liang","checker_id":136,"status":1,"process_status":40},
{"id":1916,"dept_id":1128,"large_category_id":1184,"check_date":"2026-01-16","checker_name":"Jung Han Liang","checker_id":136,"status":1,"process_status":40},
{"id":1917,"dept_id":20010,"large_category_id":1084,"check_date":"2026-01-17","checker_name":"Shangxian Piao","checker_id":10101,"status":1,"process_status":10},
{"id":1918,"dept_id":20008,"large_category_id":1184,"check_date":"2026-01-18","checker_name":"Jung Han Liang","checker_id":136,"status":1,"process_status":40},
{"id":1919,"dept_id":1141,"large_category_id":1184,"check_date":"2026-01-18","checker_name":"Jung Han Liang","checker_id":136,"status":0,"process_status":null},
{"id":1920,"dept_id":1127,"large_category_id":1184,"check_date":"2026-01-18","checker_name":"Jung Han Liang","checker_id":136,"status":0,"process_status":null},
{"id":1922,"dept_id":20031,"large_category_id":1134,"check_date":"2026-01-22","checker_name":"Yu Jiang","checker_id":140,"status":1,"process_status":40},
{"id":1923,"dept_id":20010,"large_category_id":1084,"check_date":"2026-01-24","checker_name":"Shangxian Piao","checker_id":10101,"status":1,"process_status":10},
{"id":1924,"dept_id":20010,"large_category_id":1084,"check_date":"2026-01-24","checker_name":"Joselyn Pacheco","checker_id":10254,"status":1,"process_status":10},
{"id":1925,"dept_id":20010,"large_category_id":1084,"check_date":"2026-01-24","checker_name":"Ya Xin Chen","checker_id":161,"status":0,"process_status":null},
{"id":1926,"dept_id":20032,"large_category_id":1084,"check_date":"2026-01-24","checker_name":"Juliana Li","checker_id":10033,"status":1,"process_status":40},
{"id":1928,"dept_id":1128,"large_category_id":1084,"check_date":"2026-01-25","checker_name":"Carina Medrano","checker_id":10085,"status":0,"process_status":null},
{"id":1931,"dept_id":20008,"large_category_id":1134,"check_date":"2026-01-29","checker_name":"Yu Jiang","checker_id":140,"status":1,"process_status":10},
{"id":1932,"dept_id":20032,"large_category_id":1134,"check_date":"2026-01-29","checker_name":"Yu Jiang","checker_id":140,"status":1,"process_status":40},
{"id":1934,"dept_id":20011,"large_category_id":1084,"check_date":"2026-01-29","checker_name":"Tunisia Hayward","checker_id":10029,"status":0,"process_status":null},
{"id":1933,"dept_id":1140,"large_category_id":1084,"check_date":"2026-01-30","checker_name":"Dominique Meadows","checker_id":187,"status":1,"process_status":40},
{"id":1935,"dept_id":20008,"large_category_id":1084,"check_date":"2026-02-07","checker_name":"Andrew Hu","checker_id":10041,"status":1,"process_status":10},
{"id":1936,"dept_id":20010,"large_category_id":1084,"check_date":"2026-02-07","checker_name":"Joselyn Pacheco","checker_id":10254,"status":1,"process_status":10},
{"id":1939,"dept_id":1128,"large_category_id":1084,"check_date":"2026-02-08","checker_name":"Afsana Gu","checker_id":10127,"status":0,"process_status":null},
{"id":1940,"dept_id":1128,"large_category_id":1084,"check_date":"2026-02-08","checker_name":"Carina Medrano","checker_id":10085,"status":0,"process_status":null},
{"id":1943,"dept_id":1127,"large_category_id":1134,"check_date":"2026-02-11","checker_name":"Yu Jiang","checker_id":140,"status":1,"process_status":40},
{"id":1945,"dept_id":20055,"large_category_id":1134,"check_date":"2026-02-12","checker_name":"Qingfu Hu","checker_id":10335,"status":0,"process_status":null},
{"id":1946,"dept_id":1128,"large_category_id":1134,"check_date":"2026-02-12","checker_name":"Yu Jiang","checker_id":140,"status":1,"process_status":40},
{"id":1947,"dept_id":20010,"large_category_id":1084,"check_date":"2026-02-14","checker_name":"Joselyn Pacheco","checker_id":10254,"status":1,"process_status":10},
{"id":1948,"dept_id":20027,"large_category_id":1084,"check_date":"2026-02-15","checker_name":"Chance Lee","checker_id":10233,"status":0,"process_status":null},
{"id":1949,"dept_id":20010,"large_category_id":1084,"check_date":"2026-02-15","checker_name":"Joselyn Pacheco","checker_id":10254,"status":0,"process_status":null},
{"id":1952,"dept_id":20011,"large_category_id":1084,"check_date":"2026-02-19","checker_name":"Tunisia Hayward","checker_id":10029,"status":0,"process_status":null},
{"id":1954,"dept_id":20010,"large_category_id":1084,"check_date":"2026-02-22","checker_name":"Shangxian Piao","checker_id":10101,"status":1,"process_status":10},
{"id":1955,"dept_id":20010,"large_category_id":1084,"check_date":"2026-02-28","checker_name":"Shangxian Piao","checker_id":10101,"status":1,"process_status":10},
{"id":1956,"dept_id":20032,"large_category_id":1084,"check_date":"2026-03-04","checker_name":"Juliana Li","checker_id":10033,"status":1,"process_status":40},
{"id":1959,"dept_id":20031,"large_category_id":1084,"check_date":"2026-03-06","checker_name":"Clara Mae Venturina","checker_id":10032,"status":1,"process_status":40},
{"id":1960,"dept_id":20031,"large_category_id":1084,"check_date":"2026-03-06","checker_name":"Clara Mae Venturina","checker_id":10032,"status":1,"process_status":40},
{"id":1961,"dept_id":20010,"large_category_id":1084,"check_date":"2026-03-08","checker_name":"Shangxian Piao","checker_id":10101,"status":1,"process_status":10},
{"id":1962,"dept_id":20035,"large_category_id":1084,"check_date":"2026-03-09","checker_name":"Wenny Lin","checker_id":10027,"status":1,"process_status":40},
{"id":1963,"dept_id":20031,"large_category_id":1084,"check_date":"2026-03-09","checker_name":"Clara Mae Venturina","checker_id":10032,"status":1,"process_status":40},
{"id":1965,"dept_id":20008,"large_category_id":1084,"check_date":"2026-03-09","checker_name":"Derson Liang","checker_id":10236,"status":1,"process_status":10},
{"id":1966,"dept_id":1127,"large_category_id":1084,"check_date":"2026-03-09","checker_name":"Jian Ming Juo","checker_id":10035,"status":1,"process_status":40},
{"id":1969,"dept_id":20027,"large_category_id":1084,"check_date":"2026-03-10","checker_name":"Darwin Coronel","checker_id":10031,"status":1,"process_status":40},
{"id":1971,"dept_id":20008,"large_category_id":1084,"check_date":"2026-03-10","checker_name":"Yaqing Zuo","checker_id":157,"status":1,"process_status":40},
{"id":1972,"dept_id":20010,"large_category_id":1084,"check_date":"2026-03-11","checker_name":"Shangxian Piao","checker_id":10101,"status":1,"process_status":40},
{"id":1973,"dept_id":20008,"large_category_id":1084,"check_date":"2026-03-15","checker_name":"Derson Liang","checker_id":10236,"status":1,"process_status":40},
{"id":1977,"dept_id":20010,"large_category_id":1084,"check_date":"2026-03-27","checker_name":"Shangxian Piao","checker_id":10101,"status":1,"process_status":40},
{"id":1978,"dept_id":20007,"large_category_id":1134,"check_date":"2026-03-31","checker_name":"Yu Jiang","checker_id":140,"status":0,"process_status":null},
{"id":1979,"dept_id":20035,"large_category_id":1134,"check_date":"2026-03-31","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":40},
{"id":1980,"dept_id":20007,"large_category_id":1134,"check_date":"2026-03-31","checker_name":"Yu Jiang","checker_id":140,"status":0,"process_status":null},
{"id":1981,"dept_id":1140,"large_category_id":1134,"check_date":"2026-04-01","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":40},
{"id":1982,"dept_id":20010,"large_category_id":1134,"check_date":"2026-04-01","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":40},
{"id":1984,"dept_id":20010,"large_category_id":1084,"check_date":"2026-04-03","checker_name":"Shangxian Piao","checker_id":10101,"status":1,"process_status":40},
{"id":1985,"dept_id":1127,"large_category_id":1084,"check_date":"2026-04-04","checker_name":"Jian Ming Juo","checker_id":10035,"status":1,"process_status":10},
{"id":1987,"dept_id":1127,"large_category_id":1084,"check_date":"2026-04-06","checker_name":"Jian Ming Juo","checker_id":10035,"status":1,"process_status":10},
{"id":1989,"dept_id":1127,"large_category_id":1134,"check_date":"2026-04-09","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":40},
{"id":1990,"dept_id":1140,"large_category_id":1084,"check_date":"2026-04-09","checker_name":"Dominique Meadows","checker_id":187,"status":1,"process_status":40},
{"id":1991,"dept_id":20008,"large_category_id":1084,"check_date":"2026-04-09","checker_name":"Derson Liang","checker_id":10236,"status":1,"process_status":40},
{"id":1992,"dept_id":20031,"large_category_id":1084,"check_date":"2026-04-10","checker_name":"Clara Mae Venturina","checker_id":10032,"status":1,"process_status":40},
{"id":1993,"dept_id":20010,"large_category_id":1084,"check_date":"2026-04-11","checker_name":"Sami Dalao","checker_id":10331,"status":1,"process_status":40},
{"id":1994,"dept_id":20019,"large_category_id":1084,"check_date":"2026-04-13","checker_name":"Juliana Li","checker_id":10033,"status":0,"process_status":null},
{"id":1995,"dept_id":20011,"large_category_id":1084,"check_date":"2026-04-13","checker_name":"Austin Gebhardt","checker_id":10186,"status":1,"process_status":40},
{"id":1996,"dept_id":20032,"large_category_id":1084,"check_date":"2026-04-13","checker_name":"Alexander G Harry","checker_id":10118,"status":1,"process_status":40},
{"id":1998,"dept_id":20027,"large_category_id":1084,"check_date":"2026-04-14","checker_name":"Javier Cruz","checker_id":10315,"status":1,"process_status":40},
{"id":1999,"dept_id":20027,"large_category_id":1084,"check_date":"2026-04-14","checker_name":"Javier Cruz","checker_id":10315,"status":1,"process_status":40},
{"id":2000,"dept_id":1127,"large_category_id":1084,"check_date":"2026-04-14","checker_name":"Jian Ming Juo","checker_id":10035,"status":1,"process_status":10},
{"id":2001,"dept_id":20019,"large_category_id":1084,"check_date":"2026-04-14","checker_name":"Juliana Li","checker_id":10033,"status":1,"process_status":40},
{"id":2002,"dept_id":1131,"large_category_id":1134,"check_date":"2026-04-14","checker_name":"Eamonn Caballar","checker_id":10488,"status":0,"process_status":null},
{"id":2003,"dept_id":20026,"large_category_id":1084,"check_date":"2026-04-14","checker_name":"Juan Ortiz-Fontanez","checker_id":10077,"status":1,"process_status":40},
{"id":2004,"dept_id":20008,"large_category_id":1084,"check_date":"2026-04-14","checker_name":"Yaqing Zuo","checker_id":157,"status":0,"process_status":null},
{"id":2005,"dept_id":20008,"large_category_id":1084,"check_date":"2026-04-15","checker_name":"Derson Liang","checker_id":10236,"status":1,"process_status":40},
{"id":2006,"dept_id":20035,"large_category_id":1084,"check_date":"2026-04-16","checker_name":"Wenny Lin","checker_id":10027,"status":1,"process_status":40},
{"id":2007,"dept_id":20031,"large_category_id":1084,"check_date":"2026-04-16","checker_name":"Clara Mae Venturina","checker_id":10032,"status":1,"process_status":40},
{"id":2013,"dept_id":20026,"large_category_id":1184,"check_date":"2026-04-16","checker_name":"Jung Han Liang","checker_id":136,"status":1,"process_status":20},
{"id":2014,"dept_id":20035,"large_category_id":1184,"check_date":"2026-04-16","checker_name":"Jung Han Liang","checker_id":136,"status":1,"process_status":20},
{"id":2009,"dept_id":1128,"large_category_id":1084,"check_date":"2026-04-17","checker_name":"Afsana Gu","checker_id":10127,"status":1,"process_status":40},
{"id":2010,"dept_id":1140,"large_category_id":1084,"check_date":"2026-04-17","checker_name":"Dominique Meadows","checker_id":187,"status":1,"process_status":40},
{"id":2011,"dept_id":1141,"large_category_id":1084,"check_date":"2026-04-17","checker_name":"Eric Park","checker_id":10084,"status":1,"process_status":40},
{"id":2012,"dept_id":20019,"large_category_id":1084,"check_date":"2026-04-19","checker_name":"Joselyn Pacheco Trejo","checker_id":10254,"status":1,"process_status":10},
{"id":2015,"dept_id":20008,"large_category_id":1084,"check_date":"2026-04-21","checker_name":"Derson Liang","checker_id":10236,"status":1,"process_status":40},
{"id":2016,"dept_id":20027,"large_category_id":1084,"check_date":"2026-04-21","checker_name":"Darwin Coronel","checker_id":10031,"status":1,"process_status":10},
{"id":2017,"dept_id":20027,"large_category_id":1084,"check_date":"2026-04-21","checker_name":"Darwin Coronel","checker_id":10031,"status":1,"process_status":10},
{"id":2018,"dept_id":20027,"large_category_id":1084,"check_date":"2026-04-21","checker_name":"Darwin Coronel","checker_id":10031,"status":1,"process_status":40},
{"id":2045,"dept_id":1127,"large_category_id":1184,"check_date":"2026-04-21","checker_name":"Jung Han Liang","checker_id":136,"status":1,"process_status":20},
{"id":2019,"dept_id":20035,"large_category_id":1084,"check_date":"2026-04-22","checker_name":"Brionna Jiles","checker_id":10116,"status":1,"process_status":40},
{"id":2020,"dept_id":20027,"large_category_id":1184,"check_date":"2026-04-23","checker_name":"Daniel Chu","checker_id":10251,"status":1,"process_status":40},
{"id":2046,"dept_id":1128,"large_category_id":1184,"check_date":"2026-04-23","checker_name":"Jung Han Liang","checker_id":136,"status":1,"process_status":20},
{"id":2021,"dept_id":20010,"large_category_id":1084,"check_date":"2026-04-24","checker_name":"Shangxian Piao","checker_id":10101,"status":1,"process_status":40},
{"id":2022,"dept_id":1127,"large_category_id":1084,"check_date":"2026-04-24","checker_name":"Huichen Jiang","checker_id":10053,"status":1,"process_status":10},
{"id":2023,"dept_id":20008,"large_category_id":1084,"check_date":"2026-04-24","checker_name":"Yaqing Zuo","checker_id":157,"status":1,"process_status":40},
{"id":2024,"dept_id":1140,"large_category_id":1184,"check_date":"2026-04-24","checker_name":"Daniel Chu","checker_id":10251,"status":1,"process_status":40},
{"id":2025,"dept_id":20031,"large_category_id":1084,"check_date":"2026-04-25","checker_name":"Clara Mae Venturina","checker_id":10032,"status":1,"process_status":40},
{"id":2026,"dept_id":20031,"large_category_id":1184,"check_date":"2026-04-25","checker_name":"Daniel Chu","checker_id":10251,"status":1,"process_status":40},
{"id":2027,"dept_id":20019,"large_category_id":1084,"check_date":"2026-04-25","checker_name":"Joselyn Pacheco Trejo","checker_id":10254,"status":1,"process_status":40},
{"id":2028,"dept_id":20032,"large_category_id":1084,"check_date":"2026-04-26","checker_name":"Jonathan Soto","checker_id":10177,"status":1,"process_status":40},
{"id":2029,"dept_id":20019,"large_category_id":1184,"check_date":"2026-04-26","checker_name":"Daniel Chu","checker_id":10251,"status":1,"process_status":40},
{"id":2047,"dept_id":20011,"large_category_id":1184,"check_date":"2026-04-26","checker_name":"Jung Han Liang","checker_id":136,"status":1,"process_status":20},
{"id":2048,"dept_id":1141,"large_category_id":1184,"check_date":"2026-04-26","checker_name":"Jung Han Liang","checker_id":136,"status":1,"process_status":20},
{"id":2030,"dept_id":20008,"large_category_id":1134,"check_date":"2026-04-27","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":40},
{"id":2031,"dept_id":1128,"large_category_id":1134,"check_date":"2026-04-27","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":30},
{"id":2032,"dept_id":1141,"large_category_id":1084,"check_date":"2026-04-28","checker_name":"Eric Park","checker_id":10084,"status":0,"process_status":null},
{"id":2033,"dept_id":20031,"large_category_id":1134,"check_date":"2026-04-28","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":20},
{"id":2034,"dept_id":20027,"large_category_id":1134,"check_date":"2026-04-28","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":20},
{"id":2036,"dept_id":20011,"large_category_id":1134,"check_date":"2026-04-29","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":20},
{"id":2037,"dept_id":20019,"large_category_id":1134,"check_date":"2026-04-29","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":20},
{"id":2038,"dept_id":20026,"large_category_id":1084,"check_date":"2026-04-29","checker_name":"Darwin Coronel","checker_id":10031,"status":1,"process_status":40},
{"id":2039,"dept_id":20035,"large_category_id":1134,"check_date":"2026-04-30","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":20},
{"id":2040,"dept_id":1141,"large_category_id":1134,"check_date":"2026-04-30","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":30},
{"id":2041,"dept_id":20032,"large_category_id":1134,"check_date":"2026-04-30","checker_name":"Eamonn Caballar","checker_id":10488,"status":1,"process_status":20},
{"id":2042,"dept_id":20010,"large_category_id":1184,"check_date":"2026-04-30","checker_name":"Daniel Chu","checker_id":10251,"status":1,"process_status":20},
{"id":2043,"dept_id":20032,"large_category_id":1184,"check_date":"2026-04-30","checker_name":"Daniel Chu","checker_id":10251,"status":1,"process_status":20},
{"id":2044,"dept_id":20026,"large_category_id":1184,"check_date":"2026-04-30","checker_name":"Daniel Chu","checker_id":10251,"status":1,"process_status":20},
{"id":2049,"dept_id":20008,"large_category_id":1184,"check_date":"2026-04-30","checker_name":"Jung Han Liang","checker_id":136,"status":1,"process_status":20}
]'''.replace("null", "null"))

# Reports (April 2026 only — full opportunity_desc kept for severity counts/score)
REPORTS_APR = json.loads(r'''[
{"shopcheck_data_id":1981,"checker_post_code":"LKUS00000223","score":84,"opportunity_desc":"[{\"deductionType\":2,\"count\":4,\"deductionScore\":-8},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":3,\"deductionScore\":-3}]"},
{"shopcheck_data_id":1982,"checker_post_code":"LKUS00000223","score":86,"opportunity_desc":"[{\"deductionType\":2,\"count\":4,\"deductionScore\":-8},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":1984,"checker_post_code":"LKUS00000082","score":89,"opportunity_desc":"[{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5}]"},
{"shopcheck_data_id":1985,"checker_post_code":"LKUS00000082","score":66,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":4,\"count\":3,\"deductionScore\":-3}]"},
{"shopcheck_data_id":1987,"checker_post_code":"LKUS00000082","score":44,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":11,\"deductionScore\":-18},{\"deductionType\":3,\"count\":2,\"deductionScore\":-10},{\"deductionType\":4,\"count\":3,\"deductionScore\":-3}]"},
{"shopcheck_data_id":1989,"checker_post_code":"LKUS00000223","score":79,"opportunity_desc":"[{\"deductionType\":4,\"count\":1,\"deductionScore\":-1},{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":3,\"count\":2,\"deductionScore\":-10}]"},
{"shopcheck_data_id":1990,"checker_post_code":"LKUS00000082","score":91,"opportunity_desc":"[{\"deductionType\":2,\"count\":1,\"deductionScore\":-2},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]"},
{"shopcheck_data_id":1991,"checker_post_code":"LKUS00000083","score":78,"opportunity_desc":"[{\"deductionType\":2,\"count\":7,\"deductionScore\":-14},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":3,\"deductionScore\":-3}]"},
{"shopcheck_data_id":1992,"checker_post_code":"LKUS00000082","score":98,"opportunity_desc":"[{\"deductionType\":2,\"count\":1,\"deductionScore\":-2}]"},
{"shopcheck_data_id":1993,"checker_post_code":"LKUS00000098","score":93,"opportunity_desc":"[{\"deductionType\":2,\"count\":2,\"deductionScore\":0},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]"},
{"shopcheck_data_id":1995,"checker_post_code":"LKUS00000083","score":79,"opportunity_desc":"[{\"deductionType\":2,\"count\":8,\"deductionScore\":-16},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5}]"},
{"shopcheck_data_id":1996,"checker_post_code":"LKUS00000083","score":72,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":1,\"deductionScore\":-2},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":1998,"checker_post_code":"LKUS00000098","score":95,"opportunity_desc":"[{\"deductionType\":3,\"count\":1,\"deductionScore\":-5}]"},
{"shopcheck_data_id":1999,"checker_post_code":"LKUS00000098","score":80,"opportunity_desc":"[{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":3,\"count\":2,\"deductionScore\":-10}]"},
{"shopcheck_data_id":2000,"checker_post_code":"LKUS00000082","score":83,"opportunity_desc":"[{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":3,\"count\":2,\"deductionScore\":-10},{\"deductionType\":4,\"count\":3,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2001,"checker_post_code":"LKUS00000082","score":96,"opportunity_desc":"[{\"deductionType\":2,\"count\":2,\"deductionScore\":-4}]"},
{"shopcheck_data_id":2003,"checker_post_code":"LKUS00000082","score":66,"opportunity_desc":"[{\"deductionType\":1,\"count\":2,\"deductionScore\":-10},{\"deductionType\":2,\"count\":2,\"deductionScore\":-4}]"},
{"shopcheck_data_id":2005,"checker_post_code":"LKUS00000083","score":84,"opportunity_desc":"[{\"deductionType\":2,\"count\":7,\"deductionScore\":-14},{\"deductionType\":4,\"count\":4,\"deductionScore\":-2}]"},
{"shopcheck_data_id":2006,"checker_post_code":"LKUS00000082","score":65,"opportunity_desc":"[{\"deductionType\":2,\"count\":11,\"deductionScore\":-22},{\"deductionType\":3,\"count\":2,\"deductionScore\":-10},{\"deductionType\":4,\"count\":3,\"deductionScore\":-3}]"},
{"shopcheck_data_id":2007,"checker_post_code":"LKUS00000082","score":82,"opportunity_desc":"[{\"deductionType\":2,\"count\":6,\"deductionScore\":-12},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":3,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2009,"checker_post_code":"LKUS00000082","score":71,"opportunity_desc":"[{\"deductionType\":2,\"count\":11,\"deductionScore\":-22},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]"},
{"shopcheck_data_id":2010,"checker_post_code":"LKUS00000082","score":96,"opportunity_desc":"[{\"deductionType\":2,\"count\":2,\"deductionScore\":-4}]"},
{"shopcheck_data_id":2011,"checker_post_code":"LKUS00000082","score":63,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":2,\"deductionScore\":-4},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":3,\"deductionScore\":-3}]"},
{"shopcheck_data_id":2012,"checker_post_code":"LKUS00000082","score":100,"opportunity_desc":"[]"},
{"shopcheck_data_id":2013,"checker_post_code":"LKUS00000076","score":85,"opportunity_desc":"[{\"deductionType\":2,\"count\":4,\"deductionScore\":-8},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]"},
{"shopcheck_data_id":2014,"checker_post_code":"LKUS00000076","score":67,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]"},
{"shopcheck_data_id":2015,"checker_post_code":"LKUS00000083","score":76,"opportunity_desc":"[{\"deductionType\":2,\"count\":8,\"deductionScore\":-16},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":3,\"deductionScore\":-3}]"},
{"shopcheck_data_id":2016,"checker_post_code":"LKUS00000082","score":100,"opportunity_desc":"[]"},
{"shopcheck_data_id":2017,"checker_post_code":"LKUS00000082","score":100,"opportunity_desc":"[]"},
{"shopcheck_data_id":2018,"checker_post_code":"LKUS00000082","score":64,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5}]"},
{"shopcheck_data_id":2019,"checker_post_code":"LKUS00000098","score":59,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2020,"checker_post_code":"LKUS00000076","score":94,"opportunity_desc":"[{\"deductionType\":2,\"count\":3,\"deductionScore\":-6}]"},
{"shopcheck_data_id":2021,"checker_post_code":"LKUS00000082","score":98,"opportunity_desc":"[{\"deductionType\":2,\"count\":1,\"deductionScore\":-2},{\"deductionType\":4,\"count\":2,\"deductionScore\":0}]"},
{"shopcheck_data_id":2022,"checker_post_code":"LKUS00000098","score":91,"opportunity_desc":"[{\"deductionType\":2,\"count\":4,\"deductionScore\":-8},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2023,"checker_post_code":"LKUS00000082","score":81,"opportunity_desc":"[{\"deductionType\":2,\"count\":6,\"deductionScore\":-12},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]"},
{"shopcheck_data_id":2024,"checker_post_code":"LKUS00000076","score":91,"opportunity_desc":"[{\"deductionType\":2,\"count\":4,\"deductionScore\":-8},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2025,"checker_post_code":"LKUS00000082","score":90,"opportunity_desc":"[{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":4,\"count\":2,\"deductionScore\":0}]"},
{"shopcheck_data_id":2026,"checker_post_code":"LKUS00000076","score":85,"opportunity_desc":"[{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5}]"},
{"shopcheck_data_id":2027,"checker_post_code":"LKUS00000082","score":94,"opportunity_desc":"[{\"deductionType\":2,\"count\":2,\"deductionScore\":-4},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]"},
{"shopcheck_data_id":2028,"checker_post_code":"LKUS00000083","score":90,"opportunity_desc":"[{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":4,\"count\":4,\"deductionScore\":-4}]"},
{"shopcheck_data_id":2029,"checker_post_code":"LKUS00000076","score":88,"opportunity_desc":"[{\"deductionType\":2,\"count\":6,\"deductionScore\":-12}]"},
{"shopcheck_data_id":2030,"checker_post_code":"LKUS00000223","score":87,"opportunity_desc":"[{\"deductionType\":2,\"count\":6,\"deductionScore\":-12},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2031,"checker_post_code":"LKUS00000223","score":84,"opportunity_desc":"[{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2033,"checker_post_code":"LKUS00000223","score":71,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":1,\"deductionScore\":-2},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]"},
{"shopcheck_data_id":2034,"checker_post_code":"LKUS00000223","score":82,"opportunity_desc":"[{\"deductionType\":2,\"count\":4,\"deductionScore\":-8},{\"deductionType\":3,\"count\":2,\"deductionScore\":-10}]"},
{"shopcheck_data_id":2036,"checker_post_code":"LKUS00000223","score":83,"opportunity_desc":"[{\"deductionType\":2,\"count\":8,\"deductionScore\":-16},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2037,"checker_post_code":"LKUS00000223","score":75,"opportunity_desc":"[{\"deductionType\":2,\"count\":8,\"deductionScore\":-16},{\"deductionType\":3,\"count\":2,\"deductionScore\":-10},{\"deductionType\":4,\"count\":1,\"deductionScore\":1}]"},
{"shopcheck_data_id":2038,"checker_post_code":"LKUS00000082","score":69,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":3,\"deductionScore\":-6}]"},
{"shopcheck_data_id":2039,"checker_post_code":"LKUS00000223","score":78,"opportunity_desc":"[{\"deductionType\":2,\"count\":6,\"deductionScore\":-12},{\"deductionType\":3,\"count\":2,\"deductionScore\":-10}]"},
{"shopcheck_data_id":2040,"checker_post_code":"LKUS00000223","score":69,"opportunity_desc":"[{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":1,\"count\":1,\"deductionScore\":-5}]"},
{"shopcheck_data_id":2041,"checker_post_code":"LKUS00000223","score":87,"opportunity_desc":"[{\"deductionType\":2,\"count\":6,\"deductionScore\":-12},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2042,"checker_post_code":"LKUS00000076","score":68,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2043,"checker_post_code":"LKUS00000076","score":94,"opportunity_desc":"[{\"deductionType\":2,\"count\":3,\"deductionScore\":-6}]"},
{"shopcheck_data_id":2044,"checker_post_code":"LKUS00000076","score":75,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5}]"},
{"shopcheck_data_id":2045,"checker_post_code":"LKUS00000076","score":85,"opportunity_desc":"[{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5}]"},
{"shopcheck_data_id":2046,"checker_post_code":"LKUS00000076","score":88,"opportunity_desc":"[{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2047,"checker_post_code":"LKUS00000076","score":89,"opportunity_desc":"[{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]"},
{"shopcheck_data_id":2048,"checker_post_code":"LKUS00000076","score":66,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":4,\"count\":3,\"deductionScore\":-3}]"},
{"shopcheck_data_id":2049,"checker_post_code":"LKUS00000076","score":47,"opportunity_desc":"[{\"deductionType\":1,\"count\":2,\"deductionScore\":-10},{\"deductionType\":2,\"count\":6,\"deductionScore\":-12},{\"deductionType\":3,\"count\":2,\"deductionScore\":-10},{\"deductionType\":4,\"count\":3,\"deductionScore\":-1}]"}
]''')

# Reports for Jan-Mar (for trend file)
REPORTS_Q1 = json.loads(r'''[
{"shopcheck_data_id":1898,"checker_post_code":"LKUS00000078","score":42,"opportunity_desc":"[{\"deductionType\":1,\"count\":2,\"deductionScore\":-10},{\"deductionType\":2,\"count\":11,\"deductionScore\":-22},{\"deductionType\":4,\"count\":6,\"deductionScore\":-6}]","check_date":"2026-01-08","large_category_id":1134,"dept_id":1140,"checker_name":"Yu Jiang"},
{"shopcheck_data_id":1899,"checker_post_code":"LKUS00000078","score":89,"opportunity_desc":"[{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]","check_date":"2026-01-08","large_category_id":1134,"dept_id":20010,"checker_name":"Yu Jiang"},
{"shopcheck_data_id":1900,"checker_post_code":"LKUS00000098","score":96,"opportunity_desc":"[{\"deductionType\":2,\"count\":2,\"deductionScore\":-4}]","check_date":"2026-01-10","large_category_id":1084,"dept_id":20010,"checker_name":"Shangxian Piao"},
{"shopcheck_data_id":1901,"checker_post_code":"LKUS00000076","score":62,"opportunity_desc":"[{\"deductionType\":1,\"count\":2,\"deductionScore\":-10},{\"deductionType\":2,\"count\":4,\"deductionScore\":-8}]","check_date":"2026-01-11","large_category_id":1184,"dept_id":20031,"checker_name":"Daniel Chu"},
{"shopcheck_data_id":1902,"checker_post_code":"LKUS00000082","score":67,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]","check_date":"2026-01-11","large_category_id":1084,"dept_id":1128,"checker_name":"Afsana Gu"},
{"shopcheck_data_id":1915,"checker_post_code":"LKUS00000076","score":79,"opportunity_desc":"[{\"deductionType\":2,\"count\":7,\"deductionScore\":-14},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]","check_date":"2026-01-16","large_category_id":1184,"dept_id":20011,"checker_name":"Jung Han Liang"},
{"shopcheck_data_id":1916,"checker_post_code":"LKUS00000076","score":89,"opportunity_desc":"[{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5}]","check_date":"2026-01-16","large_category_id":1184,"dept_id":1128,"checker_name":"Jung Han Liang"},
{"shopcheck_data_id":1917,"checker_post_code":"LKUS00000098","score":100,"opportunity_desc":"[]","check_date":"2026-01-17","large_category_id":1084,"dept_id":20010,"checker_name":"Shangxian Piao"},
{"shopcheck_data_id":1918,"checker_post_code":"LKUS00000076","score":72,"opportunity_desc":"[{\"deductionType\":2,\"count\":8,\"deductionScore\":-16},{\"deductionType\":3,\"count\":2,\"deductionScore\":-10},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]","check_date":"2026-01-18","large_category_id":1184,"dept_id":20008,"checker_name":"Jung Han Liang"},
{"shopcheck_data_id":1922,"checker_post_code":"LKUS00000078","score":43,"opportunity_desc":"[{\"deductionType\":3,\"count\":2,\"deductionScore\":-10},{\"deductionType\":4,\"count\":4,\"deductionScore\":-4},{\"deductionType\":1,\"count\":2,\"deductionScore\":-5},{\"deductionType\":2,\"count\":11,\"deductionScore\":-18}]","check_date":"2026-01-22","large_category_id":1134,"dept_id":20031,"checker_name":"Yu Jiang"},
{"shopcheck_data_id":1923,"checker_post_code":"LKUS00000098","score":100,"opportunity_desc":"[]","check_date":"2026-01-24","large_category_id":1084,"dept_id":20010,"checker_name":"Shangxian Piao"},
{"shopcheck_data_id":1924,"checker_post_code":"LKUS00000098","score":100,"opportunity_desc":"[]","check_date":"2026-01-24","large_category_id":1084,"dept_id":20010,"checker_name":"Joselyn Pacheco"},
{"shopcheck_data_id":1926,"checker_post_code":"LKUS00000082","score":87,"opportunity_desc":"[{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]","check_date":"2026-01-24","large_category_id":1084,"dept_id":20032,"checker_name":"Juliana Li"},
{"shopcheck_data_id":1931,"checker_post_code":"LKUS00000078","score":75,"opportunity_desc":"[{\"deductionType\":2,\"count\":8,\"deductionScore\":-16},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":4,\"deductionScore\":-4}]","check_date":"2026-01-29","large_category_id":1134,"dept_id":20008,"checker_name":"Yu Jiang"},
{"shopcheck_data_id":1932,"checker_post_code":"LKUS00000078","score":63,"opportunity_desc":"[{\"deductionType\":4,\"count\":1,\"deductionScore\":0},{\"deductionType\":2,\"count\":6,\"deductionScore\":-12},{\"deductionType\":1,\"count\":2,\"deductionScore\":-5}]","check_date":"2026-01-29","large_category_id":1134,"dept_id":20032,"checker_name":"Yu Jiang"},
{"shopcheck_data_id":1933,"checker_post_code":"LKUS00000082","score":82,"opportunity_desc":"[{\"deductionType\":2,\"count\":9,\"deductionScore\":-18}]","check_date":"2026-01-30","large_category_id":1084,"dept_id":1140,"checker_name":"Dominique Meadows"},
{"shopcheck_data_id":1935,"checker_post_code":"LKUS00000083","score":100,"opportunity_desc":"[]","check_date":"2026-02-07","large_category_id":1084,"dept_id":20008,"checker_name":"Andrew Hu"},
{"shopcheck_data_id":1936,"checker_post_code":"LKUS00000098","score":100,"opportunity_desc":"[]","check_date":"2026-02-07","large_category_id":1084,"dept_id":20010,"checker_name":"Joselyn Pacheco"},
{"shopcheck_data_id":1943,"checker_post_code":"LKUS00000078","score":48,"opportunity_desc":"[{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":4,\"deductionScore\":-4},{\"deductionType\":2,\"count\":9,\"deductionScore\":-18},{\"deductionType\":1,\"count\":1,\"deductionScore\":-5}]","check_date":"2026-02-11","large_category_id":1134,"dept_id":1127,"checker_name":"Yu Jiang"},
{"shopcheck_data_id":1946,"checker_post_code":"LKUS00000078","score":94,"opportunity_desc":"[{\"deductionType\":4,\"count\":3,\"deductionScore\":-2},{\"deductionType\":1,\"count\":1,\"deductionScore\":0},{\"deductionType\":2,\"count\":2,\"deductionScore\":-4}]","check_date":"2026-02-12","large_category_id":1134,"dept_id":1128,"checker_name":"Yu Jiang"},
{"shopcheck_data_id":1947,"checker_post_code":"LKUS00000098","score":100,"opportunity_desc":"[]","check_date":"2026-02-14","large_category_id":1084,"dept_id":20010,"checker_name":"Joselyn Pacheco"},
{"shopcheck_data_id":1954,"checker_post_code":"LKUS00000082","score":100,"opportunity_desc":"[]","check_date":"2026-02-22","large_category_id":1084,"dept_id":20010,"checker_name":"Shangxian Piao"},
{"shopcheck_data_id":1955,"checker_post_code":"LKUS00000082","score":100,"opportunity_desc":"[]","check_date":"2026-02-28","large_category_id":1084,"dept_id":20010,"checker_name":"Shangxian Piao"},
{"shopcheck_data_id":1956,"checker_post_code":"LKUS00000082","score":89,"opportunity_desc":"[{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]","check_date":"2026-03-04","large_category_id":1084,"dept_id":20032,"checker_name":"Juliana Li"},
{"shopcheck_data_id":1959,"checker_post_code":"LKUS00000082","score":70,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5}]","check_date":"2026-03-06","large_category_id":1084,"dept_id":20031,"checker_name":"Clara Mae Venturina"},
{"shopcheck_data_id":1960,"checker_post_code":"LKUS00000082","score":46,"opportunity_desc":"[{\"deductionType\":1,\"count\":2,\"deductionScore\":-10},{\"deductionType\":2,\"count\":3,\"deductionScore\":-6},{\"deductionType\":3,\"count\":3,\"deductionScore\":-15},{\"deductionType\":4,\"count\":3,\"deductionScore\":-3}]","check_date":"2026-03-06","large_category_id":1084,"dept_id":20031,"checker_name":"Clara Mae Venturina"},
{"shopcheck_data_id":1961,"checker_post_code":"LKUS00000082","score":100,"opportunity_desc":"[]","check_date":"2026-03-08","large_category_id":1084,"dept_id":20010,"checker_name":"Shangxian Piao"},
{"shopcheck_data_id":1962,"checker_post_code":"LKUS00000082","score":81,"opportunity_desc":"[{\"deductionType\":2,\"count\":7,\"deductionScore\":-14},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5}]","check_date":"2026-03-09","large_category_id":1084,"dept_id":20035,"checker_name":"Wenny Lin"},
{"shopcheck_data_id":1963,"checker_post_code":"LKUS00000082","score":47,"opportunity_desc":"[{\"deductionType\":1,\"count\":2,\"deductionScore\":-10},{\"deductionType\":2,\"count\":4,\"deductionScore\":-8},{\"deductionType\":3,\"count\":3,\"deductionScore\":-15}]","check_date":"2026-03-09","large_category_id":1084,"dept_id":20031,"checker_name":"Clara Mae Venturina"},
{"shopcheck_data_id":1965,"checker_post_code":"LKUS00000083","score":100,"opportunity_desc":"[]","check_date":"2026-03-09","large_category_id":1084,"dept_id":20008,"checker_name":"Derson Liang"},
{"shopcheck_data_id":1966,"checker_post_code":"LKUS00000082","score":95,"opportunity_desc":"[{\"deductionType\":2,\"count\":2,\"deductionScore\":-4},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]","check_date":"2026-03-09","large_category_id":1084,"dept_id":1127,"checker_name":"Jian Ming Juo"},
{"shopcheck_data_id":1969,"checker_post_code":"LKUS00000082","score":73,"opportunity_desc":"[{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":2,\"count\":1,\"deductionScore\":-2}]","check_date":"2026-03-10","large_category_id":1084,"dept_id":20027,"checker_name":"Darwin Coronel"},
{"shopcheck_data_id":1971,"checker_post_code":"LKUS00000082","score":55,"opportunity_desc":"[{\"deductionType\":2,\"count\":9,\"deductionScore\":-18},{\"deductionType\":3,\"count\":5,\"deductionScore\":-25},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]","check_date":"2026-03-10","large_category_id":1084,"dept_id":20008,"checker_name":"Yaqing Zuo"},
{"shopcheck_data_id":1972,"checker_post_code":"LKUS00000082","score":92,"opportunity_desc":"[{\"deductionType\":2,\"count\":4,\"deductionScore\":-8}]","check_date":"2026-03-11","large_category_id":1084,"dept_id":20010,"checker_name":"Shangxian Piao"},
{"shopcheck_data_id":1973,"checker_post_code":"LKUS00000083","score":84,"opportunity_desc":"[{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5},{\"deductionType\":4,\"count\":1,\"deductionScore\":-1}]","check_date":"2026-03-15","large_category_id":1084,"dept_id":20008,"checker_name":"Derson Liang"},
{"shopcheck_data_id":1977,"checker_post_code":"LKUS00000082","score":96,"opportunity_desc":"[{\"deductionType\":2,\"count\":1,\"deductionScore\":-2},{\"deductionType\":4,\"count\":2,\"deductionScore\":-2}]","check_date":"2026-03-27","large_category_id":1084,"dept_id":20010,"checker_name":"Shangxian Piao"},
{"shopcheck_data_id":1979,"checker_post_code":"LKUS00000223","score":60,"opportunity_desc":"[{\"deductionType\":2,\"count\":5,\"deductionScore\":-10},{\"deductionType\":1,\"count\":1,\"deductionScore\":-5},{\"deductionType\":3,\"count\":1,\"deductionScore\":-5}]","check_date":"2026-03-31","large_category_id":1134,"dept_id":20035,"checker_name":"Eamonn Caballar"}
]''')

# Store master (luckyus_opshop.t_shop_info)
STORES = json.loads(r'''[
{"id":626,"dept_id":1127,"shop_no":"US00001","shop_name":"8th & Broadway","status":1,"set_up_time":"2025-06-30T04:00:00","off_time":null,"address":"755 Broadway, New York , NY 10003","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":627,"dept_id":1128,"shop_no":"US00002","shop_name":"28th & 6th","status":1,"set_up_time":"2025-06-30T04:00:00","off_time":null,"address":"800 6th Ave, New York, NY 10001","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":628,"dept_id":1131,"shop_no":"US00000","shop_name":"NJ Test Kitchen","status":1,"set_up_time":"2025-05-09T04:00:00","off_time":null,"address":"1 County Rd Unit B9, Secaucus, NJ 07094","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":630,"dept_id":1140,"shop_no":"US00003","shop_name":"100 Maiden Ln","status":1,"set_up_time":"2025-09-09T04:00:00","off_time":null,"address":"100 Maiden Ln, New York, NY 10038","operation_area":"LKUS00000052","tenant":"LKUS","test_flag":0},
{"id":631,"dept_id":1141,"shop_no":"US00005","shop_name":"54th & 8th","status":1,"set_up_time":"2025-08-24T04:00:00","off_time":null,"address":"901 8th Ave, New York, NY 10019","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1132,"dept_id":20007,"shop_no":"US99999","shop_name":"NJ Test Kitchen 2","status":1,"set_up_time":"2025-06-26T04:00:00","off_time":null,"address":"1 County Rd, unit b9, Secaucus, NJ 07094","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1133,"dept_id":20008,"shop_no":"US00008","shop_name":"33rd & 10th","status":1,"set_up_time":"2025-12-01T05:00:00","off_time":null,"address":"410 10th Ave, New York, NY 10001","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1134,"dept_id":20009,"shop_no":"US00007","shop_name":"108th & Broadway","status":1,"set_up_time":"2026-04-30T04:00:00","off_time":null,"address":"2799 Broadway, New York, NY 10025","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1135,"dept_id":20010,"shop_no":"US00006","shop_name":"102 Fulton","status":1,"set_up_time":"2025-08-28T04:00:00","off_time":null,"address":"102 Fulton St, New York, NY 10038","operation_area":"LKUS00000052","tenant":"LKUS","test_flag":0},
{"id":1136,"dept_id":20011,"shop_no":"US00004","shop_name":"37th & Broadway","status":1,"set_up_time":"2025-11-20T05:00:00","off_time":null,"address":"1375 Broadway, New York, NY 10018","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1138,"dept_id":20015,"shop_no":"US00009","shop_name":"48th & 3rd","status":2,"set_up_time":null,"off_time":null,"address":"770 3rd Ave, New York, NY 10017","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1139,"dept_id":20016,"shop_no":"US00010","shop_name":"154 Bleecker","status":1,"set_up_time":"2026-04-28T04:00:00","off_time":null,"address":"154 Bleecker St, New York, NY 10012","operation_area":"LKUS00000052","tenant":"LKUS","test_flag":0},
{"id":1140,"dept_id":20017,"shop_no":"US00011","shop_name":"180 Varick","status":2,"set_up_time":null,"off_time":null,"address":"180 Varick St, New York, NY 10014","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1141,"dept_id":20018,"shop_no":"CK0008","shop_name":"测试扩容","status":1,"set_up_time":"2025-07-22T10:00:00","off_time":null,"address":"测试扩容","operation_area":"IQA200000001","tenant":"IQA2","test_flag":0},
{"id":1142,"dept_id":20019,"shop_no":"US00012","shop_name":"16th & 6th","status":1,"set_up_time":"2026-03-23T04:00:00","off_time":null,"address":"555 6th Ave, New York, NY 10011","operation_area":"LKUS00000052","tenant":"LKUS","test_flag":0},
{"id":1143,"dept_id":20020,"shop_no":"US00013","shop_name":"Grand Central Terminal","status":2,"set_up_time":null,"off_time":null,"address":"52 Vanderbilt Ave, Lower Level, New York, NY 10017","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1144,"dept_id":20021,"shop_no":"US00014","shop_name":"25 Park Row","status":2,"set_up_time":null,"off_time":null,"address":"146 Chambers St, New York, NY 10007","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1145,"dept_id":20022,"shop_no":"US00015","shop_name":"41st & Lexington","status":1,"set_up_time":"2026-04-30T04:00:00","off_time":null,"address":"369 Lexington Ave, New York, NY 10017","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1146,"dept_id":20023,"shop_no":"US00016","shop_name":"Reade & Broadway","status":2,"set_up_time":null,"off_time":null,"address":"291 Broadway, New York, NY 10007","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1147,"dept_id":20024,"shop_no":"US00017","shop_name":"63rd & 3rd","status":2,"set_up_time":null,"off_time":null,"address":"219 9th Ave, New York, NY 10011","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1148,"dept_id":20025,"shop_no":"US00018","shop_name":"40th & 10th","status":2,"set_up_time":null,"off_time":null,"address":"55010th Ave, New York, NY 10018","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1149,"dept_id":20026,"shop_no":"US00019","shop_name":"29th & 3rd","status":1,"set_up_time":"2026-04-11T04:00:00","off_time":null,"address":"401 3rd Ave, New York, NY 10016","operation_area":"LKUS00000052","tenant":"LKUS","test_flag":0},
{"id":1150,"dept_id":20027,"shop_no":"US00020","shop_name":"21st & 3rd","status":1,"set_up_time":"2026-02-06T05:00:00","off_time":null,"address":"261 3rd Avenue, New York, NY 10010","operation_area":"LKUS00000052","tenant":"LKUS","test_flag":0},
{"id":1151,"dept_id":20028,"shop_no":"US00021","shop_name":"128 W 32nd St","status":2,"set_up_time":null,"off_time":null,"address":"128 W 32nd St, New York, NY 10001","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1152,"dept_id":20029,"shop_no":"US00022","shop_name":"23rd & 8th","status":2,"set_up_time":null,"off_time":null,"address":"244 8th Ave, New York, NY 10011","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1153,"dept_id":20030,"shop_no":"US00023","shop_name":"23rd & 1st","status":2,"set_up_time":null,"off_time":null,"address":"352 E 23rd St, New York, NY 10010","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1154,"dept_id":20031,"shop_no":"US00024","shop_name":"15th & 3rd","status":1,"set_up_time":"2025-12-14T05:00:00","off_time":null,"address":"147 3rd Ave, New York, NY 10003","operation_area":"LKUS00000052","tenant":"LKUS","test_flag":0},
{"id":1155,"dept_id":20032,"shop_no":"US00025","shop_name":"221 Grand","status":1,"set_up_time":"2025-12-15T05:00:00","off_time":null,"address":"221 Grand St, New York, NY 10013","operation_area":"LKUS00000052","tenant":"LKUS","test_flag":0},
{"id":1156,"dept_id":20034,"shop_no":"US00026","shop_name":"211 Schermerhorn","status":2,"set_up_time":null,"off_time":null,"address":"211 Schermerhorn St, Brooklyn, NY 11201","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1157,"dept_id":20035,"shop_no":"US00027","shop_name":"52nd & Madison","status":1,"set_up_time":"2026-02-26T05:00:00","off_time":null,"address":"488 Madison Ave, New York, NY 10022","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1158,"dept_id":20036,"shop_no":"US00035","shop_name":"35th & 5th","status":2,"set_up_time":null,"off_time":null,"address":"366 5th Avenue, New York, NY 10001","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1159,"dept_id":20046,"shop_no":"US99998","shop_name":"Shanghai Test Kitchen","status":1,"set_up_time":"2025-11-14T05:00:00","off_time":null,"address":"Unit 802, 15 W 38th St, New York, NY 10018","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1162,"dept_id":20054,"shop_no":"US00028","shop_name":"Jackson Ave - LIC","status":2,"set_up_time":null,"off_time":null,"address":"27-01 Jackson Ave, Long Island City, NY 11101","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0},
{"id":1163,"dept_id":20055,"shop_no":"US00029","shop_name":"148 Chambers","status":2,"set_up_time":null,"off_time":null,"address":"148 Chambers St, New York, NY 10007","operation_area":"LKUS00000041","tenant":"LKUS","test_flag":0}
]''')

# Q1 deduction-counts-by-inspection (for trend file)
Q1_DEDUCTIONS = json.loads(r'''[
{"shopcheck_data_id":1898,"deduction_type":1,"cnt":2},{"shopcheck_data_id":1898,"deduction_type":2,"cnt":11},{"shopcheck_data_id":1898,"deduction_type":4,"cnt":6},
{"shopcheck_data_id":1899,"deduction_type":2,"cnt":5},{"shopcheck_data_id":1899,"deduction_type":4,"cnt":1},
{"shopcheck_data_id":1900,"deduction_type":2,"cnt":2},
{"shopcheck_data_id":1901,"deduction_type":1,"cnt":2},{"shopcheck_data_id":1901,"deduction_type":2,"cnt":4},
{"shopcheck_data_id":1902,"deduction_type":1,"cnt":1},{"shopcheck_data_id":1902,"deduction_type":2,"cnt":3},{"shopcheck_data_id":1902,"deduction_type":4,"cnt":2},
{"shopcheck_data_id":1915,"deduction_type":2,"cnt":7},{"shopcheck_data_id":1915,"deduction_type":3,"cnt":1},{"shopcheck_data_id":1915,"deduction_type":4,"cnt":2},
{"shopcheck_data_id":1916,"deduction_type":2,"cnt":3},{"shopcheck_data_id":1916,"deduction_type":3,"cnt":1},
{"shopcheck_data_id":1918,"deduction_type":2,"cnt":8},{"shopcheck_data_id":1918,"deduction_type":3,"cnt":2},{"shopcheck_data_id":1918,"deduction_type":4,"cnt":2},
{"shopcheck_data_id":1922,"deduction_type":1,"cnt":2},{"shopcheck_data_id":1922,"deduction_type":2,"cnt":11},{"shopcheck_data_id":1922,"deduction_type":3,"cnt":2},{"shopcheck_data_id":1922,"deduction_type":4,"cnt":4},
{"shopcheck_data_id":1926,"deduction_type":2,"cnt":3},{"shopcheck_data_id":1926,"deduction_type":3,"cnt":1},{"shopcheck_data_id":1926,"deduction_type":4,"cnt":2},
{"shopcheck_data_id":1928,"deduction_type":1,"cnt":1},{"shopcheck_data_id":1928,"deduction_type":2,"cnt":4},{"shopcheck_data_id":1928,"deduction_type":3,"cnt":1},{"shopcheck_data_id":1928,"deduction_type":4,"cnt":2},
{"shopcheck_data_id":1931,"deduction_type":2,"cnt":8},{"shopcheck_data_id":1931,"deduction_type":3,"cnt":1},{"shopcheck_data_id":1931,"deduction_type":4,"cnt":4},
{"shopcheck_data_id":1932,"deduction_type":1,"cnt":2},{"shopcheck_data_id":1932,"deduction_type":2,"cnt":6},{"shopcheck_data_id":1932,"deduction_type":4,"cnt":1},
{"shopcheck_data_id":1933,"deduction_type":2,"cnt":9},
{"shopcheck_data_id":1940,"deduction_type":1,"cnt":1},{"shopcheck_data_id":1940,"deduction_type":2,"cnt":6},{"shopcheck_data_id":1940,"deduction_type":3,"cnt":2},{"shopcheck_data_id":1940,"deduction_type":4,"cnt":7},
{"shopcheck_data_id":1943,"deduction_type":1,"cnt":1},{"shopcheck_data_id":1943,"deduction_type":2,"cnt":9},{"shopcheck_data_id":1943,"deduction_type":3,"cnt":1},{"shopcheck_data_id":1943,"deduction_type":4,"cnt":4},
{"shopcheck_data_id":1946,"deduction_type":1,"cnt":1},{"shopcheck_data_id":1946,"deduction_type":2,"cnt":2},{"shopcheck_data_id":1946,"deduction_type":4,"cnt":3},
{"shopcheck_data_id":1956,"deduction_type":2,"cnt":5},{"shopcheck_data_id":1956,"deduction_type":4,"cnt":1},
{"shopcheck_data_id":1959,"deduction_type":1,"cnt":1},{"shopcheck_data_id":1959,"deduction_type":3,"cnt":1},
{"shopcheck_data_id":1960,"deduction_type":1,"cnt":2},{"shopcheck_data_id":1960,"deduction_type":2,"cnt":3},{"shopcheck_data_id":1960,"deduction_type":3,"cnt":3},{"shopcheck_data_id":1960,"deduction_type":4,"cnt":3},
{"shopcheck_data_id":1962,"deduction_type":2,"cnt":7},{"shopcheck_data_id":1962,"deduction_type":3,"cnt":1},
{"shopcheck_data_id":1963,"deduction_type":1,"cnt":2},{"shopcheck_data_id":1963,"deduction_type":2,"cnt":4},{"shopcheck_data_id":1963,"deduction_type":3,"cnt":3},
{"shopcheck_data_id":1966,"deduction_type":2,"cnt":2},{"shopcheck_data_id":1966,"deduction_type":4,"cnt":1},
{"shopcheck_data_id":1969,"deduction_type":1,"cnt":1},{"shopcheck_data_id":1969,"deduction_type":2,"cnt":1},
{"shopcheck_data_id":1971,"deduction_type":2,"cnt":9},{"shopcheck_data_id":1971,"deduction_type":3,"cnt":5},{"shopcheck_data_id":1971,"deduction_type":4,"cnt":2},
{"shopcheck_data_id":1972,"deduction_type":2,"cnt":4},
{"shopcheck_data_id":1973,"deduction_type":2,"cnt":5},{"shopcheck_data_id":1973,"deduction_type":3,"cnt":1},{"shopcheck_data_id":1973,"deduction_type":4,"cnt":1},
{"shopcheck_data_id":1977,"deduction_type":2,"cnt":1},{"shopcheck_data_id":1977,"deduction_type":4,"cnt":2},
{"shopcheck_data_id":1979,"deduction_type":1,"cnt":1},{"shopcheck_data_id":1979,"deduction_type":2,"cnt":5},{"shopcheck_data_id":1979,"deduction_type":3,"cnt":1}
]''')

# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------

# dept_id -> store info
STORE_BY_DEPT = {s["dept_id"]: s for s in STORES}

def store_code(dept_id):
    s = STORE_BY_DEPT.get(dept_id)
    return s["shop_no"] if s else f"DEPT-{dept_id}"

def store_name(dept_id):
    s = STORE_BY_DEPT.get(dept_id)
    return s["shop_name"] if s else f"(unknown dept {dept_id})"

def role_for(post_code, inspection_type, name=None):
    if post_code and post_code in POSTCODE_ROLE:
        return POSTCODE_ROLE[post_code]
    return ROLE_FALLBACK.get(inspection_type, "Unknown")

def parse_dt_counts(opp_desc_json):
    """Parse opportunity_desc JSON -> {deduction_type: count}."""
    if not opp_desc_json:
        return {}
    try:
        arr = json.loads(opp_desc_json)
    except Exception:
        return {}
    out = defaultdict(int)
    for x in arr:
        out[x.get("deductionType")] += x.get("count", 0)
    return out

def parse_total_deduction(opp_desc_json):
    if not opp_desc_json:
        return 0
    try:
        arr = json.loads(opp_desc_json)
    except Exception:
        return 0
    return sum(x.get("deductionScore", 0) for x in arr)


# ---------------------------------------------------------------------------
# Load April opportunity items from disk (parses MCP response wrapper)
# ---------------------------------------------------------------------------
def load_april_opportunities():
    path = RAW / "april_opportunities.json"
    raw = path.read_text(encoding="utf-8")
    wrapper = json.loads(raw)
    inner = wrapper[0]["text"]
    parsed = json.loads(inner)
    return parsed["rows"]

APR_OPPS = load_april_opportunities()

# ---------------------------------------------------------------------------
# Build maps
# ---------------------------------------------------------------------------
HEADER_BY_ID = {h["id"]: h for h in HEADERS}
REPORT_BY_DATA_ID_APR = {r["shopcheck_data_id"]: r for r in REPORTS_APR}
REPORT_BY_DATA_ID_Q1 = {r["shopcheck_data_id"]: r for r in REPORTS_Q1}

# April inspection IDs (from headers, deleted=0, large_category in 1084/1134/1184, in April 2026)
APR_INSPECTION_IDS = sorted(
    h["id"] for h in HEADERS
    if h["check_date"][:7] == "2026-04"
)

# ---------------------------------------------------------------------------
# CSV 1: april2026_inspection_summary.csv
# ---------------------------------------------------------------------------
def write_summary():
    path = OUT / "april2026_inspection_summary.csv"
    rows = []
    for h in HEADERS:
        if h["check_date"][:7] != "2026-04":
            continue
        iid = h["id"]
        rep = REPORT_BY_DATA_ID_APR.get(iid)
        type_zh, type_raw = TYPE_MAP[h["large_category_id"]]
        post = rep["checker_post_code"] if rep else None
        # Severity counts
        if rep:
            cnts = parse_dt_counts(rep["opportunity_desc"])
            score = rep["score"]
            total_ded = parse_total_deduction(rep["opportunity_desc"])
        else:
            cnts = {}
            score = ""
            total_ded = ""
        s_c = cnts.get(1, 0)
        m_c = cnts.get(3, 0)
        g_c = cnts.get(2, 0)
        l_c = cnts.get(4, 0)
        item_count = s_c + m_c + g_c + l_c
        rows.append({
            "inspection_id": iid,
            "store_code": store_code(h["dept_id"]),
            "store_name": store_name(h["dept_id"]),
            "inspection_date": h["check_date"],
            "inspection_type": type_zh,
            "inspection_type_raw": type_raw,
            "inspector_name": h["checker_name"],
            "inspector_role": role_for(post, type_zh, h["checker_name"]),
            "total_score": score,
            "total_deduction": total_ded,
            "item_count": item_count,
            "s_count": s_c,
            "m_count": m_c,
            "g_count": g_c,
            "l_count": l_c,
        })
    rows.sort(key=lambda r: (r["store_code"], r["inspection_date"], r["inspection_id"]))
    fields = list(rows[0].keys()) if rows else [
        "inspection_id","store_code","store_name","inspection_date","inspection_type",
        "inspection_type_raw","inspector_name","inspector_role","total_score",
        "total_deduction","item_count","s_count","m_count","g_count","l_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV 2: april2026_inspection_items.csv
# ---------------------------------------------------------------------------
def write_items():
    path = OUT / "april2026_inspection_items.csv"
    rows = []
    sev_order = {"S": 0, "M": 1, "G": 2, "L": 3}
    for opp in APR_OPPS:
        iid = opp["shopcheck_data_id"]
        h = HEADER_BY_ID.get(iid)
        if not h:
            continue
        type_zh, _ = TYPE_MAP[h["large_category_id"]]
        rep = REPORT_BY_DATA_ID_APR.get(iid)
        post = rep["checker_post_code"] if rep else None
        sev = SEV_MAP.get(opp["deduction_type"], str(opp["deduction_type"]))
        desc = opp.get("remark")
        if desc is None or str(desc).strip() == "":
            desc = "(无描述)"
        rows.append({
            "item_id": opp["opp_id"],
            "inspection_id": iid,
            "store_code": store_code(h["dept_id"]),
            "store_name": store_name(h["dept_id"]),
            "inspection_date": h["check_date"],
            "inspection_type": type_zh,
            "inspector_name": h["checker_name"],
            "module_name": opp.get("module_name") or "",
            "module_subcategory": opp.get("leaf_cat_name") or "",
            "clause_number": str(opp["check_item_id"]),
            "issue_description": desc,
            "severity": sev,
            "deduction_points": opp["score_config"],
        })
    # Sort: store, date, severity (S,M,G,L), most-negative deduction first
    rows.sort(key=lambda r: (
        r["store_code"], r["inspection_date"],
        sev_order.get(r["severity"], 99),
        (r["deduction_points"] if isinstance(r["deduction_points"], (int, float)) else 0),
    ))
    fields = ["item_id","inspection_id","store_code","store_name","inspection_date",
              "inspection_type","inspector_name","module_name","module_subcategory",
              "clause_number","issue_description","severity","deduction_points"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV 3: april2026_store_master.csv
# ---------------------------------------------------------------------------
def write_store_master():
    path = OUT / "april2026_store_master.csv"
    inspected_april = set()
    for h in HEADERS:
        if h["check_date"][:7] == "2026-04":
            inspected_april.add(h["dept_id"])

    rows = []
    for s in STORES:
        # Include US tenant + dept_ids that had April inspections (covers 1141 IQA2 test shop)
        if s["tenant"] != "LKUS" and s["dept_id"] not in inspected_april:
            continue
        # status: 1=active, 2=inactive/planned, others=closed
        st = s["status"]
        status_label = "active" if st == 1 else ("inactive" if st == 2 else "closed")
        # Test flag overrides
        if s.get("test_flag") == 1 or s["shop_no"].startswith("US999") or s["shop_no"].startswith("CK"):
            status_label += " (test/internal)"
        opening = s.get("set_up_time") or ""
        if opening:
            opening = opening[:10]
        rows.append({
            "store_id": s["id"],
            "store_code": s["shop_no"],
            "store_name": s["shop_name"],
            "address": s.get("address") or "",
            "status": status_label,
            "opening_date": opening,
            "region": s.get("operation_area") or "",
            "inspected_in_april": "Yes" if s["dept_id"] in inspected_april else "No",
        })
    rows.sort(key=lambda r: (r["store_code"]))
    fields = ["store_id","store_code","store_name","address","status",
              "opening_date","region","inspected_in_april"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV 4: april2026_inspector_trend.csv
# ---------------------------------------------------------------------------
def write_inspector_trend():
    path = OUT / "april2026_inspector_trend.csv"
    counters = defaultdict(lambda: {"jan":0, "feb":0, "mar":0, "apr":0,
                                    "types": defaultdict(int), "post_codes": defaultdict(int)})
    for h in HEADERS:
        ym = h["check_date"][:7]
        bucket = {"2026-01":"jan","2026-02":"feb","2026-03":"mar","2026-04":"apr"}.get(ym)
        if not bucket:
            continue
        name = h["checker_name"]
        counters[name][bucket] += 1
        type_zh, _ = TYPE_MAP[h["large_category_id"]]
        counters[name]["types"][type_zh] += 1

    # Pull post codes from reports (Q1 + Apr) to assign role
    name_post = {}
    for r in REPORTS_Q1 + REPORTS_APR:
        if r.get("checker_name") and r.get("checker_post_code"):
            name_post[r["checker_name"]] = r["checker_post_code"]
    # Add from APR report list (Apr reports had no checker_name field — use header)
    for h in HEADERS:
        if h["check_date"][:7] != "2026-04":
            continue
        rep = REPORT_BY_DATA_ID_APR.get(h["id"])
        if rep and h["checker_name"] and rep.get("checker_post_code"):
            name_post.setdefault(h["checker_name"], rep["checker_post_code"])

    rows = []
    for name, c in counters.items():
        total = c["jan"] + c["feb"] + c["mar"] + c["apr"]
        typical = max(c["types"], key=c["types"].get) if c["types"] else ""
        rows.append({
            "inspector_name": name,
            "inspector_role": role_for(name_post.get(name), typical, name),
            "jan_count": c["jan"],
            "feb_count": c["feb"],
            "mar_count": c["mar"],
            "apr_count": c["apr"],
            "total_q1_apr": total,
            "typical_inspection_type": typical,
        })
    rows.sort(key=lambda r: (-r["total_q1_apr"], r["inspector_name"]))
    fields = ["inspector_name","inspector_role","jan_count","feb_count",
              "mar_count","apr_count","total_q1_apr","typical_inspection_type"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path

# ---------------------------------------------------------------------------
# CSV 5: jan_to_apr2026_trend_summary.csv
# ---------------------------------------------------------------------------
def write_trend_summary():
    path = OUT / "jan_to_apr2026_trend_summary.csv"

    # For each (month, inspection_type): count, distinct stores, avg score, S/M/G/L totals, item_count
    by_key = defaultdict(lambda: {"insp_ids": set(), "stores": set(),
                                  "scores": [], "S":0, "M":0, "G":0, "L":0, "items":0})

    # Helper: get reports for an inspection from either Apr or Q1 collection
    def get_report(iid):
        return REPORT_BY_DATA_ID_APR.get(iid) or REPORT_BY_DATA_ID_Q1.get(iid)

    for h in HEADERS:
        ym = h["check_date"][:7]
        if ym not in {"2026-01","2026-02","2026-03","2026-04"}:
            continue
        type_zh, _ = TYPE_MAP[h["large_category_id"]]
        rep = get_report(h["id"])
        # Severity counts come from JSON desc; for Q1 fallback to Q1_DEDUCTIONS
        if rep:
            cnts = parse_dt_counts(rep["opportunity_desc"])
            score = rep["score"]
        else:
            cnts = {}
            for d in Q1_DEDUCTIONS:
                if d["shopcheck_data_id"] == h["id"]:
                    cnts[d["deduction_type"]] = d["cnt"]
            score = None
        s_c = cnts.get(1, 0); m_c = cnts.get(3, 0); g_c = cnts.get(2, 0); l_c = cnts.get(4, 0)

        key = (ym, type_zh)
        bucket = by_key[key]
        bucket["insp_ids"].add(h["id"])
        bucket["stores"].add(h["dept_id"])
        if score is not None:
            bucket["scores"].append(score)
        bucket["S"] += s_c
        bucket["M"] += m_c
        bucket["G"] += g_c
        bucket["L"] += l_c
        bucket["items"] += s_c + m_c + g_c + l_c

    rows = []
    months = ["2026-01","2026-02","2026-03","2026-04"]
    types  = ["门店自检","QA审计","区经检查"]
    for m in months:
        for t in types:
            b = by_key.get((m, t))
            if b is None:
                rows.append({"month":m,"inspection_type":t,"inspection_count":0,
                             "stores_covered":0,"avg_score":"",
                             "s_total":0,"m_total":0,"g_total":0,"l_total":0,
                             "total_deduction_items":0})
            else:
                avg = round(sum(b["scores"])/len(b["scores"]), 1) if b["scores"] else ""
                rows.append({"month":m,"inspection_type":t,
                             "inspection_count": len(b["insp_ids"]),
                             "stores_covered": len(b["stores"]),
                             "avg_score": avg,
                             "s_total": b["S"], "m_total": b["M"], "g_total": b["G"], "l_total": b["L"],
                             "total_deduction_items": b["items"]})

    fields = ["month","inspection_type","inspection_count","stores_covered","avg_score",
              "s_total","m_total","g_total","l_total","total_deduction_items"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows), path


# ---------------------------------------------------------------------------
# Schema notes file
# ---------------------------------------------------------------------------
SCHEMA_NOTES = """\
April 2026 Inspection Export — Schema Notes

DISCOVERY
=========
- Database server (mcp-db-gateway): aws-luckyus-opqualitycontrol-rw
- Database (MySQL):                  luckyus_opqualitycontrol
- Tables found (rows):
    t_shopcheck_data            221 rows  门店检查数据 (inspection header)
    t_shopcheck_opportunity    1113 rows  门店检查机会点 (deduction items)
    t_shopcheck_report          201 rows  门店检查报告 (scoring summary)
    t_shopcheck_item_config    1289 rows  门店检查项配置 (canonical clause text)
    t_shopcheck_category_config 616 rows  门店检查类配置 (module hierarchy)
    t_shopcheck_tag             363 rows  门店检查标签 (English module labels)
    t_shopcheck_config_snapshot 2506 rows  inspection config snapshot per data row
- Store master found at:             aws-luckyus-opshop-rw / luckyus_opshop.t_shop_info  (519 rows)

NOTE on the user's "empapp" naming
==================================
The empapp 门店稽核系统 surfaces in this database under the prefix `t_shopcheck_*`.
There is no dedicated "empapp" database in the mcp-db-gateway server list.
The opqualitycontrol cluster owns both shopcheck (audits) and other QA data
(t_cs_sheet customer service tickets, t_duty_task_sheet 门店执勤, etc.).

INSPECTION-TYPE MAPPING (large_category_id)
===========================================
Resolved from t_shopcheck_data.large_category_name + cross-reference with
t_shopcheck_category_config (top-level rows where parent_id=0):

   id 1084 'Store food safety self-check'   -> 门店自检   (Store Self-Inspection)
   id 1134 'Store food safety audit'        -> QA审计     (QA Audit)
   id 1184 'Area food safety Check'         -> 区经检查   (Area Manager Inspection)

Excluded historical / test categories (not in scope):
   id  924 'IQA2Test_门店营业检查'           -> internal QA2 test data
   id  928 'US Store Food Safety Audit'      -> superseded by 1134
   id 1075 'Test', 1080 'test'               -> test rows
   id  977 'US Area food safety Check'       -> superseded by 1184
   id 1026 'Store food safety self-check'    -> superseded by 1084

SEVERITY MAPPING (S / M / G / L) — INFERRED
===========================================
The source `t_shopcheck_item_config.deduction_type` is a tinyint with values 1-4
(plus rare 9). It is NOT directly labeled S/M/G/L. We derive the mapping from:
  (a) the 'content' prefix on item_config rows: '(S)' and '(M)' literal markers, and
  (b) the typical score_config values:
       deduction_type 1 -> -5    (severe)
       deduction_type 2 -> -2    (general — most common, 405 items)
       deduction_type 3 -> -5    (major)
       deduction_type 4 -> -1    (light, 82 items)

Final mapping used in the CSV `severity` column:
       deduction_type 1 -> S
       deduction_type 2 -> G
       deduction_type 3 -> M
       deduction_type 4 -> L
       deduction_type 9 -> '9'  (kept literal — only 2 items repo-wide, both score_config=0)

CATEGORY HIERARCHY
==================
Three levels under each large_category_id (e.g. 1134):
   level-1 = inspection type itself (1134 'Store food safety audit')
   level-2 = wrapper "Store food safety self-check" (1475)
   level-3 = MODULE  e.g. 1480 'Employees' Health and Personal Hygiene'
                       1494 'Cleaning and Sanitation'
                       1502 'Sanitation and Hygiene'
                       1504 'Temperature Control / Expiration Date Management.'
                       1487 'Process Control', 1485 'Approved Supplier', 1476 'Document Record',
                       1509 'Maintenance of Equipment', 1512 'Facility', 1517 'Pests Control',
                       1521 'Site Security', 1523 'Workplace Safety',
                       1525 'Requirements on Store Audit Management Procedures'
   level-4 = SUBCATEGORY (leaf), e.g. 1481 'Employees' Health', 1482 'Personal Hygiene',
                                       1497 'Equipment and utensils', 1490 'Cross-Contamination',
                                       1477 'Licenses and certificates', 1478 'Personal certificate'.

Same module skeleton repeats under 1084 (path 1084,1579,*) and 1184 (path 1184,1630,*).

For the CSV `module_name` column the script emits the level-3 module name; the
level-4 leaf name goes to `module_subcategory`. Names are stored in English in
this US-tenant deployment (the Chinese-name examples in the task brief do not
appear in the source — those are aspirational). All names preserved verbatim.

INSPECTOR ROLE BY POST CODE (derived from data)
================================================
   LKUS00000076 -> Area Operations Manager     (Daniel Chu, Jung Han Liang)
   LKUS00000078 -> Senior QA Manager           (Yu Jiang)
   LKUS00000223 -> Senior QA Manager           (Eamonn Caballar)
   LKUS00000082 -> Store Manager
   LKUS00000083 -> Assistant Store Manager
   LKUS00000098 -> Shift Supervisor / Trainer

KEY JOIN GRAPH
==============
  t_shopcheck_data.id  ===  t_shopcheck_opportunity.shopcheck_data_id
  t_shopcheck_data.id  ===  t_shopcheck_report.shopcheck_data_id
  t_shopcheck_opportunity.check_item_id  ==  t_shopcheck_item_config.id
  t_shopcheck_item_config.category_config_id  ==  t_shopcheck_category_config.id (leaf)
  t_shopcheck_category_config.parent_id        ==  t_shopcheck_category_config.id (module)
  t_shopcheck_data.dept_id  ==  t_shop_info.dept_id        (store master)
  t_shop_info.shop_no                                       store_code (US00xxx)

April 2026 SCOPE COUNTS (deleted=0, large_category in 1084,1134,1184)
=====================================================================
  inspection rows (t_shopcheck_data)               : 63
  reports (t_shopcheck_report)                     : 59  (4 inspections never had report rows; status=0 incomplete)
  deduction items (t_shopcheck_opportunity)        : ~330 lines

SAMPLE DATA (5 rows each — see actual CSV outputs for full data)
=================================================================
[See april2026_inspection_summary.csv and april2026_inspection_items.csv for full content.]
"""

def write_schema_notes():
    path = OUT / "april2026_schema_notes.txt"
    path.write_text(SCHEMA_NOTES, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Validation queries (replicated against in-memory data)
# ---------------------------------------------------------------------------
def run_validations():
    out_lines = []
    def emit(s=""):
        out_lines.append(s)
        print(s)

    emit("="*80)
    emit("APRIL 2026 INSPECTION DATA — VALIDATION OUTPUT")
    emit("Source: aws-luckyus-opqualitycontrol-rw / luckyus_opqualitycontrol")
    emit("="*80)

    # Filter helpers
    apr_headers = [h for h in HEADERS if h["check_date"][:7] == "2026-04"]
    apr_h_by_id = {h["id"]: h for h in apr_headers}

    # ---- A. April count by type ----
    emit("\n--- A. April inspection count by type ---")
    by_t = defaultdict(lambda: {"cnt":0, "stores":set()})
    for h in apr_headers:
        t_zh, _ = TYPE_MAP[h["large_category_id"]]
        by_t[t_zh]["cnt"] += 1
        by_t[t_zh]["stores"].add(h["dept_id"])
    emit(f"{'inspection_type':16s} {'cnt':>5s} {'stores':>7s}")
    for t in ["门店自检","QA审计","区经检查"]:
        b = by_t.get(t, {"cnt":0,"stores":set()})
        emit(f"{t:16s} {b['cnt']:5d} {len(b['stores']):7d}")
    total = sum(b['cnt'] for b in by_t.values())
    emit(f"{'TOTAL':16s} {total:5d}")

    # ---- B. April severity distribution ----
    emit("\n--- B. April severity distribution (across all deduction items) ---")
    sev_cnt = defaultdict(int)
    sev_ded = defaultdict(int)
    for opp in APR_OPPS:
        if opp["shopcheck_data_id"] not in apr_h_by_id:
            continue
        sev = SEV_MAP.get(opp["deduction_type"], str(opp["deduction_type"]))
        sev_cnt[sev] += 1
        sev_ded[sev] += opp["score_config"] or 0
    emit(f"{'severity':10s} {'cnt':>5s} {'total_deduction':>16s}")
    for s in ["S","M","G","L"]:
        emit(f"{s:10s} {sev_cnt.get(s,0):5d} {sev_ded.get(s,0):16d}")
    other_sev = sum(c for k,c in sev_cnt.items() if k not in {"S","M","G","L"})
    if other_sev:
        emit(f"{'OTHER':10s} {other_sev:5d}")

    # ---- C. April distinct store count ----
    emit("\n--- C. April distinct stores inspected ---")
    apr_depts = {h["dept_id"] for h in apr_headers}
    emit(f"stores_inspected_april = {len(apr_depts)}")

    # ---- D. Same-store cross-type comparisons ----
    emit("\n--- D. Stores with multiple inspection TYPES in April ---")
    by_dept = defaultdict(set)
    for h in apr_headers:
        t_zh, _ = TYPE_MAP[h["large_category_id"]]
        by_dept[h["dept_id"]].add(t_zh)
    multi = [(d, types) for d, types in by_dept.items() if len(types) >= 2]
    multi.sort(key=lambda x: (-len(x[1]), store_code(x[0])))
    emit(f"{'store_code':10s} {'store_name':25s} {'type_variety':12s}  types_seen")
    for d, types in multi:
        emit(f"{store_code(d):10s} {store_name(d)[:25]:25s} {len(types):12d}  {' / '.join(sorted(types))}")
    if not multi:
        emit("(none)")

    # ---- E. Same-day repeat inspections / score swings ≥ 20 ----
    emit("\n--- E. Same-store same-day repeats / large score swings (≥20 pts) ---")
    by_dept_date = defaultdict(list)
    for h in apr_headers:
        rep = REPORT_BY_DATA_ID_APR.get(h["id"])
        score = rep["score"] if rep else None
        by_dept_date[(h["dept_id"], h["check_date"])].append({
            "iid": h["id"], "name": h["checker_name"], "score": score,
            "type": TYPE_MAP[h["large_category_id"]][0]
        })
    flagged = []
    for (dept, date), arr in by_dept_date.items():
        scored = [x["score"] for x in arr if isinstance(x["score"], (int,float))]
        swing = (max(scored) - min(scored)) if len(scored) >= 2 else 0
        if len(arr) >= 2 or swing >= 20:
            flagged.append((dept, date, arr, swing))
    flagged.sort(key=lambda x: (store_code(x[0]), x[1]))
    if flagged:
        emit(f"{'store_code':10s} {'date':12s} {'cnt':>3s} {'swing':>5s}  inspectors / scores")
        for dept, date, arr, swing in flagged:
            insp = " | ".join(f"{x['name']}({x['type']}, score={x['score']})" for x in arr)
            emit(f"{store_code(dept):10s} {date:12s} {len(arr):3d} {swing:5d}  {insp}")
    else:
        emit("(none)")

    # ---- F. Q1+April trend ----
    emit("\n--- F. Q1+April trend (month × type) ---")
    by_mon_type = defaultdict(lambda: {"cnt":0, "stores":set()})
    for h in HEADERS:
        ym = h["check_date"][:7]
        if ym not in {"2026-01","2026-02","2026-03","2026-04"}:
            continue
        t_zh, _ = TYPE_MAP[h["large_category_id"]]
        by_mon_type[(ym, t_zh)]["cnt"] += 1
        by_mon_type[(ym, t_zh)]["stores"].add(h["dept_id"])
    emit(f"{'month':10s} {'type':12s} {'cnt':>5s} {'stores':>7s}")
    for ym in ["2026-01","2026-02","2026-03","2026-04"]:
        for t in ["门店自检","QA审计","区经检查"]:
            b = by_mon_type.get((ym, t), {"cnt":0,"stores":set()})
            emit(f"{ym:10s} {t:12s} {b['cnt']:5d} {len(b['stores']):7d}")

    # ---- Special checks ----
    emit("\n" + "="*80)
    emit("SPECIAL CHECKS")
    emit("="*80)

    qa_count = by_t.get("QA审计", {"cnt":0})["cnt"]
    area_count = by_t.get("区经检查", {"cnt":0})["cnt"]
    if qa_count == 0:
        emit("WARNING: Zero QA audits in April 2026")
    else:
        emit(f"INFO: QA审计 count in April = {qa_count} (NOT zero — contradicts the prior context).")
    if area_count == 0:
        emit("WARNING: Zero area manager inspections in April 2026 (4th consecutive month)")
    else:
        emit(f"INFO: 区经检查 count in April = {area_count} (NOT zero — contradicts the prior context).")

    # Cross-type stores already handled in D

    # April vs March store coverage
    mar_depts = {h["dept_id"] for h in HEADERS if h["check_date"][:7] == "2026-03"}
    emit(f"\nApril active store count (distinct dept_id with inspection): {len(apr_depts)}")
    emit(f"March active store count (distinct dept_id with inspection): {len(mar_depts)}")
    emit(f"  -> April covered {len(apr_depts - mar_depts)} stores not inspected in March: " +
         ", ".join(sorted(store_code(d) for d in apr_depts - mar_depts)))
    emit(f"  -> March covered {len(mar_depts - apr_depts)} stores not inspected in April: " +
         ", ".join(sorted(store_code(d) for d in mar_depts - apr_depts)))

    # Yu Jiang vs Eamonn Caballar
    yj = {ym: 0 for ym in ["2026-01","2026-02","2026-03","2026-04"]}
    ec = dict(yj)
    for h in HEADERS:
        ym = h["check_date"][:7]
        if ym not in yj: continue
        if h["checker_name"] == "Yu Jiang": yj[ym] += 1
        if h["checker_name"] == "Eamonn Caballar": ec[ym] += 1
    emit("\nQA inspector workload by month:")
    emit(f"  Yu Jiang        : Jan={yj['2026-01']}  Feb={yj['2026-02']}  Mar={yj['2026-03']}  Apr={yj['2026-04']}")
    emit(f"  Eamonn Caballar : Jan={ec['2026-01']}  Feb={ec['2026-02']}  Mar={ec['2026-03']}  Apr={ec['2026-04']}")

    # Persist
    (OUT / "april2026_validation_output.txt").write_text("\n".join(out_lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    summary_n, summary_p = write_summary()
    items_n,   items_p   = write_items()
    stores_n,  stores_p  = write_store_master()
    insp_n,    insp_p    = write_inspector_trend()
    trend_n,   trend_p   = write_trend_summary()
    schema_p             = write_schema_notes()

    print(f"WROTE {summary_n} rows -> {summary_p}")
    print(f"WROTE {items_n} rows -> {items_p}")
    print(f"WROTE {stores_n} rows -> {stores_p}")
    print(f"WROTE {insp_n} rows -> {insp_p}")
    print(f"WROTE {trend_n} rows -> {trend_p}")
    print(f"WROTE schema notes  -> {schema_p}")
    print()
    run_validations()
