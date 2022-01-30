import unittest
import pathlib

from jinja2 import Environment, PackageLoader
from rawtypes.generator.cpp_writer import to_c_method
from rawtypes.interpreted_types import TypeManager
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

        type_manager = TypeManager()
        env = Environment(
            loader=PackageLoader("rawtypes.generator"),
        )

        print(to_c_method(s.cursor, m, env, type_manager))
