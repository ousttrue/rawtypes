import logging
import ctypes
import unittest

from jinja2 import Environment, PackageLoader
from rawtypes.generator.py_writer import to_ctypes_iter
from rawtypes.interpreted_types import TypeManager
from rawtypes.parser.struct_cursor import WrapFlags
from rawtypes.generator.cpp_writer import to_c_function
import rawtypes.generator.python_generator
from rawtypes.parser.header import Header
from rawtypes.parser import parse
from . import VCPKG_INCLUDE
logging.basicConfig(level=logging.DEBUG)

GLEW_HEADER = VCPKG_INCLUDE / 'GL/glew.h'
if GLEW_HEADER.exists():

    class TestEtc(unittest.TestCase):
        def test_glColor3bv(self):

            generator = rawtypes.generator.python_generator.PythonGenerator(
                Header(GLEW_HEADER, include_dirs=[GLEW_HEADER.parent.parent])
            )

            f = generator.parser.get_function('glColor3bv')
            self.assertIsNotNone(f)

            # macro included !
            # params = f.params
            # p0 = params[0]
            # t = generator.type_manager.from_cursor(p0.type, p0.cursor)
            # self.assertTrue(t.base.is_const)

            # pp = generator.type_manager.get_params('', f)

            # s = to_c_function(generator.env, f, generator.type_manager)
            # print(s)
