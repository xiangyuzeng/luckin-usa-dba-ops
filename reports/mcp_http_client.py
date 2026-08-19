#!/usr/bin/env python3
"""
MCP HTTP Client for Database Operations
======================================
Direct HTTP client for MCP database gateway operations.
"""

import json
import requests
import time


class MCPHttpDatabaseClient:
    """Database client that calls MCP via HTTP."""

    # MCP server configuration
    MCP_BASE_URL = "http://10.238.3.43:8080"

    # Schema to server mapping
    SCHEMA_TO_SERVER = {
        'luckyus_sales_order': 'aws-luckyus-salesorder-rw',
        'luckyus_iluckyhealth': 'aws-luckyus-iluckyhealth-rw',
        'luckyus_opshop': 'aws-luckyus-opshop-rw'
    }

    def __init__(self, configs=None):
        self.configs = configs or {}
        self.session = requests.Session()
        print(f"[MCP HTTP] Initialized with base URL: {self.MCP_BASE_URL}")

    def query(self, database: str, sql: str, params: tuple = ()) -> list[dict]:
        """Execute SQL query via MCP HTTP interface."""
        if database not in self.SCHEMA_TO_SERVER:
            raise KeyError(f"No MCP server for schema '{database}'. Known: {list(self.SCHEMA_TO_SERVER.keys())}")

        server = self.SCHEMA_TO_SERVER[database]

        # Format SQL with parameters
        formatted_sql = sql
        if params:
            for param in params:
                if isinstance(param, str):
                    escaped = param.replace("'", "''")
                    formatted_sql = formatted_sql.replace('%s', f"'{escaped}'", 1)
                elif param is None:
                    formatted_sql = formatted_sql.replace('%s', 'NULL', 1)
                else:
                    formatted_sql = formatted_sql.replace('%s', str(param), 1)

        # Add schema name if not present
        if f'{database}.' not in formatted_sql:
            formatted_sql = formatted_sql.replace('FROM t_', f'FROM {database}.t_')
            formatted_sql = formatted_sql.replace('JOIN t_', f'JOIN {database}.t_')

        print(f"[MCP HTTP] {server}: {formatted_sql[:100]}...")

        # Prepare MCP request payload
        payload = {
            "method": "mcp__mcp-db-gateway__mysql_query",
            "params": {
                "server": server,
                "sql": formatted_sql
            }
        }

        try:
            # Send HTTP POST request to MCP gateway
            response = self.session.post(
                f"{self.MCP_BASE_URL}/mcp",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            if 'rows' in result:
                rows = result['rows']
                print(f"[MCP HTTP] Got {len(rows)} rows")
                return rows
            elif 'error' in result:
                raise RuntimeError(f"MCP error: {result['error']}")
            else:
                print(f"[MCP HTTP] Unexpected response format: {result}")
                return []

        except requests.exceptions.RequestException as e:
            print(f"[MCP HTTP] HTTP request failed: {e}")
            raise RuntimeError(f"MCP HTTP request failed: {e}")
        except json.JSONDecodeError as e:
            print(f"[MCP HTTP] JSON decode error: {e}")
            raise RuntimeError(f"MCP response parsing failed: {e}")


def patch_and_run():
    """Patch the weekly report generator with HTTP MCP client."""
    print("Weekly Report Generator with MCP HTTP Client")
    print("=" * 50)

    # Set environment variables
    import os
    os.environ['MYSQL_USER'] = 'mcp_http'
    os.environ['MYSQL_PASSWORD'] = 'mcp_http'
    os.environ['HOME'] = os.path.expanduser('~')

    # Import and patch
    import sys
    sys.path.insert(0, '/app/reports')
    import weekly_ops_report_generator as wrg

    # Replace DatabaseClient
    wrg.DatabaseClient = MCPHttpDatabaseClient
    print("[MCP HTTP] DatabaseClient replaced with HTTP MCP client")

    # Run the main function
    try:
        wrg.main()
    except Exception as e:
        print(f"[MCP HTTP] Execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(patch_and_run())