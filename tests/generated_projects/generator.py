"""Generate a set of test cases for the native_lib_loader package."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import textwrap
import venv
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import tomlkit
from jinja2 import Environment, FileSystemLoader
from packaging.version import parse as parse_version

if TYPE_CHECKING:
    from os import PathLike


DIR = Path(__file__).parent
NATIVE_LIB_DIR = DIR.parent.parent


class VEnv:
    """Convenience class for managing a virtual environment for testing.

    Parameters
    ----------
    root : pathlib.Path
        The root directory for the virtual environment.

    """

    def __init__(self, root: Path):
        self.env_dir = root / "env"
        Path(self.env_dir).mkdir(exist_ok=True)

        self.wheelhouse = root / "wheelhouse"
        self.cache_dir = root / "cache"

        self.executable = Path(self.env_dir) / "bin" / "python"
        # Allow for rerunning the script on preexisting test directories for local
        # debugging and interactive exploration.
        if not Path(self.executable).exists:
            venv.create(
                self.env_dir,
                clear=True,
                with_pip=True,
            )

        self._pip_cmd_base = [
            self.executable,
            "-m",
            "pip",
            "--disable-pip-version-check",
            "--cache-dir",
            self.cache_dir,
        ]
        self._install_native_lib_loader()

    def _install_native_lib_loader(self) -> None:
        # Build the native_lib_loader_dir wheel in a temporary directory where we can
        # bump the version to ensure that it is preferred to any other available wheels.
        native_lib_loader_dir = tempfile.TemporaryDirectory()

        shutil.copytree(
            NATIVE_LIB_DIR,
            native_lib_loader_dir.name,
            ignore=shutil.ignore_patterns("tests*", "build*", "dist*", "*.egg-info*"),
            dirs_exist_ok=True,
        )

        pyproject_file = Path(native_lib_loader_dir.name) / "pyproject.toml"
        with Path(pyproject_file).open() as f:
            pyproject = tomlkit.load(f)
        project_data = pyproject["project"]

        version = parse_version(project_data["version"])
        project_data["version"] = f"{version.major + 1}.{version.minor}.{version.micro}"
        with Path(pyproject_file, "w").open() as f:
            tomlkit.dump(pyproject, f)

        self.wheel(native_lib_loader_dir.name)

    def install(self, *args: list) -> None:
        """Install a package into the virtual environment with `pip install`.

        Parameters
        ----------
        *args
            Arguments to pass to `pip install`.

        """
        return subprocess.run(
            [
                self._pip_cmd_base,
                *(
                    "install",
                    "--find-links",
                    self.wheelhouse,
                    *args,
                ),
            ],
            check=True,
        )

    def wheel(self, package_dir: PathLike, *args: list) -> None:
        """Build a wheel with `pip wheel`.

        Parameters
        ----------
        package_dir : PathLike
            The directory containing the package to build.
        *args
            Arguments to pass to `pip install`.

        """
        return subprocess.run(
            [
                self._pip_cmd_base,
                *(
                    "wheel",
                    "-v",
                    "--no-deps",
                    "--wheel-dir",
                    self.wheelhouse,
                    "--find-links",
                    self.wheelhouse,
                    package_dir,
                    *args,
                ),
            ],
            check=True,
        )

    def run(self, code: str) -> None:
        """Run Python code in the virtual environment.

        Parameters
        ----------
        code : str
            The Python code to run.

        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py") as f:
            f.write(textwrap.dedent(code))
            f.flush()
            script = f.name
            return subprocess.run([self.executable, script], check=True)


@lru_cache
def jinja_environment() -> Environment:
    """Create a Jinja2 environment for rendering templates."""
    template_dir = (DIR / "templates",)
    return Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def generate_from_template(
    output_path: PathLike,
    template_name: str,
    template_args: dict | None = None,
) -> None:
    """Generate a file from a Jinja2 template.

    Parameters
    ----------
    output_path : PathLike
        The path to write the generated file to.
    template_name : str
        The name of the template file to use.
    template_args : dict, optional
        Arguments to pass to the template.

    """
    template = jinja_environment().get_template(template_name)

    template_args = template_args or {}
    content = template.render(**template_args)
    with Path(output_path, mode="w", encoding="utf-8").open() as f:
        f.write(content)


def make_cpp_lib(root: PathLike, library_name: str) -> None:
    """Generate a standard C++ library with a CMake build system.

    Parameters
    ----------
    root : PathLike
        The root directory for the library.
    library_name : str
        The name of the library.

    """
    root = Path(root)

    lib_src_dir = root / "cpp"
    if Path(lib_src_dir).exists:
        return
    lib_cmake_dir = lib_src_dir / "cmake"
    Path(lib_cmake_dir)

    generate_from_template(
        lib_src_dir / "CMakeLists.txt",
        "cpp_CMakeLists.txt",
        {"library_name": library_name},
    )
    generate_from_template(
        lib_src_dir / "example.h",
        "example.h",
        {"library_name": library_name},
    )
    generate_from_template(
        lib_src_dir / "example.c",
        "example.c",
        {"library_name": library_name},
    )
    generate_from_template(
        lib_cmake_dir / "config.cmake.in",
        "cpp_config.cmake.in",
        {"library_name": library_name},
    )


def make_cpp_pkg(root: PathLike, package_name: str, library_name: str) -> None:
    """Generate a Python package exporting a native library.

    Parameters
    ----------
    root : PathLike
        The root directory for the package.
    package_name : str
        The name of the package.
    library_name : str
        The name of the library.

    """
    root = Path(root)

    lib_pkg_dir = root / package_name
    if Path(lib_pkg_dir).exists:
        return
    lib_dir = lib_pkg_dir / package_name
    Path(lib_dir)

    generate_from_template(
        lib_pkg_dir / "CMakeLists.txt",
        "cpp_py_CMakeLists.txt",
        {"package_name": package_name},
    )
    generate_from_template(
        lib_pkg_dir / "pyproject.toml",
        "cpp_pyproject.toml",
        {"package_name": package_name},
    )
    generate_from_template(lib_dir / "__init__.py", "cpp___init__.py")
    generate_from_template(
        lib_dir / "load.py",
        "load.py",
        {"library_name": library_name},
    )

    make_cpp_lib(lib_dir, library_name)


def make_python_pkg(
    root: PathLike,
    package_name: str,
    library_name: str,
    cpp_package_name: str,
    dependencies: list | None = None,
    build_dependencies: list | None = None,
) -> None:
    """Generate a Python package with a native library dependency.

    Parameters
    ----------
    root : PathLike
        The root directory for the package.
    package_name : str
        The name of the package.
    library_name : str
        The name of the library.
    cpp_package_name : str
        The name of the C++ package.
    dependencies : list, optional
        The runtime dependencies for the package.
    build_dependencies : list, optional
        The build dependencies for the package.

    """
    root = Path(root)

    pylib_pkg_dir = root / package_name
    if Path(pylib_pkg_dir).exists:
        return
    pylib_dir = pylib_pkg_dir / package_name
    Path(pylib_dir)

    dependencies = dependencies or []
    build_dependencies = build_dependencies or []

    generate_from_template(
        pylib_pkg_dir / "pyproject.toml",
        "py_pyproject.toml",
        {
            "package_name": package_name,
            "dependencies": dependencies,
            "build_dependencies": build_dependencies,
        },
    )
    generate_from_template(
        pylib_pkg_dir / "CMakeLists.txt",
        "py_CMakeLists.txt",
        {
            "library_name": library_name,
            "package_name": package_name,
            "dependencies": dependencies,
            "build_dependencies": build_dependencies,
        },
    )
    generate_from_template(
        pylib_dir / "__init__.py",
        "py___init__.py",
        {
            "package_name": package_name,
            "cpp_package_name": cpp_package_name,
            "dependencies": dependencies,
            "build_dependencies": build_dependencies,
        },
    )
    generate_from_template(
        pylib_dir / "pylibexample.c",
        "pylibexample.c",
        {
            "package_name": package_name,
            "dependencies": dependencies,
            "build_dependencies": build_dependencies,
        },
    )


def build_cmake_project(root: PathLike) -> None:
    """Build a CMake project.

    Parameters
    ----------
    root : PathLike
        The root directory for the project.

    """
    subprocess.run(
        ["cmake", "-S", root, "-B", root / "build"],
        check=True,
    )
    subprocess.run(
        ["cmake", "--build", root / "build"],
        check=True,
    )


def names(base_name: str) -> tuple[str, str, str]:
    """Generate package names based on the standard scheme.

    Parameters
    ----------
    base_name : str
        The base name for the library.

    """
    library_name = base_name
    cpp_package_name = f"lib{library_name}"
    python_package_name = f"pylib{library_name}"
    return library_name, cpp_package_name, python_package_name


def test_basic() -> None:
    """Test the generation of a basic library with a C++ and Python package.

    In this case everything is largely expected to work. It's a single library with a
    single function that is single-sourced.
    """
    root = DIR / "basic_lib"
    library_name, cpp_package_name, python_package_name = names("example")
    make_cpp_pkg(root, cpp_package_name, library_name)
    make_python_pkg(
        root,
        python_package_name,
        library_name,
        cpp_package_name,
        ["native_lib_loader", "libexample"],
        ["scikit-build-core", "libexample"],
    )

    env = VEnv(root)
    env.wheel(root / "libexample")
    env.wheel(root / "pylibexample")
    env.install("pylibexample", "--no-index")
    env.run(
        """
        import pylibexample
        print(f"The square of 4 is {pylibexample.pylibexample.square(4)}")
        """,
    )


def test_lib_only_available_at_build() -> None:
    """Test the behavior when a library is only available at build time.

    In this case we expect to see runtime failures in the form of loader errors.
    """
    root = DIR / "lib_only_available_at_build"
    library_name, cpp_package_name, python_package_name = names("example")
    make_cpp_lib(root, library_name)
    make_python_pkg(
        root,
        python_package_name,
        library_name,
        cpp_package_name,
        ["native_lib_loader"],
        ["scikit-build-core"],
    )

    build_cmake_project(root / "cpp")

    env = VEnv(root)
    env.wheel(
        root / "pylibexample",
        "--config-settings=cmake.args=-DCMAKE_PREFIX_PATH="
        + str(root / "cpp" / "build"),
    )
    env.install("pylibexample", "--no-index")
    env.run("import pylibexample")


if __name__ == "__main__":
    test_basic()
    test_lib_only_available_at_build()
