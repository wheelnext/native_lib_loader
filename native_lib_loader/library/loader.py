import ctypes
import os


class LibraryLoader:
    def __init__(self, path_to_local_lib, lib_name):
        self._path = path_to_local_lib
        self._lib = lib_name

    def load(self):
        # Try system library path first, then try the local path in the wheel.
        try:
            lib = ctypes.CDLL(self._lib, ctypes.RTLD_GLOBAL)
        except OSError:
            lib = ctypes.CDLL(
                os.path.join(
                    self._path,
                    self._lib,
                ),
                ctypes.RTLD_GLOBAL,
            )

        return lib
