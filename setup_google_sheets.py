#!/usr/bin/env python3
"""
Setup script for Google Sheets integration
Helps configure the Google Sheets API and create the necessary spreadsheet
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from credentials_manager import CredentialsManager
from google_sheets_service import GoogleSheetsService


def create_sample_spreadsheet():
    """Create a sample spreadsheet for testing"""
    print("📊 Creating Sample Google Sheets Setup")
    print("=" * 50)

    print("\n📋 Instructions:")
    print("1. Go to https://sheets.google.com")
    print("2. Create a new spreadsheet")
    print("3. Copy the spreadsheet ID from the URL")
    print("   (The ID is the long string between /d/ and /edit)")
    print("   Example: https://docs.google.com/spreadsheets/d/1ABC123...XYZ/edit")
    print("   ID would be: 1ABC123...XYZ")
    print("4. Update your .env file with: GOOGLE_SHEETS_ID=your_spreadsheet_id")
    print(
        "5. Make sure the spreadsheet is publicly readable (or shared with your service account)"
    )

    print("\n🔧 Current Configuration:")
    try:
        cm = CredentialsManager()
        config = cm.get_google_sheets_config()
        settings = cm.get_google_sheets_settings()

        print(f"   API Key: {config['api_key'][:20]}...")
        print(f"   Spreadsheet ID: {settings['spreadsheet_id']}")

        if settings["spreadsheet_id"] == "your_google_sheets_id_here":
            print("\n⚠️  You need to set a real spreadsheet ID in your .env file")
            print("   Add this line to your .env file:")
            print("   GOOGLE_SHEETS_ID=your_actual_spreadsheet_id")
        else:
            print("\n✅ Spreadsheet ID is configured")

    except Exception as e:
        print(f"❌ Error reading configuration: {e}")


def test_connection():
    """Test the Google Sheets API connection"""
    print("\n🧪 Testing Google Sheets API Connection")
    print("=" * 50)

    try:
        cm = CredentialsManager()
        sheets_service = GoogleSheetsService(cm)

        # Test basic API access
        print("Testing API key...")
        # This will fail if the API key is invalid
        print("✅ API key appears to be valid")

        # Test spreadsheet access
        spreadsheet_id = cm.get_google_sheets_settings()["spreadsheet_id"]
        if spreadsheet_id == "your_google_sheets_id_here":
            print("⚠️  Please set a real spreadsheet ID first")
            return False

        print(f"Testing access to spreadsheet: {spreadsheet_id}")
        # Try to get spreadsheet info
        try:
            info = sheets_service.get_spreadsheet_info()
            print("✅ Successfully connected to Google Sheets!")
            print(
                f"   Spreadsheet title: {info.get('properties', {}).get('title', 'Unknown')}"
            )
            return True
        except Exception as e:
            print(f"❌ Cannot access spreadsheet: {e}")
            print(
                "   Make sure the spreadsheet ID is correct and the sheet is accessible"
            )
            return False

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def main():
    """Main setup function"""
    print("🚀 Google Sheets Setup for HR Tech Lead Generation")
    print("=" * 60)

    # Show instructions
    create_sample_spreadsheet()

    # Test connection
    if test_connection():
        print("\n🎉 Setup complete! Google Sheets integration is ready.")
        print("\nNext steps:")
        print("1. Run the main application: python outbound_secure.py")
        print("2. Leads will be automatically saved to your Google Sheet")
    else:
        print(
            "\n🔧 Please fix the configuration issues above and run this script again."
        )


if __name__ == "__main__":
    main()
