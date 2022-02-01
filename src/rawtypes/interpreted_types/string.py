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

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: str{default_value}'

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        return f'''{indent}# {self}
{indent}cdef string p{i}
{indent}if isinstance({name}, bytes):
{indent}    p{i} = {name}
{indent}if isinstance({name}, str):
{indent}    pp{i} = {name}.encode('utf-8')
{indent}    p{i} = pp{i}
'''

    def result_typing(self, pyi: bool) -> str:
        return 'string'

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}return {call}
'''

    def py_value(self, value: str):
        return f'py_string({value})'


class CStringType(BaseType):
    def __init__(self):
        super().__init__('const char *')

    @property
    def ctypes_type(self) -> str:
        return 'ctypes.c_void_p'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: Union[bytes, str]{default_value}'

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        return f'''{indent}# {self}
{indent}cdef const char *p{i} = NULL;
{indent}if isinstance({name}, bytes):
{indent}    p{i} = <const char *>{name}
{indent}if isinstance({name}, str):
{indent}    pp{i} = {name}.encode('utf-8')
{indent}    p{i} = <const char *>pp{i}
'''

    def result_typing(self, pyi: bool) -> str:
        return 'bytes'

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}return {call}
'''

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if not default_value:
            default_value = 'nullptr'
        return f'{indent}const char *p{i} = get_cstring(t{i}, {default_value});\n'

    def py_value(self, value: str) -> str:
        return f'PyUnicode_FromString({value})'


class CharPointerType(BaseType):
    def __init__(self):
        super().__init__('const char *')

    @property
    def ctypes_type(self) -> str:
        return 'ctypes.c_void_p'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: Union[bytes, str]{default_value}'

    def result_typing(self, pyi: bool) -> str:
        raise NotImplementedError()

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        return f'{indent}char *p{i} = ctypes_get_pointer<char *>(t{i});\n'

    def py_value(self, value: str) -> str:
        raise NotImplementedError()
