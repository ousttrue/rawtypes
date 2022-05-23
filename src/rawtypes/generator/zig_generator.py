from typing import List, Union
import io
import pathlib
from .generator_base import GeneratorBase
from ..parser.type_context import TypeContext
from ..parser.struct_cursor import StructCursor, WrapFlags
from ..interpreted_types import TypeManager
from ..interpreted_types.pointer_types import PointerType
from ..interpreted_types.primitive_types import FloatType, DoubleType, Int8Type, Int16Type, Int32Type, UInt16Type, UInt32Type
from ..interpreted_types.definition import StructType
from ..interpreted_types.string import CStringType


def zig_type(type_manager: TypeManager, t: TypeContext):
    param_type = type_manager.to_type(t)
    zig_type = ''
    match param_type:
        case PointerType():
            zig_type = '?*anyopaque'
        case Int8Type():
            zig_type = 'i8'
        case Int16Type():
            zig_type = 'c_short'
        case Int32Type():
            zig_type = 'c_int'
        case UInt16Type():
            zig_type = 'c_ushort'
        case UInt32Type():
            zig_type = 'c_uint'
        case FloatType():
            zig_type = 'f32'
        case DoubleType():
            zig_type = 'f64'
        case CStringType():
            zig_type = '?[*]const u8'
        case _:
            zig_type = param_type.name
            if zig_type.startswith('ImVector<'):
                zig_type = 'ImVector'
    assert zig_type
    return f'{zig_type}'


class ZigGenerator(GeneratorBase):
    def __init__(self, *args, **kw) -> None:
        import platform
        target = 'x86_64-windows-gnu' if platform.system() == 'Windows' else ''
        super().__init__(*args, **kw, target=target)

    def generate(self, path: pathlib.Path, *, function_custom=[], is_exclude_function=None, exclude_types=[]):
        texts = []

        modules = []
        headers = []
        for header in self.headers:
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
            texts.append('''
pub const ImVector = struct {
    Size: c_int,
    Capacity: c_int,
    Data: *anyopaque,
};

''')
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

                break

        with path.open('w', encoding='utf-8') as w:
            for text in texts:
                w.write(text)
                w.write('\n')

    def write_struct(self, texts_or_sio: Union[List[str], io.TextIOBase], s: StructCursor):
        if s.is_forward_decl:
            return
        if s.is_template:
            return

        if s.name == 'ClipRect':
            pass

        if isinstance(texts_or_sio, list):
            texts = texts_or_sio
            sio = io.StringIO()
            sio.write(
                f'pub const {s.name} = extern struct {{\n')
        else:
            texts = None
            sio = texts_or_sio
            sio.write('struct {\n')
        for f in s.fields:
            t = self.type_manager.to_type(f)
            if isinstance(t, StructType) and t.nested_cursor:
                if t.nested_cursor.is_anonymous():
                    sio.write(
                        f'    {f.name}:')
                    self.write_struct(sio, StructCursor(
                        s.cursors + (t.nested_cursor,), t.nested_cursor.type, False))
                else:
                    self.write_struct(texts, StructCursor(
                        s.cursors + (t.nested_cursor,), t.nested_cursor.type, False))
                    sio.write(
                        f'    {f.name}: {t.name},\n')
            else:
                sio.write(
                    f'    {f.name}: {zig_type(self.type_manager, f)},\n')

        if texts:
            sio.write('};\n')
            texts.append(sio.getvalue())
        else:
            sio.write('}\n')

        # test size of
