from typing import List, Union, Optional
import re
import io
import pathlib
from .generator_base import GeneratorBase
from ..clang import cindex
from ..parser.type_context import TypeContext
from ..parser.struct_cursor import StructCursor, WrapFlags
from ..interpreted_types import TypeManager, BaseType
from ..interpreted_types.pointer_types import PointerType, VoidType, ArrayType
from ..interpreted_types.primitive_types import (FloatType, DoubleType,
                                                 Int8Type, Int16Type, Int32Type,
                                                 UInt8Type, UInt16Type, UInt32Type, SizeType)
from ..interpreted_types.definition import StructType
from ..interpreted_types.string import CStringType

STRUCT_MAP = {}


def from_type(t: BaseType, *, bit_width: Optional[int] = None):
    if bit_width:
        return f'u{bit_width}'
    zig_type = ''
    match t:
        case VoidType():
            zig_type = 'void'
        case ArrayType():
            base = from_type(t.base)
            zig_type = f'[{t.size}]{base}'
        case PointerType():
            base = from_type(t.base)
            if base == 'void':
                zig_type = f'?*anyopaque'
            else:
                field_count = STRUCT_MAP.get(base, 0)
                if field_count:
                    zig_type = f'?*{base}'
                else:
                    zig_type = f'?*anyopaque'
        case Int8Type():
            zig_type = 'i8'
        case Int16Type():
            zig_type = 'c_short'
        case Int32Type():
            zig_type = 'c_int'
        case UInt8Type():
            zig_type = 'u8'
        case UInt16Type():
            zig_type = 'c_ushort'
        case UInt32Type():
            zig_type = 'c_uint'
        case SizeType():
            zig_type = 'usize'
        case FloatType():
            zig_type = 'f32'
        case DoubleType():
            zig_type = 'f64'
        case CStringType():
            zig_type = '?[*]const u8'
        case _:
            zig_type = t.name
            if zig_type.startswith('ImVector<'):
                zig_type = 'ImVector'
    assert zig_type
    return f'{zig_type}'


def zig_type(type_manager: TypeManager, c: TypeContext, *, bit_width: Optional[int] = None):
    t = type_manager.to_type(c)
    return from_type(t, bit_width=bit_width)


class ZigGenerator(GeneratorBase):
    def __init__(self, *args, **kw) -> None:
        import platform
        target = 'x86_64-windows-gnu' if platform.system() == 'Windows' else ''
        super().__init__(*args, **kw, target=target)

    def generate(self, path: pathlib.Path, *, function_custom=[], is_exclude_function=None, exclude_types=[]):
        texts = [
            'const expect = @import("std").testing.expect;'
        ]

        modules = []
        headers = []
        for header in self.headers:
            if header.begin:
                texts.append(header.begin)

            #
            # enum
            #
            for e in self.parser.enums:
                if e.path != header.path:
                    continue

                sio = io.StringIO()
                enum_name = e.cursor.spelling
                if enum_name[-1] == '_':
                    enum_name = enum_name[:-1]
                sio.write(f'pub const {enum_name} = enum(c_int) {{\n')
                for value in e.get_values():
                    name = value.spelling
                    if name.startswith(enum_name):
                        if name[len(enum_name)].isdigit():
                            pass
                        else:
                            name = name[len(enum_name):]
                    sio.write(f'    {name} = {value.enum_value},\n')
                sio.write('};\n')
                texts.append(sio.getvalue())

            #
            # struct
            #
            for t in self.parser.typedef_struct_list:
                if t.path != header.path:
                    continue
                match t:
                    case StructCursor() as s:
                        self.write_struct(texts, s)

            #
            # function
            #
            methods = []
            overload_map = {}
            for f in self.parser.functions:
                if header.path != f.path:
                    continue
                if is_exclude_function and is_exclude_function(f):
                    continue
                if not header.if_include(f.spelling):
                    continue

                customize = None
                for custom in function_custom:
                    if custom.name == f.spelling:
                        customize = custom
                        break

                overload_count = overload_map.get(f.spelling, 0) + 1
                overload_map[f.spelling] = overload_count
                overload = ''
                if overload_count > 1:
                    overload += f'_{overload_count}'

                # namespace = get_namespace(f.cursors)
                func_name = f'{f.spelling}{overload}'
                args = ', '.join(
                    f'{param.name}: {zig_type(self.type_manager, param)}' for param in f.params)

                sio = io.StringIO()
                sio.write(
                    f'extern "c" fn {f.symbol}({args}) {zig_type(self.type_manager, f.result)};\n')
                sio.write(f'pub const {func_name} = {f.symbol};\n')
                texts.append(sio.getvalue())

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as w:
            for text in texts:
                w.write(text)
                w.write('\n')

    def write_struct(self, texts: List[str], s: StructCursor, sio: Optional[io.StringIO] = None):
        if s.is_forward_decl:
            return
        if s.is_template:
            return

        struct_or_union = 'union' if s.is_union else 'struct'
        if sio:
            nested = True
            sio.write(f'extern {struct_or_union} {{\n')
        else:
            nested = False
            sio = io.StringIO()
            sio.write(
                f'pub const {s.name} = extern {struct_or_union} {{\n')
            STRUCT_MAP[s.name] = len(s.fields)

        has_bitfields = False
        for f in s.fields:
            t = self.type_manager.to_type(f)
            if isinstance(t, StructType) and t.nested_cursor:
                is_union = t.nested_cursor.kind == cindex.CursorKind.UNION_DECL
                if t.nested_cursor.is_anonymous():
                    sio.write(
                        f'    {f.name}:')
                    self.write_struct(texts, StructCursor(
                        s.cursors + (t.nested_cursor,), t.nested_cursor.type, is_union), sio=sio)
                else:
                    self.write_struct(texts, StructCursor(
                        s.cursors + (t.nested_cursor,), t.nested_cursor.type, is_union))
                    sio.write(
                        f'    {f.name}: {t.name},\n')
            else:
                bit_width = None
                if f.cursor.is_bitfield():
                    has_bitfields = True
                    bit_width = f.cursor.get_bitfield_width()
                sio.write(
                    f'    {f.name}: {zig_type(self.type_manager, f, bit_width=bit_width)},\n')

        if nested:
            sio.write('}\n')
        else:
            sio.write('};\n')
            text = sio.getvalue()
            if has_bitfields:
                # pub const XXX = extern struct
                text = text.replace(' extern ', ' packed ', 1)
            texts.append(text)

        # test size of
        if s.spelling and s.sizeof > 1:
            texts.append(f'''test "sizeof {s.spelling}" {{
    // Optional pointers are the same size as normal pointers, because pointer
    // value 0 is used as the null value.
    try expect(@sizeOf({s.spelling}) == {s.sizeof});
}}
    ''')
