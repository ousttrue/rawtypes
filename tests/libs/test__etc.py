import logging
import ctypes
import unittest
from rawtypes.generator.py_writer import to_ctypes
from rawtypes.interpreted_types import TypeManager
from rawtypes.parser.struct_cursor import WrapFlags
from rawtypes.generator.cpp_writer import to_c_function
import rawtypes.generator.generator
from rawtypes.parser.header import Header
from rawtypes.parser import parse
from . import VCPKG_INCLUDE
logging.basicConfig(level=logging.DEBUG)


class TestEtc(unittest.TestCase):
    def test_clang_getNullCursor(self):
        header = VCPKG_INCLUDE / 'GL/glew.h'

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

    def test_nanovg(self):
        header = VCPKG_INCLUDE / 'nanovg.h'
        parser = parse(header, include_dirs=[VCPKG_INCLUDE])

        s = parser.get_struct('NVGcolor')
        self.assertIsNotNone(s)

        fields = s.fields
        self.assertEqual(1, len(fields))

        type_manager = TypeManager()
        flag = WrapFlags('NVGcolor', fields=True)
        ct = to_ctypes(s, flag, type_manager)
        print(ct)
        self.assertEqual(s.sizeof, ctypes.sizeof(ct))
