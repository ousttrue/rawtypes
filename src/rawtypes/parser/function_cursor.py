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
