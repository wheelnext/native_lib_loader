# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Common test helpers."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import tomlkit
from packaging.version import parse as parse_version

DIR = Path(__file__).parent
ROOT_DIR = DIR.parent.parent
MANAGER_DIR = ROOT_DIR / "pkgs" / "shared_lib_manager"
CONSUMER_DIR = ROOT_DIR / "pkgs" / "shared_lib_consumer"

COMMON_PIP_ARGS = (
    "-m",
    "pip",
    "--disable-pip-version-check",
    "--no-cache-dir",
)

ENV_ROOT = DIR / "generated"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Set up the option for saving output files."""
    parser.addoption(
        "--keep", action="store_true", help="Whether or not to persist generated files."
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure whether or not to save the outputs for later inspection."""
    if not config.getoption("--keep"):
        global ENV_ROOT  # noqa: PLW0603
        ENV_ROOT = Path(tempfile.mkdtemp())
        config.add_cleanup(lambda: shutil.rmtree(ENV_ROOT))


@pytest.fixture(scope="session")
def package_wheelhouse() -> Path:
    """Produce the wheelhouse where the built packages go."""
    return ENV_ROOT / "package_wheelhouse"


def create_patched_library(
    tmp_path_factory: pytest.TempPathFactory, pkg_source_dir: Path
) -> Path:
    """Produce a copy of the source package with a modified version.

    The incremented version ensures that this version is preferred to any other
    available on public indexes.
    """
    tmp_package_dir = tmp_path_factory.mktemp(pkg_source_dir.name)

    shutil.copytree(
        pkg_source_dir,
        tmp_package_dir,
        ignore=shutil.ignore_patterns(
            "tests*", "build*", "dist*", "*.egg-info*", ".git"
        ),
        dirs_exist_ok=True,
    )

    pyproject_file = tmp_package_dir / "pyproject.toml"
    with Path(pyproject_file).open() as f:
        pyproject = tomlkit.load(f)
    project_data = pyproject["project"]

    version = parse_version(project_data["version"])
    project_data["version"] = f"{version.major + 1}.{version.minor}.{version.micro}"
    with Path(pyproject_file).open("w") as f:
        tomlkit.dump(pyproject, f)

    return tmp_package_dir


def make_wheel(
    package_wheelhouse: Path, package_dir: Path
) -> subprocess.CompletedProcess:
    """Build a wheel for the package.

    Parameters
    ----------
    package_wheelhouse : Path
        The directory where the wheel should be stored.
    package_dir : Path
        The directory of the package to be built.

    Returns
    -------
    subprocess.CompletedProcess
        The result of the wheel building process.

    """
    return subprocess.run(
        [
            "python",
            *COMMON_PIP_ARGS,
            "wheel",
            "--no-deps",
            "--wheel-dir",
            package_wheelhouse,
            package_dir,
        ],
        check=False,
    )


@pytest.fixture(scope="session", autouse=True)
def shared_lib_manager_wheel(
    tmp_path_factory: pytest.TempPathFactory, package_wheelhouse: Path
) -> subprocess.CompletedProcess:
    """Produce a wheel for the shared_lib_manager."""
    tmp_package_dir = create_patched_library(tmp_path_factory, MANAGER_DIR)

    # Add the monkeypatching to the library.
    # TODO: Also just add the file directly in tests so it's not in the source.
    loader_init_file = tmp_package_dir / "shared_lib_manager.py"
    with Path(loader_init_file).open("a") as f, Path(
        DIR / "monkeypatch.py"
    ).open() as mp:
        f.write(mp.read())
    return make_wheel(package_wheelhouse, tmp_package_dir)


@pytest.fixture(scope="session", autouse=True)
def shared_lib_consumer_wheel(
    tmp_path_factory: pytest.TempPathFactory, package_wheelhouse: Path
) -> subprocess.CompletedProcess:
    """Produce a wheel for the shared_lib_manager."""
    tmp_package_dir = create_patched_library(tmp_path_factory, CONSUMER_DIR)
    return make_wheel(package_wheelhouse, tmp_package_dir)


@pytest.fixture(scope="session", params=("LOCAL", "GLOBAL"))
def load_mode(request: pytest.FixtureRequest) -> str:
    """Generate valid modes for opening a library."""
    return request.param
