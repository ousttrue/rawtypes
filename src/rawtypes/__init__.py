from typing import List, Callable
from ._version import *
import logging
import pathlib
from .parser import Parser
from .header import Header

logger = logging.getLogger(__name__)


def generate(headers: List[Header], package_dir: pathlib.Path, write: Callable[[pathlib.Path, Parser, List[Header]], None]):

    parser = Parser([header.path for header in headers])
    parser.traverse()

    write(package_dir, parser, headers)

    #
    # enum
    #
    enum_py_path = package_dir / 'imgui_enum.py'
    with enum_py_path.open('w') as enum_py:
        enum_py.write('''from enum import IntEnum

''')
        for e in parser.enums:
            e.write_to(enum_py)
