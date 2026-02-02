#!/usr/bin/env python3
"""Test email credentials"""
import smtplib
from dotenv import load_dotenv
import os

load_dotenv()

email = os.getenv("EMAIL_SENDER", "ariel@cliocircle.com")
password = os.getenv("EMAIL_PASSWORD")
recipient = os.getenv("EMAIL_RECIPIENT", "ariel@cliocircle.com")

if not password:
    print("❌ EMAIL_PASSWORD not set in .env")
    exit(1)

print(f"Testing email credentials...")
print(f"From: {email}")
print(f"To: {recipient}")

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(email, password)
    print("✅ Email credentials are VALID!")
    server.quit()
except smtplib.SMTPAuthenticationError as e:
    print(f"❌ Authentication failed: {e}")
    print("\n💡 Solution:")
    print("1. Go to https://myaccount.google.com/apppasswords")
    print("2. Generate a new App Password for 'Mail'")
    print("3. Update EMAIL_PASSWORD in .env file")
except Exception as e:
    print(f"❌ Error: {e}")
