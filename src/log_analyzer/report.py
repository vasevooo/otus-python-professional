import os
import json
from datetime import datetime
from typing import Any, Dict, List
from common.paths import BASE_DIR


def generate_report(
    stats: List[Dict[str, Any]], report_dir: str, last_date: datetime
) -> None:
    """
    Generate a report from the statistics.
    """
    template_path = os.path.join(BASE_DIR / report_dir, "report.html")
    with open(template_path, "r", encoding="utf-8") as file:
        template = file.read()
        table_data = json.dumps(stats)
        report = template.replace("$table_json", table_data)
        report_path = os.path.join(
            BASE_DIR, report_dir, f"report-{last_date.strftime('%Y.%m.%d')}.html"
        )
        with open(report_path, "w", encoding="utf-8") as file:
            file.write(report)
