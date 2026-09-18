import json
from pathlib import Path
import smtplib
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from email_sender import build_email_message, send_email


def _set_common_env(monkeypatch: pytest.MonkeyPatch, send_email_flag: str = "false") -> None:
    monkeypatch.setenv("EMAIL_FROM", "qa.bot@example.com")
    monkeypatch.setenv("EMAIL_TO", "team@example.com")
    monkeypatch.setenv("EMAIL_SUBJECT", "QA Daily Status Report")
    monkeypatch.setenv("SEND_EMAIL", send_email_flag)


def test_html_file_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    html_file = tmp_path / "ga_status_report.html"
    html_file.write_text("<html><body>Sample</body></html>", encoding="utf-8")
    _set_common_env(monkeypatch)

    message, metadata = build_email_message(str(html_file))

    assert html_file.exists()
    assert metadata["html_loaded_successfully"] is True
    assert message["Subject"] == "QA Daily Status Report"


def test_email_object_builds_correctly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    html_file = tmp_path / "ga_status_report.html"
    html_content = "<html><body><h1>QA Report</h1></body></html>"
    html_file.write_text(html_content, encoding="utf-8")
    _set_common_env(monkeypatch)

    message, metadata = build_email_message(str(html_file))
    html_parts = [
        part.get_content()
        for part in message.iter_parts()
        if part.get_content_type() == "text/html"
    ]

    assert message["From"] == "qa.bot@example.com"
    assert message["To"] == "team@example.com"
    assert message["Subject"] == "QA Daily Status Report"
    assert len(html_parts) == 1
    assert "<h1>QA Report</h1>" in html_parts[0]
    assert metadata["html_size_bytes"] == len(html_content.encode("utf-8"))


def test_missing_html_file_handled_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_file = tmp_path / "missing_report.html"
    _set_common_env(monkeypatch)

    with pytest.raises(FileNotFoundError, match="HTML report not found"):
        build_email_message(str(missing_file))


def test_dry_run_mode_writes_preview_and_no_send(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    html_file = tmp_path / "ga_status_report.html"
    html_file.write_text("<html><body>Dry Run</body></html>", encoding="utf-8")
    preview_file = tmp_path / "email_preview.json"
    _set_common_env(monkeypatch, send_email_flag="false")

    _, metadata = send_email(
        html_report_path=str(html_file),
        preview_output_path=str(preview_file),
    )
    output = capsys.readouterr().out
    saved = json.loads(preview_file.read_text(encoding="utf-8"))

    assert "Recipient: team@example.com" in output
    assert "Subject: QA Daily Status Report" in output
    assert "HTML file loaded successfully: Yes" in output
    assert "Send status: dry_run_not_sent" in output
    assert "DRY RUN mode: email not sent." in output
    assert preview_file.exists()
    assert saved["mode"] == "dry_run"
    assert saved["html_loaded_successfully"] is True
    assert saved["send_status"] == "dry_run_not_sent"
    assert metadata["mode"] == "dry_run"


def test_send_mode_handles_invalid_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    html_file = tmp_path / "ga_status_report.html"
    html_file.write_text("<html><body>SMTP Test</body></html>", encoding="utf-8")
    preview_file = tmp_path / "email_preview.json"
    _set_common_env(monkeypatch, send_email_flag="true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "bad-user")
    monkeypatch.setenv("SMTP_PASSWORD", "bad-pass")

    class DummySMTPAuthFailure:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self, context=None) -> None:
            _ = context

        def login(self, _user, _password) -> None:
            raise smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    monkeypatch.setattr(smtplib, "SMTP", DummySMTPAuthFailure)

    with pytest.raises(smtplib.SMTPAuthenticationError):
        send_email(str(html_file), str(preview_file))

    saved = json.loads(preview_file.read_text(encoding="utf-8"))
    assert saved["send_status"] == "failed"
    assert "Invalid SMTP credentials" in saved["failure_reason"]


def test_send_mode_handles_connection_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    html_file = tmp_path / "ga_status_report.html"
    html_file.write_text("<html><body>SMTP Test</body></html>", encoding="utf-8")
    preview_file = tmp_path / "email_preview.json"
    _set_common_env(monkeypatch, send_email_flag="true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")

    class DummySMTPConnectionFailure:
        def __init__(self, *_args, **_kwargs) -> None:
            raise smtplib.SMTPConnectError(421, "Connection refused")

    monkeypatch.setattr(smtplib, "SMTP", DummySMTPConnectionFailure)

    with pytest.raises(smtplib.SMTPConnectError):
        send_email(str(html_file), str(preview_file))

    saved = json.loads(preview_file.read_text(encoding="utf-8"))
    assert saved["send_status"] == "failed"
    assert "SMTP connection failure" in saved["failure_reason"]
