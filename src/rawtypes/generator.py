from typing import List
import pathlib
from .header import Header
from .parser import Parser
from rawtypes.rawtypes_writer import write


def generate(headers: List[Header], package_dir: pathlib.Path):

    parser = Parser([header.path for header in headers])
    parser.traverse()

    write(package_dir, parser, headers)
