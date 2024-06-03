from typing import Callable
import pathlib, re


CINDEX_HEADER: pathlib.Path = pathlib.Path(
    "C:/Program Files/LLVM/include/clang-c/Index.h"
)
if not CINDEX_HEADER.exists():
    raise FileExistsError(CINDEX_HEADER)

CINDEX_VERSION_MINOR_PATTERN = re.compile(r"#define CINDEX_VERSION_MINOR (\d+)")
m = CINDEX_VERSION_MINOR_PATTERN.search(CINDEX_HEADER.read_text())
if not m:
    raise RuntimeError()
minor_version = m.group(1)

CINDEX_VERSION_MINOR_TO_LLVM_VERSION_MAP: dict[str, str] = {
    # https://github.com/llvm/llvm-project/blob/llvmorg-17.0.6/clang/include/clang-c/Index.h
    "64": "17",
    # https://github.com/llvm/llvm-project/blob/llvmorg-16.0.6/clang/include/clang-c/Index.h
    "63": "16",
    # https://github.com/llvm/llvm-project/blob/llvmorg-15.0.7/clang/include/clang-c/Index.h
    "62": "15",
}
LLVM_VERSION = CINDEX_VERSION_MINOR_TO_LLVM_VERSION_MAP[minor_version]


LLVM_URL_MAP: dict[str, str] = {
    "18": "https://github.com/llvm/llvm-project/raw/llvmorg-18.1.6/clang/bindings/python/clang/",
    "17": "https://github.com/llvm/llvm-project/raw/llvmorg-17.0.6/clang/bindings/python/clang/",
    "16": "https://github.com/llvm/llvm-project/raw/llvmorg-16.0.6/clang/bindings/python/clang/",
    "15": "https://github.com/llvm/llvm-project/raw/llvmorg-15.0.7/clang/bindings/python/clang/",
}


def patch_enum(src: str) -> str:
    return src.replace(
        "import clang.enumerations", "from . import enumerations"
    ).replace("clang.enumerations", "enumerations")


def http_get(
    url_base: str,
    dst_dir: pathlib.Path,
    name: str,
    patch: Callable[[str], str] | None = None,
):
    dst = dst_dir / name
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    url = url_base + name
    print(url)
    import urllib.request

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        data = res.read().decode("utf-8")
        if patch:
            data = patch(data)
        dst.write_text(data)


def download_clang_cindex(dst_dir: pathlib.Path) -> None:
    """
    downlod clang package.
    save as `rawtypes.clang`
    """
    base_url = LLVM_URL_MAP[LLVM_VERSION]

    http_get(base_url, dst_dir, "__init__.py")
    http_get(base_url, dst_dir, "cindex.py", patch_enum)
    http_get(base_url, dst_dir, "enumerations.py")
