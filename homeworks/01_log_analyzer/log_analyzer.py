import os
import re
import gzip
from datetime import datetime
from pathlib import Path
from typing import Generator, Dict, Any, List, Union
from collections import defaultdict
import statistics
import json
import argparse
import sys
import structlog
import yaml

log = structlog.get_logger()


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '  # noqa: E501
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" ' # noqa: E501
#                     '$request_time';

DEFAULT_CONFIG = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./logs",
    "LOG_FILE": "./logs",
}


def resolve_path(path: Union[str, Path]) -> Path:
    path_str = str(path) if isinstance(path, Path) else path
    return (Path(__file__).parent / path_str).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="./config.yaml")
    return parser.parse_args()


def load_config(default_config: dict, config_path: str) -> dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file '{config_path}' not found")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML config: {e}")

    result_config = default_config.copy()
    result_config.update(file_config)
    return result_config


def get_log_files_paths(log_dir: Union[str, Path]) -> list[str]:
    """
    Get all nginx access log files in the specified directory.
    """
    log_file_name_prefix = "nginx-access-ui"
    full_log_dir = resolve_path(log_dir)

    if not full_log_dir.exists() or not full_log_dir.is_dir():
        raise FileNotFoundError(f"Log directory '{full_log_dir}' does not exist")

    log_files = [
        str(file_path)
        for file_path in full_log_dir.iterdir()
        if file_path.is_file() and file_path.name.startswith(log_file_name_prefix)
    ]

    return log_files


def get_latest_log_file(log_files: list[str]) -> tuple[datetime | None, str | None]:
    """
    Find the most recent log file based on the date in the filename.
    Returns a tuple of (date, filepath) or (None, None) if no valid log files found.
    """
    latest_file = None
    latest_date = None

    date_pattern = r"-(\d{8})(?:\.gz)?$"
    for file in log_files:
        match = re.search(date_pattern, file)
        if match:
            date_str = match.group(1)
            try:
                file_date = datetime.strptime(date_str, "%Y%m%d")

                if latest_date is None or file_date > latest_date:
                    latest_date = file_date
                    latest_file = file
            except ValueError:
                # Skip files with invalid date format
                continue

    return latest_date, latest_file


def read_log_file(log_file_path: str) -> Generator[Dict[str, Any], None, None]:
    """
    Generator function to read and parse nginx logs in ui_short format.

    Format:
    $remote_addr  $remote_user $http_x_real_ip [$time_local] "$request"
    $status $body_bytes_sent "$http_referer"
    "$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER"
    $request_time

    Yields parsed log entries as dictionaries with focus on URL and request_time.
    """
    # Regex pattern to parse nginx logs
    log_pattern = re.compile(
        r"(?P<remote_addr>[\d\.]+)\s+"
        r"(?P<remote_user>[^ ]*)\s+"
        r"(?P<http_x_real_ip>[^ ]*)\s+"
        r"\[(?P<time_local>.*?)\]\s+"
        r'"(?P<request>.*?)"\s+'
        r"(?P<status>\d+)\s+"
        r"(?P<body_bytes_sent>\d+)\s+"
        r'"(?P<http_referer>.*?)"\s+'
        r'"(?P<http_user_agent>.*?)"\s+'
        r'"(?P<http_x_forwarded_for>.*?)"\s+'
        r'"(?P<http_x_request_id>.*?)"\s+'
        r'"(?P<http_x_rb_user>.*?)"\s+'
        r"(?P<request_time>[\d\.]+)"
    )

    # Regex to extract URL from request field
    request_url_pattern = re.compile(
        r"^(?:GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)\s+(?P<url>[^\s]+)"
    )

    # Determine file opener based on extension
    is_gzipped = log_file_path.endswith(".gz")
    opener = gzip.open if is_gzipped else open
    mode = "rt" if is_gzipped else "r"

    try:
        with opener(log_file_path, mode, encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                try:
                    line = line.strip()
                    if not line:
                        continue

                    # Parse log line
                    match = log_pattern.match(line)
                    if not match:
                        # Unparseable line - log or skip
                        continue

                    log_entry = match.groupdict()

                    # Extract URL from request
                    request = log_entry.get("request", "")
                    url_match = request_url_pattern.match(request)
                    if url_match:
                        url = url_match.group("url")
                    else:
                        # If we can't extract URL using regex, use a fallback
                        parts = request.split()
                        url = parts[1] if len(parts) > 1 else request

                    # Store the URL and convert request_time to float
                    log_entry["url"] = url
                    log_entry["request_time"] = float(log_entry["request_time"])

                    yield log_entry

                except Exception as e:
                    print(f"Error parsing line {line_number}: {e}")
                    continue

    except Exception as e:
        # File-level error handling
        print(f"Error processing file {log_file_path}: {e}")


def get_statistics_from_log_file(
    log_file_generator: Generator[Dict[str, Any], None, None], report_size: int
) -> List[Dict[str, Any]]:
    """
    Calculate statistics from a log file generator.
    """
    url_data = defaultdict(list)
    total_requests = 0
    total_time = 0.0

    for parsed_log in log_file_generator:
        url = parsed_log["url"]
        request_time = parsed_log["request_time"]

        url_data[url].append(request_time)
        total_requests += 1
        total_time += request_time

    stats = {}
    for url, times in url_data.items():
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        max_time = max(times)
        time_sum = sum(times)
        count = len(times)

        stats[url] = {
            "count": count,
            "count_perc": round(count / total_requests * 100, 3),
            "time_sum": round(time_sum, 2),
            "time_perc": round(time_sum / total_time * 100, 3),
            "time_avg": round(avg_time, 3),
            "time_max": round(max_time, 3),
            "time_med": round(median_time, 3),
        }

    sorted_stats = sorted(stats.items(), key=lambda x: x[1]["time_sum"], reverse=True)

    sorted_stats = sorted_stats[:report_size]

    report_rows = []
    for url, metrics in sorted_stats:
        row = {"url": url}
        row.update(metrics)
        report_rows.append(row)

    return report_rows


def generate_report(
    stats: List[Dict[str, Any]], report_dir: str, last_date: datetime
) -> None:
    """
    Generate a report from the statistics.
    """
    template_path = os.path.join(report_dir, "report.html")
    with open(template_path, "r", encoding="utf-8") as file:
        template = file.read()
        table_data = json.dumps(stats)
        report = template.replace("$table_json", table_data)
        report_path = os.path.join(
            report_dir, f"report-{last_date.strftime('%Y.%m.%d')}.html"
        )
        with open(report_path, "w", encoding="utf-8") as file:
            file.write(report)


def main() -> None:
    args = parse_args()

    try:
        config = load_config(DEFAULT_CONFIG, args.config)
    except (FileNotFoundError, ValueError) as e:
        log.error("Config error", error=str(e))
        sys.exit(1)

    log.info("Config loaded successfully", config=config)

    try:
        log_files = get_log_files_paths(resolve_path(config["LOG_DIR"]))
        if not log_files:
            log.error("No log files found in the specified directory")
            sys.exit(1)
    except Exception as e:
        log.error(f"Failed to get log files: {e}")
        sys.exit(1)

    last_date, latest_file = get_latest_log_file(log_files)
    if not last_date or not latest_file:
        log.error("Failed to determine the latest log file")
        sys.exit(1)

    log.info(f"Latest log file found: {latest_file}, date: {last_date}")

    generator = read_log_file(latest_file)

    try:
        stats_from_file = get_statistics_from_log_file(generator, config["REPORT_SIZE"])
        log.info("Calculated statistics from the latest log file")
    except Exception as e:
        log.error(f"Failed to get statistics from the latest log file: {e}")
        sys.exit(1)

    try:
        generate_report(stats_from_file, config["REPORT_DIR"], last_date)
        log.info("Report generated successfully")
    except Exception as e:
        log.error(f"Failed to generate report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# test
# print(get_log_files_paths(config["LOG_DIR"]))
# last_date, latest_file = get_latest_log_file(get_log_files_paths(config["LOG_DIR"]))
# generator = read_log_file(latest_file)
# stats_from_file = get_statistics_from_log_file(generator, 5)
# print(stats_from_file)
# generate_report(stats_from_file, config["REPORT_DIR"], last_date)
# for i in range(5):  # Check first 5 entries
#     try:
#         entry = next(generator)
#         print(f"\nEntry {i+1}:")
#         for key, value in entry.items():
#             if key in ['url', 'request_time', 'request', 'status']:
#                 print(f"  {key}: {value}")
#     except StopIteration:
#         print(f"File has fewer than {i+1} entries.")
#         break
