import pathlib
import os

VCPKG_DIR = pathlib.Path(os.environ['VCPKG_DIR'])
VCPKG_INCLUDE = VCPKG_DIR / 'installed/x64-windows/include'
