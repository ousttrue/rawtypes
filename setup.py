import setuptools
import pathlib
import sys


HERE = pathlib.Path(__file__).absolute().parent


def main() -> None:
    sys.path.append(str(HERE / "src"))
    import rawtypes.cindex_util
    import rawtypes.gen_cindex_stub

    # download cindex.py
    dst_dir = HERE / "src/rawtypes/clang"
    rawtypes.cindex_util.download_clang_cindex(dst_dir)

    # generate cindex.pyi
    rawtypes.gen_cindex_stub.generate(rawtypes.cindex_util.CINDEX_HEADER, HERE / "src")

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
