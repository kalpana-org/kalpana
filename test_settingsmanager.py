import unittest
from settingsmanager import parse_terminal_setting, valid_setting,\
                            get_auto_setting_acronym


class ParseTerminalSettingTest(unittest.TestCase):

    def test_bool(self):
        trues = ['y', '1', 'true', 'Y', 'True', 'TRUE']
        falses = ['n', '0', 'false', 'N', 'False', 'FALSE']
        l = [(x, True) for x in trues] + [(x, False) for x in falses]
        for n, x in enumerate(l):
            with self.subTest(i=n):
                self.assertEqual(parse_terminal_setting(x[0], bool), x[1])

    def test_invalid_bool(self):
        l = ['no', 'yes', 'x', '10']
        for n, x in enumerate(l):
            with self.subTest(i=n):
                self.assertIsNone(parse_terminal_setting(x, bool))

    def test_int(self):
        l = ['10', '1298', '-50']
        for n, x in enumerate(l):
            with self.subTest(i=n):
                self.assertEqual(parse_terminal_setting(x, int), int(x))

    def test_invalid_int(self):
        l = ['10.1', 'x', '-0.05', 'blooop']
        for n, x in enumerate(l):
            with self.subTest(i=n):
                self.assertIsNone(parse_terminal_setting(x, int))

    def test_float(self):
        l = ['10.0', '1298', '-0.50', '-99.9']
        for n, x in enumerate(l):
            with self.subTest(i=n):
                self.assertEqual(parse_terminal_setting(x, float), float(x))

    def test_invalid_float(self):
        l = ['x', 'blooop']
        for n, x in enumerate(l):
            with self.subTest(i=n):
                self.assertIsNone(parse_terminal_setting(x, float))

    def test_no_type(self):
        l = ['10.0', 'arst', 'jinz tai lorem ipsum']
        for n, x in enumerate(l):
            with self.subTest(i=n):
                self.assertEqual(parse_terminal_setting(x, None), x)


class ValidSettingTest(unittest.TestCase):

    def setUp(self):
        self.setting_types = {
            'automatic': {
                'testbool': bool,
                'testfloat': float
            },
            'manual': {
                'testint': int,
                'testnope': None
            }
        }

    def test_valid_bool(self):
        self.assertEqual(valid_setting('testbool', True, self.setting_types), True)

    def test_invalid_bool(self):
        self.assertEqual(valid_setting('testbool', 'true', self.setting_types), False)

    def test_valid_int(self):
        self.assertEqual(valid_setting('testint', 189, self.setting_types), True)

    def test_invalid_int(self):
        self.assertEqual(valid_setting('testint', 'no', self.setting_types), False)

    def test_valid_float(self):
        self.assertEqual(valid_setting('testfloat', 12.3, self.setting_types), True)

    def test_invalid_float(self):
        self.assertEqual(valid_setting('testfloat', 12, self.setting_types), False)

    def test_notype(self):
        self.assertEqual(valid_setting('testnope', 'Haha', self.setting_types), True)

    def test_notype(self):
        self.assertEqual(valid_setting('testnope', 'Haha', self.setting_types), True)

    def test_both_subdicts(self):
        setting_types = {
            'automatic': {
                'test1auto': None
            },
            'manual': {
                'test2manual': None
            }
        }
        with self.subTest(i=0, msg='Testing automatic subdict'):
            self.assertEqual(valid_setting('test1auto', '', setting_types), True)
        with self.subTest(i=1, msg='Testing manual subdict'):
            self.assertEqual(valid_setting('test2manual', '', setting_types), True)

    def test_empty_automatic(self):
        setting_types = {
            'automatic': {},
            'manual': {
                'test': None
            }
        }
        self.assertEqual(valid_setting('test', '', setting_types), True)

    def test_empty_manual(self):
        setting_types = {
            'automatic': {
                'test': None
            },
            'manual': {}
        }
        self.assertEqual(valid_setting('test', '', setting_types), True)


class GetAutoSettingAcronymTest(unittest.TestCase):

    def test_default(self):
        default_config = {
          "automatic": {
            "Auto-Indent": False,
            "Line Numbers": False,
            "open in New Window": False,
            "Vertical Scrollbar": "on",
            "Animate Terminal Output": False,
            "Terminal Animation Interval": 5,
            "max Page Width": 1000,
            "Show WordCount in titlebar": False
          }
        }
        correct_result = {
            "ai": "Auto-Indent",
            "ln": "Line Numbers",
            "nw": "open in New Window",
            "vs": "Vertical Scrollbar",
            "ato": "Animate Terminal Output",
            "tai": "Terminal Animation Interval",
            "pw": "max Page Width",
            "swc": "Show WordCount in titlebar"
        }
        result = get_auto_setting_acronym(default_config)
        self.assertEqual(result, correct_result)

    def test_no_acronym(self):
        default_config = {
          "automatic": {
            "Auto-Indent": False,
            "line numbers": False
          }
        }
        with self.assertRaisesRegex(Exception, '(?i)config'):
            get_auto_setting_acronym(default_config)

    def test_empty_config(self):
        result = get_auto_setting_acronym({'automatic':{}})
        self.assertEqual(result, {})