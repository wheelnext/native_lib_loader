# About

This package is a companion to `shared_lib_manager` and provides a way to load shared libraries exported by that package.
Its implementation is extremely minimal.
The primary benefit of this package is to ensure that loading is safe in as many contexts as possible, including where the corresponding library may not exist.
This is particularly relevant for consumers of a shared library that may sometimes be provided by a wheel using the `shared_lib_manager` and sometimes by other sources (e.g. libraries installed using a different package manager to standard library paths).
It also aims to provide graceful error-handling for cases where the library is not available.

## Usage

This module provides a single function, `load_library_module`, which is used to load a shared library as follows:
```python
import shared_lib_consumer
shared_lib_consumer.load_library_module("foo")
```
