class void {}

class bool {
	castable to int;

	bool operator !;
}

class int {
	castable to bool;
	castable to float;

	int operator +;
	int operator -;
	int operator ~;

	int operator +int;
	int operator -int;
	int operator *int;
	int operator //int;
	int operator **int;
	int operator %int;
	int operator <<int;
	int operator >>int;
	int operator &int;
	int operator ^int;
	int operator |int;

	range operator 'to' int;

	int popcount();
	int length(int base=2);
}

class float {
	float operator +;
	float operator -;
	bool operator !;

	float operator +float;
	float operator -float;
	float operator *float;
	float operator /float;
	int operator //float;
	float operator **float;
	float operator %float;

	int round();
	bool isint();
}

class char {
	castable to str;

	bool operator !;

	char operator +char;
	char operator +int;
	char operator -char;
	char operator -int;
	char operator *int;

	range operator 'to' char;
}

class str {
	bool operator !;

	iterable char;

	char operator [int];

	str operator +str;
	str operator *int;
}

class range {
	typename type;

	iterable type;

	type operator [int];
}

class list {
	typename type;

	iterable type;

	type operator [int];

	void append(type item);

	void insert(int index, type item);

	type pop();
	type pop(int index);

	void reverse();

	void sort();
}

class tuple {
	typename types[];

	iterable types;

	types operator [int];
}

class function {
	typename argtypes[];
	typename rettype;

	call rettype (*argtypes);

	rettype map(iterable);
}
