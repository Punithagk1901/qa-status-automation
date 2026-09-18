import json
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path


def _env_get(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value
    return default


def _parse_recipients(raw_value: str) -> list[str]:
    recipients = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not recipients:
        raise ValueError("EMAIL_TO must include at least one recipient.")
    return recipients


def _resolve_html_report_path(html_report_path: str) -> Path:
    requested = Path(html_report_path)
    if requested.exists():
        return requested

    # If the requested "ga" file is absent, allow fallback to current "qa" output.
    fallback = Path("output/qa_status_report.html")
    if str(requested) == "output/ga_status_report.html" and fallback.exists():
        return fallback

    raise FileNotFoundError(f"HTML report not found: {requested}")


def _load_config_from_env() -> dict:
    email_from = _env_get("EMAIL_FROM").strip()
    if not email_from:
        raise ValueError("EMAIL_FROM is required.")

    email_to_raw = _env_get("EMAIL_TO").strip()
    email_to = _parse_recipients(email_to_raw)

    email_subject = _env_get(
        "EMAIL_SUBJECT",
        "EMAIL_ SUBJECT",
        "EMALL_SUBUECT",
        default="QA Daily Status Report",
    ).strip()
    if not email_subject:
        email_subject = "QA Daily Status Report"

    send_email = _env_get("SEND_EMAIL", default="false").strip().lower() == "true"

    smtp_host = _env_get("SMTP_HOST").strip()
    smtp_port_text = _env_get("SMTP_PORT").strip()
    smtp_username = _env_get("SMTP_USERNAME", "SMTP USERNAME").strip()
    smtp_password = _env_get("SMTP_PASSWORD", "SMTP PASSWORD").strip()

    smtp_port = 0
    if smtp_port_text:
        try:
            smtp_port = int(smtp_port_text)
        except ValueError as exc:
            raise ValueError("SMTP_PORT must be a valid integer.") from exc

    return {
        "email_from": email_from,
        "email_to": email_to,
        "email_subject": email_subject,
        "send_email": send_email,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_username": smtp_username,
        "smtp_password": smtp_password,
    }


def build_email_message(
    html_report_path: str = "output/ga_status_report.html",
) -> tuple[EmailMessage, dict]:
    config = _load_config_from_env()
    report_path = _resolve_html_report_path(html_report_path)

    html_body = report_path.read_text(encoding="utf-8")
    html_size_bytes = len(html_body.encode("utf-8"))

    message = EmailMessage()
    message["From"] = config["email_from"]
    message["To"] = ", ".join(config["email_to"])
    message["Subject"] = config["email_subject"]
    message.set_content(
        "QA Daily Status HTML report. Use an HTML-capable client for full formatting.",
        subtype="plain",
    )
    message.add_alternative(html_body, subtype="html")

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "send" if config["send_email"] else "dry_run",
        "sender": config["email_from"],
        "recipients": config["email_to"],
        "subject": config["email_subject"],
        "html_file_path": str(report_path.resolve()),
        "html_loaded_successfully": True,
        "html_size_bytes": html_size_bytes,
        "send_status": "not_attempted",
        "failure_reason": "",
    }
    return message, metadata


def _save_preview_metadata(preview_metadata: dict, preview_output_path: str) -> Path:
    preview_path = Path(preview_output_path)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(json.dumps(preview_metadata, indent=2), encoding="utf-8")
    return preview_path.resolve()


def _print_preview(preview_metadata: dict) -> None:
    print(f"Sender: {preview_metadata['sender']}")
    print(f"Recipient: {', '.join(preview_metadata['recipients'])}")
    print(f"Subject: {preview_metadata['subject']}")
    print(
        "HTML file loaded successfully: "
        f"{'Yes' if preview_metadata['html_loaded_successfully'] else 'No'}"
    )
    print(f"HTML size: {preview_metadata['html_size_bytes']} bytes")
    print(f"Send status: {preview_metadata['send_status']}")
    if preview_metadata["failure_reason"]:
        print(f"Failure reason: {preview_metadata['failure_reason']}")


def send_email(
    html_report_path: str = "output/ga_status_report.html",
    preview_output_path: str = "output/email_preview.json",
) -> tuple[EmailMessage, dict]:
    """
    Prepare and optionally send the QA dashboard email via SMTP.
    """
    config = _load_config_from_env()
    message, preview_metadata = build_email_message(html_report_path=html_report_path)

    if not config["send_email"]:
        preview_metadata["send_status"] = "dry_run_not_sent"
        preview_path = _save_preview_metadata(preview_metadata, preview_output_path)
        _print_preview(preview_metadata)
        print("DRY RUN mode: email not sent.")
        print(f"Preview metadata saved to: {preview_path}")
        return message, preview_metadata

    if not config["smtp_host"] or not config["smtp_port"]:
        preview_metadata["send_status"] = "failed"
        preview_metadata["failure_reason"] = "SMTP host/port missing."
        preview_path = _save_preview_metadata(preview_metadata, preview_output_path)
        _print_preview(preview_metadata)
        print(f"Preview metadata saved to: {preview_path}")
        raise ValueError("SMTP_HOST and SMTP_PORT are required when SEND_EMAIL=true.")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=20) as server:
            server.starttls(context=context)
            if config["smtp_username"] and config["smtp_password"]:
                server.login(config["smtp_username"], config["smtp_password"])
            server.send_message(message)

        preview_metadata["send_status"] = "success"
        preview_path = _save_preview_metadata(preview_metadata, preview_output_path)
        _print_preview(preview_metadata)
        print("Email sent successfully.")
        print(f"Preview metadata saved to: {preview_path}")
        return message, preview_metadata

    except smtplib.SMTPAuthenticationError as exc:
        preview_metadata["send_status"] = "failed"
        preview_metadata["failure_reason"] = f"Invalid SMTP credentials: {exc}"
        _save_preview_metadata(preview_metadata, preview_output_path)
        _print_preview(preview_metadata)
        raise
    except (
        smtplib.SMTPConnectError,
        smtplib.SMTPServerDisconnected,
        TimeoutError,
        OSError,
    ) as exc:
        preview_metadata["send_status"] = "failed"
        preview_metadata["failure_reason"] = f"SMTP connection failure: {exc}"
        _save_preview_metadata(preview_metadata, preview_output_path)
        _print_preview(preview_metadata)
        raise


if __name__ == "__main__":
    try:
        send_email()
    except Exception as exc:  # pragma: no cover - CLI behavior
        print(f"Email process failed: {exc}")
        raise
