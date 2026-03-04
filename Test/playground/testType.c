#include <stdio.h>

int main(void){
    int a = -1;
    printf("a = %d\n", a);
    printf("a = %ld\n", (long)a);
    printf("a = %lld\n", (long long)a);
    printf("a = %zu\n", (size_t)a);
    printf("a = %zu\n", (ssize_t)a);
    printf("a = %zu\n", (off_t)a);
	return 0;
}