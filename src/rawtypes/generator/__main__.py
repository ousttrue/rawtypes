from typing import List
import argparse
import logging
import pathlib
from . import zig_generator
from ..parser import Header


def main():
    logging.basicConfig(
        format="[%(levelname)s] %(filename)s:%(lineno)d => %(message)s",
        level=logging.DEBUG,
    )

    parser = argparse.ArgumentParser(
        prog="rawtypes.generator",
        description="parse c header and generate binding",
    )
    parser.add_argument("-s", "--src", type=pathlib.Path, required=True, nargs='+')
    parser.add_argument("-i", "--include", type=pathlib.Path, nargs='*')
    parser.add_argument("-d", "--dst", type=pathlib.Path, required=True)

    args = parser.parse_args()
    print(args.src, args.dst)

    headers: List[Header] = [        Header(
            src,
            definitions=[
                # "_WIN32=1",
                # "CINDEX_EXPORTS=1",
                # "_CINDEX_LIB_=1",
                # 'CINDEX_LINKAGE='
            ],
        ) for src in args.src]

    generator = zig_generator.ZigGenerator(
        *headers,
        include_dirs=args.include,
        use_mangling=False,
    )
    generator.generate(args.dst)


if __name__ == "__main__":
    main()
