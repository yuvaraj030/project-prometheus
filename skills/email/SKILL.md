---
name: email
description: Send and read emails using SMTP and IMAP
tools:
  - send_email
  - read_emails
---

# Email Skill

You can send and read emails on behalf of the user.

## When to Use
- User asks to send an email
- User asks to check their inbox
- User wants to reply to or forward an email
- Heartbeat check: monitor for new important emails

## Tools Available

### send_email
Send an email via SMTP.
- **to** (string, required): Recipient email address
- **subject** (string, required): Email subject line
- **body** (string, required): Email body (plain text or HTML)
- **cc** (string, optional): CC recipients
- Returns: Confirmation with message ID

### read_emails
Read recent emails from the inbox via IMAP.
- **count** (integer, optional): Number of recent emails to fetch (default: 5)
- **folder** (string, optional): Mailbox folder (default: "INBOX")
- **unread_only** (boolean, optional): Only fetch unread emails (default: true)
- Returns: List of emails with sender, subject, date, and preview

## Configuration Required
Set these environment variables:
- `EMAIL_ADDRESS` — Your email address
- `EMAIL_PASSWORD` — App password (not your main password)
- `SMTP_HOST` — SMTP server (e.g., smtp.gmail.com)
- `IMAP_HOST` — IMAP server (e.g., imap.gmail.com)

## Instructions
1. Before sending, always confirm the recipient and content with the user
2. Keep email bodies professional unless the user specifies a tone
3. When reading emails, summarize them concisely
4. Flag urgent emails for the user's attention
