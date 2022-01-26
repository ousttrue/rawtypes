import unittest
import ctypes
import pathlib
import rawtypes.generator
from rawtypes.header import Header
HERE = pathlib.Path(__file__).absolute().parent

CINDEX_HEADER = pathlib.Path("C:/Program Files/LLVM/include/clang-c/Index.h")


class TestGenerator(unittest.TestCase):

    def test_generator(self):
        generator = rawtypes.generator.Generator(Header(CINDEX_HEADER))
        generator.generate(HERE.parent / 'tmp')

        # struct 値渡し
        # struct 値返し
