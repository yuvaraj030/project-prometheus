"""
Email Campaign Bot — Writes + sends cold outreach sequences via SMTP.
Creates multi-step email sequences, manages recipients, tracks status.
"""
import os
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("EmailCampaign")


class EmailCampaign:
    """
    Autonomous email marketing bot.
    Writes AI-generated email sequences and sends via SMTP.
    """

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.campaigns: Dict[str, Dict] = {}
        self._state_path = "email_campaigns.json"
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(self._state_path):
                with open(self._state_path) as f:
                    self.campaigns = json.load(f)
        except Exception:
            self.campaigns = {}

    def _save_state(self):
        try:
            with open(self._state_path, "w") as f:
                json.dump(self.campaigns, f, indent=2)
        except Exception as e:
            logger.error(f"Save error: {e}")

    def create_campaign(self, name: str, audience: str, goal: str,
                        num_emails: int = 3) -> Dict[str, Any]:
        """
        AI writes a multi-step email sequence for a campaign.
        Returns campaign dict with generated emails.
        """
        cid = f"camp_{len(self.campaigns)+1:03d}"
        emails = []

        if self.llm:
            try:
                for step in range(1, num_emails + 1):
                    step_desc = {
                        1: "introduction email (introduce yourself/product, build curiosity)",
                        2: "follow-up email (highlight value, add social proof)",
                        3: "final call-to-action email (create urgency, clear CTA)"
                    }.get(step, f"email #{step}")

                    prompt = (
                        f"Write a professional cold outreach {step_desc}.\n\n"
                        f"Campaign: {name}\nTarget Audience: {audience}\nGoal: {goal}\n\n"
                        f"Format:\nSUBJECT: <subject line>\n\nBODY:\n<email body>\n\n"
                        f"Keep it under 150 words. Be personal, not spammy. End with a clear CTA."
                    )
                    response = self.llm.call(prompt, max_tokens=300)

                    # Parse subject and body
                    subject = f"{name} - Follow Up {step}"
                    body = response
                    if "SUBJECT:" in response:
                        parts = response.split("BODY:", 1)
                        subject = parts[0].replace("SUBJECT:", "").strip()
                        body = parts[1].strip() if len(parts) > 1 else response

                    emails.append({
                        "step": step,
                        "subject": subject,
                        "body": body,
                        "status": "draft"
                    })
            except Exception as e:
                logger.error(f"LLM error: {e}")
        else:
            # Fallback mock emails
            for step in range(1, num_emails + 1):
                emails.append({
                    "step": step,
                    "subject": f"[{name}] Quick question — Step {step}",
                    "body": (
                        f"Hi there,\n\nI wanted to reach out regarding {goal}.\n\n"
                        f"As someone in {audience}, I think this could really help you.\n\n"
                        f"Would love to chat for 15 minutes this week?\n\nBest,\nThe Agent"
                    ),
                    "status": "draft"
                })

        campaign = {
            "id": cid,
            "name": name,
            "audience": audience,
            "goal": goal,
            "emails": emails,
            "recipients": [],
            "sent_log": [],
            "created_at": datetime.now().isoformat(),
            "status": "draft"
        }
        self.campaigns[cid] = campaign
        self._save_state()
        logger.info(f"📧 Campaign '{name}' created with {len(emails)} emails")
        return campaign

    def add_recipients(self, campaign_id: str, emails: List[str]) -> str:
        """Add recipient email addresses to a campaign."""
        if campaign_id not in self.campaigns:
            return f"❌ Campaign '{campaign_id}' not found"
        valid = [e for e in emails if "@" in e]
        self.campaigns[campaign_id]["recipients"].extend(valid)
        self._save_state()
        return f"✅ Added {len(valid)} recipients to '{self.campaigns[campaign_id]['name']}'"

    def send_sequence(self, campaign_id: str, smtp_config: Optional[Dict] = None,
                      dry_run: bool = True) -> Dict[str, Any]:
        """
        Send the email sequence to all recipients.
        dry_run=True (default) simulates sending without actual SMTP.
        Set SMTP_HOST, SMTP_USER, SMTP_PASS env vars for real sending.
        """
        if campaign_id not in self.campaigns:
            return {"error": f"Campaign '{campaign_id}' not found"}

        camp = self.campaigns[campaign_id]
        recipients = camp.get("recipients", [])
        emails_seq = camp.get("emails", [])

        if not recipients:
            return {"status": "error", "message": "No recipients added. Use /emailcampaign recipients first."}

        # Get SMTP config
        smtp_host = os.getenv("SMTP_HOST", smtp_config.get("host") if smtp_config else "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", smtp_config.get("user") if smtp_config else "")
        smtp_pass = os.getenv("SMTP_PASS", smtp_config.get("password") if smtp_config else "")

        sent_count = 0
        errors = []

        # Send first email in sequence (step 1) to all recipients
        first_email = emails_seq[0] if emails_seq else None
        if not first_email:
            return {"status": "error", "message": "No emails in sequence"}

        for recipient in recipients:
            log_entry = {
                "recipient": recipient,
                "subject": first_email["subject"],
                "step": 1,
                "timestamp": datetime.now().isoformat()
            }

            if dry_run or not (smtp_user and smtp_pass):
                log_entry["status"] = "simulated"
                logger.info(f"✉️ [DRY RUN] To: {recipient} | Subject: {first_email['subject']}")
            else:
                try:
                    msg = MIMEMultipart()
                    msg["From"] = smtp_user
                    msg["To"] = recipient
                    msg["Subject"] = first_email["subject"]
                    msg.attach(MIMEText(first_email["body"], "plain"))

                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_pass)
                        server.sendmail(smtp_user, recipient, msg.as_string())

                    log_entry["status"] = "sent"
                    logger.info(f"✅ Sent to {recipient}")
                except Exception as e:
                    log_entry["status"] = "failed"
                    log_entry["error"] = str(e)
                    errors.append(f"{recipient}: {e}")
                    logger.error(f"Failed to send to {recipient}: {e}")

            camp["sent_log"].append(log_entry)
            sent_count += 1

        camp["status"] = "active"
        self._save_state()

        return {
            "campaign": camp["name"],
            "recipients": len(recipients),
            "sent": sent_count,
            "errors": len(errors),
            "mode": "dry_run (no SMTP config)" if dry_run or not smtp_user else "live",
            "first_email_subject": first_email["subject"]
        }

    def get_stats(self) -> Dict:
        stats = {"total_campaigns": len(self.campaigns), "campaigns": []}
        for cid, c in self.campaigns.items():
            sent = [l for l in c.get("sent_log", []) if l.get("status") in ("sent", "simulated")]
            stats["campaigns"].append({
                "id": cid,
                "name": c["name"],
                "emails": len(c.get("emails", [])),
                "recipients": len(c.get("recipients", [])),
                "sent": len(sent),
                "status": c.get("status", "draft")
            })
        return stats

    def list_campaigns(self) -> List[Dict]:
        return [
            {
                "id": cid,
                "name": c["name"],
                "goal": c["goal"],
                "emails": len(c.get("emails", [])),
                "recipients": len(c.get("recipients", [])),
                "status": c.get("status", "draft"),
                "created_at": c.get("created_at", "")
            }
            for cid, c in self.campaigns.items()
        ]

    def preview_campaign(self, campaign_id: str) -> str:
        """Preview the emails in a campaign."""
        if campaign_id not in self.campaigns:
            return f"❌ Campaign '{campaign_id}' not found"
        camp = self.campaigns[campaign_id]
        lines = [f"📧 Campaign: {camp['name']}\n  Goal: {camp['goal']}\n  Audience: {camp['audience']}\n"]
        for em in camp.get("emails", []):
            lines.append(f"  --- Step {em['step']} ---")
            lines.append(f"  Subject: {em['subject']}")
            lines.append(f"  Body:\n    {em['body'][:200]}...\n")
        return "\n".join(lines)
