# Overview

This page assumes some understanding of the following concepts:
- API and ABI
- Python extension modules
- Static and dynamic linking
- Load-time/compile-time linkage and runtime linking (dlopen, LoadLibrary, etc)

If you are unfamiliar with these concepts, the [background](background.md) page provides a high-level overview with links to further reading.

## Goals

On [the background page](background.md#packages-and-package-managers), we discussed the five functions of package managers that are relevant to this discussion:
1. Ensuring that packages are compatible with low-level system libraries and architecture, kernel drivers, etc.
2. Ensuring that all packages know how to find each other
3. Ensuring that all installed binaries know how to find their dependencies
4. Ensuring that all packages have compatible application programming interfaces (APIs)
5. Ensuring that all installed binaries have compatible application binary interfaces (ABIs)

Point 1 is out of scope for this project; projects like [manylinux](https://peps.python.org/pep-0513/#the-manylinux1-policy) can help build wheels that are compatible with a wider range of low-level system details, but ultimately pip needs to add support for querying the system for necessary properties to be able to make decisions about compatible libraries at install time.
Since points 2 and 4 are already satisfied by pip, that leaves points 3 and 5 to be addressed in this project.
Our primary focus for now is point 3; we may return to point 5 at a later date.

## Key Technical Background

To address point 3, we must first understand two things:
- How the loader finds libraries
- How symbols are resolved in a binary

These are significantly more involved topics than those discussed in [](background.md), so they are discussed here since it is expected that all readers will need some of these details.

### How the Loader Finds Libraries

The exact rules for the loader's library search are platform-dependent and documented at the following sites:
- [Windows](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order?redirectedfrom=MSDN)
- [OS X](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryUsageGuidelines.html#//apple_ref/doc/uid/TP40001928-SW10) (This is a legacy page, but I have not been able to find equivalent information on the [newer documentation pages](https://developer.apple.com/documentation); empirically the information provided in the legacy pages seems to still be accurate).
- [Linux](https://www.man7.org/linux/man-pages/man8/ld.so.8.html)

Essentially, the loader searches a fixed set of paths that may be configured using a few knobs like environment variables.
In addition to the documented search paths, OS X and Linux also support what OS X calls [Run-Path Dependent Libraries](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/RunpathDependentLibraries.html).
These libraries declare that their dependencies may also be found in specific directories (either relative or absolute) encoded within the binary itself.
On OS X this information is encoded in the names of `LC_LOAD_DYLIB` entries in the Mach-O file that can be seen via [`otool -l`](https://www.unix.com/man-page/osx/1/otool/).
For Linux, the information is in the `RPATH` and `RUNPATH` entries in ELF files that may be seen using [`readelf`](https://man7.org/linux/man-pages/man1/readelf.1.html) or other similar tools.
For the purpose of this document we will call all of these "runpaths" except where distinguishing is critical.
While Windows does not support the same functionality, the Windows loader will automatically search for a binary's dependencies in the same directory as the library itself; on OS X and Linux, that search is also possible but must be specified using certain special methods for runpath-dependent libraries (see the note below the table below).
Windows also exposes a programmatic interface to modify loader search paths, the [AddDllDirectory](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-adddlldirectory) function to specify a new location to search.
This function can be accessed from Python's [`os.add_dll_directory`](https://docs.python.org/3/library/os.html#os.add_dll_directory).

Once a library has been loaded, it is added to the ["loaded-module list"](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order?redirectedfrom=MSDN), which contains a list of all libraries that have been loaded into the current process space.
This list is only explicitly documented on Windows (at the above link), but it also exists on OS X and Linux.
This behavior is a fundamental property of all loaders to ensure that duplicate libraries are not loaded into the same process space and that symbols are not clobbered by different versions.
The list also ensures that load-time dependencies are satisfied in a deterministic fashion (for runtime linking it would be possible to support loading arbitrary numbers of versions of the same library using e.g. the local scopes used by the Linux loader as described in [section 1.5.4 of Drepper's dsohowto document](https://akkadia.org/drepper/dsohowto.pdf)).
Once a library has been found once, all subsequent loads of that library will use it and preempt any search for the library on the filesystem.
The exact details of this behavior are similar across platforms, but there are a number of notable differences such as the key used to identify a library in the loaded-module list and the impacts on runtime and load-time linking.

|         | Windows | OS X | Linux |
|---------|---------|------|-------|
| Loaded-module list key     | Base filename (i.e. without the full path) | Install name (seen with `otool -D $lib`)| DT_SONAME (the actual value in the binary, not the filename; you can see this with `readelf -d $lib | grep SONAME`, for example) |
| First runtime load (`dlopen`/`LoadLibrary`) by filepath | Loads exactly specified library | Same as Windows | Same as Windows |
| Second runtime load by different filepath from first load | Loads exactly specified library | Same as Windows | Searches the loaded-modules list for a library whose key (the `SONAME` of that library) matches the filename of the library being searched for and returns it if it exists; otherwise, loads the library from the specified filepath |
| Runtime load by library name | Searches the loaded-modules list for a library whose key (the filename) matches the base name of the library file attempted to load and returns it if one exists; otherwise, follows the platform search path rules | Same as Windows mutatis mutandis the key (the install name) | Same as Windows mutatis mutandis the key (the SONAME) |
| Load-time load (binary expresses a dependency e.g. `DT_NEEDED` on Linux) | Same as the above row (runtime load by library name) | Similar to Windows, but with many caveats (see below) | Similar to OS X (see below) |

Some notes:
- Regarding the key in the loaded-modules list, it should be noted that in most typical cases on OS X and Linux you do want these keys to match the filename even though they do not have to. Having a library's install name or SONAME not match the filename will cause problems in most cases since unless dependent libraries have their dependency entries suitably set _and_ the dependency is already loaded in the process space, the loader will have to go find the library and it will not be able since the search is by filename but the filename will be inferred from the dependency entry in the dependent library, which will be using the loaded-modules list key.
- The behavior of load-time loading on OS X and Linux is complicated by their support for special keys in specifying runpaths. Runpath-dependent libraries can specify relative paths at which to search for dependencies, and these paths may include special keys like `@rpath`, `@executable_path`, and `@loader_path` on OS X or `$ORIGIN` on Linux. Meanwhile, the keys that are placed in the loaded-modules list are based on the install name or SONAME of the library. The runpath lookups only apply if a library dependency cannot be found in the loaded-modules list since if the loaded-modules list contains a library whose key matches the searched library, that

:::{note}
I suspect that in the same way that on OS X the special keys used to specify the path to a dependency in the LC_LOAD_DYLIB entries are not used to determine the key in the loaded-modules list, on Linux the `$ORIGIN` key is not used when looking up a library by SONAME, i.e. it may be possible to modify the DT_NEEDED entries to include $ORIGIN and have that be removed, but I have not tested this.
:::

One important consideration is what happens if multiple libraries with the same name exist on the same machine.
While one way this could happen is that multiple different libraries happen to have the same name, a much more likely occurrence is that multiple distribution mechanisms have installed different versions of the same library onto the system.
This can be deeply problematic if two different libraries both depend on a third library, but each requires a different version of it.
In more typical situations, a package manager would solve this problem by ensuring that the dependency is always satisfied by a version of the library that is compatible with all libraries that require it, but less typical situations where this is not the case can occur, as we will see below.

### How Symbols are Resolved

Once all of the dependencies of a library are loaded, the symbols in the binary must then be resolved.
All libraries contain a [symbol table](https://en.wikipedia.org/wiki/Symbol_table) that contains a list of all identifiers (functions, classes, etc) defined in the library and their addresses.
When there are dependencies, some symbols are left undefined in the library and are filled in at runtime after dependencies are loaded.
There are two main sets of OS-specific differences to be aware of here.

#### Symbol Namespacing

Most critically, different platforms have different rules for whether external symbols are associated with a particular dependency library or not.
For consistency, we will leverage the following terminology established in [the legacy OS X documentation](https://developer.apple.com/library/archive/documentation/Porting/Conceptual/PortingUnix/compiling/compiling.html#//apple_ref/doc/uid/TP40002850-BCIHJBBF):
- A "flat namespace" means that the symbol table is keyed on just the the symbol name
- A "two-level namespace" means that the symbol table is keyed on the pair (library, symbol)

|         | Windows | OS X | Linux |
|---------|---------|------|-------|
| Load-time linking      | [Windows always uses a two-level namespace for external symbols](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format#import-directory-table) | OS X has changed behavior over time. Older versions of OS X used a flat namespace, while newer versions (anything after 10.2) default to a two-level namespace but that can be changed by specifying the [`-flat_namespace` compiler flag](https://www.unix.com/man_page/osx/1/ld/) | Linux always uses a flat namespace |
| Runtime linking      |  Same as for load-time linking, all symbols are namespaced by the library they come from | When libraries are loaded with `dlopen`, the `dlopen` caller may specify whether the symbols loaded should be added to the global namespace or not via the `RTLD_GLOBAL`/`RTLD_LOCAL` flags. [The default is `RTLD_GLOBAL`](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/dlopen.3.html). | Same as OS X, but [the default is `RTLD_LOCAL`](https://www.man7.org/linux/man-pages/man3/dlmopen.3.html) (i.e. symbols are not added to the global namespace unless specified otherwise). |

Even on platforms that support a global symbol namespace, using that namespace is generally inadvisable because it can lead to highly challenging bugs to resolve if multiple libraries in the same process space expose symbols with the same name and they are all loaded into the same process space.
This class of problem is traditionally handled in C, for example, by advising all libraries to prefix all functions with some library-specific name, e.g. `libfoo` would define `foo_do_something` and `libbar` would define `bar_do_something`.
While languages like C++ are better equipped to handle this situation natively using tools like namespaces and name mangling, the problem can still easily rear its end due to e.g. standard library (or any header-only library) template functions with the same parameters being instantiated with the exact same template parameters in multiple different binaries.
It is therefore highly likely that in a complex application multiple shared libraries will define symbols with the same name.

Typically such **symbol collisions** are handled more gracefully when load-time linking is employed.
Common header-only libraries (like the STL) will mark various functions that could be defined multiple times as [weak symbols](https://en.wikipedia.org/wiki/Weak_symbol) to support this kind of usage, and if such approaches are not used then the linker will surface a multiple definition error at compile time and it can therefore be handled by the developer.
When using runtime linking, however, these errors are deferred and passed on to the user at a point when they can do nothing about them.
Thus, populating symbols into the global symbol table with `dlopen` is generally something that should be avoided.
One reason OS X moved from the flat namespace to the two-level namespace is precisely because it dramatically reduces the risks of symbol collisions at runtime.

#### Undefined Symbols

A second factor is that different platforms have different ways of handling undefined symbols at build time.
When building a library, it may be possible to specify that symbols may be undefined at link-time.
A common example of how this would look in source code would be for a C header to be included without any corresponding definition in a source file.
However, undefined symbols could also result from post-processing of a binary, for instance by manually removing a `DT_NEEDED` entry from an ELF binary using patchelf.

|         | Windows | OS X | Linux |
|---------|---------|------|-------|
| Linker setting    | By default when building a DLL all symbols must be resolved, but this behavior can be disabled using the [`/FORCE:Unresolved`](https://learn.microsoft.com/en-us/cpp/build/reference/force-force-file-output?view=msvc-170) linker flag | By default all symbols must be resolved, but this behavior can be disabled using the [`-undefined dynamic_lookup`](https://www.unix.com/man-page/OSX/1/ld/) linker flag. | By default, undefined symbols are allowed (except in special cases such as transitive shared library dependencies of an executable), but this behavior can be changed using [the `--no-undefined` and `--no-allow-shlib-undefined`](https://linux.die.net/man/1/ld) linker flags.
| Runtime behavior     | As discussed in [this thread](https://developercommunity.visualstudio.com/t/Runtime-symbol-resolution-with-FORCE:UNR/10767093#T-N10775302-N10778881), binaries built with `/FORCE:UNRESOLVED` are not meant to be loadable and there is no way to get unresolved symbols to be resolved at runtime. | The runtime behavior for undefined symbols depends on how the symbol namespacing was defined at compile-time. If the library was compiled with a two-level namespace, then undefined symbols will fail to resolve and the library will fail to load at runtime as on Windows. If the library was compiled with a flat namespace, then the undefined symbols will be resolved at runtime by lookup in every library that has been loaded into the process space. The exact behavior differs for load-time and runtime linking ([see section 1.5.4 of Drepper's dsohowto document](https://akkadia.org/drepper/dsohowto.pdf) for a description of this behavior on Linux, which is what the OS X behavior is modeled on): in brief the main difference is that while libraries always first look up symbols in the global and then a local namespace, when using `dlopen` with `RTLD_LOCAL` only the set of libraries that are in the transitive closure of the dependency tree of the library being `dlopen`ed participate in the symbol lookup. | Symbols are always looked up using the flat namespace lookup rules described for OS X. |

Understanding how undefined symbols are resolved is important because in theory they offer one way that we could sidestep the need to address point 3.
If a library's dependency were to be removed altogether, then it would not longer be necessary for the loader to find that dependency when the library is loaded.
In exchange, however, it creates a new problem of ensuring that all of the undefined symbols in the library must now be resolvable using only symbols in the library itself or in the global symbol namespace.
We will discuss this approach below in [](#potential-solutions-for-library-sharing).

## Potential Solutions for Library Sharing

With the above background, we can more precisely state exactly what our goal is.
We started out with problem 3 above:

> Ensuring that all installed binaries know how to find their dependencies

However, a more precise statement is

> Ensuring that all installed binaries know how to find their dependencies, and that all symbols can be resolved

Therefore, solutions that remove dependencies altogether may be acceptable if all symbols can be resolved without those dependencies specified.

With this background, we are in a position to discuss the various ways in which we can safely share symbols across shared library boundaries in extension modules distributed as wheels.
Most of these options are already in use in some form or another, so the key is to identify the ones that are safe and portable across platforms.
An alternative to portability is to choose a different solution on each platform; however, this introduces additional maintenance cost and complexity, so it would be preferable to avoid.
We consider solutions roughly in order of increasing similarity to the way that shared libraries work for non-pip package management solutions.

### Option 1: Require Users to Install the Libraries

With this solution, users are required to install the libraries themselves, either via a system package manager or some other means.
This solution is the simplest for developers and avoids any risk of bundled libraries conflicting with system-installed libraries or symbol collisions.
However, this solution is also the least friendly to users unfamiliar with library management beyond Python pip installation since if dependencies are missing the extension module will fail to load and will display an unfriendly error message (usually an `OSError` showing that shared library failed to open).
Stackoverflow, Github, and other similar sites are littered with error reports from users who have encountered this problem for various libraries.
Therefore, while this is the simplest solution, the poor user experience is bad enough that that this approach should generally be avoided.

### Option 2: Bundle All Dependencies

At present, the only truly safe approach that Python extension modules take is to sidestep the issue entirely by bundling all dependencies into the wheel.
They do so either by statically linking the dependencies into the extension module or by copying shared library dependencies into the wheel and modifying the extension modules to find these copies.
This approach completely avoids the need to search for shared libraries externally, but it has two main drawbacks:

1. It increases binary size since every wheel that uses the same library will contain a copy of that library's code.
2. Libraries with global state or objects like C++ virtual classes that have RTTI (and vtables) may not be safe to use if multiple copies of their symbols exist in the same process space.

Static linking is the leaner of the above two options since it only copies necessary symbols into the final executable, whereas bundling a shared library copies the entire contents wholesale.
Static linking also enables greater protection against symbol conflicts if used correctly since symbols can be marked as internal to the library at link-time to avoid external visibility.
Empirically, however, Python extension modules leverage dynamic linking far more often than static linking, so the Python community has built tooling to support building portable packages from dynamically linked extension modules by bundling all dynamic library dependencies into the package.
[auditwheel](https://github.com/pypa/auditwheel) for Linux, [delvewheel](https://github.com/adang1345/delvewheel) for Windows, and [delocate](https://github.com/matthew-brett/delocate) for OS X (and more recently, the cross-platform [repairwheel](https://github.com/jvolkman/repairwheel)), are tools that will traverse the library dependency chain for all extension modules in a package and copy those dependencies into a suitable place in the package, fixing up the extension modules as needed to find the package's internal copies of those dependencies.

:::{note}
In the case of auditwheel, delocate, and delvewheel, it is instructive to consider their actual mode of operation based on the above discussion of how libraries are loaded.
auditwheel and delocate both leverage run paths to specify library internal dependencies.
auditwheel uses the `RPATH`, while delocate sets the `@rpath` of the extension module as well as modifying the install name of the bundled libraries.
Since Windows does not support runpaths, delvewheel uses a different approach.
For older versions of Python, it leverages the loaded-module list by preloading the bundled libraries before loading the extension modules.
For newer versions of Python, delvewheel uses `os.add_dll_directory` to add the directory containing the bundled libraries to the search path.
Note that both of these approaches for delvewheel involve directly patching the source of the Python package to add the necessary code to load the libraries.
:::

Beyond binary size, bundling dynamic libraries has other implications.
This behavior could be problematic if a wheel vendors a library that is identical to a system-installed library, since then any program that attempts to load both will be susceptible to surprising behaviors depending on which library is loaded first (because the loaded-modules list ensures that the first loaded library wins on all platforms).
To resolve this problem, the bundling tools all mangle the names of the bundled shared libraries using something like the hash of the library to make the library names unique.
This approach ensures that the libraries will not conflict with other versions of the library file existing on the system unless these files are binary-identical.
By doing so, however, the libraries do once again open up the possibility for multiple versions of the same library (e.g. libfoo v1.0 and libfoo v1.1) existing on the same system and having similar issues that may arise with static linking for global state/objects.

(option-3)=
### Option 3: Ship Libraries as Wheels and Make Them Discoverable by Other Wheels

Ultimately, this option is the goal that we seek to achieve.
We would like to be able to have a single copy of a shared library that can be reused by all other wheels on the system.

Ideally, we want to enable something like the following:
```
import libfoo  # This loads the C++ library
import pylibfoo  # This loads a Python package containing an extension module that requires libfoo.so
```

The remaining solutions will all assume that library dependencies are being shipped as standalone wheels.
All such solutions have the major benefit that no user intervention is required to install the libraries since they will be automatically handled by the pip dependency resolver.

#### Aside: PEP 725

Before we delve into the various currently possible options, we should briefly discuss PEP 725.
[PEP 725](https://peps.python.org/pep-0725/) offers a possible long-term solution to the problem, allowing Python packages to declare dependencies on system packages in a way that pip or other wheel-building tools can understand.
Something like this is ultimately necessary, but for PEP 725 to become fully usable we need (at least) four things to happen:

1. Wheels need a way of encoding that they depend on some library that may be found externally. This is what PEP 725 enables via pyproject.toml metadata.
2. pip and other build tools needs a way to translate that requirements list into a list of dependencies to find. This requires implementation on the part of each such tool.
3. System (or system-like, e.g. conda) package managers need to be updated to advertise to pip that a dependency installed by that package manager can be found. One option would be for package managers to expose some new metadata specific to pip, while an alternative would be for pip to leverage tools like CMake/meson/pkgconfig for their underlying finding capabilities.
4. pip/wheels will need a standard install location for libraries that come bundled with a wheel, as well as handling step 3 (advertising what libraries are installed). This may never be the focus if using system libraries (3) ends up always being the preferred route.

Communication between pip and other package managers is a critical piece of this since if different sources could be installing the same packages there must be a way to avoid them clobbering each other.
With conda, for example, [virtual packages](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/virtual_packages.html) provide this functionality by allowing conda to query the system for information that is beyond its scope.
However, conda (and other similar package managers) provide a greater degree of isolation than pip can with respect to native (non-Python) libraries, so PEP 725 needs to go further.

While PEP 725 is a great step in the right direction, however, it is likely years away from being a viable production solution across all use cases.
Moreover, even if all of the above steps occur we cannot assume that users will be in a position to easily install said external dependencies from a non-pip source.
Therefore, even in a PEP 725 world -- and certainly today -- we need to determine what the best way is to distribute native libraries via pip right now.

#### Option 3a: Shipping Libraries in Wheels and Creating Runpath-Dependent Extension Modules

One option is to modify the runpaths in extension modules.
The key with this solution is to assume that extension modules are always going to be installed in the same prefix as the libraries they depend on.
Then, runpaths can be set to be relative paths that point to the location of the libraries.

This solution seems attractive on its face, but it has numerous drawbacks:
- It is not fully portable since Windows does not support runpath-dependent libraries
- It requires every consumer of a library to track the layout of the library wheel to ensure that the relative paths are set up correctly. Any change to the layout of the library wheel becomes a breaking change for its consumers. A more robust and flexible solution would have the wheel somehow "export" its layout for consumers.
- Runpaths assume that packages are installed into the same prefix with a specific layout. With the modern Python import system, between meta path hooks, PYTHONPATH, and other similar modifications there is no guarantee that any set of relative paths will be sufficient to cover all cases. In principle one could decide to support a subset of layouts, but it does make for a fairly unpalatable option of having a perpetually growing list of runpaths, and in any unsupported layout the error mode will be the same unfriendly error that would be encountered if the library wasn't installed at all.
- Provides a somewhat misleading sense of control: because the loaded-module list always preempts library searches, setting runpaths only helps increase the chances of finding a library, it does not guarantee which copy will be found. This fact can lead to particularly difficult-to-debug issues if multiple versions of a library are installed on the system and the wrong one is used because the wrong library was loaded first by something else (either another Python package, or in the case of an embedded Python instance the original binary such as MPI or some GUI).

#### Option 3b: Environment Variables

Normally, a common way to make libraries discoverable is to set the appropriate environment variables.
This solution is generally frowned upon in the context of distribution because it is not portable and requires runtime modifications, but it is commonly used by end-users.
The relevant variables are `LD_LIBRARY_PATH` on Linux, `DYLD_LIBRARY_PATH` on Mac, and `PATH` on Windows.
Unfortunately, these variables cannot be used to satisfy the use case described above.
The problem is that on all platforms these variables are read once when the dynamic loader is first loaded into memory rather than being read from each time the loader tries to load a new library.
If a Python package provides a shared library, there is no way for that package to ensure that the environment variables are modified before the loader is loaded since that happens as soon as Python itself starts.
If we were always in a virtual environment (this is effectively how conda manages some things) and if virtual environments had well-defined entry points for hooking in to set environment variables we could embed the information in the environment.
Since neither of these assumptions holds in general, though, environment variables are not viable

#### Option 3c: Dynamic Loader APIs

The AddDllDirectory function on Windows is a good example of a dynamic loader API that can be used to modify the search path for libraries.
Such an API would be a good solution if it existed on all platforms, but until OS X and Linux loaders expose such a function this solution is not generally viable.

(option-3d)=
#### Option 3d: Load Libraries Globally to Satisfy Undefined Symbols

Yet another option is to create libraries that have undefined symbols that are not satisfied by specific dependencies (either by compiling with suitable linker flags or by post-processing binaries to remove dependencies) and then rely on those symbols being resolved at runtime by lookup in the global symbol table.
To add needed symbols to the global symbol table, the library containing them must be loaded with `RTLD_GLOBAL` or equivalent.
This solution has the advantage of only requiring pure Python changes.
Extension modules can import the Python package containing the library (or use `importlib` to locate it if the dependency wheel is not actually an importable Python package) and then use `ctypes` to load the library.
This minimizes the need for knowing wheel layouts and it avoids making any assumptions about where the dependency wheel is installed except that it must be somewhere that Python itself can find.
However, as discussed in [](#undefined-symbols) this approach is not portable to Windows and on other platforms it runs a significant risk of symbol collisions, making it generally a poor choice.

#### Option 3e: Leveraging the Loaded-Libraries List

This option is similar to [](#option-3d), but instead of relying on the global symbol table to resolve symbols, it relies on the loaded-modules list.
There are two main differences:
- The dependency library must be loaded with `RTLD_LOCAL` instead of `RTLD_GLOBAL` on OS X and Linux (as discussed, this behavior is always implicit on Windows)
- The dependent library should continue to express the dependency explicitly

By loading the dependency in this way, when the dependent library is loaded the loader will first check the loaded-modules list to see if the dependency is already loaded, and it will therefore find the dependency without needing to be able to locate it on the filesystem.
As discussed in [](#how-the-loader-finds-libraries), this solution requires that the library be loaded with the same key as the one in the loaded-modules list, i.e. the install name on OS X or the SONAME on Linux.

<!--On OS X there is an additional requirement imposed on the consuming extension module: the entry in the load commands must have a name that exactly matches the install name of the native library being loaded including the full path (whereas on Linux it simply must match the SONAME).-->

This solution is the most robust of all of the options discussed so far:
- It works for arbitrary package layouts and installation prefixes since it only requires that the dependency library be in a Python wheel that is importable
- It avoids arbitrary symbol collisions since the loaded-modules list is used to resolve symbols with no symbols loaded into the global namespace
- It is portable across all platforms
- It allows reuse of a single shared library, avoiding the various issues around bundling

As such, this approach is the most desirable of those discussed so far.

## Avoiding Library Collisions

In [](#symbol-namespacing) and [](#undefined-symbols) we discussed the possibility of symbol collisions in some detail.
However, we only briefly touched on the problem of library collisions in [](#how-the-loader-finds-libraries).
Having multiple versions of the same library loaded into the same process space is an important problem that we must address if we go down the route of distributing libraries in wheels.
On OS X and Linux, some level of protection is intrinsically afforded by the way library versioning is handled (see [the section on Specifying Version Information on OS X](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryDesignGuidelines.html#//apple_ref/doc/uid/TP40002013-SW19), and [SONAME versioning on Linux](https://tldp.org/HOWTO/Program-Library-HOWTO/shared-libraries.html)); if you always dlopen the versioned name of a library rather than the unversioned one you get some degree of protection that is not available on Windows.
However, that is still insufficient since all it guarantees is loading an ABI-compatible version, not necessarily one that contains all the necessary symbols (i.e. you could get an earlier minor version from the same major family that is missing the newest functions that you need).

The library name-mangling scheme employed by auditwheel, delocate, and delvewheel is one way to avoid this problem.
It ensures that if one Python package happens to use a system library, it will not "poison" the environment since the name in the loaded-modules list will differ from the mangled name that would be added by any extension module linking to the version of the library shipped in a wheel.
However, mangling in this form has clear drawbacks.
- It forces all consumers of that library to build against that exact wheel (or apply some post-processing with e.g. patchelf so that the dependency name is expressed correctly)
- It obviates any ability to use different but ABI-compatible versions
- It prevents any clever solutions that attempt to allow dynamic runtime determination of whether to use a system library or the bundled library. This could be desirable in specific cases such as installation into containers or HPC environments where a version of the library installed on the system might be preferable to the one in the wheel due to e.g. being compiled with different compile-time flags (a common example is MPI, where knowledge of the fabrics available on the specific installation target is important to compile an optimal library for performance). However, the existence of the loaded-modules list means that there is absolutely no safe way to enable this functionality; library authors choose not to mangle for this reason at their own risk.

As such, shipping wheels with libraries in the way proposed in [](#option-3) is not a perfect solution and does have drawbacks relative to what PEP 725 would enable.
With the current proposed solution, it is advisable to name-mangle for safety, but whether or not to do so will ultimately be a decision for each library author depending on the ABI stability of the library, the importance of enabling end-users to choose to use a system installation of the library if one exists, and any other potential considerations.

### Mangling on OS X

Note that with the scheme proposed here, the relevant mangling on OS X is of the install name.
Due to the way that the linker places the install name into the `LC_LOAD_DYLIB` entries and the way those are used at runtime to load libraries, we need to ensure that the install name of the loaded library exactly matches the `LC_LOAD_DYLIB` entries in the consuming Mach-O file.
The easiest way those could be made to match is by stripping out all path components from both and simply using the filename (e.g. `libexample.dylib`), but that would lead to potential collisions.
Therefore, what is needed is to ensure that the install name is mangled so that it does not conflict with other installations of the same library.

## See Also

Here are some links with discussions relevant to this topic:
- https://github.com/njsmith/wheel-builders/blob/pynativelib-proposal/pynativelib-proposal.rst
- https://discuss.python.org/t/native-dependencies-in-other-wheels-how-i-do-it-but-maybe-we-can-standardize-something/23913/
