CC = gcc
CFLAGS = -Wall -Wextra -Werror -g -D_GNU_SOURCE
RM = rm -f
NAME = ft_strace
SRC = ft_strace.c
OBJ = $(SRC:.c=.o)

all: $(NAME)

$(NAME): $(OBJ)
	$(CC) $(CFLAGS) -o $(NAME) $(OBJ)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	$(RM) $(OBJ)

fclean: clean
	$(RM) $(NAME)

re: 
	$(MAKE) fclean
	$(MAKE) all

PHONY: all clean fclean re