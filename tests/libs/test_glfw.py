import os
import pathlib
import platform
import unittest


HOME_DIR = pathlib.Path(os.environ['USERPROFILE'] if platform.system(
) == 'Windows' else os.environ['HOME'])
HEADER = HOME_DIR / ('ghq/github.com/glfw/glfw/include/GLFW/glfw3.h')
if HEADER.exists():

    class TestGlfwParse(unittest.TestCase):

        def test_parse(self):
            from rawtypes.parser import Parser
            parser = Parser.parse([HEADER])

            f = parser.get_function('glfwSetErrorCallback')
            self.assertIsNotNone(f)

            params = f.params

            self.assertEqual(1, len(params))

            from rawtypes.interpreted_types import TypeManager, TypedefType, PointerType, FunctionProto, VoidType, CStringType
            from rawtypes.interpreted_types.primitive_types import Int32Type
            type_manager = TypeManager()
            typedef = type_manager.to_type(params[0])

            self.assertEquals('GLFWerrorfun', typedef.name)
            assert isinstance(typedef, TypedefType)
            self.assertIsInstance(typedef, TypedefType)

            # typedef void (* GLFWerrorfun)(int error_code, const char* description);
            fp = typedef.base
            assert isinstance(fp, PointerType)

            f = fp.base
            assert isinstance(f,  FunctionProto)

            GLFWerrorfun = f.function
            self.assertIsInstance(type_manager.to_type(
                GLFWerrorfun.result), VoidType)
            params = GLFWerrorfun.params
            self.assertEquals(2, len(params))
            self.assertEquals('error_code', params[0].name)
            self.assertIsInstance(type_manager.to_type(params[0]), Int32Type)
            self.assertEquals('description', params[1].name)
            self.assertIsInstance(type_manager.to_type(params[1]), CStringType)
