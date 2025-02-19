# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Generate a set of test cases for the native_lib_loader package."""

from __future__ import annotations

import contextlib
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import textwrap
import venv
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from jinja2 import Environment, FileSystemLoader

if TYPE_CHECKING:
    from os import PathLike

from conftest import DIR, ENV_ROOT

sys.path.insert(0, str(DIR))


class VEnv:
    """Convenience class for managing a virtual environment for testing.

    Parameters
    ----------
    root : pathlib.Path
        The root directory for the virtual environment.

    """

    def __init__(self, root: Path, native_lib_loader_wheelhouse: Path):
        self.env_dir = root / "env"
        Path(self.env_dir).mkdir(exist_ok=True)

        self.nll_wheelhouse = str(native_lib_loader_wheelhouse)
        self.wheelhouse = str(root / "wheelhouse")
        self.cache_dir = str(root / "cache")

        self.executable = (
            str(Path(self.env_dir) / "bin" / "python")
            if platform.system() != "Windows"
            else str(Path(self.env_dir) / "Scripts" / "python.exe")
        )
        # Allow for rerunning the script on preexisting test directories for local
        # debugging and interactive exploration.
        if not Path(self.executable).exists():
            venv.create(
                self.env_dir,
                clear=True,
                with_pip=True,
            )

        self._pip_cmd_base: list[str] = [
            self.executable,
            "-m",
            "pip",
            "--disable-pip-version-check",
            "--cache-dir",
            self.cache_dir,
        ]
        # Always update pip to ensure that we have the necessary new features like
        # config-settings.
        self.install("pip", "-U")

    def install(
        self, package_name: Path | str, *args: str, editable: bool = False
    ) -> subprocess.CompletedProcess:
        """Install a package into the virtual environment with `pip install`.

        Parameters
        ----------
        package_name : str
            The name of the package to install.
        *args
            Arguments to pass to `pip install`.
        editable : bool, optional
            Whether to install the package in editable mode.

        """
        pkg_args = [package_name]
        if editable:
            pkg_args.insert(0, "-e")

        return subprocess.run(
            [
                *self._pip_cmd_base,
                *(
                    "install",
                    "--find-links",
                    self.nll_wheelhouse,
                    "--find-links",
                    self.wheelhouse,
                    *args,
                ),
                *pkg_args,
            ],
            check=True,
        )

    def wheel(
        self, package_dir: PathLike | str, *args: str
    ) -> subprocess.CompletedProcess:
        """Build a wheel with `pip wheel`.

        Parameters
        ----------
        package_dir : PathLike or str
            The directory containing the package to build.
        *args
            Arguments to pass to `pip install`.

        """
        return subprocess.run(
            [
                *self._pip_cmd_base,
                *(
                    "wheel",
                    "--no-deps",
                    "--wheel-dir",
                    self.wheelhouse,
                    "--find-links",
                    self.nll_wheelhouse,
                    "--find-links",
                    self.wheelhouse,
                    package_dir,
                    *args,
                ),
            ],
            check=True,
        )

    def run(self, code: str) -> subprocess.CompletedProcess:
        """Run Python code in the virtual environment.

        Parameters
        ----------
        code : str
            The Python code to run.

        """
        # To support Windows (prior to 3.12 when the delete_on_close parameter
        # exists) we have to manually delete the temporary file because when
        # delete=True the file cannot be reopened without following special
        # rules that we cannot control when simply executing it directly via
        # Python in the subprocess (we could with a suitable os.open call, but
        # that's not relevant here). See
        # https://docs.python.org/3/library/tempfile.html#tempfile.NamedTemporaryFile
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        f.write(textwrap.dedent(code))
        f.flush()
        f.close()
        try:
            return subprocess.run(
                [self.executable, f.name], capture_output=True, check=True
            )
        finally:
            Path(f.name).unlink()


def dir_test(base_name: str, **kwargs: str) -> Path:
    """Generate a test directory path based on the test case name.

    Parameters
    ----------
    base_name : str
        The base name for the test case.
    **kwargs
        Key-value pairs to include in the test directory name.

    """
    kwargs["test_name"] = base_name
    hasher = hashlib.sha1()
    hasher.update(json.dumps(kwargs, sort_keys=True).encode())
    dirname = ENV_ROOT / hasher.hexdigest()
    dirname.mkdir(parents=True, exist_ok=True)
    with Path(dirname / "parameters.json").open(mode="w") as f:
        json.dump(kwargs, f, sort_keys=True)
    return dirname


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
    output_path: PathLike | str,
    template_name: str,
    template_args: dict | None = None,
) -> None:
    """Generate a file from a Jinja2 template.

    Parameters
    ----------
    output_path : PathLike or str
        The path to write the generated file to.
    template_name : str
        The name of the template file to use.
    template_args : dict, optional
        Arguments to pass to the template.

    """
    template = jinja_environment().get_template(template_name)

    template_args = template_args or {}
    content = template.render(**template_args)
    with Path(output_path).open(mode="w", encoding="utf-8") as f:
        f.write(content)


def make_cpp_lib(
    root: PathLike | str,
    library_name: str,
    *,
    square_as_cube: bool = False,
    prefix: str = "",
) -> None:
    """Generate a standard C++ library with a CMake build system.

    Parameters
    ----------
    root : PathLike or str
        The root directory for the library.
    library_name : str
        The name of the library.
    square_as_cube : bool, optional
        Whether to implement the square function as a cube function.
    prefix : str, optional
        A prefix to add to the function names.

    """
    root = Path(root)

    lib_src_dir = root / library_name
    lib_cmake_dir = lib_src_dir / "cmake"
    if lib_cmake_dir.exists():
        return
    lib_cmake_dir.mkdir(parents=True)

    generate_from_template(
        lib_src_dir / "CMakeLists.txt",
        "cpp_CMakeLists.txt",
        {
            "library_name": library_name,
            "prefix": prefix,
        },
    )
    generate_from_template(
        lib_src_dir / f"{prefix}example.h",
        "example.h",
        {
            "prefix": prefix,
        },
    )
    generate_from_template(
        lib_src_dir / "example.c",
        "example.c",
        {"prefix": prefix, "square_as_cube": square_as_cube},
    )
    generate_from_template(
        lib_cmake_dir / "config.cmake.in",
        "cpp_config.cmake.in",
        {"library_name": library_name},
    )


def make_cpp_pkg(
    root: PathLike | str,
    package_name: str,
    library_names: str | list[str],
    load_mode: str,
    *,
    square_as_cube: bool = False,
) -> None:
    """Generate a Python package exporting a native library.

    Parameters
    ----------
    root : PathLike or str
        The root directory for the package.
    package_name : str
        The name of the package.
    library_names : str | list[str]
        The name of the library or libraries to build.
    load_mode : str
        The load mode used by the native_lib_loader.
    square_as_cube : bool, optional
        Whether to implement the square function as a cube function.

    """
    root = Path(root)

    lib_pkg_dir = root / package_name
    lib_dir = lib_pkg_dir / package_name
    if lib_dir.exists():
        return
    lib_dir.mkdir(parents=True)

    if isinstance(library_names, str):
        library_names = [library_names]

    generate_from_template(
        lib_pkg_dir / "CMakeLists.txt",
        "cpp_py_CMakeLists.txt",
        {
            "package_name": package_name,
            "library_names": library_names,
        },
    )
    generate_from_template(
        lib_pkg_dir / "pyproject.toml",
        "cpp_pyproject.toml",
        {"package_name": package_name},
    )
    generate_from_template(lib_dir / "__init__.py", "cpp___init__.py")

    if load_mode not in ("LOCAL", "GLOBAL", "ENV"):
        msg = f"Invalid load mode: {load_mode}"
        raise ValueError(msg)
    generate_from_template(
        lib_dir / "load.py",
        "load.py",
        {"library_names": library_names, "load_mode": load_mode},
    )

    use_prefix = len(library_names) > 1
    prefix = ""
    for library_name in library_names:
        if use_prefix:
            prefix = f"{library_name}_"
        make_cpp_lib(
            lib_dir,
            library_name,
            square_as_cube=square_as_cube,
            prefix=prefix,
        )


def make_python_pkg(  # noqa: PLR0913
    root: PathLike | str,
    package_name: str,
    library_names: str | list[str],
    cpp_package_name: str,
    *,
    dependencies: list | None = None,
    build_dependencies: list | None = None,
    load_dynamic_lib: bool = True,
    set_rpath: bool = False,
    windows_unresolved_symbols: bool = False,
) -> None:
    """Generate a Python package with a native library dependency.

    Parameters
    ----------
    root : PathLike or str
        The root directory for the package.
    package_name : str
        The name of the package.
    library_names : str | list[str]
        The name of the library or libraries.
    cpp_package_name : str
        The name of the C++ package.
    dependencies : list, optional
        The runtime dependencies for the package.
    build_dependencies : list, optional
        The build dependencies for the package.
    load_dynamic_lib : bool, optional
        Whether to load the dynamic library.
    set_rpath : bool, optional
        Whether to set the rpath for the Python extension module.
    windows_unresolved_symbols: bool, optional
        Whether to avoid linking to the C++ library on the link line to test
        unresolved symbol resolution on Windows.

    """
    root = Path(root)

    pylib_pkg_dir = root / package_name
    pylib_dir = pylib_pkg_dir / package_name
    if pylib_dir.exists():
        return
    pylib_dir.mkdir(parents=True)

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
    if isinstance(library_names, str):
        library_names = [library_names]
    generate_from_template(
        pylib_pkg_dir / "CMakeLists.txt",
        "py_CMakeLists.txt",
        {
            "library_names": library_names,
            "package_name": package_name,
            "dependencies": dependencies,
            "build_dependencies": build_dependencies,
            # cpp_package_name is only used if setting rpath
            "set_rpath": set_rpath,
            "cpp_package_name": cpp_package_name,
            "windows_unresolved_symbols": windows_unresolved_symbols,
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
            "load_dynamic_lib": load_dynamic_lib,
        },
    )
    prefixes = (
        [""]
        if len(library_names) == 1
        else [f"{library_name}_" for library_name in library_names]
    )
    generate_from_template(
        pylib_dir / "pylibexample.c",
        "pylibexample.c",
        {
            "prefixes": prefixes,
            "package_name": package_name,
            "dependencies": dependencies,
            "build_dependencies": build_dependencies,
        },
    )


def build_cmake_project(root: PathLike | str, *, install: bool = False) -> None:
    """Build a CMake project.

    Parameters
    ----------
    root : PathLike or str
        The root directory for the project.
    install: bool
        Whether or not to install the project.

    """
    root = Path(root)

    subprocess.run(
        [
            "cmake",
            "-S",
            root,
            "-B",
            root / "build",
            "--install-prefix",
            root / "install",
        ],
        check=True,
    )
    build_args = ["cmake", "--build", str(root / "build")]

    # Handle multi-config generator on Windows (assuming we aren't using
    # multi-config Ninja on Linux).
    if platform.system() == "Windows":
        # TODO: Specifying Debug instead of Release causes this to break. Not
        # sure if that is a CMake bug or what, but can be investigated later.
        build_args += ["--config", "Release"]

    subprocess.run(
        build_args,
        check=True,
    )

    if install:
        subprocess.run(
            ["cmake", "--install", root / "build"],
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


#############################################
# Test cases
#############################################
def basic_test(
    native_lib_loader_wheelhouse: Path,
    *,
    load_mode: str = "GLOBAL",
    load_dynamic_lib: bool = True,
    set_rpath: bool = False,
    python_editable: bool = False,
    windows_unresolved_symbols: bool = False,
) -> None:
    """Test the generation of a basic library with a C++ and Python package.

    In this case everything is largely expected to work. It's a single library with a
    single function that is single-sourced.

    Parameters
    ----------
    native_lib_loader_wheelhouse : Path
        The path to where the native_lib_loader wheel is.
    load_mode : str
        The load mode used by the native_lib_loader.
    load_dynamic_lib : bool
        Whether the Python package should dynamically load the native library.
    set_rpath : bool
        Whether the Python extension module should set the rpath.
    python_editable : bool
        Whether to install the Python package in editable mode.
    windows_unresolved_symbols: bool, optional
        Whether to avoid linking to the C++ library on the link line to test
        unresolved symbol resolution on Windows.

    """
    root = dir_test(
        "basic_lib",
        load_mode=load_mode,
        load_dynamic_lib=str(load_dynamic_lib),
        set_rpath=str(set_rpath),
        python_editable=str(python_editable),
        windows_unresolved_symbols=str(windows_unresolved_symbols),
    )
    library_name, cpp_package_name, python_package_name = names("example")
    make_cpp_pkg(root, cpp_package_name, library_name, load_mode, square_as_cube=False)
    make_python_pkg(
        root,
        python_package_name,
        library_name,
        cpp_package_name,
        dependencies=["native_lib_loader", "libexample"],
        build_dependencies=["scikit-build-core", "libexample"],
        load_dynamic_lib=load_dynamic_lib,
        set_rpath=set_rpath,
        windows_unresolved_symbols=windows_unresolved_symbols,
    )

    env = VEnv(root, native_lib_loader_wheelhouse)
    env.wheel(root / cpp_package_name)
    if python_editable:
        env.install(root / python_package_name, editable=python_editable)
    else:
        env.wheel(root / python_package_name)
        env.install(python_package_name, "--no-index", editable=python_editable)
    env.run(
        """
        import pylibexample
        print(f"The square of 4 is {pylibexample.pylibexample.square(4)}")
        assert pylibexample.pylibexample.square(4) == 16
        """,
    )


def two_libraries_in_package_test(
    native_lib_loader_wheelhouse: Path,
    *,
    load_mode: str = "GLOBAL",
    load_dynamic_lib: bool = True,
    set_rpath: bool = False,
    python_editable: bool = False,
    windows_unresolved_symbols: bool = False,
) -> None:
    """Test where the C++ package contains two libraries.

    Parameters
    ----------
    native_lib_loader_wheelhouse : Path
        The path to where the native_lib_loader wheel is.
    load_mode : str
        The load mode used by the native_lib_loader.
    load_dynamic_lib : bool
        Whether the Python package should dynamically load the native library.
    set_rpath : bool
        Whether the Python extension module should set the rpath.
    python_editable : bool
        Whether to install the Python package in editable mode.
    windows_unresolved_symbols: bool, optional
        Whether to avoid linking to the C++ library on the link line to test
        unresolved symbol resolution on Windows.

    """
    root = dir_test(
        "two_libraries_in_package",
        load_mode=load_mode,
        load_dynamic_lib=str(load_dynamic_lib),
        set_rpath=str(set_rpath),
        python_editable=str(python_editable),
        windows_unresolved_symbols=str(windows_unresolved_symbols),
    )
    library_name, cpp_package_name, python_package_name = names("example")
    library_names = [f"{library_name}_1", f"{library_name}_2"]
    make_cpp_pkg(root, cpp_package_name, library_names, load_mode, square_as_cube=False)
    make_python_pkg(
        root,
        python_package_name,
        library_names,
        cpp_package_name,
        dependencies=["native_lib_loader", "libexample"],
        build_dependencies=["scikit-build-core", "libexample"],
        load_dynamic_lib=load_dynamic_lib,
        set_rpath=set_rpath,
        windows_unresolved_symbols=windows_unresolved_symbols,
    )

    env = VEnv(root, native_lib_loader_wheelhouse)
    env.wheel(root / cpp_package_name)
    if python_editable:
        env.install(root / python_package_name, editable=python_editable)
    else:
        env.wheel(root / python_package_name)
        env.install(python_package_name, "--no-index", editable=python_editable)
    env.run(
        """
        import pylibexample
        print(f"The square of 4 is {pylibexample.pylibexample.example_1_square(4)}")
        assert pylibexample.pylibexample.example_1_square(4) == 16
        print(f"The square of 4 is {pylibexample.pylibexample.example_2_square(4)}")
        assert pylibexample.pylibexample.example_2_square(4) == 16
        """,
    )


def two_colliding_packages_test(
    native_lib_loader_wheelhouse: Path,
    *,
    load_mode: str = "GLOBAL",
    load_dynamic_lib: bool = True,
    set_rpath: bool = False,
) -> None:
    """Test using two libraries with symbol collisions.

    This test should work when loading locally, but global loads should collide.

    Parameters
    ----------
    native_lib_loader_wheelhouse : Path
        The path to where the native_lib_loader wheel is.
    load_mode : str
        The load mode used by the native_lib_loader.
    load_dynamic_lib : bool
        Whether the Python package should dynamically load the native library.
    set_rpath : bool
        Whether the Python extension module should set the rpath.

    """
    root = dir_test(
        "two_colliding_packages",
        load_mode=load_mode,
        load_dynamic_lib=str(load_dynamic_lib),
        set_rpath=str(set_rpath),
    )
    foo_library_name, foo_cpp_package_name, foo_python_package_name = names("foo")
    make_cpp_pkg(
        root, foo_cpp_package_name, foo_library_name, load_mode, square_as_cube=False
    )
    make_python_pkg(
        root,
        foo_python_package_name,
        foo_library_name,
        foo_cpp_package_name,
        dependencies=["native_lib_loader", "libfoo"],
        build_dependencies=["scikit-build-core", "libfoo"],
        load_dynamic_lib=load_dynamic_lib,
        set_rpath=set_rpath,
    )

    bar_library_name, bar_cpp_package_name, bar_python_package_name = names("bar")
    make_cpp_pkg(
        root, bar_cpp_package_name, bar_library_name, load_mode, square_as_cube=True
    )
    make_python_pkg(
        root,
        bar_python_package_name,
        bar_library_name,
        bar_cpp_package_name,
        dependencies=["native_lib_loader", "libbar"],
        build_dependencies=["scikit-build-core", "libbar"],
        load_dynamic_lib=load_dynamic_lib,
        set_rpath=set_rpath,
    )

    env = VEnv(root, native_lib_loader_wheelhouse)
    env.wheel(root / foo_cpp_package_name)
    env.wheel(root / foo_python_package_name)
    env.install(foo_python_package_name, "--no-index")

    env.wheel(root / bar_cpp_package_name)
    env.wheel(root / bar_python_package_name)
    env.install(bar_python_package_name, "--no-index")

    env.run(
        """
        import pylibfoo
        print(f"The square of 4 is {pylibfoo.pylibfoo.square(4)}")
        assert pylibfoo.pylibfoo.square(4) == 16
        import pylibbar
        print(f"The 'square' (actually cube) of 4 is {pylibbar.pylibbar.square(4)}")
        assert pylibbar.pylibbar.square(4) == 64
        """,
    )


def test_basic(load_mode: str, native_lib_loader_wheelhouse: Path) -> None:
    """Test a single Python extension loading an associated library."""
    basic_test(native_lib_loader_wheelhouse, load_mode=load_mode)


def test_two_libraries_in_package(
    load_mode: str, native_lib_loader_wheelhouse: Path
) -> None:
    """Test a single Python extension loading an associated library."""
    two_libraries_in_package_test(native_lib_loader_wheelhouse, load_mode=load_mode)


def test_lib_only_available_at_build_test(native_lib_loader_wheelhouse: Path) -> None:
    """Test the behavior when a library is only available at build time.

    In this case we expect to see runtime failures in the form of loader errors (which
    should be caught by the native_lib_loader).
    """
    root = dir_test("lib_only_available_at_build")
    library_name, cpp_package_name, python_package_name = names("example")
    make_cpp_lib(root, library_name)
    make_python_pkg(
        root,
        python_package_name,
        library_name,
        cpp_package_name,
        dependencies=["native_lib_loader"],
        build_dependencies=["scikit-build-core"],
        load_dynamic_lib=True,
    )

    # This is for testing behavior on Windows where the build directory does
    # not seem to be working as expected when found.
    use_cpp_from_build = False

    build_cmake_project(root / library_name, install=not use_cpp_from_build)

    env = VEnv(root, native_lib_loader_wheelhouse)
    env.wheel(
        root / python_package_name,
        "--config-settings=cmake.args=-DCMAKE_PREFIX_PATH="
        + str(root / library_name / ("build" if use_cpp_from_build else "install")),
    )
    env.install(python_package_name, "--no-index")

    # TODO: Change to pytest once we're using that
    try:
        env.run(f"import {python_package_name}")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode()
        err_msg = (
            f"ImportError: lib{library_name}.so"
            if platform.system() == "Linux"
            else "DLL load failed"
            if platform.system() == "Windows"
            else "ImportError: "  # Mac
        )

        assert err_msg in stderr, f"Did not get expected message, instead got {stderr}"


def test_two_colliding_packages(
    load_mode: str, native_lib_loader_wheelhouse: Path
) -> None:
    """Test using two libraries with symbol collisions.

    This test should work when loading locally, but global loads should collide.
    """
    # Note that the load mode does not affect Windows
    try:
        # Global loads should fail due to symbol conflicts
        two_colliding_packages_test(native_lib_loader_wheelhouse, load_mode=load_mode)
    except subprocess.CalledProcessError as e:
        # Failures are expected due to symbol collisions when loading globally.
        if load_mode == "GLOBAL":
            stderr = e.stderr.decode()
            assert "AssertionError" in stderr
        else:
            raise


# TODO: Make this test work on Mac too
@pytest.mark.skipif(
    platform.system() != "Linux", reason="RPATH only supported on Linux"
)
def test_rpath(load_mode: str, native_lib_loader_wheelhouse: Path) -> None:
    """Verify that RPATH works under normal circumstances."""
    basic_test(
        native_lib_loader_wheelhouse,
        load_mode=load_mode,
        load_dynamic_lib=False,
        set_rpath=True,
    )


def test_editable_install(native_lib_loader_wheelhouse: Path) -> None:
    """Show that dynamic loading works for editable installs."""
    basic_test(native_lib_loader_wheelhouse, load_mode="LOCAL", python_editable=True)


@pytest.mark.skipif(
    platform.system() != "Linux", reason="RPATH only supported on Linux"
)
def test_editable_install_with_rpath(native_lib_loader_wheelhouse: Path) -> None:
    """Show that RPATHs do not work for editable installs with incompatible layouts."""
    try:
        basic_test(
            native_lib_loader_wheelhouse,
            load_mode="LOCAL",
            load_dynamic_lib=False,
            set_rpath=True,
            python_editable=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode()
        assert "ImportError: " in stderr


def test_env_vars(native_lib_loader_wheelhouse: Path) -> None:
    """Show that setting LD_LIBRARY_PATH/DYLD_LIBRARY_PATH/PATH doesn't work."""
    try:
        basic_test(native_lib_loader_wheelhouse, load_mode="ENV")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode()
        assert "ImportError: " in stderr


@pytest.mark.skipif(
    platform.system() != "Windows", reason="This test is Windows-specific"
)
def test_windows_unresolved_symbols(native_lib_loader_wheelhouse: Path) -> None:
    """Demonstrate unresolved symbols on Windows."""
    # Failure is expected, but the failure in this case is basically UB
    # so we can't predict what the error code will be. Most likely the
    # code is seg faulting.
    with contextlib.suppress(subprocess.CalledProcessError):
        basic_test(
            native_lib_loader_wheelhouse,
            load_mode="LOCAL",
            windows_unresolved_symbols=True,
        )
    # Load mode should be irrelevant on Windows, but testing to verify.
    with contextlib.suppress(subprocess.CalledProcessError):
        basic_test(
            native_lib_loader_wheelhouse,
            load_mode="GLOBAL",
            windows_unresolved_symbols=True,
        )
