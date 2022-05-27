import abc
import pathlib
from ..parser.header import Header
from ..parser import Parser
from ..interpreted_types import TypeManager


class GeneratorBase(metaclass=abc.ABCMeta):
    def __init__(self, *headers: Header, use_typdef: bool, include_dirs=[], target='') -> None:
        # parse
        include_dirs = sum(
            [list(header.include_dirs) for header in headers], include_dirs)
        self.parser = Parser.parse(
            [header.path for header in headers],
            include_dirs=include_dirs,
            definitions=sum([list(header.definitions)
                            for header in headers], []),
            target=target
        )
        self.headers = [
            header for header in headers if not header.include_only]
        # prepare
        self.type_manager = TypeManager(use_typedef=use_typdef)
        from jinja2 import Environment, PackageLoader
        self.env = Environment(
            loader=PackageLoader("rawtypes.generator"),
        )

    @abc.abstractmethod
    def generate(self, package_dir: pathlib.Path, cpp_path: pathlib.Path, *, function_custom=[], is_exclude_function=None):
        pass
