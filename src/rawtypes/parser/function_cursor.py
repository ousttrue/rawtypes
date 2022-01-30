from typing import Iterable, List, Tuple, NamedTuple
import pathlib
import logging
import io
from rawtypes.clang import cindex
from .type_context import ParamContext, ResultContext

logger = logging.getLogger(__name__)


EXCLUDE_TYPES = (
    'va_list',
    'ImGuiTextFilter',
    'ImGuiStorage',
    'ImGuiStorage *',
)

EXCLUDE_FUNCS = (
    'CheckboxFlags',
    'Combo',
    'ListBox',
    'PlotLines',
)


def cj(src: Iterable[str]) -> str:
    '''
    comma join
    '''
    return '(' + ', '.join(src) + ')'


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


'''
PYX
'''


def extract_parameters(type_map, pyx: io.IOBase, params: List[ParamContext], indent: str) -> List[str]:
    param_names = []
    for i, param in enumerate(params):
        t = type_map.from_cursor(param.cursor.type, param.cursor)
        pyx.write(f'{t.cdef_param(indent, i, param.name)}')
        param_names.append(t.call_param(i))
    return param_names


def write_pyx_function(type_map, pyx: io.IOBase, function: cindex.Cursor, *, pyi=False, overload=1, prefix=''):
    result = ResultContext(function)
    result_t = type_map.from_cursor(result.type, result.cursor)
    params = ParamContext.get_function_params(function)

    overload = '' if overload == 1 else f'_{overload}'

    # signature
    pyx.write(
        f"def {prefix}{function.spelling}{overload}{cj(type_map.from_cursor(param.type, param.cursor).param(param.name, param.default_value(True), pyi=pyi) for param in params)}")
    # return type
    pyx.write(f'->{result_t.result_typing(pyi=pyi)}:')

    if pyi:
        pyx.write(' ...\n')
        return

    pyx.write('\n')

    indent = '    '

    # cdef parameters
    param_names = extract_parameters(type_map, pyx, params, indent)

    # body
    call = f'impl.{function.spelling}{cj(param_names)}'
    if result.is_void:
        pyx.write(f'{indent}{call}\n')
    else:
        pyx.write(result_t.cdef_result(indent, call))
    pyx.write('\n')


def write_pyx_method(type_map, pyx: io.IOBase, cursor: cindex.Cursor, method: cindex.Cursor, *, pyi=False):
    params = ParamContext.get_function_params(method)
    result = ResultContext(method)
    result_t = type_map.from_cursor(result.type, result.cursor)

    # signature
    pyx.write(
        f'    def {method.spelling}{self_cj(type_map.from_cursor(param.cursor.type, param.cursor).param(param.name, param.default_value, pyi=pyi) for param in params)}')
    pyx.write(f'->{result_t.result_typing(pyi=pyi)}:')

    if pyi:
        pyx.write(' ...\n')
        return

    pyx.write('\n')

    indent = '        '

    # self to ptr
    pyx.write(
        f'{indent}cdef impl.{cursor.spelling} *ptr = <impl.{cursor.spelling}*><uintptr_t>ctypes.addressof(self)\n')

    # cdef parameters
    param_names = extract_parameters(type_map, pyx, params, indent)

    # body
    call = f'ptr.{method.spelling}{cj(param_names)}'
    if result.is_void:
        pyx.write(f'{indent}{call}\n')
    else:
        pyx.write(result_t.cdef_result(indent, call))
    pyx.write('\n')


class FunctionCursor(NamedTuple):
    cursors: Tuple[cindex.Cursor, ...]

    def __repr__(self) -> str:
        return self.spelling

    @property
    def cursor(self) -> cindex.Cursor:
        return self.cursors[-1]

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.cursor.location.file.name)

    @property
    def spelling(self) -> str:
        return self.cursor.spelling

    @property
    def result(self) -> ResultContext:
        return ResultContext(self.cursor)

    @property
    def params(self) -> List[ParamContext]:
        return [param for param in ParamContext.get_function_params(self.cursor)]

    def is_exclude_function(self) -> bool:
        cursor = self.cursor
        if cursor.spelling in EXCLUDE_FUNCS:
            return True
        if cursor.spelling.startswith('operator'):
            logger.debug(f'exclude; {cursor.spelling}')
            return True
        if cursor.result_type.spelling in EXCLUDE_TYPES:
            return True
        for child in cursor.get_children():
            if child.kind == cindex.CursorKind.PARM_DECL:
                if child.type.spelling in EXCLUDE_TYPES:
                    return True
                if 'callback' in child.spelling:
                    # function pointer
                    return True
                if 'func' in child.spelling:
                    # function pointer
                    return True
                if '(*)' in child.type.spelling:
                    # function pointer
                    return True
        return False
