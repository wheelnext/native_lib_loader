# About

This repo aims to establish tooling and best practices for packaging native libraries in Python packages.
Given a native library build, it shows how to wrap that library in a Python package that exposes it.
It then shows how other libraries may be built against that library, and how they may be configured to properly load that library at runtime.

Each package that exposes a library must make that library available via CMake.
It must also expose a `load_library` Python function to be called by its dependencies at runtime.


# Notes

The problem we wish to solve is to package a native library into a wheel that can then be made available to other libraries.
For now, this document is divided up by platform since linking/loading behavior is different on each, but may be reorganized as we can find more commonalities.

## High level concepts

At a basic level, the loader maintains two tables of note.
The first is a set of loaded libraries, which is keyed on either the library name (Linux, Windows needs verification but I believe so) or the library's absolute path (OS X) depending on the platform.
The second is the symbol table, which is a list of all symbols that are available to be called by a program.
On some platforms (Unix-like), the symbol table is further subdivided into scopes; symbols in global scope are available for all subsequent symbol resolution when libraries are loaded, while symbols in local scope are only available for resolution within a particular library load chain expressed in terms of link-time dependencies hard coded into a library/executable (verify that no equivalent exists on Windows).
These two tables are both relevant for our purposes because they control how dependent libraries may find their dependencies as well as how the symbols are resolved, including in cases where the library may not be found.

Here is a clarifying example.
Say library A calls a function `foo` defined in a library B.
If library B is loaded and told to place its symbols in local scope and then the library A is loaded, B's symbols will not be available for A.
In order for

# Linux

On Linux, there are multiple ways for shared libraries to work.
