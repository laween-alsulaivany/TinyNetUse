"""Generate the Windows version resource used by PyInstaller."""

import argparse
from pathlib import Path
import re
import sys


SOURCE_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SOURCE_DIR))

from tinynetuse.version import __version__


PRODUCT_NAME = "TinyNetUse"
PUBLISHER = "Laween Al-Sulaivany"
COPYRIGHT = f"Copyright (C) 2025-2026 {PUBLISHER}"


# Windows stores file versions as four integers.
def windows_version_tuple(version):
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?", version):
        raise ValueError("Version must contain three or four numeric parts")
    parts = [int(part) for part in version.split(".")]
    return tuple(parts + [0] * (4 - len(parts)))


# Write the text format accepted by PyInstaller's --version-file option.
def write_version_info(path):
    version_tuple = windows_version_tuple(__version__)
    file_version = ".".join(str(part) for part in version_tuple)
    contents = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '{PUBLISHER}'),
          StringStruct('FileDescription', 'TinyNetUse Network Speed Monitor'),
          StringStruct('FileVersion', '{file_version}'),
          StringStruct('InternalName', '{PRODUCT_NAME}'),
          StringStruct('LegalCopyright', '{COPYRIGHT}'),
          StringStruct('OriginalFilename', '{PRODUCT_NAME}.exe'),
          StringStruct('ProductName', '{PRODUCT_NAME}'),
          StringStruct('ProductVersion', '{__version__}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?")
    parser.add_argument("--print-version", action="store_true")
    args = parser.parse_args()

    if args.print_version:
        print(__version__)
    if args.output:
        write_version_info(args.output)
    if not args.print_version and not args.output:
        parser.error("provide an output path or --print-version")


if __name__ == "__main__":
    main()
