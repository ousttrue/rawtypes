from .basetype import BaseType, Tuple


class StrType(BaseType):
    @property
    def pyi_types(self) -> Tuple[str, ...]:
        return ('str', 'bytes', 'None')


class CppStringType(StrType):
    '''
    http://docs.cython.org/en/latest/src/tutorial/strings.html#c-strings
    '''

    def __init__(self):
        super().__init__('std::string')

    def cpp_to_py(self, value: str):
        return f'py_string({value})'


class CStringType(StrType):
    def __init__(self):
        super().__init__('const char *')

    @property
    def ctypes_type(self) -> str:
        return 'ctypes.c_void_p'

    @property
    def py_result(self) -> str:
        return 'str'

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if not default_value:
            default_value = 'nullptr'
        return f'{indent}const char *p{i} = get_cstring(t{i}, {default_value});\n'

    def cpp_to_py(self, value: str) -> str:
        return f'PyUnicode_FromString({value})'


class CharPointerType(BaseType):
    '''
    str, bytes を const char* ではなく、
    c_void_p を const char * として受け取りたい。

    例 const char *text = "abcd";
    auto end = text + strlen(text);

    some_func(text, end); // pointer for text range.
    '''

    def __init__(self, is_const: bool = False) -> None:
        super().__init__('const char *', is_const)

    @property
    def ctypes_type(self) -> str:
        return f'ctypes.c_void_p'

    def py_param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: Optional[ctypes.c_void_p]{default_value}'

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        return f'{indent}char *p{i} = ctypes_get_pointer<char *>(t{i});\n'

    def cpp_to_py(self, value: str) -> str:
        return f'c_void_p({value})'
