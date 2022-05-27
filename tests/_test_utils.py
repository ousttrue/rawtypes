from typing import Callable, Tuple
from rawtypes.clang import cindex
from rawtypes.generator.python_generator import PythonGenerator
from rawtypes import interpreted_types

generator = PythonGenerator()


def parse_source(src: str) -> cindex.TranslationUnit:
    from rawtypes import clang_util
    unsaved = clang_util.Unsaved('tmp.h', src)
    return clang_util.get_tu('tmp.h', unsaved=[unsaved])


def first(tu: cindex.TranslationUnit, pred: Callable[[cindex.Cursor], bool]) -> cindex.Cursor:
    for cursor in tu.cursor.get_children():  # type: ignore
        if pred(cursor):
            return cursor

    raise RuntimeError()


def _parse_get_func(src: str) -> Tuple[cindex.TranslationUnit, cindex.Cursor]:
    tu = parse_source(src)
    return tu, first(tu, lambda cursor: cursor.kind ==
                     cindex.CursorKind.FUNCTION_DECL)


def parse_get_result_type(src: str) -> interpreted_types.BaseType:
    tu, c = _parse_get_func(src)
    return generator.type_manager.from_cursor(c.result_type, c)


def parse_get_param_type(i: int, src: str) -> interpreted_types.BaseType:
    tu, c = _parse_get_func(src)
    from rawtypes.parser.function_cursor import FunctionCursor
    p = FunctionCursor(c.result_type, (c,)).params[i].cursor
    return generator.type_manager.from_cursor(p.type, p)
