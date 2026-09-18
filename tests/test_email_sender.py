import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from email_sender import build_email_message, run_email_preparation


def test_html_file_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    html_file = tmp_path / "qa_status_report.html"
    html_file.write_text("<html><body>Sample</body></html>", encoding="utf-8")

    monkeypatch.setenv("EMAIL_FROM", "qa.bot@example.com")
    monkeypatch.setenv("EMAIL_TO", "team@example.com")
    monkeypatch.setenv("EMAIL_SUBJECT", "QA Daily Status Report")
    monkeypatch.setenv("SEND_EMAIL", "false")

    message, metadata = build_email_message(str(html_file))

    assert html_file.exists()
    assert metadata["html_loaded_successfully"] is True
    assert message["Subject"] == "QA Daily Status Report"


def test_email_object_builds_correctly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    html_file = tmp_path / "qa_status_report.html"
    html_content = "<html><body><h1>QA Report</h1></body></html>"
    html_file.write_text(html_content, encoding="utf-8")

    monkeypatch.setenv("EMAIL_FROM", "qa.bot@example.com")
    monkeypatch.setenv("EMAIL_TO", "lead@example.com, manager@example.com")
    monkeypatch.setenv("EMAIL_SUBJECT", "QA Daily Status Report")
    monkeypatch.setenv("SEND_EMAIL", "false")

    message, metadata = build_email_message(str(html_file))

    assert message["From"] == "qa.bot@example.com"
    assert message["To"] == "lead@example.com, manager@example.com"
    assert message["Subject"] == "QA Daily Status Report"
    html_parts = [
        part.get_content()
        for part in message.iter_parts()
        if part.get_content_type() == "text/html"
    ]
    assert len(html_parts) == 1
    assert "<h1>QA Report</h1>" in html_parts[0]
    assert metadata["html_size_bytes"] == len(html_content.encode("utf-8"))


def test_missing_html_file_handled_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_file = tmp_path / "missing_report.html"

    monkeypatch.setenv("EMAIL_FROM", "qa.bot@example.com")
    monkeypatch.setenv("EMAIL_TO", "team@example.com")
    monkeypatch.setenv("EMAIL_SUBJECT", "QA Daily Status Report")
    monkeypatch.setenv("SEND_EMAIL", "false")

    with pytest.raises(FileNotFoundError, match="HTML report not found"):
        build_email_message(str(missing_file))


def test_dry_run_mode_writes_preview_and_no_send(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    html_file = tmp_path / "qa_status_report.html"
    html_file.write_text("<html><body>Dry Run</body></html>", encoding="utf-8")
    preview_file = tmp_path / "email_preview.json"

    monkeypatch.setenv("EMAIL_FROM", "qa.bot@example.com")
    monkeypatch.setenv("EMAIL_TO", "team@example.com")
    monkeypatch.setenv("EMAIL_SUBJECT", "QA Daily Status Report")
    monkeypatch.setenv("SEND_EMAIL", "false")

    _, metadata = run_email_preparation(
        html_report_path=str(html_file),
        preview_output_path=str(preview_file),
    )
    output = capsys.readouterr().out

    assert "Recipient list: team@example.com" in output
    assert "Subject: QA Daily Status Report" in output
    assert "HTML file loaded successfully: Yes" in output
    assert "DRY RUN mode: email not sent." in output
    assert preview_file.exists()
    saved = json.loads(preview_file.read_text(encoding="utf-8"))
    assert saved["mode"] == "dry_run"
    assert saved["html_loaded_successfully"] is True
    assert saved["html_size_bytes"] > 0
    assert metadata["mode"] == "dry_run"
