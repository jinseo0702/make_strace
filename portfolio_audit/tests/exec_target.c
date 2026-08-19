#include <string.h>

int main(int argc, char **argv, char **envp)
{
    if (argc != 3)
        return 93;
    if (strcmp(argv[1], "alpha") != 0)
        return 94;
    if (strcmp(argv[2], "beta") != 0)
        return 95;
    if (envp == NULL || envp[0] != NULL)
        return 96;
    return 23;
}
