import os
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import List


def _parse_recipients(raw_value: str) -> List[str]:
    recipients = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not recipients:
        raise ValueError("At least one recipient is required.")
    return recipients


def generate_email_object(
    html_report_path: str = "output/qa_status_report.html",
) -> EmailMessage:
    """
    Build an email object from a local HTML report.
    Sending is intentionally disabled in this phase.
    """
    report_path = Path(html_report_path)
    if not report_path.exists():
        raise FileNotFoundError(f"HTML report not found: {report_path}")

    send_email = os.getenv("SEND_EMAIL", "false").strip().lower() == "true"
    sender = os.getenv("SENDER_EMAIL", "qa-automation@local.example").strip()
    recipients = _parse_recipients(
        os.getenv("RECIPIENT_EMAILS", "qe-team@local.example").strip()
    )
    subject = os.getenv(
        "EMAIL_SUBJECT",
        f"QA Daily Status Report - {datetime.now().strftime('%Y-%m-%d')}",
    ).strip()
    html_body = report_path.read_text(encoding="utf-8")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(
        "This message contains an HTML QA status report. Please view the HTML part.",
        subtype="plain",
    )
    message.add_alternative(html_body, subtype="html")

    # SEND_EMAIL is intentionally not used for sending in this phase.
    # Even if set to true, we only generate the object.
    _ = send_email
    return message


if __name__ == "__main__":
    email_message = generate_email_object()
    html_parts = [
        part.get_content()
        for part in email_message.iter_parts()
        if part.get_content_type() == "text/html"
    ]
    html_body = html_parts[0] if html_parts else ""

    print("SEND_EMAIL=false (email sending is disabled)")
    print(f"Sender: {email_message['From']}")
    print(f"Recipients: {email_message['To']}")
    print(f"Subject: {email_message['Subject']}")
    print("HTML Body:")
    print(html_body)
