from collections import defaultdict
from typing import Any, Dict, Generator, List
import statistics


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
