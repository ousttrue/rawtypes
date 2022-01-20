from typing import List, Optional
import logging
import pathlib


logger = logging.getLogger(__name__)


class Header:
    def __init__(self, dir: pathlib.Path, file: str, *, prefix: str = '', include_dirs: List[pathlib.Path] = None) -> None:
        self.path = dir / file
        self.prefix = prefix
        self.include_dirs = include_dirs or ()
        self.current_nemespace: Optional[str] = None
