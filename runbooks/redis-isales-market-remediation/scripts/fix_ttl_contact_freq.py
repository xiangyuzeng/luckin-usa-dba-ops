#!/usr/bin/env python3
"""
TTL Remediation Script: CONTACT_day / CONTACT_week / CONTACT_month / CONTACT_<member>
Cluster: luckyus-isales-market (AWS ElastiCache)

These are the legacy marketing *contact-frequency-control* counters written by the
old code path (uppercase `CONTACT_` prefix). They embed a date in the key name but
are written WITHOUT any EXPIRE, so they accumulate forever. As of 2026-06-29 they are
~95% of all no-TTL keys (~10.8M of ~11.4M) — by far the dominant memory-growth driver.

The newer code path (`cfc:v2:*`, `contact:user:contacted:activity:one:day:*`,
`user:activity:Category:FreqCtrl:*`) already sets TTL correctly; this script only
backfills the legacy keys.

DATE-AWARE strategy (safer than a flat TTL):
  - Parse the date embedded in the key.
  - expire_at = key_date + RETENTION; ttl = expire_at - now.
  - Future expiry  -> EXPIREAT at that timestamp (rolling retention window).
  - Already past    -> set a small JITTERED grace TTL so the millions of stale keys
                       drain gradually instead of a single thundering-herd purge.
  - Bare CONTACT_<member>_<n>_<n> (no date) -> flat RETENTION_BARE.

Key formats handled:
  CONTACT_day_<member>_<YYYY-MM-DD>_<n>
  CONTACT_week_<member>_<YYYY-MM-DD>_<n>
  CONTACT_month_<member>_<YYYY-MM>_<n>
  CONTACT_<member>_<n>_<n>                  (no date)

Usage:
    python fix_ttl_contact_freq.py --dry-run            # count + classify, no writes
    python fix_ttl_contact_freq.py --pattern day        # only CONTACT_day_*
    python fix_ttl_contact_freq.py                      # apply to all four patterns
"""

import argparse
import logging
import random
import re
import time
from datetime import datetime, timezone

import redis

# ─── Configuration ───────────────────────────────────────────────────────────

REDIS_HOST = "master.luckyus-isales-market.vyllrs.use1.cache.amazonaws.com"
REDIS_PORT = 6379
REDIS_DB = 0

# Retention windows (days) measured from the date embedded in the key.
RETENTION_DAYS = {
    "day":   14,   # per-day frequency caps only matter for a couple weeks
    "week":  35,   # ~5 weeks
    "month": 60,   # ~2 months
}
RETENTION_BARE_DAYS = 30   # CONTACT_<member>_<n>_<n> has no date -> flat TTL

# Stale (already past-due) keys: drain gradually with a jittered grace TTL
# so we never DEL ~9M keys at once.
GRACE_MIN_SECONDS = 6 * 3600       # 6h
GRACE_MAX_SECONDS = 3 * 86400      # 3d

# SCAN match patterns per sub-family
PATTERNS = {
    "day":   "CONTACT_day_*",
    "week":  "CONTACT_week_*",
    "month": "CONTACT_month_*",
    "bare":  "CONTACT_*",          # filtered in code to exclude day/week/month
}

BATCH_SIZE = 500
SLEEP_BETWEEN_BATCHES_MS = 50
LOG_EVERY_N_KEYS = 50000

# ─── Setup ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DATE_DAY_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})_\d+$")
DATE_MONTH_RE = re.compile(r"_(\d{4}-\d{2})_\d+$")


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


def parse_key_date(key: str, fam: str):
    """Return a tz-aware UTC datetime parsed from the key, or None if no date."""
    if fam == "month":
        m = DATE_MONTH_RE.search(key)
        if m:
            return datetime.strptime(m.group(1), "%Y-%m").replace(tzinfo=timezone.utc)
        return None
    # day / week both carry a full YYYY-MM-DD
    m = DATE_DAY_RE.search(key)
    if m:
        return datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return None


def desired_expire_at(key: str, fam: str, now_ts: int):
    """
    Compute the absolute expiry unix timestamp for a key.
    Returns (expire_at_ts, is_stale). For stale/past-due or undated keys the caller
    applies a jittered grace TTL instead of EXPIREAT.
    """
    if fam == "bare":
        return now_ts + RETENTION_BARE_DAYS * 86400, False

    kdate = parse_key_date(key, fam)
    if kdate is None:
        # Unexpected shape — fall back to a flat retention so we still bound it.
        return now_ts + RETENTION_BARE_DAYS * 86400, False

    retention = RETENTION_DAYS[fam] * 86400
    expire_at = int(kdate.timestamp()) + retention
    return expire_at, (expire_at <= now_ts)


def run(dry_run: bool, families):
    client = get_redis_client()

    try:
        info = client.info("memory")
        logger.info("Connected. Memory: %s / %s",
                    info["used_memory_human"], info["maxmemory_human"])
    except Exception as e:
        logger.error("Failed to connect to Redis: %s", e)
        return

    mode = "DRY-RUN" if dry_run else "EXECUTE"
    logger.info("Mode: %s | Families: %s", mode, ",".join(families))
    logger.info("Retention: day=%dd week=%dd month=%dd bare=%dd | grace %d-%ds",
                RETENTION_DAYS["day"], RETENTION_DAYS["week"], RETENTION_DAYS["month"],
                RETENTION_BARE_DAYS, GRACE_MIN_SECONDS, GRACE_MAX_SECONDS)

    grand = dict(scanned=0, no_ttl=0, has_ttl=0, set_future=0,
                 set_grace=0, errors=0, skipped_other_fam=0)

    for fam in families:
        pattern = PATTERNS[fam]
        logger.info("--- family=%s pattern=%s ---", fam, pattern)
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor=cursor, match=pattern, count=BATCH_SIZE)
            now_ts = int(time.time())

            for key in keys:
                # When scanning the bare "CONTACT_*" pattern, skip the dated sub-families
                if fam == "bare" and (
                    key.startswith("CONTACT_day_")
                    or key.startswith("CONTACT_week_")
                    or key.startswith("CONTACT_month_")
                ):
                    grand["skipped_other_fam"] += 1
                    continue

                grand["scanned"] += 1
                try:
                    ttl = client.ttl(key)
                    if ttl == -2:
                        continue                     # vanished between SCAN and TTL
                    if ttl != -1:
                        grand["has_ttl"] += 1
                        continue                     # already bounded; leave as-is

                    grand["no_ttl"] += 1
                    expire_at, is_stale = desired_expire_at(key, fam, now_ts)

                    if dry_run:
                        if is_stale:
                            grand["set_grace"] += 1
                        else:
                            grand["set_future"] += 1
                        continue

                    if is_stale:
                        grace = random.randint(GRACE_MIN_SECONDS, GRACE_MAX_SECONDS)
                        client.expire(key, grace)
                        grand["set_grace"] += 1
                    else:
                        client.expireat(key, expire_at)
                        grand["set_future"] += 1

                except Exception as e:
                    grand["errors"] += 1
                    if grand["errors"] <= 10:
                        logger.warning("Error on key %s: %s", key, e)

                if grand["scanned"] % LOG_EVERY_N_KEYS == 0:
                    logger.info("Progress: scanned=%(scanned)d no_ttl=%(no_ttl)d "
                                "future=%(set_future)d grace=%(set_grace)d "
                                "has_ttl=%(has_ttl)d errors=%(errors)d", grand)

            if keys:
                time.sleep(SLEEP_BETWEEN_BATCHES_MS / 1000.0)
            if cursor == 0:
                break

    logger.info("=" * 70)
    logger.info("COMPLETED [%s]", mode)
    logger.info("  Total scanned:        %d", grand["scanned"])
    logger.info("  No-TTL (targeted):    %d", grand["no_ttl"])
    logger.info("    -> rolling EXPIREAT: %d", grand["set_future"])
    logger.info("    -> stale grace TTL:  %d", grand["set_grace"])
    logger.info("  Already had TTL:      %d", grand["has_ttl"])
    logger.info("  Skipped (other fam):  %d", grand["skipped_other_fam"])
    logger.info("  Errors:               %d", grand["errors"])
    logger.info("=" * 70)
    if dry_run:
        logger.info("DRY-RUN only — no keys modified. Re-run without --dry-run to apply.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Date-aware TTL backfill for legacy CONTACT_* frequency-control keys")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count + classify only, do not modify")
    parser.add_argument("--pattern", choices=["day", "week", "month", "bare", "all"],
                        default="all", help="Restrict to one sub-family (default: all)")
    args = parser.parse_args()
    fams = ["day", "week", "month", "bare"] if args.pattern == "all" else [args.pattern]
    run(dry_run=args.dry_run, families=fams)
