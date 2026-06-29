#!/usr/bin/env python3
"""
TTL Remediation Script: contact:last:activity:*
Cluster: luckyus-isales-market (AWS ElastiCache)
Purpose: Reduce TTL on contact last-activity keys from ~364 days to 90 days.

These are string keys (STRLEN=24) storing timestamps of last contact activity.
Currently they have ~364-day TTL, effectively making them permanent.
Proposed TTL: 90 days (7776000 seconds) — reduces memory footprint while
retaining enough activity history for marketing segmentation.

Note: This script only REDUCES existing TTL. It will NOT set TTL on keys
that have no TTL (TTL=-1). It skips keys whose current TTL is already <= 90 days.

Usage:
    python fix_ttl_last_activity.py --dry-run     # Count keys, no changes
    python fix_ttl_last_activity.py               # Reduce TTL on matching keys
"""

import argparse
import logging
import time
import redis

# ─── Configuration ───────────────────────────────────────────────────────────

REDIS_HOST = "master.luckyus-isales-market.vyllrs.use1.cache.amazonaws.com"
REDIS_PORT = 6379
REDIS_DB = 0

KEY_PATTERN = "contact:last:activity:*"
TARGET_TTL_SECONDS = 7776000  # 90 days

BATCH_SIZE = 500
SLEEP_BETWEEN_BATCHES_MS = 50
LOG_EVERY_N_KEYS = 10000

# ─── Setup ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_redis_client() -> redis.Redis:
    """Create a TLS-enabled Redis client for ElastiCache."""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        ssl=True,
        ssl_cert_reqs="required",
        ssl_ca_certs="/etc/ssl/certs/ca-certificates.crt",
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
    )


def run(dry_run: bool = True):
    """Scan keys matching pattern and reduce TTL if currently > target."""
    client = get_redis_client()

    try:
        info = client.info("memory")
        logger.info(
            "Connected to Redis. Memory: %s / %s",
            info["used_memory_human"],
            info["maxmemory_human"],
        )
    except Exception as e:
        logger.error("Failed to connect to Redis: %s", e)
        return

    mode = "DRY-RUN" if dry_run else "EXECUTE"
    logger.info("Mode: %s | Pattern: %s | Target TTL: %ds (%d days)",
                mode, KEY_PATTERN, TARGET_TTL_SECONDS, TARGET_TTL_SECONDS // 86400)

    total_scanned = 0
    total_ttl_reduced = 0
    total_ttl_already_ok = 0
    total_no_ttl = 0
    total_errors = 0
    cursor = 0

    while True:
        cursor, keys = client.scan(cursor=cursor, match=KEY_PATTERN, count=BATCH_SIZE)

        for key in keys:
            total_scanned += 1

            try:
                ttl = client.ttl(key)

                if ttl == -1:
                    # Key has no TTL — do NOT set one (different pattern, leave for audit)
                    total_no_ttl += 1
                elif ttl == -2:
                    # Key does not exist
                    pass
                elif ttl > TARGET_TTL_SECONDS:
                    # Current TTL is longer than target — reduce it
                    total_ttl_reduced += 1
                    if not dry_run:
                        client.expire(key, TARGET_TTL_SECONDS)
                else:
                    # Current TTL is already <= target
                    total_ttl_already_ok += 1

            except Exception as e:
                total_errors += 1
                if total_errors <= 10:
                    logger.warning("Error processing key %s: %s", key, e)

            if total_scanned % LOG_EVERY_N_KEYS == 0:
                logger.info(
                    "Progress: scanned=%d, reduced=%d, already_ok=%d, no_ttl=%d, errors=%d",
                    total_scanned, total_ttl_reduced, total_ttl_already_ok, total_no_ttl, total_errors,
                )

        if keys:
            time.sleep(SLEEP_BETWEEN_BATCHES_MS / 1000.0)

        if cursor == 0:
            break

    logger.info("=" * 70)
    logger.info("COMPLETED [%s]", mode)
    logger.info("  Pattern:             %s", KEY_PATTERN)
    logger.info("  Total scanned:       %d", total_scanned)
    logger.info("  TTL reduced (>%dd):  %d", TARGET_TTL_SECONDS // 86400, total_ttl_reduced)
    logger.info("  TTL already <= %dd:  %d", TARGET_TTL_SECONDS // 86400, total_ttl_already_ok)
    logger.info("  Keys with no TTL:    %d (skipped — requires separate review)", total_no_ttl)
    logger.info("  Errors:              %d", total_errors)
    logger.info("  Target TTL:          %ds (%d days)", TARGET_TTL_SECONDS, TARGET_TTL_SECONDS // 86400)
    logger.info("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reduce TTL on contact:last:activity:* keys")
    parser.add_argument("--dry-run", action="store_true", help="Count keys only, do not modify")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
