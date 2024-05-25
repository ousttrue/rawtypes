import abc
import pathlib
from ..parser.header import Header
from ..parser import Parser
from ..interpreted_types import TypeManager


class GeneratorBase(metaclass=abc.ABCMeta):
    def __init__(
        self,
        *headers: Header,
        use_typdef: bool,
        include_dirs: list[pathlib.Path] | None = None,
        target: str = "",
        use_mangling: bool = True
    ) -> None:
        # parse
        if not include_dirs:
            include_dirs = []
        definitions: list[str] = []
        for header in headers:
            include_dirs.extend(header.include_dirs)
            definitions.extend(header.definitions)
        self.parser = Parser.parse(
            [header.path for header in headers],
            include_dirs=include_dirs,
            definitions=definitions,
            target=target,
            use_mangling=use_mangling,
        )
        self.headers = [header for header in headers if not header.include_only]
        # prepare
        self.type_manager = TypeManager(use_typedef=use_typdef)
        from jinja2 import Environment, PackageLoader

        self.env = Environment(
            loader=PackageLoader("rawtypes.generator"),
        )

    @abc.abstractmethod
    def generate(
        self,
        package_dir: pathlib.Path,
        cpp_path: pathlib.Path,
        *,
        function_custom=[],
        is_exclude_function=None
    ):
        pass
