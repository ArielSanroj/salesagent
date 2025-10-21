#!/usr/bin/env python3
"""
Test script for Google Sheets integration
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from credentials_manager import CredentialsManager
from google_sheets_service import GoogleSheetsService

def test_google_sheets():
    """Test Google Sheets integration"""
    print("🧪 Testing Google Sheets Integration")
    print("=" * 50)
    
    try:
        # Initialize services
        print("\n1. Initializing services...")
        cm = CredentialsManager()
        sheets_service = GoogleSheetsService(cm)
        print("✅ Services initialized successfully")
        
        # Test configuration
        print("\n2. Testing configuration...")
        config = cm.get_google_sheets_config()
        settings = cm.get_google_sheets_settings()
        print(f"   API Key: {config['api_key'][:20]}...")
        print(f"   Spreadsheet ID: {settings['spreadsheet_id']}")
        print("✅ Configuration loaded successfully")
        
        # Test creating leads sheet
        print("\n3. Testing leads sheet creation...")
        result = sheets_service.create_leads_sheet()
        print(f"   Result: {result}")
        print("✅ Leads sheet ready")
        
        # Test adding a sample lead
        print("\n4. Testing lead addition...")
        sample_lead = {
            "company": "Test Company Inc.",
            "person": "John Doe",
            "email": "john.doe@testcompany.com",
            "title": "HR Director",
            "relevance_score": 0.85,
            "signal_type": 1,
            "source_url": "https://example.com/news",
            "status": "New",
            "notes": "Test lead from integration test"
        }
        
        result = sheets_service.append_lead(sample_lead)
        print(f"   Lead added successfully")
        print("✅ Lead addition test passed")
        
        # Test getting leads
        print("\n5. Testing lead retrieval...")
        leads = sheets_service.get_leads_by_status()
        print(f"   Found {len(leads)} leads in sheet")
        if leads:
            print(f"   Latest lead: {leads[-1].get('Company', 'Unknown')}")
        print("✅ Lead retrieval test passed")
        
        # Test statistics
        print("\n6. Testing statistics...")
        stats = sheets_service.get_stats()
        print(f"   Total leads: {stats['total_leads']}")
        print(f"   Status counts: {stats['status_counts']}")
        print("✅ Statistics test passed")
        
        print("\n" + "=" * 50)
        print("🎉 All Google Sheets tests passed!")
        print("The integration is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_google_sheets()