#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    void *a_handle = dlopen("a/libfoo.so", RTLD_LAZY |RTLD_LOCAL);
    if (a_handle == NULL) {
        fprintf(stderr, "dlopen: %s\n", dlerror());
        return 1;
    }
    int (*a_square)(int) = dlsym(a_handle, "square");
    if (a_square == NULL) {
      fprintf(stderr, "dlsym: %s\n", dlerror());
      return 1;
    }

    void *b_handle = dlopen("b/libfoo.so", RTLD_LAZY |RTLD_LOCAL);
    if (b_handle == NULL) {
        fprintf(stderr, "dlopen: %s\n", dlerror());
        return 1;
    }
    int (*b_square)(int) = dlsym(b_handle, "square");
    if (b_square == NULL) {
      fprintf(stderr, "dlsym: %s\n", dlerror());
      return 1;
    }

    int const x = 2;
    printf("With a, the square %d is %d\n", x, a_square(x));
    printf("With b, the square %d is %d\n", x, b_square(x));

    dlclose(a_handle);
    dlclose(b_handle);

    return 0;
}
