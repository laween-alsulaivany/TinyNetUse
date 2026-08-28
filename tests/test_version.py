from pathlib import Path
import tomllib

import pytest

from build_version_info import windows_version_tuple, write_version_info
from tinynetuse.version import __version__


ROOT = Path(__file__).parents[1]


def test_pyproject_uses_the_canonical_package_version():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["dynamic"] == ["version"]
    assert project["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "tinynetuse.version.__version__"
    }


def test_pyproject_declares_the_supported_python_range():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["requires-python"] == ">=3.14,<3.15"


def test_project_uses_the_src_package_entry_point():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["tool"]["setuptools"]["package-dir"] == {"": "src"}
    assert project["project"]["gui-scripts"] == {
        "TinyNetUse": "tinynetuse.app:main"
    }


def test_runtime_and_dev_dependencies_are_separate():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = "\n".join(project["project"]["dependencies"]).casefold()
    dev = "\n".join(
        project["project"]["optional-dependencies"]["dev"]
    ).casefold()

    assert "pyside6" in runtime
    assert "psutil" in runtime
    assert "pywin32" in runtime
    assert "pyinstaller" not in runtime
    assert "pytest" not in runtime
    assert "pyinstaller" in dev
    assert "pytest" in dev
    assert "pytest-qt" in dev


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("1.2.3", (1, 2, 3, 0)),
        ("1.2.3.4", (1, 2, 3, 4)),
    ],
)
def test_windows_version_tuple(version, expected):
    assert windows_version_tuple(version) == expected


def test_windows_version_tuple_rejects_non_numeric_versions():
    with pytest.raises(ValueError):
        windows_version_tuple("1.2-beta")


def test_generated_executable_metadata_uses_application_version(tmp_path):
    output = tmp_path / "windows-version-info.txt"

    write_version_info(output)

    metadata = output.read_text(encoding="utf-8")
    file_version = ".".join(
        str(part) for part in windows_version_tuple(__version__)
    )
    assert f"StringStruct('FileVersion', '{file_version}')" in metadata
    assert f"StringStruct('ProductVersion', '{__version__}')" in metadata
    assert "StringStruct('ProductName', 'TinyNetUse')" in metadata
    assert "StringStruct('CompanyName', 'Laween Al-Sulaivany')" in metadata
    assert "StringStruct('OriginalFilename', 'TinyNetUse.exe')" in metadata


def test_build_passes_the_canonical_version_to_inno_setup():
    build_script = (ROOT / "build.bat").read_text(encoding="utf-8")
    installer = (ROOT / "packaging/installer.iss").read_text(encoding="utf-8")

    assert "build_version_info.py --print-version" in build_script
    assert "/DAppVersion=%APP_VERSION%" in build_script
    assert "packaging\\installer.iss" in build_script
    assert "#ifndef AppVersion" in installer


def test_portable_release_paths_stay_relative_to_the_repository():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )

    assert "--add-data \"assets;assets\"" in workflow
    assert "--specpath build\\portable-spec" not in workflow
