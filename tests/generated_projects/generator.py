# Copyright (c) 2024, NVIDIA CORPORATION.

import os
import subprocess
import venv
from functools import lru_cache
from pathlib import Path
import tempfile
import shutil
import tomlkit
import textwrap

from jinja2 import Environment, FileSystemLoader
from packaging.version import parse as parse_version

DIR = Path(__file__).parent
NATIVE_LIB_DIR = DIR.parent.parent


class VEnv:
    def __init__(self, root):
        self.env_dir = root / "env"
        os.makedirs(self.env_dir, exist_ok=True)

        self.wheelhouse = root / "wheelhouse"
        self.cache_dir = root / "cache"

        self.executable = Path(self.env_dir) / "bin" / "python"
        # Allow for rerunning the script on preexisting test directories for local
        # debugging and interactive exploration.
        if not os.path.exists(self.executable):
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

    def _install_native_lib_loader(self):
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
        with open(pyproject_file) as f:
            pyproject = tomlkit.load(f)
        project_data = pyproject["project"]

        version = parse_version(project_data["version"])
        project_data["version"] = f"{version.major + 1}.{version.minor}.{version.micro}"
        with open(pyproject_file, "w") as f:
            tomlkit.dump(pyproject, f)

        self.wheel(native_lib_loader_dir.name)

    def install(self, *args):
        return subprocess.run(
            self._pip_cmd_base + [
                "install",
                "--find-links",
                self.wheelhouse,
                *args,
            ],
            check=True,
        )

    def wheel(self, package_dir, *args):
        return subprocess.run(
            self._pip_cmd_base + [
                "wheel",
                "-v",
                "--no-deps",
                "--wheel-dir",
                self.wheelhouse,
                "--find-links",
                self.wheelhouse,
                package_dir,
                *args,
            ],
            check=True,
        )

    def run(self, code):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py") as f:
            f.write(textwrap.dedent(code))
            f.flush()
            script = f.name
            return subprocess.run([self.executable, script], check=True)


@lru_cache
def jinja_environment():
    template_dir = DIR / "templates",
    return Environment(
        loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
    )


def generate_from_template(output_path, template_name, template_args=None):
    template = jinja_environment().get_template(template_name)

    template_args = template_args or {}
    content = template.render(**template_args)
    with open(output_path, mode="w", encoding="utf-8") as f:
        f.write(content)


def make_cpp_lib(root, pkg_name):
    root = Path(root)

    lib_src_dir = root / "cpp"
    if os.path.exists(lib_src_dir):
        return
    lib_cmake_dir = lib_src_dir / "cmake"
    os.makedirs(lib_cmake_dir)

    generate_from_template(lib_src_dir / "CMakeLists.txt", "cpp_CMakeLists.txt", {"project_name": pkg_name})
    generate_from_template(lib_src_dir / "example.h", "example.h", {"project_name": pkg_name})
    generate_from_template(lib_src_dir / "example.c", "example.c", {"project_name": pkg_name})
    generate_from_template(lib_cmake_dir / "config.cmake.in", "cpp_config.cmake.in", {"project_name": pkg_name})


def make_cpp_pkg(root, pkg_name):
    root = Path(root)

    lib_pkg_dir = root / f"lib{pkg_name}"
    if os.path.exists(lib_pkg_dir):
        return
    lib_dir = lib_pkg_dir / f"lib{pkg_name}"
    os.makedirs(lib_dir)

    generate_from_template(lib_pkg_dir / "CMakeLists.txt", "cpp_py_CMakeLists.txt", {"project_name": pkg_name})
    generate_from_template(lib_pkg_dir / "pyproject.toml", "cpp_pyproject.toml", {"project_name": pkg_name})
    generate_from_template(lib_dir / "__init__.py", "cpp___init__.py", {"project_name": pkg_name})
    generate_from_template(lib_dir / "load.py", "load.py", {"project_name": pkg_name})

    make_cpp_lib(lib_dir, pkg_name)


def make_python_pkg(root, pkg_name, dependencies=None, build_dependencies=None):
    root = Path(root)

    pylib_pkg_dir = root / f"pylib{pkg_name}"
    if os.path.exists(pylib_pkg_dir):
        return
    pylib_dir = pylib_pkg_dir / f"pylib{pkg_name}"
    os.makedirs(pylib_dir)

    dependencies = dependencies or []
    build_dependencies = build_dependencies or []

    generate_from_template(pylib_pkg_dir / "pyproject.toml", "py_pyproject.toml", {"project_name": pkg_name, "dependencies": dependencies, "build_dependencies": build_dependencies})
    generate_from_template(pylib_pkg_dir / "CMakeLists.txt", "py_CMakeLists.txt", {"project_name": pkg_name, "dependencies": dependencies, "build_dependencies": build_dependencies})
    generate_from_template(pylib_dir / "__init__.py", "py___init__.py", {"project_name": pkg_name, "dependencies": dependencies, "build_dependencies": build_dependencies})
    generate_from_template(pylib_dir / "pylibexample.c", "pylibexample.c", {"project_name": pkg_name, "dependencies": dependencies, "build_dependencies": build_dependencies})


def build_cmake_project(root):
    subprocess.run(
        ["cmake", "-S", root, "-B", root / "build"],
        check=True,
    )
    subprocess.run(
        ["cmake", "--build", root / "build"],
        check=True,
    )

def test_basic():
    """Test the generation of a basic library with a C++ and Python package.

    In this case everything is largely expected to work. It's a single library with a
    single function that is single-sourced.
    """
    root = DIR / "basic_lib"
    make_cpp_pkg(root, "example")
    make_python_pkg(root, "example", ["native_lib_loader", "libexample"], ["scikit-build-core", "libexample"])

    env = VEnv(root)
    env.wheel(root / "libexample")
    env.wheel(root / "pylibexample")
    env.install("pylibexample", "--no-index")
    env.run(
        """
        import pylibexample
        print(f"The square of 4 is {pylibexample.pylibexample.square(4)}")
        """
    )


def test_lib_only_available_at_build():
    """Test the behavior when a library is only available at build time.

    In this case we expect to see runtime failures in the form of loader errors.
    """
    root = DIR / "lib_only_available_at_build"
    make_cpp_lib(root, "example")
    make_python_pkg(root, "example", ["native_lib_loader"], ["scikit-build-core"])

    # TODO: I don't like that I'm hardcoding knowledge of the name prefix (lib) here. I
    # should just change all the templates to use the name as-is, and the prefix should
    # be added in the generator.
    build_cmake_project(root / "cpp")

    env = VEnv(root)
    env.wheel(root / "pylibexample", "--config-settings=cmake.args=-DCMAKE_PREFIX_PATH=" + str(root / "cpp" / "build"))
    env.install("pylibexample", "--no-index")
    env.run("import pylibexample")


if __name__ == "__main__":
    test_basic()
    test_lib_only_available_at_build()
