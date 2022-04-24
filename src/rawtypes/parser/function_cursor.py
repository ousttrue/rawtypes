from audioop import reverse
import enum
from typing import List, Tuple, NamedTuple
import pathlib
import logging
from rawtypes.clang import cindex
from .type_context import ParamContext, ResultContext

LOGGER = logging.getLogger(__name__)


def rindex(l, target) -> int:
    for i in range(len(l) - 1, -1, -1):
        if l[i] == target:
            return i
    return -1


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
        cursors = [child for child in self.cursor.get_children(
        ) if child.kind == cindex.CursorKind.PARM_DECL]
        params = [ParamContext(i, child) for i, child in enumerate(cursors)]
        # params = [param for param in ParamContext.get_function_params(self.cursor)]
        tokens = [token.spelling for token in self.cursor.get_tokens()]
        open = tokens.index('(')
        close = rindex(tokens, ')')
        args = tokens[open + 1:close]
        it = iter(args)
        for i, param in enumerate(params):
            current = []
            stack = []
            while True:
                try:
                    tmp = next(it)
                    if tmp == '(':
                        stack.append(tmp)
                    elif tmp == ')':
                        stack.pop()
                    elif tmp == ',':
                        if not stack:
                            break
                    current.append(tmp)
                except StopIteration:
                    break
            if param.default_value and param.default_value.tokens[-1] == '=':
                # work around for linux
                equal = current.index('=')
                value = ' '.join(current[equal + 1:])
                LOGGER.debug(f'restore default argument: {param} => {value}')
                param.default_value.tokens.append(value)
        return params
