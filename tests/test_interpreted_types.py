import unittest
from rawtypes import interpreted_types
import _test_utils


class TestInterpretedTypes(unittest.TestCase):

    def test_primitive(self):
        void = _test_utils.parse_get_result_type('void func();')
        self.assertEqual(void, interpreted_types.primitive_types.VoidType())

        int8 = _test_utils.parse_get_result_type('char func();')
        self.assertEqual(int8, interpreted_types.primitive_types.Int8Type())

        int16 = _test_utils.parse_get_result_type('short func();')
        self.assertEqual(int16, interpreted_types.primitive_types.Int16Type())

        int32 = _test_utils.parse_get_result_type('int func();')
        self.assertEqual(int32, interpreted_types.primitive_types.Int32Type())

        int64 = _test_utils.parse_get_result_type('long long func();')
        self.assertEqual(int64, interpreted_types.primitive_types.Int64Type())

        uint8 = _test_utils.parse_get_result_type('unsigned char func();')
        self.assertEqual(uint8, interpreted_types.primitive_types.UInt8Type())

        uint16 = _test_utils.parse_get_result_type('unsigned short func();')
        self.assertEqual(
            uint16, interpreted_types.primitive_types.UInt16Type())

        uint32 = _test_utils.parse_get_result_type('unsigned int func();')
        self.assertEqual(
            uint32, interpreted_types.primitive_types.UInt32Type())

        uint64 = _test_utils.parse_get_result_type(
            'unsigned long long func();')
        self.assertEqual(
            uint64, interpreted_types.primitive_types.UInt64Type())

        float32 = _test_utils.parse_get_result_type('float func();')
        self.assertEqual(
            float32, interpreted_types.primitive_types.FloatType())

        float64 = _test_utils.parse_get_result_type('double func();')
        self.assertEqual(
            float64, interpreted_types.primitive_types.DoubleType())

    def test_size_t(self):
        size_t = _test_utils.parse_get_result_type('''
#include <stddef.h>
size_t func();
''')
        self.assertEqual(
            size_t, interpreted_types.primitive_types.SizeType())

    def test_pointer(self):
        int32 = _test_utils.parse_get_param_type(0, 'void func(int p0);')
        self.assertEqual(int32, interpreted_types.primitive_types.Int32Type())

        p = _test_utils.parse_get_param_type(0, 'void func(float *p0);')
        self.assertEqual(p, interpreted_types.PointerType(
            interpreted_types.primitive_types.FloatType()))

        # inner const
        const_p = _test_utils.parse_get_param_type(
            0, 'void func(const float *p0);')
        self.assertEqual(const_p, interpreted_types.PointerType(
            interpreted_types.primitive_types.FloatType(is_const=True)))

        # outer const
        p_const = _test_utils.parse_get_param_type(
            0, 'void func(float * const p0);')
        p_const_base = interpreted_types.primitive_types.FloatType()
        self.assertEqual(p_const, interpreted_types.PointerType(
            p_const_base, is_const=True))

        # inner const ref
        ref = _test_utils.parse_get_param_type(
            0, 'void func(const float &p0);')
        self.assertEqual(ref, interpreted_types.ReferenceType(
            interpreted_types.primitive_types.FloatType(is_const=True)))

        # double pointer
        pp = _test_utils.parse_get_param_type(0, 'void func(float **p0);')
        self.assertEqual(pp, interpreted_types.PointerType(
            interpreted_types.PointerType(interpreted_types.primitive_types.FloatType())))

    def test_typedef(self):
        typedef = _test_utils.parse_get_param_type(0, '''typedef int INT
        void func(INT p0);
        ''')
        assert isinstance(typedef, interpreted_types.TypedefType)
        self.assertIsInstance(
            typedef, interpreted_types.TypedefType)
        self.assertIsInstance(
            typedef.resolve(), interpreted_types.primitive_types.Int32Type)

        const_p = _test_utils.parse_get_param_type(0, '''
        struct Some{
            int value;
        };
        typedef Some SOME;
        void func(const SOME *p0);
        ''')

        assert isinstance(const_p, interpreted_types.PointerType)
        self.assertIsInstance(const_p, interpreted_types.PointerType)
        typedef = const_p.base
        assert isinstance(typedef, interpreted_types.TypedefType)
        struct_type = typedef.base
        assert isinstance(struct_type, interpreted_types.StructType)

# typedef

# struct

# function pointer


if __name__ == '__main__':
    unittest.main()
