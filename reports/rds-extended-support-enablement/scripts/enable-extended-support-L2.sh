#!/usr/bin/env bash
# enable-extended-support-L2.sh — enable RDS Extended Support on L2 instances
# DRY-RUN by default; pass --apply to execute. See _common.sh for logic.
set -euo pipefail
LEVEL="L2"
TARGETS=(
  aws-luckyus-fichargecontrol-rw
  aws-luckyus-ifiaccounting-rw
  aws-luckyus-ilsopdevopsdata-rw
  aws-luckyus-iluckyams-rw
  aws-luckyus-iluckydorisops-rw
  aws-luckyus-iluckyhealth-rw
  aws-luckyus-iopocp-rw
  aws-luckyus-oplog-rw
  aws-luckyus-opqualitycontrol-rw
  aws-luckyus-scm-wmssimulate-rw
)
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
run_enable "$@"
