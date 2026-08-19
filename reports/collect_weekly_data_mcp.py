#!/usr/bin/env python3
"""
Weekly Report Data Collector using MCP
======================================
This script collects all the data needed for the weekly report using MCP tools,
then outputs JSON that can be used by the report generator.
"""

import json
from datetime import datetime, timedelta


def week_bounds(start_date: datetime) -> tuple[datetime, datetime]:
    """Return (Monday 00:00, Sunday 23:59:59) for the week containing start_date."""
    monday = start_date - timedelta(days=start_date.weekday())
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


def main():
    # Get current week
    today = datetime.now()
    days_since_monday = today.weekday()
    if days_since_monday == 0 and today.hour < 9:
        # Monday before 9 AM — report on 2 weeks ago
        week_start = today - timedelta(days=7)
    else:
        week_start = today - timedelta(days=days_since_monday + 7)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    mon, sun = week_bounds(week_start)
    iso_year, iso_week, _ = mon.isocalendar()

    print(f"=== Collecting data for Week {iso_year}-W{iso_week:02d} ===")
    print(f"Period: {mon:%Y-%m-%d} (Mon) to {sun:%Y-%m-%d} (Sun)")
    print()
    print("This script will collect data using MCP tools.")
    print("Run this in Claude Code environment with MCP access.")
    print()
    print("Next step: Claude Code should execute MCP queries and collect data.")

    # Output the SQL queries that need to be executed
    queries = {
        "overview_this_week": f"""
            SELECT
                COUNT(*) AS total_orders,
                SUM(CASE WHEN status IN (20,90) THEN 1 ELSE 0 END) AS completed_orders,
                SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) AS cancelled_orders,
                SUM(CASE WHEN status IN (20,90) THEN pay_money ELSE 0 END) AS total_revenue,
                AVG(CASE WHEN status IN (20,90) THEN pay_money END) AS avg_ticket
            FROM t_order
            WHERE CONVERT_TZ(create_time, 'UTC', 'America/New_York') >= '{mon:%Y-%m-%d} 00:00:00'
              AND CONVERT_TZ(create_time, 'UTC', 'America/New_York') < '{sun + timedelta(days=1):%Y-%m-%d} 00:00:00'
        """,

        "daily_breakdown": f"""
            SELECT
                DATE(CONVERT_TZ(create_time, 'UTC', 'America/New_York')) AS order_date,
                DAYOFWEEK(CONVERT_TZ(create_time, 'UTC', 'America/New_York')) AS dow,
                COUNT(*) AS orders,
                SUM(pay_money) AS revenue,
                AVG(pay_money) AS avg_ticket
            FROM t_order
            WHERE status IN (20, 90)
              AND CONVERT_TZ(create_time, 'UTC', 'America/New_York') >= '{mon:%Y-%m-%d} 00:00:00'
              AND CONVERT_TZ(create_time, 'UTC', 'America/New_York') < '{sun + timedelta(days=1):%Y-%m-%d} 00:00:00'
            GROUP BY DATE(CONVERT_TZ(create_time, 'UTC', 'America/New_York'))
            ORDER BY order_date
        """,

        "store_performance": f"""
            SELECT
                o.shop_id,
                o.shop_name,
                COUNT(*) AS total_orders,
                SUM(CASE WHEN o.status IN (20,90) THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN o.status IN (20,90) THEN o.pay_money ELSE 0 END) AS revenue,
                AVG(CASE WHEN o.status IN (20,90) THEN o.pay_money END) AS avg_ticket
            FROM t_order o
            WHERE CONVERT_TZ(o.create_time, 'UTC', 'America/New_York') >= '{mon:%Y-%m-%d} 00:00:00'
              AND CONVERT_TZ(o.create_time, 'UTC', 'America/New_York') < '{sun + timedelta(days=1):%Y-%m-%d} 00:00:00'
            GROUP BY o.shop_id, o.shop_name
            ORDER BY revenue DESC
        """
    }

    with open('/app/reports/weekly_queries.json', 'w') as f:
        json.dump({
            'week_info': {
                'start': mon.isoformat(),
                'end': sun.isoformat(),
                'iso_year': iso_year,
                'iso_week': iso_week
            },
            'queries': queries
        }, f, indent=2)

    print("Queries saved to weekly_queries.json")
    print("Next: Execute these queries with MCP tools")


if __name__ == "__main__":
    main()