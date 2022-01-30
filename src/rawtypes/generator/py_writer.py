import io

from soupsieve import Iterable
from rawtypes.clang import cindex
from rawtypes.interpreted_types import TypeManager
from rawtypes.parser.struct_cursor import StructCursor, WrapFlags
from rawtypes.parser.type_context import TypeContext


def to_ctypes_method(cursor: cindex.Cursor, method: cindex.Cursor, type_manager: TypeManager, *, pyi=False) -> str:
    w = io.StringIO()
    params = TypeContext.get_function_params(method)
    result = TypeContext.from_function_result(method)
    result_t = type_manager.from_cursor(result.type, result.cursor)

    # signature
    w.write(
        f'    def {method.spelling}(self, *args)')
    w.write(f'->{result_t.result_typing(pyi=pyi)}:')

    if pyi:
        w.write(' ...\n')
    else:
        w.write('\n')

        indent = '        '

        w.write(f'{indent}from .impl import imgui\n')
        w.write(
            f'{indent}return imgui.{cursor.spelling}_{method.spelling}(self, *args)\n')

    return w.getvalue()


def to_ctypes_iter(s: StructCursor, flags: WrapFlags, type_manager: TypeManager) -> Iterable[str]:
    w = io.StringIO()
    cursor = s.cursor
    fields = s.fields if flags.fields else []

    # first: anonymous fields
    if fields:
        for field in fields:
            if field.is_anonymous_field:
                is_union = False
                match field.cursor.kind:
                    case cindex.CursorKind.UNION_DECL:
                        is_union = True
                for src in to_ctypes_iter(StructCursor(s.cursors + (field.cursor,), field.type, is_union),
                                     WrapFlags(f'{s.spelling}_anonymouse_{field.index}', fields=True), type_manager):
                    yield src

    # second: fields
    w.write(
        f'class {s.name}(ctypes.{"Union" if s.is_union else "Structure"}):\n')
    if fields:
        w.write('    _fields_=[\n')
        indent = '        '
        for field in fields:
            name = field.name
            if flags.custom_fields.get(name):
                name = '_' + name
            w.write(type_manager.from_cursor(
                field.cursor.type, field.cursor).ctypes_field(indent, name))
        w.write('    ]\n\n')

    for _, v in flags.custom_fields.items():
        w.write('    @property\n')
        for l in v.splitlines():
            w.write(f'    {l}\n')
        w.write('\n')

    methods = TypeContext.get_struct_methods(cursor, includes=flags.methods)
    if methods:
        for method in methods:
            w.write(to_ctypes_method(cursor, method, type_manager))

    for code in flags.custom_methods:
        for l in code.splitlines():
            w.write(f'    {l}\n')
        w.write('\n')

    if not fields:  # and not methods and not flags.custom_methods:
        w.write('    pass\n\n')

    yield w.getvalue()
