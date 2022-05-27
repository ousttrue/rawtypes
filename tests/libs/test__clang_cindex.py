import unittest
import pathlib
import logging
from rawtypes.generator.cpp_writer import to_c_function
from rawtypes.parser.header import Header
from rawtypes.parser.struct_cursor import WrapFlags
import rawtypes.generator.python_generator

logging.basicConfig(level=logging.DEBUG)
HERE = pathlib.Path(__file__).absolute().parent

CINDEX_HEADER = pathlib.Path("C:/Program Files/LLVM/include/clang-c/Index.h")
if CINDEX_HEADER.exists():

    class TestGenerator(unittest.TestCase):
        def setUp(self) -> None:
            self.generator = rawtypes.generator.python_generator.PythonGenerator(
                Header(CINDEX_HEADER, include_dirs=[CINDEX_HEADER.parent.parent]))
            self.generator.type_manager.WRAP_TYPES.append(
                WrapFlags('clang', 'CXCursor', True)
            )

        def test_clang_getNullCursor(self):
            '''
            // return by value
            CINDEX_LINKAGE CXCursor clang_getNullCursor(void);
            '''
            f = self.generator.parser.get_function('clang_getNullCursor')
            self.assertIsNotNone(f)

            s = to_c_function(self.generator.env, f,
                              self.generator.type_manager)
            print(s)

        def test_clang_equalLocations(self):
            '''
            // param by value
            CINDEX_LINKAGE unsigned clang_equalLocations(CXSourceLocation loc1, CXSourceLocation loc2);
            '''
            f = self.generator.parser.get_function('clang_equalLocations')
            self.assertIsNotNone(f)

            s = to_c_function(self.generator.env, f,
                              self.generator.type_manager)
            print(s)

            params = f.params
            self.assertEqual(2, len(params))
