from datetime import datetime
import gzip
from pathlib import Path
import re
from common.paths import BASE_DIR
from typing import Any, Dict, Generator, Union
from common.logging import setup_pre_logging
import structlog

setup_pre_logging()
log = structlog.get_logger()

# Regex pattern to parse nginx logs
LOG_PATTERN = re.compile(
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
REQUEST_URL_PATTERN = re.compile(
    r"^(?:GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)\s+(?P<url>[^\s]+)"
)


def get_log_files_paths(log_dir: Union[str, Path]) -> list[str]:
    """
    Get all nginx access log files in the specified directory.
    """
    log_file_name_prefix = "nginx-access-ui"
    full_log_dir = BASE_DIR / log_dir

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
                    match = LOG_PATTERN.match(line)
                    if not match:
                        # Unparseable line - log or skip
                        continue

                    log_entry = match.groupdict()

                    # Extract URL from request
                    request = log_entry.get("request", "")
                    url_match = REQUEST_URL_PATTERN.match(request)
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

                except (ValueError, KeyError) as e:
                    log.error("Error parsing line", error=e, line_number=line_number)
                    continue

    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        # File-level error handling
        log.error("Error processing file", error=e, file_path=log_file_path)
        raise
