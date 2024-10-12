#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    // b/libfoo.so contains the definition of square that c/libbar.so uses
    void *a_handle;
    if (getenv("LOAD_A") != NULL) {
      a_handle = dlopen("a/libfoo.so", RTLD_LAZY | RTLD_GLOBAL);
      if (a_handle == NULL) {
          fprintf(stderr, "dlopen: %s\n", dlerror());
          return 1;
      }
    }
    void *b_handle = dlopen("b/libbar.so", RTLD_LAZY | RTLD_LOCAL);
    if (b_handle == NULL) {
        fprintf(stderr, "dlopen: %s\n", dlerror());
        return 1;
    }

    int (*b_four)(int) = dlsym(b_handle, "power_four");
    if (b_four == NULL) {
        return 1;
    }

    int const x = 2;
    int const expected = x * x * x * x;
    int const actual = b_four(x);

    dlclose(b_handle);
    if (getenv("LOAD_A") != NULL) {
        dlclose(a_handle); 
        printf("With a loaded, the fourth power of %d is %d, got %d\n", x, expected, actual);
    } else {
        printf("The fourth power of %d is %d, got %d\n", x, expected, actual);
    }

    return 0;
}
