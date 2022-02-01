from typing import Iterable
import io
from jinja2 import Environment
from rawtypes.clang import cindex
from rawtypes.interpreted_types import TypeManager
from rawtypes.parser.struct_cursor import StructCursor, WrapFlags
from rawtypes.parser.type_context import ParamContext, ResultContext, TypeContext


def to_ctypes_method(cursor: cindex.Cursor, method: cindex.Cursor, type_manager: TypeManager, *, pyi=False) -> str:
    w = io.StringIO()
    params = ParamContext.get_function_params(method)
    result = ResultContext(method)
    result_t = type_manager.from_cursor(result.type, result.cursor)

    # signature
    w.write(f'def {method.spelling}(self, *args)')
    w.write(f'->{result_t.result_typing(pyi=pyi)}:')

    if pyi:
        w.write(' ...\n')
    else:
        w.write('\n')
        indent = '    '
        w.write(f'{indent}from .impl import imgui\n')
        w.write(
            f'{indent}return imgui.{cursor.spelling}_{method.spelling}(self, *args)\n')

    return w.getvalue()


def to_ctypes_iter(env: Environment, s: StructCursor, flags: WrapFlags, type_manager: TypeManager) -> Iterable[str]:
    fields = s.fields if flags.fields else []

    # first: anonymous fields
    if fields:
        for field in fields:
            if field.is_anonymous_field:
                is_union = False
                match field.cursor.kind:
                    case cindex.CursorKind.UNION_DECL:
                        is_union = True
                for src in to_ctypes_iter(env, StructCursor(s.cursors + (field.cursor,), field.type, is_union),
                                          WrapFlags(f'{s.spelling}_anonymouse_{field.index}', fields=True), type_manager):
                    yield src

    # second: fields
    template = env.get_template('ctypes_structure.py')

    anonymous = []
    if fields:
        for i, field in enumerate(fields):
            name = field.name
            if flags.custom_fields.get(name):
                name = '_' + name
            fields[i] = type_manager.from_cursor(
                field.cursor.type, field.cursor).ctypes_field(name) + ','
            if field.is_anonymous_field:
                anonymous.append(field.name)

    methods = TypeContext.get_struct_methods(s.cursor, includes=flags.methods)
    if methods:
        for i, method in enumerate(methods):
            methods[i] = to_ctypes_method(s.cursor, method, type_manager)

    for code in flags.custom_methods:
        methods.append(code)

    yield template.render(
        name=s.name,
        base_type="Union" if s.is_union else "Structure",
        anonymous=anonymous,
        fields=fields,
        custom_fields=[v for _, v in flags.custom_fields.items()],
        methods=methods
    )
