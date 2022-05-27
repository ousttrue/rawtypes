from .basetype import BaseType
from ..parser.function_cursor import FunctionCursor


class FunctionProto(BaseType):
    def __init__(self, function: FunctionCursor) -> None:
        super().__init__(function.cursor.spelling, True)
        self.function = function
