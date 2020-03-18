class Test {
	int a = 1

	init {
		.a = 3
	}

	constr () {
		.a = 5
	}

	constr (int a) {
		.a = a
	}
}

main {
	stdio.println(Test.a)

	Test t
	stdio.println(t.a)
	t.a = 2
	stdio.println(t.a)
	delete t

	Test t = Test()
	stdio.println(t.a)
	delete t

	Test t = Test(7)
	stdio.println(t.a)
	delete t

	#Test t(10)
	#stdio.println(t.a)
	#delete t
}
