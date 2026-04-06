"""
Email & Calendar Agent — Gmail reading/sending + Google Calendar scheduling.
Uses existing OAuthEngine for token management.
Requires: google-auth google-auth-oauthlib google-api-python-client
"""

import os
import json
import base64
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from email.mime.text import MIMEText

logger = logging.getLogger("EmailCalendarAgent")

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.warning("google-api-python-client not installed. Run: pip install google-api-python-client")


class EmailCalendarAgent:
    """
    Autonomous Gmail + Google Calendar agent.
    Reads inbox, sends emails, schedules events, and triages autonomously.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar",
    ]

    def __init__(self, oauth_engine=None, llm_provider=None):
        self.oauth = oauth_engine
        self.llm = llm_provider
        self._gmail = None
        self._calendar = None
        self.triage_log: List[Dict] = []
        logger.info("📧 EmailCalendarAgent initialized.")

    def _get_credentials(self):
        """Get OAuth2 credentials from OAuthEngine or environment."""
        if self.oauth and hasattr(self.oauth, 'get_credentials'):
            return self.oauth.get_credentials(self.SCOPES)
        # Direct token file fallback
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        import google.auth.exceptions

        token_path = os.getenv("GOOGLE_TOKEN_PATH", "google_token.json")
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except google.auth.exceptions.RefreshError:
                creds = None
        return creds

    def _gmail_service(self):
        if self._gmail is None:
            if not GOOGLE_API_AVAILABLE:
                return None
            creds = self._get_credentials()
            if creds:
                self._gmail = build("gmail", "v1", credentials=creds)
        return self._gmail

    def _calendar_service(self):
        if self._calendar is None:
            if not GOOGLE_API_AVAILABLE:
                return None
            creds = self._get_credentials()
            if creds:
                self._calendar = build("calendar", "v3", credentials=creds)
        return self._calendar

    # ─────────────────────── GMAIL ───────────────────────

    def read_inbox(self, max_results: int = 10, unread_only: bool = True) -> List[Dict]:
        """Read recent emails from Gmail inbox."""
        svc = self._gmail_service()
        if not svc:
            return self._mock_inbox(max_results)

        try:
            query = "is:unread" if unread_only else ""
            results = svc.users().messages().list(
                userId="me", maxResults=max_results, q=query
            ).execute()

            messages = results.get("messages", [])
            emails = []
            for msg_ref in messages:
                msg = svc.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                ).execute()
                emails.append(self._parse_message(msg))
            return emails
        except HttpError as e:
            logger.error(f"Gmail read failed: {e}")
            return []

    def _parse_message(self, msg: Dict) -> Dict:
        """Parse a Gmail message object into a clean dict."""
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        body = ""
        payload = msg.get("payload", {})

        # Extract body text
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            body = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
        else:
            for part in payload.get("parts", []):
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    body = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
                    break

        return {
            "id": msg["id"],
            "thread_id": msg.get("threadId"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", "(no subject)"),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "body": body[:2000],
            "labels": msg.get("labelIds", []),
        }

    def _mock_inbox(self, max_results: int) -> List[Dict]:
        """Return mock emails when Google API is not configured."""
        return [
            {
                "id": f"mock_{i}",
                "from": f"sender{i}@example.com",
                "subject": f"[MOCK] Email subject #{i}",
                "date": datetime.now().isoformat(),
                "snippet": "This is a mock email for testing without Google API credentials.",
                "body": f"Hello! This is mock email #{i}. Configure GOOGLE_TOKEN_PATH to receive real emails.",
                "labels": ["INBOX", "UNREAD"],
            }
            for i in range(1, min(max_results + 1, 4))
        ]

    def send_email(self, to: str, subject: str, body: str, reply_to_id: str = None) -> Dict:
        """Send an email via Gmail."""
        svc = self._gmail_service()
        if not svc:
            logger.info(f"[MOCK EMAIL] To: {to} | Subject: {subject}")
            return {"status": "mock_sent", "to": to, "subject": subject}

        try:
            msg = MIMEText(body)
            msg["to"] = to
            msg["subject"] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

            body_data = {"raw": raw}
            if reply_to_id:
                body_data["threadId"] = reply_to_id

            result = svc.users().messages().send(userId="me", body=body_data).execute()
            logger.info(f"✉️ Email sent to {to} (id: {result['id']})")
            return {"status": "sent", "id": result["id"], "to": to, "subject": subject}
        except HttpError as e:
            logger.error(f"Email send failed: {e}")
            return {"status": "error", "error": str(e)}

    def mark_read(self, message_id: str) -> bool:
        """Mark an email as read."""
        svc = self._gmail_service()
        if not svc:
            return True
        try:
            svc.users().messages().modify(
                userId="me", id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            return True
        except HttpError:
            return False

    def archive_email(self, message_id: str) -> bool:
        """Archive an email (remove from inbox)."""
        svc = self._gmail_service()
        if not svc:
            return True
        try:
            svc.users().messages().modify(
                userId="me", id=message_id,
                body={"removeLabelIds": ["INBOX"]}
            ).execute()
            return True
        except HttpError:
            return False

    # ─────────────────────── CALENDAR ───────────────────────

    def list_events(self, days: int = 7) -> List[Dict]:
        """List upcoming Google Calendar events."""
        svc = self._calendar_service()
        if not svc:
            return self._mock_events(days)

        try:
            now = datetime.utcnow().isoformat() + "Z"
            end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
            result = svc.events().list(
                calendarId="primary",
                timeMin=now, timeMax=end,
                maxResults=20, singleEvents=True,
                orderBy="startTime"
            ).execute()
            events = result.get("items", [])
            return [
                {
                    "id": e["id"],
                    "title": e.get("summary", "(no title)"),
                    "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
                    "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
                    "description": e.get("description", ""),
                    "location": e.get("location", ""),
                }
                for e in events
            ]
        except HttpError as e:
            logger.error(f"Calendar list failed: {e}")
            return []

    def _mock_events(self, days: int) -> List[Dict]:
        now = datetime.now()
        return [
            {
                "id": "mock_event_1",
                "title": "[MOCK] Team Standup",
                "start": (now + timedelta(hours=2)).isoformat(),
                "end": (now + timedelta(hours=2, minutes=30)).isoformat(),
                "description": "Mock calendar event — configure Google OAuth to see real events.",
            }
        ]

    def create_event(self, title: str, start: str, end: str,
                     description: str = "", location: str = "") -> Dict:
        """Create a new Google Calendar event."""
        svc = self._calendar_service()
        if not svc:
            logger.info(f"[MOCK EVENT] '{title}' from {start} to {end}")
            return {"status": "mock_created", "title": title, "start": start}

        try:
            event = {
                "summary": title,
                "description": description,
                "location": location,
                "start": {"dateTime": start, "timeZone": "UTC"},
                "end": {"dateTime": end, "timeZone": "UTC"},
            }
            result = svc.events().insert(calendarId="primary", body=event).execute()
            logger.info(f"📅 Event created: '{title}' (id: {result['id']})")
            return {"status": "created", "id": result["id"], "title": title,
                    "link": result.get("htmlLink")}
        except HttpError as e:
            logger.error(f"Calendar event creation failed: {e}")
            return {"status": "error", "error": str(e)}

    # ─────────────────────── AUTONOMOUS TRIAGE ───────────────────────

    def autonomous_inbox_triage(self, max_emails: int = 5) -> List[Dict]:
        """
        Autonomous inbox management:
        1. Read unread emails
        2. Use LLM to classify: reply/archive/flag
        3. Draft and send replies for action-required emails
        4. Archive non-essential emails
        """
        if not self.llm:
            return [{"error": "No LLM provider — triage requires an LLM"}]

        emails = self.read_inbox(max_results=max_emails)
        results = []

        for email in emails:
            prompt = f"""You are an AI email assistant. Analyze this email and decide how to handle it.

From: {email['from']}
Subject: {email['subject']}
Body: {email['body'][:500]}

Respond with ONLY this JSON:
{{"action": "reply"|"archive"|"flag", "reason": "brief reason", "draft_reply": "reply text if action=reply, else null"}}"""

            try:
                response = self.llm.call(prompt, max_tokens=300)
                # Parse JSON
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                else:
                    decision = {"action": "flag", "reason": "Could not parse LLM response"}

                action = decision.get("action", "flag")
                result = {
                    "email_id": email["id"],
                    "from": email["from"],
                    "subject": email["subject"],
                    "action": action,
                    "reason": decision.get("reason", ""),
                }

                if action == "reply" and decision.get("draft_reply"):
                    sent = self.send_email(
                        to=email["from"],
                        subject=f"Re: {email['subject']}",
                        body=decision["draft_reply"],
                        reply_to_id=email.get("thread_id")
                    )
                    result["reply_status"] = sent.get("status")
                    self.mark_read(email["id"])
                elif action == "archive":
                    self.archive_email(email["id"])
                    self.mark_read(email["id"])
                # "flag" — leave in inbox, just mark read
                else:
                    self.mark_read(email["id"])

                results.append(result)
                self.triage_log.append({**result, "timestamp": datetime.now().isoformat()})
                logger.info(f"📧 Triaged '{email['subject']}' → {action}")

            except Exception as e:
                results.append({"email_id": email["id"], "error": str(e)})

        return results

    def get_status(self) -> Dict:
        """Return agent status."""
        return {
            "google_api_available": GOOGLE_API_AVAILABLE,
            "gmail_connected": self._gmail is not None,
            "calendar_connected": self._calendar is not None,
            "emails_triaged": len(self.triage_log),
            "recent_triage": self.triage_log[-3:],
        }
