from typing import List, Optional, Callable, TypeAlias
import io
import pathlib
from .generator_base import GeneratorBase
from ..clang import cindex
from ..parser.type_context import TypeContext
from ..parser.struct_cursor import StructCursor
from ..parser.header import Header
from ..interpreted_types import BaseType
from ..interpreted_types.pointer_types import PointerType, VoidType, ArrayType, ReferenceType
from ..interpreted_types.primitive_types import (FloatType, DoubleType,
                                                 Int8Type, Int16Type, Int32Type,
                                                 UInt8Type, UInt16Type, UInt32Type, SizeType)
from ..interpreted_types.definition import StructType
from ..interpreted_types.string import CStringType

TYPE_CALLBACK: TypeAlias = Callable[[BaseType], Optional[str]]
ZIG_SYMBOLS = ['type']
DEFAULT_ARG_NAME = '__default'


def rename_symbol(name: str) -> str:
    if name in ZIG_SYMBOLS:
        return '_' + name
    return name


class ZigGenerator(GeneratorBase):
    def __init__(self, *headers: Header, include_dirs=[]) -> None:
        import platform
        target = 'x86_64-windows-gnu' if platform.system() == 'Windows' else ''
        super().__init__(*headers, include_dirs=include_dirs, target=target)
        self.custom: Optional[TYPE_CALLBACK] = None
        self.struct_map = {}

    def from_type(self, t: BaseType, is_arg: bool, *, bit_width: Optional[int] = None) -> str:
        if bit_width:
            return f'u{bit_width}'

        if self.custom:
            if custom_result := self.custom(t):
                return custom_result

        zig_type = ''
        match t:
            case VoidType():
                zig_type = 'void'
            case ArrayType():
                base = self.from_type(t.base, False)
                if is_arg:
                    # to pointer
                    zig_type = f'*{base}'
                else:
                    # array or slice ?
                    zig_type = f'[{t.size}]{base}'
            case PointerType():
                base = self.from_type(t.base, False)
                const = 'const ' if (is_arg and t.base.is_const) else ''
                if base == 'void':
                    zig_type = f'?*{const}anyopaque'
                else:
                    field_count = self.struct_map.get(base, 0)
                    if field_count:
                        zig_type = f'?*{const}{base}'
                    else:
                        zig_type = f'?*{const}anyopaque'
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
        assert zig_type
        return f'{zig_type}'

    def zig_type(self, c: TypeContext, is_arg: bool, *, bit_width: Optional[int] = None) -> str:
        t = self.type_manager.to_type(c)
        return self.from_type(t, is_arg, bit_width=bit_width)

    def is_const_reference(self, c: TypeContext) -> bool:
        t = self.type_manager.to_type(c)
        if not isinstance(t, ReferenceType):
            return False
        return t.base.is_const

    def generate(self, path: pathlib.Path, *, function_custom=[], is_exclude_function=None, custom: Optional[TYPE_CALLBACK] = None):
        self.custom = custom
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
            overload_map = {}
            for f in self.parser.functions:
                if header.path != f.path:
                    continue
                if is_exclude_function and is_exclude_function(f):
                    continue
                if not header.if_include(f.spelling):
                    continue

                args = [
                    f'{rename_symbol(param.name)}: {self.zig_type(param, True)}' for param in f.params]
                if f.spelling == f.symbol:
                    texts.append(
                        f'pub extern "c" fn {f.symbol}({", ".join(args)}) {self.zig_type(f.result, False)};')
                else:
                    # mangle version
                    texts.append(
                        f'extern "c" fn {f.symbol}({", ".join(args)}) {self.zig_type(f.result, False)};')

                    # wrap
                    overload_count = overload_map.get(f.spelling, 0) + 1
                    overload_map[f.spelling] = overload_count
                    overload = ''
                    if overload_count > 1:
                        overload += f'_{overload_count}'
                    func_name = f'{f.spelling}{overload}'
                    # arg_names = ', '.join(rename_symbol(param.name)
                    #                       for param in f.params)

                    with_default = ''
                    has_default = False
                    arg_names = []
                    for i, param in enumerate(f.params):
                        if with_default:
                            with_default += ', '
                        if param.default_value:
                            if not has_default:
                                with_default += DEFAULT_ARG_NAME + ': struct{'
                                has_default = True
                            if self.is_const_reference(param):
                                zig_type = self.zig_type(param, False)
                                assert zig_type[:2] == '?*'
                                with_default += f'{rename_symbol(param.name)}: {zig_type[2:]}= {param.default_value.zig_value}'
                                arg_names.append(
                                    '&' + DEFAULT_ARG_NAME + '.' + rename_symbol(param.name))
                            else:
                                with_default += f'{rename_symbol(param.name)}: {self.zig_type(param, False)}= {param.default_value.zig_value}'
                                arg_names.append(
                                    DEFAULT_ARG_NAME + '.' + rename_symbol(param.name))
                        else:
                            arg_names.append(rename_symbol(param.name))
                            with_default += args[i]
                    if has_default:
                        with_default += '}'

                    texts.append(f'''pub fn {func_name}({with_default}) {self.zig_type(f.result, False)}
    {{
        return {f.symbol}({", ".join(arg_names)});
    }}''')

        #
        # write texts
        #
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

        if not s.fields:
            texts.append(f'pub const {s.name} = opaque {{}};')
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
            self.struct_map[s.name] = len(s.fields)

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
                    f'    {f.name}: {self.zig_type(f, False, bit_width=bit_width)},\n')

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
