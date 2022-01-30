from typing import Optional
from .basetype import BaseType
from .primitive_types import PrimitiveType, VoidType


def add_impl(base: Optional[BaseType]) -> str:
    if not base:
        raise RuntimeError()

    # Find types that don't require impl
    match base:
        case PrimitiveType() | VoidType():
            return base.name
        case PointerType():
            match base.base:
                case PrimitiveType() | VoidType():
                    return base.name

    return 'impl.' + base.name


class PointerType(BaseType):
    def __init__(self, base: BaseType, is_const=False):
        super().__init__(base.name + '*', base=base, is_const=is_const)

    def result_typing(self, pyi: bool) -> str:
        return 'ctypes.c_void_p'

    @property
    def ctypes_type(self) -> str:
        if not self.base:
            raise RuntimeError()
        return f'ctypes.Array'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", ctypes.c_void_p), # {self}'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: Union[ctypes.c_void_p, ctypes.Array, ctypes.Structure]{default_value}'

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        base_name = add_impl(self.base)
        return f'''{indent}# {self}
{indent}cdef {base_name} *p{i};
{indent}if isinstance({name}, ctypes.c_void_p):
{indent}    p{i} = <{base_name} *><uintptr_t>({name}.value)
{indent}if isinstance({name}, (ctypes.Array, ctypes.Structure)):
{indent}    p{i} = <{base_name} *><uintptr_t>ctypes.addressof({name})
'''

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}cdef void* value = <void*>{call}
{indent}return ctypes.c_void_p(<uintptr_t>value)
'''

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if default_value:
            return f'{indent}{self.base.const_prefix}{self.base.name} *p{i} = t{i} ? ctypes_get_pointer<{self.base.const_prefix}{self.base.name}*>(t{i}) : {default_value};\n'
        else:
            return f'{indent}{self.base.const_prefix}{self.base.name} *p{i} = ctypes_get_pointer<{self.base.const_prefix}{self.base.name}*>(t{i});\n'

    def py_value(self, value: str) -> str:
        return f'c_void_p({value})'


class ReferenceType(PointerType):
    base: BaseType

    def __init__(self, base: BaseType, is_const=False):
        super().__init__(base, is_const)
        self.name = base.name + '&'

    def result_typing(self, pyi: bool) -> str:
        return 'ctypes.c_void_p'

    @property
    def ctypes_type(self) -> str:
        return 'ctypes.Array'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", ctypes.c_void_p), # {self}'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: {self.ctypes_type}{default_value}'

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        base_name = add_impl(self.base)
        return f'''{indent}# {self}
{indent}cdef {base_name} *p{i} = <{base_name} *><void*><uintptr_t>(ctypes.addressof({name}))
'''

    def call_param(self, i: int) -> str:
        return f'p{i}[0]'

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}cdef void* value = <void*>&{call}
{indent}return ctypes.c_void_p(<uintptr_t>value)
'''

    def cpp_call_name(self, i: int):
        return f'*p{i}'

    def cpp_result(self, indent: str, call: str) -> str:
        return f'''{indent}// {self}
{indent}auto *value = &{call};
{indent}auto py_value = c_void_p(value);
{indent}return py_value;
'''


class ArrayType(PointerType):
    size: int

    def __init__(self, base: BaseType, size: int, is_const=False):
        super().__init__(base, is_const)
        self.size = size
        self.name = f'{base.name}[{size}]'

    @property
    def ctypes_type(self) -> str:
        if not self.base:
            raise RuntimeError()
        return f'{self.base.ctypes_type} * {self.size}'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", {self.ctypes_type}), # {self}'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: ctypes.Array{default_value}'

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        base_name = add_impl(self.base)
        return f'''{indent}# {self}
{indent}cdef {base_name} *p{i} = <{base_name}*><void*><uintptr_t>ctypes.addressof({name})
'''

    def result_typing(self, pyi: bool) -> str:
        return 'ctypes.c_void_p'


class RefenreceToStdArrayType(BaseType):
    size: int

    def __init__(self, base: BaseType, size: int, is_const=False):
        super().__init__(f'{base.name}[{size}]', base=base, is_const=is_const)
        self.size = size

    @property
    def ctypes_type(self) -> str:
        if not self.base:
            raise RuntimeError()
        return f'{self.base.ctypes_type} * {self.size}'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: ctypes.Array{default_value}'

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        type_name = f'{self.const_prefix}{self.base.name}{self.size}'
        return f'''{indent}# {self}
{indent}cdef {type_name} *p{i} = NULL
{indent}if isinstance({name}, (ctypes.Array, ctypes.Structure)):
{indent}    p{i} = <{type_name}*><uintptr_t>ctypes.addressof({name})
'''

    def call_param(self, i: int) -> str:
        return f'p{i}[0]'

    def result_typing(self, pyi: bool) -> str:
        return 'ctypes.c_void_p'
