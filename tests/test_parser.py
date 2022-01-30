import unittest
import pathlib
import rawtypes.clang_util
from rawtypes.parser import Parser, Header

SRC = '''
void add(int a, inb b);

void add(int a, int b)
{
    return a+b;
}
'''


class TestParser(unittest.TestCase):

    def test_parse(self):
        parser = Parser(
            [pathlib.Path('C:/vcpkg/installed/x64-windows/include/imgui.h')])
        parser.traverse()

        f = parser.get_function('GetIO')
        self.assertIsNotNone(f)
