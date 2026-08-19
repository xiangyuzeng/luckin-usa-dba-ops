#!/usr/bin/env python3
"""
MCP Database Forwarder for Weekly Ops Report
===========================================
This replaces the DatabaseClient with one that forwards queries to MCP.
"""

import json
import sys
import os

# Import the MCP tool function - this will be available when running in Claude Code
def mcp_mysql_query(server: str, sql: str):
    """Forward query to MCP. This will be replaced with actual MCP call."""
    # This is a placeholder - when actually running in Claude Code,
    # this will use the real MCP tool
    raise RuntimeError("This should only be called within Claude Code with MCP tools available")


class MCPForwardingDatabaseClient:
    """Database client that forwards all queries to MCP."""

    # Mapping from schema names to MCP server names
    SCHEMA_TO_SERVER = {
        'luckyus_sales_order': 'aws-luckyus-salesorder-rw',
        'luckyus_iluckyhealth': 'aws-luckyus-iluckyhealth-rw',
        'luckyus_opshop': 'aws-luckyus-opshop-rw'
    }

    def __init__(self, configs=None):
        """Initialize MCP client. Configs are ignored as MCP handles authentication."""
        self.configs = configs or {}
        print(f"[MCP Forwarder] Initialized with schema mappings: {list(self.SCHEMA_TO_SERVER.keys())}")

    def query(self, database: str, sql: str, params: tuple = ()) -> list[dict]:
        """Execute SQL query via MCP and return results."""
        if database not in self.SCHEMA_TO_SERVER:
            raise KeyError(
                f"No MCP server mapped for schema '{database}'. "
                f"Known schemas: {sorted(self.SCHEMA_TO_SERVER)}"
            )

        server = self.SCHEMA_TO_SERVER[database]

        # Handle parameterized queries
        formatted_sql = sql
        if params:
            # Simple parameter substitution with proper escaping
            for param in params:
                if isinstance(param, str):
                    # Escape single quotes and wrap in quotes
                    escaped = param.replace("'", "''")
                    formatted_sql = formatted_sql.replace('%s', f"'{escaped}'", 1)
                elif param is None:
                    formatted_sql = formatted_sql.replace('%s', 'NULL', 1)
                else:
                    formatted_sql = formatted_sql.replace('%s', str(param), 1)

        print(f"[MCP Forwarder] Executing on {server}: {formatted_sql[:100]}...")

        try:
            # This is where the magic happens - we forward to MCP
            result = mcp_mysql_query(server, formatted_sql)

            # MCP returns format: {"rows": [...], "count": N}
            if isinstance(result, dict) and 'rows' in result:
                rows = result['rows']
                print(f"[MCP Forwarder] Got {len(rows)} rows")
                return rows
            else:
                print(f"[MCP Forwarder] Unexpected result format: {type(result)}")
                return []

        except Exception as e:
            print(f"[MCP Forwarder] Query failed: {e}")
            raise RuntimeError(f"MCP query failed: {e}")


def patch_database_client():
    """Replace DatabaseClient in the weekly report generator with MCP forwarder."""
    import weekly_ops_report_generator as wrg

    # Replace the DatabaseClient class
    wrg.DatabaseClient = MCPForwardingDatabaseClient
    print("[MCP Forwarder] DatabaseClient replaced with MCP forwarder")

    return wrg


if __name__ == "__main__":
    print("MCP Database Forwarder")
    print(f"Schema mappings: {MCPForwardingDatabaseClient.SCHEMA_TO_SERVER}")