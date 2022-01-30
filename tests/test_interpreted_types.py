from typing import Callable, Tuple
import unittest
from rawtypes import interpreted_types
from rawtypes.clang import cindex
from rawtypes.generator.generator import Generator

generator = Generator()


def parse(src: str) -> cindex.TranslationUnit:
    from rawtypes import clang_util
    unsaved = clang_util.Unsaved('tmp.h', src)
    return clang_util.get_tu('tmp.h', unsaved=[unsaved])


def first(tu: cindex.TranslationUnit, pred: Callable[[cindex.Cursor], bool]) -> cindex.Cursor:
    for cursor in tu.cursor.get_children():  # type: ignore
        if pred(cursor):
            return cursor

    raise RuntimeError()


def parse_get_func(src: str) -> Tuple[cindex.TranslationUnit, cindex.Cursor]:
    tu = parse(src)
    return tu, first(tu, lambda cursor: cursor.kind ==
                     cindex.CursorKind.FUNCTION_DECL)


def parse_get_result_type(src: str) -> interpreted_types.BaseType:
    tu, c = parse_get_func(src)
    return generator.type_manager.from_cursor(c.result_type, c)


def parse_get_param_type(i: int, src: str) -> interpreted_types.BaseType:
    tu, c = parse_get_func(src)
    from rawtypes.parser.type_context import ParamContext
    p = ParamContext.get_function_params(c)[i].cursor
    return generator.type_manager.from_cursor(p.type, p)


class TestInterpretedTypes(unittest.TestCase):

    def test_primitive(self):
        void = parse_get_result_type('void func();')
        self.assertEqual(void, interpreted_types.primitive_types.VoidType())

        int8 = parse_get_result_type('char func();')
        self.assertEqual(int8, interpreted_types.primitive_types.Int8Type())

        int16 = parse_get_result_type('short func();')
        self.assertEqual(int16, interpreted_types.primitive_types.Int16Type())

        int32 = parse_get_result_type('int func();')
        self.assertEqual(int32, interpreted_types.primitive_types.Int32Type())

        int64 = parse_get_result_type('long long func();')
        self.assertEqual(int64, interpreted_types.primitive_types.Int64Type())

        uint8 = parse_get_result_type('unsigned char func();')
        self.assertEqual(uint8, interpreted_types.primitive_types.UInt8Type())

        uint16 = parse_get_result_type('unsigned short func();')
        self.assertEqual(
            uint16, interpreted_types.primitive_types.UInt16Type())

        uint32 = parse_get_result_type('unsigned int func();')
        self.assertEqual(
            uint32, interpreted_types.primitive_types.UInt32Type())

        uint64 = parse_get_result_type('unsigned long long func();')
        self.assertEqual(
            uint64, interpreted_types.primitive_types.UInt64Type())

        float32 = parse_get_result_type('float func();')
        self.assertEqual(
            float32, interpreted_types.primitive_types.FloatType())

        float64 = parse_get_result_type('double func();')
        self.assertEqual(
            float64, interpreted_types.primitive_types.DoubleType())

        size_t = parse_get_result_type('size_t func();')
        self.assertEqual(
            size_t, interpreted_types.primitive_types.SizeType())

    def test_pointer(self):
        int32 = parse_get_param_type(0, 'void func(int p0);')
        self.assertEqual(int32, interpreted_types.primitive_types.Int32Type())

        p = parse_get_param_type(0, 'void func(float *p0);')
        self.assertEqual(p, interpreted_types.PointerType(
            interpreted_types.primitive_types.FloatType()))

        # inner const
        const_p = parse_get_param_type(0, 'void func(const float *p0);')
        self.assertEqual(const_p, interpreted_types.PointerType(
            interpreted_types.primitive_types.FloatType(is_const=True)))

        # outer const
        p_const = parse_get_param_type(0, 'void func(float * const p0);')
        p_const_base = interpreted_types.primitive_types.FloatType()
        self.assertEqual(p_const, interpreted_types.PointerType(
            p_const_base, is_const=True))

        # inner const ref
        ref = parse_get_param_type(0, 'void func(const float &p0);')
        self.assertEqual(ref, interpreted_types.ReferenceType(
            interpreted_types.primitive_types.FloatType(is_const=True)))

        # double pointer
        pp = parse_get_param_type(0, 'void func(float **p0);')
        self.assertEqual(pp, interpreted_types.PointerType(
            interpreted_types.PointerType(interpreted_types.primitive_types.FloatType())))

    def test_typedef(self):
        typedef = parse_get_param_type(0, '''typedef int INT
        void func(INT p0);
        ''')
        self.assertIsInstance(
            typedef, interpreted_types.primitive_types.Int32Type)

        const_p = parse_get_param_type(0, '''
        struct Some{
            int value;
        };
        typedef Some SOME;
        void func(const SOME *p0);
        ''')
        self.assertIsInstance(const_p, interpreted_types.PointerType)
        self.assertIsInstance(const_p.base, interpreted_types.StructType)
        self.assertIsNone(const_p.base.base)

# typedef

# struct

# function pointer


if __name__ == '__main__':
    unittest.main()
