from typing import List, Optional, Callable
import logging
import pathlib


logger = logging.getLogger(__name__)


class Header:
    def __init__(self, path: pathlib.Path, *,
                 prefix: str = '',
                 include_dirs: List[pathlib.Path] = None,
                 begin='',
                 before_include='',
                 after_include='',
                 definitions: List[str] = None,
                 include_only=False,
                 if_include: Callable[[str], bool] = lambda _: True) -> None:
        self.path = path
        self.prefix = prefix
        self.include_dirs = include_dirs or ()
        self.definitions = definitions or ()
        self.current_nemespace: Optional[str] = None
        self.begin = begin
        self.before_include = before_include
        self.after_include = after_include
        self.include_only = include_only
        self.if_include = if_include
