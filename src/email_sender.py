import json
import os
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path


def _parse_recipients(raw_value: str) -> list[str]:
    recipients = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not recipients:
        raise ValueError("EMAIL_TO must include at least one recipient.")
    return recipients


def _load_config_from_env() -> dict:
    email_from = os.getenv("EMAIL_FROM", "").strip()
    if not email_from:
        raise ValueError("EMAIL_FROM is required.")

    email_to_raw = os.getenv("EMAIL_TO", "").strip()
    email_to = _parse_recipients(email_to_raw)

    # EMAIL_SUBJECT is the primary variable. The typo fallback exists for resilience.
    email_subject = os.getenv(
        "EMAIL_SUBJECT",
        os.getenv("EMALL_SUBUECT", "QA Daily Status Report"),
    ).strip()
    if not email_subject:
        email_subject = "QA Daily Status Report"

    send_email = os.getenv("SEND_EMAIL", "false").strip().lower() == "true"

    return {
        "email_from": email_from,
        "email_to": email_to,
        "email_subject": email_subject,
        "send_email": send_email,
    }


def build_email_message(
    html_report_path: str = "output/qa_status_report.html",
) -> tuple[EmailMessage, dict]:
    """
    Build an email object and dry-run metadata from the generated HTML report.
    """
    config = _load_config_from_env()

    report_path = Path(html_report_path)
    if not report_path.exists():
        raise FileNotFoundError(f"HTML report not found: {report_path}")

    html_body = report_path.read_text(encoding="utf-8")
    html_size_bytes = len(html_body.encode("utf-8"))

    message = EmailMessage()
    message["From"] = config["email_from"]
    message["To"] = ", ".join(config["email_to"])
    message["Subject"] = config["email_subject"]
    message.set_content(
        "This is a dry-run QA status email preview. HTML body is attached as alternative.",
        subtype="plain",
    )
    message.add_alternative(html_body, subtype="html")

    preview_metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "send" if config["send_email"] else "dry_run",
        "sender": config["email_from"],
        "recipients": config["email_to"],
        "subject": config["email_subject"],
        "html_file_path": str(report_path.resolve()),
        "html_loaded_successfully": True,
        "html_size_bytes": html_size_bytes,
    }
    return message, preview_metadata


def run_email_preparation(
    html_report_path: str = "output/qa_status_report.html",
    preview_output_path: str = "output/email_preview.json",
) -> tuple[EmailMessage, dict]:
    """
    Prepare email payload and dry-run metadata. Does not send email.
    """
    message, preview_metadata = build_email_message(html_report_path=html_report_path)

    preview_path = Path(preview_output_path)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(json.dumps(preview_metadata, indent=2), encoding="utf-8")

    print(f"Sender: {preview_metadata['sender']}")
    print(f"Recipient list: {', '.join(preview_metadata['recipients'])}")
    print(f"Subject: {preview_metadata['subject']}")
    print(
        f"HTML file loaded successfully: "
        f"{'Yes' if preview_metadata['html_loaded_successfully'] else 'No'}"
    )
    print(f"HTML size: {preview_metadata['html_size_bytes']} bytes")

    if preview_metadata["mode"] == "send":
        print("Email sending would occur here.")
    else:
        print("DRY RUN mode: email not sent.")

    print(f"Preview metadata saved to: {preview_path.resolve()}")
    return message, preview_metadata


if __name__ == "__main__":
    run_email_preparation()
