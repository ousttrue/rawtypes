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
    result_type: cindex.Type
    cursors: Tuple[cindex.Cursor, ...]

    def __repr__(self) -> str:
        return self.spelling

    @property
    def mangled_name(self) -> str:
        return self.cursor.mangled_name

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
        return ResultContext(self.result_type, self.cursor)

    @property
    def params(self) -> List[ParamContext]:
        cursors = [child for child in self.cursor.get_children(
        ) if child.kind == cindex.CursorKind.PARM_DECL]
        values = [ParamContext(i, child) for i, child in enumerate(cursors)]
        tokens = [token.spelling for token in self.cursor.get_tokens()]

        # remove token !
        if len(tokens) > 4:
            match tokens[-4:]:
                case ['IM_FMTLIST', '(', _, ')']:
                    tokens = tokens[:-4]
                case ['IM_FMTARGS', '(', _, ')']:
                    tokens = tokens[:-4]

        stack = []
        args = [[]]
        for i in range(len(tokens)-1, -1, -1):
            match tokens[i]:
                case ')':
                    stack.append(1)
                case '(':
                    stack.pop()
                    if not stack:
                        break
                case _:
                    if len(stack) == 1 and tokens[i] == ',':
                        args.insert(0, [])
                    elif stack:
                        args[0].insert(0, tokens[i])
        if args == [[]] or args == [['void']]:
            args = []

        if args and args[-1] == ['...']:
            # TODO:
            pass
        else:
            assert(len(values) == len(args))
            for param, token in zip(values, args):
                pass

        return values
