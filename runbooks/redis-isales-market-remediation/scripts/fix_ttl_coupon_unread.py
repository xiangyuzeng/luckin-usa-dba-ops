#!/usr/bin/env python3
"""
TTL Remediation Script: MARKETING:COUPON:UNREAD:*
Cluster: luckyus-isales-market (AWS ElastiCache)
Purpose: Set TTL on coupon unread flag keys that currently have no expiry.

These keys are per-user sets tracking unread coupon IDs.
They grow monotonically as new users are created and never expire.
Proposed TTL: 60 days (5184000 seconds) — coupon campaigns rarely exceed 60 days.

Usage:
    python fix_ttl_coupon_unread.py --dry-run     # Count keys, no changes
    python fix_ttl_coupon_unread.py               # Apply TTL to all matching keys
"""

import argparse
import logging
import time
import ssl
import redis

# ─── Configuration ───────────────────────────────────────────────────────────

REDIS_HOST = "master.luckyus-isales-market.vyllrs.use1.cache.amazonaws.com"
REDIS_PORT = 6379
REDIS_DB = 0

KEY_PATTERN = "MARKETING:COUPON:UNREAD:*"
TARGET_TTL_SECONDS = 5184000  # 60 days

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
        ssl_ca_certs="/etc/ssl/certs/ca-certificates.crt",  # adjust for your OS
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
    )


def run(dry_run: bool = True):
    """Scan keys matching pattern and apply TTL."""
    client = get_redis_client()

    # Verify connectivity
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
    total_no_ttl = 0
    total_already_has_ttl = 0
    total_set_ttl = 0
    total_errors = 0
    cursor = 0

    while True:
        cursor, keys = client.scan(cursor=cursor, match=KEY_PATTERN, count=BATCH_SIZE)

        for key in keys:
            total_scanned += 1

            try:
                ttl = client.ttl(key)

                if ttl == -1:
                    # Key exists but has no TTL
                    total_no_ttl += 1
                    if not dry_run:
                        client.expire(key, TARGET_TTL_SECONDS)
                        total_set_ttl += 1
                elif ttl == -2:
                    # Key does not exist (expired between SCAN and TTL check)
                    pass
                else:
                    # Key already has a TTL
                    total_already_has_ttl += 1

            except Exception as e:
                total_errors += 1
                if total_errors <= 10:
                    logger.warning("Error processing key %s: %s", key, e)

            if total_scanned % LOG_EVERY_N_KEYS == 0:
                logger.info(
                    "Progress: scanned=%d, no_ttl=%d, already_has_ttl=%d, set_ttl=%d, errors=%d",
                    total_scanned, total_no_ttl, total_already_has_ttl, total_set_ttl, total_errors,
                )

        # Rate limiting between batches
        if keys:
            time.sleep(SLEEP_BETWEEN_BATCHES_MS / 1000.0)

        if cursor == 0:
            break

    # Final summary
    logger.info("=" * 70)
    logger.info("COMPLETED [%s]", mode)
    logger.info("  Pattern:            %s", KEY_PATTERN)
    logger.info("  Total scanned:      %d", total_scanned)
    logger.info("  Keys with no TTL:   %d", total_no_ttl)
    logger.info("  Keys already w/TTL: %d", total_already_has_ttl)
    if not dry_run:
        logger.info("  TTL applied:        %d", total_set_ttl)
    logger.info("  Errors:             %d", total_errors)
    logger.info("  Target TTL:         %ds (%d days)", TARGET_TTL_SECONDS, TARGET_TTL_SECONDS // 86400)
    logger.info("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set TTL on MARKETING:COUPON:UNREAD:* keys")
    parser.add_argument("--dry-run", action="store_true", help="Count keys only, do not modify")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
