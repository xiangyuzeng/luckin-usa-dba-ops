#!/usr/bin/env bash
# enable-extended-support-L0.sh — enable RDS Extended Support on L0 instances
# DRY-RUN by default; pass --apply to execute. See _common.sh for logic.
set -euo pipefail
LEVEL="L0"
TARGETS=(
  aws-luckyus-cdpactivity-rw
  aws-luckyus-fitax-rw
  aws-luckyus-ipermission-rw
  aws-luckyus-iriskcontrolservice-rw
  aws-luckyus-isalescdp-rw
  aws-luckyus-isalescouponservice-rw
  aws-luckyus-isalesprivatedomain-rw
  aws-luckyus-opproduction-rw
  aws-luckyus-opshop-rw
  aws-luckyus-opshopsale-rw
  aws-luckyus-salescrm-rw
  aws-luckyus-salesmarketing-rw
  aws-luckyus-salesorder-rw
  aws-luckyus-salespayment-rw
  aws-luckyus-scm-shopstock-rw
  aws-luckyus-scmcommodity-rw
)
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
run_enable "$@"
