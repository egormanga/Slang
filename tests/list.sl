#| Slang `list' test. |#

list l = [int: 1, 2, 3]

main {
	#int i = 0
	#while (i < 3) {
	for i in (0 to 3) {
		stdio.println(i, l[i])
		#i -=- 1
	}
	for i in l stdio.println(i)
	stdio.println(l, *l)
}
