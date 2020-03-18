#include <stdarg.h>
#include <string.h>

typedef struct atom {
	enum {b, i8, u8, i16, u16, i32, u32, i64, u64, i128, u128} type;
	union {
		_Bool* b;
		int8_t* i8;
		uint8_t* u8;
		int16_t* i16;
		uint16_t* u16;
		int32_t* i32;
		uint32_t* u32;
		int64_t* i64;
		uint64_t* u64;
		void* data;
	};
} atom_t;

typedef atom_t (*builtin_function)(int nargs, atom_t args[nargs]);

typedef struct builtin {
	const char* name;
	builtin_function fp;
} builtin_t;


/// XXX ///


atom_t _builtin_println(int nargs, atom_t args[nargs]) {
	static int res;
	res = puts(args[0].data);
	return (atom_t){i32, .i32 = &res};
}


/// XXX ///


builtin_t builtins[] = {
	{"println", _builtin_println},
{NULL, NULL}};

builtin_function get_builtin(const char* name) {
	for (builtin_t* i = builtins; i->name != NULL; i++)
		if (strcmp(i->name, name) == 0)
			return i->fp;
	return NULL;
}
