from typing import Callable
import setuptools
import pathlib
import sys
import os
import platform


HERE = pathlib.Path(__file__).absolute().parent
sys.path.append(str(HERE / "src"))


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


def download_clang_cindex(base_url: str, dst_dir: pathlib.Path) -> None:
    """
    downlod clang package.
    save as `rawtypes.clang`
    """
    http_get(base_url, dst_dir, "__init__.py")
    http_get(base_url, dst_dir, "cindex.py", patch_enum)
    http_get(base_url, dst_dir, "enumerations.py")


def main() -> None:
    for k, v in LLVM_URL_MAP.items():
        dst = HERE / f"src/rawtypes/clang{k}"
        download_clang_cindex(v, dst)

    setuptools.setup(
        name="rawtypes",
        use_scm_version=True,
        setup_requires=["setuptools_scm"],
        # package
        package_dir={"": "src"},
        packages=setuptools.find_packages("src"),
        package_data={"rawtypes.generator": ["templates/*"]},
        install_requires=["Jinja2"],
        # meta-data
        description="A code generator using libclang for a python extension.",
        long_description=(HERE / "README.md").read_text(),
        long_description_content_type="text/markdown",
        author="ousttrue",
        project_urls={
            "Documentation": "https://ousttrue.github.io/rawtypes/",
            "Source": "https://github.com/ousttrue/rawtypes",
        },
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "Topic :: Software Development :: Build Tools",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3.10",
        ],
    )


if __name__ == "__main__":
    main()
