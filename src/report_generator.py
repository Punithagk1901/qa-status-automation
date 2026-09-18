from datetime import datetime
from pathlib import Path
from typing import Union

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from excel_reader import load_excel
from metrics import calculate_metrics


DETAIL_COLUMNS = ["Date", "Platform", "Task", "Status", "Owner", "Remarks"]
SUMMARY_COLUMNS = ["Total", "Passed", "Failed", "Blocked", "Not Executed"]


def _safe_percentage(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _determine_health_status(derived_metrics: dict) -> dict:
    pass_percentage = float(derived_metrics["Pass Percentage"])
    failure_percentage = float(derived_metrics["Failure Percentage"])
    blocked_percentage = float(derived_metrics["Blocked Percentage"])

    if pass_percentage >= 95 and failure_percentage <= 3 and blocked_percentage <= 2:
        return {
            "label": "Green",
            "tone_class": "health-green",
            "description": "Quality is on track for release readiness.",
        }
    if pass_percentage >= 90 and failure_percentage <= 7 and blocked_percentage <= 5:
        return {
            "label": "Amber",
            "tone_class": "health-amber",
            "description": "Quality needs close monitoring and rapid follow-up.",
        }
    return {
        "label": "Red",
        "tone_class": "health-red",
        "description": "Quality risk is high and requires immediate action.",
    }


def _build_platform_breakdown(dataframe: pd.DataFrame) -> list[dict]:
    if dataframe.empty:
        return []

    grouped = (
        dataframe.groupby("Platform", dropna=False)[SUMMARY_COLUMNS]
        .sum(numeric_only=True)
        .reset_index()
    )
    grouped["Platform"] = grouped["Platform"].replace("", "Unspecified").fillna("Unspecified")
    grouped["Executed"] = grouped["Passed"] + grouped["Failed"] + grouped["Blocked"]
    grouped["Pass %"] = grouped.apply(
        lambda row: _safe_percentage(row["Passed"], row["Executed"]), axis=1
    )
    grouped["Failure %"] = grouped.apply(
        lambda row: _safe_percentage(row["Failed"], row["Executed"]), axis=1
    )
    grouped["Blocked %"] = grouped.apply(
        lambda row: _safe_percentage(row["Blocked"], row["Executed"]), axis=1
    )
    grouped = grouped.sort_values(by=["Failure %", "Blocked %"], ascending=[False, False])
    return grouped.to_dict(orient="records")


def _build_release_summary(dataframe: pd.DataFrame) -> list[dict]:
    if dataframe.empty:
        return []

    grouped = (
        dataframe.groupby(["Release", "UAT Date", "PROD Date"], dropna=False)[SUMMARY_COLUMNS]
        .sum(numeric_only=True)
        .reset_index()
    )
    grouped["Release"] = grouped["Release"].replace("", "Unspecified").fillna("Unspecified")
    grouped["UAT Date"] = grouped["UAT Date"].fillna("")
    grouped["PROD Date"] = grouped["PROD Date"].fillna("")
    grouped["Executed"] = grouped["Passed"] + grouped["Failed"] + grouped["Blocked"]
    grouped["Pass %"] = grouped.apply(
        lambda row: _safe_percentage(row["Passed"], row["Executed"]), axis=1
    )
    grouped["Failure %"] = grouped.apply(
        lambda row: _safe_percentage(row["Failed"], row["Executed"]), axis=1
    )
    grouped["Blocked %"] = grouped.apply(
        lambda row: _safe_percentage(row["Blocked"], row["Executed"]), axis=1
    )
    grouped = grouped.sort_values(by=["Release"])
    return grouped.to_dict(orient="records")


def _build_executive_summary(
    totals: dict, derived: dict, health_status: dict, platform_breakdown: list[dict]
) -> list[str]:
    insights = [
        (
            f"Overall health is {health_status['label']} with pass rate "
            f"{derived['Pass Percentage']:.2f}% and execution rate "
            f"{derived['Execution Percentage']:.2f}%."
        ),
        (
            f"{derived['Executed']} of {totals['Total Tests']} planned tests were executed; "
            f"{totals['Not Executed']} remain pending."
        ),
    ]

    if platform_breakdown:
        top_risk_platform = platform_breakdown[0]
        insights.append(
            (
                f"Highest risk platform is {top_risk_platform['Platform']} "
                f"(Failure {top_risk_platform['Failure %']:.2f}%, "
                f"Blocked {top_risk_platform['Blocked %']:.2f}%)."
            )
        )
    else:
        insights.append("No platform data available for risk comparison.")

    return insights


def generate_report(
    excel_path: Union[str, Path],
    template_path: Union[str, Path] = "templates/status_email.html",
    output_path: Union[str, Path] = "output/qa_status_report.html",
) -> Path:
    """
    Generate a local Outlook-friendly HTML QA status dashboard.
    """
    dataframe = load_excel(excel_path, sheet_name="Daily_Status")
    metrics = calculate_metrics(dataframe)
    health_status = _determine_health_status(metrics["derived"])
    platform_breakdown = _build_platform_breakdown(dataframe)
    release_summary = _build_release_summary(dataframe)
    executive_summary = _build_executive_summary(
        metrics["totals"], metrics["derived"], health_status, platform_breakdown
    )

    details_df = dataframe[DETAIL_COLUMNS].copy()
    details_df = details_df.fillna("").astype(str)
    detail_rows = details_df.to_dict(orient="records")

    template_file = Path(template_path)
    environment = Environment(
        loader=FileSystemLoader(str(template_file.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = environment.get_template(template_file.name)

    rendered_html = template.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        totals=metrics["totals"],
        derived=metrics["derived"],
        health_status=health_status,
        executive_summary=executive_summary,
        platform_breakdown=platform_breakdown,
        release_summary=release_summary,
        detail_rows=detail_rows,
    )

    final_output_path = Path(output_path)
    final_output_path.parent.mkdir(parents=True, exist_ok=True)
    final_output_path.write_text(rendered_html, encoding="utf-8")

    return final_output_path.resolve()


if __name__ == "__main__":
    output_file = generate_report("QA_Status_Template.xlsx")
    print(f"Generated report: {output_file}")
