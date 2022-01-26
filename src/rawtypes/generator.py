from typing import List, Optional
import pathlib
from .header import Header
from .parser import Parser
from rawtypes.rawtypes_writer import write


class Generator:
    def __init__(self) -> None:
        self.parser: Optional[Parser] = None
        self.headers: List[Header] = []

    def parse(self, *headers: Header):
        self.headers = list(headers)
        self.parser = Parser([header.path for header in headers])
        self.parser.traverse()

    def generate(self, package_dir: pathlib.Path) -> pathlib.Path:
        match self.parser:
            case Parser():
                return write(package_dir, self.parser, self.headers)
        raise Exception()


def generate(headers: List[Header], package_dir: pathlib.Path) -> pathlib.Path:
    generator = Generator()
    generator.parse(*headers)
    return generator.generate(package_dir)
