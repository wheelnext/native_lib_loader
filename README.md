# About

This repo aims to establish tooling and best practices for packaging native libraries in Python packages.
Given a native library build, it shows how to wrap that library in a Python package that exposes it.
It then shows how other libraries may be built against that library, and how they may be configured to properly load that library at runtime.

Each package that exposes a library must make that library available via CMake.
It must also expose a `load_library` Python function to be called by its dependencies at runtime.
