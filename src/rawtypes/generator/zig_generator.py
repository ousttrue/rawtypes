
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
    def generate(self, path: pathlib.Path, *, function_custom=[], is_exclude_function=None):
        with path.open('w', encoding='utf-8') as w:
            w.write('''// rawtypes generated
const std = @import("std");
const testing = std.testing;
export fn add(a: i32, b: i32) i32 {
    return a + b;
}
test "basic add functionality" {
    try testing.expect(add(3, 7) == 10);
}

''')

            modules = []
            headers = []
            for header in self.headers:

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

                    args = ', '.join(f'{param.name}: {zig_type(self.type_manager, param)}' for param in f.params)

                    w.write(f'extern "c" fn {f.symbol}({args}) {zig_type(self.type_manager, f.result)};\n')
                    w.write(f'const {func_name} = {f.symbol};\n')

                    break
