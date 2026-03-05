#include <stdio.h>

int main(void) {
    char *s = NULL;

    // NULL 포인터를 문자열 버퍼처럼 쓰면 UB, 보통 segfault
    s[0] = 'A';

    // 또는 puts(s); / strcpy(s, "hi"); 도 비슷하게 터질 수 있음
    return 0;
}
