import sys
import unittest
import pathlib
import platform
import os
from jinja2 import Environment, PackageLoader
from rawtypes.generator.cpp_writer import to_c_method
from rawtypes.interpreted_types import TypeManager
from rawtypes.parser import Parser

HOME_DIR = pathlib.Path(os.environ['USERPROFILE'] if platform.system(
) == 'Windows' else os.environ['HOME'])
HEADER = HOME_DIR / ('ghq/github.com/ocornut/imgui/imgui.h')

if HEADER.exists():
    class TestImGuiParse(unittest.TestCase):

        def test_parse(self):
            parser = Parser.parse([HEADER])

            f = parser.get_function('CreateContext')
            self.assertIsNotNone(f)
            params = f.params
            self.assertEqual(1, len(params))
            self.assertEqual('NULL', params[0].default_value.cpp_value)

            f = parser.get_function('GetIO')
            self.assertIsNotNone(f)

            f = parser.get_function('BeginChild')
            self.assertIsNotNone(f)

            f = parser.get_function('ProgressBar')
            self.assertIsNotNone(f)
            params = f.params
            self.assertEqual(3, len(params))
            self.assertEqual('NULL', params[2].default_value.cpp_value)

            # cehck size_t
            f = parser.get_function('SaveIniSettingsToMemory')
            self.assertIsNotNone(f)
            params = f.params
            self.assertEqual(1, len(params))
            type_manager = TypeManager()
            p = type_manager.to_type(params[0])
            self.assertEqual('size_t', p.base.name)

            # 'ImFontAtlas_AddFont'
            s = parser.get_struct('ImFontAtlas')
            self.assertIsNotNone(s)

            m = s.get_method('AddFont')
            self.assertIsNotNone(m)

            type_manager = TypeManager()
            env = Environment(
                loader=PackageLoader("rawtypes.generator"),
            )

            print(to_c_method(env, s.cursor, m, type_manager))
