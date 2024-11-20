# About

Shipping native libraries in Python wheels is fraught for a number of reasons.
The way pip installs packages is not generally compatible with system package managers in the sense that neither is aware of what the other has installed and pip does not install packages into directories that the dynamic linker knows how to find.
For the same reason, there is also no standardized way to share libraries between different wheels.
This repository aims to establish such a standardized solution.
It provides a standard approach for exporting a native library from a wheel in such a way as to be usable as a library (ELF/PE/Mach-O, depending on your platform) dependency by other native libraries, including Python extension modules.
It also shows how that library may be consumed safely at runtime by its dependencies in a way that is as agnostic as possible to whether the library was actually installed from a wheel or by some alternative means.

Goals:
- Ensure that native libraries installed via Python wheels (or sdists that produce the libraries) can be used by downstream dependencies (Python extension modules or other native libraries) regardless of file layouts, Python environments, or other considerations.

Non-Goals:
- Establishing any mechanism for safely sharing libraries installed by system package managers. That is the domain of [PEP 725](https://peps.python.org/pep-0725/).
- Guarantee safe coexistence of multiple copies of the same shared library (possibly of different versions). That is in general not possible. To achieve similar goals the standard approach is static linking, or in the case of Python wheels bundling of name-mangled DSOs. This project does not proscribe any mangling behavior, although mangling is still recommended for maximum safety.
- Standardize practices for shipping native libraries in wheels suitable for _building_ against. While that is something that goes hand-in-hand with runtime usage, it is not a strict prerequisite and requires an entirely different class of solutions. That being said, most of the examples in this repository will be of libraries that are suitable for use as either runtime or build-time dependencies.

The code in this repository is extremely minimal and can easily be vendored directly into any codebase.
Most of the complexity is in understanding the various edge cases and how this tool chooses an approach that manages to handle as many of them as possible.

## High-Level Description

In a nutshell, the premise of the tooling here is to use ctypes to load the library before anything needs to use it.
This approach is predicated on the fact that once the library is loaded, any future reference to it as a dependency will resolve to the first loaded location of that library.
There are a few important caveats to this approach.
First, we must consider platform-specific behavior:
- Windows: This solution simply works out of the box. No additional considerations are required.
- Linux: The library must have an SONAME set. This may be checked using a command like `readelf` (e.g. `readelf -d <package-name> | grep SONAME`). The SONAME is set using the `-soname` flag for the linker `ld`. Libraries without a SONAME set will not be cached for subsequent searches, and as a result pre-loading with ctypes will not work as expected.
- OS X: The library's install name must match exactly the name of the library encoded in its dependent's `LC_LOAD_DYLIB` entry (as shown in `otool` output). Note that unlike the other two platforms this means that some responsibility for correct usage falls to the consumer of the library (hence increasing the value of making the library easy to use at build-time as well so that setting the correct install name can be handled by simply compiling against the library with the set install name instead of having to rename after the fact).

Second, we must ensure that we do not load the library in an unsafe way that pollutes the global symbol table.
For this, we must use the `RTLD_LOCAL` flag when loading (this has no effect on Windows, but is relevant for Linux and OS X).

An extended discussion on the technical details is [here](doc/main.md).
