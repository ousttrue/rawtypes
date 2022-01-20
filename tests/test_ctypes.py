import unittest
import ctypes


class TestCTypesTests(unittest.TestCase):

    def test_cast(self):
        class Num(ctypes.Structure):
            _fields_ = [
                ('value', ctypes.c_int)
            ]

        value = ctypes.c_int(123)
        p = ctypes.pointer(value)
        c = ctypes.cast(p, ctypes.POINTER(Num))
        self.assertEqual(123, c[0].value)

        pp = ctypes.addressof(c[0])
        x = ctypes.cast(ctypes.c_void_p(pp), ctypes.POINTER(Num))[0]
        print(pp)
        print(type(x))
        print(ctypes.addressof(x))


    def test_address(self):
        p = ctypes.c_void_p()
        self.assertIsInstance(p, ctypes.c_void_p)
        # self.assertEqual(ctypes.addressof(p), p.value)

        pp = ctypes.byref(p)
        # ctypes.addressof(pp)
        print(pp)
        # self.assertIsInstance(pp, ctypes.c_void_p)

        class f2(ctypes.Structure):
            _fields_ = [
                ('x', ctypes.c_float),
                ('y', ctypes.c_float),
            ]
        v = f2()
        self.assertIsInstance(v, ctypes.Structure)
        ctypes.addressof(v)

        a = (ctypes.c_int * 3)()
        self.assertIsInstance(a, ctypes.Array)
        ctypes.addressof(a)
        # ctypes.addressof(a[0])

    def test_function_type(self):
        def func(p):
            pass
        fp = ctypes.CFUNCTYPE(None, ctypes.c_void_p)(func)
        print(type(fp))
        print(type(fp.__class__))
        self.assertIsInstance(fp, ctypes._CFuncPtr)


if __name__ == '__main__':
    unittest.main()
