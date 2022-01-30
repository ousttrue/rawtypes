from rawtypes.clang import cindex
from .basetype import BaseType


class TypedefType(BaseType):
    def result_typing(self, pyi: bool) -> str:
        return self.name

    @property
    def ctypes_type(self) -> str:
        # TODO:
        return 'ctypes.c_void_p'  # function pointer

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return name + default_value

    def cdef_param(self, indent: str, i: int, name: str) -> str:

        return f'''{indent}# {self}
{indent}cdef impl.{self.name} p{i} = <impl.{self.name}><uintptr_t>{name}
'''

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}return {call}
'''

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if default_value:
            return f'{indent}{self.name} p{i} = t{i} ? ctypes_get_pointer<{self.name}>(t{i}) : {default_value};\n'
        else:
            return f'{indent}{self.name} p{i} = ctypes_get_pointer<{self.name}>(t{i});\n'

    def py_value(self, value: str) -> str:
        return self.base.py_value(value)


class StructType(BaseType):
    cursor: cindex.Cursor

    def __init__(self, name: str, cursor: cindex.Cursor, is_const=False, is_wrap_type=False):
        if name.startswith('struct '):
            name = name[7:]
        super().__init__(name, is_const=is_const)
        self.cursor = cursor
        self.is_wrap_type = is_wrap_type

    @property
    def ctypes_type(self) -> str:
        name = self.cursor.spelling
        if name:
            return name
        # anonymous
        return f'_{self.cursor.hash}'

    def result_typing(self, pyi: bool) -> str:
        return self.cursor.spelling

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return name + default_value

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        return f'''{indent}# {self}
{indent}cdef p{i} = {name}
'''

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}cdef void* value = <void*>{call}
{indent}return ctypes.c_void_p(value)
'''

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if default_value:
            raise NotImplementedError()
        else:
            return f'{indent}{self.name} *p{i} = ctypes_get_pointer<{self.name}*>(t{i});\n'

    def cpp_call_name(self, i: int):
        return f'*p{i}'

    def py_value(self, value: str) -> str:
        if not self.is_wrap_type:
            raise NotImplemented("return by value. but no python type")
        return f'ctypes_copy({value}, "{self.name}", "nanovg")'


class EnumType(BaseType):
    def __init__(self, name: str):
        super().__init__(name)

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: int{default_value}'

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        enum_name = self.name.split('::')[-1]
        return f'{indent}cdef impl.{enum_name} p{i} = <impl.{enum_name}>{name}\n'

    @property
    def result_typing(self) -> str:
        return 'int'

    def cdef_result(self, indent: str, call: str) -> str:
        return f'{indent}{call}\n'
