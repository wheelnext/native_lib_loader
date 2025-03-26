# About

This package centralizes best practices for shipping shared libraries in Python wheels.
The goal is to ensure that native libraries installed via Python wheels can be used by downstream dependencies regardless of file layouts, Python environments, or other considerations.
This package eschews implicit behavior, preferring instead to expose clear entry points for packages to declare that they expose certain shared libraries for other packages to access.
The code in this repository is extremely minimal and can easily be vendored directly into any codebase.
Most of the complexity is in understanding the various edge cases and how this tool chooses an approach that manages to handle as many of them as possible.
The package supports consumers specifying whether they wish to allow libraries to be loaded from the system or only from the wheel, but there are limitations to this approach, namely that if some other package loads the library before a package using the `native_lib_manager`, the library loaded first will always take precedence due to system loader rules beyond what the `native_lib_manager` can control.
This package does not attempt to address the use of libraries at build time.

## Usage

A package shipping a native library should place the following snippet in their `__init__.py` (or make the loader module visible at some other well-defined location).

```python
# __init__.py
import shared_lib_manager
import os

root = os.path.dirname(os.path.abspath(__file__))
loader = shared_lib_manager.LibraryLoader(
    {
        "foo": shared_lib_manager.PlatformLibrary(
            Darwin=os.path.join(root, "lib", "libfoo.dylib"),
            Windows=os.path.join(root, "lib", "foo.dll"),
        ),
    },
    mode=shared_lib_manager.LoadMode.{{ load_mode }},
)
```

The `loader` object is now available to any other package that ships binaries that link to the shared libraries that the `loader` exposes.
To add those libraries to the search path, they invoke the `loader.load` method like so:
```python
import pkg
pkg.loader.load()
```
