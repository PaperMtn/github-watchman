import builtins
import calendar
import json
import os
import re
import time
import requests
import yaml
from requests.exceptions import HTTPError
from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter

import github_watchman.config as cfg
import github_watchman.logger as logger


class GitHubAPIClient(object):

    def __init__(self, token, base_url):
        self.token = token
        self.base_url = base_url.rstrip('\\')
        self.per_page = 100
        self.session = session = requests.session()
        session.mount(self.base_url, HTTPAdapter(max_retries=Retry(connect=3, backoff_factor=1)))
        session.headers.update({
            'Authorization': 'token {}'.format(self.token),
            'Accept': 'application/vnd.github.v3.text-match+json'
        })

        if 'https://api.github.com' not in base_url and 'api/v3' not in base_url:
            self.base_url = '/'.join((base_url.rstrip('/'), 'api/v3'))
        else:
            self.base_url = base_url.rstrip('/')

    def make_request(self, url, params=None, data=None, method='GET', verify_ssl=True):
        try:
            response = self.session.request(method, url, params=params, data=data, verify=verify_ssl)
            response.raise_for_status()

            return response

        except HTTPError as http_error:
            if response.status_code == 400:
                if response.json().get('message').get('error'):
                    raise Exception(response.json().get('message').get('error'))
                else:
                    raise http_error
            elif response.status_code == 502 or response.status_code == 500:
                print('Retrying...')
                time.sleep(30)
                response = self.session.request(method, url, params=params, data=data, verify=verify_ssl)
                response.raise_for_status()
                return response
            elif response.status_code == 403:
                if response.headers.get('Retry-After'):
                    print('GitHub API abuse limit hit - retrying in {} seconds'.format(
                        (response.headers.get('Retry-After'))))
                    time.sleep(int(response.headers.get('Retry-After')) + 2)
                    response = self.session.request(method, url, params=params, data=data, verify=verify_ssl)
                    response.raise_for_status()
                    return response
                elif int(response.headers.get('X-RateLimit-Remaining')) == 0:
                    print('GitHub API rate limit reached - cooling off')
                    time.sleep(int(response.headers.get('X-RateLimit-Reset')) - int(time.time()) + 5)
                    response = self.session.request(method, url, params=params, data=data, verify=verify_ssl)
                    response.raise_for_status()
                    return response
                else:
                    print(response.headers)
            else:
                raise http_error
        except Exception as e:
            print(e)

    def multipage_search(self, url, query, media_type=None):
        """Wrapper for GitHub API methods that use pagination"""

        if media_type is None:
            media_type = 'application/vnd.github.v3.text-match+json'

        results = []
        params = {
            'per_page': self.per_page,
            'q': query,
            'page': 1
        }
        self.session.headers.update({'Accept': media_type})

        response = self.make_request('/'.join((self.base_url, url)), params=params)
        for value in response.json().get('items'):
            results.append(value)

        if response.links.get('last'):
            total_pages = response.links.get('last').get('url')[response.links.get('last').get('url').rindex('=') + 1:]
            for page in range(2, int(total_pages) + 1):
                time.sleep(2)
                params['page'] = str(page)
                response = self.make_request('/'.join((self.base_url, url)), params=params)
                for value in response.json().get('items'):
                    results.append(value)

        return results

    def get_user(self):
        return self.make_request('/'.join((self.base_url, 'user'))).json()

    def get_repository(self, fullname):
        return self.make_request('/'.join((self.base_url, 'repos/{}'.format(fullname)))).json()


def initiate_github_connection():
    """Create a GitHub API client object"""

    try:
        token = os.environ['GITHUB_WATCHMAN_TOKEN']
    except KeyError:
        with open('{}/watchman.conf'.format(os.path.expanduser('~'))) as yaml_file:
            config = yaml.safe_load(yaml_file)

        token = config.get('github_watchman').get('token')

    try:
        url = os.environ['GITHUB_WATCHMAN_URL']
    except KeyError:
        with open('{}/watchman.conf'.format(os.path.expanduser('~'))) as yaml_file:
            config = yaml.safe_load(yaml_file)

        url = config.get('github_watchman').get('url')

    return GitHubAPIClient(token, url)


def convert_time(timestamp):
    """Convert ISO 8601 timestamp to epoch """

    pattern = '%Y-%m-%dT%H:%M:%SZ'
    return int(time.mktime(time.strptime(timestamp, pattern)))


def deduplicate(input_list):
    """Removes duplicates where results are returned by multiple queries"""

    list_of_strings = [json.dumps(d, sort_keys=True) for d in input_list]
    list_of_strings = set(list_of_strings)
    return [json.loads(s) for s in list_of_strings]


def search_code(github: GitHubAPIClient, log_handler, rule, timeframe=cfg.ALL_TIME):
    """Uses the Search API to get code fragments matching a search term.
        This is then filtered by regex to find true matches"""

    results = []
    now = calendar.timegm(time.gmtime())
    if isinstance(log_handler, logger.StdoutLogger):
        print = log_handler.log_info
    else:
        print = builtins.print

    for query in rule.get('strings'):
        code_list = github.multipage_search('search/code', query)
        if code_list:
            print('{} code fragments found matching: {}'.format(len(code_list), query.replace('"', '')))
            if timeframe != cfg.ALL_TIME:
                for code in code_list:
                    r = re.compile(rule.get('pattern'))
                    repository = github.get_repository(code.get('repository').get('full_name'))
                    if convert_time(repository.get('updated_at')) > (now - timeframe) and r.search(str(code.get('text_matches'))):
                        match_list = []
                        for match in code.get('text_matches'):
                            match_list.append({
                                'object_url': match.get('object_url'),
                                'object_type': match.get('object_type'),
                                'fragment': match.get('fragment')
                            })

                        results_dict = {
                            'file_name': code.get('name'),
                            'file_url': code.get('html_url'),
                            'sha': code.get('sha'),
                            'repository': {
                                'repository_id': code.get('repository').get('id'),
                                'repository_node_id': code.get('repository').get('node_id'),
                                'repository_name': code.get('repository').get('name'),
                                'repository_url': code.get('repository').get('html_url'),
                            },
                            'matches': match_list
                        }

                        results.append(results_dict)
            else:
                for code in code_list:
                    r = re.compile(rule.get('pattern'))
                    if r.search(str(code.get('text_matches'))):
                        match_list = []
                        for match in code.get('text_matches'):
                            match_list.append({
                                'object_url': match.get('object_url'),
                                'object_type': match.get('object_type'),
                                'fragment': match.get('fragment')
                            })

                        results_dict = {
                            'file_name': code.get('name'),
                            'file_url': code.get('html_url'),
                            'sha': code.get('sha'),
                            'repository': {
                                'repository_id': code.get('repository').get('id'),
                                'repository_node_id': code.get('repository').get('node_id'),
                                'repository_name': code.get('repository').get('name'),
                                'repository_url': code.get('repository').get('html_url'),
                            },
                            'matches': match_list
                        }

                        results.append(results_dict)
        else:
            print('No code fragments found matching: {}'.format(query.replace('"', '')))
    if results:
        results = deduplicate(results)
        print('{} total matches found after filtering'.format(len(results)))
        return results
    else:
        print('No matches found after filtering')


def search_commits(github: GitHubAPIClient, log_handler, rule, timeframe=cfg.ALL_TIME):
    """Uses the Search API to get commits matching a search term.
        This is then filtered by regex to find true matches"""

    results = []
    now = calendar.timegm(time.gmtime())
    if isinstance(log_handler, logger.StdoutLogger):
        print = log_handler.log_info
    else:
        print = builtins.print

    pattern = '%Y-%m-%dT%H:%M:%S.%f%z'

    for query in rule.get('strings'):
        commit_list = github.multipage_search('search/commits', query, 'application/vnd.github.cloak-preview.text-match+json')
        if commit_list:
            print('{} commits found matching: {}'.format(len(commit_list), query.replace('"', '')))
            for commit in commit_list:
                r = re.compile(rule.get('pattern'))
                commit_time = int(time.mktime(time.strptime(commit.get('commit').get('committer').get('date'), pattern)))
                if commit_time > (now - timeframe) and r.search(str(commit.get('text_matches'))):
                    match_list = []
                    for match in commit.get('text_matches'):
                        match_list.append({
                            'object_url': match.get('object_url'),
                            'object_type': match.get('object_type'),
                            'fragment': match.get('fragment')
                        })

                    results_dict = {
                        'commit_url': commit.get('html_url'),
                        'sha': commit.get('sha'),
                        'comments_url': commit.get('comments_url'),
                        'committer_name': commit.get('committer').get('name'),
                        'committer_id': commit.get('committer').get('id'),
                        'committer_email': commit.get('committer').get('email'),
                        'committer_login': commit.get('committer').get('email'),
                        'commit_date': commit.get('commit').get('committer').get('date'),
                        'message': commit.get('message'),
                        'repository': {
                            'repository_id': commit.get('repository').get('id'),
                            'repository_node_id': commit.get('repository').get('node_id'),
                            'repository_name': commit.get('repository').get('name'),
                            'repository_url': commit.get('repository').get('html_url'),
                        },
                        'matches': match_list
                    }

                    results.append(results_dict)
        else:
            print('No commits found matching: {}'.format(query.replace('"', '')))
    if results:
        results = deduplicate(results)
        print('{} total matches found after filtering'.format(len(results)))
        return results
    else:
        print('No matches found after filtering')


def search_issues(github: GitHubAPIClient, log_handler, rule, timeframe=cfg.ALL_TIME):
    """Uses the Search API to get issues matching a search term.
        This is then filtered by regex to find true matches"""

    results = []
    now = calendar.timegm(time.gmtime())
    if isinstance(log_handler, logger.StdoutLogger):
        print = log_handler.log_info
    else:
        print = builtins.print

    for query in rule.get('strings'):
        issue_list = github.multipage_search('search/issues', query)
        if issue_list:
            print('{} issues found matching: {}'.format(len(issue_list), query.replace('"', '')))
            for issue in issue_list:
                r = re.compile(rule.get('pattern'))
                if convert_time(issue.get('updated_at')) > (now - timeframe) and r.search(str(issue.get('text_matches'))):
                    match_list = []
                    for match in issue.get('text_matches'):
                        match_list.append({
                            'object_url': match.get('object_url'),
                            'object_type': match.get('object_type'),
                            'fragment': match.get('fragment')
                        })

                    results_dict = {
                        'issue_id': issue.get('id'),
                        'issue_title': issue.get('title'),
                        'issue_body': issue.get('body'),
                        'issue_url': issue.get('html_url'),
                        'sha': issue.get('sha'),
                        'user_login': issue.get('user').get('login'),
                        'user_id': issue.get('user').get('id'),
                        'state': issue.get('state'),
                        'updated_at': issue.get('updated_at'),
                        'repository_url': issue.get('repository_url'),
                        'matches': match_list
                    }

                    results.append(results_dict)
        else:
            print('No issues found matching: {}'.format(len(issue_list), query.replace('"', '')))
    if results:
        results = deduplicate(results)
        print('{} total matches found after filtering'.format(len(results)))
        return results
    else:
        print('No matches found after filtering')


def search_repositories(github: GitHubAPIClient, log_handler, rule, timeframe=cfg.ALL_TIME):
    """Uses the Search API to get repositories matching a search term.
        This is then filtered by regex to find true matches"""

    results = []
    now = calendar.timegm(time.gmtime())
    if isinstance(log_handler, logger.StdoutLogger):
        print = log_handler.log_info
    else:
        print = builtins.print

    for query in rule.get('strings'):
        repo_list = github.multipage_search('search/repositories', query)
        if repo_list:
            print('{} repositories found matching: {}'.format(len(repo_list), query.replace('"', '')))
            for repo in repo_list:
                r = re.compile(rule.get('pattern'))
                if convert_time(repo.get('updated_at')) > (now - timeframe) and r.search(str(repo.get('text_matches'))):
                    match_list = []
                    for match in repo.get('text_matches'):
                        match_list.append({
                            'object_url': match.get('object_url'),
                            'object_type': match.get('object_type'),
                            'fragment': match.get('fragment')
                        })

                    results_dict = {
                        'repository_id': repo.get('id'),
                        'repository_name': repo.get('full_name'),
                        'repository_description': repo.get('description'),
                        'repository_url': repo.get('html_url'),
                        'updated_at': repo.get('updated_at'),
                        'owner_login': repo.get('owner').get('login'),
                        'owner_id': repo.get('owner').get('id'),
                        'issue_url': repo.get('html_url'),
                        'matches': match_list
                    }

                    results.append(results_dict)
        else:
            print('No repositories found matching: {}'.format(query.replace('"', '')))
    if results:
        results = deduplicate(results)
        print('{} total matches found after filtering'.format(len(results)))
        return results
    else:
        print('No matches found after filtering')
