# Logging
GitHub Watchman gives the following logging options:
- CSV
- Log file
- Stdout
- TCP stream

## CSV logging
CSV logging is the default logging option if no other output method is given at runtime.

Results for each search are output as CSV files in your current working directory.

## JSON formatted logging
All other logging options output their logs in JSON format. Here is an example:

```json
{"localtime": "2020-01-01 00:00:00,000", "level": "NOTIFY", "source": "GitHub Watchman", "scope": "issues", "type": "Slack API Tokens", "severity": "70", "detection_data": {"issue_body": "...", "issue_id": 12345, "issue_title": "...", "issue_url": "https://westeros.github.com/lannister_docs/issues/12345", "matches": [{"fragment": "...", "object_type": "IssueComment", "object_url": "https://westeros.github.com/repositories/12345/issues/comments/12345"}], "repository_url": "https://westeros.github.com/repos/lannister_docs/lannister_slack_bot", "sha": null, "state": "open", "updated_at": "2020-09-27T01:47:23Z", "user_id": 12345, "user_login": "tlannister"}}
```
This should contain all of the information you require to ingest these logs into a SIEM, or other log analysis platform.


### File logging
File logging saves JSON formatted logs to a file.

The path where you want to output the file needs to be passed when running GitHub Watchman. This can be done via the .conf file:
```yaml
github_watchman:
  token: abc123
  url: https://github.example.com
  logging:
    file_logging:
      path: /var/put_my_logs_here/
    json_tcp:
      host:
      port:
```
Or by setting your log path in the environment variable: `GITHUB_WATCHMAN_LOG_PATH`

If file logging is selected as the output option, but no path is give, GitHub Watchman defaults to the user's home directory.

The filename will be `github_watchman.log`

Note: GitHub Watchman does not handle the rotation of the file. You would need a solution such as logrotate for this.

### Stdout logging
Stdout logging sends JSON formatted logs to Stdout, for you to capture however you want.

### TCP stream logging
With this option, JSON formmatted logs are sent to a destination of your choosing via TCP

You will need to pass GitHub Watchman a host and port to receive the logs, either via .conf file:

```yaml
github_watchman:
  token: abc123
  url: https://github.example.com
  logging:
    file_logging:
      path:
    json_tcp:
      host: localhost
      port: 9020
```
Or by setting the environment variables `GITHUB_WATCHMAN_HOST` and `GITHUB_WATCHMAN_PORT`
