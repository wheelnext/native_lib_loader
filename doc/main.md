# Sharing Dynamic Libraries Between Wheels

## Challenges With Distributing Portable Binaries

There are numerous challenges associated with distributing portable binaries.
For the purpose of this discussion, these challenges fall into two primary classes: 1) ensuring that binaries are compatible with the low-level details of any possible target system; and 2) enabling compatibility between various higher-level libraries installed on the system.
The first set of problems is typically solved by ensuring that binaries are compiled for a specific architecture and against suitably old versions of system libraries that avoid newer symbols.
Such problems are out of scope in this document which is concerned with the second class of problems.

Package managers provide a standard approach to installing mutually compatible binaries.
Package managers typically choose where binaries are installed in one of two ways: 1) system package managers like `apt` or `yum` (and special cases like Homebrew on OS X) install packages in standard system locations that are visible to all binaries; or 2) third-party managers (Spack, conda, nix) have some way to produce isolated environments within which libraries installed by that package manager are (by mechanisms like environment variables) always preferred to system packages.
The sandboxing provided by the second class of managers is critical to their functioning safely because mixing and matching binaries from different package managers that have no way to communicate with each other can easily lead to broken environments containing incompatible objects.
This problem can be ameliorated by introducing some method for package managers to communicate, such as [conda's virtual packages](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/virtual_packages.html), but that introduces an additional complexity as well as another point of failure.

Distributing Python packages with `pip` introduces some unique challenges when it comes to Python's [extension modules](https://docs.python.org/3/extending/extending.html) produced via its C API.
When such extension modules are self-contained, only the first class of portability problems discussed above (low-level architectural/system library details) needs to be addressed.
When extension modules have external library dependencies, however, problems around inter-library compatibility come into play.
To understand why, consider the two different ways in which shared libraries may be used (the terminology varies from platform to platform; I will use one internally consistent set in this document):
- Load-time dynamic linking: this is when, at link-time, one library or executable declares a dependency on another.
During compilation this is expressed by providing the name of (or path to) the dependency.
This is the more common way in which dynamic libraries are used because it allows the functions/classes/etc from the dependency to be used directly in code.
For example, if I have a C header `foo.h` declaring a function `f(x)` that is defined in `foo.c`, `bar.c` would contain `#include "foo.h"` and then directly use `f(x)` in its code.
- Runtime dynamic linking: with this approach, the library is loaded using specific functions for library loading when the program executes (`dlopen` on [Linux](https://www.man7.org/linux/man-pages/man3/dlmopen.3.html) or [Mac](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/dlopen.3.html)  and [LoadLibrary on Windows](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibrarya)).
The main program does not have a direct library dependency, and as a result it can be loaded on a system where the dependent library does not exist.
Notably, if a library has any load-time dependencies, then those dependencies will be loaded whenever the library is loaded at runtime.
To use functions from the library, functions must be found at runtime using APIs that allow querying a library handle for functions by name.
This approach is necessary when a library is intended to be optional, for instance, but is more cumbersome because errors are observed at runtime and instead of at link-time, making code harder to debug.
Runtime loading is a standard approach for a plugin or module architecture.

Python extension modules are simply shared libraries (`.so` files on Linux, `.dylib` on OS X, and [`.pyd` on Windows](https://docs.python.org/3/faq/windows.html#is-a-pyd-file-the-same-as-a-dll) ) that are dynamically linked by Python at runtime.
Python's `import` statement will load pure Python modules directly, but extension modules are loaded by runtime dynamic linking.
If the extension module has external dependencies, though, then those transitive dependencies are loaded as well, typically by following the rules for load-time dynamic linking.
As noted above, the primary differences between runtime and load-time linking are in how the code is structured, but there are also subtle differences between how each finds libraries (as well as between different platforms) that impact what Python extensions can do safely.
With runtime linking the path to the library may be constructed as an absolute path at runtime, but with load-time linking the search paths are defined by specific rules on each platform.
If an extension module depends on other shared libraries, then the search for those transitive dependencies will follow the load-time dependency search rules.

The fundamental challenge for distributing native libraries with `pip` is that it does not fall into either category of package managers described above: it cannot install native libraries into system locations (at least, not without serious hacks that would clobber system packages), nor can it operate in a self-contained environment where all libraries are handled consistently (Python virtual environments cannot really be used for this without bending over backwards, and even if they could we cannot assume that users are always in a virtual environment).
[PEP 725](https://peps.python.org/pep-0725/) offers one possible solution to the problem, allowing Python packages to declare dependencies on system packages in a way that pip or other wheel-building tools can understand.
While something like this is ultimately necessary, a complete solution in this space is likely years away.
We effectively need four things to happen:
1.
Wheels need a way of encoding that they depend on some library that may be found externally.
This is what PEP 725 enables via pyproject.toml metadata.
2.
pip and other build tools needs a way to translate that requirements list into a list of dependencies to find.
This requires implementation on the part of each such tool.
3.
System (or system-like, e.g.
conda) package managers need to be updated to advertise to pip that a dependency installed by that package manager can be found.
One option would be for package managers to expose some new metadata specific to pip, while an alternative would be for pip to leverage tools like CMake/meson/pkgconfig for their underlying finding capabilities.
4.
pip/wheels will need a standard install location for libraries that come bundled with a wheel, as well as handling step 3 (advertising what libraries are installed).
This may never be the focus if using system libraries (3) ends up always being the preferred route.

Moreover, even if all of these occur we cannot assume that users will be in a position to easily install said external dependencies from a non-pip source.
Therefore, even in a PEP 725 world -- and certainly today -- we need to determine what the best way is to distribute native libraries via pip right now.

## Current Approaches for Native Library Dependencies in Wheels

At present, there are generally two ways that Python packages handle native library dependencies.

### Static linking

Static linking is the classic approach used across many languages.
It provides a clean approach to ensuring that a built artifact is isolated from changes to libraries in the environment.
In the context of Python packages, it has two main drawbacks:
- It increases binary size.
If many running binaries all use the same library at runtime and statically link it, they will each contain copies of that library's code instead of reusing it.
- Not all libraries actually support multiple copies of their symbols being loaded at runtime.
Examples of such libraries include those with global state or those with objects like C++ virtual classes that have RTTI (and vtables), neither of which can in the general case be safely used if multiple copies of a library exist at once.

### Bundling of Dynamic Libraries

Empirically Python extension modules leverage dynamic linking far more often than static linking, so to support building portable packages from dynamically linked extension modules the Python community has built tooling to support the alternate solution of bundling all dynamic libraries into a package.
[auditwheel](https://github.com/pypa/auditwheel) for Linux, [delvewheel](https://github.com/adang1345/delvewheel) for Windows, and [delocate](https://github.com/matthew-brett/delocate) for OS X, are tools that will traverse the library dependency chain for all extension modules in a package and copy those dependencies into a suitable place in the package, fixing up the extension modules as needed to find the package's internal copies of those dependencies.
This process brings us back to the question of how load-time dependencies of libraries are normally found.
The exact rules for this process are documented at the following sites:
- [Windows](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order?redirectedfrom=MSDN)
- [OS X](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryUsageGuidelines.html#//apple_ref/doc/uid/TP40001928-SW10) (This is a legacy page, but I have not been able to find equivalent information on the [newer documentation pages](https://developer.apple.com/documentation); empirically the information provided in the legacy pages seems to still be accurate).
- [Linux](https://www.man7.org/linux/man-pages/man8/ld.so.8.html)

In addition to the documented search paths, OS X and Linux also supports what OS X calls [Run-Path Dependent Libraries](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/RunpathDependentLibraries.html).
These libraries effectively declare that some dependencies may be searched for in specific directories encoded within the binary itself (on Mac this is encoded in the names of `LC_LOAD_DYLIB` entries in the Mach-O file that can be seen via [`otool -l`](https://www.unix.com/man-page/osx/1/otool/), whereas for Linux it is the `RPATH` and `RUNPATH` entries in ELF files that may be seen using [`readelf`](https://man7.org/linux/man-pages/man1/readelf.1.html)).
Windows does not support the same functionality, but its search path does include the directory that the library is placed in.

auditwheel and delocate both leverage run paths to specify library internal dependencies, while on Windows delvewheel leverages the loaded-module list, i.e.
the fact that if a library with a name has already been loaded once then subsequent attempts to load a library with that name will simply reuse the original library without attempting a further search.
delvewheel injects library loading code into the package to ensure that dependent libraries are loaded before any extension modules that need them.

This approach exacerbates the binary size drawback of static linking since static linking at least only copies necessary symbols into the final executable, whereas with bundling a shared library the entire contents are included wholesale.
Beyond binary size, bundling dynamic libraries has other implications.
While the loaded-module list is explicitly documented as part of the search on Windows, something similar exists on both OS X and Linux.
This behavior could be problematic if a wheel vendors a library that is identical to a system-installed library, since then any program that attempts to load both will be susceptible to surprising behaviors depending on which library is loaded first (on all platforms, the first loaded library wins).
To resolve this problem, the bundling tools all mangle the names of the bundled shared libraries using something like the hash of the library to make the library names unique.
This approach ensures that the libraries will not conflict with other versions of the library file existing on the system unless these files are binary-identical.
By doing so, however, the libraries do once again open up the possibility for multiple versions of the same library (e.g.
libfoo v1.0 and libfoo v1.1) existing on the same system and having similar issues that may arise with static linking.

## Proposed Approach for Sharing

Based on the above, there are two primary issues that arise from how native libraries are currently handled: binary size, and issues with symbol duplication across multiple copies of the library.
The latter cannot truly be solved without something like PEP 725 because non-Python libraries could always be loaded within some executable that embeds Python, but it could be improved by at least maximizing sharing between all Python extension modules, which would also minimize total binary size.
The easiest way to accomplish this is to ship the native libraries in wheels in such a way as to facilitate other wheels expressing a dependency on them.
Ideally, we want to enable the following:
```
import libfoo  # This loads the C++ library
import pylibfoo  # This loads a Python package containing an extension module that requires libfoo.so
```
For this to work, we need to address how libraries are loaded.

### Library Loading

The key problem is that libraries installed by `pip` will not be visible to extension modules in other packages by default.
A (roughly) platform-independent solution for making them visible is to leverage the loaded-modules list, which also exists on Mac and Linux although it is not as explicitly documented as it is on Windows.
The concept ensures that load-time dependencies are satisfied in a deterministic fashion (for runtime linking it would be possible to support loading arbitrary numbers of versions of the same library using e.g.
the local scopes used by the Linux loader as described in [section 1.5.4 of Drepper's dsohowto document](https://akkadia.org/drepper/dsohowto.pdf)).
Since on all platforms the first library with a given "name" is automatically reused to satisfy future requests for that library, the crux of the matter is to identify the unique key used to identify libraries.
1.
 Windows
	1.
Runtime linking: If two libraries with the same name but in different directories are loaded by path using `LoadLibrary`, the two handles will be distinct.
If the second call uses the module name without a path, however, the same handle will be returned as the first time.
In other words, the filename (e.g.
`foo.dll`) is the unique key in the loaded library table, and all subsequent loads will use this.
	2.
Load-time linking: The first library loaded with a given name in any directory, either by `LoadLibrary` or via another load-time link, is the first one used.
Therefore, a call to `LoadLibrary` with a given library name will ensure that all subsequent loads via transitive load-time dependencies will use that first library.
2.
OS X
	1.
Runtime linking: If two libraries with the same name but in different directories are loaded by path using `dlopen`, the two handles will be distinct.
If the second call uses the module name without a path, then the loader first checks if a module with that [install name](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/OverviewOfDynamicLibraries.html#//apple_ref/doc/uid/TP40001873-SW1) (for more details on how install names are used by the linker, [see this post](https://forums.developer.apple.com/forums/thread/736719)) has been loaded previously.
The install name of a binary is baked into it when it is built, but may be modified later using [install_name_tool](https://www.unix.com/man-page/osx/1/install_name_tool/).
This means that unlike with Windows, the unique key used to identify a library to the loader for uniqueness is not the filename on disk, but the install name, which may or may not be the same.
	2.
Load-time linking: The exact details around this are somewhat complex.
A binary expresses a load-time dependency on a dynamic library via an `LC_LOAD_DYLIB` load command (which can be seen using [`otool -l`](https://www.unix.com/man-page/osx/1/otool/)), and that dependency has a name encoded.
If that name matches an existing loaded library's install name exactly in its entirety, the previously loaded library (whether loaded via runtime or load-time linking) will be used.
I specify in its entirety because the `LC_LOAD_DYLIB` entry's name may include forward slashes as well as certain special values `@loader_path` and `@rpath`.
For the purpose of checking the list of loaded libraries, neither these fields nor anything to the left of the final forward slash are considered special, i.e.
an install name match requires an exact match of the entire name.
If no previously loaded libraries match the encoded install name, however, then the loader will use the entry's name to search for the library, _after_ stripping out any directory names _except_ if the directory name includes one of the above special keys, in which case those are used as part of the path.
The upshot is that the behavior for searching previously loaded libraries to satisfy load-time dependencies of a library in OS X is the same as Windows except that the unique key used to identify a library is not its filename on disk but rather its install name.
 1.
Linux
	 1.
Runtime linking: The situation on Linux is different than on OS X or Windows w.r.t.
to loading by paths.
If consecutive `dlopen` calls are passed paths to two libraries with the same name but at different paths, the second call may return a handle to the first loaded library even though the path is different.
Even when given paths, `dlopen` on Linux will check the loaded-modules list before attempting to load the second copy.
Note, however, that I said the second call _may_ return the first library.
Whether or not the first library is returned depends on whether the libraries in question have their `DT_SONAME` properties set.
The reason is that if two libraries have the same SONAME, the loader will treat them as the same library even if they were loaded from different paths, [as can be seen in the code to maintain the unique library list in glibc](https://codebrowser.dev/glibc/glibc/elf/dl-load.c.html#1972).
Conversely if two libraries do not have an SONAME set, they may both be runtime loaded by a process even if they have the same name (note: whether intentionally or not, Python makes use of this fact to avoid having two extension modules with the same name conflict each other by not setting the SONAME on extension modules; it appears that [this has bitten at least LLVM once before](https://reviews.llvm.org/D107113?id=362936)).
This behavior affects runtime dynamic loading in a way unique to Linux compared to Windows or OS X where it is always possible to load libraries by absolute path and get exactly what you expected.
	 2.
Load-time linking: With respect to load-time dependencies, the behavior on Linux is essentially the same as OS X except instead of the install name the unique key is the SONAME.
If a library with a given SONAME has already been loaded, then it may be used to satisfy a load-time dependency for a future runtime loaded library.
If not, then libraries are searched according to the rules mentioned above.

Therefore, in order to make a native library available for an extension module, it is sufficient to load it in a way that adds it to the registry of loaded modules.
On Windows, a `LoadLibrary` call is sufficient.
On OS X and Linux, the call is sufficient if and only if the library has the appropriate properties: on Linux the library _must_ have its SONAME set, whereas on OS X it must have its install name set.
On OS X there is an additional requirement imposed on the consuming extension module: the entry in the load commands must have a name that exactly matches the install name of the native library being loaded including the full path (whereas on Linux it simply must match the SONAME).

## Discarded Solutions

### Environment Variables

A common way to make libraries discoverable is to set the appropriate environment variables.
This solution is generally frowned upon in the context of distribution because it is not portable and requires runtime modifications, but it is commonly used by end-users.
The relevant variables are `LD_LIBRARY_PATH` on Linux, `DYLD_LIBRARY_PATH` on Mac, and `PATH` on Windows.
Unfortunately, these variables cannot be used to satisfy the use case described above.
The problem is that on all platforms these variables are read once when the dynamic loader is first loaded into memory rather than being read from each time the loader tries to load a new library.
As a result, by the time `import libfoo` occurs, the search paths used by the loader have already been fixed and cannot be modified using the environment variables.

In principle, one could imagine solving this problem in a limited subset of cases.
For example, when using Python virtual environments there is a consistent activation process that you could hook into.
However, there are no well-defined entry points for doing so, so one would have to resort to manual modification of activation scripts, and the same approach would not be portable across different types of virtual environments.
More importantly, virtual environments are not ubiquitous and we cannot assume that they are always in use.

### Dynamic Loader APIs

Ideally dynamic loaders would expose a programmatic interface to modify search paths.
Windows exposes a function [AddDllDirectory](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-adddlldirectory) that can be accessed from Python's [`os.add_dll_directory`](https://docs.python.org/3/library/os.html#os.add_dll_directory) to specify a new location to search, but unfortunately no equivalent exists on other platforms.
Therefore, this type of modification is not currently a viable solution either.
If OS X and Linux loaders were to expose such a function then this could become possible in the future.

### Setting RPATHs

RPATHs appear to be a viable solution for generating portable binaries, but in the wheel case they assuredly are not.
One obvious issue is platform availability: no analog exists on Windows.
However, the problems are deeper than that.
Since the first loaded module wins on all platforms, an extension module with RPATHs set could still wind up using the wrong version of a library if another extension module was loaded before it that triggered loading of the library from a different location (this problem also exists with the solution proposed in this file, but empirically RPATHs seem to give a much greater false sense of security here).
Another issue is that RPATHs are specific to a particular layout of packages that may not be satisfied.
With the modern Python import system, between meta path hooks, PYTHONPATH, and other similar modifications there is no guarantee that any set of relative paths will be sufficient to cover all cases.
In principle we could simply decide that only a subset of layouts are supported, but it does make for a fairly unpalatable option of having a perpetually growing list of RPATHs.
Moreover, it results in every consumer having to track the layout of the native library wheel rather than having the wheel choose how it exports the library.

### Allowing Undefined Symbols

All of the above discussion presumes that dependencies must be findable for a dependent extension module to work at runtime.
However, this is technically not the case.
Really, all that needs to happen is for all of the symbols (functions, classes, etc) required by a library to be available at runtime.
This suggests an alternative path for making wheels work: simply remove dynamic linkages to external dependencies, but instead make sure the symbols for those libraries are made available in some global sense prior to the extension module being loaded.

In principle, this can be done on some platforms.
When building the library it is possible to specify that symbols may be undefined at link-time.
This can be done in the following ways on each platform:
- Linux: The linker allows undefined references by default, except in certain cases(transitive shared library dependencies of an executable).
See [`the ld docs`](https://linux.die.net/man/1/ld) for details, specifically the `--no-undefined` and `--no-allow-shlib-undefined` flags.
- OS X: The linker accepts the [`-undefined dynamic_lookup`](https://www.unix.com/man-page/OSX/1/ld/) flag.
- Windows: The linker can be instructed to ignore undefined symbols using the [`/FORCE:Unresolved`](https://learn.microsoft.com/en-us/cpp/build/reference/force-force-file-output?view=msvc-170) linker option

The second piece of this is making sure that the library can actually find these undefined symbols at runtime.
This process is once again platform-dependent, and unfortunately does not appear possible on all platforms:

- Linux: Symbols are looked up in a single global namespace, meaning that there is no library name associated with the symbol when it is being looked up, only the symbol name itself.
However, there are caveats.
Libraries loaded via `dlopen` may specify whether the symbols loaded should be added to the global namespace or not via the `RTLD_[GLOBAL|LOCAL]` flags.
The default is `RTLD_LOCAL`, which means that if you `dlopen` one library that defines a function `foo` and a subsequently loaded library was compiled with an undefined symbol `foo` , the second load will fail to resolve correctly unless the first one is loaded with `RTLD_GLOBAL`.
- OS X: Older versions of OSX used a flat namespace like Linux, while newer versions (anything after 10.2) default to a [two-level namespace](https://developer.apple.com/library/archive/documentation/Porting/Conceptual/PortingUnix/compiling/compiling.html#//apple_ref/doc/uid/TP40002850-BCIHJBBF), which means that symbols are associated with a library and are looked up by the pair (library, symbol) rather than just the symbol name.
To allow global lookup to work, the library must be compiled with the legacy flat namespace behavior using the `-flat-namespace` linker flag.
Then, the same logic as Linux applies: `dlopen` must be passed `RTLD_GLOBAL` when loading the library dependencies (note that unlike on Linux, on OS X global is the default for dlopen).
- Windows: Symbols in executables are stored in [the import table](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format#the-idata-section)  as a pair (library, symbol) indicating what library the required symbol comes from, i.e.
the same as the two-level namespace lookup on OS X.
There unfortunately does not seem to be any way to force Windows to allow symbol lookup in all loaded libraries if the default lookup fails.
As discussed in [this thread](https://developercommunity.visualstudio.com/t/Runtime-symbol-resolution-with-FORCE:UNR/10767093#T-N10775302-N10778881) it looks like binaries built with `/FORCE:UNRESOLVED` are not meant to resolve symbols at runtime in this way.

Even if this solution could be made to work on Windows, however, it has some severe drawbacks.
The reason OS X moved from the flat namespace to the two-level namespace is that it dramatically reduces the risks of symbol collisions at runtime.
While libraries in newer languages like C++ are somewhat better equipped for this due to tools like namespaces and name mangling, it is still highly likely that in a complex application multiple libraries will define symbols with the same name.
Linux's rules around local ELF scopes when `dlopen` is used provide some safety guarantees, but they are thrown out the window with global loading and mean that symbol collisions become a regular problem.
Such errors can be extremely challenging to debug and severely degrade the user experience.
As such, this approach is best avoided.

## Safety and Library Name Mangling

With the proposed approach for packaging wheels, the same concerns around multiple different versions of a library existing on the system discussed in [](#Bundling of Dynamic Libraries) still apply.
On OS X and Linux, some level of protection is afforded by the way library versioning is handled (see [the section on Specifying Version Information on OS X](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryDesignGuidelines.html#//apple_ref/doc/uid/TP40002013-SW19), and [SONAME versioning on Linux](https://tldp.org/HOWTO/Program-Library-HOWTO/shared-libraries.html)); if you always dlopen the versioned name of a library rather than the unversioned one you get some degree of protection that is not available on Windows.
However, that is still insufficient since all it guarantees is loading an ABI-compatible version, not necessarily one that contains all the necessary symbols (i.e.
you could get an earlier minor version from the same major family that is missing the newest functions that you need).
The safest choice would be for all native libraries distributed in wheels to have a different name from the same library that would be distributed on the system (see e.g.
the [pynativelib proposal](https://github.com/njsmith/wheel-builders/blob/pynativelib-proposal/pynativelib-proposal.rst) in which all libraries distributed in wheels are prefixed with `pynativelib`, so `libfoo.so` would become `pynativelib_libfoo.so`).
This does mean that we will not be able to use system-installed libraries with the wheel, which may in some cases be desirable.
Unfortunately, due to the first loaded library always winning, there is no safe way to make a runtime decision about which dependency to use since the result is order-dependent.
If that functionality is critical, then the consumer must accept the risk of an unrelated library being loaded.
For some libraries there is either 1) no way to provide an optimal binary for a platform as a wheel, or 2) having multiple versions of a library loaded at the same time is intrinsically unsafe.
An example of case 1 would be something like MPI where knowledge of the fabrics available on the specific installation target is important to have a binary compiled exactly for that.
`pip`'s metadata is not rich enough to capture such information, nor is its installation mechanism smart enough to identify all such properties, and even if neither of these things were true maintaining compiled versions of the library for every possible compile-time flag combination is combinatorially infeasible.
An example of case 2 could be something like OpenMP where having multiple libraries loaded could lead to oversubscription of threads, or any library where objects have RTTI that is not safe to pass from one "version" of the library to another (e.g.
any class with virtual methods; the vtables defined in one copy of the library may be incompatible when passed to the other).
In such cases the tradeoff of not making fully isolated wheels may be worthwhile.

### OS X and Mangling

Note that with the scheme proposed here, the relevant mangling on OS X is of the install name.
Due to the way that the linker places the install name into the `LC_LOAD_DYLIB` entries and the way those are used at runtime to load libraries, we need to ensure that the install name of the loaded library exactly matches the `LC_LOAD_DYLIB` entries in the consuming Mach-O file.
The easiest way those could be made to match is by stripping out all path components from both and simply using the filename (e.g. `libexample.dylib`), but that would lead to potential collisions.
Therefore, what is needed is to ensure that the install name is mangled so that it does not conflict with other installations of the same library.
