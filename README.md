<img src="https://i.imgur.com/4lNLwdV.png" width="550">

# GitHub Watchman
![Python 2.7 and 3 compatible](https://img.shields.io/pypi/pyversions/github-watchman)
![PyPI version](https://img.shields.io/pypi/v/github-watchman.svg)
![License: MIT](https://img.shields.io/pypi/l/github-watchman.svg)

## About GitHub Watchman

GitHub Watchman is an application that uses the GitHub API to audit GitHub for sensitive data and credentials exposed internally.

### Features
It searches GitHub for internally shared projects and looks at:
- Code
- Commits
- Issues
- Repositories

For the following data:
- GCP keys and service account files
- AWS keys
- Azure keys and service account files
- Google API keys
- Slack API tokens & webhooks
- Private keys (SSH, PGP, any other misc private key)
- Exposed tokens (Bearer tokens, access tokens, client_secret etc.)
- S3 config files
- Passwords in plaintext
- and more

#### Time based searching
You can run GitHub Watchman to look for results going back as far as:
- 24 hours
- 7 days
- 30 days
- All time

This means after one deep scan, you can schedule GitHub Watchman to run regularly and only return results from your chosen timeframe.

### Rules
GitHub Watchman uses custom YAML rules to detect matches in GitHub.

They follow this format:

```yaml
---
filename:
enabled: #[true|false]
meta:
  name:
  author:
  date:
  description: #what the search should find#
  severity: #rating out of 100#
scope: #what to search, any combination of the below#
- code
- commits
- issues
- repositories
test_cases:
  match_cases:
  - #test case that should match the regex#
  fail_cases:
  - #test case that should not match the regex#
strings:
- #search query to use in GitHub#
pattern: #Regex pattern to filter out false positives#
```
There are Python tests to ensure rules are formatted properly and that the Regex patterns work in the `tests` dir

More information about rules, and how you can add your own, is in the file `docs/rules.md`.


### Logging

GitHub Watchman gives the following logging options:
- CSV
- Log file
- Stdout
- TCP stream

When using CSV logging, searches for rules are returned in separate CSV files, for all other methods of logging, results are output in JSON format, perfect for ingesting into a SIEM or other log analysis platform.

For file and TCP stream logging, configuration options need to be passed via `.conf` file or environment variable. See the file `docs/logging.md` for instructions on how to set it up.

If no logging option is given, GitHub Watchman defaults to CSV logging.

## Requirements

### GitHub versions
GitHub Watchman uses the v3 API, and works with GitHub Enterprise Server versions that support the v3 API.

GitHub Watchman also works with GitHub.com (Free, Pro and Team) using the API.

### GitHub personal access token
To run GitHub Watchman, you will need a GitHub personal access token.

You can create a personal access token in the GitHub GUI via Settings -> Developer settings -> Personal access tokens

The token needs no specific scopes assigned, as it searches public repositories in the GitHub instance.

**Note**: Personal access tokens act on behalf of the user who creates them, so I would suggest you create a token using a service account, otherwise the app will have access to your private repositories.

### GitHub URL

You also need to provide the URL of your GitHub instance.

#### Providing token & URL
GitHub Watchman will first try to get the the GitHub token and URL from the environment variables `GITHUB_WATCHMAN_TOKEN` and `GITHUB_WATCHMAN_URL`, if this fails they will be taken from .conf file (see below).

### .conf file
Configuration options can be passed in a file named `watchman.conf` which must be stored in your home directory. The file should follow the YAML format, and should look like below:
```yaml
github_watchman:
  token: abc123
  url: https://github.example.com
  logging:
    file_logging:
      path:
    json_tcp:
      host:
      port:
```
GitHub Watchman will look for this file at runtime, and use the configuration options from here. If you are not using the advanced logging features, leave them blank.

If you are having issues with your .conf file, run it through a YAML linter.

An example file is in `docs/example.conf`

**Note** If you use any other Watchman applications and already have a `watchman.conf` file, just append the conf data for GitHub Watchman to the existing file.

## Installation
Install via pip

`pip install github-watchman`

Or via source

## Usage
GitHub Watchman will be installed as a global command, use as follows:
```
usage: github-watchman [-h] --timeframe {d,w,m,a} --output
                   {csv,file,stdout,stream} [--version] [--all] [--code]
                   [--commits] [--issues] [--repositories]

Monitoring GitHub for sensitive data shared publicly

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --all                 Find everything
  --code                Search code
  --commits             Search commits
  --issues              Search issues
  --repositories        Search merge requests

required arguments:
  --timeframe {d,w,m,a}
                        How far back to search: d = 24 hours w = 7 days, m =
                        30 days, a = all time
  --output {csv,file,stdout,stream}
                        Where to send results


  ```

You can run GitHub Watchman to look for everything, and output to default CSV:

`github-watchman --timeframe a --all`

Or arguments can be grouped together to search more granularly. This will look for commits and milestones for the last 30 days, and output the results to a TCP stream:

`github-watchman --timeframe m --commits --milestones --output stream`

## Other Watchman apps
You may be interested in some of the other apps in the Watchman family:
- [Slack Watchman](https://github.com/PaperMtn/slack-watchman)
- [GitLab Watchman](https://github.com/PaperMtn/gitlab-watchman)

## License
The source code for this project is released under the [GNU General Public Licence](https://www.gnu.org/licenses/licenses.html#GPL). This project is not associated with GitHub.
