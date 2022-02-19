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
    def __init__(self, base: BaseType, is_const=False, name_override=None):
        super().__init__(name_override if name_override else base.name + '*', is_const)
        if not base:
            raise RuntimeError()
        self.base = base

    @property
    def ctypes_type(self) -> str:
        return f'ctypes.Array'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", ctypes.c_void_p), # {self}'

    def py_param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: Union[ctypes.c_void_p, ctypes.Array, ctypes.Structure]{default_value}'

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if default_value:
            return f'{indent}{self.base.const_prefix}{self.base.name} *p{i} = t{i} ? ctypes_get_pointer<{self.base.const_prefix}{self.base.name}*>(t{i}) : {default_value};\n'
        else:
            return f'{indent}{self.base.const_prefix}{self.base.name} *p{i} = ctypes_get_pointer<{self.base.const_prefix}{self.base.name}*>(t{i});\n'

    def cpp_to_py(self, value: str) -> str:
        return f'c_void_p({value})'


class ReferenceType(PointerType):
    base: BaseType

    def __init__(self, base: BaseType, is_const=False):
        super().__init__(base, is_const, name_override=base.name + '&')

    @property
    def ctypes_type(self) -> str:
        return 'ctypes.Array'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", ctypes.c_void_p), # {self}'

    def py_param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: {self.ctypes_type}{default_value}'

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
        super().__init__(base, is_const, name_override=f'{base.name}[{size}]')
        self.size = size

    @property
    def ctypes_type(self) -> str:
        if not self.base:
            raise RuntimeError()
        return f'{self.base.ctypes_type} * {self.size}'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", {self.ctypes_type}), # {self}'

    def py_param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: ctypes.Array{default_value}'


class RefenreceToStdArrayType(PointerType):
    size: int

    def __init__(self, base: BaseType, size: int, is_const=False):
        super().__init__(base=base, is_const=is_const,
                         name_override=f'{base.name}[{size}]')
        self.size = size

    @property
    def ctypes_type(self) -> str:
        if not self.base:
            raise RuntimeError()
        return f'{self.base.ctypes_type} * {self.size}'

    def py_param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: ctypes.Array{default_value}'
