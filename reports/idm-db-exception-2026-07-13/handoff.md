# idm DB 异常 P1 告警 — 分析与交接

**收件人**：@方思扬（idm 应用负责人）
**发起**：曾翔宇（DBA / Infra）
**日期**：2026-07-13

---

## 一、遇到的问题

2026-07-13 凌晨起，宙斯(SkyWalking)对 `service=idm` 连续触发 P1 告警：

- 【全局异常-DB异常告警-P1】异常 java sql SQL 总数 ≥ 10
- 【全局异常-DB异常告警-P1】异常 org apache ibatis 总数 ≥ 10

告警时间（UTC，美东 EDT = UTC−4）：03:26、03:28、03:41(×2)、11:45。同期时间线上还有一条 06:17【AWS RDS 重启/主从切换】和一条 09:51【WSS pod OOM】。

需要确认三件事：两条告警是否同源、是否与 RDS 重启有关、以及一次为何能累计到 10 条以上异常。

---

## 二、查到的线索与依据

**1. 原始异常栈（ES `iprod_tomcat_lucky_k8s-2026.07.13-000275`）**

```
URI=/idm/resource/idm/operation/dynamicquery/query/shop_kpi_all_indicators
Mapper: com.luckincoffee.pub.idm.modules.operation.dynamicquery.dao.redshift.DynamicQueryMapper
org.springframework.dao.RecoverableDataAccessException
  → com.mysql.cj.jdbc.exceptions.CommunicationsException: Communications link failure
     "last packet received 70,073 ms ago / sent 87,704 ms ago"
     → Caused by: java.net.SocketTimeoutException: Read timed out
```

异常沿栈翻译两层：JDBC 层是 `com.mysql.cj...CommunicationsException`（继承自 `java.sql.SQLNonTransientConnectionException`），MyBatis 层再包成 `PersistenceException`。最底层根因是 `SocketTimeoutException: Read timed out`。

**2. 目标数据源**

Mapper 包名为 `...dao.redshift`，但驱动是 `com.mysql.cj.jdbc`（MySQL 线协议），查询对象是 `dw_ads` / `ods_luckyus_*` 数仓 schema（如 `dw_ads.ads_opt_t_shop_employee_operate_d_1d` LEFT JOIN `ods_luckyus_sales_order.t_order_stat_dim`）。据此判断该数据源为走 MySQL 协议的分析数仓（Doris 一侧），并非 Amazon Redshift，也非 idm 的业务库 pubdm。

**3. pubdm 与 RDS 事件核查（CloudWatch / RDS events）**

- pubdm 全天连接数稳定 8–13、CPU 5–8%，无掉零/无尖峰，无重启或 failover 事件。
- 全天没有任何生产 RDS 实例重启；06:17 告警对应的是当晚一批蓝绿部署 green 实例（opshopsale / icyberdata / opshop / mfranchise 等，01:06–05:23 UTC）的切换，与 idm 的库无关。

**4. 请求扇出（同一 URI 报出不同 SQL）**

同一接口 `shop_kpi_all_indicators` 在不同时刻报出不同的失败 SQL：`efficiencyDuration`（效率时长）、`endOpenedStoreCount`（已开业门店数）等。栈中调用链为 `query()` → `executeSubQuery()` → `executeDynamicQueryByField()`，即一次请求按 KPI 指标拆成多条子查询，每条子查询独立执行、独立超时、独立抛异常。

**5. 单请求耗时与重复请求（nginx 访问日志）**

- 单次请求耗时 70–156 秒：`shop_kpi_all_indicators` 记录到 126531ms、156141ms、70114ms；同期 `shopEmpAttendOpt/statis`(118s)、`ocp/metrics/query`(70s×2) 等 idm→数仓查询同样超时。
- 报文中同一池化连接"last packet sent 119,517ms ago / received 70,074ms ago"，说明多条子查询在一个请求内顺序复用同一连接、各等约 70 秒。
- 相关请求均带同一 `X-LK-MID=2401001624` / `cid=660101`；在 03:20–03:26 之间该看板被多次发起（页面长时间无响应时被反复提交）。

**6. 时段特征**

异常集中在凌晨（03:23 UTC = 前日 23:23 EDT），与每日数仓 ETL 重建 `dw_ads.ads_opt_*` 日表的窗口重叠。

---

## 三、结论

1. **两条告警同源**：`java sql` 与 `org apache ibatis` 是同一次失败在 JDBC 层与 MyBatis 层各计一次数，按一类问题处理。（11:45 仅 ibatis 触发，是 java.sql 侧当分钟未达阈值 10 的计数差异，非新故障。）

2. **与 RDS 重启无关**：idm 业务库 pubdm 全天正常、无重启；06:17 告警为蓝绿实例切换。异常根因不在 pubdm。

3. **根因**：idm 门店 KPI 看板（`dynamicquery` 模块，`dao.redshift` 数据源 = Doris 数仓）的分析查询执行超过约 70 秒的 JDBC socket 读超时（`Read timed out`），叠加数仓夜间 ETL 窗口导致查询变慢。

4. **一次为何累计到 ≥10 条**：单次请求按指标扇出为多条子查询（日志中已见 `efficiencyDuration`、`endOpenedStoreCount` 等多个），每条超时各记一条异常；同时段该看板被多次发起。两个因素叠加即可在一分钟内超过阈值 10。触发来源从日志可见为同一 `MID=2401001624` 的多次请求，具体是定时刷新还是人工连续操作，两种情况都能解释该现象，从现有日志无法进一步区分。

5. **影响**：该接口为门店 KPI 看板查询，异常集中在凌晨低峰；对交易主链路无直接影响，但存在数仓查询在业务高峰同样超时的风险。

**可考虑的处置方向**（供判断参考，优先级从高到低）：
- 数仓侧对 `shop_kpi_all_indicators` 相关 SQL 做 `EXPLAIN` 与慢查询/ETL 争用排查（治本方向；DBA 到 idoris:9030 无网络访问权限，此项需数仓侧执行）。
- 后端对多指标子查询做合并 / 限流 / 超时降级，避免一次请求串行发起十余条长查询。
- 前端在查询未返回时做超时提示与防重复提交。
- 告警侧可将 `dao.redshift`（数仓）异常与 pubdm 业务库异常分类，减少同一条 P1 的混淆。

— 曾翔宇
