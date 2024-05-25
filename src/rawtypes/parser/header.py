from typing import Callable, NamedTuple
import logging
import pathlib


logger = logging.getLogger(__name__)


class StructConfiguration(NamedTuple):
    name: str
    methods: bool = False


class Header:
    def __init__(
        self,
        path: pathlib.Path,
        *,
        prefix: str = "",
        include_dirs: list[pathlib.Path] | None = None,
        begin: str = "",
        before_include: str = "",
        after_include: str = "",
        definitions: list[str] | None = None,
        include_only: bool = False,
        if_include: Callable[[str], bool] = lambda _: True,
        additional_functions: dict[str, str] | None = None,
        structs: list[StructConfiguration] | None = None
    ) -> None:
        self.path = path
        self.prefix = prefix
        self.include_dirs = include_dirs or ()
        self.definitions = definitions or ()
        self.current_namespace: str | None = None
        self.begin = begin
        self.before_include = before_include
        self.after_include = after_include
        self.include_only = include_only
        self.if_include = if_include
        self.additional_functions = additional_functions
        self.structs = {s.name: s for s in structs or []}
