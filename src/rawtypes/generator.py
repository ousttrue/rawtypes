from typing import List
import pathlib
from .header import Header
from .parser import Parser
from . import rawtypes_writer
from .interpreted_types import *
from jinja2 import Environment, PackageLoader, select_autoescape


class Generator:
    def __init__(self, *headers: Header, include_dirs=[]) -> None:
        self.headers = list(headers)

        targets = []
        for header in headers:
            targets.append(header.path)
            include_dirs += header.include_dirs
        self.parser = Parser(
            [header.path for header in headers], include_dirs=include_dirs)
        self.parser.traverse()
        self.types = TypeManager()

        self.env = Environment(
            loader=PackageLoader("rawtypes"),
        )

    def generate(self, package_dir: pathlib.Path) -> pathlib.Path:
        cpp_path = package_dir / 'rawtypes/implmodule.cpp'
        cpp_path.parent.mkdir(parents=True, exist_ok=True)

        modules = []
        headers = []
        for header in self.headers:
            # separate header to submodule
            info = rawtypes_writer.ModuleInfo(header.path.stem)
            sio = io.StringIO()
            info.write_to(sio)
            modules.append(sio.getvalue())

            sio = io.StringIO()
            for method in rawtypes_writer.write_header(sio, self, header, package_dir):
                info.functios.append(method)
            headers.append(sio.getvalue())

        with cpp_path.open('w') as w:
            template = self.env.get_template("impl.cpp")
            w.write(template.render(headers=headers, modules=modules))

        return cpp_path


def generate(headers: List[Header], package_dir: pathlib.Path) -> pathlib.Path:
    generator = Generator(*headers)
    return generator.generate(package_dir)
