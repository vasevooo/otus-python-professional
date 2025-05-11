from log_analyzer.reader import read_log_file
import tempfile


def test_read_log_file_single_line() -> None:
    log_line = (
        "1.1.1.1 - - [29/Jun/2017:03:50:22 +0300] "
        '"GET /test/url HTTP/1.1" 200 123 "-" "UserAgent" "-" "req-id" "-" 0.456\n'
    )
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(log_line)
        tmp.flush()
        parsed = list(read_log_file(tmp.name))

    assert len(parsed) == 1
    assert parsed[0]["url"] == "/test/url"
    assert parsed[0]["request_time"] == 0.456
