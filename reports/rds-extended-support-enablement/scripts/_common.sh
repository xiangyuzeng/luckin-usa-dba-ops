#!/usr/bin/env bash
# _common.sh — shared logic for RDS Extended Support enablement (per-level wrappers source this)
# Compatible with bash 4.2 (Amazon Linux 2 / dbtools0x-prod-usa-aws).
#
# A wrapper defines:  LEVEL="L0"  and  TARGETS=( id1 id2 ... )  then sources this file
# and calls:  run_enable "$@"
#
# Behaviour:
#   - DRY-RUN by default. Prints what WOULD change. Nothing is modified.
#   - Pass --apply to actually call modify-db-instance.
#   - Idempotent: instances already on extended support are skipped.
#   - Only acts on engine=mysql instances in `available` state; anything else is skipped & logged.
#   - Value set: --engine-lifecycle-support open-source-rds-extended-support
#
# NOTE: enabling extended-support is a *billing preference*. Charges only accrue once the
# instance's major version passes RDS standard support end. On 8.4 (standard support for
# years) this sets the preference with no current charge, preventing future forced auto-upgrade.

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
TARGET_VALUE="open-source-rds-extended-support"
APPLY=0

LOG_DIR="${LOG_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/logs}"
mkdir -p "$LOG_DIR"

_ts() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }

usage() {
  cat <<EOF
Usage: $0 [--apply] [--region us-east-1]
  (no flag)   DRY-RUN — show planned changes, modify nothing (default)
  --apply     Execute: enable Extended Support on the ${LEVEL} target instances
  --region R  Override AWS region (default: ${REGION})

Targets (${LEVEL}): ${#TARGETS[@]} instances
EOF
}

parse_args() {
  while [ "${1:-}" != "" ]; do
    case "$1" in
      --apply)  APPLY=1 ;;
      --region) shift; REGION="${1:?--region needs a value}" ;;
      -h|--help) usage; exit 0 ;;
      *) echo "unknown arg: $1" >&2; usage; exit 2 ;;
    esac
    shift
  done
}

# one describe call -> "els<TAB>status<TAB>engine" (or "MISSING\tMISSING\tMISSING")
_describe() {
  aws rds describe-db-instances --region "$REGION" \
    --db-instance-identifier "$1" \
    --query 'DBInstances[0].[EngineLifecycleSupport,DBInstanceStatus,Engine]' \
    --output text 2>/dev/null || printf 'MISSING\tMISSING\tMISSING\n'
}

run_enable() {
  parse_args "$@"
  local logf="${LOG_DIR}/enable-${LEVEL}-$(date -u +%Y%m%dT%H%M%SZ).log"
  local mode="DRY-RUN"; [ "$APPLY" -eq 1 ] && mode="APPLY"
  {
    echo "=== RDS Extended Support enablement — ${LEVEL} — mode=${mode} region=${REGION} @ $(_ts) ==="
    echo "operator=$(aws sts get-caller-identity --query Arn --output text 2>/dev/null || echo unknown)"
    echo "targets=${#TARGETS[@]}"
    echo
  } | tee "$logf"

  local ok=0 skip=0 already=0 fail=0 i
  for i in ${TARGETS[@]+"${TARGETS[@]}"}; do
    local els st eng desc
    desc="$(_describe "$i")"
    els="$(printf '%s' "$desc" | cut -f1)"
    st="$(printf '%s' "$desc" | cut -f2)"
    eng="$(printf '%s' "$desc" | cut -f3)"

    if [ "$els" = "MISSING" ] || [ "$eng" = "MISSING" ] || [ -z "$els" ]; then
      printf '  [SKIP ] %-45s not found in region %s\n' "$i" "$REGION" | tee -a "$logf"; skip=$((skip+1)); continue
    fi
    if [ "$eng" != "mysql" ]; then
      printf '  [SKIP ] %-45s engine=%s (not mysql)\n' "$i" "$eng" | tee -a "$logf"; skip=$((skip+1)); continue
    fi
    if [ "$els" = "$TARGET_VALUE" ]; then
      printf '  [ALDY ] %-45s already extended-support (status=%s)\n' "$i" "$st" | tee -a "$logf"; already=$((already+1)); continue
    fi
    if [ "$st" != "available" ]; then
      printf '  [WARN ] %-45s status=%s (not available) — will still queue if --apply\n' "$i" "$st" | tee -a "$logf"
    fi

    if [ "$APPLY" -eq 0 ]; then
      printf '  [PLAN ] %-45s %s -> %s\n' "$i" "$els" "$TARGET_VALUE" | tee -a "$logf"; ok=$((ok+1)); continue
    fi

    if aws rds modify-db-instance --region "$REGION" \
         --db-instance-identifier "$i" \
         --engine-lifecycle-support "$TARGET_VALUE" \
         --apply-immediately \
         --query 'DBInstance.[DBInstanceIdentifier,EngineLifecycleSupport,DBInstanceStatus]' \
         --output text >>"$logf" 2>&1; then
      printf '  [DONE ] %-45s -> %s\n' "$i" "$TARGET_VALUE" | tee -a "$logf"; ok=$((ok+1))
    else
      printf '  [FAIL ] %-45s modify-db-instance failed (see log)\n' "$i" | tee -a "$logf"; fail=$((fail+1))
    fi
  done

  {
    echo
    echo "=== summary ${LEVEL} (${mode}) : planned/done=${ok} already=${already} skipped=${skip} failed=${fail} ==="
    echo "log: ${logf}"
  } | tee -a "$logf"
  [ "$fail" -eq 0 ]
}
