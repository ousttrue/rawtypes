import unittest
import _test_utils

SRC = '''
void add(int a, inb b);
'''


class TestParser(unittest.TestCase):

    def test_parse(self):
        f = _test_utils._parse_get_func(SRC)
        self.assertIsNotNone(f)
