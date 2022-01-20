import io
import pathlib
from .header import Header
from .parser import Parser
from .interpreted_types import wrap_types
from .declarations import function


def write_pyi(header: Header, pyi: io.IOBase, parser: Parser):
    types = [x for x in parser.typedef_struct_list if pathlib.Path(
        x.cursor.location.file.name) == header.path]
    if types:
        for v in wrap_types.WRAP_TYPES:
            for func in types:
                if func.cursor.spelling == v.name:
                    func.write_pyi(pyi, flags=v)

    funcs = [x for x in parser.functions if pathlib.Path(
        x.cursor.location.file.name) == header.path]
    if funcs:
        overload = {}
        for func in funcs:
            if func.is_exclude_function():
                continue

            name = func.spelling
            count = overload.get(name, 0) + 1
            function.write_pyx_function(
                pyi, func.cursor, pyi=True, overload=count, prefix=header.prefix)
            overload[name] = count
