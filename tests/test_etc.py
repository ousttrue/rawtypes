import unittest
import ctypes
import pathlib
from rawtypes.generator.cpp_writer import to_c_function
import rawtypes.generator.generator
from rawtypes.parser.header import Header
from rawtypes.parser.typewrap import TypeWrap
import logging
logging.basicConfig(level=logging.DEBUG)
HERE = pathlib.Path(__file__).absolute().parent


class TestEtc(unittest.TestCase):
    def test_clang_getNullCursor(self):
        header = pathlib.Path(
            'C:/vcpkg/installed/x64-windows/include/GL/glew.h')

        generator = rawtypes.generator.generator.Generator(
            Header(header, include_dirs=[header.parent.parent])
        )

        f = generator.parser.get_function('glColor3bv')
        self.assertIsNotNone(f)

        params = f.params
        i, p0 = params[0]
        t = generator.type_manager.from_cursor(p0.type, p0.cursor)
        self.assertTrue(t.base.is_const)

        pp = generator.type_manager.get_params('', f)

        s = to_c_function(f, generator.env, generator.type_manager)
        print(s)
