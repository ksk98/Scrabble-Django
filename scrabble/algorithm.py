from scrabble.word_set import words as dictionary


def creates_valid_word(board: list[list[str]], start_x: int, start_y: int, axis_is_x: bool) -> bool:
    current_pos = get_starting_pos_of_word(board, start_x, start_y, axis_is_x)
    word = []

    if axis_is_x:
        ind = 0
    else:
        ind = 1

    while current_pos[ind] < len(board):
        letter = board[current_pos[0]][current_pos[1]]

        if letter != "":
            word.append(letter)
        else:
            break

        current_pos[ind] += 1

    full_word = "".join(word)
    return full_word in dictionary


def get_starting_pos_of_word(board: list[list[str]], start_x: int, start_y: int, axis_is_x: bool) -> [int, int]:
    current_pos = [start_x, start_y]

    if axis_is_x:
        while current_pos[0] > 0:
            if board[current_pos[0] - 1][current_pos[1]] != "":
                current_pos[0] -= 1
            else:
                break
    else:
        while current_pos[1] > 0:
            if board[current_pos[0]][current_pos[1 - 1]] != "":
                current_pos[1] -= 1
            else:
                break

    return [current_pos[0], current_pos[1]]


def board_to_string(board: list[list[str]]) -> str:
    return ''.join(item for inner_list in board for item in inner_list)
