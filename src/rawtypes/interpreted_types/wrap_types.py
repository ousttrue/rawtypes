from typing import Optional, Tuple
import io
from .basetype import BaseType
from .pointer_types import PointerType, ReferenceType
from ..parser.struct_cursor import WrapFlags


class PointerToStructType(PointerType):
    def __init__(self, base: BaseType, is_const: bool, wrap_type: Optional[WrapFlags]):
        if not base:
            raise RuntimeError()
        super().__init__(base, is_const)
        self.wrap_type = wrap_type

    @property
    def ctypes_type(self) -> str:
        return f'{self.base.name}'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", ctypes.c_void_p), # {self}'

    @property
    def pyi_types(self) -> Tuple[str]:
        return (f'{self.base.name}',)

    def cpp_to_py(self, value: str) -> str:
        if self.wrap_type:
            return f'ctypes_cast(c_void_p({value}), "{self.base.name}", "{self.wrap_type.submodule}")'
        else:
            return f'c_void_p({value})'


class ReferenceToStructType(ReferenceType):
    def __init__(self, base: BaseType, is_const: bool, wrap_type: Optional[WrapFlags]):
        if not base:
            raise RuntimeError()
        super().__init__(base, is_const)
        self.wrap_type = wrap_type

    @property
    def ctypes_type(self) -> str:
        return f'{self.base.name}'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", ctypes.c_void_p), # {self}'

    @property
    def pyi_types(self) -> Tuple[str]:
        return (f'{self.base.name}',)

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if default_value:
            return f'''{indent}auto default_value{i} = {default_value};
{indent}{self.base.name} *p{i} = t{i} ? ctypes_get_pointer<{self.base.name}*>(t{i}) : &default_value{i};
'''
        else:
            return f'{indent}{self.base.name} *p{i} = ctypes_get_pointer<{self.base.name}*>(t{i});\n'

    def cpp_result(self, indent: str, call: str) -> str:
        sio = io.StringIO()
        sio.write(f'{indent}// {self}\n')
        sio.write(f'{indent}auto value = &{call};\n')
        sio.write(f'{indent}auto py_value = c_void_p(value);\n')
        if self.wrap_type:
            sio.write(
                f'{indent}py_value = ctypes_cast(py_value, "{self.base.name}", "{self.wrap_type.submodule}");\n')
        sio.write(f'{indent}return py_value;\n')
        return sio.getvalue()
