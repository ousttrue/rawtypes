import io
import pathlib
from .generator_base import GeneratorBase
from ..parser.type_context import TypeContext
from ..interpreted_types import TypeManager
from ..interpreted_types.pointer_types import PointerType


def zig_type(type_manager: TypeManager, t: TypeContext):
    param_type = type_manager.to_type(t)
    zig_type = ''
    match param_type:
        case PointerType():
            zig_type = '?*anyopaque'
        case _:
            zig_type = param_type.name
    assert zig_type
    return f'{zig_type}'


class ZigGenerator(GeneratorBase):
    def __init__(self, *args, **kw) -> None:
        import platform
        target = 'x86_64-windows-gnu' if platform.system() == 'Windows' else ''
        super().__init__(*args, **kw, target=target)

    def generate(self, path: pathlib.Path, *, function_custom=[], is_exclude_function=None):
        sio = io.StringIO()

        modules = []
        headers = []
        for header in self.headers:
            for e in self.parser.enums:
                if e.path != header.path:
                    continue

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
                # sio.write(to_c_function(self.env, f, self.type_manager,
                #           namespace=namespace, func_name=func_name, custom=customize))
                # sio.write('\n')

                args = ', '.join(
                    f'{param.name}: {zig_type(self.type_manager, param)}' for param in f.params)

                sio.write(
                    f'extern "c" fn {f.symbol}({args}) {zig_type(self.type_manager, f.result)};\n')
                sio.write(f'pub const {func_name} = {f.symbol};\n')

                break

        with path.open('w', encoding='utf-8') as w:
            w.write(sio.getvalue())
