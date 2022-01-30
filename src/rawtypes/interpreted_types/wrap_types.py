import io
from .basetype import BaseType
from .pointer_types import PointerType, ReferenceType


class PointerToStructType(PointerType):
    def __init__(self, base: BaseType, is_const: bool, is_wrap_type: bool):
        super().__init__(base, is_const)
        self.is_wrap_type = is_wrap_type

    @property
    def ctypes_type(self) -> str:
        if not self.base:
            raise RuntimeError()
        return f'{self.base.name}'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", ctypes.c_void_p), # {self}'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: {self.ctypes_type}{default_value}'

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        return f'''{indent}# {self}
{indent}cdef impl.{self.ctypes_type} *p{i} = NULL
{indent}if {name}:
{indent}    p{i} = <impl.{self.ctypes_type}*><uintptr_t>ctypes.addressof({name})
'''

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}cdef impl.{self.ctypes_type} *value = {call}
{indent}if value:
{indent}    return ctypes.cast(<uintptr_t>value, ctypes.POINTER({self.ctypes_type}))[0]
'''

    def result_typing(self, pyi: bool) -> str:
        return f'{self.ctypes_type}'

    def py_value(self, value: str) -> str:
        if self.is_wrap_type:
            return f'ctypes_cast(c_void_p({value}), "{self.base.name}", "imgui")'
        else:
            return f'c_void_p({value})'


class ReferenceToStructType(ReferenceType):
    def __init__(self, base: BaseType, is_const: bool, is_wrap_type: bool):
        super().__init__(base, is_const)
        self.is_wrap_type = is_wrap_type

    @property
    def ctypes_type(self) -> str:
        if not self.base:
            raise RuntimeError()
        return f'{self.base.name}'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", ctypes.c_void_p), # {self}'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: {self.ctypes_type}{default_value}'

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        return f'''{indent}# {self}
{indent}cdef {self.const_prefix}impl.{self.ctypes_type} *p{i} = NULL
{indent}if isinstance({name}, ctypes.Structure):
{indent}    p{i} = <{self.const_prefix}impl.{self.ctypes_type} *><uintptr_t>ctypes.addressof({name})
'''

    def call_param(self, i: int) -> str:
        return f'p{i}[0]'

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}cdef {self.const_prefix}impl.{self.ctypes_type} *value = &{call}
{indent}return ctypes.cast(ctypes.c_void_p(<uintptr_t>value), ctypes.POINTER({self.ctypes_type}))[0]
'''

    def result_typing(self, pyi: bool) -> str:
        return f'{self.ctypes_type}'

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if default_value:
            return f'''{indent}{self.name} default_value{i} = {default_value};
{indent}{self.base.name} *p{i} = t{i} ? ctypes_get_pointer<{self.base.name}*>(t{i}) : &default_value{i};
'''
        else:
            return f'{indent}{self.base.name} *p{i} = ctypes_get_pointer<{self.base.name}*>(t{i});\n'

    def cpp_result(self, indent: str, call: str) -> str:
        sio = io.StringIO()
        sio.write(f'{indent}// {self}\n')
        sio.write(f'{indent}auto value = &{call};\n')
        sio.write(f'{indent}auto py_value = c_void_p(value);\n')
        if self.is_wrap_type:
            sio.write(
                f'{indent}py_value = ctypes_cast(py_value, "{self.base.name}", "imgui");\n')
        sio.write(f'{indent}return py_value;\n')
        return sio.getvalue()
