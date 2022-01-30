from typing import Iterable
import pathlib
from .parser import Parser
from .header import Header


def parse(*headers: pathlib.Path, include_dirs: Iterable[pathlib.Path] = ()) -> Parser:
    parser = Parser([header for header in headers], include_dirs=include_dirs)
    parser.traverse()
    return parser
