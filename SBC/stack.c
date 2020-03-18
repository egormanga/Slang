/*
#define CAT(a, b) a##_##b
#define TEMPLATE(name, type) CAT(name, type)

#define stack		TEMPLATE(stack, T)
#define stack_t	TEMPLATE(stack_t, T)
#define stack_item	TEMPLATE(stack_item, T)
#define stack_push	TEMPLATE(stack_push, T)
#define stack_pop	TEMPLATE(stack_pop, T)
*/

#define T atom_t

typedef struct stack {
	struct stack_item* top;
} stack_t;

struct stack_item {
	T data;
	struct stack_item* below;
};

stack_t* stack() {
	stack_t* st = malloc(sizeof(*st));
	st->top = NULL;
	return st;
}

void stack_push(stack_t* st, T data) {
	struct stack_item* new = malloc(sizeof(*new));
	new->data = data;
	if (st->top != NULL) new->below = st->top;
	st->top = new;
}

T stack_pop(stack_t* st) {
	assert (st->top != NULL);
	struct stack_item* item = st->top;
	st->top = item->below;
	T data = item->data;
	free(item);
	return data;
}

/*
#undef stack
#undef stack_t
#undef stack_item
#undef stack_push
#undef stack_pop
*/

#undef T
