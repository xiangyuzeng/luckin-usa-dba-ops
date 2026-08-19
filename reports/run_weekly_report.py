#!/usr/bin/env python3
"""
Luckin Coffee USA Weekly Operations Report - Final Working Version
================================================================
This is the debugged and working version of the weekly report generator.

Usage:
    python3 run_weekly_report.py                    # Generate current week report
    python3 run_weekly_report.py --dry-run          # Preview data only
    python3 run_weekly_report.py --week-start 2026-04-13  # Specific week

Features:
✅ Uses MCP database integration (no environment variables needed)
✅ Handles all query patterns and field requirements
✅ Generates complete 7-chapter PDF report
✅ Real data integration with fallback defaults
✅ Full insight analysis and store rankings
✅ Action item generation

Generated Files:
- PDF Report: /app/reports/reports/weekly-report-YYYY-WNN.pdf
- JSON Data: /app/reports/complete_weekly_data.json
"""

import os
import sys

# Import the working universal injector
sys.path.insert(0, os.path.dirname(__file__))
from universal_injector import patch_and_run

def main():
    print("🔥 Luckin Coffee USA Weekly Operations Report Generator")
    print("=" * 60)
    print("✅ MCP Database Integration")
    print("✅ Complete 7-Chapter PDF Report")
    print("✅ Real Data with Smart Fallbacks")
    print("✅ Insight Analysis & Store Rankings")
    print()

    # Run the working version
    result = patch_and_run()

    if result == 0:
        print()
        print("🎉 SUCCESS! Weekly report generated successfully!")
        print()
        print("📊 Generated files:")
        print("   • PDF Report: /app/reports/reports/weekly-report-*-W*.pdf")
        print("   • Data Files: /app/reports/complete_weekly_data.json")
        print()
        print("🔍 To view the PDF, copy it to your local machine or")
        print("   use a PDF viewer in your environment.")

        # Try to find the generated PDF
        import glob
        pdfs = glob.glob("/app/reports/reports/weekly-report-*.pdf")
        if pdfs:
            latest_pdf = max(pdfs, key=os.path.getmtime)
            size_kb = os.path.getsize(latest_pdf) / 1024
            print(f"📄 Latest PDF: {latest_pdf} ({size_kb:.1f} KB)")
    else:
        print()
        print("❌ Report generation failed. Check the error messages above.")
        print("   Most common issues:")
        print("   • Database connectivity (check MCP servers)")
        print("   • Missing dependencies (install with pip)")
        print("   • Font files (check NotoSansCJK font path)")

    return result

if __name__ == "__main__":
    sys.exit(main())