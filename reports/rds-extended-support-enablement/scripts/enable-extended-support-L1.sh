#!/usr/bin/env bash
# enable-extended-support-L1.sh — enable RDS Extended Support on L1 instances
# DRY-RUN by default; pass --apply to execute. See _common.sh for logic.
set -euo pipefail
LEVEL="L1"
TARGETS=(
  aws-luckyus-devops-rw
  aws-luckyus-framework01-rw
  aws-luckyus-framework02-rw
  aws-luckyus-iadmin-rw
  aws-luckyus-ibehr-rw
  aws-luckyus-ibillingcentersrv-rw
  aws-luckyus-ibizconfigcenter-rw
  aws-luckyus-icyberdata-rw
  aws-luckyus-iehr-rw
  aws-luckyus-igers-rw
  aws-luckyus-ijumpserver-jumpserver-rw
  aws-luckyus-iluckyauthapi-rw
  aws-luckyus-iluckymedia-rw
  aws-luckyus-iopenadmin-rw
  aws-luckyus-iopenlinker-rw
  aws-luckyus-iopenservice-rw
  aws-luckyus-iopshopexpand-rw
  aws-luckyus-iotplatform-rw
  aws-luckyus-ireplenishment-rw
  aws-luckyus-isalesdatamarketing-rw
  aws-luckyus-isalesmembermarketing-rw
  aws-luckyus-iunifiedreconcile-rw
  aws-luckyus-iworkflowmidlayer-rw
  aws-luckyus-ldas-rw
  aws-luckyus-ldas01-rw
  aws-luckyus-mfranchise-rw
  aws-luckyus-opempefficiency-rw
  aws-luckyus-pubdm-rw
  aws-luckyus-scm-asset-rw
  aws-luckyus-scm-openapi-rw
  aws-luckyus-scm-ordering-rw
  aws-luckyus-scm-plan-rw
  aws-luckyus-scm-purchase-rw
  aws-luckyus-scm-wds-rw
  aws-luckyus-scmsrm-rw
  aws-luckyus-upush-rw
)
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
run_enable "$@"
