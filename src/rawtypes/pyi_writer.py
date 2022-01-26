import io
import pathlib
from .header import Header
from .declarations import function


def write_pyi(header: Header, generator, pyi: io.IOBase):
    types = [x for x in generator.parser.typedef_struct_list if pathlib.Path(
        x.cursor.location.file.name) == header.path]
    if types:
        for v in generator.types.WRAP_TYPES:
            for func in types:
                if func.cursor.spelling == v.name:
                    func.write_pyi(generator.types, pyi, flags=v)

    funcs = [x for x in generator.parser.functions if pathlib.Path(
        x.cursor.location.file.name) == header.path]
    if funcs:
        overload = {}
        for func in funcs:
            if func.is_exclude_function():
                continue

            name = func.spelling
            count = overload.get(name, 0) + 1
            function.write_pyx_function(
                generator.types, pyi, func.cursor, pyi=True, overload=count, prefix=header.prefix)
            overload[name] = count
