#!/bin/bash
# cron_reconcile.sh — 定时对账 AWS Redis 监控三文件（dry-run，只在漂移/异常时告警）。
# 放在 exporter 目录，由 crontab 调用。兼容 Amazon Linux 2 / bash 4.2。
#
# 行为：跑 sync_redis_monitoring.py（不加 --apply，只读不写），当出现
#   · 退出码 !=0（[!] DB 在营但 AWS 无对应 RG 之类硬问题），或
#   · 输出里有「将更新」（说明现网三文件与 AWS+ozono 已经不同步）
# 时，把完整输出发告警；否则静默。
#
# 密码不写进 crontab：从同目录 root-only 文件 .ldas_pwd（chmod 600）读取。
set -u

DIR="/data/redis-exporter/redis_exporter-v1.74.0.linux-amd64"
PWD_FILE="$DIR/.ldas_pwd"          # 仅存 ldas 只读密码一行，chmod 600 root:root
SCRIPT="$DIR/sync_redis_monitoring.py"

cd "$DIR" || { echo "cd $DIR failed" >&2; exit 2; }

if [ ! -r "$PWD_FILE" ]; then
    echo "missing/unreadable $PWD_FILE" >&2
    exit 2
fi
export LDAS_PWD="$(cat "$PWD_FILE")"

OUT="$(python3 "$SCRIPT" 2>&1)"
RC=$?

need_alert=0
[ "$RC" -ne 0 ] && need_alert=1
printf '%s\n' "$OUT" | grep -q '将更新' && need_alert=1

if [ "$need_alert" -eq 1 ]; then
    SUBJECT="[LKUS] AWS Redis 监控漂移待处理 (rc=$RC)"
    # —— 告警渠道二选一，按现网改 ——
    # (a) 邮件：
    if command -v mail >/dev/null 2>&1; then
        printf '%s\n' "$OUT" | mail -s "$SUBJECT" dba@example.com
    fi
    # (b) 或 webhook（如你的 alert-mailserver / Slack incoming webhook）：
    # curl -sS -X POST -H 'Content-Type: text/plain' \
    #     --data-binary "$(printf '%s\n%s\n' "$SUBJECT" "$OUT")" \
    #     "https://<your-webhook-endpoint>" >/dev/null
    :
fi

# cron 本身总是正常退出，避免 cron MAILTO 每次重复发；告警已单独发出。
exit 0
