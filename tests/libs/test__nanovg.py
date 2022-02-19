import logging
import ctypes
import unittest

from jinja2 import Environment, PackageLoader
from rawtypes.generator.py_writer import to_ctypes_iter
from rawtypes.interpreted_types import TypeManager
from rawtypes.interpreted_types.string import CharPointerType
from rawtypes.parser.struct_cursor import WrapFlags
from rawtypes.generator.cpp_writer import FunctionCustomization, to_c_function
import rawtypes.generator.generator
from rawtypes.parser.header import Header
from rawtypes.parser import parse

from . import VCPKG_INCLUDE

logging.basicConfig(level=logging.DEBUG)


class TestNanoVG(unittest.TestCase):
    def test_nanovg(self):
        header = VCPKG_INCLUDE / 'nanovg.h'
        parser = parse(header, include_dirs=[VCPKG_INCLUDE])

        s = parser.get_struct('NVGcolor')
        self.assertIsNotNone(s)

        fields = s.fields
        self.assertEqual(1, len(fields))

        type_manager = TypeManager()
        flag = WrapFlags('nanovg', 'NVGcolor', fields=True)

        env = Environment(
            loader=PackageLoader("rawtypes.generator"),
        )

        for src in to_ctypes_iter(env, s, flag, type_manager):
            print(src)
            l = {}
            exec(src, globals(), l)
            # print(l)
            for k, v in l.items():
                globals()[k] = v

        self.assertEqual(s.sizeof, ctypes.sizeof(v))

    def test_char_p(self):
        header = VCPKG_INCLUDE / 'nanovg.h'
        parser = parse(header, include_dirs=[VCPKG_INCLUDE])

        f = parser.get_function('nvgTextBreakLines')
        self.assertIsNotNone(f)

        env = Environment(
            loader=PackageLoader("rawtypes.generator"),
        )

        type_manager = TypeManager()
        s = to_c_function(env, f, type_manager, custom=FunctionCustomization('', {
            'string': CharPointerType(),
            'end': CharPointerType(),
        }))
        print(s)
