import builtins
import argparse
import os
import yaml
import time
from pathlib import Path
from datetime import date
from colorama import init, deinit
from termcolor import colored

import github_watchman.github_wrapper as github
import github_watchman.__about__ as a
import github_watchman.config as cfg
import github_watchman.logger as logger


RULES_PATH = (Path(__file__).parent / 'rules').resolve()
OUTPUT_LOGGER = ''


def validate_conf(path):
    """Check the file watchman.conf exists"""

    if os.environ.get('GITHUB_WATCHMAN_TOKEN') and os.environ.get('GITHUB_WATCHMAN_URL'):
        return True
    if os.path.exists(path):
        with open(path) as yaml_file:
            return yaml.safe_load(yaml_file).get('github_watchman')


def search(github_connection, rule, tf, scope):
    if isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
        print = OUTPUT_LOGGER.log_info
    else:
        print = builtins.print
    try:
        if scope == 'code':
            print(colored('Searching for {} in {}'.format(rule.get('meta').get('name'),
                                                          'code'), 'yellow'))

            code = github.search_code(github_connection, OUTPUT_LOGGER, rule, tf)
            if code:
                if isinstance(OUTPUT_LOGGER, logger.CSVLogger):
                    OUTPUT_LOGGER.write_csv('exposed_{}'.format(rule.get('filename').split('.')[0]),
                                            'code',
                                            code)
                else:
                    for log_data in code:
                        OUTPUT_LOGGER.log_notification(log_data, 'code', rule.get('meta').get('name'),
                                                       rule.get('meta').get('severity'))
                    print('Results output to log')

        if scope == 'commits':
            print(colored('Searching for {} in {}'.format(rule.get('meta').get('name'),
                                                          'commits'), 'yellow'))

            commits = github.search_commits(github_connection, OUTPUT_LOGGER, rule, tf)
            if commits:
                if isinstance(OUTPUT_LOGGER, logger.CSVLogger):
                    OUTPUT_LOGGER.write_csv('exposed_{}'.format(rule.get('filename').split('.')[0]),
                                            'commits',
                                            commits)
                else:
                    for log_data in commits:
                        OUTPUT_LOGGER.log_notification(log_data, 'commits', rule.get('meta').get('name'),
                                                       rule.get('meta').get('severity'))
                    print('Results output to log')

        if scope == 'issues':
            print(colored('Searching for {} in {}'.format(rule.get('meta').get('name'),
                                                          'issues'), 'yellow'))

            issues = github.search_issues(github_connection, OUTPUT_LOGGER, rule, tf)
            if issues:
                if isinstance(OUTPUT_LOGGER, logger.CSVLogger):
                    OUTPUT_LOGGER.write_csv('exposed_{}'.format(rule.get('filename').split('.')[0]),
                                            'issues',
                                            issues)
                else:
                    for log_data in issues:
                        OUTPUT_LOGGER.log_notification(log_data, 'issues', rule.get('meta').get('name'),
                                                       rule.get('meta').get('severity'))
                    print('Results output to log')

        if scope == 'repositories':
            print(colored('Searching for {} in {}'.format(rule.get('meta').get('name'),
                                                          'repositories'), 'yellow'))

            repositories = github.search_repositories(github_connection, OUTPUT_LOGGER, rule, tf)
            if repositories:
                if isinstance(OUTPUT_LOGGER, logger.CSVLogger):
                    OUTPUT_LOGGER.write_csv('exposed_{}'.format(rule.get('filename').split('.')[0]),
                                            'repositories',
                                            repositories)
                else:
                    for log_data in repositories:
                        OUTPUT_LOGGER.log_notification(log_data, 'wiki_blobs', rule.get('meta').get('name'),
                                                       rule.get('meta').get('severity'))
                    print('Results output to log')
    except Exception as e:
        if isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
            print = OUTPUT_LOGGER.log_critical
        else:
            print = builtins.print

        print(colored(e, 'red'))


def load_rules():
    rules = []
    try:
        for file in os.scandir(RULES_PATH):
            if file.name.endswith('.yaml'):
                with open(file) as yaml_file:
                    rule = yaml.safe_load(yaml_file)
                    if rule.get('enabled'):
                        rules.append(rule)
        return rules
    except Exception as e:
        if isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
            print = OUTPUT_LOGGER.log_critical
        else:
            print = builtins.print

        print(colored(e, 'red'))


def main():
    global OUTPUT_LOGGER
    try:
        init()

        parser = argparse.ArgumentParser(description=a.__summary__)
        required = parser.add_argument_group('required arguments')
        required.add_argument('--timeframe', choices=['d', 'w', 'm', 'a'], dest='time',
                              help='How far back to search: d = 24 hours w = 7 days, m = 30 days, a = all time',
                              required=True)
        required.add_argument('--output', choices=['csv', 'file', 'stdout', 'stream'], dest='logging_type',
                              help='Where to send results', required=True)
        parser.add_argument('--version', action='version',
                            version='github-watchman {}'.format(a.__version__))
        parser.add_argument('--all', dest='everything', action='store_true',
                            help='Find everything')
        parser.add_argument('--code', dest='code', action='store_true',
                            help='Search code')
        parser.add_argument('--commits', dest='commits', action='store_true',
                            help='Search commits')
        parser.add_argument('--issues', dest='issues', action='store_true',
                            help='Search issues')
        parser.add_argument('--repositories', dest='repositories', action='store_true',
                            help='Search merge requests')

        args = parser.parse_args()
        tm = args.time
        everything = args.everything
        code = args.code
        commits = args.commits
        repositories = args.repositories
        issues = args.issues
        logging_type = args.logging_type

        if tm == 'd':
            tf = cfg.DAY_TIMEFRAME
        elif tm == 'w':
            tf = cfg.WEEK_TIMEFRAME
        elif tm == 'm':
            tf = cfg.MONTH_TIMEFRAME
        else:
            tf = cfg.ALL_TIME
        conf_path = '{}/watchman.conf'.format(os.path.expanduser('~'))

        if not validate_conf(conf_path):
            raise Exception(
                colored('GITHUB_WATCHMAN_TOKEN environment variable or watchman.conf file not detected. '
                        '\nEnsure environment variable is set or a valid file is located in your home '
                        'directory: {} ', 'red')
                .format(os.path.expanduser('~')))
        else:
            config = validate_conf(conf_path)
            connection = github.initiate_github_connection()

        if logging_type:
            if logging_type == 'file':
                if os.environ.get('GITHUB_WATCHMAN_LOG_PATH'):
                    OUTPUT_LOGGER = logger.FileLogger(os.environ.get('GITHUB_WATCHMAN_LOG_PATH'))
                elif config.get('logging').get('file_logging').get('path') and \
                        os.path.exists(config.get('logging').get('file_logging').get('path')):
                    OUTPUT_LOGGER = logger.FileLogger(log_path=config.get('logging').get('file_logging').get('path'))
                else:
                    print('No config given, outputting github_watchman.log file to home path')
                    OUTPUT_LOGGER = logger.FileLogger(log_path=os.path.expanduser('~'))
            elif logging_type == 'stdout':
                OUTPUT_LOGGER = logger.StdoutLogger()
            elif logging_type == 'stream':
                if os.environ.get('GITHUB_WATCHMAN_HOST') and os.environ.get('GITHUB_WATCHMAN_PORT'):
                    OUTPUT_LOGGER = logger.SocketJSONLogger(os.environ.get('GITHUB_WATCHMAN_HOST'),
                                                            os.environ.get('GITHUB_WATCHMAN_PORT'))
                elif config.get('logging').get('json_tcp').get('host') and \
                        config.get('logging').get('json_tcp').get('port'):
                    OUTPUT_LOGGER = logger.SocketJSONLogger(config.get('logging').get('json_tcp').get('host'),
                                                            config.get('logging').get('json_tcp').get('port'))
                else:
                    raise Exception("JSON TCP stream selected with no config")
            else:
                OUTPUT_LOGGER = logger.CSVLogger()
        else:
            print('No logging option selected, defaulting to CSV')
            OUTPUT_LOGGER = logger.CSVLogger()

        now = int(time.time())
        today = date.today().strftime('%Y-%m-%d')
        start_date = time.strftime('%Y-%m-%d', time.localtime(now - tf))

        if not isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
            print = builtins.print
            print(colored('''
              #####          #     #                                 
             #     # # ##### #     # #    # #####                    
             #       #   #   #     # #    # #    #                   
             #  #### #   #   ####### #    # #####                    
             #     # #   #   #     # #    # #    #                   
             #     # #   #   #     # #    # #    #                   
              #####  #   #   #     #  ####  #####                    
                                                                     
             #     #                                                 
             #  #  #   ##   #####  ####  #    # #    #   ##   #    # 
             #  #  #  #  #    #   #    # #    # ##  ##  #  #  ##   # 
             #  #  # #    #   #   #      ###### # ## # #    # # #  # 
             #  #  # ######   #   #      #    # #    # ###### #  # # 
             #  #  # #    #   #   #    # #    # #    # #    # #   ## 
              ## ##  #    #   #    ####  #    # #    # #    # #    #
                                                                 ''', 'magenta'))
            print('Version: {}\n'.format(a.__version__))
            print('Searching from {} to {}'.format(start_date, today))
            print('Importing rules...')
            rules_list = load_rules()
            print('{} rules loaded'.format(len(rules_list)))
        else:
            OUTPUT_LOGGER.log_info('GitHub Watchman started execution')
            OUTPUT_LOGGER.log_info('Version: {}'.format(a.__version__))
            OUTPUT_LOGGER.log_info('Importing rules...')
            rules_list = load_rules()
            OUTPUT_LOGGER.log_info('{} rules loaded'.format(len(rules_list)))
            print = OUTPUT_LOGGER.log_info

        if everything:
            print(colored('Getting everything...', 'magenta'))
            for rule in rules_list:
                if 'code' in rule.get('scope'):
                    search(connection, rule, tf, 'code')
                if 'commits' in rule.get('scope'):
                    search(connection, rule, tf, 'commits')
                if 'issues' in rule.get('scope'):
                    search(connection, rule, tf, 'issues')
                if 'repositories' in rule.get('scope'):
                    search(connection, rule, tf, 'repositories')
        else:
            if code:
                print(colored('Searching blobs', 'magenta'))
                for rule in rules_list:
                    if 'code' in rule.get('scope'):
                        search(connection, rule, tf, 'code')
            if commits:
                print(colored('Searching commits', 'magenta'))
                for rule in rules_list:
                    if 'commits' in rule.get('scope'):
                        search(connection, rule, tf, 'commits')
            if issues:
                print(colored('Searching issues', 'magenta'))
                for rule in rules_list:
                    if 'issues' in rule.get('scope'):
                        search(connection, rule, tf, 'issues')
            if repositories:
                print(colored('Searching repositories', 'magenta'))
                for rule in rules_list:
                    if 'repositories' in rule.get('scope'):
                        search(connection, rule, tf, 'repositories')

        print(colored('++++++Audit completed++++++', 'green'))

        deinit()

    except Exception as e:
        if isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
            print = OUTPUT_LOGGER.log_critical
        else:
            print = builtins.print

        print(colored(e, 'red'))


if __name__ == '__main__':
    main()
