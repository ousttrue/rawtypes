from typing import Iterable, List
import io
from jinja2 import Environment
from rawtypes.clang import cindex
from rawtypes.interpreted_types import TypeManager
from rawtypes.parser.struct_cursor import StructCursor, WrapFlags
from rawtypes.parser.type_context import FieldContext, ParamContext, ResultContext, TypeContext
from rawtypes.parser.function_cursor import FunctionCursor


def to_ctypes_method(cursor: cindex.Cursor, method: cindex.Cursor, type_manager: TypeManager) -> str:
    w = io.StringIO()
    # params = ParamContext.get_function_params(method)
    result = ResultContext(method.result_type, method)
    result_t = type_manager.from_cursor(result.type, result.cursor)

    # signature
    w.write(f'def {method.spelling}(self, *args)')
    w.write(f'->{result_t.py_result}:')

    w.write('\n')
    indent = '    '
    w.write(f'{indent}from .impl import imgui\n')
    w.write(
        f'{indent}return imgui.{cursor.spelling}_{method.spelling}(self, *args)\n')

    return w.getvalue()


def to_ctypes_iter(env: Environment, s: StructCursor, flags: WrapFlags, type_manager: TypeManager) -> Iterable[str]:
    _fields = s.fields if flags.fields else []

    # first: anonymous fields
    for field in _fields:
        if field.is_anonymous_field:
            is_union = False
            match field.cursor.kind:
                case cindex.CursorKind.UNION_DECL:
                    is_union = True
            for src in to_ctypes_iter(env, StructCursor(s.cursors + (field.cursor,), field.type, is_union),
                                      WrapFlags('', f'{s.spelling}_anonymouse_{field.index}', fields=True), type_manager):
                yield src

    # second: fields
    template = env.get_template('ctypes_structure.py')

    anonymous = []
    fields = []
    for field in _fields:
        name = field.name
        if flags.custom_fields.get(name):
            name = '_' + name
        fields.append(type_manager.from_cursor(
            field.cursor.type, field.cursor).ctypes_field(name) + ',')
        if field.is_anonymous_field:
            anonymous.append(field.name)

    methods = [to_ctypes_method(s.cursor, method, type_manager)
               for method in TypeContext.get_struct_methods(s.cursor, includes=flags.methods)]

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


def cj(src: Iterable[str]) -> str:
    '''
    comma join
    '''
    return '(' + ', '.join(src) + ')'


def write_pyi_function(type_map: TypeManager, pyx: io.IOBase, function: cindex.Cursor, *, overload=1, prefix=''):
    f = FunctionCursor(function.result_type, [function])
    params = f.params
    result = f.result
    result_t = type_map.from_cursor(result.type, result.cursor)

    overload = '' if overload == 1 else f'_{overload}'

    values = []
    for param in params:
        values.append(type_map.from_cursor(param.type, param.cursor).py_param(
            param.name, param.default_value.py_value if param.default_value else '', pyi=True))

    # signature
    pyx.write(
        f"def {prefix}{function.spelling}{overload}{cj(values)}")
    # return type
    pyx.write(f'->{result_t.py_result}:')

    pyx.write(' ...\n')
    return


def self_cj(src: Iterable[str]) -> str:
    '''
    comma join
    '''
    sio = io.StringIO()
    sio.write('(self')
    for x in src:
        sio.write(', ')
        sio.write(x)
    sio.write(')')
    return sio.getvalue()


def write_pyi_method(type_map: TypeManager, pyx: io.IOBase, cursor: cindex.Cursor, method: cindex.Cursor):
    f = FunctionCursor(method.result_type, [method])
    params = f.params
    result = f.result
    result_t = type_map.from_cursor(result.type, result.cursor)

    values = []
    for param in params:
        values.append(type_map.from_cursor(param.cursor.type, param.cursor).py_param(
            param.name, param.default_value.py_value if param.default_value else '', pyi=True))

    # signature
    pyx.write(
        f'    def {method.spelling}{self_cj(values)}')
    pyx.write(f'->{result_t.py_result}:')

    pyx.write(' ...\n')
    return


def write_pyi_struct(self: StructCursor, type_map, pyi: io.IOBase, *, flags: WrapFlags = WrapFlags('', '')):
    cursor = self.cursors[-1]

    definition = cursor.get_definition()
    if definition and definition != cursor:
        # skip forward decl
        return

    pyi.write(f'class {cursor.spelling}(ctypes.Structure):\n')
    fields = FieldContext.get_struct_fields(cursor) if flags.fields else []
    if fields:
        for field in fields:
            name = field.name
            if flags.custom_fields.get(name):
                name = '_' + name
            pyi.write(type_map.from_cursor(field.type, field.cursor).pyi_field(
                '    ', field.name))
            pyi.write('\n')
        pyi.write('\n')

    for k, v in flags.custom_fields.items():
        pyi.write('    @property\n')
        l = next(iter(v.splitlines()))
        pyi.write(f'    {l} ...\n')

    methods = FieldContext.get_struct_methods(
        cursor, includes=flags.methods)
    if methods:
        for method in methods:
            write_pyi_method(
                type_map, pyi, cursor, method)

    for custom in flags.custom_methods:
        l = next(iter(custom.splitlines()))
        pyi.write(f'    {l} ...\n')

    if not fields and not methods:
        pyi.write('    pass\n\n')
