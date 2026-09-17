from pathlib import Path
from typing import Union

import pandas as pd


REQUIRED_COLUMNS = [
    "Date",
    "Platform",
    "Task",
    "Status",
    "Total",
    "Passed",
    "Failed",
    "Blocked",
    "Not Executed",
    "Owner",
    "Remarks",
    "Release",
    "UAT Date",
    "PROD Date",
]

NUMERIC_COLUMNS = ["Total", "Passed", "Failed", "Blocked", "Not Executed"]
TEXT_COLUMNS = [
    "Date",
    "Platform",
    "Task",
    "Status",
    "Owner",
    "Remarks",
    "Release",
    "UAT Date",
    "PROD Date",
]


def validate_excel(dataframe: pd.DataFrame) -> None:
    """Validate that all required columns are present."""
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in dataframe.columns]
    if missing_columns:
        missing_list = ", ".join(missing_columns)
        raise ValueError(f"Missing required column(s): {missing_list}")


def load_excel(
    file_path: Union[str, Path],
    sheet_name: str = "Daily_Status",
) -> pd.DataFrame:
    """
    Load and validate QA status data from an Excel workbook.

    Rules implemented:
    - Excel file exists
    - Sheet exists
    - All required columns exist
    - Empty rows are ignored
    - Missing numeric values become 0
    - Missing text values become blank
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    try:
        dataframe = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    except ValueError as exc:
        raise ValueError(f"Sheet '{sheet_name}' not found in {path}") from exc

    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    validate_excel(dataframe)

    # Ignore fully empty rows before applying clean-up defaults.
    dataframe = dataframe.dropna(how="all").copy()

    for column in NUMERIC_COLUMNS:
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce").fillna(0)

    for column in TEXT_COLUMNS:
        dataframe[column] = dataframe[column].fillna("")

    return dataframe
