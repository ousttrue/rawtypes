import unittest
import _test_utils
from rawtypes.parser import Parser

SRC = '''
void add(int a, inb b);

void default_bool(bool enable = true, bool disable = false);
'''


class TestParser(unittest.TestCase):

    def test_parse(self):
        parser = Parser.parse_source(SRC)

        f = parser.get_function('add')
        self.assertIsNotNone(f)

        f = parser.get_function('default_bool')
        self.assertIsNotNone(f)
        enable = f.params[0]
        disable = f.params[1]
        pass
