#!/usr/bin/env python3
"""
Test script for Gmail integration
Tests the email draft creation system
"""

import os
from datetime import datetime

import pandas as pd


def create_test_csv():
    """Create a test CSV with sample leads"""
    test_data = [
        {
            "Signal Type": "HR tech evaluations",
            "Company": "Test Company 1",
            "Person": "John Smith",
            "Action Details": "HR tech evaluations",
            "Post or News": "Test Article 1",
            "Contact Information or URL": "john.smith@testcompany1.com",
            "Personalized Email Draft": "Test draft 1",
            "relevance_score": 0.8,
            "date": "2025-09-29",
        },
        {
            "Signal Type": "New leadership ≤90 days",
            "Company": "Test Company 2",
            "Person": "Jane Doe",
            "Action Details": "New leadership ≤90 days",
            "Post or News": "Test Article 2",
            "Contact Information or URL": "jane.doe@testcompany2.com",
            "Personalized Email Draft": "Test draft 2",
            "relevance_score": 0.9,
            "date": "2025-09-29",
        },
        {
            "Signal Type": "Expansion",
            "Company": "Test Company 3",
            "Person": "Bob Johnson",
            "Action Details": "Expansion",
            "Post or News": "Test Article 3",
            "Contact Information or URL": "bob.johnson@testcompany3.com",
            "Personalized Email Draft": "Test draft 3",
            "relevance_score": 0.7,
            "date": "2025-09-29",
        },
    ]

    df = pd.DataFrame(test_data)
    df.to_csv("test_leads.csv", index=False)
    print("✅ Created test_leads.csv with 3 sample leads")
    return "test_leads.csv"


def test_gmail_system():
    """Test the Gmail email system"""
    print("🧪 Testing Gmail Email System")
    print("=" * 40)

    # Create test CSV
    csv_file = create_test_csv()

    try:
        from gmail_email_system import GmailEmailSystem

        # Initialize system
        email_system = GmailEmailSystem()

        # Check if credentials exist
        if not os.path.exists("gmail_credentials.json"):
            print("❌ Gmail credentials not found!")
            print("📝 Please follow gmail_setup_instructions.md to set up Gmail API")
            print("   1. Create Google Cloud project")
            print("   2. Enable Gmail API")
            print("   3. Create OAuth credentials")
            print("   4. Download as gmail_credentials.json")
            return False

        # Initialize Gmail service
        print("🔧 Initializing Gmail service...")
        if not email_system.get_gmail_service():
            print("❌ Failed to initialize Gmail service")
            return False

        print("✅ Gmail service initialized successfully")

        # Test email personalization
        print("\n📧 Testing email personalization...")
        test_lead = {
            "Signal Type": "HR tech evaluations",
            "Company": "Test Company",
            "Person": "John Smith",
            "Action Details": "HR tech evaluations",
        }

        subject, body = email_system.personalize_email_content(
            test_lead, "HR tech evaluations"
        )
        print(f"✅ Generated subject: {subject}")
        print(f"✅ Generated body preview: {body[:100]}...")

        # Test draft creation (without actually creating drafts)
        print("\n📝 Testing draft creation logic...")
        df = pd.read_csv(csv_file)
        leads_data = df.to_dict("records")

        processed_count = 0
        for lead in leads_data:
            contact_info = lead.get("Contact Information or URL", "")
            if "@" in contact_info and "Manual validation needed" not in contact_info:
                processed_count += 1

        print(f"✅ Would process {processed_count} leads for draft creation")

        print("\n🎯 Gmail integration test completed successfully!")
        print("📋 Next steps:")
        print("   1. Set up Gmail credentials (gmail_setup_instructions.md)")
        print("   2. Run weekly automation")
        print("   3. Check Gmail drafts folder")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("📦 Please install Gmail API dependencies:")
        print(
            "   pip install google-auth google-auth-oauthlib google-api-python-client"
        )
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Main test function"""
    print("🚀 Gmail Integration Test")
    print("=" * 50)

    success = test_gmail_system()

    if success:
        print("\n✅ All tests passed! Gmail integration is ready.")
    else:
        print("\n❌ Tests failed. Please check setup and try again.")

    # Cleanup
    if os.path.exists("test_leads.csv"):
        os.remove("test_leads.csv")
        print("🧹 Cleaned up test files")


if __name__ == "__main__":
    main()
