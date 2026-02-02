#!/usr/bin/env python3
"""Test email sending now"""
import smtplib
import os
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

load_dotenv()

email = os.getenv("EMAIL_SENDER", "ariel@cliocircle.com")
password = os.getenv("EMAIL_PASSWORD")
recipient = os.getenv("EMAIL_RECIPIENT", "ariel@cliocircle.com")

if not password:
    print("❌ EMAIL_PASSWORD not set in .env")
    exit(1)

print(f"📧 Testing email sending...")
print(f"From: {email}")
print(f"To: {recipient}")

try:
    # Create message
    msg = MIMEMultipart("alternative")
    msg["From"] = email
    msg["To"] = recipient
    msg["Subject"] = f"Test Email - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # Create HTML body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin: 0;">✅ Email Test Successful!</h2>
            </div>
            <p>Hello Ariel,</p>
            <p>This is a test email sent at <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong>.</p>
            <p>The email system is working correctly! 🎉</p>
            <p>Your scheduler should now be able to send daily reports.</p>
        </div>
    </body>
    </html>
    """
    
    # Create plain text version
    plain_body = f"""
Hello Ariel,

This is a test email sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

The email system is working correctly!

Your scheduler should now be able to send daily reports.
"""
    
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    
    # Send email
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(email, password)
    server.sendmail(email, recipient, msg.as_string())
    server.quit()
    
    print("✅ Email sent successfully!")
    print(f"📬 Check your inbox at {recipient}")
    
except smtplib.SMTPAuthenticationError as e:
    print(f"❌ Authentication failed: {e}")
    print("\n💡 Solution:")
    print("1. Go to https://myaccount.google.com/apppasswords")
    print("2. Generate a new App Password for 'Mail'")
    print("3. Update EMAIL_PASSWORD in .env file")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()









