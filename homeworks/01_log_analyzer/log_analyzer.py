# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '  # noqa: E501
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" ' # noqa: E501
#                     '$request_time';

config = {"REPORT_SIZE": 1000, "REPORT_DIR": "./reports", "LOG_DIR": "./log"}


def main() -> None:
    pass


if __name__ == "__main__":
    main()
