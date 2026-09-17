from datetime import datetime
from pathlib import Path
from typing import Union

from jinja2 import Environment, FileSystemLoader, select_autoescape

from excel_reader import load_excel
from metrics import calculate_metrics


DETAIL_COLUMNS = ["Date", "Platform", "Task", "Status", "Owner", "Remarks"]


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

    details_df = dataframe[DETAIL_COLUMNS].copy()
    details_df = details_df.fillna("")
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
        detail_rows=detail_rows,
    )

    final_output_path = Path(output_path)
    final_output_path.parent.mkdir(parents=True, exist_ok=True)
    final_output_path.write_text(rendered_html, encoding="utf-8")

    return final_output_path.resolve()


if __name__ == "__main__":
    output_file = generate_report("QA_Status_Template.xlsx")
    print(f"Generated report: {output_file}")
