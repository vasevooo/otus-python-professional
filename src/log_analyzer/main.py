import sys
import structlog
from common.config import load_config
from common.paths import BASE_DIR
from pathlib import Path

from reader import read_log_file, get_latest_log_file, get_log_files_paths
from stats import get_statistics_from_log_file
from report import generate_report
from common.logging import setup_logging, setup_pre_logging
from common.cli import parse_args


FILE_DIR = Path(__file__).parent.resolve()

DEFAULT_CONFIG = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./logs",
    "LOG_FILE": None,
}


def main() -> None:
    setup_pre_logging()
    log = structlog.get_logger()
    log.info("Startup log initialized")
    log.info(f"Base directory: {BASE_DIR}, File directory: {FILE_DIR}")

    args = parse_args(default_dir=FILE_DIR)

    try:
        config = load_config(default_config=DEFAULT_CONFIG, config_path=args.config)
    except (FileNotFoundError, ValueError) as e:
        log.error("Config error", error=str(e))
        sys.exit(1)

    log.info("Config loaded successfully", config=config)

    try:
        if config.get("LOG_FILE"):
            setup_logging(config.get("LOG_FILE"))
            log = structlog.get_logger()
            log.info("Logger reconfigured", config=config)
    except Exception as e:
        log.error("Logger reconfiguration error", error=str(e))
        sys.exit(1)

    try:
        log_dir = BASE_DIR / config["LOG_DIR"]
        report_dir = BASE_DIR / config["REPORT_DIR"]
        report_dir.mkdir(parents=True, exist_ok=True)

        log_files = get_log_files_paths(log_dir)

        report_date, log_file = get_latest_log_file(log_files)
        log.info(f"Latest log file found: {log_file}, date: {report_date}")
        report_path = report_dir / f"report-{report_date.strftime('%Y.%m.%d')}.html"

        if report_path.exists():
            log.info("Report already exists, skipping", report=str(report_path))
            return

        log_entries = read_log_file(log_file)
        stats = get_statistics_from_log_file(log_entries, config["REPORT_SIZE"])
        log.info("Calculated statistics from the latest log file")
        generate_report(stats, report_dir, report_date)

        log.info("Report generated", report=str(report_path))

    except KeyboardInterrupt:
        log.error("Execution interrupted by user")
        sys.exit(130)
    except Exception:
        log.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
