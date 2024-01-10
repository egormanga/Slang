#| Slang `class' test. |#

class Test {
	int a = 1

	init {
		.a = 3
	}

	constr () {
		.a = 5
	}

	constr (int .a);
}

main {
	stdio.println(Test.a)  # 1

	Test t
	stdio.println(t.a)  # 3
	t.a = 2
	stdio.println(t.a)  # 2
	delete t

	Test t = Test()
	stdio.println(t.a)  # 5
	delete t

	Test t = Test(7)
	stdio.println(t.a)  # 7
	delete t

	#Test t(10)
	#stdio.println(t.a)  # 10
	#delete t
}
