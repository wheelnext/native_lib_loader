#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    // b/libfoo.so contains an erroneous definition of square
    void *b_handle;
    if (getenv("LOAD_B") != NULL) {
      b_handle = dlopen("b/libfoo.so", RTLD_LAZY |RTLD_LOCAL);
      if (b_handle == NULL) {
          fprintf(stderr, "dlopen: %s\n", dlerror());
          return 1;
      }
    }
    void *a_handle = dlopen("a/libfoo.so", RTLD_LAZY |RTLD_LOCAL);
    if (a_handle == NULL) {
        fprintf(stderr, "dlopen: %s\n", dlerror());
        return 1;
    }
    void *c_handle = dlopen("c/libbar.so", RTLD_LAZY |RTLD_LOCAL);
    if (c_handle == NULL) {
        fprintf(stderr, "dlopen: %s\n", dlerror());
        return 1;
    }

    int (*c_four)(int) = dlsym(c_handle, "power_four");
    if (c_four == NULL) {
        return 1;
    }

    int const x = 2;
    int const expected = x * x * x * x;
    int const actual = c_four(x);

    dlclose(a_handle);
    dlclose(c_handle);
    if (getenv("LOAD_B") != NULL) {
        dlclose(b_handle); 
        printf("With b loaded, the fourth power of %d is %d, got %d\n", x, expected, actual);
    } else {
        printf("The fourth power of %d is %d, got %d\n", x, expected, actual);
    }

    return 0;
}
