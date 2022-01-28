import unittest
import ctypes
import pathlib
import rawtypes.generator
from rawtypes.header import Header
from rawtypes.interpreted_types import WrapFlags
import logging
logging.basicConfig(level=logging.DEBUG)
HERE = pathlib.Path(__file__).absolute().parent

CINDEX_HEADER = pathlib.Path("C:/Program Files/LLVM/include/clang-c/Index.h")


class TestGenerator(unittest.TestCase):

    def test_generator(self):
        generator = rawtypes.generator.Generator(
            Header(CINDEX_HEADER, include_dirs=[CINDEX_HEADER.parent.parent]))

        # CINDEX_LINKAGE CXCursor clang_getNullCursor(void);
        f = generator.parser.get_function('clang_getNullCursor')
        self.assertIsNotNone(f)

        generator.type_manager.WRAP_TYPES.append(
            WrapFlags('CxCursor', True)
        )

        s = f.to_c_function(generator.type_manager)
        print(s)

        # generator.generate(HERE.parent / 'tmp')

        # struct 値渡し
        # struct 値返し
