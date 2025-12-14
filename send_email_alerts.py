"""
send_email_alerts.py - Local Email Alerts (No SNS Required)
Send threat alerts via SMTP (Gmail, Outlook, etc.)
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv


class LocalEmailAlerter:
    """Send email alerts using local SMTP (Gmail, Outlook, etc.)"""
    
    def __init__(self):
        """Initialize email configuration from .env"""
        load_dotenv()
        
        # Email settings
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.alert_email = os.getenv('ALERT_EMAIL', self.sender_email)
        
        # Validate configuration
        if not self.sender_email or not self.sender_password:
            print("⚠️  Email alerts not configured")
            print("   Add to .env file:")
            print("   SENDER_EMAIL=your.email@gmail.com")
            print("   SENDER_PASSWORD=your_app_password")
            print("   ALERT_EMAIL=recipient@example.com")
            self.enabled = False
        else:
            self.enabled = True
    
    def send_threat_alert(self, 
                         threats: List[Dict[str, Any]],
                         camera_id: str,
                         video_datetime: datetime,
                         results_dir: Path) -> bool:
        """
        Send email alert for detected threats
        
        Args:
            threats: List of threat dictionaries
            camera_id: Camera identifier
            video_datetime: When video was recorded
            results_dir: Directory with results
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            print("❌ Email alerts not configured, skipping")
            return False
        
        # Filter HIGH/MEDIUM threats
        high_threats = [t for t in threats if t['threat_level'] == 'HIGH']
        medium_threats = [t for t in threats if t['threat_level'] == 'MEDIUM']
        
        if not high_threats and not medium_threats:
            print("ℹ️  No HIGH/MEDIUM threats to alert on")
            return False
        
        # Create email
        subject = f"⚠️ CCTV Alert: {len(high_threats)} HIGH, {len(medium_threats)} MEDIUM threats"
        body = self._create_email_body(
            high_threats, medium_threats, camera_id, video_datetime, results_dir
        )
        
        # Send email
        try:
            return self._send_email(subject, body)
        except Exception as e:
            print(f"❌ Failed to send email alert: {e}")
            return False
    
    def _create_email_body(self, 
                          high_threats: List[Dict],
                          medium_threats: List[Dict],
                          camera_id: str,
                          video_datetime: datetime,
                          results_dir: Path) -> str:
        """Create HTML email body"""
        
        lines = [
            "<html><body style='font-family: Arial, sans-serif;'>",
            "<div style='background: #f44336; color: white; padding: 20px;'>",
            "<h1 style='margin: 0;'>🚨 CCTV THREAT ALERT</h1>",
            "</div>",
            "<div style='padding: 20px;'>",
            
            f"<p><strong>Camera:</strong> {camera_id}</p>",
            f"<p><strong>Date/Time:</strong> {video_datetime.strftime('%Y-%m-%d %I:%M %p')}</p>",
            
            "<hr>",
            
            f"<h2 style='color: #f44336;'>⚠️ {len(high_threats)} HIGH Priority Threats</h2>",
            f"<h3 style='color: #ff9800;'>⚠️ {len(medium_threats)} MEDIUM Priority Threats</h3>",
        ]
        
        # HIGH threats detail
        if high_threats:
            lines.append("<div style='background: #ffebee; padding: 15px; margin: 10px 0; border-left: 4px solid #f44336;'>")
            lines.append("<h3 style='margin-top: 0; color: #f44336;'>HIGH PRIORITY THREATS</h3>")
            lines.append("<ul>")
            
            for threat in high_threats[:10]:  # Limit to 10
                time_str = threat.get('time_str', 'Unknown time')
                obj = threat.get('detected_class', 'Unknown')
                conf = threat.get('confidence', 0)
                
                lines.append(
                    f"<li><strong>{obj.upper()}</strong> detected at {time_str} "
                    f"(confidence: {conf:.0%})</li>"
                )
            
            if len(high_threats) > 10:
                lines.append(f"<li><em>... and {len(high_threats) - 10} more</em></li>")
            
            lines.append("</ul>")
            lines.append("</div>")
        
        # MEDIUM threats summary
        if medium_threats:
            lines.append("<div style='background: #fff3e0; padding: 15px; margin: 10px 0; border-left: 4px solid #ff9800;'>")
            lines.append("<h3 style='margin-top: 0; color: #ff9800;'>MEDIUM PRIORITY THREATS</h3>")
            
            # Group by class
            medium_by_class = {}
            for threat in medium_threats:
                obj = threat.get('detected_class', 'Unknown')
                if obj not in medium_by_class:
                    medium_by_class[obj] = []
                medium_by_class[obj].append(threat)
            
            lines.append("<ul>")
            for obj, threats_list in medium_by_class.items():
                lines.append(f"<li><strong>{len(threats_list)} {obj}(s)</strong> detected</li>")
            lines.append("</ul>")
            lines.append("</div>")
        
        # Results location
        lines.append("<hr>")
        lines.append("<h3>📁 Results Location</h3>")
        lines.append(f"<p><code>{results_dir.absolute()}</code></p>")
        lines.append("<p>Files generated:</p>")
        lines.append("<ul>")
        lines.append("<li>threat_report.json - Detailed threat analysis</li>")
        lines.append("<li>detection_report.json - All detections</li>")
        lines.append("<li>summary.json - Processing summary</li>")
        lines.append("<li>flagged_clips/ - Video clips of threats</li>")
        lines.append("<li>detections/ - Annotated frames</li>")
        lines.append("</ul>")
        
        # Footer
        lines.append("<hr>")
        lines.append("<p style='color: #666; font-size: 12px;'>")
        lines.append("This alert was generated by your CCTV Threat Detection System<br>")
        lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}")
        lines.append("</p>")
        
        lines.append("</div></body></html>")
        
        return "\n".join(lines)
    
    def _send_email(self, subject: str, body_html: str) -> bool:
        """Send email via SMTP"""
        
        print(f"📧 Sending email alert to {self.alert_email}...")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = self.alert_email
        
        # Add HTML body
        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)
        
        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            print(f"✅ Email alert sent successfully!")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("❌ Email authentication failed")
            print("   For Gmail: Use an App Password, not your regular password")
            print("   See: https://support.google.com/accounts/answer/185833")
            return False
        
        except Exception as e:
            print(f"❌ Email send failed: {e}")
            return False
    
    def send_test_alert(self) -> bool:
        """Send a test alert to verify email configuration"""
        
        if not self.enabled:
            print("❌ Email not configured")
            return False
        
        subject = "🧪 Test: CCTV Alert System"
        
        body = """
        <html><body style='font-family: Arial, sans-serif;'>
        <div style='background: #4CAF50; color: white; padding: 20px;'>
        <h1 style='margin: 0;'>🧪 Email Alert Test</h1>
        </div>
        <div style='padding: 20px;'>
        
        <h2>Test Successful!</h2>
        
        <p>If you received this email, your CCTV alert system email configuration is working correctly.</p>
        
        <h3>Configuration:</h3>
        <ul>
        <li><strong>SMTP Server:</strong> {}</li>
        <li><strong>Port:</strong> {}</li>
        <li><strong>Sender:</strong> {}</li>
        <li><strong>Recipient:</strong> {}</li>
        </ul>
        
        <p style='background: #e3f2fd; padding: 10px; border-left: 4px solid #2196F3;'>
        <strong>Next Steps:</strong><br>
        Run your CCTV analysis pipeline, and you'll receive alerts when HIGH or MEDIUM threats are detected.
        </p>
        
        <hr>
        <p style='color: #666; font-size: 12px;'>
        Test sent at: {}<br>
        CCTV Threat Detection System
        </p>
        
        </div></body></html>
        """.format(
            self.smtp_server,
            self.smtp_port,
            self.sender_email,
            self.alert_email,
            datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        )
        
        return self._send_email(subject, body)


def main():
    """Test email alerting"""
    
    print("="*60)
    print("Email Alert System Test")
    print("="*60)
    print()
    
    alerter = LocalEmailAlerter()
    
    if not alerter.enabled:
        print("\n" + "="*60)
        print("❌ Email Not Configured")
        print("="*60)
        print()
        print("Add these to your .env file:")
        print()
        print("# Gmail configuration (RECOMMENDED)")
        print("SMTP_SERVER=smtp.gmail.com")
        print("SMTP_PORT=587")
        print("SENDER_EMAIL=your.email@gmail.com")
        print("SENDER_PASSWORD=your_app_password  # NOT your regular password!")
        print("ALERT_EMAIL=recipient@example.com  # Can be same as sender")
        print()
        print("# OR Outlook configuration")
        print("# SMTP_SERVER=smtp-mail.outlook.com")
        print("# SMTP_PORT=587")
        print("# SENDER_EMAIL=your.email@outlook.com")
        print("# SENDER_PASSWORD=your_password")
        print("# ALERT_EMAIL=recipient@example.com")
        print()
        print("="*60)
        print("📖 Setup Guide:")
        print("="*60)
        print()
        print("For Gmail (RECOMMENDED):")
        print("  1. Go to: https://myaccount.google.com/apppasswords")
        print("  2. Create an 'App Password' for 'Mail'")
        print("  3. Use that 16-character password in .env")
        print()
        print("For Outlook:")
        print("  1. Use your regular Outlook password")
        print("  2. May need to enable 'Less secure app access'")
        print()
        return
    
    print(f"Configuration:")
    print(f"  SMTP Server: {alerter.smtp_server}:{alerter.smtp_port}")
    print(f"  Sender: {alerter.sender_email}")
    print(f"  Recipient: {alerter.alert_email}")
    print()
    
    print("Sending test email...")
    success = alerter.send_test_alert()
    
    if success:
        print()
        print("="*60)
        print("✅ Test Email Sent Successfully!")
        print("="*60)
        print()
        print("Check your inbox (and spam folder) for the test email")
        print()
        print("Your email alerts are now configured! ✨")
        print()
    else:
        print()
        print("="*60)
        print("❌ Test Email Failed")
        print("="*60)
        print()
        print("Common issues:")
        print("  - Using regular password instead of App Password (Gmail)")
        print("  - Incorrect email/password")
        print("  - Firewall blocking SMTP")
        print("  - Less secure apps not enabled (Outlook)")
        print()


if __name__ == '__main__':
    main()