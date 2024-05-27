import argparse
import pathlib
import logging
from . import generate


def main():
    logging.basicConfig(
        format="[%(levelname)s] %(filename)s:%(lineno)d => %(message)s",
        level=logging.DEBUG,
    )
    parser = argparse.ArgumentParser(
        prog="cindex stub generator",
        description="pyi from LLVM/include/clang-c/Index.h",
    )
    parser.add_argument(
        "--src",
        help="path to clang-c/Index.h",
        type=pathlib.Path,
        default="C:/Program Files/LLVM/include/clang-c/Index.h",
    )
    # ubuntu: libclang-13-dev
    # "/usr/lib/llvm-13/include/clang-c/Index.h"

    parser.add_argument(
        "dst",
        help="root directory for pyi. DST_DIR/rawtypes/clang/cindex.pyi will be generated.",
        type=pathlib.Path,
    )
    args = parser.parse_args()

    generate(args.src, args.dst)


if __name__ == "__main__":
    main()
