from typing import List, Optional, Callable, Dict, NamedTuple
import logging
import pathlib


logger = logging.getLogger(__name__)


class StructConfiguration(NamedTuple):
    name: str
    methods: bool = False


class Header:
    def __init__(self, path: pathlib.Path, *,
                 prefix: str = '',
                 include_dirs: Optional[List[pathlib.Path]] = None,
                 begin='',
                 before_include='',
                 after_include='',
                 definitions: Optional[List[str]] = None,
                 include_only=False,
                 if_include: Callable[[str], bool] = lambda _: True,
                 additional_functions: Optional[Dict[str, str]] = None,
                 structs: Optional[List[StructConfiguration]] = None) -> None:
        self.path = path
        self.prefix = prefix
        self.include_dirs = include_dirs or ()
        self.definitions = definitions or ()
        self.current_namespace: Optional[str] = None
        self.begin = begin
        self.before_include = before_include
        self.after_include = after_include
        self.include_only = include_only
        self.if_include = if_include
        self.additional_functions = additional_functions
        self.structs = {s.name: s for s in structs or []}
