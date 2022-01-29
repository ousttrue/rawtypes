import unittest
import pathlib
from rawtypes.parser import Parser

HEADER = pathlib.Path('C:/vcpkg/installed/x64-windows/include/imgui.h')


class TestImGuiParse(unittest.TestCase):

    def test_parse(self):
        parser = Parser([HEADER])
        parser.traverse()

        f = parser.get_function('GetIO')
        self.assertIsNotNone(f)

        # 'ImFontAtlas_AddFont'
        s = parser.get_struct('ImFontAtlas')
        self.assertIsNotNone(s)

        m = s.get_method('AddFont')
        self.assertIsNotNone(m)
