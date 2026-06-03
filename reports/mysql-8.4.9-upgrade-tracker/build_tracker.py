#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the MySQL 8.0.45 -> 8.4.9 MAJOR-version upgrade tracking table.

Source of fields:
  - Per-instance metadata (db list, services, service level, spec, memory, swap,
    business group, R&D owner, batch) carried from the completed 8.0.41/8.0.40 -> 8.0.45
    minor-upgrade tracker (April-May 2026).
  - 当前版本 set to 8.0.45 (verified live 2026-06-03: full fleet on 8.0.45).
  - 数据库大小 refreshed live via information_schema 2026-06-03 (mcp-db-gateway).
    Exception: ilsopdevopsdata is not exposed via the gateway -> May figure (20.00 MB) carried.

NOTE: this is a MAJOR version upgrade (8.0 -> 8.4 LTS), NOT a minor patch like 8.0.41->8.0.45.
See the report preamble for the breaking-change pre-flight checklist.
"""
import csv

CUR = "8.0.45"
TGT = "8.4.9"

# columns per row:
# seq, instance, dblist, services, level, spec, mem_gb, avail_mb, swap_mb, size, group, owner, batch, note
ROWS = [
 (1,"ldas01","luckyus_ldas_slowquery\nluckyus_db_collection","idataccm\nidbtask\nidbcollect","L2\nL1\nL2","db.t4g.large",8,649,219,"127.64 GB","架构\n运维","张杨","第1批","原 8.0.41，已随车队升至 8.0.45；major 升级需新建 mysql8.4 参数组"),
 (2,"ilsopdevopsdata","luckyus_ilsopdevopsdata","ilsopdevopsdata","L2","db.t4g.micro",1,116,375,"20.00 MB","质量效能","夏文涛","第1批","大小为 5月基线（未经 gateway 暴露，未刷新）"),
 (3,"iluckyhealth","luckyus_iluckyhealth","iluckyhealth","L2","db.t3.small",2,66,868,"34.66 GB","运维","叶荣海","第1批","可用内存仅 66MB，车队最低；major 升级 Multi-AZ failover 内存压力风险高"),
 (4,"ldas","luckyus_dbmsdbsearch\nluckyus_ldas_cmdb\nluckyus_ozono\nluckyus_apigatewayadmin\nluckyus_ldas_nacos\nluckyus_ikafadmin","ildbquery\nldascmdb\nluckyozono\nluckyapigatewayadmin\nldasnacos\nikafadmin","L1\nL1\nL2\nL2","db.t4g.large",8,1065,327,"1.58 GB","架构\n运维","张杨\n孔增\n金盛昌\n张黎明\n翁延海","第1批","8.0.45 升级曾多次部署失败、参数组缺 lower_case_table_names；8.4 必须新建 mysql8.4 参数组且 lctn 创建后不可改"),
 (5,"ijumpserver","luckyus_ijumpserver_jumpserver","ijumpserver","L1","db.t4g.micro",1,96,627,"153.58 MB","信息安全","刘成锡","第1批",""),
 (6,"devops","luckyus_ilopamanager\nluckyus_uam\nluckyus_authservice\nluckyus_iluckyptsweb\nluckyus_auth\nluckyus_izeus\nluckyus_umbgrafana","izeusanomaly\nizeusmetric\nizeusalert\nizeusnotice\nizeusreceiver\nizeushome\nilopamanager\nlauthservice\nluckyuam\numbgrafana\nluckyauth","L1\nL2","db.t4g.medium",4,1604,9,"343.14 MB","质量效能\n运维","林鑫涛\n吴心一\n徐博轩\n杨涛\n姚清居\n桂升斌\n吴春林","第1批","存储 gp2；含 uam/auth 鉴权库 —— 重点核查 mysql_native_password 用户"),
 (7,"framework01","luckyus_lcp_noahusercenter\nluckyus_lcp_apiserver\nluckyus_nacos\nluckyus_isentineldashboard\nluckyus_iluckyenvsystemweb\nluckyus_koalaadmin\nluckyus_zkdoctor\nluckyus_kbx\nluckyus_horae\nluckyus_bsportal\nluckyus_sddl_platform\nluckyus_gaea","ucpmanagement\nluckynacos\nisentineldashboard\niluckyenvsystemweb\nkoalaadmin\nizkdoctor\nkbx\nhorae\nluckybsportal\nluckysddladmin\nluckygaea","L1\nL2","db.t4g.medium",4,1601,32,"511.50 MB","架构","车永生\n罗宁\n黄国仲\n林正权\n王卫\n张隆洋\n刘俊琪","第1批","12 库 283 表；含 Nacos 配置中心 —— 升级期间确认配置中心连接驱动兼容 caching_sha2_password"),
 (8,"framework02","luckyus_src\nluckyus_target\nluckyus_iluckyflowadmin\nluckyus_datalink\nluckyus_ihmonitorconsole\nluckyus_onepiececonsole\nluckyus_chronusconsole\nluckyus_ilkm","iluckyflowadmin\nluckydatalink\nihmonitorconsole\nonepiececonsole\nonepiecesync\nchronusconsole\nchronusreporter\nchronussharding\nilkm","L2\nL1","db.t4g.medium",4,997,88,"3.32 GB","架构","罗宁\n林正权\n张黎明\n代俊健\n王卫","第1批",""),
 (9,"upush","luckyus_iupushsms\nluckyus_iupushemail\nluckyus_iupushusercenter\nluckyus_iupushapp\nluckyus_iupushaid\nluckyus_iupushadmin\nluckyus_mdm\nluckyus_imdmext\nluckyus_mdmadmin","iupushsms\niupushemail\niupushusercenter\niupushapp\niupushaid\niupushadmin\nluckymdm\nimdmext\nluckymdmadmin","L1","db.t4g.medium",4,256,335,"20.11 GB","架构","罗宁\n林智贤\n刘洋","第1批","可用内存偏低 256MB；上轮因 datalink 续传 binlog 问题暂缓，本轮蓝绿前需复核"),
 (10,"iotplatform","luckyus_iot_platform","iotiplatformorderapi\niotiplatformmanagement\niotiplatformservice","L1\nL1\nL1","db.t4g.medium",4,1504,8,"692.48 MB","AIot","李晨端\n左达奇","第1批","上轮因 datalink 续传 binlog 问题暂缓，本轮蓝绿前需复核"),
 (11,"icyberdata","luckyus_icyberdata_nacos\nluckyus_icyberdata_user\nluckyus_icyberdata","icyberdata","L1","db.t4g.medium",4,676,1423,"26.11 GB","大数据","田洪彬","第1批","最大存储 635GB；Swap 1423MB"),
 (12,"iluckydorisops","luckyus_iluckydorisops","iluckydorisops","L2","db.t4g.micro",1,124,405,"8.16 MB","大数据","苏晓博","第1批",""),
 (13,"scm-wmssimulate","luckyus_scm_wmssimulate","iscmwmssimulate","L2","db.t4g.micro",1,111,534,"44.41 MB","国际供应链","方思扬","第2批",""),
 (14,"fichargecontrol","luckyus_fi_chargecontrol","ifichargecontrolservice","L2","db.t4g.micro",1,105,559,"51.70 MB","国际公共平台","尤志杰","第2批",""),
 (15,"ifiaccounting","luckyus_ifiaccounting","ifiaccounting","L2","db.t4g.micro",1,99,871,"323.23 MB","国际公共平台","尤志杰","第2批",""),
 (16,"iopocp","luckyus_iopocp","iopocp","L2","db.t4g.micro",1,96,622,"2.17 GB","国际运营","陈培浩","第2批",""),
 (17,"opqualitycontrol","luckyus_opqualitycontrol","iopqualitycontrol","L2","db.t4g.micro",1,90,754,"707.34 MB","国际运营","陈培浩","第2批",""),
 (18,"oplog","luckyus_oplog","iopdaq","L2","db.t4g.micro",1,110,410,"8.13 MB","国际运营","张少群","第2批",""),
 (19,"iadmin","luckyus_iadmin","iadmin","L1","db.t4g.micro",1,113,511,"129.11 MB","国际公共平台","陈亮","第3批",""),
 (20,"ibizconfigcenter","luckyus_ibizconfigcenter","ibizconfigcenter","L1","db.t4g.micro",1,116,435,"32.55 MB","国际公共平台","陈亮","第3批",""),
 (21,"igers","luckyus_igers","igers","L1","db.t4g.micro",1,118,401,"8.22 MB","国际公共平台","陈亮","第3批",""),
 (22,"iluckyauthapi","luckyus_iluckyauthapi","iluckyauthapi","L1","db.t4g.micro",1,112,408,"8.06 MB","国际公共平台","陈亮","第3批","鉴权服务 —— 重点核查 mysql_native_password 用户与连接驱动"),
 (23,"ibillingcentersrv","luckyus_ibillingcenterservice","ibillingcenterservice","L1","db.t4g.micro",1,104,670,"1.76 GB","国际公共平台","陈亮","第3批",""),
 (24,"iehr","luckyus_iehr","iehr","L1","db.t4g.micro",1,109,554,"40.64 MB","国际公共平台","陈亮","第3批",""),
 (25,"iopenlinker","luckyus_iopenlinker","iopenlinkeradmin\niopenlinker","L1","db.t4g.micro",1,117,493,"124.00 MB","国际营销增长","张晓松","第3批",""),
 (26,"iopenservice","luckyus_iopenservice","iopenservice","L1","db.t4g.micro",1,120,408,"8.34 MB","国际公共平台","陈亮","第3批",""),
 (27,"iopshopexpand","luckyus_iopshopexpand","iopshopexpand","L1","db.t4g.micro",1,115,423,"8.86 MB","国际运营","陈培浩","第3批",""),
 (28,"iunifiedreconcile","luckyus_iunifiedreconcile","iunifiedreconcile","L1","db.t4g.micro",1,126,426,"11.92 MB","国际公共平台","陈亮\n陈洪君","第3批",""),
 (29,"mfranchise","luckyus_mfranchise","imfranchiseservice","L1","db.t4g.micro",1,122,457,"10.67 MB","国际公共平台","陈亮\n陈洪君","第3批",""),
 (30,"iworkflowmidlayer","luckyus_iworkflowmidlayer","imessageflow\niworkflowmidlayer","L1\nL1","db.t4g.medium",4,525,218,"6.29 GB","国际公共平台","陈亮\n陈洪君","第3批","1/31 发生过 innodb_buffer_pool_size 被缩减事故，升级后必须验证 buffer pool 配置"),
 (31,"scm-asset","luckyus_scm_asset","iscmasset","L1","db.t4g.micro",1,108,594,"25.72 MB","国际供应链","方思扬","第3批",""),
 (32,"scm-openapi","luckyus_scm_openapi","iscmopenapi","L1","db.t4g.micro",1,116,577,"165.69 MB","国际供应链","方思扬","第3批",""),
 (33,"scm-plan","luckyus_scm_plan","iscmplan","L1","db.t4g.micro",1,119,472,"13.03 MB","国际供应链","方思扬","第3批",""),
 (34,"scm-ordering","luckyus_scm_ordering","iscmordering","L1","db.t4g.micro",1,90,771,"513.42 MB","国际供应链","方思扬","第3批",""),
 (35,"scm-purchase","luckyus_scm_purchase","iscmpurchase","L1","db.t4g.micro",1,101,799,"159.84 MB","国际供应链","方思扬","第3批",""),
 (36,"scm-wds","luckyus_scm_wds","iscmwds","L1","db.t4g.micro",1,102,720,"214.83 MB","国际供应链","方思扬","第3批",""),
 (37,"scmsrm","luckyus_scm_srm","iscmsrm","L1","db.t4g.micro",1,104,733,"125.89 MB","国际供应链","方思扬","第3批",""),
 (38,"pubdm","luckyus_pub_dm","idm","L1","db.t4g.micro",1,109,511,"16.81 MB","国际供应链","方思扬","第3批",""),
 (39,"iopenadmin","luckyus_iopenadmin","iopenadmin","L1","db.t4g.micro",1,123,419,"8.66 MB","国际供应链","方思扬","第3批",""),
 (40,"ireplenishment","luckyus_ireplenishment","ireplenishment","L1","db.t4g.micro",1,119,647,"1.93 GB","供应链算法","高天牧\n黄方进","第3批",""),
 (41,"opempefficiency","luckyus_opempefficiency","iopempefficiency","L1","db.t4g.micro",1,101,546,"117.27 MB","国际运营","陈培浩","第3批",""),
 (42,"iluckymedia","luckyus_iluckymedia","iluckymedia","L1","db.t4g.micro",1,120,416,"8.83 MB","国际运营","张少群","第3批",""),
 (43,"isalesmembermarketing","luckyus_isalesmembermarketing","isalesmembermarketingadmin\nisalesmembermarketingservice","L2\nL1","db.t4g.micro",1,115,425,"8.97 MB","国际营销增长","李加彬\n张翔\n张晓松","第3批",""),
 (44,"isalesdatamarketing","luckyus_isalesdatamarketing","isalesdatamarketingservice\nisalesdatamarketingadmin","L1\nL1","db.t4g.medium",4,666,490,"9.47 GB","国际营销增长","李加彬\n张翔\n张晓松","第3批",""),
 (45,"iriskcontrolservice","luckyus_iriskcontrolservice","iriskcontrolservice","L0","db.t4g.micro",1,94,1207,"23.59 GB","信息安全","林宏鹏","第3批","Swap 最高 1207MB；L0 核心，1GB 机型承载 23.6GB 数据，蓝绿期间内存压力高"),
 (46,"ipermission","luckyus_ipermission","iopenauth\nipermission","L0\nL1","db.t4g.micro",1,96,591,"99.61 MB","国际公共平台","陈亮\n张晓松","第4批","L0 鉴权 —— 重点核查 mysql_native_password 用户"),
 (47,"fitax","luckyus_fi_tax","ifitax","L0","db.t4g.micro",1,119,393,"8.67 MB","国际公共平台","尤志杰","第4批",""),
 (48,"scm-shopstock","luckyus_scm_shopstock","iscmsims\niscmshopstock","L1\nL0","db.t4g.medium",4,466,325,"8.11 GB","国际供应链","方思扬","第4批",""),
 (49,"scmcommodity","luckyus_scm_commodity","iscmcommodityadmin\niscmcommodity","L1\nL0","db.t4g.medium",4,2057,0,"199.91 MB","国际供应链","方思扬","第4批",""),
 (50,"opproduction","luckyus_opproduction","iopproduction","L0","db.t4g.micro",1,90,594,"5.80 GB","国际运营","陈培浩\n游熖","第4批","L0 核心，1GB 机型承载 5.8GB 数据"),
 (51,"opshopsale","luckyus_opshopsale","iopshopsaleservice","L0","db.t4g.micro",1,83,658,"304.28 MB","国际运营","陈培浩\n游熖","第4批","可用内存 83MB，车队偏低；L0 核心"),
 (52,"opshop","luckyus_opshop","iopshopservice\niopshopadmin","L0\nL2","db.t4g.medium",4,2254,0,"40.53 MB","国际运营","陈培浩\n游熖","第4批",""),
 (53,"isalesprivatedomain","luckyus_isales_privatedomain","isalesprivatedomainadmin\nisalesmarketingadmin\nisalesprivatedomainservice","L2\nL1\nL0","db.t4g.medium",4,661,135,"2.64 GB","国际营销增长","张翔\n上官锦程\n王良","第4批",""),
 (54,"salescrm","luckyus_sales_crm","isalesmarketingadmin\nisalescrmservice\nisalescrmadmin","L0\nL0\nL0","db.t4g.medium",4,1785,0,"632.09 MB","国际营销增长","张翔\n高如森","第4批","全 L0 核心"),
 (55,"cdpactivity","luckyus_cdp_activity","icdpactivityengine\nisalesmarketingservice\nisalesmarketingadmin","L1\nL0\nL0","db.t4g.medium",4,485,375,"18.19 GB","国际营销增长","张晓松","第4批",""),
 (56,"isalescdp","luckyus_isales_cdp","isalesmarketingadmin\nicdprealtimeusergroupengine","L1\nL0","db.t4g.medium",4,993,0,"2.69 GB","国际营销增长","张晓松","第4批","3/12 发生过 OOM/Multi-AZ 故障转移事故，升级后扩展验证"),
 (57,"salesmarketing","luckyus_sales_marketing","icdprealtimeusergroupengine\nisalesmarketingservice\nisalesmarketingadmin","L1\nL0\nL0","db.t4g.xlarge",16,1509,204,"25.20 GB","国际营销增长","张晓松","第4批","车队最大实例 xlarge 16GB；大小由 46GB→25GB（疑似清理/binlog 回收）；最后升级、全面验证"),
 (58,"salespayment","luckyus_sales_payment","isalespaymentservice\nisalespaymentadmin","L0\nL1","db.t4g.medium",4,1687,0,"793.06 MB","国际营销增长","张晓松","第4批","核心支付系统，逐个升级、单独蓝绿"),
 (59,"salesorder","luckyus_sales_order","isalesmarketingadmin\nisalesordersync\nisalesorderservice\nisalesorderadmin","L0\nL2\nL0\nL0","db.t4g.medium",4,421,218,"5.82 GB","国际营销增长","张晓松","第4批","核心订单系统；升级后必须验证 group_concat_max_len = 1048576"),
]

LEVEL_FULL = {"L0":"L0（核心业务服务）","L1":"L1（重要业务服务）","L2":"L2（普通业务服务）"}

def expand_level(s):
    return "\n".join(LEVEL_FULL.get(x, x) for x in s.split("\n"))

def mem_risk(avail):
    if avail < 150:
        return "高"
    if avail <= 300:
        return "中"
    return "低"

HEADER = ["序号","实例名称","数据库列表","关联服务","服务等级",
          "当前版本","目标版本","规格","内存(GB)","可用内存(MB)","Swap(MB)",
          "内存风险¹","数据库大小","业务分组","研发负责人","批次","操作人",
          "计划操作日期【北京时间】","升级状态","原库及蓝绿部署清理","备注"]

# --- CSV ---
with open("mysql_8.4.9_upgrade_tracker.csv","w",newline="",encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    for r in ROWS:
        seq,inst,dbl,svc,lvl,spec,memgb,avail,swap,size,grp,owner,batch,note = r
        w.writerow([seq,inst,dbl,svc,expand_level(lvl),CUR,TGT,spec,memgb,avail,swap,
                    mem_risk(avail),size,grp,owner,batch,"待定","未开始","未开始",note])

# summary stats
total = len(ROWS)
by_batch = {}
by_spec = {}
risk = {"高":0,"中":0,"低":0}
for r in ROWS:
    by_batch[r[12]] = by_batch.get(r[12],0)+1
    by_spec[r[5]] = by_spec.get(r[5],0)+1
    risk[mem_risk(r[7])] += 1

print("rows:", total)
print("by_batch:", by_batch)
print("by_spec:", by_spec)
print("mem_risk:", risk)

# --- Markdown report ---
def br(s):
    return s.replace("\n","<br>")

preamble = f"""# MySQL 8.0.45 → 8.4.9 升级跟踪表

> **生成日期**：2026-06-03 ｜ **当前版本（全车队已统一）**：8.0.45 ｜ **目标版本**：8.4.9（8.4 LTS）
> **实例总数**：{total} ｜ **AWS 账户**：257394478466 / us-east-1
> 数据库大小为 2026-06-03 经 mcp-db-gateway `information_schema` 实时刷新（ilsopdevopsdata 未经网关暴露，沿用 5 月基线）。
> 规格 / 内存 / 可用内存 / Swap 沿用 2026-04~05 月 8.0.45 升级跟踪基线（机型未变；可用内存/Swap 为 CloudWatch 时点快照）。

## ⚠️ 这是一次「大版本」升级，与 8.0.41→8.0.45 小版本升级有本质区别

8.0 → 8.4 是 RDS MySQL 的 **major version upgrade**，必须按大版本流程处理。以下为升级前必做的兼容性核查（每个实例都要过）：

| # | 检查项 | 说明 |
|---|--------|------|
| 1 | **mysql_native_password 认证插件** | 8.4 中该插件默认 **disabled**（`--mysql-native-password=OFF`）。升级前必须审计 `mysql.user` 中 `plugin='mysql_native_password'` 的账号并迁移到 `caching_sha2_password`，否则应用连接会失败。鉴权/核心库（devops、iluckyauthapi、ipermission、salescrm 等）尤其重点。 |
| 2 | **新建 mysql8.4 参数组** | 不能复用 8.0 family 参数组；需为每实例建 `mysql8.4` family 参数组。**`lower_case_table_names` 创建后不可改**——8.0.45 升级时 `luckyus-prod` 参数组就因缺该项导致 ldas 多次部署失败，本轮务必先对齐。 |
| 3 | **已移除/重命名的系统变量** | 8.4 移除了多个 8.0 中已弃用的变量（如部分 `innodb_*`、复制相关、`expire_logs_days` 等）。自定义参数组需逐项核对，移除已废弃项后再创建。 |
| 4 | **RDS 升级前置预检（pre-upgrade check）** | RDS 大版本升级会自动跑 pre-check；提前用 blue/green 或测试实例（`dba84test`）跑一遍，查看 `PrePatchCompatibility` / 升级预检日志中的不兼容项与孤立表/分区。 |
| 5 | **蓝绿部署（Blue/Green Deployment）** | 8.0→8.4 支持蓝绿。L0/L1 强烈建议走蓝绿：绿环境先升 8.4 验证、回切风险可控、切换窗口短。原库与蓝绿环境的清理需登记在「原库及蓝绿部署清理」列。 |
| 6 | **应用驱动兼容性** | 确认 JDBC / 各语言 connector 版本支持 `caching_sha2_password`（旧驱动需 RSA 公钥或 SSL）。Nacos（framework01）、鉴权服务为重点。 |
| 7 | **内存压力** | 升级中 RDS 执行 Multi-AZ 故障转移，短暂增加内存压力。当前 **39 个实例可用内存 < 150MB（风险「高」，全部为 db.t4g.micro 1GB 机型的长期状态）**。先例：iluckyams 曾在 83–148MB 可用内存下成功完成自动升级；isalescdp 曾于 3/12 发生 OOM/failover，需重点关注。 |

## 升级批次（沿用 8.0.45 升级的风险分级顺序：基础/普通服务先行，L0 核心最后）

| 批次 | 实例数 | 说明 |
|------|--------|------|
| 第1批 | {by_batch.get('第1批',0)} | 基础服务 / 大数据（ldas、devops、framework、upush、iotplatform 等） |
| 第2批 | {by_batch.get('第2批',0)} | L2 普通业务服务（scm-wmssimulate、fichargecontrol、iopocp 等） |
| 第3批 | {by_batch.get('第3批',0)} | L1 重要业务服务（公共平台 / 供应链 / 运营 / 营销，含 1 个 L0 iriskcontrol） |
| 第4批 | {by_batch.get('第4批',0)} | L0 核心业务服务（支付、订单、CRM、CDP、shopstock 等），逐个升级、全面验证 |

> **计划日期 / 操作人**：本轮均为「待定」，待大版本预检通过、参数组与认证插件迁移方案确认后再排期。

## 实例明细（{total} 实例）

| # | 实例 | 服务等级 | 当前→目标 | 规格 | 内存GB | 可用MB | Swap MB | 风险¹ | 数据库大小 | 业务分组 | 批次 | 状态 | 备注 |
|---|------|----------|-----------|------|-------|--------|---------|------|-----------|----------|------|------|------|"""

lines = [preamble]
for r in ROWS:
    seq,inst,dbl,svc,lvl,spec,memgb,avail,swap,size,grp,owner,batch,note = r
    lines.append("| {} | {} | {} | {}→{} | {} | {} | {} | {} | {} | {} | {} | {} | 未开始 | {} |".format(
        seq,inst,br(lvl),CUR,TGT,spec,memgb,avail,swap,mem_risk(avail),size,br(grp),batch,note or "—"))

footer = f"""

## 汇总统计

| 指标 | 值 |
|------|-----|
| 必须升级 | {total} |
| 已完成 | 0 |
| 完成率 | 0.0% |
| 可用内存「高」风险（<150MB） | {risk['高']} |
| 可用内存「中」风险（150–300MB） | {risk['中']} |
| 可用内存「低」风险（>300MB） | {risk['低']} |

**机型分布**：db.t4g.micro × {by_spec.get('db.t4g.micro',0)}、db.t4g.medium × {by_spec.get('db.t4g.medium',0)}、db.t4g.large × {by_spec.get('db.t4g.large',0)}、db.t4g.xlarge × {by_spec.get('db.t4g.xlarge',0)}、db.t3.small × {by_spec.get('db.t3.small',0)}

---
¹ **内存风险**：升级过程中 RDS 执行 Multi-AZ 故障转移，短暂增加内存压力。「高」= 可用内存 < 150MB（全部为 db.t4g.micro 1GB 机型长期运行状态，非升级引入的新风险）；「中」= 150–300MB；「低」= > 300MB。

> 完整可编辑跟踪表见同目录 `mysql_8.4.9_upgrade_tracker.csv`（21 列，含数据库列表 / 关联服务 / 研发负责人 / 操作人 / 计划日期 / 原库及蓝绿清理 等）。
"""

with open("README.md","w",encoding="utf-8") as f:
    f.write("\n".join(lines))
    f.write(footer)
print("wrote README.md")
