#| Slang `each' test. |#

main {
	list l = [int: 1, 2, 3]
	l.each(stdio.println)

	[int: 4, 5].each(stdio.println)
}
