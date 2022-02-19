from .basetype import BaseType


class StringType(BaseType):
    '''
    http://docs.cython.org/en/latest/src/tutorial/strings.html#c-strings
    '''

    def __init__(self):
        super().__init__('std::string')

    @property
    def ctypes_type(self) -> str:
        return 'string'

    def py_param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: str{default_value}'

    def cpp_to_py(self, value: str):
        return f'py_string({value})'


class CStringType(BaseType):
    def __init__(self):
        super().__init__('const char *')

    @property
    def ctypes_type(self) -> str:
        return 'ctypes.c_void_p'

    def py_param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: Union[bytes, str]{default_value}'

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if not default_value:
            default_value = 'nullptr'
        return f'{indent}const char *p{i} = get_cstring(t{i}, {default_value});\n'

    def cpp_to_py(self, value: str) -> str:
        return f'PyUnicode_FromString({value})'


class CharPointerType(BaseType):
    def __init__(self):
        super().__init__('const char *')

    @property
    def ctypes_type(self) -> str:
        return 'ctypes.c_void_p'

    def py_param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: Union[bytes, str]{default_value}'

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        return f'{indent}char *p{i} = ctypes_get_pointer<char *>(t{i});\n'

    def cpp_to_py(self, value: str) -> str:
        raise NotImplementedError()
