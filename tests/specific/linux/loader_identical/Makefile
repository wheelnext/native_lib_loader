.PHONY: clean with_soname without_soname

clean:
	rm -f a/libfoo.so b/libfoo.so c/libbar.so main main_osx

with_soname:
	gcc -shared -fPIC -Wl,-soname,libfoo.so -o a/libfoo.so a/foo.c
	gcc -shared -fPIC -Wl,-soname,libfoo.so -o b/libfoo.so b/foo.c
	gcc -shared -fPIC -o c/libbar.so c/bar.c -lfoo -La/
	gcc -ldl -o main main.c
	./main
	LOAD_B=1 ./main

without_soname:
	gcc -shared -fPIC -o a/libfoo.so a/foo.c
	gcc -shared -fPIC -o b/libfoo.so b/foo.c
	gcc -shared -fPIC -o c/libbar.so c/bar.c -lfoo -La/
	gcc -ldl -o main main.c
	./main

osx:
	gcc -shared -fPIC -o a/libfoo.so a/foo.c
	gcc -shared -fPIC -o b/libfoo.so b/foo.c
	gcc -ldl -o main_osx main.c
	./main_osx
