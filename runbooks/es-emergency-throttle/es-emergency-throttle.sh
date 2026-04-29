#!/bin/bash
#
# OpenSearch 集群即时减压脚本
# 适用: luckylfe-log (m5.large × 4) + luckyur-log (m5.xlarge × 4)
# 类型: 集群级动态参数下发，零中断，可一键回滚
#
# 用法:
#   ./es-emergency-throttle.sh status   {lfe|ur}     # 查看当前 cluster settings + health
#   ./es-emergency-throttle.sh preflight {lfe|ur}    # 连通性 + 现状预检
#   ./es-emergency-throttle.sh apply    {lfe|ur}     # 下发减压参数（带二次确认）
#   ./es-emergency-throttle.sh verify   {lfe|ur}     # 验证生效 + 关键指标
#   ./es-emergency-throttle.sh rollback {lfe|ur}     # 全部置 null，恢复默认
#   ./es-emergency-throttle.sh reroute  lfe          # 触发未分配分片重试 (仅 luckylfe-log)
#
# 关联文档:
#   /app/reports/es-cluster-incident-2026-04-29.md
#   /app/reports/es-cluster-quick-fix-2026-04-29.md
#
set -euo pipefail

# ---------- 集群端点 ----------
ENDPOINT_LFE='https://vpc-luckylfe-log-eh3n6nwo4c43eofoz36j35kni4.us-east-1.es.amazonaws.com'
# luckyur-log 端点：通过环境变量 LUCKYUR_LOG_ENDPOINT 注入，避免硬编码
ENDPOINT_UR="${LUCKYUR_LOG_ENDPOINT:-}"

REGION='us-east-1'
ACCOUNT='257394478466'

# ---------- 参数集 ----------
PAYLOAD_LFE='{
  "persistent": {
    "indices.breaker.total.limit": "70%",
    "indices.breaker.request.limit": "50%",
    "indices.breaker.fielddata.limit": "25%",
    "indices.fielddata.cache.size": "15%",
    "search.max_buckets": 10000,
    "action.search.shard_count.limit": 500,
    "cluster.routing.allocation.total_shards_per_node": 200
  }
}'

PAYLOAD_UR='{
  "persistent": {
    "indices.breaker.total.limit": "70%",
    "indices.breaker.fielddata.limit": "25%",
    "indices.fielddata.cache.size": "15%",
    "search.max_buckets": 10000,
    "action.search.shard_count.limit": 500
  }
}'

ROLLBACK_PAYLOAD='{
  "persistent": {
    "indices.breaker.total.limit": null,
    "indices.breaker.request.limit": null,
    "indices.breaker.fielddata.limit": null,
    "indices.fielddata.cache.size": null,
    "search.max_buckets": null,
    "action.search.shard_count.limit": null,
    "cluster.routing.allocation.total_shards_per_node": null
  }
}'

# ---------- 工具函数 ----------
log()  { printf '\033[0;34m[%s]\033[0m %s\n' "$(date -u +%FT%TZ)" "$*"; }
ok()   { printf '\033[0;32m[%s] ✓\033[0m %s\n' "$(date -u +%FT%TZ)" "$*"; }
warn() { printf '\033[0;33m[%s] ⚠\033[0m %s\n' "$(date -u +%FT%TZ)" "$*"; }
err()  { printf '\033[0;31m[%s] ✗\033[0m %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }

resolve_endpoint() {
  case "${1:-}" in
    lfe) echo "$ENDPOINT_LFE"; echo "luckylfe-log" >&2 ;;
    ur)
      if [ -z "$ENDPOINT_UR" ]; then
        err "请先设置环境变量 LUCKYUR_LOG_ENDPOINT，例如:"
        err "  export LUCKYUR_LOG_ENDPOINT='https://vpc-luckyur-log-<id>.us-east-1.es.amazonaws.com'"
        exit 2
      fi
      echo "$ENDPOINT_UR"; echo "luckyur-log" >&2 ;;
    *) err "未知集群: ${1:-}（用 lfe 或 ur）"; exit 2 ;;
  esac
}

resolve_payload() {
  case "$1" in
    lfe) echo "$PAYLOAD_LFE" ;;
    ur)  echo "$PAYLOAD_UR" ;;
  esac
}

resolve_domain() {
  case "$1" in
    lfe) echo "luckylfe-log" ;;
    ur)  echo "luckyur-log" ;;
  esac
}

confirm() {
  local prompt="$1"
  printf '\033[1;33m%s [yes/N]: \033[0m' "$prompt" >&2
  read -r reply
  [ "$reply" = "yes" ]
}

require_jq() {
  command -v jq >/dev/null 2>&1 || { err "需要 jq，请先 'sudo apt-get install jq' 或 'brew install jq'"; exit 3; }
}

# ---------- 子命令 ----------
cmd_status() {
  local key="$1"
  local endpoint; endpoint=$(resolve_endpoint "$key" 2>/dev/null)
  log "查询 $(resolve_domain "$key") 当前 cluster settings 与健康状态..."
  echo "--- _cluster/settings (persistent) ---"
  curl -sS "$endpoint/_cluster/settings?pretty" | jq '.persistent'
  echo "--- _cluster/health ---"
  curl -sS "$endpoint/_cluster/health?pretty"
}

cmd_preflight() {
  local key="$1"
  local endpoint; endpoint=$(resolve_endpoint "$key" 2>/dev/null)
  local domain; domain=$(resolve_domain "$key")

  log "[1/4] 连通性检查 $endpoint ..."
  if ! curl -sS --max-time 10 -o /dev/null -w "%{http_code}\n" "$endpoint/_cluster/health" | grep -qE '^2[0-9][0-9]'; then
    err "无法访问 $endpoint（可能是 VPC 内网，请在 bastion / EKS 节点上执行）"
    exit 4
  fi
  ok "连通性正常"

  log "[2/4] 集群健康..."
  curl -sS "$endpoint/_cluster/health?pretty" | jq '{status, number_of_nodes, active_primary_shards, unassigned_shards}'

  log "[3/4] CloudWatch 最近 1h JVM 峰值..."
  aws cloudwatch get-metric-statistics --namespace AWS/ES \
    --metric-name JVMMemoryPressure \
    --dimensions Name=DomainName,Value="$domain" Name=ClientId,Value="$ACCOUNT" \
    --start-time "$(date -u -d '1 hour ago' +%FT%TZ)" \
    --end-time "$(date -u +%FT%TZ)" \
    --period 300 --statistics Maximum --region "$REGION" \
    --query 'Datapoints | sort_by(@,&Timestamp)[-3:].[Timestamp,Maximum]' --output table 2>&1 || true

  log "[4/4] 当前 persistent settings 是否已存在我们的参数..."
  curl -sS "$endpoint/_cluster/settings?pretty" | \
    jq '.persistent | {
      total: (."indices.breaker.total".limit // "default"),
      fielddata_cache: (."indices.fielddata.cache".size // "default"),
      max_buckets: (."search.max_buckets" // "default")
    }'
  ok "预检完成"
}

cmd_apply() {
  local key="$1"
  local endpoint; endpoint=$(resolve_endpoint "$key" 2>/dev/null)
  local domain; domain=$(resolve_domain "$key")
  local payload; payload=$(resolve_payload "$key")

  warn "即将向 $domain 下发以下 persistent settings:"
  echo "$payload" | jq .
  warn "影响：超大聚合 / 跨海量分片查询会被熔断器拒绝（HTTP 400/503）"
  warn "回滚：./es-emergency-throttle.sh rollback $key"
  echo
  if ! confirm "确认下发？输入 yes 继续"; then
    err "已取消"; exit 5
  fi

  log "下发参数到 $domain ..."
  local resp
  resp=$(curl -sS -XPUT "$endpoint/_cluster/settings" \
    -H 'Content-Type: application/json' -d "$payload")
  echo "$resp" | jq .
  if echo "$resp" | jq -e '.acknowledged == true' >/dev/null; then
    ok "下发成功，参数已生效（persistent，集群重启不丢失）"
  else
    err "下发可能失败，请手动检查"
    exit 6
  fi

  log "建议立即跑: ./es-emergency-throttle.sh verify $key"
}

cmd_verify() {
  local key="$1"
  local endpoint; endpoint=$(resolve_endpoint "$key" 2>/dev/null)
  local domain; domain=$(resolve_domain "$key")

  log "[1/3] 验证 settings 已落库..."
  curl -sS "$endpoint/_cluster/settings?pretty" | jq '.persistent'

  log "[2/3] 集群健康..."
  curl -sS "$endpoint/_cluster/health?pretty" | \
    jq '{status, number_of_nodes, active_primary_shards, unassigned_shards}'

  log "[3/3] CloudWatch 最近 30 分钟 JVM / 5xx 趋势..."
  echo "--- JVMMemoryPressure (Max, 5min) ---"
  aws cloudwatch get-metric-statistics --namespace AWS/ES \
    --metric-name JVMMemoryPressure \
    --dimensions Name=DomainName,Value="$domain" Name=ClientId,Value="$ACCOUNT" \
    --start-time "$(date -u -d '30 min ago' +%FT%TZ)" \
    --end-time "$(date -u +%FT%TZ)" \
    --period 300 --statistics Maximum --region "$REGION" \
    --query 'Datapoints | sort_by(@,&Timestamp)[*].[Timestamp,Maximum]' --output table

  echo "--- 5xx (Sum, 5min) ---"
  aws cloudwatch get-metric-statistics --namespace AWS/ES \
    --metric-name 5xx \
    --dimensions Name=DomainName,Value="$domain" Name=ClientId,Value="$ACCOUNT" \
    --start-time "$(date -u -d '30 min ago' +%FT%TZ)" \
    --end-time "$(date -u +%FT%TZ)" \
    --period 300 --statistics Sum --region "$REGION" \
    --query 'Datapoints | sort_by(@,&Timestamp)[*].[Timestamp,Sum]' --output table 2>/dev/null || echo "(no 5xx datapoints)"

  ok "验证完成。预期 JVM 峰值 30-60min 内回落 5-10 个百分点"
}

cmd_rollback() {
  local key="$1"
  local endpoint; endpoint=$(resolve_endpoint "$key" 2>/dev/null)
  local domain; domain=$(resolve_domain "$key")

  warn "即将回滚 $domain 的所有减压参数到默认值"
  if ! confirm "确认回滚？输入 yes 继续"; then
    err "已取消"; exit 5
  fi

  log "回滚 $domain ..."
  curl -sS -XPUT "$endpoint/_cluster/settings" \
    -H 'Content-Type: application/json' \
    -d "$ROLLBACK_PAYLOAD" | jq .
  ok "已回滚"
}

cmd_reroute() {
  local key="$1"
  if [ "$key" != "lfe" ]; then
    err "reroute 仅适用于 lfe（luckylfe-log 当前有 26 个未分配分片）"
    exit 7
  fi
  local endpoint; endpoint=$(resolve_endpoint lfe 2>/dev/null)

  log "触发 retry_failed=true ..."
  curl -sS -XPOST "$endpoint/_cluster/reroute?retry_failed=true" | jq '{acknowledged}'
  log "查询分片分配解释（如未恢复）..."
  curl -sS "$endpoint/_cluster/allocation/explain?pretty" | head -60 || true
}

# ---------- 入口 ----------
require_jq
case "${1:-help}" in
  status)    cmd_status "${2:?用法: $0 status {lfe|ur}}" ;;
  preflight) cmd_preflight "${2:?用法: $0 preflight {lfe|ur}}" ;;
  apply)     cmd_apply "${2:?用法: $0 apply {lfe|ur}}" ;;
  verify)    cmd_verify "${2:?用法: $0 verify {lfe|ur}}" ;;
  rollback)  cmd_rollback "${2:?用法: $0 rollback {lfe|ur}}" ;;
  reroute)   cmd_reroute "${2:?用法: $0 reroute lfe}" ;;
  help|*)
    sed -n '2,/^set -euo/p' "$0" | head -n -1 | sed 's/^# \{0,1\}//'
    ;;
esac
