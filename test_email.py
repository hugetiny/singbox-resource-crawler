import smtplib
import sys
import os
import json
from email.mime.text import MIMEText

# Load config
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
except Exception as e:
    print(f"Error loading config: {e}")
    sys.exit(1)

email_config = config.get('logging', {}).get('email_config', {})

smtp_server = email_config.get('smtp_server')
smtp_port = email_config.get('smtp_port')
username = email_config.get('username')
password = email_config.get('password')
from_addr = email_config.get('from_addr')
to_addrs = email_config.get('to_addrs')

print(f"Testing email configuration...")
print(f"Server: {smtp_server}:{smtp_port}")
print(f"User: {username}")
print(f"To: {to_addrs}")

try:
    msg = MIMEText("This is a test email from your Singbox Crawler Service.")
    msg['Subject'] = "Crawler Email Test"
    msg['From'] = from_addr
    msg['To'] = ", ".join(to_addrs)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.set_debuglevel(1) # Show debug info
        server.starttls()
        print("Logging in...")
        server.login(username, password)
        print("Sending mail...")
        server.sendmail(from_addr, to_addrs, msg.as_string())
    
    print("\n✅ Email sent successfully! Your configuration is correct.")
except smtplib.SMTPAuthenticationError:
    print("\n❌ Authentication Failed.")
    print("This usually means you need an 'App Password' instead of your login password.")
    print("If you have 2FA enabled, your regular password will NOT work.")
except Exception as e:
    print(f"\n❌ Error: {e}")
