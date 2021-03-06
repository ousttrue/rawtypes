from typing import Optional, Tuple, List
from rawtypes.clang import cindex
from ..parser.struct_cursor import StructCursor, WrapFlags
from .basetype import BaseType
from .pointer_types import PointerType


class TypedefType(BaseType):
    def __init__(self, name: str, base: BaseType, is_const: bool = False) -> None:
        super().__init__(name, is_const)
        self.base = base

    def is_function_pointer(self) -> bool:
        from .function_types import FunctionProto
        if isinstance(self.base, FunctionProto):
            return True
        if isinstance(self.base, PointerType):
            if isinstance(self.base.base, FunctionProto):
                return True
        return False

    def resolve(self) -> BaseType:
        current = self
        while isinstance(current, TypedefType):
            current = current.base
        return current

    @property
    def ctypes_type(self) -> str:
        # TODO:
        return 'ctypes.c_void_p'  # function pointer

    def py_param(self, name: str, default_value: str, pyi: bool) -> str:
        return name + default_value

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if default_value:
            return f'{indent}{self.name} p{i} = t{i} ? ctypes_get_pointer<{self.name}>(t{i}) : {default_value};\n'
        else:
            return f'{indent}{self.name} p{i} = ctypes_get_pointer<{self.name}>(t{i});\n'

    def cpp_to_py(self, value: str) -> str:
        return self.base.cpp_to_py(value)


class StructType(BaseType):
    def __init__(self, name: str, cursor: cindex.Cursor, is_const=False, wrap_type: Optional[WrapFlags] = None):
        if name.startswith('const '):
            name = name[len('const '):]
        if name.startswith('struct '):
            name = name[len('struct '):]
        if name.startswith('union '):
            name = name[len('union '):]
        super().__init__(name, is_const=is_const)
        self.cursor = cursor
        self.wrap_type = wrap_type

    def to_struct_cursor(self, cursors: Tuple[cindex.Cursor, ...]) -> StructCursor:
        return StructCursor(cursors + (self.cursor,), self.cursor.type, self.cursor.kind == cindex.CursorKind.UNION_DECL)

    @property
    def ctypes_type(self) -> str:
        name = self.name
        if name:
            return name
        # anonymous
        return f'_{self.cursor.hash}'

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if default_value:
            raise NotImplementedError()
        else:
            return f'{indent}{self.name} *p{i} = ctypes_get_pointer<{self.name}*>(t{i});\n'

    def cpp_call_name(self, i: int):
        return f'*p{i}'

    def cpp_to_py(self, value: str) -> str:
        if not self.wrap_type:
            raise NotImplemented("return by value. but no python type")
        return f'ctypes_copy({value}, "{self.name}", "nanovg")'


class EnumType(BaseType):
    def __init__(self, name: str):
        if name.startswith('enum '):
            name = name[len('enum ')]
        super().__init__(name)

    @property
    def ctypes_type(self) -> str:
        return 'ctypes.c_int'

    @property
    def pyi_types(self) -> Tuple[str]:
        return ('int',)
