# Library Design

Here we discuss the design of the existing tools in this repository.
These tools take the information from the [](#solutions) page but make more opinionated choices about how to leverage them.
This page aims to explain those choices, as well as provide context on how to safely deviate from those choices on a case-by-case basis.
All the discussion here assumes that we are using the library loading approach proposed in [](#solutions).

The current architecture of the tools assumes that the package containing a library will be willing to include Python code to expose that library.
The benefit of this approach is that the package can then provide a uniform interface regardless of how the files in the package are rearranged, and consumers can interact with this solely in Python.
However, it is equally viable for the package to put the onus on consumers to determine how the library should be loaded.
In that case, the library wheel does not have to use the `shared_lib_manager` at all.
Consuming wheels are responsible for performing the `ctypes` calls themselves.
The primary downside of this approach is that the same logic has to be duplicated in many places.
The benefit is that the library wheel can be packaged essentially as-is, particularly if the approach taken is a simple binary repackaging.
