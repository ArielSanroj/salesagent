#!/usr/bin/env python3
"""
Contact Discovery Script for HR Tech Lead Generation
Enhances the CSV with manual contact research steps
"""

import csv
import sys
from pathlib import Path


def generate_contact_research_plan(csv_file: str = "all_signals.csv"):
    """Generate a contact research plan from opportunities CSV"""

    if not Path(csv_file).exists():
        print(f"❌ CSV file not found: {csv_file}")
        return

    print("=" * 80)
    print("📋 CONTACT RESEARCH PLAN")
    print("=" * 80)
    print()

    opportunities = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            opportunities.append(row)

    # Sort by relevance score (highest first)
    opportunities.sort(key=lambda x: float(x.get("Relevance Score", 0)), reverse=True)

    signal_names = {
        "1": "HR tech evaluations",
        "2": "New leadership ≤90 days",
        "3": "High-intent website/content",
        "4": "Tech stack change",
        "5": "Expansion",
        "6": "Hiring/downsizing",
    }

    for i, opp in enumerate(opportunities, 1):
        company = opp.get("Company", "Unknown")
        signal_type = opp.get("Signal Type", "")
        score = opp.get("Relevance Score", "0")
        url = opp.get("URL", "")

        signal_name = signal_names.get(signal_type, "Unknown signal")

        print(f"{i}. {company} ({signal_name}) - Score: {score}")
        print(f"   📄 Article: {url}")
        print(f"   🎯 Target: ", end="")

        # Suggest target based on signal type
        if signal_type == "1":
            print("CHRO, VP of HR, or Head of Talent Acquisition")
        elif signal_type == "2":
            print("Newly appointed CHRO, VP of HR, or Head of People")
        elif signal_type == "3":
            print("CHRO, VP of HR, or Head of HR Technology")
        elif signal_type == "4":
            print("CHRO, VP of HR, or Head of HRIS/HR Technology")
        elif signal_type == "5":
            print("CHRO, VP of HR, or Head of People Operations")
        elif signal_type == "6":
            print("CHRO, VP of HR, or Head of Talent Acquisition")
        else:
            print("CHRO or VP of HR")

        print(f"   🔍 Research Steps:")
        print(f"      1. Open article: {url}")
        print(f"      2. Extract names from quotes/mentions")
        print(f"      3. LinkedIn: Search '{company}' + 'CHRO' or 'VP HR'")
        print(f"      4. Company website: Check About/Leadership page")
        print(
            f"      5. Hunter.io: Domain search for {company.lower().replace(' ', '')}.com"
        )
        print()

    print("=" * 80)
    print("💡 TIPS:")
    print("  • Prioritize Signal Type 1 & 2 (highest intent)")
    print("  • Use LinkedIn Sales Navigator for verified contacts")
    print("  • Check article quotes for executive names")
    print("  • Add HUNTER_KEY to .env for automated email finding")
    print("=" * 80)


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "all_signals.csv"
    generate_contact_research_plan(csv_file)
