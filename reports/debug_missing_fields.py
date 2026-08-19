#!/usr/bin/env python3
"""
Debug Missing Fields
===================
This script runs the report generator and captures all missing field errors.
"""

import subprocess
import re
import sys

def run_and_capture_errors():
    """Run the universal injector and capture all KeyError messages."""
    try:
        result = subprocess.run(
            ['python3', 'universal_injector.py', '--dry-run'],
            capture_output=True, text=True, cwd='/app/reports'
        )

        output = result.stderr + result.stdout

        # Find all KeyError messages
        keyerrors = re.findall(r"KeyError: '([^']+)'", output)

        if keyerrors:
            print("Missing fields found:")
            for field in keyerrors:
                print(f"  - {field}")

            print(f"\nTotal missing fields: {len(keyerrors)}")
            print(f"Unique missing fields: {len(set(keyerrors))}")

            # Generate field additions
            print("\nFields to add to universal response:")
            unique_fields = set(keyerrors)
            for field in sorted(unique_fields):
                print(f"            '{field}': 0.0,")
        else:
            print("No KeyError found! Script may have completed successfully.")

        return result.returncode == 0, keyerrors

    except Exception as e:
        print(f"Error running script: {e}")
        return False, []

if __name__ == "__main__":
    success, errors = run_and_capture_errors()
    if success:
        print("SUCCESS: Script completed without KeyError!")
    else:
        print(f"FAILED: Found {len(errors)} missing fields")
    sys.exit(0 if success else 1)