import unittest
import ctypes
import pathlib
import rawtypes.generator
from rawtypes.header import Header
import logging
logging.basicConfig(level=logging.DEBUG)
HERE = pathlib.Path(__file__).absolute().parent

CINDEX_HEADER = pathlib.Path("C:/Program Files/LLVM/include/clang-c/Index.h")


class TestGenerator(unittest.TestCase):

    def test_generator(self):
        generator = rawtypes.generator.Generator(
            Header(CINDEX_HEADER, include_dirs=[CINDEX_HEADER.parent.parent]))

        parser = generator.parser

        # CINDEX_LINKAGE CXCursor clang_getNullCursor(void);
        f = parser.get_function('clang_getNullCursor')
        self.assertIsNotNone(f)

        # generator.generate(HERE.parent / 'tmp')

        # struct 値渡し
        # struct 値返し
