#!/usr/bin/env python3
"""
Improved Gmail API Email System for HR Tech Lead Generation
Consolidates functionality from both gmail_email_system.py and gmail_email_system_secure.py
Creates personalized email drafts for each lead based on signal type
"""

import base64
import json
import logging
import os

# Add src to path for imports
import sys
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).parent / "src"))

from credentials_manager import CredentialsManager


class GmailEmailSystem:
    """Improved Gmail email system with template management and secure configuration"""

    def __init__(self, credentials_manager: Optional[CredentialsManager] = None):
        self.credentials_manager = credentials_manager or CredentialsManager()
        self.service = None
        self.templates = {}
        self.setup_logging()
        self.load_templates()

    def setup_logging(self):
        """Setup logging for email system"""
        logging.basicConfig(
            level=logging.INFO,
            filename="gmail_email_system.log",
            format="%(asctime)s - %(levelname)s - %(message)s",
            filemode="a",
        )

    def load_templates(self):
        """Load email templates from YAML configuration"""
        try:
            template_file = Path("config/email_templates.yaml")
            if template_file.exists():
                with open(template_file, "r") as f:
                    self.templates = yaml.safe_load(f)
                logging.info("Email templates loaded successfully")
            else:
                logging.warning("Email templates file not found, using defaults")
                self._load_default_templates()
        except Exception as e:
            logging.error(f"Error loading email templates: {e}")
            self._load_default_templates()

    def _load_default_templates(self):
        """Load default templates if YAML file is not available"""
        self.templates = {
            "templates": {
                "hr_tech_evaluations": {
                    "subject_template": "Streamlining Your HR Tech Evaluation Process - {company_name}",
                    "opening_template": "Hi {person_name},\n\nI noticed {company_name} is currently evaluating HR technology solutions.",
                    "body_template": "At Clio, we've helped over 200 companies streamline their HR operations.",
                    "closing_template": "Best regards,\nAriel\nCEO & Founder, Clio",
                }
            },
            "email_config": {
                "sender_name": "Ariel",
                "sender_title": "CEO & Founder",
                "company_name": "Clio",
            },
        }

    def get_gmail_service(self):
        """Authenticate and return Gmail API service."""
        try:
            gmail_config = self.credentials_manager.get_gmail_config()

            creds = None
            token_file = gmail_config["token_file"]
            credentials_file = gmail_config["credentials_file"]

            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(
                    token_file, gmail_config["scopes"]
                )

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, gmail_config["scopes"]
                    )
                    creds = flow.run_local_server(port=0)

                # Save the credentials for the next run
                with open(token_file, "w") as token:
                    token.write(creds.to_json())

            self.service = build("gmail", "v1", credentials=creds)
            logging.info("Gmail service initialized successfully")
            return self.service

        except Exception as e:
            logging.error(f"Failed to initialize Gmail service: {e}")
            raise

    def get_template_for_signal(self, signal_type: int) -> str:
        """Get template name for signal type"""
        signal_templates = {
            1: "hr_tech_evaluations",
            2: "new_leadership",
            3: "high_intent_content",
            4: "tech_stack_change",
            5: "expansion",
            6: "hiring_downsizing",
        }
        return signal_templates.get(signal_type, "hr_tech_evaluations")

    def load_email_template(self, template_name: str) -> Dict[str, str]:
        """Load email template by name"""
        if template_name not in self.templates["templates"]:
            logging.warning(f"Template {template_name} not found, using default")
            template_name = "hr_tech_evaluations"

        return self.templates["templates"][template_name]

    def personalize_template(
        self, template: Dict[str, str], variables: Dict[str, str]
    ) -> Dict[str, str]:
        """Personalize template with variables"""
        personalized = {}

        for key, template_str in template.items():
            try:
                personalized[key] = template_str.format(**variables)
            except KeyError as e:
                logging.warning(f"Missing variable {e} in template {key}")
                personalized[key] = template_str

        return personalized

    def is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False

        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def generate_email_content(self, opportunity: Dict[str, Any]) -> Dict[str, str]:
        """Generate personalized email content for an opportunity"""
        try:
            # Get template for signal type
            template_name = self.get_template_for_signal(
                opportunity.get("signal_type", 1)
            )
            template = self.load_email_template(template_name)

            # Prepare variables
            variables = {
                "person_name": opportunity.get("person", "there"),
                "company_name": opportunity.get("company", "your company"),
                "sender_name": self.templates["email_config"]["sender_name"],
                "sender_title": self.templates["email_config"]["sender_title"],
                "company": self.templates["email_config"]["company_name"],
            }

            # Add specific variables based on signal type
            if opportunity.get("signal_type") == 3:  # High-intent content
                variables[
                    "content_topic"
                ] = "HR technology"  # Could be extracted from content

            # Personalize template
            personalized = self.personalize_template(template, variables)

            # Combine into full email
            full_body = f"{personalized['opening_template']}\n\n{personalized['body_template']}\n\n{personalized['closing_template']}"

            return {
                "subject": personalized["subject_template"],
                "body": full_body,
                "to": opportunity.get("email", ""),
                "company": opportunity.get("company", ""),
                "person": opportunity.get("person", ""),
            }

        except Exception as e:
            logging.error(f"Error generating email content: {e}")
            return {
                "subject": f"HR Technology Solutions - {opportunity.get('company', 'Your Company')}",
                "body": f"Hi {opportunity.get('person', 'there')},\n\nI'd like to discuss how Clio can help {opportunity.get('company', 'your company')} with HR technology solutions.\n\nBest regards,\nAriel\nCEO & Founder, Clio",
                "to": opportunity.get("email", ""),
                "company": opportunity.get("company", ""),
                "person": opportunity.get("person", ""),
            }

    def create_draft(self, email_content: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Create Gmail draft"""
        try:
            if not self.service:
                self.get_gmail_service()

            # Validate email
            if not self.is_valid_email(email_content["to"]):
                logging.warning(f"Invalid email address: {email_content['to']}")
                return None

            # Create message
            message = MIMEText(email_content["body"])
            message["to"] = email_content["to"]
            message["subject"] = email_content["subject"]
            message["from"] = f"Ariel <ariel@cliocircle.com>"

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Create draft
            draft_body = {"message": {"raw": raw_message}}

            draft = (
                self.service.users()
                .drafts()
                .create(userId="me", body=draft_body)
                .execute()
            )

            logging.info(
                f"Created draft for {email_content['to']} at {email_content['company']}"
            )
            return {
                "id": draft["id"],
                "to": email_content["to"],
                "subject": email_content["subject"],
                "company": email_content["company"],
            }

        except Exception as e:
            logging.error(f"Error creating draft: {e}")
            return None

    def create_batch_drafts(
        self, opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Create multiple email drafts"""
        if not opportunities:
            return []

        logging.info(f"Creating {len(opportunities)} email drafts...")

        drafts_created = []
        for i, opportunity in enumerate(opportunities):
            try:
                # Generate email content
                email_content = self.generate_email_content(opportunity)

                # Create draft
                draft = self.create_draft(email_content)
                if draft:
                    drafts_created.append(draft)

                # Rate limiting
                if i < len(opportunities) - 1:
                    time.sleep(1)

            except Exception as e:
                logging.error(f"Error creating draft for opportunity {i}: {e}")
                continue

        logging.info(f"Created {len(drafts_created)} email drafts successfully")
        return drafts_created

    def validate_template(self, template: Dict[str, str]) -> bool:
        """Validate email template structure"""
        required_fields = [
            "subject_template",
            "opening_template",
            "body_template",
            "closing_template",
        ]
        return all(field in template for field in required_fields)

    def get_draft_summary(self, drafts: List[Dict[str, str]]) -> Dict[str, Any]:
        """Get summary of created drafts"""
        if not drafts:
            return {"total_drafts": 0, "companies": [], "errors": 0}

        companies = [draft["company"] for draft in drafts if draft.get("company")]

        return {
            "total_drafts": len(drafts),
            "companies": list(set(companies)),
            "unique_companies": len(set(companies)),
            "errors": 0,
        }

    def save_draft_summary(
        self, drafts: List[Dict[str, str]], filename: str = "email_drafts_summary.json"
    ):
        """Save draft creation summary to file"""
        try:
            summary = self.get_draft_summary(drafts)
            summary["timestamp"] = datetime.now().isoformat()
            summary["drafts"] = drafts

            with open(filename, "w") as f:
                json.dump(summary, f, indent=2)

            logging.info(f"Draft summary saved to {filename}")

        except Exception as e:
            logging.error(f"Error saving draft summary: {e}")


def main():
    """Test the Gmail email system"""
    try:
        # Initialize credentials manager
        credentials_manager = CredentialsManager()

        # Initialize email system
        email_system = GmailEmailSystem(credentials_manager)

        # Test with sample opportunity
        test_opportunity = {
            "company": "Test Company",
            "person": "John Doe",
            "email": "john.doe@testcompany.com",
            "signal_type": 1,
        }

        # Generate email content
        email_content = email_system.generate_email_content(test_opportunity)
        print("Generated email content:")
        print(f"Subject: {email_content['subject']}")
        print(f"To: {email_content['to']}")
        print(f"Body:\n{email_content['body']}")

        # Test draft creation (uncomment to actually create draft)
        # draft = email_system.create_draft(email_content)
        # if draft:
        #     print(f"Draft created with ID: {draft['id']}")

    except Exception as e:
        logging.error(f"Test failed: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
