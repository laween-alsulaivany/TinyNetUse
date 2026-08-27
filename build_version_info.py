"""Generate the Windows version resource used by PyInstaller."""

from tinynetuse.version import __version__
import argparse
from pathlib import Path
import re
import sys


SOURCE_DIR = Path(__file__).resolve().parent / "src"
# load the package version from the source tree when this script runs from the repo
sys.path.insert(0, str(SOURCE_DIR))


PRODUCT_NAME = "TinyNetUse"
PUBLISHER = "Laween Al-Sulaivany"
COPYRIGHT = f"Copyright (C) 2025-2026 {PUBLISHER}"


# Windows stores file versions as four integers.
def windows_version_tuple(version):
  # PyInstaller needs numeric components, while the package exposes a dotted string
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?", version):
        raise ValueError("Version must contain three or four numeric parts")
    parts = [int(part) for part in version.split(".")]
  # Windows always has four slots, so release versions get a zero build number
    return tuple(parts + [0] * (4 - len(parts)))


# Write the text format accepted by PyInstaller's --version-file option.
def write_version_info(path):
  # keep the numeric Windows version and the original package version available
    version_tuple = windows_version_tuple(__version__)
    file_version = ".".join(str(part) for part in version_tuple)
  # this is Python-like text consumed later by PyInstaller, not a native resource file
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
    # callers may point the build at a new staging directory
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def main():
  # support both build-script output and a cheap version-only check
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?")
    parser.add_argument("--print-version", action="store_true")
    args = parser.parse_args()

    if args.print_version:
      # useful to batch files and release tooling without creating a file
        print(__version__)
    if args.output:
      # writing is optional so --print-version can stay side-effect free
        write_version_info(args.output)
    if not args.print_version and not args.output:
      # reject an empty invocation instead of silently doing nothing
        parser.error("provide an output path or --print-version")


if __name__ == "__main__":
    main()
