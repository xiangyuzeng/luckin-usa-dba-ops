#!/usr/bin/env python3
"""
Weekly Ops Report Runner with MCP Database Support
==================================================
This script patches the original weekly_ops_report_generator.py to use MCP
database connections instead of PyMySQL direct connections.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Apply MCP patch
from mcp_database_patch import patch_database_client
patched_module = patch_database_client()

# Now run the main function from the patched module
if __name__ == "__main__":
    print("Running Weekly Ops Report Generator with MCP Database Support")
    print("=" * 60)

    # Set mock environment variables to satisfy config loading
    os.environ['MYSQL_USER'] = 'mcp_user'
    os.environ['MYSQL_PASSWORD'] = 'mcp_password'
    os.environ['HOME'] = os.path.expanduser('~')

    # Run the main function
    patched_module.main()