# Background

## Motivation

For the purpose of this document, we will distinguish between two types of languages: **[compiled languages](https://en.wikipedia.org/wiki/Compiled_language)** and **[interpreted languages](https://en.wikipedia.org/wiki/Interpreted_language)**.
Code written in compiled languages must be translated into machine code before it can run, whereas interpreted code is run directly by an **interpreter** (usually itself a compiled program) at runtime.
Python is an example of an interpreted language, while C++ is an example of a compiled language.
For the rest of this document, we will use these two as representative examples of interpreted and compiled languages.

Since Python is an interpreted language, why do we care about how compiled languages work?
While there are multiple implementations of the Python interpreter, the most popular by far is [CPython](https://en.wikipedia.org/wiki/CPython), the _de facto_ reference implementation of Python written in C.
A huge part of Python's success is due to its ability to leverage existing C libraries by writing [Python extension modules](https://docs.python.org/3/extending/extending.html) that leverage CPython's [C API](https://docs.python.org/3/c-api/index.html).
This functionality is critical to Python's success, but it also in practice means that as a near-universal "glue language" Python libraries are effectively exposed to the set of library and packaging problems from every language that Python extension modules interact with.
As such, the distribution of many of the most popular Python packages requires a deep knowledge of these pieces.

## Libraries and Interfaces

Ideally, code to achieve a particular task should be written once and reused.
The typical unit of code sharing is a **[library](https://en.wikipedia.org/wiki/Library_(computing))**, which is a collection of useful bits of code (functions, classes, etc) that can be reused by other code.
To be shareable, libraries must establish a contract, the [interface](https://en.wikipedia.org/wiki/Interface_(computing)), for how other code can interact with them.
When a developer manages all the code in a project, the stability of the interface is not a major concern since all code can be updated together.
When code is shared between different projects, however, the interface becomes a contract that must remain stable or risk breaking other code.

### Programming and Binary Interfaces

There are two primary types of interfaces relevant in to this discussion: the **[application programming interface (API)](https://en.wikipedia.org/wiki/Application_programming_interface)** and the **[application binary interface (ABI)](https://en.wikipedia.org/wiki/Application_binary_interface)**.
The API is the set of objects (functions, classes, etc) that a library exposes publicly.
For code written in interpreted languages, the API is the only relevant interface.
For compiled code, the ABI is a second, lower-level interface that describes how code interacts with other code after it is compiled to machine instructions.
The ABI is typically a stricter contract than the API because it includes rules about how data is passed between functions, how memory is managed, and other low-level details.
While the API is entirely governed by source code, the ABI is additionally influenced by many other factors such as the compiler used or the operating system on which the code is run.

## Linking and Loading

For interpreted languages, libraries are nothing more than source code.
For compiled languages, however, libraries are typically distributed in compiled form.
To understand how compiled libraries are used, we must understand just a little bit of how [compilers](https://en.wikipedia.org/wiki/Compiler) work.
Very crudely, compilation involves two steps:
1. The translation into machine code. This step itself usually has many other sub-steps (preprocessing, translation into IR, assembling, etc) that we will not go into here.
2. **[Linking](https://en.wikipedia.org/wiki/Linker_(computing))**: the machine code is combined with other machine code to form a single binary.

Compiled libraries are distributed in one of two forms:
1. [Static libraries](https://en.wikipedia.org/wiki/Static_library) are essentially archives of compiled code. When a project depending on a static library is compiled, the linking step essentially copies all relevant components of the static library into the binary. This produces binaries that are inflated in size but are relatively portable due to the lack of external dependencies.
2. [Dynamic (aka shared) libraries](https://en.wikipedia.org/wiki/Dynamic-link_library) are loaded at runtime by the operating system.

There are two ways in which dynamic libraries can be used, and these in turn depend on the [loader](https://en.wikipedia.org/wiki/Loader_(computing)) used by the operating system:
1. Load-time dynamic linking: this is when a project declares a dependency on a dynamic library while being compiled. This is the more common way in which dynamic libraries are used because it allows the functions/classes/etc from the dependency to be used directly in code. For example, if I have a C header `foo.h` declaring a function `f(x)` that is defined in `foo.c`, `bar.c` would contain `#include "foo.h"` and then directly use `f(x)` in its code.
2. Runtime dynamic linking: with this approach, the library is loaded using specific functions for library loading when the program executes (`dlopen` on [Linux](https://www.man7.org/linux/man-pages/man3/dlmopen.3.html) or [Mac](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/dlopen.3.html)  and [LoadLibrary on Windows](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibrarya)). Notably, runtime loading of a library also triggers transitive loading of all of _its_ dependencies. Runtime loading has the advantage that the main compiled program does not express a library dependency in its binary, so it can be loaded on a system where the dependent library does not exist. This approach is necessary when a library is intended to be optional, for instance, and is a standard practice for enabling a plugin architecture. This flexibility comes at a cost, however, because errors are observed at runtime instead of at link-time and can make code harder to debug.

With all the above in mind, we are now prepared to understand how all of this information relates to Python extension modules.
Python's C API can be used to embed calls to functions across various library interfaces using [foreign function interfaces](https://en.wikipedia.org/wiki/Foreign_function_interface) (FFIs).
Python extension modules are nothing more than shared libraries (`.so` files on Linux, `.dylib` on OS X, and [`.pyd` on Windows](https://docs.python.org/3/faq/windows.html#is-a-pyd-file-the-same-as-a-dll)) that the Python interpreter loads as plugins via runtime dynamic linking when code tries to `import` them (for pure Python modules, `import` simply runs the Python source code in the package directly).

## Packages and Package Managers

**Packages** are a distribution mechanism for libraries.
Packages bundle libraries with metadata that can be used to identify the interface of the bundled library.
As libraries evolve, the metadata is updated to reflect the changes to the interface.
**Wheels** are the standard package distribution format for Python packages.

**Package managers** manage installation and removal of packages.
Package managers enable creating consistent, reproducible environments of mutually compatible software.
At a high level, package managers leverage package metadata to ensure that environments are kept in a valid state with compatible software, and they use various mechanisms to ensure that installed packages know how to find one another within an environment.
Concretely, we can break down the purposes of package managers into five main tasks for the purpose of this discussion, namely ensuring that:
1. packages are compatible with low-level system libraries and architecture, kernel drivers, etc.
2. all packages know how to find each other
3. all installed binaries know how to find their dependencies
4. all packages have compatible application programming interfaces (APIs)
5. all installed binaries have compatible application binary interfaces (ABIs)

Some relevant notes on the above:
- To address point 1, package managers must be able to query the system for the properties needed to satisfy the package's requirements.
- To address points 2 and 3, package managers must install packages into predictable locations depending on the type of package. The distinction between these two points is that the loader is responsible for how binaries find their dependencies, while the language interpreters are responsible for ensuring that code written in those languages can find its dependencies, so the package manager must install packages in appropriate locations. Both the [GNU loader](https://man7.org/linux/man-pages/man8/ld.so.8.html) and [Python](https://docs.python.org/3/reference/import.html#searching) have well-documented procedures for finding Python modules.
- To address points 4 and 5, package managers rely on package metadata to provide enough information to determine when two packages are compatible. At minimum, this comes in the form of package versions, but it can also include other information to, for example, identify the package's ABI.

Although a general classification of package managers is challenging due to many of them serving multiple use cases, for this discussion we primarily care about how they solve the above problems.
For this purpose, package managers typically come in two flavors:
1. System package managers (e.g. `apt` or `yum` on Linux) manage a single centralized set of packages that are installed to standard system locations that are visible to all other packages and the loader. Only a single version of a package is typically available, so minimal dependency resolution is required, and the entire set of available packages is built from the ground up to be compatible, thereby satisfying all five criteria above.
2. Third-party managers (Spack, conda, nix) typically have some way to produce isolated environments within which libraries installed by that package manager. These package managers support installing different versions of packages into different environments, so complex dependency resolution is required to resolve a given environment specification. Mechanisms like environment variables (such as `LD_LIBRARY_PATH` on Linux or `PYTHONPATH` in general) are used when environments are active to ensure that packages within the environment take precedence over system packages. Within a given environment, all libraries are handled consistently, satisfying all five criteria above.

## Gaps in pip functionality

With all of the above in mind, we can finally answer our primary question: why is it so difficult to distribute Python extension modules with pip?
The fundamental challenge is that it does not fall into either category of package managers described above.
At present, pip only satisfies criteria 2 and 4 above, and only for Python packages.
It does not have the ability to query the system for the properties needed to satisfy 1 (e.g. it cannot account for C++ ABI, the CUDA version on the system, other drivers, etc), it does not install packages into system locations where the loader could find them to satisfy point 3, and the metadata that pip supports is insufficient to fully describe library ABIs since pip is primarily designed around Python packages where only API matters.
Additionally, pip cannot be guaranteed to be used inside a virtual environment, so mechanisms involving e.g. setting environment variables are not guaranteed to work.
Therefore, we must find ways to patch these gaps as best as we can using other means.
