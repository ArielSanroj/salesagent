#!/usr/bin/env python3
"""
Contact Research Script for HR Tech Lead Generation
Uses Hunter.io API to find and verify email addresses for target companies
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

HUNTER_API_KEY = os.getenv("HUNTER_KEY")
HUNTER_BASE_URL = "https://api.hunter.io/v2"


def find_emails_by_domain(domain: str, company: str, title: str = "CHRO") -> List[Dict]:
    """Find emails for a company domain using Hunter.io"""
    if not HUNTER_API_KEY:
        print(f"⚠️  HUNTER_KEY not configured in .env")
        return []

    try:
        # Search for emails by domain and title
        url = f"{HUNTER_BASE_URL}/domain-search"
        params = {
            "domain": domain,
            "api_key": HUNTER_API_KEY,
            "seniority": "executive",
            "title": title,
            "limit": 10,
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data.get("data") and data["data"].get("emails"):
            emails = []
            for email_info in data["data"]["emails"]:
                emails.append(
                    {
                        "email": email_info.get("value"),
                        "first_name": email_info.get("first_name"),
                        "last_name": email_info.get("last_name"),
                        "title": email_info.get("title"),
                        "confidence": email_info.get("confidence_score", 0),
                        "sources": email_info.get("sources", []),
                    }
                )
            return emails
        else:
            print(f"   ℹ️  No emails found for {domain}")
            return []

    except Exception as e:
        print(f"   ❌ Error searching {domain}: {e}")
        return []


def verify_email(email: str) -> Dict:
    """Verify an email address using Hunter.io"""
    if not HUNTER_API_KEY:
        return {"verified": False, "reason": "HUNTER_KEY not configured"}

    try:
        url = f"{HUNTER_BASE_URL}/email-verifier"
        params = {"email": email, "api_key": HUNTER_API_KEY}

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        return {
            "verified": data.get("data", {}).get("result") == "deliverable",
            "score": data.get("data", {}).get("score", 0),
            "sources": data.get("data", {}).get("sources", []),
        }
    except Exception as e:
        return {"verified": False, "reason": str(e)}


def extract_domain_from_url(url: str) -> str:
    """Extract domain from URL"""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc
    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def get_company_domain(company: str) -> str:
    """Convert company name to likely domain"""
    # Remove common suffixes and clean
    company_clean = company.lower()
    company_clean = company_clean.replace(" inc", "").replace(" corp", "")
    company_clean = company_clean.replace(" llc", "").replace(" ltd", "")
    company_clean = company_clean.replace(" & ", " ").replace(" and ", " ")
    company_clean = company_clean.replace(" ", "").replace(".", "")
    return f"{company_clean}.com"


def research_company_contacts(company: str, url: str, signal_type: str) -> Dict:
    """Research contacts for a specific company"""
    print(f"\n{'='*80}")
    print(f"🔍 Researching: {company}")
    print(f"📄 Article: {url}")
    print(f"{'='*80}")

    # Determine target title based on signal type
    signal_titles = {
        "1": ["CHRO", "VP of Human Resources", "Head of HR"],
        "2": ["CHRO", "VP of HR", "Head of People"],
        "3": ["CHRO", "VP of HR", "Head of HR Technology"],
        "4": ["CHRO", "VP of HR", "Head of HRIS"],
        "5": ["CHRO", "VP of HR", "Head of People Operations"],
        "6": ["CHRO", "VP of HR", "Head of Talent Acquisition"],
    }

    titles = signal_titles.get(signal_type, ["CHRO", "VP of HR"])

    # Try to extract domain from URL first
    article_domain = extract_domain_from_url(url)

    # If it's a news site, we need to find the actual company domain
    news_sites = [
        "postregister",
        "hastingstribune",
        "shrm",
        "prnewswire",
        "deloitte",
        "mercer",
        "ffnews",
        "fintechfinance",
    ]

    if any(news in article_domain.lower() for news in news_sites):
        # This is a news article, we need the actual company domain
        company_domain = get_company_domain(company)
        print(f"   📰 News article detected, using company domain: {company_domain}")
    else:
        company_domain = article_domain

    results = {"company": company, "url": url, "domain": company_domain, "contacts": []}

    # Search for each title
    for title in titles:
        print(f"\n   🎯 Searching for: {title}")
        emails = find_emails_by_domain(company_domain, company, title)

        for email_info in emails:
            # Verify the email
            print(
                f"      ✉️  Found: {email_info['email']} ({email_info.get('first_name', '')} {email_info.get('last_name', '')})"
            )
            verification = verify_email(email_info["email"])

            if verification.get("verified"):
                print(f"      ✅ Verified (Score: {verification.get('score', 0)})")
                results["contacts"].append(
                    {
                        **email_info,
                        "verified": True,
                        "verification_score": verification.get("score", 0),
                    }
                )
            else:
                print(
                    f"      ⚠️  Not verified: {verification.get('reason', 'Unknown')}"
                )
                results["contacts"].append({**email_info, "verified": False})

    return results


def main():
    """Main function to research contacts from CSV"""
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "all_signals.csv"

    if not Path(csv_file).exists():
        print(f"❌ CSV file not found: {csv_file}")
        return

    if not HUNTER_API_KEY:
        print("❌ HUNTER_KEY not found in .env file")
        print("   Please add: HUNTER_KEY=your_api_key")
        return

    print("=" * 80)
    print("📋 CONTACT RESEARCH - Using Hunter.io API")
    print("=" * 80)

    # Read opportunities
    opportunities = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            opportunities.append(row)

    # Focus on the 5 key companies identified
    key_companies = {
        "Rally House": None,
        "McLean & Company": None,
        "Smartstream": None,
        "Deloitte": None,
        "Mercer": None,
    }

    # Map opportunities to companies - check both Company field and Title
    for opp in opportunities:
        company = opp.get("Company", "")
        title = opp.get("Title", "")

        # Check if this is one of our target companies in Company field
        for key_company in key_companies.keys():
            if (
                key_company.lower() in company.lower()
                or company.lower() in key_company.lower()
            ):
                key_companies[key_company] = opp
                break

        # Also check article titles for company names
        for key_company in key_companies.keys():
            if key_companies[key_company] is None:  # Only if not already found
                if key_company.lower() in title.lower():
                    # Create a modified opportunity with correct company
                    modified_opp = opp.copy()
                    modified_opp["Company"] = key_company
                    key_companies[key_company] = modified_opp
                    print(f"✅ Found {key_company} in article title: {title[:60]}...")
                    break

    # Research each company
    all_results = []
    for company_name, opp_data in key_companies.items():
        if opp_data:
            results = research_company_contacts(
                company=opp_data.get("Company", company_name),
                url=opp_data.get("URL", ""),
                signal_type=opp_data.get("Signal Type", "1"),
            )
            all_results.append(results)
        else:
            print(f"\n⚠️  {company_name} not found in CSV")

    # Save results
    output_file = "contact_research_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"✅ Research complete! Results saved to: {output_file}")
    print(f"{'='*80}")

    # Summary
    total_contacts = sum(len(r["contacts"]) for r in all_results)
    verified_contacts = sum(
        len([c for c in r["contacts"] if c.get("verified")]) for r in all_results
    )

    print(f"\n📊 Summary:")
    print(f"   Total contacts found: {total_contacts}")
    print(f"   Verified contacts: {verified_contacts}")
    print(f"\n💡 Next steps:")
    print(f"   1. Review {output_file} for verified contacts")
    print(f"   2. Update all_signals.csv with verified emails")
    print(f"   3. Use these contacts for outreach campaigns")


if __name__ == "__main__":
    main()
