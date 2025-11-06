"""
Email utilities for sending notifications
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

logger = logging.getLogger(__name__)

# Email configuration from environment variables
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")  # Production URL or localhost for dev
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USERNAME)
SENDER_NAME = os.getenv("SENDER_NAME", "The Trading Game")


def send_email(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """
    Send an email using SMTP
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML content of the email
        text_body: Plain text fallback (optional)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    # Skip if email not configured
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.info(f"Email not configured. Would have sent to {to_email}: {subject}")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg['To'] = to_email
        
        # Add text and HTML parts
        if text_body:
            part1 = MIMEText(text_body, 'plain')
            msg.attach(part1)
        
        part2 = MIMEText(html_body, 'html')
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


def send_registration_email(username: str, email: str) -> bool:
    """
    Send welcome email when a user registers
    
    Args:
        username: New user's username
        email: User's email address
    
    Returns:
        True if email sent successfully, False otherwise
    """
    subject = "Welcome to The Trading Game! 🎮"
    
    text_body = f"""
Hello {username},

Welcome to The Trading Game!

Your account has been successfully created. You can now:
- Create new game sessions and invite friends
- Join existing games using a game code
- Track your game history and statistics

Get started by logging in at: {APP_URL}

Happy trading!

The Trading Game Team
"""
    
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .features {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .feature-item {{
            padding: 10px 0;
        }}
        .feature-icon {{
            font-size: 20px;
            margin-right: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎮 Welcome to The Trading Game!</h1>
    </div>
    <div class="content">
        <h2>Hello {username},</h2>
        <p>Your account has been successfully created! We're excited to have you join our trading community.</p>
        
        <div class="features">
            <h3>What You Can Do:</h3>
            <div class="feature-item">
                <span class="feature-icon">🎲</span>
                <strong>Create Game Sessions</strong> - Host your own games and invite friends
            </div>
            <div class="feature-item">
                <span class="feature-icon">🚀</span>
                <strong>Join Existing Games</strong> - Use a game code to jump into the action
            </div>
            <div class="feature-item">
                <span class="feature-icon">📊</span>
                <strong>Track Your Progress</strong> - View your game history and statistics
            </div>
            <div class="feature-item">
                <span class="feature-icon">🏆</span>
                <strong>Compete & Collaborate</strong> - Trade with other nations and build your economy
            </div>
        </div>
        
        <center>
            <a href="{APP_URL}" class="button">Get Started</a>
        </center>
        
        <p style="margin-top: 30px; color: #666; font-size: 14px;">
            If you didn't create this account, please ignore this email.
        </p>
    </div>
</body>
</html>
"""
    
    return send_email(email, subject, html_body, text_body)
