import pathlib
import os
import platform

if platform.system()=='Windows':
    VCPKG_DIR = pathlib.Path(os.environ['VCPKG_DIR'])
    VCPKG_INCLUDE = VCPKG_DIR / 'installed/x64-windows/include'
else:
    VCPKG_INCLUDE = pathlib.Path('/usr/include')
