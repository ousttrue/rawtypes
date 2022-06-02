from typing import List, Optional, Callable, TypeAlias, NamedTuple, Tuple
import io
import pathlib
from .generator_base import GeneratorBase
from ..clang import cindex
from ..parser.type_context import TypeContext, ParamContext
from ..parser.struct_cursor import StructCursor
from ..parser.typedef_cursor import TypedefCursor
from ..parser.function_cursor import FunctionCursor
from ..parser.header import Header, StructConfiguration
from ..interpreted_types import BaseType, TypeManager, TypeWithCursor, FunctionProto, TypedefType
from ..interpreted_types.pointer_types import PointerType, VoidType, ArrayType, ReferenceType
from ..interpreted_types.primitive_types import (FloatType, DoubleType,
                                                 Int8Type, Int16Type, Int32Type, Int64Type,
                                                 UInt8Type, UInt16Type, UInt32Type, UInt64Type,
                                                 SizeType)
from ..interpreted_types.definition import StructType
from ..interpreted_types.string_types import CStringType

TYPE_CALLBACK: TypeAlias = Callable[[BaseType], Optional[str]]
ZIG_SYMBOLS = ['type', 'align']
DEFAULT_ARG_NAME = '__default'


def to_cpp_arg(p: ParamContext):
    # t = generator.type_manager.to_type(p)
    return f'{p.type.spelling} {p.name}'


def rename_symbol(name: str) -> str:
    if name in ZIG_SYMBOLS:
        return '_' + name
    return name


def remove_const_ref(name: str) -> str:
    if name[0] == '*':
        name = name[1:].strip()
    if name.startswith('const '):
        name = name[6:].strip()
    return name


class Workaround(NamedTuple):
    f: FunctionCursor
    code: str


class FunctionOverload:
    def __init__(self) -> None:
        self.overload_map = {}

    def get_overloaded_func_name(self, func_name: str) -> str:
        overload_count = self.overload_map.get(func_name, 0) + 1
        self.overload_map[func_name] = overload_count
        overload = ''
        if overload_count > 1:
            overload += f'_{overload_count}'
        return f'{func_name}{overload}'


class ZigGenerator(GeneratorBase):
    def __init__(self, *headers: Header, include_dirs=[]) -> None:
        import platform
        target = 'x86_64-windows-gnu' if platform.system() == 'Windows' else ''
        super().__init__(*headers, use_typdef=True, include_dirs=include_dirs, target=target)
        self.custom: Optional[TYPE_CALLBACK] = None
        self.struct_map = {}
        self.function_overload = FunctionOverload()

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
                const = ''
                if is_arg:
                    if t.base.is_const:
                        const = 'const '
                    elif isinstance(base, FunctionProto):
                        const = 'const '

                pointer = '*' if isinstance(t, ReferenceType) else '?*'
                if base == 'void':
                    zig_type = f'{pointer}{const}anyopaque'
                else:
                    zig_type = f'{pointer}{const}{base}'
            case Int8Type():
                zig_type = 'i8'
            case Int16Type():
                zig_type = 'c_short'
            case Int32Type():
                zig_type = 'c_int'
            case Int64Type():
                zig_type = 'c_longlong'
            case UInt8Type():
                zig_type = 'u8'
            case UInt16Type():
                zig_type = 'c_ushort'
            case UInt32Type():
                zig_type = 'c_uint'
            case UInt64Type():
                zig_type = 'c_ulonglong'
            case SizeType():
                zig_type = 'usize'
            case FloatType():
                zig_type = 'f32'
            case DoubleType():
                zig_type = 'f64'
            case CStringType():
                zig_type = '?[*:0]const u8'
            case TypedefType():
                if t.is_function_pointer():
                    zig_type = t.name
                if isinstance(t.base, PointerType) and isinstance(t.base.base, FunctionProto):
                    zig_type = f'*const {t.name}'
                else:
                    zig_type = self.from_type(t.resolve(), is_arg)
            case FunctionProto():
                f = t.function
                args = [
                    f'{rename_symbol(param.name)}: {self.zig_type(param, True)}' for param in f.params]
                zig_type = f'fn ({", ".join(args)}) {self.zig_type(f.result, False)}'
            case _:
                zig_type = t.name
                if zig_type.startswith('const '):
                    zig_type = zig_type[6:]

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

    def generate(self, path: pathlib.Path, *, is_exclude_function=None, custom: Optional[TYPE_CALLBACK] = None, return_byvalue_workaround=False) -> List[Workaround]:
        self.custom = custom
        self.texts = [
            '// this is generated by rawtypes',
            'const expect = @import("std").testing.expect;'
        ]

        workaround_codes: List[Workaround] = []
        for header in self.headers:
            if header.begin:
                self.texts.append(header.begin)

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
                self.texts.append(sio.getvalue())

            #
            # struct
            #
            for t in self.parser.typedef_struct_list:
                if t.path != header.path:
                    continue
                match t:
                    case TypedefCursor() as td:
                        self.write_typedef(td)
                    case StructCursor() as s:
                        self.write_struct(
                            s, config=header.structs.get(s.spelling))

            #
            # function
            #
            for f in self.parser.functions:
                if header.path != f.path:
                    continue
                if is_exclude_function and is_exclude_function(f):
                    continue
                if not header.if_include(f.spelling):
                    continue

                code = self.write_function(
                    f, return_byvalue_workaround=return_byvalue_workaround)
                if code:
                    workaround_codes.append(code)

        #
        # write texts
        #
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as w:
            for text in self.texts:
                w.write(text)
                w.write('\n')

        return workaround_codes

    def write_typedef(self, td: TypedefCursor):
        underlying = self.type_manager.get(
            TypeWithCursor(td.underlying_type, td.cursor))
        if underlying.name == td.spelling:
            return
        match underlying:
            case PointerType():
                if isinstance(underlying.base, FunctionProto):
                    f = underlying.base.function
                    args = [
                        f'{rename_symbol(param.name)}: {self.zig_type(param, True)}' for param in f.params]
                    self.texts.append(
                        f'const {td.spelling} = fn ({", ".join(args)}) callconv(.C) {self.zig_type(f.result, False)};')
            case StructType():
                pass
            # case _:
            #     self.texts.append(
            #         f'const {td.spelling} = {self.from_type(underlying, False)};')

    def write_struct(self, s: StructCursor, *, indent='', sio: Optional[io.StringIO] = None, config: Optional[StructConfiguration] = None):
        if s.is_forward_decl:
            return
        if s.is_template:
            return

        if not s.fields:
            self.texts.append(f'pub const {s.name} = opaque {{}};')
            return

        struct_or_union = 'union' if s.is_union else 'struct'
        if sio:
            nested = True
            sio.write(f' extern {struct_or_union} {{\n')
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
                        f'{indent}    {f.name}:')
                    self.write_struct(StructCursor(
                        s.cursors + (t.nested_cursor,), t.nested_cursor.type, is_union), indent=indent+'    ', sio=sio)
                    sio.write(',\n')
                else:
                    self.write_struct(StructCursor(
                        s.cursors + (t.nested_cursor,), t.nested_cursor.type, is_union), indent=indent+'    ')
                    sio.write(
                        f'{indent}    {f.name}: {t.name},\n')
            else:
                bit_width = None
                if f.cursor.is_bitfield():
                    has_bitfields = True
                    bit_width = f.cursor.get_bitfield_width()
                sio.write(
                    f'{indent}    {f.name}: {self.zig_type(f, False, bit_width=bit_width)},\n')

        if config and config.methods:
            overload = FunctionOverload()
            for method in s.get_methods():
                self.write_method(s, method, sio, overload)

        if nested:
            sio.write(f'{indent}}}')
        else:
            sio.write('};\n')
            text = sio.getvalue()
            if has_bitfields:
                # pub const XXX = extern struct
                text = text.replace(' extern ', ' packed ', 1)
            self.texts.append(text)

        # test size of
        if s.spelling and s.sizeof > 1:
            self.texts.append(f'''test "sizeof {s.spelling}" {{
    // Optional pointers are the same size as normal pointers, because pointer
    // value 0 is used as the null value.
    try expect(@sizeOf({s.spelling}) == {s.sizeof});
}}
''')

    def write_method(self, s: StructCursor, f: FunctionCursor, sio: io.StringIO, overload: FunctionOverload):
        args = [f'self: * {s.spelling}'] + [
            f'{rename_symbol(param.name)}: {self.zig_type(param, True)}' for param in f.params]
        self.texts.append(
            f'''extern fn {f.mangled_name}({", ".join(args)}) {self.zig_type(f.result, False)};''')

        with_default, arg_names = self.get_params(f)
        arg_names = ['self'] + arg_names
        if with_default:
            with_default = f'self: * {s.spelling}, ' + with_default
        else:
            with_default = f'self: * {s.spelling}'

        func_name = overload.get_overloaded_func_name(f.spelling)
        sio.write(f'''    pub fn {func_name}({with_default}) {self.zig_type(f.result, True)}
    {{
        return {f.mangled_name}({", ".join(arg_names)});
    }}
'''
                  )

    def write_function(self, f: FunctionCursor, return_byvalue_workaround=False) -> Optional[Workaround]:
        args = [
            f'{rename_symbol(param.name)}: {self.zig_type(param, True)}' for param in f.params]
        if f.is_variadic:
            args.append('...')
        if f.spelling == f.mangled_name:
            self.texts.append(
                f'pub extern "c" fn {f.mangled_name}({", ".join(args)}) {self.zig_type(f.result, False)};')
            return

        if f.return_struct_byvalue and return_byvalue_workaround:
            # [zig]
            # call workaround wrapper
            result = self.type_manager.to_type(f.result)
            args = [f'v: *{result.name}'] + args
            self.texts.append(
                f'extern "c" fn imgui_{f.spelling}({", ".join(args)}) void;')

            self.texts.append(f'''pub fn {f.spelling}() {result.name}
{{
    var v: {result.name} = undefined;
    imgui_{f.spelling}(&v);
    return v;
}}
''')

            # [cpp]
            # workaround wrapper
            args = [f'{result.name} *__ret__'] + \
                [to_cpp_arg(p) for p in f.params]

            code = f'''
void imgui_{f.cursor.spelling}({", ".join(args)})
{{
    *__ret__ = ImGui::{f.cursor.spelling}({", ".join(p.name for p in f.params)});
}}
'''
            return Workaround(f, code)

        else:
            with_default, arg_names = self.get_params(f)

            # mangle version
            self.texts.append(
                f'extern "c" fn {f.mangled_name}({", ".join(args)}) {self.zig_type(f.result, False)};')

            # wrap
            func_name = self.function_overload.get_overloaded_func_name(
                f.spelling)
            if f.is_variadic:
                with_default += ', __va__: anytype'
                self.texts.append(f'''pub fn {func_name}({with_default}) {self.zig_type(f.result, False)}
{{
    return @call(.{{}}, {f.mangled_name}, .{{{", ".join(arg_names)}}} ++ __va__);
}}''')
            else:
                self.texts.append(f'''pub fn {func_name}({with_default}) {self.zig_type(f.result, False)}
{{
    return {f.mangled_name}({", ".join(arg_names)});
}}''')

    def get_params(self, f: FunctionCursor) -> Tuple[str, List[str]]:
        with_default = ''
        has_default = False
        arg_names = []
        for i, param in enumerate(f.params):
            if with_default:
                with_default += ', '

            zig_type = self.zig_type(param, True)
            if param.default_value:
                if not has_default:
                    with_default += DEFAULT_ARG_NAME + ': struct{'
                    has_default = True

                if self.is_const_reference(param):
                    # remove pointer
                    assert zig_type[0] == '*'
                    zig_type = remove_const_ref(zig_type)
                    with_default += f'{rename_symbol(param.name)}: {zig_type}= {param.default_value.zig_value}'
                    # restore pointer
                    arg_names.append(
                        '&' + DEFAULT_ARG_NAME + '.' + rename_symbol(param.name))
                else:
                    with_default += f'{rename_symbol(param.name)}: {zig_type}= {param.default_value.zig_value}'
                    arg_names.append(
                        DEFAULT_ARG_NAME + '.' + rename_symbol(param.name))
            else:
                if self.is_const_reference(param):
                    # remove pointer
                    assert zig_type[0] == '*'
                    zig_type = remove_const_ref(zig_type)
                    with_default += f'{rename_symbol(param.name)}: {zig_type}'
                    # restore pointer
                    arg_names.append('&'+rename_symbol(param.name))
                else:
                    with_default += f'{rename_symbol(param.name)}: {zig_type}'
                    arg_names.append(rename_symbol(param.name))
        if has_default:
            with_default += '}'
        return with_default, arg_names
