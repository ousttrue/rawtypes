from typing import NamedTuple, Union, Tuple, Dict
import io
from .basetype import BaseType
from .pointer_types import PointerType, ReferenceType

IMVECTOR = '''

def iterate(data: ctypes.c_void_p, t: Type[ctypes.Structure], count: int)->Iterable[ctypes.Structure]:
    p = ctypes.cast(data, ctypes.POINTER(t))
    for i in range(count):
        yield p[i]


class ImVector(ctypes.Structure):
    _fields_ = (
        ('Size', ctypes.c_int),
        ('Capacity', ctypes.c_int),
        ('Data', ctypes.c_void_p),
    )

    def each(self, t: Type[ctypes.Structure])->Iterable[ctypes.Structure]:
        return iterate(self.Data, t, self.Size)

'''


class WrapFlags(NamedTuple):
    name: str
    fields: bool = False
    custom_fields: Dict[str, str] = {}
    methods: Union[bool, Tuple[str, ...]] = False
    custom_methods: Tuple[str, ...] = ()
    default_constructor: bool = False


WRAP_TYPES = [
    WrapFlags('ImVec2', fields=True, custom_methods=(
        '''def __iter__(self):
    yield self.x
    yield self.y
''',
    )),
    WrapFlags('ImVec4', fields=True, custom_methods=(
        '''def __iter__(self):
    yield self.x
    yield self.y
    yield self.w
    yield self.h
''',
    )),
    WrapFlags('ImFont'),
    WrapFlags('ImFontConfig', fields=True, default_constructor=True),
    WrapFlags('ImFontAtlasCustomRect', fields=True),
    WrapFlags('ImFontAtlas', fields=True, methods=True),
    WrapFlags('ImGuiIO', fields=True, custom_fields={
        'Fonts': '''def Fonts(self)->'ImFontAtlas':
    return ctypes.cast(ctypes.c_void_p(self._Fonts), ctypes.POINTER(ImFontAtlas))[0]
'''
    }),
    WrapFlags('ImGuiContext'),
    WrapFlags('ImDrawCmd', fields=True),
    WrapFlags('ImDrawData', fields=True),
    WrapFlags('ImDrawListSplitter', fields=True),
    WrapFlags('ImDrawCmdHeader', fields=True),
    WrapFlags('ImDrawList', fields=True),
    WrapFlags('ImGuiViewport', fields=True, methods=True),
    WrapFlags('ImGuiStyle'),
    WrapFlags('ImGuiWindowClass'),

    # tinygizmo
    WrapFlags('gizmo_context', fields=True, methods=True),
]


def is_wrap_type(name: str) -> bool:
    for w in WRAP_TYPES:
        if w.name == name:
            return True
    return False


class ImVec2WrapType(BaseType):
    def __init__(self):
        super().__init__('ImVec2')

    @property
    def ctypes_type(self) -> str:
        return 'ImVec2'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: Union[ImVec2, Tuple[float, float]]{default_value}'

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        return f'''{indent}# {self}
{indent}cdef impl.ImVec2 p{i} = impl.ImVec2({name}[0], {name}[1]) if isinstance({name}, tuple) else impl.ImVec2({name}.x, {name}.y)
'''

    def result_typing(self, pyi: bool) -> str:
        return 'Tuple[float, float]'

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}cdef impl.ImVec2 value = {call}
{indent}return (value.x, value.y)
'''

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        if default_value:
            return f'{indent}ImVec2 p{i} = t{i} ? get_ImVec2(t{i}) : {default_value};\n'
        else:
            return f'{indent}ImVec2 p{i} = get_ImVec2(t{i});\n'

    def py_value(self, value: str) -> str:
        return f'Py_BuildValue("(ff)", {value}.x, {value}.y)'


class ImVec4WrapType(BaseType):
    def __init__(self):
        super().__init__('ImVec4')

    @property
    def ctypes_type(self) -> str:
        return 'ImVec4'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        return f'{name}: Union[ImVec4, Tuple[float, float, float, float]]{default_value}'

    def result_typing(self, pyi: bool) -> str:
        return 'Tuple[float, float, float, float]'

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}cdef impl.ImVec4 value = {call}
{indent}return (value.x, value.y, value.z, value.w)
'''

    def py_value(self, value: str) -> str:
        return f'Py_BuildValue("(ffff)", {value}.x, {value}.y, {value}.z, {value}.w)'


class ImVector(BaseType):
    def __init__(self):
        super().__init__('ImVector')

    @property
    def ctypes_type(self) -> str:
        return 'ImVector'


class VertexBufferType(BaseType):
    def __init__(self):
        super().__init__('VertexBuffer')

    @property
    def ctypes_type(self) -> str:
        return 'VertexBuffer'

    def result_typing(self, pyi: bool) -> str:
        return 'Tuple[ctypes.c_void_p, int, ctypes.c_void_p, int]'

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}cdef impl.VertexBuffer value = {call}
{indent}return (ctypes.c_void_p(<uintptr_t>value.vertices), value.vertices_count, ctypes.c_void_p(<uintptr_t>value.indices), value.indices_count)
'''


class PointerToStructType(PointerType):
    def __init__(self, base: BaseType, is_const: bool):
        super().__init__(base, is_const)

    @property
    def ctypes_type(self) -> str:
        if not self.base:
            raise RuntimeError()
        return f'{self.base.name}'

    def ctypes_field(self, indent: str, name: str) -> str:
        return f'{indent}("{name}", ctypes.c_void_p), # {self}\n'

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
        if is_wrap_type(self.base.name):
            return f'ctypes_cast(c_void_p({value}), "{self.base.name}")'
        else:
            return f'c_void_p({value})'


class ReferenceToStructType(ReferenceType):
    def __init__(self, base: BaseType, is_const: bool):
        super().__init__(base, is_const)

    @property
    def ctypes_type(self) -> str:
        if not self.base:
            raise RuntimeError()
        return f'{self.base.name}'

    def ctypes_field(self, indent: str, name: str) -> str:
        return f'{indent}("{name}", ctypes.c_void_p), # {self}\n'

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
        if is_wrap_type(self.base.name):
            sio.write(
                f'{indent}py_value = ctypes_cast(py_value, "{self.base.name}");\n')
        sio.write(f'{indent}return py_value;\n')
        return sio.getvalue()
