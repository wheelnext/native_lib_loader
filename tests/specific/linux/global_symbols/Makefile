.PHONY: clean demo

clean:
	rm -f a/libfoo.so b/libbar.so main

demo:
	gcc -shared -fPIC -Wl,-soname,libfoo.so -o a/libfoo.so a/foo.c
	gcc -shared -fPIC -o b/libbar.so b/bar.c -Wl,--allow-shlib-undefined
	gcc -ldl -o main main.c
	LOAD_A=1 ./main
	./main || echo "Failed without loading a/libfoo.so"
