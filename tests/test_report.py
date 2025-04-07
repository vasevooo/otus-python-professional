from log_analyzer.report import generate_report
import tempfile
from pathlib import Path
from datetime import datetime


def test_render_report_creates_file() -> None:
    stats = [
        {
            "url": "/a",
            "count": 1,
            "count_perc": 100,
            "time_sum": 1.0,
            "time_perc": 100,
            "time_avg": 1.0,
            "time_max": 1.0,
            "time_med": 1.0,
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        template_path = tmpdir_path / "report.html"
        report_path = tmpdir_path / "report-2025.04.07.html"

        # минимальный шаблон
        template_path.write_text("<html>$table_json</html>", encoding="utf-8")
        generate_report(stats, str(tmpdir_path), datetime(2025, 4, 7))

        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "/a" in content
        assert "$table_json" not in content
