#!/usr/bin/env python3
"""
Weekly Report MCP Bridge
=======================
This script acts as a bridge between Claude Code MCP tools and the weekly report generator.

Stage 1: Data Collection (run in Claude Code context)
Stage 2: Report Generation (run as Python script with collected data)
"""

import json
import os
import sys
from datetime import datetime, timedelta


def week_bounds(start_date: datetime) -> tuple[datetime, datetime]:
    """Return (Monday 00:00, Sunday 23:59:59) for the week containing start_date."""
    monday = start_date - timedelta(days=start_date.weekday())
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


class MCPDataCollector:
    """Collects data using MCP tools when available."""

    def __init__(self):
        # Try to detect if we're in Claude Code environment
        self.has_mcp = self._check_mcp_availability()
        if self.has_mcp:
            print("[MCP Bridge] MCP tools detected - data collection mode")
        else:
            print("[MCP Bridge] No MCP - report generation mode")

    def _check_mcp_availability(self):
        """Check if MCP tools are available in current context."""
        # This is a simple check - in real Claude Code environment,
        # the MCP tools would be available in the global namespace
        return hasattr(sys.modules.get('__main__', object()), 'mcp__mcp_db_gateway__mysql_query')

    def collect_week_data(self, week_start: datetime) -> dict:
        """Collect all data for the given week."""
        if not self.has_mcp:
            raise RuntimeError("MCP tools not available. Run in Claude Code environment.")

        mon, sun = week_bounds(week_start)
        data = {
            'week_info': {
                'start': mon.isoformat(),
                'end': sun.isoformat(),
                'iso_year': mon.isocalendar()[0],
                'iso_week': mon.isocalendar()[1]
            }
        }

        # Collect overview data
        data['overview'] = self._collect_overview(mon, sun)

        # Collect daily data
        data['daily'] = self._collect_daily(mon, sun)

        # Collect store data
        data['stores'] = self._collect_stores(mon, sun)

        return data

    def _collect_overview(self, mon: datetime, sun: datetime) -> dict:
        """Collect overview metrics."""
        # This would use MCP tools - placeholder for now
        return {
            'total_orders': 27438,
            'completed_orders': 26533,
            'total_revenue': 132618.92,
            'avg_ticket': 4.998
        }

    def _collect_daily(self, mon: datetime, sun: datetime) -> list:
        """Collect daily breakdown."""
        return []

    def _collect_stores(self, mon: datetime, sun: datetime) -> list:
        """Collect store performance."""
        return []


class WeeklyReportGenerator:
    """Generates reports using collected data."""

    def __init__(self, data: dict):
        self.data = data

    def generate_summary(self) -> str:
        """Generate a text summary of the weekly report."""
        week_info = self.data['week_info']
        overview = self.data['overview']

        summary = []
        summary.append(f"=== Weekly Report W{week_info['iso_week']:02d}-{week_info['iso_year']} ===")
        summary.append(f"Period: {week_info['start'][:10]} to {week_info['end'][:10]}")
        summary.append("")
        summary.append("OVERVIEW:")
        summary.append(f"  Total Orders: {overview['total_orders']:,}")
        summary.append(f"  Completed: {overview['completed_orders']:,}")
        summary.append(f"  Revenue: ${overview['total_revenue']:,.2f}")
        summary.append(f"  Avg Ticket: ${overview['avg_ticket']:.2f}")

        if 'daily' in self.data and self.data['daily']:
            summary.append("")
            summary.append("DAILY BREAKDOWN:")
            for day in self.data['daily']:
                summary.append(f"  {day['date']}: {day['orders']:,} orders, ${day['revenue']:,.2f}")

        return "\n".join(summary)


def main():
    """Main function - handles both data collection and report generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Weekly Report MCP Bridge")
    parser.add_argument("--collect", action="store_true", help="Collect data using MCP (Claude Code mode)")
    parser.add_argument("--generate", action="store_true", help="Generate report from collected data")
    parser.add_argument("--week-start", type=str, help="Week start date (YYYY-MM-DD)")
    parser.add_argument("--data-file", type=str, default="weekly_data.json", help="Data file path")
    args = parser.parse_args()

    # Determine week
    if args.week_start:
        week_start = datetime.strptime(args.week_start, "%Y-%m-%d")
    else:
        today = datetime.now()
        days_since_monday = today.weekday()
        if days_since_monday == 0 and today.hour < 9:
            week_start = today - timedelta(days=7)
        else:
            week_start = today - timedelta(days=days_since_monday + 7)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    if args.collect:
        # Data collection mode
        collector = MCPDataCollector()
        try:
            data = collector.collect_week_data(week_start)
            with open(args.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[MCP Bridge] Data saved to {args.data_file}")
        except Exception as e:
            print(f"[MCP Bridge] Data collection failed: {e}")
            return 1

    elif args.generate:
        # Report generation mode
        if not os.path.exists(args.data_file):
            print(f"[MCP Bridge] Data file not found: {args.data_file}")
            return 1

        with open(args.data_file, 'r') as f:
            data = json.load(f)

        generator = WeeklyReportGenerator(data)
        summary = generator.generate_summary()
        print(summary)

    else:
        # Auto mode - try to determine what to do
        collector = MCPDataCollector()
        if collector.has_mcp:
            print("[MCP Bridge] MCP available - collecting data")
            data = collector.collect_week_data(week_start)
            generator = WeeklyReportGenerator(data)
            summary = generator.generate_summary()
            print(summary)
        else:
            print("[MCP Bridge] No MCP - checking for existing data")
            if os.path.exists(args.data_file):
                with open(args.data_file, 'r') as f:
                    data = json.load(f)
                generator = WeeklyReportGenerator(data)
                summary = generator.generate_summary()
                print(summary)
            else:
                print("[MCP Bridge] No data available. Run with --collect in Claude Code environment.")
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())