#!/usr/bin/env python3
"""
Google Sheets Service for HR Tech Lead Generation
Handles lead data storage and retrieval using Google Sheets API
"""

import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

import requests
from credentials_manager import CredentialsManager


class GoogleSheetsService:
    """Service for managing Google Sheets operations"""

    def __init__(self, credentials_manager: Optional[CredentialsManager] = None):
        self.credentials_manager = credentials_manager or CredentialsManager()
        self.logger = logging.getLogger(__name__)
        self.api_config = self.credentials_manager.get_google_sheets_config()
        self.settings = self.credentials_manager.get_google_sheets_settings()
        self.base_url = self.api_config["base_url"]
        self.api_key = self.api_config["api_key"]
        self.timeout = self.api_config["timeout"]
        self.max_retries = self.api_config["max_retries"]
        self.retry_delay = self.api_config["retry_delay"]

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to Google Sheets API with retry logic"""
        url = f"{self.base_url}/{endpoint}"
        params = kwargs.get("params", {})
        params["key"] = self.api_key

        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=kwargs.get("json"),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    self.logger.error(f"All retry attempts failed: {e}")
                    raise

    def get_spreadsheet_info(self) -> Dict[str, Any]:
        """Get information about the spreadsheet"""
        try:
            spreadsheet_id = self.settings["spreadsheet_id"]
            if not spreadsheet_id:
                raise ValueError("Spreadsheet ID not configured")

            endpoint = f"{spreadsheet_id}"
            return self._make_request("GET", endpoint)

        except Exception as e:
            self.logger.error(f"Failed to get spreadsheet info: {e}")
            raise

    def get_sheet_data(self, sheet_name: str, range_name: str = None) -> List[List[str]]:
        """Get data from a specific sheet"""
        try:
            spreadsheet_id = self.settings["spreadsheet_id"]
            if not spreadsheet_id:
                raise ValueError("Spreadsheet ID not configured")

            if range_name:
                range_param = f"{sheet_name}!{range_name}"
            else:
                range_param = sheet_name

            endpoint = f"{spreadsheet_id}/values/{range_param}"
            response = self._make_request("GET", endpoint)

            return response.get("values", [])

        except Exception as e:
            self.logger.error(f"Failed to get sheet data: {e}")
            raise

    def append_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Append a new lead to the leads sheet"""
        try:
            spreadsheet_id = self.settings["spreadsheet_id"]
            if not spreadsheet_id:
                raise ValueError("Spreadsheet ID not configured")

            # Prepare the row data
            row_data = self._format_lead_row(lead_data)

            # Append to the sheet
            endpoint = f"{spreadsheet_id}/values/{self.settings['leads_sheet_name']}:append"
            params = {
                "valueInputOption": "USER_ENTERED",
                "insertDataOption": "INSERT_ROWS",
            }

            body = {
                "values": [row_data]
            }

            response = self._make_request(
                "POST", 
                endpoint, 
                params=params, 
                json=body
            )

            self.logger.info(f"Successfully added lead for {lead_data.get('company', 'Unknown')}")
            return response

        except Exception as e:
            self.logger.error(f"Failed to append lead: {e}")
            raise

    def _format_lead_row(self, lead_data: Dict[str, Any]) -> List[str]:
        """Format lead data as a row for Google Sheets"""
        headers = self.settings["headers"]
        row = []

        for header in headers:
            if header == "Date":
                row.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            elif header == "Company":
                row.append(lead_data.get("company", ""))
            elif header == "Person":
                row.append(lead_data.get("person", ""))
            elif header == "Email":
                row.append(lead_data.get("email", ""))
            elif header == "Title":
                row.append(lead_data.get("title", ""))
            elif header == "Relevance Score":
                row.append(str(lead_data.get("relevance_score", 0)))
            elif header == "Signal Type":
                row.append(str(lead_data.get("signal_type", "")))
            elif header == "Source URL":
                row.append(lead_data.get("source_url", ""))
            elif header == "Status":
                row.append(lead_data.get("status", "New"))
            elif header == "Notes":
                row.append(lead_data.get("notes", ""))
            else:
                row.append("")

        return row

    def update_lead_status(self, row_index: int, status: str, notes: str = "") -> Dict[str, Any]:
        """Update the status of a lead by row index"""
        try:
            spreadsheet_id = self.settings["spreadsheet_id"]
            if not spreadsheet_id:
                raise ValueError("Spreadsheet ID not configured")

            # Update status and notes columns
            status_col = self.settings["headers"].index("Status") + 1  # Convert to 1-based
            notes_col = self.settings["headers"].index("Notes") + 1

            # Update status
            status_range = f"{self.settings['leads_sheet_name']}!{chr(64 + status_col)}{row_index}"
            endpoint = f"{spreadsheet_id}/values/{status_range}"
            body = {"values": [[status]]}
            self._make_request("PUT", endpoint, json=body)

            # Update notes if provided
            if notes:
                notes_range = f"{self.settings['leads_sheet_name']}!{chr(64 + notes_col)}{row_index}"
                endpoint = f"{spreadsheet_id}/values/{notes_range}"
                body = {"values": [[notes]]}
                self._make_request("PUT", endpoint, json=body)

            self.logger.info(f"Updated lead status at row {row_index} to {status}")
            return {"success": True}

        except Exception as e:
            self.logger.error(f"Failed to update lead status: {e}")
            raise

    def get_leads_by_status(self, status: str = None) -> List[Dict[str, Any]]:
        """Get leads filtered by status"""
        try:
            data = self.get_sheet_data(self.settings["leads_sheet_name"])
            if not data:
                return []

            headers = data[0] if data else self.settings["headers"]
            leads = []

            for i, row in enumerate(data[1:], start=2):  # Skip header row
                if len(row) < len(headers):
                    # Pad row with empty strings if needed
                    row.extend([""] * (len(headers) - len(row)))

                lead = dict(zip(headers, row))
                lead["row_index"] = i

                if status is None or lead.get("Status", "").lower() == status.lower():
                    leads.append(lead)

            return leads

        except Exception as e:
            self.logger.error(f"Failed to get leads by status: {e}")
            raise

    def create_leads_sheet(self) -> Dict[str, Any]:
        """Create the leads sheet with headers if it doesn't exist"""
        try:
            spreadsheet_id = self.settings["spreadsheet_id"]
            if not spreadsheet_id:
                raise ValueError("Spreadsheet ID not configured")

            # Check if sheet exists
            try:
                self.get_sheet_data(self.settings["leads_sheet_name"])
                self.logger.info("Leads sheet already exists")
                return {"success": True, "message": "Sheet already exists"}
            except:
                # Sheet doesn't exist, create it
                pass

            # Add the sheet
            endpoint = f"{spreadsheet_id}:batchUpdate"
            body = {
                "requests": [{
                    "addSheet": {
                        "properties": {
                            "title": self.settings["leads_sheet_name"]
                        }
                    }
                }]
            }

            response = self._make_request("POST", endpoint, json=body)

            # Add headers
            headers_range = f"{self.settings['leads_sheet_name']}!A1:{chr(64 + len(self.settings['headers']))}1"
            endpoint = f"{spreadsheet_id}/values/{headers_range}"
            body = {"values": [self.settings["headers"]]}
            self._make_request("PUT", endpoint, json=body)

            self.logger.info("Successfully created leads sheet with headers")
            return {"success": True, "message": "Sheet created successfully"}

        except Exception as e:
            self.logger.error(f"Failed to create leads sheet: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the leads"""
        try:
            leads = self.get_leads_by_status()
            total_leads = len(leads)

            # Count by status
            status_counts = {}
            for lead in leads:
                status = lead.get("Status", "Unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

            # Count by signal type
            signal_counts = {}
            for lead in leads:
                signal_type = lead.get("Signal Type", "Unknown")
                signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1

            return {
                "total_leads": total_leads,
                "status_counts": status_counts,
                "signal_type_counts": signal_counts,
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            raise