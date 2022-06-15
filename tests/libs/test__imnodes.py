import sys
import unittest
import pathlib
import platform
import os
from jinja2 import Environment, PackageLoader
from rawtypes.generator.cpp_writer import to_c_method
from rawtypes.interpreted_types import TypeManager, TypedefType, PointerType
from rawtypes.interpreted_types import primitive_types
from rawtypes.parser import Parser

HOME_DIR = pathlib.Path(os.environ['USERPROFILE'] if platform.system(
) == 'Windows' else os.environ['HOME'])
IMGUI_HEADER = HOME_DIR / ('ghq/github.com/ocornut/imgui/imgui.h')
HERE = pathlib.Path(__file__).absolute().parent
HEADER = HERE / 'srcs/ImNodes/ImNodes.h'
if IMGUI_HEADER.exists():
    class TestImGuiParse(unittest.TestCase):

        def test_parse(self):
            parser = Parser.parse(
                [HEADER, HEADER.parent / 'ImNodesEz.h'], include_dirs=[HEADER.parent, IMGUI_HEADER.parent])

            s = parser.get_struct('StyleVars')
            self.assertIsNotNone(s)

            type_manager = TypeManager()

            self.assertEqual(3, len(s.fields))
            f = s.fields[2]
            self.assertFalse(f.is_anonymous_field)
            self.assertTrue(f.is_anonymous_type)
            t = type_manager.to_type(f)
            print(f'{f.name}: {t}')
