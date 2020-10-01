import yaml
import os
import unittest
from pathlib import Path

RULES_PATH = (Path(__file__).parents[1] / 'watchman/rules').resolve()


def load_rules():
    rules = []
    for file in os.scandir(RULES_PATH):
        if file.name.endswith('.yaml'):
            with open(file) as yaml_file:
                rule = yaml.safe_load(yaml_file)
                if rule.get('enabled'):
                    rules.append(rule)
    return rules


def check_yaml(rule):
    try:
        yaml_rule = yaml.safe_load(rule)
    except:
        return False
    return True


class TestEmail(unittest.TestCase):
    def test_rule_format(self):
        """Check rules are properly formed YAML ready to be ingested"""

        for file in os.scandir(RULES_PATH):
            if file.name.endswith('.yaml'):
                with open(file) as yaml_file:
                    self.assertTrue(check_yaml(yaml_file.read()), msg='Malformed YAML: {}'.format(yaml_file.name))

    def test_rule_matching_cases(self):
        """Test that the match case strings match the regex. Skip if the match case is 'blank'"""

        rules_list = load_rules()
        for rule in rules_list:
            for test_case in rule.get('test_cases').get('match_cases'):
                if not test_case == 'blank':
                    self.assertRegex(test_case, rule.get('pattern'), msg='Regex does not detect given match case')

    def test_rule_failing_cases(self):
        """Test that the fail case strings don't match the regex. Skip if the fail case is 'blank'"""

        rules_list = load_rules()
        for rule in rules_list:
            for test_case in rule.get('test_cases').get('fail_cases'):
                if not test_case == 'blank':
                    self.assertNotRegex(test_case, rule.get('pattern'),
                                        msg='Regex does detect given failure case, it should '
                                            'not')


if __name__ == '__main__':
    unittest.main()
