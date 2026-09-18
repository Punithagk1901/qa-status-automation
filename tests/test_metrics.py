from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metrics import calculate_metrics


def test_calculate_metrics_normal_data() -> None:
    dataframe = pd.DataFrame(
        [
            {"Total": 100, "Passed": 70, "Failed": 20, "Blocked": 5, "Not Executed": 5},
            {"Total": 50, "Passed": 30, "Failed": 10, "Blocked": 5, "Not Executed": 5},
        ]
    )

    result = calculate_metrics(dataframe)

    assert result["totals"]["Total Tests"] == 150
    assert result["totals"]["Passed"] == 100
    assert result["totals"]["Failed"] == 30
    assert result["totals"]["Blocked"] == 10
    assert result["totals"]["Not Executed"] == 10
    assert result["derived"]["Executed"] == 140
    assert result["derived"]["Execution Percentage"] == 93.33
    assert result["derived"]["Pass Percentage"] == 71.43


def test_calculate_metrics_empty_data() -> None:
    dataframe = pd.DataFrame(columns=["Total", "Passed", "Failed", "Blocked", "Not Executed"])

    result = calculate_metrics(dataframe)

    assert result["totals"]["Total Tests"] == 0
    assert result["totals"]["Passed"] == 0
    assert result["totals"]["Failed"] == 0
    assert result["totals"]["Blocked"] == 0
    assert result["totals"]["Not Executed"] == 0
    assert result["derived"]["Executed"] == 0
    assert result["derived"]["Execution Percentage"] == 0.0
    assert result["derived"]["Pass Percentage"] == 0.0


def test_calculate_metrics_zero_totals() -> None:
    dataframe = pd.DataFrame(
        [{"Total": 0, "Passed": 0, "Failed": 0, "Blocked": 0, "Not Executed": 0}]
    )

    result = calculate_metrics(dataframe)

    assert result["derived"]["Executed"] == 0
    assert result["derived"]["Execution Percentage"] == 0.0
    assert result["derived"]["Pass Percentage"] == 0.0


def test_calculate_metrics_hundred_percent_pass() -> None:
    dataframe = pd.DataFrame(
        [
            {"Total": 20, "Passed": 20, "Failed": 0, "Blocked": 0, "Not Executed": 0},
            {"Total": 10, "Passed": 10, "Failed": 0, "Blocked": 0, "Not Executed": 0},
        ]
    )

    result = calculate_metrics(dataframe)

    assert result["derived"]["Executed"] == 30
    assert result["derived"]["Execution Percentage"] == 100.0
    assert result["derived"]["Pass Percentage"] == 100.0


def test_calculate_metrics_mixed_pass_fail() -> None:
    dataframe = pd.DataFrame(
        [
            {"Total": 80, "Passed": 40, "Failed": 20, "Blocked": 10, "Not Executed": 10},
            {"Total": 20, "Passed": 5, "Failed": 10, "Blocked": 0, "Not Executed": 5},
        ]
    )

    result = calculate_metrics(dataframe)

    assert result["totals"]["Total Tests"] == 100
    assert result["totals"]["Passed"] == 45
    assert result["totals"]["Failed"] == 30
    assert result["totals"]["Blocked"] == 10
    assert result["totals"]["Not Executed"] == 15
    assert result["derived"]["Executed"] == 85
    assert result["derived"]["Execution Percentage"] == 85.0
    assert result["derived"]["Pass Percentage"] == 52.94
