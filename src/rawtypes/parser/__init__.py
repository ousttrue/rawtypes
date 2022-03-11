from typing import Iterable
import pathlib
from .parser import Parser


def parse(*headers: pathlib.Path, include_dirs: Iterable[pathlib.Path] = ()) -> Parser:
    return Parser.parse([header for header in headers], include_dirs=include_dirs)
