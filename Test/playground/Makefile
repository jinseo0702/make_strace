CC = gcc
CFLAGS = -Wall -Wextra -Werror -g
RM = rm -f
NAME = playground
SRC = ex02.c
OBJ = $(SRC:.c=.o)

all: $(NAME)

$(NAME): $(OBJ)
	$(CC) $(CFLAGS) -o $(NAME) $(OBJ)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	$(RM) $(OBJ)

fclean: clean
	$(RM) playground

re: 
	$(MAKE) fclean
	$(MAKE) all

PHONY: all clean fclean re