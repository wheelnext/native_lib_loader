"""Common test helpers."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import tomlkit
from packaging.version import parse as parse_version

DIR = Path(__file__).parent
NATIVE_LIB_DIR = DIR.parent.parent

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
        os.environ["NATIVE_LIB_LOADER_TESTING"] = "1"
        config.add_cleanup(lambda: shutil.rmtree(ENV_ROOT))


@pytest.fixture(scope="session")
def native_lib_loader_wheelhouse() -> Path:
    """Produce the wheelhouse where the native_lib_loader built wheel goes."""
    return ENV_ROOT / "nll_wheelhouse"


@pytest.fixture(scope="session", autouse=True)
def native_lib_loader_wheel(
    tmp_path_factory: pytest.TempPathFactory, native_lib_loader_wheelhouse: Path
) -> subprocess.CompletedProcess:
    """Produce a wheel for native_lib_loader.

    Build in a temporary directory where we can increment the version to ensure that
    this version is preferred to any other.
    """
    native_lib_loader_dir = tmp_path_factory.mktemp("nll_dir")

    shutil.copytree(
        NATIVE_LIB_DIR,
        native_lib_loader_dir,
        ignore=shutil.ignore_patterns(
            "tests*", "build*", "dist*", "*.egg-info*", ".git"
        ),
        dirs_exist_ok=True,
    )

    pyproject_file = native_lib_loader_dir / "pyproject.toml"
    with Path(pyproject_file).open() as f:
        pyproject = tomlkit.load(f)
    project_data = pyproject["project"]

    version = parse_version(project_data["version"])
    project_data["version"] = f"{version.major + 1}.{version.minor}.{version.micro}"
    with Path(pyproject_file).open("w") as f:
        tomlkit.dump(pyproject, f)

    return subprocess.run(
        [
            "python",
            *COMMON_PIP_ARGS,
            "wheel",
            "--no-deps",
            "--wheel-dir",
            native_lib_loader_wheelhouse,
            native_lib_loader_dir,
        ],
        check=False,
    )


@pytest.fixture(scope="session", params=("LOCAL", "GLOBAL"))
def load_mode(request: pytest.FixtureRequest) -> str:
    """Generate valid modes for opening a library."""
    return request.param
