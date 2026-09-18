from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from excel_reader import REQUIRED_COLUMNS, load_excel, validate_excel


def _write_excel(dataframe: pd.DataFrame, file_path: Path, sheet_name: str) -> None:
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name)


def _valid_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Date": "2026-09-17",
                "Platform": "Web",
                "Task": "Login regression smoke",
                "Status": "In Progress",
                "Total": 40,
                "Passed": 28,
                "Failed": 3,
                "Blocked": 2,
                "Not Executed": 7,
                "Owner": "Sample Owner A",
                "Remarks": "Sample row",
                "Release": "R2026.09.1",
                "UAT Date": "2026-09-20",
                "PROD Date": "2026-09-27",
            }
        ]
    )


def test_load_excel_raises_when_file_does_not_exist() -> None:
    with pytest.raises(FileNotFoundError):
        load_excel("does_not_exist.xlsx")


def test_load_excel_raises_when_sheet_is_missing(tmp_path: Path) -> None:
    file_path = tmp_path / "qa.xlsx"
    _write_excel(_valid_dataframe(), file_path, sheet_name="WrongSheet")

    with pytest.raises(ValueError, match="Sheet 'Daily_Status' not found"):
        load_excel(file_path)


def test_validate_excel_raises_when_required_columns_missing() -> None:
    invalid_df = pd.DataFrame([{"Date": "2026-09-17", "Platform": "Web"}])

    with pytest.raises(ValueError, match="Missing required column"):
        validate_excel(invalid_df)


def test_load_excel_ignores_fully_empty_rows(tmp_path: Path) -> None:
    file_path = tmp_path / "qa.xlsx"
    dataframe = pd.DataFrame(
        [
            _valid_dataframe().iloc[0].to_dict(),
            {column: None for column in REQUIRED_COLUMNS},
            {**_valid_dataframe().iloc[0].to_dict(), "Platform": "iOS"},
        ]
    )
    _write_excel(dataframe, file_path, sheet_name="Daily_Status")

    result = load_excel(file_path)

    assert len(result) == 2
    assert set(result["Platform"]) == {"Web", "iOS"}


def test_load_excel_fills_missing_numeric_and_text_values(tmp_path: Path) -> None:
    file_path = tmp_path / "qa.xlsx"
    dataframe = pd.DataFrame(
        [
            {
                "Date": None,
                "Platform": "Android",
                "Task": "Checkout critical path",
                "Status": None,
                "Total": None,
                "Passed": "",
                "Failed": None,
                "Blocked": None,
                "Not Executed": None,
                "Owner": None,
                "Remarks": None,
                "Release": None,
                "UAT Date": None,
                "PROD Date": None,
            }
        ]
    )
    _write_excel(dataframe, file_path, sheet_name="Daily_Status")

    result = load_excel(file_path)
    row = result.iloc[0]

    assert row["Total"] == 0
    assert row["Passed"] == 0
    assert row["Failed"] == 0
    assert row["Blocked"] == 0
    assert row["Not Executed"] == 0
    assert row["Date"] == ""
    assert row["Status"] == ""
    assert row["Owner"] == ""
    assert row["Remarks"] == ""
