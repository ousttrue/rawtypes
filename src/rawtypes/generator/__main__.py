import argparse
import logging
import pathlib
from . import zig_generator
from ..parser import Header
from ..clang_util.generate_cindex_stub import get_cindex_module


def main():
    logging.basicConfig(
        format="[%(levelname)s] %(filename)s:%(lineno)d => %(message)s",
        level=logging.DEBUG,
    )

    parser = argparse.ArgumentParser(
        prog="rawtypes.generator",
        description="parse c header and generate binding",
    )
    parser.add_argument("-s", "--src", type=pathlib.Path, required=True)
    parser.add_argument("-d", "--dst", type=pathlib.Path, required=True)

    args = parser.parse_args()
    print(args.src, args.dst)

    generator = zig_generator.ZigGenerator(
        Header(
            args.src,
            definitions=[
                "_WIN32=1",
                "CINDEX_EXPORTS=1",
                "_CINDEX_LIB_=1",
                # 'CINDEX_LINKAGE='
            ],
        ),
        use_mangling=False,
    )   
    generator.generate(args.dst)


if __name__ == "__main__":
    main()
