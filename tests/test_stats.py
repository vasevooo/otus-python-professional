from log_analyzer.stats import get_statistics_from_log_file


def test_calculate_stats_basic() -> None:
    entries = [
        {"url": "/a", "request_time": 1.0},
        {"url": "/a", "request_time": 2.0},
        {"url": "/b", "request_time": 3.0},
    ]

    stats = get_statistics_from_log_file((e for e in entries), report_size=2)
    assert len(stats) == 2

    stat_a = next(s for s in stats if s["url"] == "/a")
    assert stat_a["count"] == 2
    assert stat_a["time_avg"] == 1.5
    assert stat_a["time_sum"] == 3.0
