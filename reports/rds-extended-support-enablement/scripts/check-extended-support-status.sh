#!/usr/bin/env bash
# check-extended-support-status.sh
# Read-only audit of EngineLifecycleSupport across ALL RDS instances (+ Aurora clusters).
# No modifications. Prints a table, a summary, and (optionally) writes a CSV.
#
# Usage:
#   ./check-extended-support-status.sh [--region us-east-1] [--csv out.csv] [--only-disabled]
#     --region R        AWS region (default: us-east-1 or $AWS_REGION)
#     --csv FILE        also write full result as CSV
#     --only-disabled   only list instances WITHOUT extended support enabled
#
# EngineLifecycleSupport values:
#   open-source-rds-extended-support           = enrolled (future forced auto-upgrade avoided)
#   open-source-rds-extended-support-disabled  = NOT enrolled (AWS may force-upgrade after std support ends)

set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"
CSV=""
ONLY_DISABLED=0

while [ "${1:-}" != "" ]; do
  case "$1" in
    --region) shift; REGION="${1:?}" ;;
    --csv) shift; CSV="${1:?}" ;;
    --only-disabled) ONLY_DISABLED=1 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

echo "=== RDS Extended Support status — region=${REGION} — $(date -u +%FT%TZ) ==="

# DB instances: id, engine, version, EngineLifecycleSupport, class, status
rows="$(aws rds describe-db-instances --region "$REGION" \
  --query 'DBInstances[].[DBInstanceIdentifier,Engine,EngineVersion,EngineLifecycleSupport,DBInstanceClass,DBInstanceStatus]' \
  --output text | sort)"

# Aurora / DB clusters also carry EngineLifecycleSupport
crows="$(aws rds describe-db-clusters --region "$REGION" \
  --query 'DBClusters[].[DBClusterIdentifier,Engine,EngineVersion,EngineLifecycleSupport,DBClusterInstanceClass,Status]' \
  --output text 2>/dev/null | sort || true)"

printf '\n%-46s %-10s %-9s %-14s %-16s %s\n' "IDENTIFIER" "ENGINE" "VERSION" "EXT-SUPPORT" "CLASS" "STATUS"
printf '%s\n' "----------------------------------------------------------------------------------------------------------------"

emit() {  # stream: id engine ver els class status ; kind
  local kind="$2"
  while IFS=$'\t' read -r id eng ver els cls st; do
    [ -z "${id:-}" ] && continue
    local flag="disabled"; case "$els" in *"-disabled") flag="disabled";; open-source-rds-extended-support) flag="ENABLED";; *) flag="$els";; esac
    if [ "$ONLY_DISABLED" -eq 1 ] && [ "$flag" = "ENABLED" ]; then continue; fi
    printf '%-46s %-10s %-9s %-14s %-16s %s\n' "$id" "$eng" "$ver" "$flag" "$cls" "$st"
    if [ -n "$CSV" ]; then echo "${kind},${id},${eng},${ver},${els},${cls},${st}" >> "$CSV"; fi
  done <<< "$1"
}

if [ -n "$CSV" ]; then echo "resource_type,identifier,engine,version,engine_lifecycle_support,class,status" > "$CSV"; fi
emit "$rows" "db-instance"
[ -n "$crows" ] && emit "$crows" "db-cluster"

# Summary (instances only)
echo
echo "=== summary (db instances) ==="
awk -F'\t' '
  { total++;
    if ($4=="open-source-rds-extended-support") enabled++; else disabled++;
    if ($2=="mysql" && $3 ~ /^8\.0/) my80++;
    if ($2=="mysql" && $3 ~ /^8\.4/) my84++;
  }
  END{
    printf "  total instances      : %d\n", total;
    printf "  extended-support ON  : %d\n", enabled+0;
    printf "  extended-support OFF : %d\n", disabled+0;
    printf "  mysql 8.0.x          : %d\n", my80+0;
    printf "  mysql 8.4.x          : %d\n", my84+0;
  }' <<< "$rows"

[ -n "$CSV" ] && echo && echo "CSV written: $CSV"
