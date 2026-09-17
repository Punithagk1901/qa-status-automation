from typing import Dict

import pandas as pd


METRIC_COLUMNS = ["Total", "Passed", "Failed", "Blocked", "Not Executed"]


def _safe_percentage(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def calculate_metrics(dataframe: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Calculate QA totals and derived metrics from validated Excel data.
    """
    missing_columns = [column for column in METRIC_COLUMNS if column not in dataframe.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required metric column(s): {missing}")

    total_tests = int(pd.to_numeric(dataframe["Total"], errors="coerce").fillna(0).sum())
    passed = int(pd.to_numeric(dataframe["Passed"], errors="coerce").fillna(0).sum())
    failed = int(pd.to_numeric(dataframe["Failed"], errors="coerce").fillna(0).sum())
    blocked = int(pd.to_numeric(dataframe["Blocked"], errors="coerce").fillna(0).sum())
    not_executed = int(pd.to_numeric(dataframe["Not Executed"], errors="coerce").fillna(0).sum())

    executed = passed + failed + blocked
    execution_percentage = _safe_percentage(executed, total_tests)
    pass_percentage = _safe_percentage(passed, executed)

    return {
        "totals": {
            "Total Tests": total_tests,
            "Passed": passed,
            "Failed": failed,
            "Blocked": blocked,
            "Not Executed": not_executed,
        },
        "derived": {
            "Executed": executed,
            "Execution Percentage": execution_percentage,
            "Pass Percentage": pass_percentage,
        },
    }
